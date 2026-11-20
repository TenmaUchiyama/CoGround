using System;
using System.Collections.Generic;
using System.Text;
using Newtonsoft.Json.Linq;
using UnityEngine;

/// <summary>
/// 家庭ルールまわりの状態 (state.updated) を、文字で見せる。
///
///   - 家の時計 (clock)
///   - 台車を止めているか、その理由 (execution.robot.held / execution.monitor.active)
///   - 台車がいま避けている領域 (execution.monitor.keepout)
///   - 人の位置が観測できているか (people)
///   - 依頼の行ごとの状態と理由 (task.rows)。行の下に、当てはまらなかった・判断できなかったルールと根拠の属性 (judgments)
///   - ロボット自身についてのルール (止まれ・ゆっくり動け) と、その内容・条件 (norms)
///   - カメラ (VLM) に聞いている属性と、住人が登録する属性 (attributes。ルールが使っている属性から決まる)
///   - 登録の途中のルールと、確かめる内容 (pending_rules)
///   - 最後の登録 (norms.compile) でルールにできなかった部分 (未対応の内容など。CoGroundHomeCommands.RuleCompiled)
///
/// ■ 使い方
///   CoGroundServerClient と同じシーンの GameObject に付ける。Text が空なら、この GameObject の位置に TextMesh を作る。
///   Robot Anchor (台車の Transform) を入れると、止めている間だけ、その上に「停止中」を出す。
///
/// ■ ほかのスクリプトから
///   Held / HoldReason / Keepout / Rows と、HoldChanged (止めた・動かせるようになった) を読める。
///   文字にした結果は StatusText。
/// </summary>
public class CoGroundHomeStatus : MonoBehaviour
{
    /// <summary>依頼の行 (state.task.rows の 1 つ)</summary>
    public class Row
    {
        public string ObjectId, Label, ExecState, Destination, Reason;
    }

    [SerializeField] CoGroundServerClient client;
    [Tooltip("文字を出す先。空なら、この GameObject の位置に作る")]
    [SerializeField] TextMesh text;
    [SerializeField] float characterSize = 0.006f;
    [SerializeField] Color textColor = Color.white;
    [SerializeField] Color heldColor = new Color(1f, 0.35f, 0.3f, 1f);
    [Tooltip("文字をカメラに向ける")]
    [SerializeField] bool faceCamera = true;
    [Tooltip("終わった行 (収納した) も出す")]
    [SerializeField] bool showDoneRows = true;
    [Tooltip("行の下に、当てはまらなかった・判断できなかったルールと、その根拠にした属性を出す")]
    [SerializeField] bool showJudgments = true;
    [Tooltip("ロボット自身についてのルールを出す")]
    [SerializeField] bool showRobotRules = true;
    [Tooltip("カメラ (VLM) に聞いている属性と、住人が登録する属性を出す")]
    [SerializeField] bool showAttributes = true;

    [Header("停止の目印")]
    [Tooltip("台車の Transform。入れると、止めている間だけその上に「停止中」を出す")]
    [SerializeField] Transform robotAnchor;
    [SerializeField] float anchorHeight = 1.3f;

    /// <summary>サーバーが台車を止めている (hold)</summary>
    public bool Held { get; private set; }
    /// <summary>止めている理由 (止めていなければ空)</summary>
    public string HoldReason { get; private set; } = "";
    /// <summary>台車がいま避けている領域の ID</summary>
    public IReadOnlyList<string> Keepout => keepout;
    public IReadOnlyList<Row> Rows => rows;
    public string StatusText { get; private set; } = "";
    /// <summary>(止めているか, 理由)</summary>
    public event Action<bool, string> HoldChanged;

    CoGroundServerClient Client => client != null ? client : CoGroundServerClient.Instance;
    CoGroundServerClient subscribed;
    readonly List<string> keepout = new List<string>();
    readonly List<Row> rows = new List<Row>();
    readonly List<string> notRegistered = new List<string>();
    string notRegisteredText = "";
    TextMesh holdMark;

    void Start()
    {
        if (text == null) text = MakeText("Home Status", transform, TextAnchor.UpperLeft);
        subscribed = Client;
        if (subscribed == null) { Debug.LogWarning("[CoGroundHomeStatus] CoGroundServerClient が見つからない", this); return; }
        subscribed.StateUpdated += OnStateUpdated;
        CoGroundHomeCommands.RuleCompiled += OnRuleCompiled;
        if (subscribed.LatestState != null) OnStateUpdated(subscribed.LatestState);
    }

    /// <summary>ルールにできなかった部分を覚えておく (次の登録まで出す)</summary>
    void OnRuleCompiled(CoGroundHomeCommands source, JToken result)
    {
        notRegistered.Clear();
        notRegistered.AddRange(source.LastUnresolved);
        notRegisteredText = source.LastCompiledText;
        if (subscribed != null && subscribed.LatestState != null) OnStateUpdated(subscribed.LatestState);
    }

    void OnDestroy()
    {
        CoGroundHomeCommands.RuleCompiled -= OnRuleCompiled;
        if (subscribed != null) subscribed.StateUpdated -= OnStateUpdated;
        if (holdMark != null) Destroy(holdMark.gameObject);
    }

    void OnEnable() => SetVisible(true);
    void OnDisable() => SetVisible(false);

    void SetVisible(bool visible)
    {
        if (text != null) text.gameObject.SetActive(visible);
        if (holdMark != null) holdMark.gameObject.SetActive(visible && Held);
    }

    TextMesh MakeText(string objectName, Transform parent, TextAnchor anchor)
    {
        var go = new GameObject(objectName);
        go.transform.SetParent(parent, false);
        var mesh = go.AddComponent<TextMesh>();
        // TextMesh はフォントを指定しないと何も表示されないので、Unity 内蔵フォントを使う
        var font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
        mesh.font = font;
        go.GetComponent<MeshRenderer>().sharedMaterial = font.material;
        mesh.anchor = anchor;
        mesh.alignment = TextAlignment.Left;
        mesh.characterSize = characterSize;
        mesh.fontSize = 48;
        mesh.color = textColor;
        return mesh;
    }

    void OnStateUpdated(JObject state)
    {
        var execution = state["execution"];
        var monitor = execution?["monitor"];
        var robot = execution?["robot"];
        var active = monitor?["active"];
        var hasActive = active != null && active.Type == JTokenType.Object;

        var held = (bool?)robot?["held"] ?? (bool?)monitor?["held"] ?? false;
        var reason = "";
        if (held)
        {
            reason = hasActive ? (string)active["reason"] : null;
            if (string.IsNullOrEmpty(reason)) reason = (string)robot?["hold_reason"] ?? "";
        }

        keepout.Clear();
        if (monitor?["keepout"] is JArray zones)
            foreach (var z in zones) keepout.Add((string)z);

        rows.Clear();
        var task = state["task"];
        var hasTask = task != null && task.Type == JTokenType.Object;
        if (hasTask && task["rows"] is JArray taskRows)
            foreach (var r in taskRows)
                rows.Add(new Row
                {
                    ObjectId = (string)r["object_id"], Label = (string)r["label"], ExecState = (string)r["exec_state"],
                    Destination = (string)r["destination"], Reason = (string)r["reason"],
                });

        var sb = new StringBuilder();
        var clock = state["clock"];
        var now = (string)clock?["now"];
        if (!string.IsNullOrEmpty(now))
        {
            // ISO 8601 (2026-01-01T18:05:00+09:00) の時刻の部分
            var at = now.IndexOf('T');
            var hhmm = at >= 0 && now.Length >= at + 6 ? now.Substring(at + 1, 5) : now;
            sb.Append("House clock ").Append(hhmm);
            if ((bool?)clock["frozen"] == true) sb.Append(" (frozen)");
            else if ((bool?)clock["overridden"] == true) sb.Append(" (set manually)");
            sb.Append('\n');
        }
        if (held) sb.Append("■ HOLD: ").Append(string.IsNullOrEmpty(reason) ? "(no reason)" : reason).Append('\n');
        if (keepout.Count > 0) sb.Append("Avoiding zones: ").Append(string.Join(", ", keepout)).Append('\n');

        var people = state["people"];
        if (people != null && people.Type == JTokenType.Object)
        {
            if ((bool?)people["observed"] == true) sb.Append("People: ").Append((people["people"] as JArray)?.Count ?? 0).Append("\n");
            else sb.Append("People: not observed\n");
        }

        if (hasTask)
        {
            sb.Append((string)task["closed_at"] != null ? "Request (closed): " : "Request: ").Append((string)task["text"]).Append('\n');
            foreach (var r in rows)
            {
                if (!showDoneRows && r.ExecState == "done") continue;
                sb.Append("  ").Append(string.IsNullOrEmpty(r.Label) ? r.ObjectId : $"{r.Label} ({r.ObjectId})")
                  .Append(": ").Append(ExecStateLabel(r.ExecState));
                if (!string.IsNullOrEmpty(r.Destination)) sb.Append(" → ").Append(r.Destination);
                if (!string.IsNullOrEmpty(r.Reason)) sb.Append("\n    ").Append(r.Reason);
                sb.Append('\n');
                if (showJudgments && state["judgments"]?[r.ObjectId] is JArray judgments)
                    foreach (var j in judgments)
                    {
                        // 属性で選ぶルールのうち、当てはまらなかった・判断できなかったもの
                        var attribute = (string)j["attribute"];
                        if (string.IsNullOrEmpty(attribute) || attribute == "category" || attribute == "group" || attribute == "role") continue;
                        if (j["matches"] is JValue m && m.Type == JTokenType.Boolean && (bool)m) continue;
                        sb.Append("    · ").Append(CoGroundNormText.Judgment(j)).Append('\n');
                    }
            }
        }

        if (showRobotRules && state["norms"] is JArray norms)
        {
            var any = false;
            foreach (var n in norms)
            {
                if (!CoGroundNormText.IsAboutRobot(n)) continue;
                if (!any) { sb.Append("Rules about the robot:\n"); any = true; }
                sb.Append("  ").Append((string)n["id"]).Append(": ").Append((string)n["original_text"]).Append('\n');
                var content = CoGroundNormText.Content(n, state);
                var conditions = CoGroundNormText.Conditions(n, state);
                sb.Append("    ").Append(content);
                if (!string.IsNullOrEmpty(conditions)) sb.Append(" · ").Append(conditions);
                sb.Append('\n');
            }
        }

        if (showAttributes && state["attributes"] is JArray attributes && attributes.Count > 0)
        {
            var asked = new List<string>();
            var byResident = new List<string>();
            foreach (var a in attributes)
            {
                var ids = new List<string>();
                if (a["rule_ids"] is JArray ruleIds)
                    foreach (var id in ruleIds) ids.Add((string)id);
                var entry = ids.Count > 0 ? $"{(string)a["name"]} ({string.Join(", ", ids)})" : (string)a["name"];
                ((bool?)a["visual"] == false ? byResident : asked).Add(entry);
            }
            if (asked.Count > 0) sb.Append("Asking the camera about: ").Append(string.Join(", ", asked)).Append('\n');
            if (byResident.Count > 0) sb.Append("Set by a resident (not visible): ").Append(string.Join(", ", byResident)).Append('\n');
        }

        if (state["pending_rules"] is JArray pending && pending.Count > 0)
        {
            sb.Append("Pending rules:\n");
            foreach (var p in pending)
            {
                sb.Append("  ").Append((string)p["rule"]?["id"]).Append(": ").Append((string)p["rule"]?["original_text"]).Append('\n');
                if (p["pending_refs"] is JArray refs)
                    foreach (var x in refs) sb.Append("    Needs region: ").Append((string)x["phrase"]).Append(" (").Append((string)x["ref"]).Append(")\n");
                if (p["unresolved"] is JArray unresolved)
                    foreach (var x in unresolved) sb.Append("    Undetermined: ").Append((string)x == "scope.until" ? "expiry time" : (string)x).Append('\n');
                if (p["notes"] is JArray notes)
                    foreach (var x in notes) sb.Append("    ").Append((string)x).Append('\n');
            }
        }

        if (notRegistered.Count > 0)
        {
            sb.Append("Not registered");
            if (!string.IsNullOrEmpty(notRegisteredText)) sb.Append(" (\"").Append(notRegisteredText).Append("\")");
            sb.Append(":\n");
            foreach (var u in notRegistered) sb.Append("  ").Append(u).Append('\n');
        }

        StatusText = sb.ToString().TrimEnd('\n');
        if (text != null)
        {
            text.text = StatusText;
            text.color = held ? heldColor : textColor;
        }

        var changed = held != Held || reason != HoldReason;
        Held = held;
        HoldReason = reason;
        UpdateHoldMark();
        if (changed) HoldChanged?.Invoke(held, reason);
    }

    /// <summary>依頼の行の状態 (exec_state) を、住人に見せる言葉にする。</summary>
    public static string ExecStateLabel(string state)
    {
        switch (state)
        {
            case "pending": return "To be carried";
            case "deferred": return "Deferred";
            case "in_progress": return "Carrying";
            case "placed_unverified": return "Placed (verifying)";
            case "done": return "Stored";
            case "misplaced": return "In a different place than specified";
            case "unverified": return "Placed but not verified";
            case "failed": return "Could not carry";
            default: return state ?? "?";
        }
    }

    void UpdateHoldMark()
    {
        if (robotAnchor == null)
        {
            if (holdMark != null) holdMark.gameObject.SetActive(false);
            return;
        }
        if (holdMark == null)
        {
            if (!Held) return;
            holdMark = MakeText("Hold Mark", null, TextAnchor.LowerCenter);
            holdMark.alignment = TextAlignment.Center;
            holdMark.color = heldColor;
        }
        holdMark.gameObject.SetActive(Held && isActiveAndEnabled);
        holdMark.text = string.IsNullOrEmpty(HoldReason) ? "HOLD" : "HOLD\n" + HoldReason;
    }

    void LateUpdate()
    {
        var cam = Camera.main;
        if (holdMark != null && holdMark.gameObject.activeSelf && robotAnchor != null)
        {
            holdMark.transform.position = robotAnchor.position + Vector3.up * anchorHeight;
            if (cam != null) Face(holdMark.transform, cam);
        }
        if (faceCamera && text != null && cam != null) Face(text.transform, cam);
    }

    // TextMesh は -Z 側から読める
    static void Face(Transform t, Camera cam)
    {
        var dir = t.position - cam.transform.position;
        if (dir.sqrMagnitude > 1e-6f) t.rotation = Quaternion.LookRotation(dir, Vector3.up);
    }
}
