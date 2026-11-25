using Newtonsoft.Json.Linq;
using UnityEngine;

/// <summary>
/// After (未来の環境) を決める共通の判定。CoGroundAfterView (物体) と CoGroundRuleTagView (吹き出し) が使う。
///
/// ■ いつ見せるか
///   Plan (どの物をどこへ) だけでは、腕が届くか・禁止区域を通らずに行けるかは分からない。
///   なので、依頼の結果は、動作計画 (motion.plan) の結果が出た step から順に見せる (結果がまだの step は IsChecking)。
///   全部の step に結果が出るまでは Stage.Checking (IsConfirmed が false)。
///   進入禁止のルールがあるときは、サーバーが全 step の結果をまとめて出す (途中で結果が覆りうるため)。
///   サーバーは依頼 (task.request) を受けると、自動で動作計画を始める (Services.start_auto_motion_plan)。
///   RequireTask / RequireMotion で変えられる (CoGroundRuleTagView の Inspector)。
///
/// ■ 片付くか
///   Plan の step が ok で、動作計画で ok なら片付く。infeasible (届かない・通れない)、
///   動作計画そのものの失敗 (motion.status = failed) なら「計画できない」。
///   禁止区域で通れない物は、サーバーが Plan の step を保留 (deferred, 違反の判定つき) にする。
///
/// ■ 検証済みの予測 (motion.preview)
///   サーバーは、step ごとの検証結果を state の motion.preview にまとめて出す (ステップ別の予測・最終 After・実行が同じ版を見る):
///     move (この順番で運べると検証できた) / stay_rule (家庭ルールにより残す) / stay_infeasible (動作が成立せず残す) /
///     checking (確認中) / unverified (未確認。今回の実行の対象から外れる)
///   「皿を棚に置く」という作業の候補ができただけ (検証前) の物は、移動する予定として見せない。
///
/// ■ どの時点を見せるか (UpToIndex)
///   Before → ①の後 → ②の後 → 最終 After を切り替えるため、「この番号の step まで終わった時点」を UpToIndex に入れる
///   (最終 After は int.MaxValue)。その時点までに動く物だけが「動いた」扱いになる (MovedAtView)。
///   後の step で動く物は、その時点ではまだ元の位置にある。CoGroundAfterView.SetViewStep で変える。
///
/// ■ 置き終わった姿勢
///   動作計画があり、その step が ok なら、時間軸の最後の姿勢 (CoGroundTaskPlanPlayer の rest)。
///   無ければ Plan の置き位置 (step.to.pose)。どちらも bbox の中心の姿勢。
///   動作計画は再生しない。計算 (motion.plan) が終わった時点で、最後の姿勢はもう決まっている。
/// </summary>
public static class CoGroundFuture
{
    /// <summary>
    /// true なら、依頼 (task.request) が開いていない間は Plan を無いものとして扱う。
    /// サーバーは依頼が無くても運ぶ物すべてで Plan を作る (暗黙の依頼) が、それを「もう片付けを頼んだ」ように見せないため。
    /// CoGroundRuleTagView の Show Only With Request で変える。
    /// </summary>
    public static bool RequireTask = true;

    /// <summary>true なら、動作計画で確かめ終わるまで Plan を無いものとして扱う (IsConfirmed)</summary>
    public static bool RequireMotion = true;

    /// <summary>見せる時点: この番号 (0 始まり) の step まで終わった状態。最終 After は int.MaxValue</summary>
    public static int UpToIndex = int.MaxValue;

    public static class StepState
    {
        public const string Move = "move", StayRule = "stay_rule", StayInfeasible = "stay_infeasible",
            Checking = "checking", Unverified = "unverified";
    }

    /// <summary>state の motion.preview (無ければ null。古いサーバー)</summary>
    public static JObject Preview(JObject state) => state?["motion"]?["preview"] as JObject;

    /// <summary>motion.preview の、その step の項目 (state / reason / blocked_by)。無ければ null</summary>
    public static JObject PreviewStep(JObject state, string stepId)
    {
        if (Preview(state)?["steps"] is JArray steps)
            foreach (var s in steps)
                if ((string)s["step_id"] == stepId) return s as JObject;
        return null;
    }

    /// <summary>step の検証結果 (StepState のどれか) と理由</summary>
    public static string StateOf(JObject state, PlanDto plan, StepDto step, out string reason)
    {
        var p = PreviewStep(state, step.Id);
        if (p != null)
        {
            reason = (string)p["reason"];
            return (string)p["state"];
        }
        // 古いサーバー (preview が無い): Plan と motion.steps から決める
        reason = step.Message;
        if (step.Status == StepStatus.Infeasible) return StepState.StayInfeasible;
        if (step.Status != StepStatus.Ok) return StepState.StayRule;
        var ms = MotionStatus(state, plan, step, out reason);
        return ms == "ok" ? StepState.Move : ms == "infeasible" ? StepState.StayInfeasible : StepState.Unverified;
    }

    /// <summary>未確認 (検証が失敗した・タイムアウトした・検証のあとで状況が変わった)。今回の実行の対象から外れる</summary>
    public static bool IsUnverified(JObject state, PlanDto plan, StepDto step, out string reason) =>
        StateOf(state, plan, step, out reason) == StepState.Unverified;

    /// <summary>見せている時点 (UpToIndex) までに、この物体は動いている</summary>
    public static bool MovedAtView(JObject state, PlanDto plan, StepDto step) =>
        step.Index <= UpToIndex && WillBeDone(state, plan, step);

    public enum Stage
    {
        /// <summary>依頼が無い (RequireTask のとき)</summary>
        NoRequest,
        /// <summary>依頼はあるが、動作計画で確かめている途中 (または、まだ始まっていない)</summary>
        Checking,
        /// <summary>結果を見せられる</summary>
        Ready,
    }

    /// <summary>いまの段階</summary>
    public static Stage StageOf(JObject state)
    {
        var token = state?["plan"];
        if (RequireTask && !HasActiveTask(state)) return Stage.NoRequest;
        if (token == null || token.Type == JTokenType.Null) return Stage.Ready; // 運ぶ物が無い
        if (RequireMotion && !IsConfirmed(state, token)) return Stage.Checking;
        return Stage.Ready;
    }

    /// <summary>
    /// ok の step すべてに、動作計画の結果 (ok / infeasible) がある。または動作計画が失敗した。
    /// 計画中 (planning) は false。古くなった (stale) step があれば false。
    /// </summary>
    public static bool IsConfirmed(JObject state, JToken plan)
    {
        // 検証済みの予測があれば、それに従う。未確認 (unverified) の step は「未確認」として見せるので、確認中だけ待つ
        var preview = Preview(state);
        if (preview != null) return (string)preview["status"] != StepState.Checking;
        var motion = state?["motion"] as JObject;
        var status = (string)motion?["status"];
        if (status == "planning") return false;
        // 失敗も結果 (ok の step は「計画できない」になる)。ただし、この Plan を計画して失敗したときだけ (前の依頼の失敗は使わない)
        if (status == "failed") return (string)motion["plan_id"] == (string)plan?["id"];
        if (!(plan?["steps"] is JArray steps)) return true;
        foreach (var s in steps)
        {
            if ((string)s["status"] != StepStatus.Ok) continue;
            var m = motion?["steps"]?[(string)s["id"]];
            var ms = m != null && m.Type != JTokenType.Null ? (string)m["status"] : null;
            if (ms != "ok" && ms != "infeasible") return false;
        }
        return true;
    }

    /// <summary>開いている依頼がある (state.task があり、closed_at が空)</summary>
    public static bool HasActiveTask(JObject state)
    {
        var task = state?["task"];
        if (task == null || task.Type == JTokenType.Null) return false;
        var closed = task["closed_at"];
        return closed == null || closed.Type == JTokenType.Null;
    }

    /// <summary>
    /// 見せる Plan の JSON (依頼が要るのに無ければ null)。描き直しの判定にも使う。
    /// 確認中 (Stage.Checking) でも返す: 動作計画は step を順に確かめ、サーバーは結果が出た step から motion.preview に入れるので、
    /// 結果が出た物から順に見せる。まだ確かめていない step は IsChecking で、各表示が出さずに飛ばす。
    /// (古いサーバーは preview が無く、step ごとの「確認中」が分からないので、全部終わるまで null)
    /// </summary>
    public static JToken PlanToken(JObject state)
    {
        var token = state?["plan"];
        if (token == null || token.Type == JTokenType.Null) return null;
        var stage = StageOf(state);
        if (stage == Stage.NoRequest) return null;
        if (stage == Stage.Checking && Preview(state) == null) return null;
        return token;
    }

    /// <summary>この step は、動作計画でまだ確かめている途中 (結果が出るまで、ラベルや予測位置を出さない)</summary>
    public static bool IsChecking(JObject state, PlanDto plan, StepDto step) =>
        StateOf(state, plan, step, out _) == StepState.Checking;

    /// <summary>
    /// 動作計画での step の状態 (ok / infeasible / stale)。結果が無ければ null。
    /// motion.steps はいまの Plan の step id で引ける (Plan が作り直されて id が変わっても、サーバーが対応づける)。
    /// 動作計画そのものが失敗していれば、ok の step は infeasible (理由 = motion.error)
    /// </summary>
    public static string MotionStatus(JObject state, PlanDto plan, StepDto step, out string reason)
    {
        reason = null;
        var motion = state?["motion"] as JObject;
        if (motion == null || plan == null) return null;
        if ((string)motion["status"] == "failed" && (string)motion["plan_id"] == plan.Id && step.Status == StepStatus.Ok)
        {
            reason = (string)motion["error"];
            return "infeasible";
        }
        var s = motion["steps"]?[step.Id];
        if (s == null || s.Type == JTokenType.Null) return null;
        reason = (string)s["reason"];
        return (string)s["status"];
    }

    /// <summary>動作計画で「計画できない」と分かった</summary>
    public static bool IsMotionInfeasible(JObject state, PlanDto plan, StepDto step, out string reason) =>
        StateOf(state, plan, step, out reason) == StepState.StayInfeasible && step.Status == StepStatus.Ok;

    /// <summary>最終 After で片付いている (この順番で、把持・移動・配置まで実行できると検証できた)</summary>
    public static bool WillBeDone(JObject state, PlanDto plan, StepDto step) =>
        StateOf(state, plan, step, out _) == StepState.Move;

    /// <summary>置き終わった姿勢 (bbox の中心)。分からなければ false</summary>
    public static bool TryFinalPose(JObject state, PlanDto plan, StepDto step, out Vector3 position, out Quaternion rotation)
    {
        // 計画中は、時間軸がまだ前の計画のもの (新しい時間軸は全 step が終わってから届く) なので使わない
        if (MotionStatus(state, plan, step, out _) == "ok" && (string)state?["motion"]?["status"] != "planning")
        {
            var player = CoGroundTaskPlanPlayer.Instance;
            var obj = CoGroundSceneObject.Find(step.ObjectId);
            var pickable = obj != null ? obj.GetComponent<MoveItPickable>() : null;
            var name = pickable != null ? pickable.ObjectName : step.ObjectId;
            if (player != null && player.TryGetRestPose(name, out position, out rotation))
                return true;
        }
        if (step.To?.Pose != null)
        {
            position = step.To.Pose.PositionV;
            rotation = step.To.Pose.RotationQ;
            return true;
        }
        position = default;
        rotation = Quaternion.identity;
        return false;
    }

    /// <summary>この state の見せる Plan (無ければ、または依頼が要るのに無ければ null)</summary>
    public static PlanDto ReadPlan(JObject state)
    {
        var token = PlanToken(state);
        return token != null ? token.ToObject<PlanDto>(CoGroundServerClient.Serializer) : null;
    }
}
