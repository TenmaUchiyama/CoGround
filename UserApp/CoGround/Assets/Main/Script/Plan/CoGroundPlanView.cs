using System;
using System.Collections.Generic;
using Newtonsoft.Json.Linq;
using UnityEngine;

/// <summary>
/// サーバーが作った Plan (state.updated の plan) をシーンに描く。
///
/// ■ step ごとに描くもの
///   - ok / infeasible: いまの位置から置き位置への弧、置き位置に物体の見た目の半透明コピー
///     (シーンに物体が無ければ物体の大きさの箱)、
///     ラベル「番号  物体 → 行き先」とルールの文
///   - ambiguous / unmatched (行き先が決まらない): 物体の上にラベルだけ
///   - deferred (家庭ルールによる保留): 物体の上にラベルだけ。理由と、違反・未確定になった家庭ルールを出す
///   色は status で変える (Ok / Infeasible / Undecided Color)。
///   弧と置き位置のゴーストを出すのは、この順番で運べると検証できた step だけ (CoGroundFuture.WillBeDone)。
///   作業の候補ができただけの step・検証で成立しなかった step は、物体の上のラベルだけにする。
///
/// ■ 使い方
///   CoGroundServerClient と同じシーンの、どれかの GameObject に付けるだけ。
///   Plan が変わるたびに描き直す。ルールが無い (plan が null) ときは何も描かない。
///
/// ■ ほかのスクリプトから
///   Plan / PlanChanged で今の Plan を受け取れる。Highlight(stepId) でその step だけを目立たせる (null で戻す)。
/// </summary>
public class CoGroundPlanView : MonoBehaviour
{
    [SerializeField] CoGroundServerClient client;

    [Header("色")]
    [SerializeField] Color okColor = new Color(0.2f, 0.9f, 0.5f, 0.9f);
    [SerializeField] Color infeasibleColor = new Color(1f, 0.3f, 0.25f, 0.9f);
    [Tooltip("ambiguous / unmatched (行き先が決まらない)")]
    [SerializeField] Color undecidedColor = new Color(1f, 0.8f, 0.2f, 0.9f);
    [Tooltip("deferred (家庭ルールによる保留。運ばずに残す)")]
    [SerializeField] Color deferredColor = new Color(0.65f, 0.6f, 1f, 0.9f);
    [Tooltip("Highlight で選ばれていない step の濃さ")]
    [Range(0f, 1f)] [SerializeField] float dimmedAlpha = 0.15f;

    [Header("形")]
    [SerializeField] float lineWidth = 0.008f;
    [Tooltip("弧のいちばん高い所を、始点と終点の高いほうからどれだけ上げるか [m]")]
    [SerializeField] float arcHeight = 0.15f;
    [Range(0f, 1f)] [SerializeField] float ghostAlpha = 0.35f;
    [SerializeField] bool showLabels = true;
    [Tooltip("いまの位置から置き位置への弧 (物体の通り道) を出す")]
    [SerializeField] bool showArcs = true;
    [SerializeField] float labelSize = 0.006f;
    [Tooltip("ラベルにルールの文も出す")]
    [SerializeField] bool showRuleText = true;
    [Tooltip("テキストと物体への引き出し線。空なら Resources/CoGroundObjectLabel を使用")]
    [SerializeField] CoGroundObjectLabel labelPrefab;

    /// <summary>文字のラベルを出すか (CoGroundRuleTagView を使うときは、そちらが false にする)。次に描き直すときに効く</summary>
    public bool ShowLabels { get => showLabels; set => showLabels = value; }

    /// <summary>弧 (物体の通り道) を出すか。すぐ効く</summary>
    public bool ShowArcs
    {
        get => showArcs;
        set
        {
            showArcs = value;
            foreach (var v in visuals)
                if (v.Line != null) v.Line.gameObject.SetActive(value);
        }
    }

    /// <summary>いまの Plan (無ければ null)</summary>
    public PlanDto Plan { get; private set; }
    public event Action<PlanDto> PlanChanged;

    const int ArcPoints = 24;
    const float DefaultSize = 0.1f;

    class StepVisual
    {
        public string StepId;
        public GameObject Root;
        public Color Color;
        public LineRenderer Line;
        /// <summary>ゴースト (物体の見た目の複製、または箱) の全 Renderer で共有する</summary>
        public Material GhostMaterial;
        public TextMesh Label;
        public CoGroundObjectLabel ObjectLabel;
    }

    readonly List<StepVisual> visuals = new List<StepVisual>();
    CoGroundServerClient subscribed;
    string drawnKey;
    string highlighted;
    JObject latestState;

    CoGroundServerClient Client => client != null ? client : CoGroundServerClient.Instance;

    void Start()
    {
        if (labelPrefab == null) labelPrefab = Resources.Load<CoGroundObjectLabel>("CoGroundObjectLabel");
        subscribed = Client;
        if (subscribed == null) { Debug.LogWarning("[CoGroundPlanView] CoGroundServerClient が見つからない", this); return; }
        subscribed.StateUpdated += OnStateUpdated;
        if (subscribed.LatestState != null) OnStateUpdated(subscribed.LatestState);
    }

    void OnDestroy()
    {
        if (subscribed != null) subscribed.StateUpdated -= OnStateUpdated;
        Clear();
    }

    void OnDisable() => SetVisible(false);
    void OnEnable() => SetVisible(true);

    void OnStateUpdated(JObject state)
    {
        var planToken = CoGroundFuture.PlanToken(state); // 依頼が無ければ null (CoGroundFuture.RequireTask)
        var plan = planToken != null && planToken.Type != JTokenType.Null
            ? planToken.ToObject<PlanDto>(CoGroundServerClient.Serializer) : null;

        // Plan と、描くのに使う物体の大きさ・ルールの文が同じなら描き直さない
        var sizes = new Dictionary<string, Vector3>();
        if (state["scene"]?["objects"] is JArray objects)
            foreach (var o in objects)
                if (o["size"] is JArray s && s.Count == 3) sizes[(string)o["id"]] = CoGroundServerClient.ToVector3(s);
        var ruleTexts = new Dictionary<string, string>();
        if (state["rules"] is JArray rules)
            foreach (var r in rules) ruleTexts[(string)r["id"]] = (string)r["text"];
        // 家庭ルール (norms) は住人の言葉 (original_text) を見せる
        var normTexts = "";
        if (state["norms"] is JArray norms)
            foreach (var n in norms)
            {
                var id = (string)n["id"];
                var original = (string)n["original_text"];
                if (id == null) continue;
                if (!string.IsNullOrEmpty(original) || !ruleTexts.ContainsKey(id)) ruleTexts[id] = original;
                normTexts += id + "=" + original + ";";
            }

        var key = planToken?.ToString(Newtonsoft.Json.Formatting.None) + "|" + (state["rules"]?.ToString(Newtonsoft.Json.Formatting.None)) + "|" + normTexts
                  + "|" + CoGroundFuture.Preview(state)?["steps"]?.ToString(Newtonsoft.Json.Formatting.None);
        latestState = state;
        var changed = plan?.Id != Plan?.Id || plan?.Version != Plan?.Version || key != drawnKey;
        Plan = plan;
        if (!changed) return;
        drawnKey = key;

        Clear();
        if (plan != null)
            foreach (var step in plan.Steps)
            {
                // まだ確かめている途中の step は、結果が出るまで出さない
                if (CoGroundFuture.IsChecking(state, plan, step)) continue;
                visuals.Add(Build(step, sizes, ruleTexts));
            }
        SetVisible(isActiveAndEnabled);
        ApplyHighlight();
        PlanChanged?.Invoke(plan);
    }

    /// <summary>その step だけを目立たせる。null か空で全部を元に戻す。</summary>
    public void Highlight(string stepId)
    {
        highlighted = string.IsNullOrEmpty(stepId) ? null : stepId;
        ApplyHighlight();
    }

    StepVisual Build(StepDto step, Dictionary<string, Vector3> sizes, Dictionary<string, string> ruleTexts)
    {
        // 保留 (deferred) は、行き先が入っていても運ばないので、物体の上にラベルだけを出す
        var deferred = step.Status == StepStatus.Deferred;
        // 検証できていない・成立しない step は、置き位置へ動く絵にしない
        var stepState = CoGroundFuture.StateOf(latestState, Plan, step, out var stateReason);
        var notMoving = stepState != CoGroundFuture.StepState.Move;
        var undecided = step.To == null || deferred || notMoving;
        var color = deferred ? deferredColor
            : stepState == CoGroundFuture.StepState.StayInfeasible || step.Status == StepStatus.Infeasible ? infeasibleColor
            : undecided ? undecidedColor : okColor;
        var size = sizes.TryGetValue(step.ObjectId, out var s) ? s : Vector3.one * DefaultSize;
        var from = step.From.Pose.PositionV;

        var v = new StepVisual { StepId = step.Id, Color = color, Root = new GameObject($"Plan Step {step.Id} ({step.ObjectId})") };
        v.Root.transform.SetParent(transform, true);

        Vector3 labelAt;
        string text;
        if (undecided)
        {
            labelAt = from + Vector3.up * (size.y * 0.5f + 0.03f);
            text = deferred ? $"{step.Index + 1}  {step.ObjectId}: deferred"
                : stepState == CoGroundFuture.StepState.StayInfeasible ? $"{step.Index + 1}  {step.ObjectId}: stays"
                : stepState == CoGroundFuture.StepState.Unverified ? $"{step.Index + 1}  {step.ObjectId}: unverified"
                : $"{step.Index + 1}  {step.ObjectId}: ?";
            if (!string.IsNullOrEmpty(step.Message)) text += "\n" + step.Message;
            else if (!string.IsNullOrEmpty(stateReason)) text += "\n" + stateReason;
            if (deferred) text += VerdictLines(step, ruleTexts);
        }
        else
        {
            var to = step.To.Pose.PositionV;

            v.Line = new GameObject("Arc").AddComponent<LineRenderer>();
            v.Line.transform.SetParent(v.Root.transform, false);
            v.Line.useWorldSpace = true;
            v.Line.material = FetchGhost.MakeMaterial(color);
            v.Line.startWidth = v.Line.endWidth = lineWidth;
            v.Line.numCapVertices = 4;
            v.Line.numCornerVertices = 2;
            v.Line.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            v.Line.receiveShadows = false;
            v.Line.positionCount = ArcPoints;
            // 2 次ベジェ。頂点が「高いほう + arcHeight」になるように制御点を置く
            var peak = Mathf.Max(from.y, to.y) + arcHeight;
            var control = (from + to) * 0.5f;
            control.y = 2f * peak - (from.y + to.y) * 0.5f;
            for (int i = 0; i < ArcPoints; i++)
            {
                var t = i / (float)(ArcPoints - 1);
                v.Line.SetPosition(i, (1 - t) * (1 - t) * from + 2 * (1 - t) * t * control + t * t * to);
            }

            v.Line.gameObject.SetActive(showArcs);

            v.GhostMaterial = FetchGhost.MakeMaterial(WithAlpha(color, ghostAlpha));
            BuildGhost(v, step.ObjectId, to, step.To.Pose.RotationQ, size);

            labelAt = to + Vector3.up * (size.y * 0.5f + 0.03f);
            text = $"{step.Index + 1}  {step.ObjectId} → {step.To.RegionId ?? "?"}";
            if (showRuleText && step.RuleId != null && ruleTexts.TryGetValue(step.RuleId, out var ruleText) && !string.IsNullOrEmpty(ruleText))
                text += "\n" + ruleText;
            if (!string.IsNullOrEmpty(step.Message)) text += "\n" + step.Message;
        }

        if (showLabels)
        {
            if (labelPrefab != null)
            {
                // 行き先を決められない場合も、該当するルールを表示する。
                if (undecided && !deferred && showRuleText)
                {
                    if (step.RuleId != null && ruleTexts.TryGetValue(step.RuleId, out var matchedText))
                        text += "\n" + matchedText;
                    foreach (var id in step.CandidateRuleIds)
                        if (ruleTexts.TryGetValue(id, out var candidateText)) text += "\n" + candidateText;
                }
                text += "\n[" + step.Status + "]";
                var obj = CoGroundSceneObject.Find(step.ObjectId);
                v.ObjectLabel = Instantiate(labelPrefab, v.Root.transform);
                v.ObjectLabel.Bind(obj != null ? obj.transform : null, from, text, color, labelSize);
                return v;
            }
            var labelGo = new GameObject("Label");
            labelGo.transform.SetParent(v.Root.transform, false);
            labelGo.transform.position = labelAt;
            v.Label = labelGo.AddComponent<TextMesh>();
            // TextMesh はフォントを指定しないと何も表示されないので、Unity 内蔵フォントを使う
            var font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
            v.Label.font = font;
            labelGo.GetComponent<MeshRenderer>().sharedMaterial = font.material;
            v.Label.anchor = TextAnchor.LowerCenter;
            v.Label.alignment = TextAlignment.Center;
            v.Label.characterSize = labelSize;
            v.Label.fontSize = 48;
            v.Label.color = color;
            v.Label.text = text;
        }
        return v;
    }

    /// <summary>保留の理由になった判定 (違反の予測・未確定) を、ルールの文と一緒に並べる。</summary>
    string VerdictLines(StepDto step, Dictionary<string, string> ruleTexts)
    {
        var text = "";
        if (step.Verdicts == null) return text;
        foreach (var verdict in step.Verdicts)
        {
            if (verdict.Value != VerdictValue.Violated && verdict.Value != VerdictValue.Undetermined) continue;
            text += $"\n{verdict.RuleId}: {VerdictValue.Label(verdict.Value)}";
            if (showRuleText && verdict.RuleId != null && ruleTexts.TryGetValue(verdict.RuleId, out var ruleText) && !string.IsNullOrEmpty(ruleText))
                text += $" \"{ruleText}\"";
            if (verdict.Missing != null && verdict.Missing.Count > 0)
            {
                var keys = new List<string>();
                foreach (var m in verdict.Missing) keys.Add(string.IsNullOrEmpty(m.EntityId) ? m.Key : $"{m.Key} of {m.EntityId}");
                text += "\n  Missing information: " + string.Join(", ", keys);
            }
        }
        return text;
    }

    /// <summary>
    /// 置き位置に、物体の見た目をそのまま写した半透明のゴーストを置く。
    /// シーンに物体が無い / メッシュが無いときは、物体の大きさの箱で代わりにする。
    /// </summary>
    void BuildGhost(StepVisual v, string objectId, Vector3 to, Quaternion toRotation, Vector3 size)
    {
        var obj = CoGroundSceneObject.Find(objectId);
        if (obj != null)
        {
            var ghost = FetchGhost.CreateVisualCopy(obj.transform, "Ghost", v.GhostMaterial);
            if (ghost.transform.childCount > 0)
            {
                // 置き位置は bbox の中心の姿勢なので、物体の Transform (= ゴーストのルート) の位置に直す
                obj.GetTransformInReportedFrame(out var localPos, out var localRot);
                ghost.transform.SetParent(v.Root.transform, false);
                ghost.transform.SetPositionAndRotation(to + toRotation * localPos, toRotation * localRot);
                foreach (var r in ghost.GetComponentsInChildren<Renderer>()) r.receiveShadows = false;
                return;
            }
            Destroy(ghost);
        }

        var box = GameObject.CreatePrimitive(PrimitiveType.Cube);
        box.name = "Ghost";
        Destroy(box.GetComponent<Collider>());
        box.transform.SetParent(v.Root.transform, false);
        box.transform.SetPositionAndRotation(to, toRotation);
        box.transform.localScale = size;
        var renderer = box.GetComponent<Renderer>();
        renderer.sharedMaterial = v.GhostMaterial;
        renderer.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
        renderer.receiveShadows = false;
    }

    void LateUpdate()
    {
        // ラベルをカメラに向ける (TextMesh は -Z 側から読める)
        var cam = Camera.main;
        if (cam == null) return;
        foreach (var v in visuals)
            if (v.Label != null)
                v.Label.transform.rotation = Quaternion.LookRotation(v.Label.transform.position - cam.transform.position, Vector3.up);
    }

    void ApplyHighlight()
    {
        foreach (var v in visuals)
        {
            var k = highlighted == null || v.StepId == highlighted ? 1f : dimmedAlpha;
            if (v.Line != null) v.Line.material.color = WithAlpha(v.Color, v.Color.a * k);
            if (v.GhostMaterial != null) v.GhostMaterial.color = WithAlpha(v.Color, ghostAlpha * k);
            if (v.Label != null) v.Label.color = WithAlpha(v.Color, v.Color.a * k);
            if (v.ObjectLabel != null) v.ObjectLabel.SetColor(WithAlpha(v.Color, v.Color.a * k));
        }
    }

    void SetVisible(bool visible)
    {
        foreach (var v in visuals)
            if (v.Root != null) v.Root.SetActive(visible);
    }

    void Clear()
    {
        foreach (var v in visuals)
        {
            if (v.Root == null) continue;
            // 実行中に作った Material も一緒に消す
            if (v.Line != null) Destroy(v.Line.material);
            if (v.GhostMaterial != null) Destroy(v.GhostMaterial);
            Destroy(v.Root);
        }
        visuals.Clear();
    }

    static Color WithAlpha(Color c, float a) => new Color(c.r, c.g, c.b, a);
}
