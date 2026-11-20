using System;
using System.Collections.Generic;
using Newtonsoft.Json.Linq;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.UI;

/// <summary>
/// 作業順序 (シーケンス) を確認・編集し、時点ごとの予測を切り替え、実行するパネル (World Space Canvas)。
/// UI は Awake で自分で組み立てる (Prefab は要らない)。
///
/// ■ 参加者の流れ
///   1. 依頼する (音声の SpeechTaskRequester、または CoGroundHomeCommands の task.request)
///   2. ロボットの提案した順序が並ぶ: 「1. mug → shelf_upper」。検証中の行は「Checking…」
///   3. 行の Up / Down / Del で並べ替え・削除、下の「Add step」で追加 (対象・置き先・挿入位置を選ぶ)。
///      変えると、最初に影響を受ける step 以降をサーバーが検証し直す (sequence.*)
///   4. 上の「Before / After 1 / After 2 / … / Final」で、同じ視点のまま各時点の予測を見る (CoGroundAfterView.SetViewStep)
///   5. 「Execute this plan」で実行 (exec.start に、いま見ている予測の版 preview_id を渡す)。
///      検証が終わっていない・古い予測からは始められない。実行の直前にサーバーが検証し直し、
///      動かす対象が変わったら、更新した予測を出して止まる (もう一度確認して押す)
///   6. 結果は行に出る (done / failed と理由)。運び終わった物は Results に残る
///
/// ■ 行の状態 (サーバーの motion.preview。CoGroundFuture.StepState)
///   Will move        この順番で、把持・移動・配置まで実行できると検証できた
///   Stays (rule)     家庭ルールにより残す (理由つき)
///   Stays            動作が成立せず残す (経路が無い・置ける空きが無い・手前の物がじゃま など)
///   Checking…        確認中
///   Unverified       未確認 (今回の実行の対象から外れる。Re-check で検証し直す)
///
/// ■ 使い方
///   メニュー CoGround > シーケンス パネルを置く。または空の GameObject にこのコンポーネントを付ける。
///   CoGroundServerClient と CoGroundAfterView が同じシーンに要る (AfterView が無ければ一覧と編集だけ動く)。
///   VR で押すには、Canvas に ISDK の Ray / Poke を付ける (Before・After パネルと同じ)。エディタではマウスで押せる。
/// </summary>
public class CoGroundSequencePanel : MonoBehaviour
{
    [SerializeField] CoGroundServerClient client;
    [SerializeField] CoGroundAfterView afterView;

    [Header("大きさ")]
    [Tooltip("Canvas の 1 px が何 m か")]
    [SerializeField] float metersPerPixel = 0.0005f;
    [SerializeField] Font font;

    [Header("実行")]
    [Tooltip("実行の直前に、サーバーに検証し直させる (プレビューのあとで環境が変わっていたら、古い経路で動き出さない)")]
    [SerializeField] bool revalidateBeforeExecute = true;
    [Tooltip("実行 (直前の検証を含む) と編集の応答を待つ秒数")]
    [SerializeField] float requestTimeoutSeconds = 300f;

    [Header("色")]
    [SerializeField] Color panelColor = new Color(0.09f, 0.10f, 0.12f, 0.94f);
    [SerializeField] Color rowColor = new Color(0.14f, 0.15f, 0.18f, 1f);
    [SerializeField] Color buttonColor = new Color(0.22f, 0.24f, 0.28f, 1f);
    [SerializeField] Color activeColor = new Color(0.20f, 0.52f, 0.98f, 1f);
    [SerializeField] Color executeColor = new Color(0.15f, 0.62f, 0.38f, 1f);
    [SerializeField] Color disabledColor = new Color(0.17f, 0.18f, 0.20f, 1f);
    [SerializeField] Color textColor = new Color(0.92f, 0.94f, 0.97f, 1f);
    [SerializeField] Color mutedColor = new Color(0.66f, 0.70f, 0.76f, 1f);
    [SerializeField] Color moveColor = new Color(0.35f, 0.9f, 0.55f, 1f);
    [SerializeField] Color ruleColor = new Color(0.72f, 0.68f, 1f, 1f);
    [SerializeField] Color infeasibleColor = new Color(1f, 0.45f, 0.4f, 1f);
    [SerializeField] Color checkingColor = new Color(1f, 0.82f, 0.3f, 1f);

    const float Width = 760, Pad = 16, RowHeight = 62, ButtonHeight = 48;

    CoGroundServerClient Client => client != null ? client : CoGroundServerClient.Instance;
    CoGroundServerClient subscribed;
    JObject state;
    string drawnKey;
    bool busy;
    string message = "";

    RectTransform content;
    readonly List<GameObject> built = new List<GameObject>();

    // 追加する step の選択 (対象・置き先・挿入位置)
    int addObject, addRegion, addIndex = int.MaxValue;

    // ------------------------------------------------------------------ 組み立て

    void Awake()
    {
        if (font == null) font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
        var canvas = GetComponent<Canvas>();
        if (canvas == null)
        {
            canvas = gameObject.AddComponent<Canvas>();
            canvas.renderMode = RenderMode.WorldSpace;
            gameObject.AddComponent<CanvasScaler>().dynamicPixelsPerUnit = 3;
            gameObject.AddComponent<GraphicRaycaster>();
            var rect = (RectTransform)transform;
            rect.sizeDelta = new Vector2(Width, 600);
            rect.localScale = Vector3.one * metersPerPixel;
        }
        var bg = new GameObject("Background", typeof(RectTransform), typeof(Image));
        bg.transform.SetParent(transform, false);
        bg.GetComponent<Image>().color = panelColor;
        Stretch((RectTransform)bg.transform);

        var go = new GameObject("Content", typeof(RectTransform));
        go.transform.SetParent(transform, false);
        content = (RectTransform)go.transform;
        Stretch(content);

        // マウスで押せるように (VR では ISDK の Ray / Poke を Canvas に付ける)
        if (FindAnyObjectByType<EventSystem>() == null)
            new GameObject("EventSystem", typeof(EventSystem), typeof(StandaloneInputModule));
    }

    void Start()
    {
        if (afterView == null) afterView = FindAnyObjectByType<CoGroundAfterView>();
        if (afterView != null) afterView.ViewChanged += Redraw;
        var canvas = GetComponent<Canvas>();
        if (canvas != null && canvas.worldCamera == null) canvas.worldCamera = Camera.main; // マウスで押すのに要る
        subscribed = Client;
        if (subscribed == null) { Debug.LogWarning("[CoGroundSequencePanel] CoGroundServerClient が見つからない", this); Redraw(); return; }
        subscribed.StateUpdated += OnStateUpdated;
        if (subscribed.LatestState != null) OnStateUpdated(subscribed.LatestState);
        else Redraw();
    }

    void OnDestroy()
    {
        if (subscribed != null) subscribed.StateUpdated -= OnStateUpdated;
        if (afterView != null) afterView.ViewChanged -= Redraw;
    }

    void OnStateUpdated(JObject s)
    {
        state = s;
        var key = s["motion"]?["preview"]?.ToString(Newtonsoft.Json.Formatting.None) + "|" + s["motion"]?["progress"]
                  + "|" + s["execution"]?["mode"] + "|" + s["execution"]?["reason"]
                  + "|" + s["execution"]?["steps"]?.ToString(Newtonsoft.Json.Formatting.None)
                  + "|" + s["execution"]?["current"]?.ToString(Newtonsoft.Json.Formatting.None)
                  + "|" + TaskKey(s) + "|" + CoGroundFuture.HasActiveTask(s);
        if (key == drawnKey) return;
        drawnKey = key;
        Redraw();
    }

    static string TaskKey(JObject s)
    {
        var text = "";
        if (s["task"]?["rows"] is JArray rows)
            foreach (var r in rows) text += r["object_id"] + ":" + r["exec_state"] + ":" + r["reason"] + ";";
        return text;
    }

    // ------------------------------------------------------------------ 描画

    float y;

    void Redraw()
    {
        if (content == null) return;
        foreach (var g in built) if (g != null) Destroy(g);
        built.Clear();
        y = Pad;

        var preview = CoGroundFuture.Preview(state);
        var steps = preview?["steps"] as JArray ?? new JArray();
        var hasTask = CoGroundFuture.HasActiveTask(state);
        var execution = state?["execution"] as JObject;
        var running = (string)execution?["mode"] == "running";
        var status = (string)preview?["status"] ?? "none";

        AddLabel("Task sequence", 30, textColor, 40, FontStyle.Bold);
        AddLabel(StatusLine(hasTask, status, execution, preview), 22, StatusColor(status, running), 0);
        var notice = (string)preview?["notice"];
        if (!string.IsNullOrEmpty(notice)) AddLabel(notice, 22, checkingColor, 0);
        if (!string.IsNullOrEmpty(message)) AddLabel(message, 22, infeasibleColor, 0);

        if (!hasTask)
        {
            AddLabel("Ask the robot first, e.g. \"Clear the desk\".", 22, mutedColor, 0);
            Finish();
            return;
        }

        // ---- 見せる時点 ----
        AddLabel("Show", 20, mutedColor, 26);
        var viewing = afterView == null || afterView.Mode == CoGroundAfterView.ViewMode.Before ? -1 : afterView.ViewStep;
        var times = new List<(string, int)> { ("Before", -1) };
        for (int i = 0; i < steps.Count; i++) times.Add(($"After {i + 1}", i));
        times.Add(("Final", int.MaxValue));
        var perRow = Mathf.Min(times.Count, 6);
        var w = (Width - Pad * 2 - (perRow - 1) * 8) / perRow;
        for (int i = 0; i < times.Count; i++)
        {
            var (text, index) = times[i];
            var active = viewing == index;
            var col = i % perRow;
            if (col == 0 && i > 0) y += ButtonHeight + 8;
            AddButton(text, Pad + col * (w + 8), y, w, ButtonHeight, active ? activeColor : buttonColor, true, () => ShowTime(index), 20);
        }
        y += ButtonHeight + 14;

        // ---- step の行 ----
        for (int i = 0; i < steps.Count; i++) StepRow(steps, i, execution, running);
        if (steps.Count == 0) AddLabel("No steps. Add one below.", 22, mutedColor, 0);

        // ---- 順序変更の提案 ----
        if (preview?["suggestion"] is JObject suggestion && !running)
        {
            y += 6;
            var top = y;
            AddLabel("Suggestion: " + (string)suggestion["message"], 21, checkingColor, 0, FontStyle.Normal, Width - Pad * 2 - 150);
            var order = suggestion["order"] as JArray;
            // 採用するかは参加者が決める。採用すると、その順序で検証し直してから After が変わる
            AddButton("Apply", Width - Pad - 140, top, 140, ButtonHeight, activeColor, !busy && order != null,
                   () => Call("sequence.reorder", new JObject { ["object_ids"] = order }), 22);
            y = Mathf.Max(y, top + ButtonHeight + 4);
        }

        // ---- 追加 ----
        if (!running) AddRow(steps);

        // ---- 結果 (運び終わった物・実行で失敗した物) ----
        var results = Results();
        if (results != "") { y += 6; AddLabel("Results", 20, mutedColor, 26); AddLabel(results, 21, textColor, 0); }

        // ---- 検証し直す / 実行 ----
        y += 10;
        var half = (Width - Pad * 2 - 12) / 2;
        var checking = status == CoGroundFuture.StepState.Checking;
        AddButton(checking ? "Checking…" : "Re-check", Pad, y, half, 60, buttonColor, !busy && !running && !checking && steps.Count > 0,
               () => Call("motion.plan", new JObject()), 24);
        var executable = (bool?)preview?["executable"] == true;
        if (running)
            AddButton("Stop", Pad + half + 12, y, half, 60, infeasibleColor, !busy, () => Call("exec.stop", new JObject()), 24);
        else
            AddButton("Execute this plan", Pad + half + 12, y, half, 60, executable ? executeColor : disabledColor, !busy && executable,
                   () => Execute((string)preview["id"]), 24);
        y += 60;
        Finish();
    }

    void Finish()
    {
        y += Pad;
        ((RectTransform)transform).sizeDelta = new Vector2(Width, y);
    }

    string StatusLine(bool hasTask, string status, JObject execution, JObject preview)
    {
        if (subscribed == null || !subscribed.IsConnected) return "Not connected to the server";
        if (!hasTask) return "No request yet";
        var mode = (string)execution?["mode"];
        if (mode == "running")
        {
            var current = execution["current"] as JObject;
            return current != null ? $"Executing: {current["skill"]} {current["object_id"]}" : "Executing…";
        }
        if (mode == "paused") return "Stopped: " + (string)execution["reason"];
        switch (status)
        {
            case "checking":
                var progress = (string)state?["motion"]?["progress"];
                return "Checking if the robot can do it…" + (string.IsNullOrEmpty(progress) ? "" : " " + progress);
            case "ready":
                return (bool?)preview?["executable"] == true
                    ? "Checked. Compare Before / After, then execute."
                    : "Checked. Nothing can be moved in this plan.";
            case "unverified": return "Some steps aren't checked. Press Re-check.";
            default: return "No steps";
        }
    }

    Color StatusColor(string status, bool running) =>
        running ? activeColor : status == "ready" ? moveColor : status == "checking" ? checkingColor : mutedColor;

    void StepRow(JArray steps, int i, JObject execution, bool running)
    {
        var step = (JObject)steps[i];
        var objectId = (string)step["object_id"];
        var stepState = (string)step["state"];
        var reason = (string)step["reason"];
        var to = (string)step["to_region"];

        var row = AddBox(Pad, y, Width - Pad * 2, RowHeight, rowColor);
        var label = (string)step["label"];
        var name = string.IsNullOrEmpty(label) || label == objectId ? objectId : $"{objectId} ({label})";
        AddText(row, $"{i + 1}. {name}  →  {to ?? "?"}", 23, textColor, 10, 2, Width - Pad * 2 - 190, 30, TextAnchor.MiddleLeft, FontStyle.Bold);

        string line;
        Color color;
        // 実行の状態があれば、そちらを先に見せる (done / failed と理由)
        var exec = execution?["steps"]?[(string)step["step_id"]] as JObject;
        var execStatus = (string)exec?["status"];
        if (execStatus != null && execStatus != "pending" && execStatus != "blocked")
        {
            var detail = (string)exec["detail"];
            line = execStatus + (string.IsNullOrEmpty(detail) ? "" : ": " + detail);
            color = execStatus == "done" ? moveColor : execStatus == "failed" || execStatus == "misplaced" ? infeasibleColor : checkingColor;
        }
        else switch (stepState)
        {
            case CoGroundFuture.StepState.Move: line = "Will move"; color = moveColor; break;
            case CoGroundFuture.StepState.StayRule: line = "Stays (rule): " + reason; color = ruleColor; break;
            case CoGroundFuture.StepState.StayInfeasible: line = "Stays: " + reason; color = infeasibleColor; break;
            case CoGroundFuture.StepState.Checking: line = "Checking…"; color = checkingColor; break;
            default: line = "Unverified: " + reason; color = mutedColor; break;
        }
        AddText(row, line, 19, color, 10, 31, Width - Pad * 2 - 190, 28, TextAnchor.UpperLeft, FontStyle.Normal);

        var x = Width - Pad * 2 - 174;
        var enabled = !busy && !running;
        SmallButton(row, "Up", x, enabled && i > 0, () => Call("sequence.move", new JObject { ["object_id"] = objectId, ["index"] = i - 1 }));
        SmallButton(row, "Down", x + 58, enabled && i < steps.Count - 1, () => Call("sequence.move", new JObject { ["object_id"] = objectId, ["index"] = i + 1 }));
        SmallButton(row, "Del", x + 116, enabled, () => Call("sequence.remove", new JObject { ["object_id"] = objectId }));
        y += RowHeight + 6;
    }

    void AddRow(JArray steps)
    {
        // 対象: シーンの運べる物のうち、まだシーケンスに無いもの
        var inSequence = new HashSet<string>();
        foreach (var s in steps) inSequence.Add((string)s["object_id"]);
        var objects = new List<string>();
        var regions = new List<string> { null }; // null = ルールが決める
        if (state?["scene"]?["objects"] is JArray sceneObjects)
            foreach (var o in sceneObjects)
                if ((string)o["role"] == "item" && !inSequence.Contains((string)o["id"])) objects.Add((string)o["id"]);
        if (state?["scene"]?["regions"] is JArray sceneRegions)
            foreach (var r in sceneRegions)
                if (r["box"] != null && r["box"].Type != JTokenType.Null) regions.Add((string)r["id"]);

        y += 6;
        AddLabel("Add step  (carry an object to a place)", 20, mutedColor, 26);
        if (objects.Count == 0) { AddLabel("Every object is already in the sequence.", 21, mutedColor, 0); return; }
        addObject = Mathf.Clamp(addObject, 0, objects.Count - 1);
        addRegion = Mathf.Clamp(addRegion, 0, regions.Count - 1);
        var at = Mathf.Clamp(addIndex, 0, steps.Count);

        var w = (Width - Pad * 2 - 16) / 3;
        AddCycle("Object", objects[addObject], Pad, w, () => { addObject = (addObject + 1) % objects.Count; Redraw(); });
        AddCycle("To", regions[addRegion] ?? "(by rule)", Pad + w + 8, w, () => { addRegion = (addRegion + 1) % regions.Count; Redraw(); });
        AddCycle("Position", at >= steps.Count ? "last" : $"before {at + 1}", Pad + (w + 8) * 2, w,
              () => { addIndex = at >= steps.Count ? 0 : at + 1; Redraw(); });
        y += ButtonHeight + 30;

        var objectId = objects[addObject];
        var region = regions[addRegion];
        AddButton("Add step", Pad, y, Width - Pad * 2, ButtonHeight, activeColor, !busy, () =>
        {
            var args = new JObject { ["object_id"] = objectId, ["index"] = at };
            if (region != null) args["target_region"] = region;
            Call("sequence.add", args);
        }, 22);
        y += ButtonHeight + 6;
    }

    /// <summary>運び終わった物と、実行で失敗した物 (Plan の行から消えたあとも見えるように)</summary>
    string Results()
    {
        var text = "";
        if (!(state?["task"]?["rows"] is JArray rows)) return text;
        foreach (var r in rows)
        {
            var s = (string)r["exec_state"];
            var id = (string)r["object_id"];
            var reason = (string)r["reason"];
            string line = null;
            switch (s)
            {
                case "done": line = $"{id}: moved to {r["destination"]}"; break;
                case "misplaced": line = $"{id}: placed, but not where predicted ({reason})"; break;
                case "unverified": line = $"{id}: placed, but couldn't confirm where"; break;
                case "failed": line = $"{id}: stopped ({reason})"; break;
                case "in_progress": case "placed_unverified": line = $"{id}: in progress"; break;
            }
            if (line != null) text += (text == "" ? "" : "\n") + line;
        }
        return text;
    }

    // ------------------------------------------------------------------ 操作

    void ShowTime(int index)
    {
        if (afterView == null) return;
        if (index < 0) afterView.SetMode(CoGroundAfterView.ViewMode.Before);
        else afterView.SetViewStep(index);
    }

    /// <summary>いま見ている予測の版で実行する。版が古い・検証が済んでいない・実行前の検証で変わった、ならサーバーが断る</summary>
    public void Execute(string previewId)
    {
        var args = new JObject { ["preview_id"] = previewId, ["revalidate"] = revalidateBeforeExecute };
        Call("exec.start", args, "Re-checking before execution…");
    }

    async void Call(string method, JObject args, string working = null)
    {
        var c = Client;
        if (c == null || busy) return;
        busy = true;
        message = working ?? "";
        Redraw();
        try
        {
            await c.RequestAsync(method, args, timeout: TimeSpan.FromSeconds(requestTimeoutSeconds));
            message = "";
        }
        catch (CoGroundRpcException e)
        {
            message = Clean(e.Message);
            Debug.LogWarning($"[CoGroundSequencePanel] {method}: {e.Message}", this);
        }
        catch (Exception e)
        {
            message = e.Message;
            Debug.LogWarning($"[CoGroundSequencePanel] {method}: {e}", this);
        }
        if (this == null) return;
        busy = false;
        Redraw();
    }

    /// <summary>"[invalid_state] ..." の頭のコードを落とす</summary>
    static string Clean(string text)
    {
        var end = text.StartsWith("[") ? text.IndexOf("] ", StringComparison.Ordinal) : -1;
        return end >= 0 ? text.Substring(end + 2) : text;
    }

    // ------------------------------------------------------------------ UI の部品

    void AddLabel(string text, int size, Color color, float height, FontStyle style = FontStyle.Normal, float width = 0)
    {
        if (width <= 0) width = Width - Pad * 2;
        var t = MakeText(content, text, size, color, TextAnchor.UpperLeft, style);
        var h = height > 0 ? height : Mathf.Max(size + 8, MeasureHeight(t, width) + 6);
        Place(t.rectTransform, Pad, y, width, h);
        built.Add(t.gameObject);
        y += h;
    }

    float MeasureHeight(Text t, float width)
    {
        var settings = t.GetGenerationSettings(new Vector2(width, 0));
        return t.cachedTextGeneratorForLayout.GetPreferredHeight(t.text, settings) / t.pixelsPerUnit;
    }

    RectTransform AddBox(float x, float top, float width, float height, Color color)
    {
        var go = new GameObject("Row", typeof(RectTransform), typeof(Image));
        go.transform.SetParent(content, false);
        go.GetComponent<Image>().color = color;
        var rect = (RectTransform)go.transform;
        Place(rect, x, top, width, height);
        built.Add(go);
        return rect;
    }

    void AddText(RectTransform parent, string text, int size, Color color, float x, float top, float width, float height, TextAnchor anchor, FontStyle style)
    {
        var t = MakeText(parent, text, size, color, anchor, style);
        t.horizontalOverflow = HorizontalWrapMode.Wrap;
        t.verticalOverflow = VerticalWrapMode.Truncate;
        Place(t.rectTransform, x, top, width, height);
    }

    void SmallButton(RectTransform parent, string text, float x, bool enabled, Action onClick) =>
        MakeButton(parent, text, x, (RowHeight - 46) / 2, 52, 46, buttonColor, enabled, onClick, 17);

    void AddButton(string text, float x, float top, float width, float height, Color color, bool enabled, Action onClick, int size) =>
        built.Add(MakeButton(content, text, x, top, width, height, color, enabled, onClick, size));

    void AddCycle(string caption, string value, float x, float width, Action onClick)
    {
        var t = MakeText(content, caption, 18, mutedColor, TextAnchor.LowerLeft, FontStyle.Normal);
        Place(t.rectTransform, x, y, width, 24);
        built.Add(t.gameObject);
        built.Add(MakeButton(content, value + "  >", x, y + 24, width, ButtonHeight, buttonColor, !busy, onClick, 20));
    }

    GameObject MakeButton(RectTransform parent, string text, float x, float top, float width, float height, Color color, bool enabled, Action onClick, int size)
    {
        var go = new GameObject("Button " + text, typeof(RectTransform), typeof(Image));
        go.transform.SetParent(parent, false);
        var image = go.GetComponent<Image>();
        image.color = enabled ? color : disabledColor;
        Place((RectTransform)go.transform, x, top, width, height);
        var button = go.AddComponent<Button>();
        button.targetGraphic = image;
        button.interactable = enabled;
        if (onClick != null) button.onClick.AddListener(() => onClick());
        var t = MakeText((RectTransform)go.transform, text, size, enabled ? textColor : mutedColor, TextAnchor.MiddleCenter, FontStyle.Bold);
        t.horizontalOverflow = HorizontalWrapMode.Wrap;
        t.verticalOverflow = VerticalWrapMode.Truncate;
        Stretch(t.rectTransform);
        return go;
    }

    Text MakeText(RectTransform parent, string text, int size, Color color, TextAnchor anchor, FontStyle style)
    {
        var go = new GameObject("Text", typeof(RectTransform), typeof(Text));
        go.transform.SetParent(parent, false);
        var t = go.GetComponent<Text>();
        t.font = font;
        t.text = text ?? "";
        t.fontSize = size;
        t.fontStyle = style;
        t.color = color;
        t.alignment = anchor;
        t.horizontalOverflow = HorizontalWrapMode.Wrap;
        t.verticalOverflow = VerticalWrapMode.Overflow;
        t.raycastTarget = false;
        return t;
    }

    /// <summary>親の左上から (x, top) の位置に、width x height で置く</summary>
    static void Place(RectTransform rect, float x, float top, float width, float height)
    {
        rect.anchorMin = rect.anchorMax = new Vector2(0, 1);
        rect.pivot = new Vector2(0, 1);
        rect.anchoredPosition = new Vector2(x, -top);
        rect.sizeDelta = new Vector2(width, height);
    }

    static void Stretch(RectTransform rect)
    {
        rect.anchorMin = Vector2.zero;
        rect.anchorMax = Vector2.one;
        rect.offsetMin = rect.offsetMax = Vector2.zero;
    }
}
