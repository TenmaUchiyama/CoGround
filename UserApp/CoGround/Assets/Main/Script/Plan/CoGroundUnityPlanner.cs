using System;
using System.Collections.Generic;
using Newtonsoft.Json.Linq;
using UnityEngine;

/// <summary>
/// Unity だけの動作計画 (ROS / MoveIt を使わない、デモ用の簡単な計画)。
/// サーバーの Plan (どの物をどこへ) から、「台車の移動 → ピック → 移動 → プレース」の時間軸を Unity の中で作り、
/// CoGroundTaskPlanPlayer の Ghost で再生する。実行 (Execute this plan) のときは、同じ時間軸で「今のロボット」と本物の物体を動かす。
///
///   サーバー (state.updated の plan / motion.preview / execution) ──▶ このスクリプト ──SetTimeline──▶ CoGroundTaskPlanPlayer
///
/// ■ 前提: サーバーは代役のロボット (FakeRobot) で動かす
///   サーバーの .env から COGROUND_ROSBRIDGE_URL を外す (無ければ FakeRobot になり、ROS は呼ばれない)。
///   step が運べるか (move / stay_…) はサーバーの motion.preview のまま使う。ここでは「move」の step だけを動かす。
///   実行の速さを合わせるには、サーバーの COGROUND_FAKE_PHASE_DELAY を Arm Phase Seconds と同じ値にする (例: 1.5)。
///
/// ■ 計画の中身 (失敗は考えない。届かない・ぶつかる、は今は見ない)
///   - 止まる位置: 家具の CoGroundApproachPoint (目標に近いもの)。無ければ物体の手前 Standoff の位置を自動で選ぶ
///   - 台車の経路: BaseNavPlanner (コライダーを避ける A*)。道が無ければ直線
///   - 腕: 真上からつかむ姿勢を、Ghost の関節を数値的に解いて (IK) 作る。解けなくても一番近い姿勢で続ける
///   - phase の名前と順番は ROS の pick_place_server と同じ (navigating / opening / approaching / … / retreating)
///
/// ■ ロボット
///   「今のロボット」は、見た目だけの Fetch (FetchGhostRig。不透明) をこのスクリプトが持つ。
///   始まりの位置はシーンの Fetch (RosJointToFetch が付いたもの) の base_link。Hide Scene Fetch ならシーンの Fetch は隠す
///   (ROS が無いと動かないので)。実行が終わると、今のロボットは最後の位置に残り、次の計画はそこから始まる。
///
/// ■ 表示
///   Ghost は計画を繰り返し再生する。CoGroundSequencePanel で「After 2」を選んでいる間は、② の動きだけを繰り返す。
///   Show Ghost In After = false なら、After のあいだは Ghost を隠す (もとの動き)。
///
/// ■ 使い方
///   CoGroundServerClient があるシーンなら、Play 開始時に自動で作られる (AutoAddEnabled = false で止められる)。シーンに置いてもよい。
/// </summary>
[DefaultExecutionOrder(50)]
public class CoGroundUnityPlanner : MonoBehaviour
{
    /// <summary>false にすると自動では作らない (ROS の計画に戻すとき)</summary>
    public static bool AutoAddEnabled = true;

    [SerializeField] CoGroundServerClient client;

    [Header("台車")]
    [SerializeField] float linearSpeed = 0.5f;
    [Tooltip("[rad/s]")]
    [SerializeField] float angularSpeed = 1.2f;
    [SerializeField] float robotRadius = 0.28f;
    [Tooltip("止まる位置 (CoGroundApproachPoint) が無いとき、物体からこの距離だけ手前に止まる [m]")]
    [SerializeField] float standoff = 0.65f;

    [Header("腕")]
    [Tooltip("腕の phase 1 つの長さ [s]。サーバーの COGROUND_FAKE_PHASE_DELAY と同じにすると、実行のときに速さが合う")]
    [SerializeField] float armPhaseSeconds = 1.5f;
    [Tooltip("つかむ前・置く前に、手を物体の上のこの高さで止める [m]")]
    [SerializeField] float hoverHeight = 0.12f;
    [Tooltip("入れ物 (ごみ箱・箱など) に入れるとき、入れ物の上面からこの高さで離す [m]")]
    [SerializeField] float dropHeight = 0.05f;

    [Header("表示")]
    [Tooltip("シーンの Fetch (RosJointToFetch) を隠して、見た目だけの Fetch を今のロボットとして見せる")]
    [SerializeField] bool hideSceneFetch = true;
    [Tooltip("After を見ている間も、計画の Ghost を再生する")]
    [SerializeField] bool showGhostInAfter = true;
    [SerializeField] Color objectGhostColor = new Color(1f, 0.75f, 0.2f, 0.45f);

    [Header("実行")]
    [Tooltip("サーバーの進み方に遅れたとき、最大で何倍速まで上げて追いつくか")]
    [SerializeField] float maxCatchUpSpeed = 8f;

    // 時間軸に入れる関節: 胴 + 腕 7 つ (IK で解く) + 指 2 つ
    static readonly string[] JointNames =
    {
        "torso_lift_joint", "shoulder_pan_joint", "shoulder_lift_joint", "upperarm_roll_joint",
        "elbow_flex_joint", "forearm_roll_joint", "wrist_flex_joint", "wrist_roll_joint",
        "l_gripper_finger_joint", "r_gripper_finger_joint",
    };
    const int ArmDof = 8, LeftFinger = 8, RightFinger = 9;
    static readonly float[] Lower = { 0f, -1.6056f, -1.221f, -6.283f, -2.251f, -6.283f, -2.16f, -6.283f };
    static readonly float[] Upper = { 0.386f, 1.6056f, 1.518f, 6.283f, 2.251f, 6.283f, 2.16f, 6.283f };
    // たたんだ姿勢 (Fetch の tuck) と、手を下に向けて前に出した姿勢 (IK の出発点、運ぶときの姿勢)
    static readonly float[] Tuck = { 0.05f, 1.32f, 1.40f, -0.2f, 1.72f, 0f, 1.66f, 0f, 0f, 0f };
    static readonly float[] Ready = { 0.2f, 0f, -0.4f, 0f, 1.1f, 0f, 0.87f, 0f, 0f, 0f };
    const float FingerOpen = 0.05f;
    const string GripperLink = "gripper_link";

    CoGroundServerClient Client => client != null ? client : CoGroundServerClient.Instance;
    CoGroundServerClient subscribed;
    CoGroundTaskPlanPlayer player;
    CoGroundAfterView afterView;
    JObject state;
    bool dirty;
    string builtKey;

    // ---- ロボット ----
    FetchGhostRig robotRig;   // 今のロボット (不透明)
    FetchGhostRig solver;     // IK を解くための見えない Fetch
    Transform sceneFetch;
    Vector3 robotPos;
    float robotYaw;           // Unity の Y 回りの角度 [deg]
    float[] robotQ = (float[])Tuck.Clone();
    readonly BaseNavPlanner nav = new BaseNavPlanner();
    Material objectMaterial;

    // ---- いまの時間軸 ----
    class ExecPhase { public string obj, name; public float t0, t1; public bool carrying; }
    CoGroundTaskPlanPlayer.TimelineData timeline;
    readonly List<ExecPhase> execPhases = new List<ExecPhase>();
    readonly Dictionary<int, Vector2> stepRanges = new Dictionary<int, Vector2>(); // step の番号 -> (t0, t1)
    readonly Dictionary<int, Vector2> pickRanges = new Dictionary<int, Vector2>(); // step の番号 -> 取りに行く〜持ち上げるまで (t0, t1)
    readonly Dictionary<string, string> trackNames = new Dictionary<string, string>(); // 物体の ID -> 時間軸での名前

    /// <summary>
    /// Before で、この番号の step の「取りに行く → つかむ → 持ち上げる」だけを繰り返している (-1 = 全体を再生)。
    /// 物体の吹き出しを押すと切り替わる (CoGroundRuleTagView)。After に切り替える・計画が変わる・実行を始める、で -1 に戻る。
    /// </summary>
    public int FocusStep { get; private set; } = -1;
    /// <summary>FocusStep が変わった</summary>
    public event Action FocusChanged;

    /// <summary>この step の「つかむところ」を再生できるか (この順番で運べると検証できた step だけ)</summary>
    public bool CanFocus(int stepIndex) => !executing && pickRanges.ContainsKey(stepIndex);

    /// <summary>同じ step をもう一度選ぶと、全体の再生に戻る</summary>
    public void ToggleFocus(int stepIndex) => SetFocus(FocusStep == stepIndex ? -1 : stepIndex);

    public void SetFocus(int stepIndex)
    {
        if (stepIndex >= 0 && !CanFocus(stepIndex)) stepIndex = -1;
        if (stepIndex == FocusStep) return;
        FocusStep = stepIndex;
        if (stepIndex >= 0 && player != null)
        {
            // 選んだら、その動きの最初から見せる (一時停止していても再生する)
            var range = pickRanges[stepIndex];
            player.SetPlayRange(range.x, range.y);
            player.Seek(range.x);
            player.Play();
        }
        FocusChanged?.Invoke();
    }

    // ---- 実行 ----
    bool executing;
    float execTime, execTarget, lastObjectEnd;
    string lastSkill;
    readonly HashSet<string> placed = new HashSet<string>();
    readonly Dictionary<Rigidbody, bool> kinematicBefore = new Dictionary<Rigidbody, bool>();

    /// <summary>Unity の計画で実行を再生している</summary>
    public bool IsExecuting => executing;

    [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
    static void AutoAdd()
    {
        if (!AutoAddEnabled) return;
        if (FindAnyObjectByType<CoGroundUnityPlanner>() != null) return;
        if (FindAnyObjectByType<CoGroundServerClient>() == null) return;
        if (Resources.Load<FetchGhostRig>(FetchGhostRig.ResourceName) == null) return;
        new GameObject("CoGround Unity Planner").AddComponent<CoGroundUnityPlanner>();
        Debug.Log("[CoGroundUnityPlanner] 自動で作った (Unity だけの動作計画)");
    }

    void Awake()
    {
        // AfterView などが Start で Player を探すので、先に用意する
        player = CoGroundTaskPlanPlayer.Instance;
        if (player == null) player = new GameObject("CoGround Task Plan Player").AddComponent<CoGroundTaskPlanPlayer>();
        player.UseRosResults = false;
        player.ShowWhileSuppressed = showGhostInAfter;
    }

    void Start()
    {
        FindSceneFetch();
        solver = FetchGhostRig.Create("Unity Planner IK (hidden)", null);
        robotRig = FetchGhostRig.Create("Fetch (Unity plan)", null);
        if (solver == null || robotRig == null) { enabled = false; return; }
        robotRig.Visible = true;
        PoseRobotRig();

        nav.RobotRadius = robotRadius;
        nav.Ignore = sceneFetch;

        subscribed = Client;
        if (subscribed == null) { Debug.LogWarning("[CoGroundUnityPlanner] CoGroundServerClient が見つからない", this); return; }
        subscribed.StateUpdated += OnStateUpdated;
        if (subscribed.LatestState != null) OnStateUpdated(subscribed.LatestState);
    }

    void OnDestroy()
    {
        if (subscribed != null) subscribed.StateUpdated -= OnStateUpdated;
        if (robotRig != null) Destroy(robotRig.gameObject);
        if (solver != null) Destroy(solver.gameObject);
        if (objectMaterial != null) Destroy(objectMaterial);
    }

    void OnStateUpdated(JObject s)
    {
        state = s;
        dirty = true;
    }

    /// <summary>始まりの位置をシーンの Fetch から決める。Hide Scene Fetch なら隠す</summary>
    void FindSceneFetch()
    {
        var joint = FindAnyObjectByType<RosJointToFetch>(FindObjectsInactive.Include);
        var info = joint == null ? FindAnyObjectByType<FetchRobotModeInfo>(FindObjectsInactive.Include) : null;
        sceneFetch = joint != null ? joint.transform : info != null ? info.transform : null;
        if (sceneFetch == null)
        {
            robotPos = transform.position;
            robotYaw = YawOf(transform.forward, 0f);
            return;
        }
        Transform baseLink = sceneFetch;
        foreach (var t in sceneFetch.GetComponentsInChildren<Transform>(true))
            if (t.name == "base_link") { baseLink = t; break; }
        robotPos = baseLink.position;
        robotYaw = YawOf(baseLink.forward, 0f);
        if (!hideSceneFetch) return;
        foreach (var r in sceneFetch.GetComponentsInChildren<Renderer>(true)) r.enabled = false;
        foreach (var c in sceneFetch.GetComponentsInChildren<Collider>(true)) c.enabled = false;
        Debug.Log($"[CoGroundUnityPlanner] シーンの Fetch ({sceneFetch.name}) を隠し、見た目だけの Fetch を今のロボットにした");
    }

    // ------------------------------------------------------------------ 毎フレーム

    void Update()
    {
        if (player == null || robotRig == null) return;
        player.ShowWhileSuppressed = showGhostInAfter;

        var execution = state?["execution"] as JObject;
        bool serverRunning = (string)execution?["mode"] == "running";
        if (serverRunning && !executing && timeline != null) BeginExecution();

        if (executing)
        {
            StepExecution(execution, serverRunning);
            return;
        }

        if (dirty)
        {
            dirty = false;
            Rebuild();
        }
        PoseRobotRig();
        UpdatePlayRange();
    }

    void PoseRobotRig()
    {
        for (int i = 0; i < JointNames.Length; i++) robotRig.SetJoint(JointNames[i], robotQ[i]);
        robotRig.SetBasePose(robotPos, Quaternion.Euler(0f, robotYaw, 0f));
    }

    /// <summary>
    /// 「After N」を見ている間は、その step の動きだけを繰り返す。
    /// Before で step を選んでいる間 (FocusStep) は、その step の「取りに行く → つかむ → 持ち上げる」だけを繰り返す
    /// </summary>
    void UpdatePlayRange()
    {
        if (afterView == null) afterView = FindAnyObjectByType<CoGroundAfterView>();
        bool after = afterView != null && afterView.isActiveAndEnabled && afterView.Mode == CoGroundAfterView.ViewMode.After;
        if (after && FocusStep >= 0) SetFocus(-1); // Before に戻ったときは全体の再生から
        if (after && stepRanges.TryGetValue(afterView.ViewStep, out var range))
            player.SetPlayRange(range.x, range.y);
        else if (FocusStep >= 0 && pickRanges.TryGetValue(FocusStep, out var pick))
            player.SetPlayRange(pick.x, pick.y);
        else
            player.SetPlayRange(0f, 0f);
    }

    // ------------------------------------------------------------------ 計画を作る

    void Rebuild()
    {
        var plan = CoGroundFuture.ReadPlan(state);
        var moves = new List<StepDto>();
        if (plan != null)
            foreach (var step in plan.Steps)
                if (step.To?.Pose != null && CoGroundFuture.StateOf(state, plan, step, out _) == CoGroundFuture.StepState.Move)
                    moves.Add(step);
        moves.Sort((a, b) => a.Index.CompareTo(b.Index));

        var key = $"{Round(robotPos)}|{Mathf.Round(robotYaw)}";
        foreach (var m in moves)
            key += $"|{m.Index}:{m.ObjectId}:{Round(m.From?.Pose != null ? m.From.Pose.PositionV : Vector3.zero)}:{Round(m.To.Pose.PositionV)}:{m.To.RegionId}";
        if (key == builtKey) return;
        builtKey = key;

        timeline = null;
        execPhases.Clear();
        stepRanges.Clear();
        pickRanges.Clear();
        trackNames.Clear();
        SetFocus(-1); // 計画が変わると、同じ番号が別の物を指すことがある
        if (moves.Count == 0) { player.SetTimeline(null); return; }

        try
        {
            timeline = Build(plan, moves);
            player.SetTimeline(timeline);
            Debug.Log($"[CoGroundUnityPlanner] 計画を作った: {timeline.Label}, {timeline.Duration:F1} 秒");
        }
        catch (Exception e)
        {
            Debug.LogError($"[CoGroundUnityPlanner] 計画を作れなかった: {e}");
            timeline = null;
            player.SetTimeline(null);
        }
    }

    static string Round(Vector3 v) => $"{Mathf.Round(v.x * 100f)},{Mathf.Round(v.y * 100f)},{Mathf.Round(v.z * 100f)}";

    // 時間軸を作っている途中の状態
    float t;
    Vector3 pos;
    float yaw;
    float[] q;
    CoGroundTaskPlanPlayer.TimelineData d;

    CoGroundTaskPlanPlayer.TimelineData Build(PlanDto plan, List<StepDto> moves)
    {
        d = new CoGroundTaskPlanPlayer.TimelineData
        {
            PlanId = plan.Id, Label = $"Unity plan · {moves.Count} step", BaseHeight = robotPos.y, JointNames = JointNames,
        };
        t = 0f; pos = robotPos; yaw = robotYaw; q = (float[])robotQ.Clone();
        AddBaseKey();
        AddJointKey();

        foreach (var step in moves)
        {
            float stepStart = t;
            var obj = CoGroundSceneObject.Find(step.ObjectId);

            // 物体のいまの姿勢 (bbox の中心) と大きさ
            Vector3 center, size = Vector3.one * 0.08f;
            Quaternion rotation;
            if (obj != null)
            {
                var dto = obj.ToDto();
                center = new Vector3(dto.Position[0], dto.Position[1], dto.Position[2]);
                rotation = new Quaternion(dto.Rotation[0], dto.Rotation[1], dto.Rotation[2], dto.Rotation[3]);
                if (dto.Size != null && dto.Size.Length == 3) size = new Vector3(dto.Size[0], dto.Size[1], dto.Size[2]);
            }
            else if (step.From?.Pose != null) { center = step.From.Pose.PositionV; rotation = step.From.Pose.RotationQ; }
            else continue;
            Vector3 restCenter = step.To.Pose.PositionV;
            Quaternion restRotation = step.To.Pose.RotationQ;
            float finger = Mathf.Clamp(Mathf.Min(size.x, size.z) / 2f - 0.005f, 0f, FingerOpen);

            // ---- 取りに行く ----
            ChooseStop(center, step.From?.RegionId, out var stopPos, out var stopYaw);
            Drive(stopPos, stopYaw, step, false);

            // 真上からつかむ: 物体の上面から 4 cm 下 (背の低い物は中心) を手の中心にする
            Vector3 grasp = center + Vector3.up * Mathf.Max(0f, size.y / 2f - 0.04f);
            Quaternion baseRot = Quaternion.Euler(0f, yaw, 0f);
            Quaternion down = Quaternion.LookRotation(Vector3.down, baseRot * Vector3.forward);
            var qPre = SolveArm(pos, baseRot, grasp + Vector3.up * hoverHeight, down, Ready, step.ObjectId + " pre-grasp");
            var qGrasp = SolveArm(pos, baseRot, grasp, down, qPre, step.ObjectId + " grasp");

            // つかんだ瞬間の、手から見た物体の姿勢 (運んでいる間はこれで手に付ける)
            SetSolver(pos, baseRot, qGrasp);
            solver.TryGetLink(GripperLink, out var tip);
            Vector3 localPos = tip.InverseTransformPoint(center);
            Quaternion localRot = Quaternion.Inverse(tip.rotation) * rotation;

            ArmPhase(step, "opening", WithFingers(Ready, FingerOpen));
            ArmPhase(step, "approaching", WithFingers(qPre, FingerOpen));
            ArmPhase(step, "descending", WithFingers(qGrasp, FingerOpen));
            ArmPhase(step, "grasping", WithFingers(qGrasp, finger));
            float attachStart = t;
            ArmPhase(step, "lifting", WithFingers(qPre, finger), WithFingers(Ready, finger));
            pickRanges[step.Index] = new Vector2(stepStart, t);

            // ---- 置きに行く ----
            ChooseStop(restCenter, step.To.RegionId, out stopPos, out stopYaw);
            Drive(stopPos, stopYaw, step, true);

            // 入れ物 (ごみ箱・箱など) には上から落とす。机・棚にはそっと置く
            Vector3 release = restCenter;
            var place = CoGroundSceneObject.Find(step.To.RegionId);
            if (place != null && place.PlaceZone != null
                && place.Category != CoGroundCategory.table && place.Category != CoGroundCategory.shelf)
            {
                float top = place.PlaceZone.position.y + Mathf.Abs(place.PlaceZone.lossyScale.y) / 2f;
                release.y = Mathf.Max(release.y, top + size.y / 2f + dropHeight);
            }
            baseRot = Quaternion.Euler(0f, yaw, 0f);
            // 置いたときの物体の向きが Plan の向きになる手の向き。真下向きから大きく外れるなら、真下向きのまま置く
            Quaternion tipRot = restRotation * Quaternion.Inverse(localRot);
            if (Vector3.Angle(tipRot * Vector3.forward, Vector3.down) > 20f)
                tipRot = Quaternion.LookRotation(Vector3.down, baseRot * Vector3.forward);
            Vector3 tipPos = release - tipRot * localPos;
            var qPrePlace = SolveArm(pos, baseRot, tipPos + Vector3.up * hoverHeight, tipRot, Ready, step.ObjectId + " pre-place");
            var qPlace = SolveArm(pos, baseRot, tipPos, tipRot, qPrePlace, step.ObjectId + " place");

            ArmPhase(step, "moving", WithFingers(qPrePlace, finger));
            ArmPhase(step, "lowering", WithFingers(qPlace, finger));
            ArmPhase(step, "releasing", WithFingers(qPlace, FingerOpen));
            float attachEnd = t;
            ArmPhase(step, "retreating", WithFingers(qPrePlace, FingerOpen), Tuck);

            var pickable = obj != null ? obj.GetComponent<MoveItPickable>() : null;
            string trackName = pickable != null ? pickable.ObjectName : step.ObjectId; // CoGroundFuture.TryFinalPose と同じ名前
            trackNames[step.ObjectId] = trackName;
            d.Objects.Add(new CoGroundTaskPlanPlayer.ObjectData
            {
                Name = trackName, StartPos = center, StartRot = rotation, RestPos = restCenter, RestRot = restRotation,
                T0 = attachStart, T1 = attachEnd, Link = GripperLink, LocalPos = localPos, LocalRot = localRot,
                Ghost = MakeObjectGhost(obj, center, rotation),
            });
            stepRanges[step.Index] = new Vector2(stepStart, t);
        }

        AddBaseKey();
        AddJointKey();
        d.Duration = t;
        return d;
    }

    void AddBaseKey()
    {
        d.BaseT.Add(t);
        d.BasePos.Add(pos);
        d.BaseYaw.Add(-yaw * Mathf.Deg2Rad); // ROS の yaw
    }

    void AddJointKey()
    {
        d.JointT.Add(t);
        d.JointV.Add((float[])q.Clone());
    }

    static float[] WithFingers(float[] arm, float finger)
    {
        var r = (float[])arm.Clone();
        r[LeftFinger] = r[RightFinger] = finger;
        return r;
    }

    /// <summary>腕の phase 1 つ。via があれば、前半で via、後半で target へ</summary>
    void ArmPhase(StepDto step, string name, float[] target, float[] then = null)
    {
        float t0 = t;
        if (then == null)
        {
            t += armPhaseSeconds; q = target; AddJointKey();
        }
        else
        {
            t += armPhaseSeconds / 2f; q = target; AddJointKey();
            t += armPhaseSeconds / 2f; q = then; AddJointKey();
        }
        AddPhase(step, name, t0, false);
    }

    void AddPhase(StepDto step, string name, float t0, bool carrying)
    {
        d.Phases.Add(new CoGroundTaskPlanPlayer.Phase { StepId = step.Id, Name = name, T0 = t0, T1 = t });
        execPhases.Add(new ExecPhase { obj = step.ObjectId, name = name, t0 = t0, t1 = t, carrying = carrying });
    }

    /// <summary>台車を goal まで動かす (向きを変える → 進む、を折れ線の辺ごとに。最後に goalYaw を向く)</summary>
    void Drive(Vector3 goal, float goalYaw, StepDto step, bool carrying)
    {
        float t0 = t;
        AddBaseKey();  // ここまでは止まっている
        AddJointKey();
        goal.y = pos.y;
        var path = new List<Vector3>();
        if (Vector3.Distance(pos, goal) > 0.01f)
        {
            if (!nav.TryPlan(pos, goal, path, out var error))
            {
                Debug.LogWarning($"[CoGroundUnityPlanner] {step.ObjectId}: 台車の道が見つからない ({error})。直線で動かす");
                path.Clear();
                path.Add(pos);
                path.Add(goal);
            }
        }
        for (int i = 1; i < path.Count; i++)
        {
            Vector3 seg = path[i] - pos;
            seg.y = 0f;
            if (seg.magnitude < 0.01f) continue;
            Turn(YawOf(seg, yaw));
            t += seg.magnitude / Mathf.Max(0.05f, linearSpeed);
            pos = new Vector3(path[i].x, pos.y, path[i].z);
            AddBaseKey();
        }
        Turn(goalYaw);
        AddBaseKey();
        AddJointKey(); // 動いている間、腕はそのまま
        AddPhase(step, "navigating", t0, carrying);
    }

    void Turn(float toYaw)
    {
        float delta = Mathf.Abs(Mathf.DeltaAngle(yaw, toYaw));
        yaw = toYaw;
        if (delta < 0.5f) return;
        t += delta * Mathf.Deg2Rad / Mathf.Max(0.05f, angularSpeed);
        AddBaseKey();
    }

    /// <summary>水平の向き → Unity の Y 回りの角度 [deg]。向きが決まらなければ fallback</summary>
    static float YawOf(Vector3 direction, float fallback)
    {
        direction.y = 0f;
        return direction.sqrMagnitude < 1e-8f ? fallback : Mathf.Atan2(direction.x, direction.z) * Mathf.Rad2Deg;
    }

    /// <summary>
    /// target (物体や置き位置) で作業するときに台車が止まる位置と向き。
    /// 家具 (regionId と同じ ID の CoGroundSceneObject) に CoGroundApproachPoint があれば、target に近いもの。
    /// 無ければ、target からロボット側へ Standoff だけ離れた位置 (ぶつかるなら、まわりを順に探す)。
    /// </summary>
    void ChooseStop(Vector3 target, string regionId, out Vector3 stopPos, out float stopYaw)
    {
        var furniture = string.IsNullOrEmpty(regionId) ? null : CoGroundSceneObject.Find(regionId);
        if (furniture != null)
        {
            CoGroundApproachPoint best = null;
            float bestDistance = float.PositiveInfinity;
            foreach (var a in furniture.ApproachPoints)
            {
                if (!a.isActiveAndEnabled) continue;
                Vector3 delta = a.transform.position - target;
                delta.y = 0f;
                if (delta.magnitude < bestDistance) { bestDistance = delta.magnitude; best = a; }
            }
            if (best != null)
            {
                stopPos = new Vector3(best.transform.position.x, pos.y, best.transform.position.z);
                stopYaw = YawOf(best.transform.forward, yaw);
                return;
            }
        }

        Vector3 toTarget = target - pos;
        toTarget.y = 0f;
        float facing = YawOf(toTarget, yaw);
        Vector3 flat = new Vector3(target.x, pos.y, target.z);
        if (toTarget.magnitude <= standoff + 0.05f && toTarget.magnitude >= 0.4f)
        {
            // もう届く位置にいる: 向きだけ変える
            stopPos = pos; stopYaw = facing;
            return;
        }
        stopPos = flat - Quaternion.Euler(0f, facing, 0f) * Vector3.forward * standoff;
        stopYaw = facing;
        foreach (float offset in new[] { 0f, 45f, -45f, 90f, -90f, 135f, -135f, 180f })
        {
            float a = facing + offset;
            Vector3 candidate = flat - Quaternion.Euler(0f, a, 0f) * Vector3.forward * standoff;
            if (!BaseFits(candidate)) continue;
            stopPos = candidate; stopYaw = a;
            return;
        }
    }

    bool BaseFits(Vector3 p)
    {
        float r = robotRadius;
        var hits = Physics.OverlapCapsule(p + Vector3.up * (0.05f + r), p + Vector3.up * Mathf.Max(1.2f - r, 0.05f + r), r, ~0,
                                          QueryTriggerInteraction.Ignore);
        foreach (var h in hits)
        {
            if (sceneFetch != null && h.transform.IsChildOf(sceneFetch)) continue;
            return false;
        }
        return true;
    }

    /// <summary>運ぶ物の Ghost: 物体の見た目の半透明コピー (原点 = bbox の中心)。メッシュが無ければ null (Player が箱を作る)</summary>
    Transform MakeObjectGhost(CoGroundSceneObject obj, Vector3 center, Quaternion rotation)
    {
        if (obj == null) return null;
        if (objectMaterial == null) objectMaterial = FetchGhost.MakeMaterial(objectGhostColor);
        var root = new GameObject($"{obj.Id} (plan ghost)");
        root.transform.SetPositionAndRotation(center, rotation);
        Matrix4x4 inverse = root.transform.worldToLocalMatrix;
        // After のあいだは物体の Renderer が切られている (Diminish) ので、enabled は見ない
        foreach (var renderer in obj.GetComponentsInChildren<MeshRenderer>(true))
        {
            var filter = renderer.GetComponent<MeshFilter>();
            if (filter == null || filter.sharedMesh == null) continue;
            var go = new GameObject(renderer.name);
            go.transform.SetParent(root.transform, false);
            Matrix4x4 rel = inverse * renderer.transform.localToWorldMatrix;
            go.transform.localPosition = rel.GetPosition();
            go.transform.localRotation = rel.rotation;
            go.transform.localScale = rel.lossyScale;
            go.AddComponent<MeshFilter>().sharedMesh = filter.sharedMesh;
            var r = go.AddComponent<MeshRenderer>();
            var mats = new Material[renderer.sharedMaterials.Length];
            for (int i = 0; i < mats.Length; i++) mats[i] = objectMaterial;
            r.sharedMaterials = mats;
            r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            r.receiveShadows = false;
        }
        if (root.transform.childCount == 0) { Destroy(root); return null; }
        return root.transform;
    }

    // ------------------------------------------------------------------ 腕の IK (数値的に解く)

    void SetSolver(Vector3 basePos, Quaternion baseRot, float[] joints)
    {
        solver.SetBasePose(basePos, baseRot);
        for (int i = 0; i < ArmDof; i++) solver.SetJoint(JointNames[i], joints[i]);
    }

    /// <summary>
    /// gripper_link を (targetPos, targetRot) にする関節角 (胴 + 腕 7 つ)。seed から始めて少しずつ近づける (減衰つき最小二乗)。
    /// 届かないときも、一番近づいた姿勢を返す (失敗にはしない)。
    /// </summary>
    float[] SolveArm(Vector3 basePos, Quaternion baseRot, Vector3 targetPos, Quaternion targetRot, float[] seed, string label)
    {
        const float RotWeight = 0.25f, Damping = 0.05f, Delta = 0.005f, MaxStep = 0.25f;
        var joints = (float[])seed.Clone();
        solver.SetBasePose(basePos, baseRot);
        if (!solver.TryGetLink(GripperLink, out var tip))
        {
            Debug.LogWarning($"[CoGroundUnityPlanner] {GripperLink} が Ghost に無い。腕は動かさない");
            return joints;
        }

        var jac = new double[6, ArmDof];
        var a = new double[6, 7];
        var e = new double[6];
        float positionError = float.PositiveInfinity;
        for (int iter = 0; iter < 100; iter++)
        {
            SetSolver(basePos, baseRot, joints);
            Vector3 p0 = tip.position;
            Quaternion r0 = tip.rotation;
            Vector3 dp = targetPos - p0;
            Vector3 dr = RotationVector(targetRot * Quaternion.Inverse(r0));
            positionError = dp.magnitude;
            if (positionError < 0.002f && dr.magnitude < 0.02f) break;
            e[0] = dp.x; e[1] = dp.y; e[2] = dp.z;
            e[3] = dr.x * RotWeight; e[4] = dr.y * RotWeight; e[5] = dr.z * RotWeight;

            // ヤコビアン (関節を少し動かして、手がどれだけ動くかを見る)
            for (int j = 0; j < ArmDof; j++)
            {
                solver.SetJoint(JointNames[j], joints[j] + Delta);
                Vector3 jp = (tip.position - p0) / Delta;
                Vector3 jr = RotationVector(tip.rotation * Quaternion.Inverse(r0)) * (RotWeight / Delta);
                solver.SetJoint(JointNames[j], joints[j]);
                jac[0, j] = jp.x; jac[1, j] = jp.y; jac[2, j] = jp.z;
                jac[3, j] = jr.x; jac[4, j] = jr.y; jac[5, j] = jr.z;
            }

            // dq = J^T (J J^T + λ² I)^-1 e
            for (int r = 0; r < 6; r++)
            {
                for (int c = 0; c < 6; c++)
                {
                    double sum = r == c ? Damping * Damping : 0.0;
                    for (int j = 0; j < ArmDof; j++) sum += jac[r, j] * jac[c, j];
                    a[r, c] = sum;
                }
                a[r, 6] = e[r];
            }
            if (!SolveLinear(a, 6)) break;
            var dq = new float[ArmDof];
            float largest = 0f;
            for (int j = 0; j < ArmDof; j++)
            {
                double sum = 0.0;
                for (int r = 0; r < 6; r++) sum += jac[r, j] * a[r, 6];
                dq[j] = (float)sum;
                largest = Mathf.Max(largest, Mathf.Abs(dq[j]));
            }
            float scale = largest > MaxStep ? MaxStep / largest : 1f;
            for (int j = 0; j < ArmDof; j++)
                joints[j] = Mathf.Clamp(joints[j] + dq[j] * scale, Lower[j], Upper[j]);
        }
        if (positionError > 0.03f)
            Debug.LogWarning($"[CoGroundUnityPlanner] {label}: 手が届かない (あと {positionError * 100f:F0} cm)。一番近い姿勢で続ける");
        return joints;
    }

    /// <summary>回転を「軸 × 角度 [rad]」のベクトルにする (小さい回転でも精度が落ちない形で)</summary>
    static Vector3 RotationVector(Quaternion rotation)
    {
        if (rotation.w < 0f) rotation = new Quaternion(-rotation.x, -rotation.y, -rotation.z, -rotation.w);
        var v = new Vector3(rotation.x, rotation.y, rotation.z);
        float length = v.magnitude;
        if (length < 1e-9f) return v * 2f;
        return v * (2f * Mathf.Atan2(length, rotation.w) / length);
    }

    /// <summary>n 元の連立一次方程式 (a は n × (n+1) の拡大行列)。解は a[i, n] に入る。解けなければ false</summary>
    static bool SolveLinear(double[,] a, int n)
    {
        for (int col = 0; col < n; col++)
        {
            int pivot = col;
            for (int r = col + 1; r < n; r++)
                if (Math.Abs(a[r, col]) > Math.Abs(a[pivot, col])) pivot = r;
            if (Math.Abs(a[pivot, col]) < 1e-12) return false;
            if (pivot != col)
                for (int c = 0; c <= n; c++) (a[col, c], a[pivot, c]) = (a[pivot, c], a[col, c]);
            for (int r = 0; r < n; r++)
            {
                if (r == col) continue;
                double factor = a[r, col] / a[col, col];
                if (factor == 0.0) continue;
                for (int c = col; c <= n; c++) a[r, c] -= factor * a[col, c];
            }
        }
        for (int r = 0; r < n; r++) a[r, n] /= a[r, r];
        return true;
    }

    // ------------------------------------------------------------------ 実行 (サーバーの進み方に合わせて再生する)

    void BeginExecution()
    {
        SetFocus(-1);
        executing = true;
        execTime = 0f;
        execTarget = 0f;
        lastObjectEnd = 0f;
        lastSkill = null;
        placed.Clear();
        player.Hidden = true; // 実行中は、今のロボットだけを見せる
        Debug.Log("[CoGroundUnityPlanner] 実行を始めた (Unity の計画を再生する)");
    }

    void StepExecution(JObject execution, bool serverRunning)
    {
        string holding = (string)execution?["robot"]?["holding"];
        if (serverRunning && execution?["current"] is JObject current)
        {
            // サーバーがいま実行している phase の終わりまで進める
            string obj = (string)current["object_id"];
            string skill = (string)current["skill"];
            string phase = (string)current["phase"];
            lastSkill = skill;
            bool started = !string.IsNullOrEmpty(phase);
            string name = skill == "navigate" ? "navigating" : started ? phase : skill == "pick" ? "opening" : "moving";
            bool carrying = holding == obj;
            foreach (var p in execPhases)
            {
                if (p.obj != obj) continue;
                lastObjectEnd = Mathf.Max(lastObjectEnd, p.t1);
                if (p.name != name || (name == "navigating" && p.carrying != carrying)) continue;
                execTarget = Mathf.Max(execTarget, started || skill == "navigate" ? p.t1 : p.t0);
            }
        }
        else if (!serverRunning && string.IsNullOrEmpty(holding) && (lastSkill == "place" || lastSkill == "put_back"))
        {
            // 置き終わって止まった (全部終わった、またはここで止まった): その物の動きを最後まで見せる
            execTarget = Mathf.Max(execTarget, lastObjectEnd);
        }

        // 遅れていなければ等速。phase 1 つ分より遅れたら、速めて追いつく
        float gap = execTarget - execTime;
        if (gap > 0f)
        {
            float allowed = Mathf.Max(0.1f, armPhaseSeconds * 1.2f);
            float speed = gap <= allowed ? 1f : Mathf.Clamp(gap / allowed, 1f, Mathf.Max(1f, maxCatchUpSpeed));
            execTime = Mathf.Min(execTarget, execTime + Time.deltaTime * speed);
        }

        player.ApplyTo(robotRig, execTime);
        MoveRealObjects();

        if (!serverRunning && execTarget - execTime < 1e-3f) EndExecution();
    }

    /// <summary>本物の物体を動かす: つかんでいる間は今のロボットの手に付け、置いたら置き位置へ</summary>
    void MoveRealObjects()
    {
        foreach (var kv in trackNames)
        {
            if (placed.Contains(kv.Key)) continue;
            if (!player.TryGetObjectPose(kv.Value, execTime, robotRig, out var stage, out var center, out var rotation)) continue;
            if (stage == CoGroundTaskPlanPlayer.ObjectStage.Before) continue;
            var obj = CoGroundSceneObject.Find(kv.Key);
            if (obj == null) continue;

            var body = obj.GetComponent<Rigidbody>();
            if (body != null && !kinematicBefore.ContainsKey(body))
            {
                kinematicBefore[body] = body.isKinematic; // 運んでいる間は物理で動かさない
                body.isKinematic = true;
            }
            obj.GetTransformInReportedFrame(out var localPos, out var localRot);
            obj.transform.SetPositionAndRotation(center + rotation * localPos, rotation * localRot);

            if (stage != CoGroundTaskPlanPlayer.ObjectStage.Done) continue;
            placed.Add(kv.Key);
            if (body != null && kinematicBefore.TryGetValue(body, out var was))
            {
                body.isKinematic = was;
                kinematicBefore.Remove(body);
            }
        }
    }

    void EndExecution()
    {
        // 今のロボットは、止まった時点の姿勢のまま残る (次の計画はここから始まる)
        var baseLink = robotRig.BaseLink;
        robotPos = baseLink.position;
        robotYaw = YawOf(baseLink.forward, robotYaw);
        if (timeline != null) robotQ = SampleJoints(timeline, execTime);
        executing = false;
        player.Hidden = false;
        builtKey = null;
        dirty = true;
        Debug.Log("[CoGroundUnityPlanner] 実行の再生が終わった");
    }

    static float[] SampleJoints(CoGroundTaskPlanPlayer.TimelineData data, float time)
    {
        int n = data.JointT.Count;
        if (n == 0) return (float[])Tuck.Clone();
        if (time <= data.JointT[0]) return (float[])data.JointV[0].Clone();
        for (int i = 0; i < n - 1; i++)
        {
            if (time > data.JointT[i + 1]) continue;
            float span = data.JointT[i + 1] - data.JointT[i];
            float a = span > 1e-6f ? Mathf.Clamp01((time - data.JointT[i]) / span) : 1f;
            var result = new float[data.JointV[i].Length];
            for (int k = 0; k < result.Length; k++) result[k] = Mathf.Lerp(data.JointV[i][k], data.JointV[i + 1][k], a);
            return result;
        }
        return (float[])data.JointV[n - 1].Clone();
    }
}
