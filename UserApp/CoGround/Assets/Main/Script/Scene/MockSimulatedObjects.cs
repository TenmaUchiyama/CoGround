using System;
using System.Collections.Generic;
using System.Globalization;
using System.Text;
using Newtonsoft.Json;
using UnityEngine;

/// <summary>
/// VR シミュレーション用: 「物体はもう認識できた」体で、認識結果の物体リストをサーバーに送る。
/// 検出 (DetectionPipeline) を飛ばして、ルール照合 → タスクの計画 (Plan) から始めるための入口。
///
/// ■ 流れ
///   MockSimulatedObjects (認識済みの物体リスト = 検出器が出す部分: カテゴリ・位置・大きさ)
///      │ scene.update  (SceneObjectDto のリスト、observation.source = detection)
///      ▼
///   サーバー vlm.py      … 属性 (fragile / trash など) を VLM が付ける (いまは代役 vlm_mock_attributes.json)
///   サーバー norms/planner.py … 物体ごとに属性と家庭ルール (片付けルールも含む) を照合し、行き先と「触ってよいか」を決めて Plan を作る
///      │ state.updated (plan)
///      ▼
///   CoGroundPlanView が描く / CoGroundTaskPlanPlayer が実行する
///   ルールは CoGroundRulesSender が rules.set で送る (送る順はどちらが先でもよい。サーバーはどちらでも Plan を作り直す)
///   サーバーは COGROUND_VLM=mock で動かす (compose.yaml の既定)。off だと属性が付かず、条件のあるルールに合わない
///
/// ■ 属性
///   基本は送らない (VLM の仕事)。Attributes に書いた分だけ送り、サーバーの VLM より優先される。
///   「VLM が間違えた」「検出器が属性も出した」場合を試すときに使う。
///
/// ■ 使い方
///   1. CoGroundSceneReporter と同じシーンの GameObject に付ける
///   2. コンテキストメニュー「シーンの物体から認識結果を作る」で、いまの CoGroundSceneObject を
///      認識された形 (observation.source = detection) に写してリストにする。属性は写さない (Copy Attributes On Capture で写す)。
///      リストはインスペクタで直せる (確信度を下げる・Recognized を外して「見つからなかった」にする など)
///   3. Play。Replace Simulation Objects が on なら、CoGroundSceneReporter は真値 (CoGroundSceneObject) を送らず、
///      このリストだけを送る。接続したら認識結果と、届いた Plan をログに出す
///
/// ■ 位置
///   Anchor があれば、Position / Rotation / Place Zone / Approach Poses は Anchor から見た値 (スケールは見ない)。
///   ロボットが Anchor の物体を運ぶと認識結果の位置も付いていくので、実行後に Plan が作り直される。
///   Anchor が無ければワールド座標の値 (動かない)。
/// </summary>
public class MockSimulatedObjects : MonoBehaviour, ICoGroundSceneSource
{
    public enum ObservationSourceKind { detection, manual, simulation }
    public enum AttributeSourceKind { vlm, detector, user, ground_truth }
    public enum TrackingKind { tracked, occluded, lost }

    [Serializable]
    public class MockAttribute
    {
        public string key;
        [Tooltip("true / false、数値、文字列のどれか")]
        public string value;
        public AttributeSourceKind source = AttributeSourceKind.vlm;
        [Range(0f, 1f)] public float confidence = 0.9f;
    }

    [Serializable]
    public class MockPose
    {
        public Vector3 position;
        public Vector3 rotation;
    }

    /// <summary>認識された物体 1 つ分。ToDto でサーバーが照合する SceneObjectDto になる</summary>
    [Serializable]
    public class MockSimulatedObject
    {
        [Tooltip("外すと「見つからなかった」扱い (送らない)")]
        public bool recognized = true;
        public string id;
        public CoGroundCategory category = CoGroundCategory.cup;
        [Tooltip("検出器の生のラベル (空なら category)")]
        public string detectorLabel;
        [Range(0f, 1f)] public float confidence = 0.9f;
        public TrackingKind tracking = TrackingKind.tracked;

        [Tooltip("位置の基準。あれば下の値はこの Transform から見た値 (物体を運ぶと付いていく)。無ければワールド座標")]
        public Transform anchor;
        [Tooltip("bbox の中心")]
        public Vector3 position;
        [Tooltip("bbox の向き (オイラー角)")]
        public Vector3 rotation;
        [Tooltip("bbox の大きさ [m] (ローカル軸)")]
        public Vector3 size = new Vector3(0.1f, 0.1f, 0.1f);

        [Tooltip("ふつうは空 (属性はサーバーの VLM が付ける)。書いた分だけ送り、VLM より優先される")]
        public List<MockAttribute> attributes = new List<MockAttribute>();

        [Header("置く場所 (receptacle / surface のみ)")]
        public bool hasPlaceZone;
        public Vector3 placeZoneCenter;
        public Vector3 placeZoneRotation;
        public Vector3 placeZoneSize;
        public List<MockPose> approachPoses = new List<MockPose>();

        Vector3 ToWorld(Vector3 p) => anchor != null ? anchor.position + anchor.rotation * p : p;
        Quaternion ToWorldRot(Vector3 euler) => anchor != null ? anchor.rotation * Quaternion.Euler(euler) : Quaternion.Euler(euler);

        public Vector3 WorldPosition => ToWorld(position);
        public Quaternion WorldRotation => ToWorldRot(rotation);

        public SceneObjectDto ToDto(ObservationSourceKind source)
        {
            var dto = new SceneObjectDto
            {
                Id = id,
                Category = category.ToString(),
                Position = SceneJson.V(ToWorld(position)),
                Rotation = SceneJson.Q(ToWorldRot(rotation)),
                Size = SceneJson.V(size),
                Observation = new ObservationDto
                {
                    Source = source.ToString(),
                    DetectorLabel = string.IsNullOrWhiteSpace(detectorLabel) ? category.ToString() : detectorLabel.Trim(),
                    Confidence = confidence,
                    Tracking = tracking.ToString(),
                    LastSeen = Time.time,
                },
            };
            foreach (var a in attributes)
            {
                if (string.IsNullOrWhiteSpace(a.key)) continue;
                dto.Attributes[a.key.Trim()] = new AttributeDto
                {
                    Value = ParseValue(a.value),
                    Source = a.source.ToString(),
                    Confidence = a.source == AttributeSourceKind.ground_truth ? (float?)null : a.confidence,
                };
            }
            if (hasPlaceZone)
                dto.PlaceZone = BoxDto.From(ToWorld(placeZoneCenter), ToWorldRot(placeZoneRotation), placeZoneSize);
            foreach (var p in approachPoses)
                (dto.ApproachPoses ??= new List<PoseDto>()).Add(PoseDto.From(ToWorld(p.position), ToWorldRot(p.rotation)));
            return dto;
        }
    }

    [Header("認識済みの物体")]
    [SerializeField] List<MockSimulatedObject> objects = new List<MockSimulatedObject>();
    [Tooltip("observation.source に入れる値。認識された体なら detection")]
    [SerializeField] ObservationSourceKind observationSource = ObservationSourceKind.detection;

    [Header("シミュレーションの開始")]
    [Tooltip("空なら同じシーンから探す")]
    [SerializeField] CoGroundSceneReporter reporter;
    [Tooltip("空なら同じシーンから探す (無くてもよい)")]
    [SerializeField] CoGroundRulesSender rulesSender;
    [Tooltip("空なら同じシーンから探す (無くてもよい。Plan をログに出すのに使う)")]
    [SerializeField] CoGroundPlanView planView;
    [Tooltip("CoGroundSceneReporter に真値 (CoGroundSceneObject) を送らせず、このリストだけを送らせる")]
    [SerializeField] bool replaceSimulationObjects = true;
    [SerializeField] bool logRecognizedOnConnect = true;
    [SerializeField] bool logPlan = true;
    [Tooltip("サーバーが付けた属性 (VLM) を、変わったときにログに出す")]
    [SerializeField] bool logVlmAttributes = true;

    string lastAttributeLog;

    public IReadOnlyList<MockSimulatedObject> Objects => objects;

    CoGroundServerClient subscribed;

    void Awake()
    {
        if (reporter == null) reporter = FindAnyObjectByType<CoGroundSceneReporter>();
        if (rulesSender == null) rulesSender = FindAnyObjectByType<CoGroundRulesSender>();
        if (planView == null) planView = FindAnyObjectByType<CoGroundPlanView>();

        if (reporter == null) { Debug.LogWarning("[MockSimulatedObjects] CoGroundSceneReporter が見つからない", this); return; }
        // 接続 (= reporter が最初に送る) より前に切り替える
        if (replaceSimulationObjects) reporter.IncludeSimulationObjects = false;
        reporter.AddSource(this);
        
    }

    void Start()
    {
        subscribed = CoGroundServerClient.Instance;
        if (subscribed != null)
        {
            subscribed.Connected += OnConnected;
            subscribed.StateUpdated += OnStateUpdated;
            if (subscribed.IsConnected) OnConnected();
        }
        if (planView != null) planView.PlanChanged += OnPlanChanged;
        Debug.Log("Started");
    }

    void OnDestroy()
    {
        if (subscribed != null) { subscribed.Connected -= OnConnected; subscribed.StateUpdated -= OnStateUpdated; }
        if (planView != null) planView.PlanChanged -= OnPlanChanged;
    }

    void OnConnected()
    {
        if (logRecognizedOnConnect) LogRecognized();
    }

    public void CollectObjects(List<SceneObjectDto> into)
    {
        foreach (var o in objects)
            if (o.recognized && !string.IsNullOrWhiteSpace(o.id)) into.Add(o.ToDto(observationSource));
    }

    /// <summary>サーバーに送る形 (scene.update の params) のまま返す</summary>
    public SceneSnapshotDto BuildSnapshot()
    {
        var snapshot = new SceneSnapshotDto { CapturedAt = Time.time };
        CollectObjects(snapshot.Objects);
        return snapshot;
    }

    /// <summary>認識結果を送り直し、ルールも送り直す (= ここから計画をやり直す)</summary>
    [ContextMenu("認識済みの状態から計画をやり直す")]
    public void Restart()
    {
        if (!Application.isPlaying) { Debug.LogWarning("[MockSimulatedObjects] Play 中に使う", this); return; }
        LogRecognized();
        if (reporter != null) reporter.SendNow();
        if (rulesSender != null) rulesSender.SendRules();
    }

    [ContextMenu("認識結果を JSON でログに出す")]
    public void LogRecognizedJson()
    {
        Debug.Log("[MockSimulatedObjects] scene.update:\n" + JsonConvert.SerializeObject(BuildSnapshot(), Formatting.Indented), this);
    }

    void LogRecognized()
    {
        var sb = new StringBuilder();
        int n = 0;
        foreach (var o in objects)
        {
            if (!o.recognized || string.IsNullOrWhiteSpace(o.id)) continue;
            n++;
            sb.Append($"\n  {o.id} ({o.category}, {o.confidence:0.00})");
            if (o.hasPlaceZone) sb.Append(" [置く場所]");
            foreach (var a in o.attributes)
                if (!string.IsNullOrWhiteSpace(a.key)) sb.Append($" {a.key.Trim()}={a.value}");
        }
        Debug.Log($"[MockSimulatedObjects] 認識済みの物体 {n} 個 (source={observationSource}) から開始:{sb}", this);
    }

    void OnStateUpdated(Newtonsoft.Json.Linq.JObject state)
    {
        if (!logVlmAttributes || !(state["scene"]?["objects"] is Newtonsoft.Json.Linq.JArray objs)) return;
        var sb = new StringBuilder();
        foreach (var o in objs)
        {
            if ((string)o["observation"]?["source"] != "detection") continue;
            sb.Append($"\n  {o["id"]}:");
            if (o["attributes"] is Newtonsoft.Json.Linq.JObject attrs)
                foreach (var p in attrs.Properties())
                    sb.Append($" {p.Name}={p.Value["value"]?.ToString(Formatting.None)}({p.Value["source"]})");
        }
        var text = sb.ToString();
        if (text == lastAttributeLog) return;  // 変わったときだけ
        lastAttributeLog = text;
        Debug.Log($"[MockSimulatedObjects] サーバーが照合に使う属性:{text}", this);
    }

    void OnPlanChanged(PlanDto plan)
    {
        if (!logPlan) return;
        if (plan == null) { Debug.Log("[MockSimulatedObjects] Plan なし (ルールが無い)", this); return; }
        var sb = new StringBuilder();
        foreach (var s in plan.Steps)
        {
            var to = s.To?.RegionId ?? "?";
            sb.Append($"\n  {s.Index + 1}. {s.ObjectId}: {s.From?.RegionId ?? "-"} → {to}  [{s.Status}] rule={s.RuleId ?? "-"}");
            if (s.CandidateRuleIds != null && s.CandidateRuleIds.Count > 0) sb.Append($" 候補={string.Join(",", s.CandidateRuleIds)}");
            if (!string.IsNullOrEmpty(s.Message)) sb.Append($" ({s.Message})");
        }
        Debug.Log($"[MockSimulatedObjects] Plan v{plan.Version} (scene v{plan.BaseSceneVersion}) steps={plan.Steps.Count}{sb}", this);
    }

    /// <summary>
    /// いまのシーンの CoGroundSceneObject を、認識された形に写してリストを作り直す。
    /// Anchor はその物体 (運ぶと付いていく)。属性は vlm、確信度は Default Confidence。
    /// </summary>
    [ContextMenu("シーンの物体から認識結果を作る")]
    public void CaptureFromScene()
    {
#if UNITY_EDITOR
        UnityEditor.Undo.RecordObject(this, "Capture Mock Simulated Objects");
#endif
        var sceneObjects = FindObjectsByType<CoGroundSceneObject>(FindObjectsInactive.Exclude, FindObjectsSortMode.None);
        Array.Sort(sceneObjects, (a, b) => string.CompareOrdinal(a.Id, b.Id));
        objects = new List<MockSimulatedObject>();
        foreach (var so in sceneObjects)
        {
            var dto = so.ToDto();
            var anchor = so.transform;
            var inv = Quaternion.Inverse(anchor.rotation);
            Vector3 Local(float[] p) => inv * (new Vector3(p[0], p[1], p[2]) - anchor.position);
            Vector3 LocalEuler(float[] q) => (inv * new Quaternion(q[0], q[1], q[2], q[3])).eulerAngles;

            var m = new MockSimulatedObject
            {
                id = dto.Id,
                category = so.Category,
                detectorLabel = so.Category.ToString().Replace('_', ' '),
                confidence = defaultConfidence,
                anchor = anchor,
                position = Local(dto.Position),
                rotation = LocalEuler(dto.Rotation),
                size = new Vector3(dto.Size[0], dto.Size[1], dto.Size[2]),
            };
            if (copyAttributesOnCapture)
                foreach (var kv in dto.Attributes)
                    m.attributes.Add(new MockAttribute
                {
                    key = kv.Key,
                    value = Convert.ToString(kv.Value.Value, CultureInfo.InvariantCulture)?.ToLowerInvariant(),
                    source = AttributeSourceKind.vlm,
                    confidence = defaultConfidence,
                });
            if (dto.PlaceZone != null)
            {
                m.hasPlaceZone = true;
                m.placeZoneCenter = Local(dto.PlaceZone.Center);
                m.placeZoneRotation = LocalEuler(dto.PlaceZone.Rotation);
                m.placeZoneSize = new Vector3(dto.PlaceZone.Size[0], dto.PlaceZone.Size[1], dto.PlaceZone.Size[2]);
            }
            if (dto.ApproachPoses != null)
                foreach (var p in dto.ApproachPoses)
                    m.approachPoses.Add(new MockPose { position = Local(p.Position), rotation = LocalEuler(p.Rotation) });
            objects.Add(m);
        }
        Debug.Log($"[MockSimulatedObjects] シーンから {objects.Count} 個の認識結果を作った", this);
#if UNITY_EDITOR
        UnityEditor.EditorUtility.SetDirty(this);
#endif
    }

    [Tooltip("「シーンの物体から認識結果を作る」で入れる確信度")]
    [Range(0f, 1f)] [SerializeField] float defaultConfidence = 0.9f;
    [Tooltip("「シーンの物体から認識結果を作る」で CoGroundSceneObject の属性も写す (写すとサーバーの VLM より優先される)")]
    [SerializeField] bool copyAttributesOnCapture = false;

    static object ParseValue(string s)
    {
        s = (s ?? "").Trim();
        if (bool.TryParse(s, out var b)) return b;
        if (float.TryParse(s, NumberStyles.Float, CultureInfo.InvariantCulture, out var f)) return f;
        return s;
    }

    // 認識結果の箱 (水色) と place_zone (黄色)。この GameObject を選んだときだけ
    void OnDrawGizmosSelected()
    {
        foreach (var o in objects)
        {
            if (!o.recognized) continue;
            Gizmos.color = new Color(0.2f, 0.85f, 1f, 0.9f);
            Gizmos.matrix = Matrix4x4.TRS(o.WorldPosition, o.WorldRotation, Vector3.one);
            Gizmos.DrawWireCube(Vector3.zero, o.size);
            if (o.hasPlaceZone)
            {
                var c = o.anchor != null ? o.anchor.position + o.anchor.rotation * o.placeZoneCenter : o.placeZoneCenter;
                var r = o.anchor != null ? o.anchor.rotation * Quaternion.Euler(o.placeZoneRotation) : Quaternion.Euler(o.placeZoneRotation);
                Gizmos.color = new Color(1f, 0.85f, 0.1f, 0.9f);
                Gizmos.matrix = Matrix4x4.TRS(c, r, Vector3.one);
                Gizmos.DrawWireCube(Vector3.zero, o.placeZoneSize);
            }
#if UNITY_EDITOR
            UnityEditor.Handles.Label(o.WorldPosition + Vector3.up * (o.size.y / 2f + 0.02f), $"{o.id} {o.confidence:0.00}");
#endif
        }
        Gizmos.matrix = Matrix4x4.identity;
    }
}
