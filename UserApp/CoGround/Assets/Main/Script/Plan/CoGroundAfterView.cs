using System.Collections.Generic;
using Newtonsoft.Json.Linq;
using UnityEngine;

/// <summary>
/// Before / After の切り替え。After は「Plan を実行し終えたら、シーンはこうなる」(未来の環境) を一瞬で見せる。
/// アニメーションや動作計画の再生はしない (完了できるか・できないかをぱっと分かるようにするため)。
///
/// ■ どの時点を見せるか
///   Before → ①の後 → ②の後 → 最終 After を同じ視点で切り替えられる (SetViewStep / ShowFinal。CoGroundSequencePanel が呼ぶ)。
///   「①の後」なら、① までに動く物だけが動いた状態になり、② 以降で動く物は元の位置に通常の濃さで残る。
///
/// ■ After で見せるもの
///   - その時点までに動く物 (この順番で、把持・移動・配置まで実行できると検証できた step。CoGroundFuture.MovedAtView):
///     元の位置の物体を消し (Diminish。当たり判定や MoveIt はそのまま)、置き終わった姿勢に予測位置のコピーを置く。
///     消し方は Diminish Style で選ぶ:
///       DiminishedReality  物体の箱に DR のマスク (DR/StencilMask) を置く。箱の中だけ、物が無いときの背景メッシュ
///                          (DR/StencilReadTextured。Script/DiminishReality/README.md) が見えるので、
///                          パススルーに写っている実物も消えて見える。Renderer がある物体 (シミュレーション) は Renderer も切る。
///                          カメラで認識した物体 (CoGroundPerceivedObjects) にも効く。
///                          背景メッシュがシーンに無いときは Ghost と同じ見せ方にする
///       Ghost              Renderer を切って、薄いコピーを置く (実物は消えない)
///     「皿を棚に置く」という作業の候補ができただけ (検証前・検証で成立しなかった) の物は、動かさない。
///     置き終わった姿勢は、動作計画 (motion.plan) があればその最後の姿勢、無ければ Plan の置き位置
///     (動作計画は再生しない。計算が終われば最後の姿勢は決まっている)
///   - ゴールにたどり着けない物 (deferred / ambiguous / unmatched / infeasible): 物体は残し、上に理由のラベルを出す
///       deferred    家庭ルールで保留 (触るな・進入禁止の経路しかない・判定する情報が足りない)。違反・未確定のルールの文も出す
///       ambiguous   合うルールが複数あり、行き先が決まらない (候補のルールの文も出す)
///       unmatched   行き先の領域がシーンに無い
///       infeasible  動作が成立しない (置き先に空きが無い、経路が無い、つかめない など。検証で分かったもの)
///       unverified  未確認 (認識不足・タイムアウトなど)。今回の実行の対象から外れる
///   - Plan に出てこない物 (もう行き先にある、ルールに関係ない): そのまま
///   After のあいだは CoGroundPlanView (弧・ゴースト) と、動作計画の再生 (CoGroundTaskPlanPlayer の Ghost) を隠す。
///
/// ■ Before
///   いまのシーンのまま (この部品は何もしない。隠した物体は元に戻す)。
///
/// ■ 使い方
///   CoGroundServerClient と同じシーンのどれかの GameObject に付ける。Mode で切り替える
///   (インスペクタ、コンテキストメニュー、または SetMode / Toggle を UI から呼ぶ)。
///   Plan が変わるたびに (ロボットが運んだ、ルールを変えた) 描き直す。
/// </summary>
public class CoGroundAfterView : MonoBehaviour
{
    public enum ViewMode { Before, After }
    public enum DiminishStyle { DiminishedReality, Ghost }

    [SerializeField] CoGroundServerClient client;
    [SerializeField] ViewMode mode = ViewMode.After;
    [Tooltip("After のあいだ隠す Plan の表示 (空なら同じシーンから探す)")]
    [SerializeField] CoGroundPlanView planView;
    [SerializeField] bool hidePlanViewInAfter = true;

    [Header("ラベル")]
    [Tooltip("空なら Resources/CoGroundObjectLabel")]
    [SerializeField] CoGroundObjectLabel labelPrefab;
    [Tooltip("片付けられない物の上に文字のラベルを出す (CoGroundRuleTagView を使うときは、そちらが false にする)")]
    [SerializeField] bool showLabels = true;
    [SerializeField] float labelSize = 0.006f;
    [SerializeField] bool showRuleText = true;
    [Tooltip("deferred (家庭ルールによる保留)")]
    [SerializeField] Color deferredColor = new Color(0.65f, 0.6f, 1f, 0.95f);
    [Tooltip("ambiguous / unmatched (行き先が決まらない)")]
    [SerializeField] Color undecidedColor = new Color(1f, 0.8f, 0.2f, 0.95f);
    [Tooltip("infeasible (動かし方を計画できない)")]
    [SerializeField] Color infeasibleColor = new Color(1f, 0.3f, 0.25f, 0.95f);

    [Header("未来の環境")]
    [Tooltip("片付いた物を、置き終わった姿勢に半透明で置く")]
    [SerializeField] bool showFutureObjects = true;
    [SerializeField] Color futureColor = new Color(0.85f, 0.92f, 1f, 0.55f);
    [Tooltip("動く物を元の位置からどう消すか。\n" +
             "DiminishedReality: 物体の箱に DR のマスクを置き、物が無いときの背景メッシュを見せる (実物も消える)。" +
             "背景メッシュ (DR/StencilReadTextured) がシーンに無ければ Ghost になる\n" +
             "Ghost: 薄い姿を残す")]
    [SerializeField] DiminishStyle diminishStyle = DiminishStyle.DiminishedReality;
    [Tooltip("Ghost のとき、動く物の元の位置に残す薄い姿。alpha を 0 にすると完全に消す")]
    [SerializeField] Color diminishedColor = new Color(0.8f, 0.8f, 0.85f, 0.14f);
    [Tooltip("DR のマスクの材質 (DR_StencilMask.mat)。空なら Resources の DR_StencilMask シェーダーから作る")]
    [SerializeField] Material drMaskMaterial;
    [Tooltip("DR のマスクを物体の箱より大きくする倍率 (影や位置のずれを覆う)")]
    [SerializeField] float drMaskMargin = 1.2f;
    [Tooltip("DR のマスクを各方向に広げる量 [m] (倍率のあとに足す。下は机にめり込ませる)")]
    [SerializeField] float drMaskPadding = 0.02f;
    [Tooltip("カメラで認識した物体の箱 (空なら同じシーンから探す)。Renderer の無い実物を DR で消すのに使う")]
    [SerializeField] CoGroundPerceivedObjects perceivedObjects;
    [Tooltip("未確認 (検証できなかった。実行の対象から外れる)")]
    [SerializeField] Color unverifiedColor = new Color(0.75f, 0.75f, 0.78f, 0.95f);

    public ViewMode Mode => mode;
    /// <summary>見せている時点: この番号 (0 始まり) の step まで終わった状態。最終 After は int.MaxValue</summary>
    public int ViewStep => CoGroundFuture.UpToIndex;
    /// <summary>モードか時点が変わった</summary>
    public event System.Action ViewChanged;
    public bool ShowLabels { get => showLabels; set { showLabels = value; if (subscribed != null) Apply(); } }

    CoGroundServerClient Client => client != null ? client : CoGroundServerClient.Instance;
    CoGroundServerClient subscribed;
    PlanDto plan;
    JObject state;
    CoGroundTaskPlanPlayer player;
    Material futureMaterial;
    Material diminishedMaterial;
    Material createdMaskMaterial;
    bool hasDrBackground;
    bool warnedNoDrBackground;
    readonly List<GameObject> futureObjects = new List<GameObject>();
    readonly Dictionary<string, string> ruleTexts = new Dictionary<string, string>();
    string drawnKey;

    /// <summary>見えなくした Renderer と、元の enabled</summary>
    readonly Dictionary<Renderer, bool> hidden = new Dictionary<Renderer, bool>();
    readonly List<GameObject> labels = new List<GameObject>();

    void Start()
    {
        if (labelPrefab == null) labelPrefab = Resources.Load<CoGroundObjectLabel>("CoGroundObjectLabel");
        if (planView == null) planView = FindAnyObjectByType<CoGroundPlanView>();
        if (perceivedObjects == null) perceivedObjects = FindAnyObjectByType<CoGroundPerceivedObjects>();
        subscribed = Client;
        if (subscribed == null) { Debug.LogWarning("[CoGroundAfterView] CoGroundServerClient が見つからない", this); return; }
        subscribed.StateUpdated += OnStateUpdated;
        player = CoGroundTaskPlanPlayer.Instance;
        if (player != null) player.TimelineChanged += OnTimelineChanged;
        if (subscribed.LatestState != null) OnStateUpdated(subscribed.LatestState);
        Apply();
    }

    // 動作計画の時間軸が届いたら、置き終わった姿勢が変わる
    void OnTimelineChanged() { if (isActiveAndEnabled) Apply(); }

    void OnDestroy()
    {
        if (subscribed != null) subscribed.StateUpdated -= OnStateUpdated;
        if (player != null) player.TimelineChanged -= OnTimelineChanged;
        Restore();
        if (futureMaterial != null) Destroy(futureMaterial);
        if (diminishedMaterial != null) Destroy(diminishedMaterial);
        if (createdMaskMaterial != null) Destroy(createdMaskMaterial);
    }

    void OnDisable() { Restore(); SetPlanViewVisible(true); SetPlayerSuppressed(false); }
    void OnEnable() { if (subscribed != null) Apply(); }

    void OnValidate()
    {
        if (Application.isPlaying && isActiveAndEnabled && subscribed != null) Apply();
    }

    public void SetMode(ViewMode m)
    {
        mode = m;
        if (m == ViewMode.After && CoGroundFuture.UpToIndex < 0) CoGroundFuture.UpToIndex = int.MaxValue;
        Apply();
        ViewChanged?.Invoke();
    }

    /// <summary>「この番号 (0 始まり) の step の後」を見せる。Before / 最終 After と同じ視点のまま、物体だけが変わる</summary>
    public void SetViewStep(int stepIndex)
    {
        CoGroundFuture.UpToIndex = stepIndex;
        mode = ViewMode.After;
        Apply();
        ViewChanged?.Invoke();
    }

    /// <summary>最終 After (全部の step が終わった状態)</summary>
    public void ShowFinal() => SetViewStep(int.MaxValue);

    [ContextMenu("Before / After を切り替える")]
    public void Toggle() => SetMode(mode == ViewMode.After ? ViewMode.Before : ViewMode.After);

    [ContextMenu("Before")] public void ShowBefore() => SetMode(ViewMode.Before);
    [ContextMenu("After")] public void ShowAfter() => SetMode(ViewMode.After);

    void OnStateUpdated(JObject state)
    {
        var planToken = CoGroundFuture.PlanToken(state); // 依頼が無ければ null (CoGroundFuture.RequireTask)
        plan = planToken != null && planToken.Type != JTokenType.Null
            ? planToken.ToObject<PlanDto>(CoGroundServerClient.Serializer) : null;
        this.state = state;

        ruleTexts.Clear();
        if (state["rules"] is JArray rules)
            foreach (var r in rules) ruleTexts[(string)r["id"]] = (string)r["text"];
        if (state["norms"] is JArray norms)  // 家庭ルールは住人の言葉 (original_text)
            foreach (var n in norms)
            {
                var id = (string)n["id"];
                var original = (string)n["original_text"];
                if (id != null && (!string.IsNullOrEmpty(original) || !ruleTexts.ContainsKey(id))) ruleTexts[id] = original;
            }
        // 依頼の間だけのルール (T1 など。「全部 box_1 に入れて」)。依頼が開いている間だけ効く
        if (state["task"] is JObject task && task["closed_at"]?.Type == JTokenType.Null && task["rules"] is JArray taskRules)
            foreach (var n in taskRules)
                if ((string)n["id"] is string id) ruleTexts[id] = (string)n["original_text"];

        var key = planToken?.ToString(Newtonsoft.Json.Formatting.None) + "|" + string.Join(";", ruleTexts)
                  + "|" + state["motion"]?.ToString(Newtonsoft.Json.Formatting.None);
        if (key == drawnKey) return;
        drawnKey = key;
        Apply();
    }

    void Apply()
    {
        Restore();
        var after = mode == ViewMode.After && isActiveAndEnabled;
        SetPlanViewVisible(!(after && hidePlanViewInAfter));
        SetPlayerSuppressed(after);
        if (!after || plan == null) return;

        foreach (var step in plan.Steps)
        {
            var obj = CoGroundSceneObject.Find(step.ObjectId);
            var stepState = CoGroundFuture.StateOf(state, plan, step, out var reason);
            if (stepState == CoGroundFuture.StepState.Move)
            {
                // 検証できた step。見せている時点より後で動く物は、まだ元の位置に通常の濃さである
                if (step.Index > CoGroundFuture.UpToIndex) continue;
                // 予測位置のコピーは、物体を隠す前に作る (隠した Renderer は写せない)
                var hasPose = CoGroundFuture.TryFinalPose(state, plan, step, out var pos, out var rot);
                if (showFutureObjects && hasPose) AddFutureObject(step, obj, pos, rot);
                Diminish(step, obj);
                continue;
            }
            // まだ確かめている途中の step は、結果が出るまで何も出さない (元の位置に通常の濃さである)
            if (stepState == CoGroundFuture.StepState.Checking) continue;
            AddLabel(step, obj, step.Status == StepStatus.Ok ? reason ?? "" : null,
                     stepState == CoGroundFuture.StepState.Unverified);
        }
    }

    /// <summary>置き終わった姿勢 (bbox の中心) に、物体の見た目の半透明コピーを置く (物体が無ければ箱)</summary>
    void AddFutureObject(StepDto step, CoGroundSceneObject obj, Vector3 center, Quaternion rotation)
    {
        if (futureMaterial == null) futureMaterial = FetchGhost.MakeMaterial(futureColor);
        GameObject copy = null;
        if (obj != null)
        {
            copy = FetchGhost.CreateVisualCopy(obj.transform, $"Future ({step.ObjectId})", futureMaterial);
            if (copy.transform.childCount > 0)
            {
                obj.GetTransformInReportedFrame(out var localPos, out var localRot);
                copy.transform.SetPositionAndRotation(center + rotation * localPos, rotation * localRot);
            }
            else { Destroy(copy); copy = null; }
        }
        if (copy == null)
        {
            copy = GameObject.CreatePrimitive(PrimitiveType.Cube);
            copy.name = $"Future ({step.ObjectId})";
            Destroy(copy.GetComponent<Collider>());
            copy.transform.SetPositionAndRotation(center, rotation);
            copy.transform.localScale = Vector3.one * 0.1f;
            copy.GetComponent<Renderer>().sharedMaterial = futureMaterial;
        }
        copy.transform.SetParent(transform, true);
        foreach (var r in copy.GetComponentsInChildren<Renderer>())
        {
            r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            r.receiveShadows = false;
        }
        futureObjects.Add(copy);
    }

    /// <summary>元の位置の物体を消す (DR のマスク、または薄いコピー)。obj が null = Renderer の無い実物 (カメラで認識した物体)</summary>
    void Diminish(StepDto step, CoGroundSceneObject obj)
    {
        if (diminishStyle == DiminishStyle.DiminishedReality && HasDrBackground())
        {
            if (TryGetObjectBox(step, obj, out var center, out var rotation, out var size)) AddDrMask(step, center, rotation, size);
            if (obj != null) Hide(obj.transform);
            return;
        }
        if (obj == null) return;
        if (diminishedColor.a > 0.001f)
        {
            if (diminishedMaterial == null) diminishedMaterial = FetchGhost.MakeMaterial(diminishedColor);
            diminishedMaterial.color = diminishedColor;
            var copy = FetchGhost.CreateVisualCopy(obj.transform, $"Diminished ({step.ObjectId})", diminishedMaterial);
            copy.transform.SetParent(transform, true);
            foreach (var r in copy.GetComponentsInChildren<Renderer>()) r.receiveShadows = false;
            futureObjects.Add(copy);
        }
        Hide(obj.transform);
    }

    /// <summary>動かす前の物体の箱。シーンの物体ならその箱、カメラで認識した物体なら認識結果の箱</summary>
    bool TryGetObjectBox(StepDto step, CoGroundSceneObject obj, out Vector3 center, out Quaternion rotation, out Vector3 size)
    {
        if (obj != null) { obj.GetBox(out center, out rotation, out size); return true; }
        rotation = Quaternion.identity; // 認識結果の箱はワールド軸に沿っている
        if (perceivedObjects != null && perceivedObjects.TryGetBox(step.ObjectId, out center, out size)) return true;
        center = size = Vector3.zero;
        return false;
    }

    /// <summary>
    /// DR のマスク (見えない箱。覆った画素のステンシルに印を付ける) を物体の箱に置く。
    /// 背景メッシュ (DR/StencilReadTextured) はこの箱の中だけ描かれる。
    /// </summary>
    void AddDrMask(StepDto step, Vector3 center, Quaternion rotation, Vector3 size)
    {
        var material = DrMaskMaterial();
        if (material == null) return;
        var box = GameObject.CreatePrimitive(PrimitiveType.Cube);
        box.name = $"DR Mask ({step.ObjectId})";
        Destroy(box.GetComponent<Collider>()); // 検出のレイや把持の当たり判定に入れない
        box.transform.SetPositionAndRotation(center, rotation);
        box.transform.localScale = size * Mathf.Max(1f, drMaskMargin) + Vector3.one * (2f * Mathf.Max(0f, drMaskPadding));
        box.transform.SetParent(transform, true);
        var r = box.GetComponent<Renderer>();
        r.sharedMaterial = material;
        r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
        r.receiveShadows = false;
        box.AddComponent<DRMaskShaderGlobals>(); // 箱の輪郭をぼかす (背景のシェーダーに箱の位置を渡す)
        futureObjects.Add(box);
    }

    Material DrMaskMaterial()
    {
        if (drMaskMaterial != null) return drMaskMaterial;
        if (createdMaskMaterial == null)
        {
            var shader = Resources.Load<Shader>("DR_StencilMask");
            if (shader == null) { Debug.LogError("[CoGroundAfterView] Resources/DR_StencilMask (シェーダー) が無い", this); return null; }
            createdMaskMaterial = new Material(shader);
        }
        return createdMaskMaterial;
    }

    /// <summary>物が無いときの背景メッシュ (DR/StencilRead... の材質) がシーンにあるか。無ければ DR では何も出ない</summary>
    bool HasDrBackground()
    {
        if (hasDrBackground) return true;
        foreach (var r in FindObjectsByType<MeshRenderer>(FindObjectsSortMode.None))
            foreach (var m in r.sharedMaterials)
                if (m != null && m.shader != null && m.shader.name.StartsWith("DR/StencilRead")) return hasDrBackground = true;
        if (!warnedNoDrBackground)
        {
            warnedNoDrBackground = true;
            Debug.LogWarning("[CoGroundAfterView] Diminish Style = DiminishedReality だが、背景メッシュ (DR/StencilReadTextured の材質) が" +
                             "シーンに無いので Ghost で見せる。Script/DiminishReality/README.md の手順 2・3", this);
        }
        return false;
    }

    void SetPlayerSuppressed(bool suppressed)
    {
        if (player != null) player.Suppressed = suppressed;
    }

    void Hide(Transform root)
    {
        foreach (var r in root.GetComponentsInChildren<Renderer>(true))
        {
            if (hidden.ContainsKey(r)) continue;
            hidden[r] = r.enabled;
            r.enabled = false;
        }
    }

    /// <param name="motionReason">null でなければ、動作計画で計画できないと分かった (その理由)</param>
    void AddLabel(StepDto step, CoGroundSceneObject obj, string motionReason = null, bool unverified = false)
    {
        if (labelPrefab == null || !showLabels) return;
        Color color;
        string headline;
        if (unverified) { color = unverifiedColor; headline = "Unverified (not part of this run)"; }
        else if (motionReason != null) { color = infeasibleColor; headline = "Stays here (can't be done)"; }
        else switch (step.Status)
        {
            case StepStatus.Deferred: color = deferredColor; headline = "Can't tidy (deferred)"; break;
            case StepStatus.Ambiguous: color = undecidedColor; headline = "Destination undecided"; break;
            case StepStatus.Unmatched: color = undecidedColor; headline = "No destination"; break;
            case StepStatus.Infeasible: color = infeasibleColor; headline = "Stays here (can't be done)"; break;
            default: color = undecidedColor; headline = step.Status; break;
        }

        var text = $"{step.ObjectId}: {headline}";
        if (!string.IsNullOrEmpty(motionReason)) text += "\n" + motionReason;
        if (!string.IsNullOrEmpty(step.Message)) text += "\n" + step.Message;
        if (step.Status == StepStatus.Deferred) text += VerdictLines(step);
        if (step.Status == StepStatus.Ambiguous && showRuleText)
            foreach (var id in step.CandidateRuleIds)
                if (ruleTexts.TryGetValue(id, out var t) && !string.IsNullOrEmpty(t)) text += $"\nCandidate {id} \"{t}\"";

        var from = step.From?.Pose != null ? step.From.Pose.PositionV : (obj != null ? obj.transform.position : Vector3.zero);
        var label = Instantiate(labelPrefab, transform);
        label.name = $"After Label ({step.ObjectId})";
        label.Bind(obj != null ? obj.transform : null, from, text, color, labelSize);
        labels.Add(label.gameObject);
    }

    /// <summary>保留の理由になった判定 (違反の予測・未確定) を、ルールの文と一緒に並べる。</summary>
    string VerdictLines(StepDto step)
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

    void Restore()
    {
        foreach (var kv in hidden)
            if (kv.Key != null) kv.Key.enabled = kv.Value;
        hidden.Clear();
        foreach (var l in labels)
            if (l != null) Destroy(l);
        labels.Clear();
        foreach (var f in futureObjects)
        {
            if (f == null) continue;
            f.SetActive(false); // DR のマスクは、この場で数から外す (Destroy はフレームの終わり)
            Destroy(f);
        }
        futureObjects.Clear();
    }

    void SetPlanViewVisible(bool visible)
    {
        if (planView != null && planView.enabled != visible) planView.enabled = visible;
    }
}
