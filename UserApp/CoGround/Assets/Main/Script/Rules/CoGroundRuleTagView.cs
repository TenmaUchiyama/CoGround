using System.Collections.Generic;
using Newtonsoft.Json.Linq;
using UnityEngine;

/// <summary>
/// サーバーの状態 (state.updated の plan / norms / zones) から、ルール表示の Prefab
/// (Resources/RuleTag の RuleBubble / RuleSign / RuleFloorArea) を置く。
///
/// ■ 物体の吹き出し (Plan の step ごと)
///   ok          義務 (青)          「R1  皿は流しへ」/ Before: sink_1 へ運ぶ。After では出さない (看板と置き終わった位置のコピーで分かる)
///   deferred    違反の判定あり → 禁止 (赤)「N1  触らない」/ Before: N1 に反するので運ばない、After: N1 に反するので残す
///               未確定だけ   → 判断できない (黄)。2 行目に足りない情報
///   ambiguous   判断できない (黄)  合うルールが複数ある (候補のルール番号)
///   unmatched   判断できない (黄)  行き先の領域がシーンに無い
///   infeasible  計画できない (灰)  動かし方を計画できない
///   許可 (紫) は、サーバーが「どの例外が効いたか」を返していないので、まだ出さない。
///   ルール番号は step の rule_id と判定 (verdicts) の rule_id をそのまま使うので、Before と After で同じになる。
///   吹き出しの下の行に、当てはまらなかった・判断できなかったルールも出す (Show Judgments。state.judgments):
///     「N1 doesn't apply: fragile = false (VLM)」
///   VLM が割れ物を「割れ物ではない」と間違えると、ルールは黙って非該当になる。ここに出しておけば、住人がその場で
///   気づいて直せる (CoGroundHomeCommands の「属性を訂正する」)。
///
/// ■ 置き場所の看板 (家庭ルールごと)
///   placed_in で領域を指すルール (片付けルールも含む) を、その領域を持つ物体 (流し・棚など) の上に立てる。
///   色はルールの norm (義務 = ここに置く / 禁止 = ここには置かない / 許可)。同じ場所に複数あれば横に並べる。
///   2 行目に条件 (「18:00–23:00」「unless box_white has no free space」など)。
///
/// ■ 床のエリア (家庭ルールごと)
///   target.kind = zone のルール (「18 時以降ここに入るな」など) を、state.zones の範囲に貼る。
///   2 行目に内容 (入る / 中にいる) と条件。条件が領域を読むルール (「台所の中ではゆっくり」) も、その領域に貼る。
///
/// ■ ロボットの上 (ロボット自身についてのルール)
///   target.kind = robot のルール (「子供が近いときは止まれ」「ゆっくり動け」) を、ロボットの上に並べる (Show Robot Rules)。
///
/// 内容と条件の言い方は、サーバーの語彙 (state.vocabulary) から読む (CoGroundNormText)。
///
/// ■ 使い方
///   CoGroundPlanView があるシーン (RoboSim) なら、Play 開始時に自動で作られる (Auto Add)。シーンに置いてもよい。
///   これがある間は、CoGroundPlanView / CoGroundAfterView の文字のラベルは止める (弧・ゴースト・物体を隠すのはそのまま)。
///   Before / After は CoGroundAfterView の Mode に合わせる。
/// </summary>
public class CoGroundRuleTagView : MonoBehaviour
{
    [SerializeField] CoGroundServerClient client;
    [Tooltip("空なら同じシーンから探す (Before / After の切り替えに使う)")]
    [SerializeField] CoGroundAfterView afterView;
    [Tooltip("空なら同じシーンから探す (文字のラベルを止める)")]
    [SerializeField] CoGroundPlanView planView;

    [Header("Prefab (空なら Resources/RuleTag)")]
    [SerializeField] GameObject bubblePrefab;
    [SerializeField] GameObject signPrefab;
    [SerializeField] GameObject floorPrefab;
    [Tooltip("配色 (空なら Resources/CoGroundRuleStyle)")]
    [SerializeField] CoGroundRuleStyle style;

    [Header("出すもの")]
    [SerializeField] bool showObjectBubbles = true;
    [SerializeField] bool showPlaceSigns = true;
    [SerializeField] bool showFloorAreas = true;
    [Tooltip("ロボット自身についてのルール (止まれ・ゆっくり動け) を、ロボットの上に出す")]
    [SerializeField] bool showRobotRules = true;
    [Tooltip("吹き出しに、当てはまらなかった・判断できなかったルールと、その根拠にした属性を出す (VLM の間違いに気づけるように)")]
    [SerializeField] bool showJudgments = true;
    [Tooltip("吹き出し 1 つに出す照合の行の上限")]
    [SerializeField] int maxJudgmentLines = 3;
    [Tooltip("看板と床に、条件 (時刻・依頼者・状態) を 2 行目として出す")]
    [SerializeField] bool showConditions = true;
    [Tooltip("1 行目の頭に【禁止】などの種類を出す")]
    [SerializeField] bool showKindLabel = true;
    [Tooltip("吹き出しの大きさ (Prefab の何倍か)。重なって見づらいときは小さくする")]
    [SerializeField] float bubbleScale = 0.6f;
    [Tooltip("看板の大きさ (Prefab の何倍か。棒も一緒に縮む)")]
    [SerializeField] float signScale = 0.6f;
    [Tooltip("床の文字の大きさ (Prefab の何倍か。模様の範囲は変わらない)")]
    [SerializeField] float floorLabelScale = 0.7f;
    [Tooltip("CoGroundPlanView の弧 (物体の通り道) を出す")]
    [SerializeField] bool showPlanArcs = false;
    [Tooltip("吹き出しを物体の上面からどれだけ上に出すか [m]")]
    [SerializeField] float bubbleGap = 0.04f;
    [Tooltip("同じ置き場所に看板が複数あるときの間隔 [m]")]
    [SerializeField] float signSpacing = 0.45f;
    [Tooltip("ロボットの上に並べる吹き出しの間隔 [m]")]
    [SerializeField] float robotRuleSpacing = 0.16f;

    [Header("依頼")]
    [Tooltip("依頼 (task.request) が開いていない間は、Plan (吹き出し・置き位置のゴースト・After) を出さない。看板と床はルールなので出す")]
    [SerializeField] bool showOnlyWithRequest = true;
    [Tooltip("Play を始めてサーバーにつながったら、前の依頼を閉じる (task.close)。毎回、依頼の前から始める")]
    [SerializeField] bool closeRequestOnStart = true;
    [Tooltip("依頼の結果は、動作計画 (腕が届くか・禁止区域を通らずに行けるか) で確かめ終わってから出す。確かめている間はロボットの上に「確認中」を出す")]
    [SerializeField] bool showOnlyAfterMotionPlan = true;

    CoGroundServerClient subscribed;
    JObject state;
    string drawnKey;
    CoGroundAfterView.ViewMode drawnMode;
    int drawnUpTo = int.MaxValue;
    readonly List<GameObject> spawned = new List<GameObject>();
    readonly Dictionary<string, string> ruleTexts = new Dictionary<string, string>();
    readonly Dictionary<string, Vector3> sizes = new Dictionary<string, Vector3>();

    // ---- ほかのスクリプト (表示ボタンなど) から ----

    /// <summary>ルール表示を全部出す / 隠す</summary>
    public bool Visible { get => enabled; set => enabled = value; }
    public bool ShowObjectBubbles { get => showObjectBubbles; set { showObjectBubbles = value; Rebuild(); } }
    public bool ShowPlaceSigns { get => showPlaceSigns; set { showPlaceSigns = value; Rebuild(); } }
    public bool ShowFloorAreas { get => showFloorAreas; set { showFloorAreas = value; Rebuild(); } }
    public bool ShowKindLabel { get => showKindLabel; set { showKindLabel = value; Rebuild(); } }
    public bool ShowRobotRules { get => showRobotRules; set { showRobotRules = value; Rebuild(); } }
    /// <summary>当てはまらなかったルールと、その根拠の属性を吹き出しに出す</summary>
    public bool ShowJudgments { get => showJudgments; set { showJudgments = value; Rebuild(); } }
    public bool ShowConditions { get => showConditions; set { showConditions = value; Rebuild(); } }
    /// <summary>CoGroundPlanView の弧 (物体の通り道)</summary>
    public bool ShowPlanArcs { get => showPlanArcs; set { showPlanArcs = value; if (planView != null) planView.ShowArcs = value; } }

    [ContextMenu("ルール表示を出す・隠す")]
    public void ToggleVisible() => Visible = !Visible;

    CoGroundServerClient Client => client != null ? client : CoGroundServerClient.Instance;
    bool IsAfter => afterView != null && afterView.isActiveAndEnabled && afterView.Mode == CoGroundAfterView.ViewMode.After;

    [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
    static void AutoAdd()
    {
        if (FindAnyObjectByType<CoGroundRuleTagView>() != null) return;
        if (FindAnyObjectByType<CoGroundPlanView>() == null) return; // Plan を描くシーンだけ
        new GameObject("CoGround Rule Tag View").AddComponent<CoGroundRuleTagView>();
        Debug.Log("[CoGroundRuleTagView] 自動で作った (ルール表示の Prefab で Plan を見せる)");
    }

    void Awake()
    {
        // 古い文字のラベルは、ほかの部品の Start (最初の描画) より前に止める
        if (planView == null) planView = FindAnyObjectByType<CoGroundPlanView>();
        if (afterView == null) afterView = FindAnyObjectByType<CoGroundAfterView>();
        CoGroundFuture.RequireTask = showOnlyWithRequest;
        CoGroundFuture.RequireMotion = showOnlyAfterMotionPlan;
        if (planView != null) { planView.ShowLabels = false; planView.ShowArcs = showPlanArcs; }
        if (afterView != null) afterView.ShowLabels = false;

        if (bubblePrefab == null) bubblePrefab = Resources.Load<GameObject>("RuleTag/RuleBubble");
        if (signPrefab == null) signPrefab = Resources.Load<GameObject>("RuleTag/RuleSign");
        if (floorPrefab == null) floorPrefab = Resources.Load<GameObject>("RuleTag/RuleFloorArea");
        if (bubblePrefab == null || signPrefab == null || floorPrefab == null)
            Debug.LogWarning("[CoGroundRuleTagView] Resources/RuleTag の Prefab が無い。メニュー CoGround > ルール表示の Prefab を作る", this);
    }

    void Start()
    {
        subscribed = Client;
        if (subscribed == null) { Debug.LogWarning("[CoGroundRuleTagView] CoGroundServerClient が見つからない", this); return; }
        subscribed.StateUpdated += OnStateUpdated;
        if (closeRequestOnStart)
        {
            subscribed.Connected += CloseRequestOnce;
            if (subscribed.IsConnected) CloseRequestOnce();
        }
        player = CoGroundTaskPlanPlayer.Instance;
        if (player != null) player.TimelineChanged += Rebuild;
        if (subscribed.LatestState != null) OnStateUpdated(subscribed.LatestState);
    }

    void OnDestroy()
    {
        if (subscribed != null) { subscribed.StateUpdated -= OnStateUpdated; subscribed.Connected -= CloseRequestOnce; }
        if (player != null) player.TimelineChanged -= Rebuild;
        Clear();
    }

    void OnEnable() { foreach (var g in spawned) if (g != null) g.SetActive(true); }
    void OnDisable() { foreach (var g in spawned) if (g != null) g.SetActive(false); }

    void Update()
    {
        // Before / After が切り替わったら描き直す
        var mode = IsAfter ? CoGroundAfterView.ViewMode.After : CoGroundAfterView.ViewMode.Before;
        if (state != null && (mode != drawnMode || CoGroundFuture.UpToIndex != drawnUpTo)) Rebuild();
    }

    CoGroundTaskPlanPlayer player;
    bool requestClosed;

    /// <summary>前の Play の依頼がサーバーに残っていれば閉じる (Play ごとに 1 回)</summary>
    async void CloseRequestOnce()
    {
        if (requestClosed || subscribed == null) return;
        requestClosed = true;
        try
        {
            await subscribed.RequestAsync("task.close");
            Debug.Log("[CoGroundRuleTagView] 前の依頼を閉じた (task.close)。依頼を送るまで Plan は出さない");
        }
        catch (System.Exception e)
        {
            // 開いている依頼が無ければ、サーバーは断る (No open request)。それで良い
            if (e.Message.Contains("No open request")) Debug.Log("[CoGroundRuleTagView] 前の依頼は無かった");
            else Debug.LogWarning("[CoGroundRuleTagView] task.close に失敗: " + e.Message, this);
        }
    }
    PlanDto drawnPlan;

    void OnStateUpdated(JObject s)
    {
        state = s;
        var key = CoGroundFuture.PlanToken(s)?.ToString(Newtonsoft.Json.Formatting.None) + "|" + s["norms"]?.ToString(Newtonsoft.Json.Formatting.None)
                  + "|" + s["rules"]?.ToString(Newtonsoft.Json.Formatting.None) + "|" + s["zones"]?.ToString(Newtonsoft.Json.Formatting.None)
                  + "|" + s["motion"]?.ToString(Newtonsoft.Json.Formatting.None) + "|" + CoGroundFuture.StageOf(s)
                  + "|" + s["judgments"]?.ToString(Newtonsoft.Json.Formatting.None) + "|" + (s["vocabulary"] != null);
        if (key == drawnKey) return;
        drawnKey = key;
        Rebuild();
    }

    /// <summary>今の state で描き直す</summary>
    public void Rebuild()
    {
        Clear();
        if (state == null) return;
        drawnMode = IsAfter ? CoGroundAfterView.ViewMode.After : CoGroundAfterView.ViewMode.Before;
        drawnUpTo = CoGroundFuture.UpToIndex;
        ReadTables();
        var norms = state["norms"] as JArray;

        var checking = showObjectBubbles && bubblePrefab != null && CoGroundFuture.StageOf(state) == CoGroundFuture.Stage.Checking;
        if (checking) BuildChecking();
        if (showRobotRules && bubblePrefab != null && norms != null) BuildRobotRules(norms, checking ? 1 : 0);
        if (showObjectBubbles && bubblePrefab != null)
        {
            var plan = drawnPlan = CoGroundFuture.ReadPlan(state);
            if (plan != null)
                foreach (var step in plan.Steps) BuildBubble(step);
        }
        if (norms != null)
        {
            if (showPlaceSigns && signPrefab != null) BuildSigns(norms);
            if (showFloorAreas && floorPrefab != null) BuildFloors(norms);
        }
        if (!isActiveAndEnabled) OnDisable();
    }

    void ReadTables()
    {
        ruleTexts.Clear();
        if (state["rules"] is JArray rules)
            foreach (var r in rules)
                if ((string)r["id"] is string id) ruleTexts[id] = (string)r["text"];
        if (state["norms"] is JArray norms) // 家庭ルールは住人の言葉 (original_text)
            foreach (var n in norms)
                if ((string)n["id"] is string id && (!string.IsNullOrEmpty((string)n["original_text"]) || !ruleTexts.ContainsKey(id)))
                    ruleTexts[id] = (string)n["original_text"];

        sizes.Clear();
        if (state["scene"]?["objects"] is JArray objects)
            foreach (var o in objects)
                if (o["size"] is JArray sz && sz.Count == 3) sizes[(string)o["id"]] = CoGroundServerClient.ToVector3(sz);
    }

    string RuleText(string id) => id != null && ruleTexts.TryGetValue(id, out var t) && !string.IsNullOrEmpty(t) ? t : "";

    // ---- 確認中 ----

    /// <summary>動作計画で確かめている間、ロボットの上に 1 つだけ出す (灰。種類の名前は出さない)</summary>
    void BuildChecking()
    {
        var robot = FindAnyObjectByType<RosJointToFetch>();
        if (robot == null) return;
        TryTop(robot.transform, out var top);
        var progress = (string)state["motion"]?["progress"];
        var tag = Spawn(bubblePrefab, "Rule Bubble (checking)", top + Vector3.up * bubbleGap, bubbleScale);
        tag.Set(CoGroundRuleKind.Infeasible, "", "Checking if the robot can do it…", progress ?? "", false);
        tag.Follow(robot.transform);
    }

    // ---- ロボット自身についてのルール ----

    /// <summary>target.kind = robot のルールを、ロボットの上に下から順に並べる (skip = 先に出ている吹き出しの数)</summary>
    void BuildRobotRules(JArray norms, int skip)
    {
        var robot = FindAnyObjectByType<RosJointToFetch>();
        if (robot == null) return;
        TryTop(robot.transform, out var top);
        var index = skip;
        foreach (var n in norms)
        {
            if (!CoGroundNormText.IsAboutRobot(n)) continue;
            var id = (string)n["id"];
            var at = top + Vector3.up * (bubbleGap + index * robotRuleSpacing);
            var tag = Spawn(bubblePrefab, $"Rule Bubble {id} (robot)", at, bubbleScale);
            tag.Set(NormKind((string)n["norm"]), id, Or((string)n["original_text"], CoGroundNormText.Content(n, state)),
                    ContentAndConditions(n), showKindLabel);
            tag.Follow(robot.transform);
            index++;
        }
    }

    /// <summary>「内容 · 条件」(例: the base moves at 0.2 m/s or slower · when a person (child) is within 2 m of the base)</summary>
    string ContentAndConditions(JToken norm)
    {
        var content = CoGroundNormText.Content(norm, state);
        var conditions = showConditions ? CoGroundNormText.Conditions(norm, state) : "";
        return string.IsNullOrEmpty(conditions) ? content : string.IsNullOrEmpty(content) ? conditions : content + " · " + conditions;
    }

    // ---- 物体の吹き出し ----

    void BuildBubble(StepDto step)
    {
        var after = drawnMode == CoGroundAfterView.ViewMode.After;
        // After で片付く物には吹き出しを出さない。置き場所は看板 (どの種類がここに来るか) と、
        // 置き終わった位置の半透明のコピー (どの物がここに来たか) で分かる
        // 見せている時点 (①の後 など) より後で動く物は、まだ元の位置にあるので「これから運ぶ」吹き出しを出す
        if (after && CoGroundFuture.MovedAtView(state, drawnPlan, step)) return;
        var obj = CoGroundSceneObject.Find(step.ObjectId);
        CoGroundRuleKind kind;
        string id = step.RuleId, text, note;

        // 動作計画 (motion.plan) で計画できないと分かった ok の step は「計画できない」
        string motionReason = null;
        bool motionInfeasible = step.Status == StepStatus.Ok
                                && CoGroundFuture.IsMotionInfeasible(state, drawnPlan, step, out motionReason);

        if (step.Status == StepStatus.Ok && CoGroundFuture.IsUnverified(state, drawnPlan, step, out var unverifiedReason))
        {
            // 未確認 (検証できなかった): 元の位置に理由を出し、今回の実行の対象から外す
            kind = CoGroundRuleKind.Infeasible;
            text = "Unverified";
            note = Or(unverifiedReason, "Not checked yet") + " (not part of this run)";
        }
        else if (motionInfeasible)
        {
            kind = CoGroundRuleKind.Infeasible;
            text = Or(RuleText(id), step.ObjectId);
            note = Or(motionReason, "Can't plan the motion");
        }
        else switch (step.Status)
        {
            case StepStatus.Ok:
                kind = CoGroundRuleKind.Obligation;
                text = Or(RuleText(id), step.ObjectId);
                var region = step.To?.RegionId ?? "?";
                note = $"Carry to {region}";
                break;
            case StepStatus.Deferred:
                DeferredReason(step, after, out kind, out id, out text, out note);
                break;
            case StepStatus.Ambiguous:
                kind = CoGroundRuleKind.Undecided;
                id = step.CandidateRuleIds != null && step.CandidateRuleIds.Count > 0 ? string.Join(" / ", step.CandidateRuleIds) : id;
                text = "Destination undecided";
                note = Or(step.Message, "Multiple rules match");
                break;
            case StepStatus.Unmatched:
                kind = CoGroundRuleKind.Undecided;
                text = Or(RuleText(id), "No destination");
                note = Or(step.Message, "Destination zone isn't in the scene");
                break;
            case StepStatus.Infeasible:
                kind = CoGroundRuleKind.Infeasible;
                text = Or(RuleText(id), step.ObjectId);
                note = Or(step.Message, "Can't plan the motion");
                break;
            default:
                kind = CoGroundRuleKind.Undecided;
                text = step.Status;
                note = step.Message ?? "";
                break;
        }

        Vector3 anchor;
        Transform follow = null;
        if (obj != null && TryTop(obj.transform, out var top))
        {
            anchor = top + Vector3.up * bubbleGap;
            follow = obj.transform;
        }
        else
        {
            var size = sizes.TryGetValue(step.ObjectId, out var s) ? s : Vector3.one * 0.1f;
            anchor = (step.From?.Pose?.PositionV ?? Vector3.zero) + Vector3.up * (size.y * 0.5f + bubbleGap);
        }

        var judged = JudgmentNote(step.ObjectId);
        if (!string.IsNullOrEmpty(judged)) note = string.IsNullOrEmpty(note) ? judged : note + "\n" + judged;

        var tag = Spawn(bubblePrefab, $"Rule Bubble {step.Id} ({step.ObjectId})", anchor, bubbleScale);
        tag.Set(kind, id ?? "", text, note, showKindLabel);
        if (follow != null) tag.Follow(follow);
    }

    /// <summary>
    /// その物体について、当てはまらなかった・判断できなかったルール (属性で選ぶものだけ) を行にする。
    /// 種類 (category など) で選ぶ収納先のルールは、当てはまらないのが普通なので出さない。
    /// </summary>
    string JudgmentNote(string objectId)
    {
        if (!showJudgments || objectId == null || !(state["judgments"]?[objectId] is JArray judgments)) return "";
        var lines = new List<string>();
        foreach (var j in judgments)
        {
            var attribute = (string)j["attribute"];
            if (string.IsNullOrEmpty(attribute) || attribute == "category" || attribute == "group" || attribute == "role") continue;
            var matches = j["matches"];
            if (matches != null && matches.Type == JTokenType.Boolean && (bool)matches) continue; // 該当は、判定 (吹き出しの色) に出ている
            if (lines.Count >= Mathf.Max(0, maxJudgmentLines)) { lines.Add("…"); break; }
            lines.Add(CoGroundNormText.Judgment(j));
        }
        return string.Join("\n", lines);
    }

    /// <summary>保留の理由: 違反があれば禁止、未確定だけなら判断できない</summary>
    void DeferredReason(StepDto step, bool after, out CoGroundRuleKind kind, out string id, out string text, out string note)
    {
        VerdictDto violated = null, undetermined = null;
        if (step.Verdicts != null)
            foreach (var v in step.Verdicts)
            {
                if (v.Value == VerdictValue.Violated && violated == null) violated = v;
                if (v.Value == VerdictValue.Undetermined && undetermined == null) undetermined = v;
            }

        if (violated != null)
        {
            kind = CoGroundRuleKind.Prohibition;
            id = violated.RuleId;
            text = Or(RuleText(id), Or(violated.Detail, "Prohibited"));
            note = after ? $"Left in place because it violates {id}" : $"Not carried because it violates {id}";
            return;
        }
        kind = CoGroundRuleKind.Undecided;
        if (undetermined != null)
        {
            id = undetermined.RuleId;
            text = Or(RuleText(id), "Can't decide");
            var keys = new List<string>();
            if (undetermined.Missing != null)
                foreach (var m in undetermined.Missing) keys.Add(CoGroundNormText.Missing(m.Key, m.EntityId));
            note = keys.Count > 0 ? "Missing information: " + string.Join(", ", keys) : Or(step.Message, "Not enough information to decide");
            return;
        }
        id = step.RuleId;
        text = Or(RuleText(id), "Deferred");
        note = Or(step.Message, "Deferred by a household rule");
    }

    // ---- 置き場所の看板 ----

    void BuildSigns(JArray norms)
    {
        var perRegion = new Dictionary<string, int>();
        foreach (var n in norms)
        {
            if ((string)n["requirement"]?["predicate"] != "placed_in") continue;
            var region = (string)n["requirement"]?["args"]?["region"];
            if (string.IsNullOrEmpty(region) || !TryRegionTop(region, out var top)) continue;

            perRegion.TryGetValue(region, out var index);
            perRegion[region] = index + 1;
            // 2 つ目からは左右交互に並べる
            var offset = index == 0 ? 0f : ((index + 1) / 2) * signSpacing * (index % 2 == 1 ? 1f : -1f);
            var id = (string)n["id"];
            var tag = Spawn(signPrefab, $"Rule Sign {id} ({region})", top + Vector3.right * offset * signScale, signScale);
            tag.Set(NormKind((string)n["norm"]), id, Or((string)n["original_text"], region),
                    showConditions ? CoGroundNormText.Conditions(n, state) : "", showKindLabel);
            var obj = CoGroundSceneObject.Find(region);
            if (obj != null) tag.Follow(obj.transform);
        }
    }

    // ---- 床のエリア ----

    void BuildFloors(JArray norms)
    {
        var zones = new Dictionary<string, JToken>();
        if (state["zones"] is JArray zs)
            foreach (var z in zs)
                if ((string)z["id"] is string zid) zones[zid] = z;

        foreach (var n in norms)
        {
            // 対象が領域のルール (入るな・中にいるな) と、条件が領域を読むルール (台所の中ではゆっくり)
            var zoneIds = new List<string>();
            if ((string)n["target"]?["kind"] == "zone" && (string)n["target"]?["id"] is string targetZone) zoneIds.Add(targetZone);
            foreach (var z in CoGroundNormText.ConditionZones(n))
                if (!zoneIds.Contains(z)) zoneIds.Add(z);

            foreach (var zoneId in zoneIds)
            {
                if (!zones.TryGetValue(zoneId, out var zone)) continue;
                var pts = ZonePoints(zone);
                if (pts.Count < 3) continue;

                var id = (string)n["id"];
                var tag = Spawn(floorPrefab, $"Rule Floor {id} ({zoneId})", pts[0], 1f);
                var label = tag.transform.Find("Label");
                if (label != null) label.localScale *= floorLabelScale;
                tag.SetArea(pts);
                tag.Set(NormKind((string)n["norm"]), id, Or((string)n["original_text"], zoneId), ContentAndConditions(n), showKindLabel);
            }
        }
    }

    static List<Vector3> ZonePoints(JToken zone)
    {
        var pts = new List<Vector3>();
        if (zone["polygon"] is JArray poly && poly.Count >= 3)
        {
            foreach (var p in poly) pts.Add(CoGroundServerClient.ToVector3(p));
            return pts;
        }
        if (zone["box"] is JObject box)
        {
            // 直方体の底面の四隅
            var c = CoGroundServerClient.ToVector3(box["center"]);
            var size = CoGroundServerClient.ToVector3(box["size"]);
            var rot = box["rotation"] is JArray q && q.Count == 4 ? CoGroundServerClient.ToQuaternion(q) : Quaternion.identity;
            var h = size * 0.5f;
            foreach (var (x, z) in new[] { (-1f, -1f), (1f, -1f), (1f, 1f), (-1f, 1f) })
                pts.Add(c + rot * new Vector3(h.x * x, -h.y, h.z * z));
        }
        return pts;
    }

    // ---- 部品 ----

    CoGroundRuleTag Spawn(GameObject prefab, string name, Vector3 position, float scale)
    {
        var go = Instantiate(prefab, position, Quaternion.identity, transform);
        go.name = name;
        go.transform.localScale = prefab.transform.localScale * scale;
        spawned.Add(go);
        var tag = go.GetComponent<CoGroundRuleTag>();
        if (style != null) tag.Style = style;
        return tag;
    }

    void Clear()
    {
        foreach (var g in spawned) if (g != null) Destroy(g);
        spawned.Clear();
    }

    static CoGroundRuleKind NormKind(string norm) =>
        norm == "prohibition" ? CoGroundRuleKind.Prohibition :
        norm == "permission" ? CoGroundRuleKind.Permission : CoGroundRuleKind.Obligation;

    static string Or(string a, string b) => string.IsNullOrEmpty(a) ? b : a;

    /// <summary>物体の見た目 (Renderer) の上面の中心。ルール表示自身は除く</summary>
    static bool TryTop(Transform root, out Vector3 top)
    {
        var any = false;
        var b = new Bounds();
        foreach (var r in root.GetComponentsInChildren<Renderer>())
        {
            if (!r.enabled || r.GetComponentInParent<CoGroundRuleTag>() != null) continue;
            if (!any) { b = r.bounds; any = true; }
            else b.Encapsulate(r.bounds);
        }
        top = any ? new Vector3(b.center.x, b.max.y, b.center.z) : root.position;
        return any;
    }

    /// <summary>置き場所の上面。シーンの物体があればその見た目、無ければ scene.regions の box</summary>
    bool TryRegionTop(string region, out Vector3 top)
    {
        var obj = CoGroundSceneObject.Find(region);
        if (obj != null && TryTop(obj.transform, out top)) return true;
        if (state["scene"]?["regions"] is JArray regions)
            foreach (var r in regions)
                if ((string)r["id"] == region && r["box"] is JObject box)
                {
                    var c = CoGroundServerClient.ToVector3(box["center"]);
                    var size = CoGroundServerClient.ToVector3(box["size"]);
                    top = c + Vector3.up * size.y * 0.5f;
                    return true;
                }
        top = default;
        return false;
    }
}
