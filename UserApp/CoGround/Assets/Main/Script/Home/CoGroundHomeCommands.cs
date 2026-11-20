using System;
using System.Collections.Generic;
using System.Globalization;
using System.Threading.Tasks;
using Newtonsoft.Json.Linq;
using UnityEngine;

/// <summary>
/// 家庭ルールの操作を、グラウンディングサーバーに送る入口 (依頼、言葉からのルール登録、訂正、結果の説明)。
/// インスペクタに値を入れ、右上メニュー (⋮) から試す。UI や音声入力からは、同じ名前の public メソッドを呼ぶ。
/// サーバー側は Backend/grounding_server/coground_server/handlers/task.py と handlers/home.py。
///
/// ■ 流れ (例)
///   1. 「ルールを言葉で登録する」  norms.compile   夕方6時以降は、リビングのこのあたりに入るな
///      → 範囲が決まらないルールは登録の途中 (pending_rules) になる。CoGroundZone で範囲を送り、
///        「登録の途中のルールを確定する」(rules.confirm) か、CoGroundZone の Confirm Pending Rules で確定する
///      → ルールにできなかった部分 (「静かに運べ」など、サーバーの語彙に無い内容 = 未対応) は LastUnresolved に入り、
///        RuleCompiled で届く。CoGroundHomeStatus が「Not registered」として見せる (黙って落とさない)
///   2. 「片付けを依頼する」        task.request    机の上のものを全部片づけて
///   3. 「属性を訂正する」          objects.set_attribute   この皿は割れ物ではない
///      「ルールの時刻を訂正する」  rules.update            19 時からにして
///      「例外を足す」              rules.add_exception     私が頼んだときは触ってよい
///   4. 「結果を聞く」              task.report     行ごとの judgments に、当てはまらなかったルールとその根拠の属性も入る
///
/// ■ シーケンス (作業順序) の編集と実行
///   依頼のあと、ロボットの提案した順序を足す・外す・並べ替える (sequence.add / remove / move)。
///   変えると、影響を受ける step 以降をサーバーが検証し直す。検証が済んだ予測 (state の motion.preview) を確認してから
///   「確認した予測で実行する」(exec.start に preview_id を渡す)。UI は CoGroundSequencePanel。
///
/// 訂正の応答 (correction.changes = 訂正の前後で変わった行と項目) は LastCorrection と CorrectionReceived で受け取れる。
/// 経路の判定 (領域への進入の禁止) は動作計画が出すので、訂正のあとは動作計画 (motion.plan) をやり直す。
/// </summary>
public class CoGroundHomeCommands : MonoBehaviour
{
    [SerializeField] CoGroundServerClient client;

    [Header("依頼 (task.request)")]
    [SerializeField] string requestText = "Clear everything off the desk";
    [Tooltip("依頼者の人物 ID。空なら渡さない (「私が頼んだときだけ」のルールは未確定になる)")]
    [SerializeField] string requester = "";
    [Tooltip("この領域にある物すべてを対象にする。空なら、シーンに 1 つだけある机")]
    [SerializeField] string sourceRegion = "";
    [Tooltip("依頼の言葉から対象の物体を LLM に決めさせる (数秒かかる)")]
    [SerializeField] bool interpret = false;

    [Header("ルールを言葉で登録する (norms.compile)")]
    [TextArea] [SerializeField] string ruleText = "夕方6時以降は子供が遊びまわるから、リビングのこのあたりには入るな";
    [Tooltip("登録者の人物 ID (「私が頼んだときだけ」の「私」)。空なら渡さない")]
    [SerializeField] string author = "";

    [Header("登録の途中のルールを確定する (rules.confirm)")]
    [SerializeField] string pendingRuleId = "";
    [Tooltip("範囲に使う領域。空なら Zone Id を使う")]
    [SerializeField] CoGroundZone zone;
    [SerializeField] string zoneId = "";
    [Tooltip("解除時刻 (HH:MM)。空なら渡さない")]
    [SerializeField] string until = "";
    [Tooltip("解除時刻を決めないままにする、と住人が決めた")]
    [SerializeField] bool keepOpen = false;

    [Header("属性を訂正する (objects.set_attribute)")]
    [SerializeField] string objectId = "";
    [SerializeField] string attributeKey = "fragile";
    [Tooltip("true / false、数値、文字列のどれか。空なら訂正を取り消す (届いた値に戻す)")]
    [SerializeField] string attributeValue = "false";

    [Header("ルールの時刻を訂正する (rules.update) / 例外を足す (rules.add_exception)")]
    [SerializeField] string ruleId = "";
    [Tooltip("効き始める時刻 (HH:MM)。空なら変えない。- で消す")]
    [SerializeField] string scopeFrom = "";
    [Tooltip("効かなくなる時刻 (HH:MM)。空なら変えない。- で消す")]
    [SerializeField] string scopeUntil = "";
    [Tooltip("例外: この人物が依頼したときだけ。空なら、だれの依頼でも")]
    [SerializeField] string exceptionRequester = "";
    [Tooltip("例外: この物体だけ (元の禁止が物体についてのとき)。空なら絞らない")]
    [SerializeField] string exceptionObjectId = "";
    [SerializeField] string exceptionText = "You may touch it when I ask";

    [Header("シーケンスの編集 (sequence.*)")]
    [Tooltip("足す・外す・動かす物体の ID")]
    [SerializeField] string sequenceObjectId = "";
    [Tooltip("足すときの置き先の領域。空ならルールが決める")]
    [SerializeField] string sequenceTargetRegion = "";
    [Tooltip("足す・動かす位置 (0 始まり。負なら最後に足す)")]
    [SerializeField] int sequenceIndex = -1;

    [Header("家の時計 (clock.set。デモ・評価用)")]
    [Tooltip("HH:MM か ISO 8601")]
    [SerializeField] string clockTime = "18:05";
    [Tooltip("その時刻で止める")]
    [SerializeField] bool freezeClock = true;

    /// <summary>最後の訂正の応答の correction (before / after / affected_rule_ids / changes)</summary>
    public JToken LastCorrection { get; private set; }
    /// <summary>最後の task.report の message (住人に伝える文)</summary>
    public string LastReportMessage { get; private set; } = "";
    public event Action<JToken> CorrectionReceived;
    /// <summary>最後の norms.compile で、ルールにできなかった部分と理由 (未対応の内容、シーンに無い行き先など)</summary>
    public IReadOnlyList<string> LastUnresolved => lastUnresolved;
    /// <summary>最後の norms.compile に渡した言葉</summary>
    public string LastCompiledText { get; private set; } = "";
    /// <summary>norms.compile の応答 (norms / pending / unresolved)。シーンのどの CoGroundHomeCommands からでも届く</summary>
    public static event Action<CoGroundHomeCommands, JToken> RuleCompiled;

    readonly List<string> lastUnresolved = new List<string>();
    /// <summary>task.report の応答 (summary / message / rows / corrections)</summary>
    public event Action<JToken> ReportReceived;

    CoGroundServerClient Client => client != null ? client : CoGroundServerClient.Instance;

    // ------------------------------------------------------------------ 依頼

    [ContextMenu("片付けを依頼する (task.request)")]
    public void RequestTaskFromInspector() => _ = RequestTask(requestText, requester, sourceRegion, interpret);

    /// <summary>片付けを依頼する。対象の物体はここで決まる (あとで増減しない)。</summary>
    public async Task<JToken> RequestTask(string text, string requesterId = null, string region = null, bool useLlm = false)
    {
        var args = new JObject { ["text"] = text };
        if (!string.IsNullOrWhiteSpace(requesterId)) args["requester"] = requesterId.Trim();
        if (useLlm) args["interpret"] = true;
        else if (!string.IsNullOrWhiteSpace(region)) args["source_region"] = region.Trim();
        var result = await Call("task.request", args);
        if (result != null) Debug.Log($"[CoGroundHomeCommands] 依頼した: {result["counts"]?.ToString(Newtonsoft.Json.Formatting.None)}", this);
        return result;
    }

    [ContextMenu("依頼を閉じる (task.close)")]
    public void CloseTaskFromInspector() => _ = Call("task.close", null);

    [ContextMenu("結果を聞く (task.report)")]
    public void ReportFromInspector() => _ = Report();

    /// <summary>依頼の結果を、住人に伝える形で受け取る (message が全文)。</summary>
    public async Task<JToken> Report()
    {
        var result = await Call("task.report", null);
        if (result == null) return null;
        LastReportMessage = (string)result["message"] ?? "";
        Debug.Log($"[CoGroundHomeCommands] {LastReportMessage}", this);
        // 当てはまらなかった・判断できなかったルールと、その根拠 (VLM の間違いに気づけるように)
        if (result["rows"] is JArray rows)
            foreach (var row in rows)
                if (row["judgments"] is JArray judgments)
                    foreach (var j in judgments)
                        if (!(j["matches"] is JValue m && m.Type == JTokenType.Boolean && (bool)m))
                            Debug.Log($"[CoGroundHomeCommands]   {row["object_id"]}: {CoGroundNormText.Judgment(j)}", this);
        ReportReceived?.Invoke(result);
        return result;
    }

    // ------------------------------------------------------------------ シーケンスの編集と実行

    [ContextMenu("step を足す (sequence.add)")]
    public void AddStepFromInspector() => _ = AddStep(sequenceObjectId, sequenceTargetRegion, sequenceIndex);

    /// <summary>
    /// 物体を運ぶ step を足す。region が空ならルールが置き先を決める。index が負なら最後。
    /// 家庭ルールで触れない物・置き先がルールに合わない物は、step は入るが「残す」になり、理由が付く。
    /// </summary>
    public Task<JToken> AddStep(string id, string region = null, int index = -1)
    {
        var args = new JObject { ["object_id"] = id.Trim() };
        if (!string.IsNullOrWhiteSpace(region)) args["target_region"] = region.Trim();
        if (index >= 0) args["index"] = index;
        return Call("sequence.add", args);
    }

    [ContextMenu("step を外す (sequence.remove)")]
    public void RemoveStepFromInspector() => _ = RemoveStep(sequenceObjectId);

    /// <summary>step を外す (その物体は動かさない)。残りの順序と予測が更新される。</summary>
    public Task<JToken> RemoveStep(string id) => Call("sequence.remove", new JObject { ["object_id"] = id.Trim() });

    [ContextMenu("step を動かす (sequence.move)")]
    public void MoveStepFromInspector() => _ = MoveStep(sequenceObjectId, Mathf.Max(0, sequenceIndex));

    /// <summary>step を index 番目 (0 始まり) へ動かす。</summary>
    public Task<JToken> MoveStep(string id, int index) =>
        Call("sequence.move", new JObject { ["object_id"] = id.Trim(), ["index"] = index });

    [ContextMenu("検証し直す (motion.plan)")]
    public void RecheckFromInspector() => _ = Call("motion.plan", new JObject());

    [ContextMenu("確認した予測で実行する (exec.start)")]
    public void ExecuteFromInspector() => _ = ExecuteConfirmedPreview();

    /// <summary>
    /// いま届いている検証済みの予測 (motion.preview) で実行する。検証が済んでいない・予測が変わった・
    /// 実行の直前の検証で動かす対象が変わった、ならサーバーが断る (更新された After を確認して、もう一度呼ぶ)。
    /// </summary>
    public Task<JToken> ExecuteConfirmedPreview()
    {
        var c = Client;
        var preview = CoGroundFuture.Preview(c != null ? c.LatestState : null);
        if (preview == null)
        {
            Debug.LogWarning("[CoGroundHomeCommands] 検証済みの予測 (motion.preview) がまだ無い", this);
            return Task.FromResult<JToken>(null);
        }
        return Call("exec.start", new JObject { ["preview_id"] = (string)preview["id"] }, 300f);
    }

    // ------------------------------------------------------------------ ルールの登録

    [ContextMenu("ルールを言葉で登録する (norms.compile)")]
    public void CompileRuleFromInspector() => _ = CompileRule(ruleText, author);

    /// <summary>
    /// 住人の言葉を家庭ルールにする (LLM。数秒かかる)。確定したルールはすぐ効く。
    /// 範囲・解除時刻が決まらないルールは result["pending"] に入る (rules.confirm で確定する)。
    /// </summary>
    public async Task<JToken> CompileRule(string text, string authorId = null)
    {
        var args = new JObject { ["text"] = text };
        if (!string.IsNullOrWhiteSpace(authorId)) args["author"] = authorId.Trim();
        var result = await Call("norms.compile", args);
        if (result == null) return null;
        var norms = result["norms"] as JArray;
        var pending = result["pending"] as JArray;
        LastCompiledText = text;
        lastUnresolved.Clear();
        if (result["unresolved"] is JArray unresolved)
            foreach (var u in unresolved) lastUnresolved.Add((string)u);
        Debug.Log($"[CoGroundHomeCommands] norms.compile: 確定 {norms?.Count ?? 0} 件、登録の途中 {pending?.Count ?? 0} 件、" +
                  $"ルールにできなかった部分 {lastUnresolved.Count} 件", this);
        foreach (var u in lastUnresolved) Debug.LogWarning($"[CoGroundHomeCommands]   ルールにしていない: {u}", this);
        RuleCompiled?.Invoke(this, result);
        if (pending != null)
            foreach (var p in pending)
                Debug.Log($"[CoGroundHomeCommands]   {p["rule"]?["id"]}: 範囲 {p["pending_refs"]?.ToString(Newtonsoft.Json.Formatting.None)} " +
                          $"未解決 {p["unresolved"]?.ToString(Newtonsoft.Json.Formatting.None)}", this);
        return result;
    }

    [ContextMenu("登録の途中のルールを確定する (rules.confirm)")]
    public void ConfirmRuleFromInspector() =>
        _ = ConfirmRule(pendingRuleId, zone != null ? zone.Id : zoneId, until, keepOpen);

    /// <summary>
    /// 登録の途中のルールを確定する。ruleId が空なら、登録の途中のルールが 1 つだけのときにそれを使う。
    /// 領域は、そのルールの範囲の参照すべてに当てる。足りないものがあればサーバーが断る (勝手に補わない)。
    /// </summary>
    public async Task<JToken> ConfirmRule(string id, string zone, string untilTime = null, bool open = false)
    {
        var c = Client;
        var pending = c != null ? c.LatestState?["pending_rules"] as JArray : null;
        JToken entry = null;
        if (pending != null)
            foreach (var p in pending)
                if (string.IsNullOrWhiteSpace(id) ? pending.Count == 1 : (string)p["rule"]?["id"] == id.Trim()) entry = p;
        if (entry == null)
        {
            Debug.LogWarning($"[CoGroundHomeCommands] 登録の途中のルール {id} が無い (state.pending_rules を確かめる)", this);
            return null;
        }

        var refs = new JObject();
        if (entry["pending_refs"] is JArray pendingRefs && pendingRefs.Count > 0)
        {
            if (string.IsNullOrWhiteSpace(zone))
            {
                Debug.LogWarning("[CoGroundHomeCommands] このルールは範囲が要る (Zone か Zone Id を入れる)", this);
                return null;
            }
            foreach (var r in pendingRefs) refs[(string)r["ref"]] = zone.Trim();
        }
        var args = new JObject { ["rule_id"] = (string)entry["rule"]["id"], ["refs"] = refs };
        if (!string.IsNullOrWhiteSpace(untilTime)) args["until"] = untilTime.Trim();
        if (open) args["keep_open"] = true;
        var result = await Call("rules.confirm", args);
        if (result != null) Debug.Log($"[CoGroundHomeCommands] 確定した: {result["rule"]?["id"]} {result["rule"]?["original_text"]}", this);
        return result;
    }

    [ContextMenu("登録の途中のルールを捨てる (rules.discard_pending)")]
    public void DiscardPendingFromInspector() => _ = Call("rules.discard_pending", new JObject { ["rule_id"] = pendingRuleId.Trim() });

    // ------------------------------------------------------------------ 訂正

    [ContextMenu("属性を訂正する (objects.set_attribute)")]
    public void SetAttributeFromInspector() =>
        _ = SetAttribute(objectId, attributeKey, string.IsNullOrWhiteSpace(attributeValue) ? null : ParseValue(attributeValue));

    /// <summary>物体の属性を訂正する (例: この皿は割れ物ではない)。value が null なら訂正を取り消す。</summary>
    public Task<JToken> SetAttribute(string id, string key, JToken value) =>
        Correct("objects.set_attribute", new JObject { ["object_id"] = id.Trim(), ["key"] = key.Trim(), ["value"] = value ?? JValue.CreateNull() });

    [ContextMenu("ルールの時刻を訂正する (rules.update)")]
    public void UpdateRuleFromInspector()
    {
        var args = new JObject { ["rule_id"] = ruleId.Trim() };
        if (!string.IsNullOrWhiteSpace(scopeFrom)) args["from"] = TimeOrNull(scopeFrom);
        if (!string.IsNullOrWhiteSpace(scopeUntil)) args["until"] = TimeOrNull(scopeUntil);
        if (args.Count == 1) { Debug.LogWarning("[CoGroundHomeCommands] 変える項目 (Scope From / Scope Until) が無い", this); return; }
        _ = Correct("rules.update", args);
    }

    /// <summary>家庭ルールの効く時間を訂正する (例: 19 時からにして)。null の項目は変えない。"-" はその項目を消す。</summary>
    public Task<JToken> UpdateRule(string id, string from = null, string untilTime = null)
    {
        var args = new JObject { ["rule_id"] = id.Trim() };
        if (!string.IsNullOrWhiteSpace(from)) args["from"] = TimeOrNull(from);
        if (!string.IsNullOrWhiteSpace(untilTime)) args["until"] = TimeOrNull(untilTime);
        return Correct("rules.update", args);
    }

    [ContextMenu("例外を足す (rules.add_exception)")]
    public void AddExceptionFromInspector() => _ = AddException(ruleId, exceptionRequester, exceptionObjectId, exceptionText);

    /// <summary>元の禁止に例外 (許可) を足す (例: 私が頼んだときは触ってよい)。</summary>
    public Task<JToken> AddException(string prohibitionId, string requesterId = null, string onlyObjectId = null, string originalText = null)
    {
        var args = new JObject { ["exception_of"] = prohibitionId.Trim() };
        if (!string.IsNullOrWhiteSpace(requesterId)) { args["requester"] = requesterId.Trim(); args["author"] = requesterId.Trim(); }
        if (!string.IsNullOrWhiteSpace(onlyObjectId)) args["object_id"] = onlyObjectId.Trim();
        if (!string.IsNullOrWhiteSpace(originalText)) args["original_text"] = originalText;
        return Correct("rules.add_exception", args);
    }

    /// <summary>領域の範囲を訂正する (zones.update)。CoGroundZone のいまの角を使う。変わった行と項目が返る。</summary>
    public Task<JToken> UpdateZone(CoGroundZone target)
    {
        var points = new List<Vector3>();
        target.CollectPoints(points);
        var polygon = new JArray();
        foreach (var p in points) polygon.Add(CoGroundServerClient.ToJson(p));
        return Correct("zones.update", new JObject { ["id"] = target.Id, ["polygon"] = polygon });
    }

    [ContextMenu("領域の範囲を訂正する (zones.update)")]
    public void UpdateZoneFromInspector()
    {
        if (zone == null) { Debug.LogWarning("[CoGroundHomeCommands] Zone を入れる", this); return; }
        _ = UpdateZone(zone);
    }

    // ------------------------------------------------------------------ 時計

    [ContextMenu("家の時計を合わせる (clock.set)")]
    public void SetClockFromInspector() => _ = Call("clock.set", new JObject { ["time"] = clockTime.Trim(), ["freeze"] = freezeClock });

    [ContextMenu("家の時計を実時刻に戻す (clock.reset)")]
    public void ResetClockFromInspector() => _ = Call("clock.reset", null);

    // ------------------------------------------------------------------ 共通

    async Task<JToken> Correct(string method, JObject args)
    {
        var result = await Call(method, args);
        if (result == null) return null;
        LastCorrection = result["correction"];
        var changes = LastCorrection?["changes"] as JArray;
        Debug.Log($"[CoGroundHomeCommands] {method}: 変わった行 {changes?.Count ?? 0} 件 {changes?.ToString(Newtonsoft.Json.Formatting.None)}", this);
        CorrectionReceived?.Invoke(LastCorrection);
        return result;
    }

    /// <summary>要求を送る。失敗したら警告を出して null を返す。</summary>
    async Task<JToken> Call(string method, JObject args, float timeoutSeconds = 0f)
    {
        var c = Client;
        if (c == null) { Debug.LogWarning("[CoGroundHomeCommands] CoGroundServerClient が見つからない", this); return null; }
        try
        {
            return await c.RequestAsync(method, args, onStream: d => Debug.Log($"[CoGroundHomeCommands] {method}: {d?.ToString(Newtonsoft.Json.Formatting.None)}", this),
                                        timeout: timeoutSeconds > 0f ? System.TimeSpan.FromSeconds(timeoutSeconds) : (System.TimeSpan?)null);
        }
        catch (CoGroundRpcException e)
        {
            Debug.LogWarning($"[CoGroundHomeCommands] {method} failed: {e.Message} {e.Details}", this);
            return null;
        }
    }

    static JToken TimeOrNull(string s) => s.Trim() == "-" ? JValue.CreateNull() : new JValue(s.Trim());

    /// <summary>true / false、数値、それ以外は文字列。</summary>
    static JToken ParseValue(string s)
    {
        s = s.Trim();
        if (bool.TryParse(s, out var b)) return new JValue(b);
        if (double.TryParse(s, NumberStyles.Float, CultureInfo.InvariantCulture, out var d)) return new JValue(d);
        return new JValue(s);
    }
}
