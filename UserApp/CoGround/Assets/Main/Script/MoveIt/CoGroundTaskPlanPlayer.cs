using System;
using System.Collections.Generic;
using Newtonsoft.Json.Linq;
using RosMessageTypes.Std;
using Unity.Robotics.ROSTCPConnector;
using Unity.Robotics.ROSTCPConnector.ROSGeometry;
using UnityEngine;

/// <summary>
/// 動作計画 (Web UI の「Plan（動作計画）を作る」= motion.plan、ロボット単体テストの robot.plan) の結果を、
/// 半透明のロボット (Ghost) で通しで再生する。
/// 台車の移動 → ピック → 移動 → プレース を 1 本の時間軸として受け取り、画面下のシーケンスバーで
/// 再生・一時停止・好きな時刻へ移動 (行ったり来たり) ができる。運ぶ物の Ghost も、つかんでいる間は手に付いて動く。
///
///   pick_place_server ──/coground/task/plan_result (JSON)──▶ このスクリプト
///
/// ■ Ghost
///   見た目だけの Fetch (FetchGhostRig。Resources/FetchGhostModel) を使う。VR 上の Fetch (本物) は読まない・複製しない。
///   台車の位置・関節角はすべて計画の時間軸から決める (始まりの姿勢 = 時間軸の t=0 = 計画したときのロボットの位置)。
///   計画に含まれない関節 (頭など) だけは、計画を受け取ったときのロボットの関節角 (FetchRobotState = ROS の joint_states) を使う。
///
/// ■ Ghost の表示
///   Ghost は計画だけを見せる (半透明)。ロボットが実行している間 (/coground/skill/state の busy) は、Hide While Busy なら隠す。
///   今のロボットの見た目は、シミュレーションでは VR 上の Fetch (FetchRobotModeInfo)、本番では実物が担う。
///
/// ■ 使い方
///   ロボットのシーン (RosJointToFetch がある) なら、Play 開始時に自動で作られる (Auto Add)。シーンに置いてもよい。
///
/// ■ ほかのスクリプトから (VR の UI をつなぐときなど)
///   Instance、Seek(t) / Play() / Pause()、Time / Duration / CurrentPhase / HasPlan / TimelineChanged、Rig (Ghost)。
///
/// ■ 時間軸の形 (pick_place_server.py の docstring も参照。位置はすべて ROS の world = Unity の World を To&lt;FLU&gt; したもの)
///   timeline.base     [[t, x, y, yaw], ...]           base_link の位置
///   timeline.base_z   z                               base_link の高さ (無ければ今のロボットの高さ)
///   timeline.joints   [[t, v1, v2, ...], ...]         joint_names の順の関節角
///   timeline.attached [{object, t0, t1, link, pose}]  t0〜t1 の間、物体は link に付いている (pose は link から見た姿勢)
///   timeline.phases   [{step_id, phase, t0, t1}]
///   timeline.objects  [{object, start, rest}]         計画の始めの位置と、置いた後の位置
/// </summary>
public class CoGroundTaskPlanPlayer : MonoBehaviour
{
    [SerializeField] string resultTopic = "/coground/task/plan_result";
    [SerializeField] string skillStateTopic = "/coground/skill/state";

    [Header("Ghost")]
    [Tooltip("計画を再生するときの Ghost のマテリアル。未設定なら半透明の色から作る (Quest ビルドで表示されないときは指定する)")]
    [SerializeField] Material ghostMaterial;
    [SerializeField] Color ghostColor = new Color(0.3f, 0.7f, 1f, 0.35f);
    [SerializeField] Color objectGhostColor = new Color(1f, 0.75f, 0.2f, 0.45f);
    [Tooltip("ロボットが実行している間は Ghost を隠す")]
    [SerializeField] bool hideWhileBusy = true;

    [Header("再生")]
    [SerializeField] float playbackSpeed = 1f;
    [SerializeField] bool loop = true;
    [Tooltip("計画が届いたら最初から再生する")]
    [SerializeField] bool autoPlay = true;

    [Header("シーケンスバー (OnGUI)")]
    [SerializeField] bool showBar = true;
    [SerializeField] float barScale = 1.5f;

    static CoGroundTaskPlanPlayer instance;

    /// <summary>シーンの CoGroundTaskPlanPlayer (無ければ null)</summary>
    public static CoGroundTaskPlanPlayer Instance =>
        instance != null ? instance : (instance = FindAnyObjectByType<CoGroundTaskPlanPlayer>());

    // ---- Ghost ----
    FetchGhostRig rig;
    Material planMaterial, objectMaterial;
    bool visible;

    // ---- 時間軸 ----
    class Attach { public string obj, link; public float t0, t1; public Vector3 localPos; public Quaternion localRot; }
    class ObjectTrack { public string name; public Vector3 startPos, restPos; public Quaternion startRot, restRot; public bool hasRest; public Transform ghost; }
    public class Phase { public string StepId, Name; public float T0, T1; }

    float[] baseT; Vector3[] basePos; float[] baseYaw;
    float baseHeight;
    float[] jointT; float[][] jointV; string[] jointNames;
    readonly Dictionary<string, float> startJoints = new Dictionary<string, float>(); // 計画に含まれない関節の値
    readonly List<Attach> attaches = new List<Attach>();
    readonly List<ObjectTrack> objects = new List<ObjectTrack>();
    readonly List<Phase> phases = new List<Phase>();
    float duration;
    float time;
    bool playing;
    bool busy;
    string planLabel = "";

    public bool HasPlan => duration > 0f;
    public float Duration => duration;
    public float Time => time;
    public bool IsPlaying => playing;
    public IReadOnlyList<Phase> Phases => phases;
    public Phase CurrentPhase => phases.Find(p => time >= p.T0 && time <= p.T1);
    /// <summary>Ghost (見た目だけの Fetch)。Start の後で使える。Resources/FetchGhostModel が無ければ null</summary>
    public FetchGhostRig Rig => rig;
    /// <summary>新しい計画が届いた (無くなったときも)</summary>
    public event Action TimelineChanged;

    /// <summary>この時間軸を作った Plan の ID (無ければ空)</summary>
    public string PlanId { get; private set; } = "";
    /// <summary>true の間は Ghost を出さない (After で未来の環境を見せている間など)</summary>
    public bool Suppressed { get; set; }
    /// <summary>true なら、Suppressed でも Ghost を出す (Unity だけの計画: After を見ながら動きも見せる)</summary>
    public bool ShowWhileSuppressed { get; set; }
    /// <summary>true の間は Ghost を出さない (Unity だけの計画: 実行中は「今のロボット」だけを見せる)</summary>
    public bool Hidden { get; set; }
    /// <summary>false なら、ROS の計画結果 (/coground/task/plan_result) を使わない (Unity だけの計画: CoGroundUnityPlanner が SetTimeline で渡す)</summary>
    public bool UseRosResults { get; set; } = true;

    /// <summary>
    /// 再生する範囲 (秒)。end が start 以下なら全体。範囲の終わりまで行ったら範囲の始めへ戻る (loop のとき)。
    /// 「① の後」を見ている間は ① の動きだけを繰り返す、という使い方をする。
    /// </summary>
    public void SetPlayRange(float start, float end)
    {
        if (Mathf.Approximately(start, rangeStart) && Mathf.Approximately(end, rangeEnd)) return;
        rangeStart = start; rangeEnd = end;
        if (end > start && (time < start || time > end)) time = start;
    }
    float rangeStart, rangeEnd;

    /// <summary>Unity で作った時間軸 (CoGroundUnityPlanner)。位置・向きは Unity の World</summary>
    public class TimelineData
    {
        public string PlanId = "", Label = "";
        public float Duration;
        /// <summary>台車 (base_link) の位置と、ROS の yaw [rad] (= -Unity の Y 回りの角度)</summary>
        public List<float> BaseT = new List<float>();
        public List<Vector3> BasePos = new List<Vector3>();
        public List<float> BaseYaw = new List<float>();
        public float BaseHeight;
        public string[] JointNames = new string[0];
        public List<float> JointT = new List<float>();
        public List<float[]> JointV = new List<float[]>();
        /// <summary>時間軸に含まれない関節の値 (頭など)</summary>
        public Dictionary<string, float> StartJoints = new Dictionary<string, float>();
        public List<Phase> Phases = new List<Phase>();
        public List<ObjectData> Objects = new List<ObjectData>();
    }

    public class ObjectData
    {
        public string Name;
        public Vector3 StartPos, RestPos;
        public Quaternion StartRot = Quaternion.identity, RestRot = Quaternion.identity;
        /// <summary>T0〜T1 の間は Link に付いている (LocalPos / LocalRot は Link から見た bbox の中心の姿勢)</summary>
        public float T0, T1;
        public string Link = "gripper_link";
        public Vector3 LocalPos;
        public Quaternion LocalRot = Quaternion.identity;
        /// <summary>運ぶ物の Ghost (原点 = bbox の中心)。null なら箱を作る。Player が持ち主になる (消すのも Player)</summary>
        public Transform Ghost;
    }

    public enum ObjectStage { Before, Held, Done }

    /// <summary>Unity で作った時間軸を再生する (null なら消す)</summary>
    public void SetTimeline(TimelineData d)
    {
        Clear();
        if (d == null || d.Duration <= 0f) return;
        duration = d.Duration;
        baseT = d.BaseT.ToArray(); basePos = d.BasePos.ToArray(); baseYaw = d.BaseYaw.ToArray();
        baseHeight = d.BaseHeight;
        jointNames = d.JointNames;
        jointT = d.JointT.ToArray(); jointV = d.JointV.ToArray();
        startJoints.Clear();
        foreach (var kv in d.StartJoints) startJoints[kv.Key] = kv.Value;
        phases.AddRange(d.Phases);
        foreach (var o in d.Objects)
        {
            attaches.Add(new Attach { obj = o.Name, link = o.Link, t0 = o.T0, t1 = o.T1, localPos = o.LocalPos, localRot = o.LocalRot });
            var ghost = o.Ghost != null ? o.Ghost : MakeObjectGhost(o.Name);
            foreach (var r in ghost.GetComponentsInChildren<Renderer>()) r.enabled = false;
            objects.Add(new ObjectTrack
            {
                name = o.Name, startPos = o.StartPos, startRot = o.StartRot,
                restPos = o.RestPos, restRot = o.RestRot, hasRest = true, ghost = ghost,
            });
        }
        PlanId = d.PlanId ?? "";
        planLabel = d.Label ?? "";
        rangeStart = rangeEnd = 0f;
        time = 0f;
        playing = autoPlay;
        TimelineChanged?.Invoke();
    }

    /// <summary>時刻 t の姿勢 (台車と関節) を、別の Fetch (見た目だけ) に当てる</summary>
    public void ApplyTo(FetchGhostRig target, float t)
    {
        if (target == null || !HasPlan) return;
        target.SetJoints(startJoints);
        ApplyBase(target, t);
        ApplyJoints(target, t);
    }

    /// <summary>時刻 t の物体の姿勢 (bbox の中心)。Held のときは target の手に付いた姿勢。知らない物体は false</summary>
    public bool TryGetObjectPose(string objectName, float t, FetchGhostRig target, out ObjectStage stage, out Vector3 position, out Quaternion rotation)
    {
        stage = ObjectStage.Before; position = default; rotation = Quaternion.identity;
        foreach (var o in objects)
        {
            if (o.name != objectName) continue;
            stage = PoseOf(o, t, target, out position, out rotation);
            return true;
        }
        return false;
    }

    ObjectStage PoseOf(ObjectTrack o, float t, FetchGhostRig target, out Vector3 position, out Quaternion rotation)
    {
        Attach holding = null, done = null;
        foreach (var a in attaches)
        {
            if (a.obj != o.name) continue;
            if (t >= a.t0 && t <= a.t1) holding = a;
            else if (t > a.t1) done = a;
        }
        if (holding != null && target != null && target.TryGetLink(holding.link, out var link))
        {
            position = link.TransformPoint(holding.localPos); rotation = link.rotation * holding.localRot;
            return ObjectStage.Held;
        }
        if (done != null && o.hasRest) { position = o.restPos; rotation = o.restRot; return ObjectStage.Done; }
        position = o.startPos; rotation = o.startRot;
        return ObjectStage.Before;
    }

    /// <summary>
    /// 物体を置き終わった姿勢 (時間軸の最後。ワールド、bbox の中心)。
    /// objectName は Planning Scene の名前 (MoveItPickable.ObjectName)。運ばない物・無い物は false
    /// </summary>
    public bool TryGetRestPose(string objectName, out Vector3 position, out Quaternion rotation)
    {
        foreach (var o in objects)
            if (o.name == objectName && o.hasRest) { position = o.restPos; rotation = o.restRot; return true; }
        position = default; rotation = Quaternion.identity;
        return false;
    }

    public void Seek(float t) { time = Mathf.Clamp(t, 0f, duration); }
    public void Play() { if (HasPlan) playing = true; }
    public void Pause() { playing = false; }

    [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
    static void AutoAdd()
    {
        if (FindAnyObjectByType<CoGroundTaskPlanPlayer>() != null) return;
        // ロボットのシーンだけ (RosJointToFetch は目印に使うだけで、中身は読まない)
        if (FindAnyObjectByType<RosJointToFetch>(FindObjectsInactive.Include) == null) return;
        new GameObject("CoGround Task Plan Player").AddComponent<CoGroundTaskPlanPlayer>();
        Debug.Log("[CoGroundTaskPlanPlayer] 自動で作った (動作計画の通し再生)");
    }

    void Awake()
    {
        if (instance == null) instance = this;
    }

    void Start()
    {
        planMaterial = ghostMaterial != null ? ghostMaterial : FetchGhost.MakeMaterial(ghostColor);
        if (objectMaterial == null) objectMaterial = FetchGhost.MakeMaterial(objectGhostColor);
        rig = FetchGhostRig.Create("Task Plan Ghost", planMaterial);
        if (rig == null) { enabled = false; return; }

        _ = FetchRobotState.Instance; // 今のロボットの状態を受け取り始める
        var ros = ROSConnection.GetOrCreateInstance();
        ros.Subscribe<StringMsg>(resultTopic, OnResult);
        ros.Subscribe<StringMsg>(skillStateTopic, OnSkillState);
    }

    void OnDestroy()
    {
        if (rig != null) Destroy(rig.gameObject);
        ClearObjects();
        if (instance == this) instance = null;
    }

    // ------------------------------------------------------------------ 受け取る

    void OnSkillState(StringMsg msg)
    {
        try { busy = JObject.Parse(msg.data).Value<bool?>("busy") ?? false; }
        catch (Exception) { busy = false; }
    }

    void OnResult(StringMsg msg)
    {
        if (!UseRosResults) return;
        JObject root;
        try { root = JObject.Parse(msg.data); }
        catch (Exception e) { Debug.LogWarning($"[CoGroundTaskPlanPlayer] 計画の JSON が読めない: {e.Message}"); return; }

        var tl = root["timeline"] as JObject;
        string error = (string)root["error"] ?? "";
        if (tl == null || !string.IsNullOrEmpty(error))
        {
            if (!string.IsNullOrEmpty(error)) Debug.LogWarning($"[CoGroundTaskPlanPlayer] 計画できなかった: {error}");
            Clear();
            return;
        }
        try { Load(root, tl); }
        catch (Exception e)
        {
            Debug.LogError($"[CoGroundTaskPlanPlayer] 時間軸を読めない: {e}");
            Clear();
        }
    }

    void Clear()
    {
        duration = 0f; time = 0f; playing = false;
        rangeStart = rangeEnd = 0f;
        baseT = null; jointT = null;
        attaches.Clear(); phases.Clear();
        ClearObjects();
        planLabel = "";
        PlanId = "";
        TimelineChanged?.Invoke();
    }

    void ClearObjects()
    {
        foreach (var o in objects) if (o.ghost != null) Destroy(o.ghost.gameObject);
        objects.Clear();
    }

    static Vector3 RosPos(JToken p) => new Vector3<FLU>((float)p[0], (float)p[1], (float)p[2]).toUnity;
    static Quaternion RosRot(JToken q) =>
        q == null ? Quaternion.identity : new Quaternion<FLU>((float)q[0], (float)q[1], (float)q[2], (float)q[3]).toUnity;
    static Quaternion YawRot(float yaw) => new Quaternion<FLU>(0f, 0f, Mathf.Sin(yaw / 2f), Mathf.Cos(yaw / 2f)).toUnity;

    void Load(JObject root, JObject tl)
    {
        Clear();
        duration = (float)tl["duration"];

        var b = (JArray)tl["base"];
        baseT = new float[b.Count]; basePos = new Vector3[b.Count]; baseYaw = new float[b.Count];
        for (int i = 0; i < b.Count; i++)
        {
            baseT[i] = (float)b[i][0];
            basePos[i] = new Vector3<FLU>((float)b[i][1], (float)b[i][2], 0f).toUnity;
            baseYaw[i] = (float)b[i][3];
        }
        // 台車の高さ (ROS の z = Unity の y)。古い pick_place_server は送らないので、そのときは今のロボットの高さ
        if (tl["base_z"] != null && tl["base_z"].Type != JTokenType.Null) baseHeight = (float)tl["base_z"];
        else baseHeight = FetchRobotState.Instance.TryGetBasePose(out var p0, out _) ? p0.y : 0f;

        jointNames = tl["joint_names"].ToObject<string[]>();
        var j = (JArray)tl["joints"];
        jointT = new float[j.Count]; jointV = new float[j.Count][];
        for (int i = 0; i < j.Count; i++)
        {
            var row = (JArray)j[i];
            jointT[i] = (float)row[0];
            jointV[i] = new float[jointNames.Length];
            for (int k = 0; k < jointNames.Length && k + 1 < row.Count; k++) jointV[i][k] = (float)row[k + 1];
        }
        // 計画に含まれない関節 (頭など) は、計画を受け取ったときのロボットの値のままにする
        startJoints.Clear();
        foreach (var kv in FetchRobotState.Instance.Joints) startJoints[kv.Key] = kv.Value;

        foreach (var a in tl["attached"] ?? new JArray())
        {
            var pose = a["pose"];
            attaches.Add(new Attach
            {
                obj = (string)a["object"], link = (string)a["link"] ?? "gripper_link",
                t0 = (float)a["t0"], t1 = a["t1"] != null && a["t1"].Type != JTokenType.Null ? (float)a["t1"] : duration,
                // link から見た姿勢 (ROS) -> Unity のローカル。URDF Importer はリンクの軸を To<FLU> と同じ対応で作る
                localPos = RosPos(pose["position"]), localRot = RosRot(pose["orientation"]),
            });
        }
        foreach (var p in tl["phases"] ?? new JArray())
            phases.Add(new Phase { StepId = (string)p["step_id"], Name = (string)p["phase"], T0 = (float)p["t0"], T1 = (float)p["t1"] });

        foreach (var o in tl["objects"] ?? new JArray())
        {
            var track = new ObjectTrack
            {
                name = (string)o["object"],
                startPos = RosPos(o["start"]["position"]), startRot = RosRot(o["start"]["orientation"]),
                hasRest = o["rest"] != null && o["rest"].Type != JTokenType.Null,
            };
            if (track.hasRest) { track.restPos = RosPos(o["rest"]["position"]); track.restRot = RosRot(o["rest"]["orientation"]); }
            track.ghost = MakeObjectGhost(track.name);
            objects.Add(track);
        }

        int ok = 0, all = 0;
        foreach (var s in root["steps"] ?? new JArray()) { all++; if ((string)s["status"] == "ok") ok++; }
        PlanId = (string)root["plan_id"] ?? "";
        planLabel = $"{(string)root["plan_id"]} v{(int)root["plan_version"]} · ok {ok}/{all} step";
        time = 0f;
        playing = autoPlay;
        Debug.Log($"[CoGroundTaskPlanPlayer] 計画を受け取った: {planLabel}, {duration:F1} 秒");
        TimelineChanged?.Invoke();
    }

    Transform MakeObjectGhost(string objectName)
    {
        Vector3 size = Vector3.one * 0.1f;
        foreach (var p in MoveItPickable.All) if (p.ObjectName == objectName) { size = p.WorldSize; break; }
        var cube = GameObject.CreatePrimitive(PrimitiveType.Cube);
        cube.name = $"{objectName} (task plan)";
        Destroy(cube.GetComponent<Collider>());
        cube.transform.localScale = size;
        var r = cube.GetComponent<MeshRenderer>();
        if (objectMaterial == null) objectMaterial = FetchGhost.MakeMaterial(objectGhostColor);
        r.sharedMaterial = objectMaterial;
        r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
        r.enabled = false;
        return cube.transform;
    }

    // ------------------------------------------------------------------ 再生

    void Update()
    {
        if (playing && HasPlan)
        {
            bool ranged = rangeEnd > rangeStart;
            float lo = ranged ? Mathf.Clamp(rangeStart, 0f, duration) : 0f;
            float hi = ranged ? Mathf.Clamp(rangeEnd, lo, duration) : duration;
            time += UnityEngine.Time.deltaTime * playbackSpeed;
            if (time < lo) time = lo;
            if (time > hi)
            {
                if (loop) time = lo;
                else { time = hi; playing = false; }
            }
        }
        ApplyPose();
    }

    // Ghost を動かすのはここだけ
    void ApplyPose()
    {
        if (rig == null) return;
        bool show = HasPlan && !Hidden && (!Suppressed || ShowWhileSuppressed) && !(hideWhileBusy && busy);
        SetVisible(show);
        if (!show) return;
        rig.SetJoints(startJoints);
        ApplyBase(rig, time);
        ApplyJoints(rig, time);
    }

    void LateUpdate()
    {
        bool show = visible;
        foreach (var o in objects)
        {
            if (o.ghost == null) continue;
            foreach (var r in o.ghost.GetComponentsInChildren<Renderer>())
                if (r.enabled != show) r.enabled = show;
            if (!show) continue;
            PoseOf(o, time, rig, out var pos, out var rot);
            o.ghost.SetPositionAndRotation(pos, rot);
        }
    }

    void ApplyBase(FetchGhostRig rig, float t)
    {
        if (baseT == null || baseT.Length == 0) return;
        int i = Segment(baseT, t, out float a);
        int k = Mathf.Min(i + 1, baseT.Length - 1);
        Vector3 pos = Vector3.Lerp(basePos[i], basePos[k], a);
        pos.y = baseHeight;
        float yaw = baseYaw[i] + Mathf.DeltaAngle(baseYaw[i] * Mathf.Rad2Deg, baseYaw[k] * Mathf.Rad2Deg) * Mathf.Deg2Rad * a;
        rig.SetBasePose(pos, YawRot(yaw));
    }

    void ApplyJoints(FetchGhostRig rig, float t)
    {
        if (jointT == null || jointT.Length == 0 || jointNames.Length == 0) return;
        int i = Segment(jointT, t, out float a);
        int k = Mathf.Min(i + 1, jointT.Length - 1);
        for (int n = 0; n < jointNames.Length; n++)
            rig.SetJoint(jointNames[n], Mathf.Lerp(jointV[i][n], jointV[k][n], a));
    }

    /// <summary>times の中で t を挟む区間の始まり i と、その中での割合 a</summary>
    static int Segment(float[] times, float t, out float a)
    {
        int n = times.Length;
        if (t <= times[0] || n == 1) { a = 0f; return 0; }
        if (t >= times[n - 1]) { a = 1f; return Mathf.Max(0, n - 2); }
        int lo = 0, hi = n - 1;
        while (hi - lo > 1)
        {
            int mid = (lo + hi) / 2;
            if (times[mid] <= t) lo = mid; else hi = mid;
        }
        float span = times[hi] - times[lo];
        a = span > 1e-6f ? Mathf.Clamp01((t - times[lo]) / span) : 1f;
        return lo;
    }

    void SetVisible(bool show)
    {
        if (show == visible) return;
        visible = show;
        rig.Visible = show;
    }

    // ------------------------------------------------------------------ シーケンスバー

    public static readonly Dictionary<string, string> PhaseLabel = new Dictionary<string, string>
    {
        { "navigating", "Move" }, { "opening", "Open fingers" }, { "approaching", "Approach" }, { "descending", "Lower hand" },
        { "grasping", "Grasp" }, { "lifting", "Lift" }, { "moving", "Over placement" }, { "lowering", "Lower" },
        { "releasing", "Release" }, { "retreating", "Retreat" },
    };
    static readonly HashSet<string> PickPhases = new HashSet<string> { "opening", "approaching", "descending", "grasping", "lifting" };

    void OnGUI()
    {
        if (!showBar || !HasPlan) return;
        GUI.matrix = Matrix4x4.Scale(new Vector3(barScale, barScale, 1f));
        float w = Screen.width / barScale, h = Screen.height / barScale;
        var area = new Rect(10, h - 84, w - 20, 74);
        GUI.Box(area, GUIContent.none);

        GUILayout.BeginArea(new Rect(area.x + 6, area.y + 4, area.width - 12, 26));
        GUILayout.BeginHorizontal();
        if (GUILayout.Button(playing ? "❚❚" : "▶", GUILayout.Width(36))) { if (playing) Pause(); else Play(); }
        var phase = CurrentPhase;
        string phaseText = phase != null ? $"{phase.StepId}: {(PhaseLabel.TryGetValue(phase.Name, out var l) ? l : phase.Name)}" : "";
        GUILayout.Label($"{time:F1} / {duration:F1} s   {phaseText}", GUILayout.Width(260));
        GUILayout.Label(planLabel + (busy && hideWhileBusy ? "  (hidden while executing)" : ""));
        GUILayout.EndHorizontal();
        GUILayout.EndArea();

        // 区切りの帯 (クリックでその区切りの始まりへ)
        var strip = new Rect(area.x + 6, area.y + 32, area.width - 12, 12);
        var old = GUI.color;
        foreach (var p in phases)
        {
            var r = new Rect(strip.x + strip.width * p.T0 / duration, strip.y, Mathf.Max(1f, strip.width * (p.T1 - p.T0) / duration), strip.height);
            GUI.color = p.Name == "navigating" ? new Color(0.45f, 0.5f, 0.6f) : PickPhases.Contains(p.Name) ? new Color(0.25f, 0.5f, 1f) : new Color(0.2f, 0.7f, 0.35f);
            GUI.DrawTexture(r, Texture2D.whiteTexture);
            if (UnityEngine.Event.current.type == EventType.MouseDown && r.Contains(UnityEngine.Event.current.mousePosition))
            {
                Seek(p.T0);
                UnityEngine.Event.current.Use();
            }
        }
        GUI.color = Color.white;
        GUI.DrawTexture(new Rect(strip.x + strip.width * time / duration - 1, strip.y - 2, 2, strip.height + 4), Texture2D.whiteTexture);
        GUI.color = old;

        // つまみ (動かすと一時停止してその時刻へ)
        float t = GUI.HorizontalSlider(new Rect(area.x + 6, area.y + 50, area.width - 12, 16), time, 0f, duration);
        if (!Mathf.Approximately(t, time)) { Pause(); Seek(t); }
    }
}
