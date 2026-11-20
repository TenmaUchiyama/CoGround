using RosMessageTypes.Geometry;
using RosMessageTypes.Std;
using Unity.Robotics.ROSTCPConnector;
using Unity.Robotics.ROSTCPConnector.ROSGeometry;
using UnityEngine;

/// <summary>
/// RViz の MotionPlanning と同じ操作を Unity で行う。
///   - オレンジの手先 (目標) を動かす → Plan → Execute (Plan &amp; Execute で一度に)
///   - 計画結果は MoveItTrajectoryPreview が緑の半透明ロボットで再生する
///   - 状態 (/coground/arm/status) とグリッパーの開閉
///   - Pick &amp; Place: 運ぶ箱 (MoveItPickable) と置き場所 (MoveItPlaceTarget) を選んで運ぶ (ROS の pick_place_server)
///
/// どの GameObject に付けてもよい (今は fetch に付いている)。MoveItTrajectoryPreview は自動で追加される。
/// VR 上の Fetch (本物) は読まない。手先の目標の形と「目標 = 現在」は、非表示のゴースト (FetchGhostRig) を
/// 今のロボットの状態 (FetchRobotState = ROS の joint_states / 台車の位置) にして求める。
/// ROS 側は arm_command_server (/coground/arm/*) を使う。auto_execute は false (既定) のまま使うこと。
///
/// Editor での目標の動かし方: 再生中に「目標を選択」を押し、Scene ビューの移動・回転ツールで動かす。
/// VR では goal (Transform) を手でつかめるようにし、Plan() などを UI のボタンから呼ぶ。
/// </summary>
[RequireComponent(typeof(MoveItTrajectoryPreview))]
public class MoveItArmPanel : MonoBehaviour
{
    [Header("ROS トピック")]
    [SerializeField] string goalPoseTopic = "/coground/arm/goal_pose";
    [SerializeField] string executeTopic = "/coground/arm/execute";
    [SerializeField] string stopTopic = "/coground/arm/stop";
    [SerializeField] string gripperTopic = "/coground/gripper/command";
    [SerializeField] string statusTopic = "/coground/arm/status";
    [SerializeField] string pickPlaceStatusTopic = "/coground/pick_place/status";

    [Header("目標 (手先 = wrist_roll_link の位置・向き)")]
    [Tooltip("手先のリンク名。MoveIt の arm グループの先端")]
    [SerializeField] string wristLinkName = "wrist_roll_link";
    [Tooltip("目標の Transform。未設定ならグリッパーの形をしたオレンジの半透明を作る")]
    [SerializeField] Transform goal;
    [SerializeField] Material goalMaterial;
    [SerializeField] Color goalColor = new Color(1f, 0.5f, 0f, 0.5f);
    [Tooltip("目標を動かして止めたら自動で Plan する (VR で手で動かすとき用)")]
    [SerializeField] bool planWhenGoalStops = false;
    [SerializeField] float goalStopSeconds = 0.4f;

    [Header("画面のパネル (OnGUI)")]
    [SerializeField] bool showPanel = true;
    [SerializeField] float panelScale = 1.5f;

    ROSConnection ros;
    FetchGhostRig currentRig; // 今のロボットの姿勢にした非表示のゴースト (手先の位置を求める用)
    Transform wristLink;
    bool goalInitialized;
    string status = "(Not connected: waiting for arm_command_server status)";
    bool executeWhenPlanned;
    float gripperWidth = 0.1f;
    string pickPlaceStatus = "(Waiting for pick_place_server status)";
    int selectedPickable, selectedTarget;
    Vector2 scroll;

    Vector3 lastGoalPos;
    Quaternion lastGoalRot;
    float goalMovedTime = -1f;

    public Transform Goal => goal;
    public string Status => status;

    void Start()
    {
        currentRig = FetchGhostRig.Create("MoveIt Current (hidden)", null);
        if (currentRig == null || !currentRig.TryGetLink(wristLinkName, out wristLink))
        {
            Debug.LogError($"[MoveItArmPanel] ゴーストの {wristLinkName} が見つからない (Resources/FetchGhostModel が必要)");
            enabled = false;
            return;
        }

        if (goal == null)
        {
            var mat = goalMaterial != null ? goalMaterial : FetchGhost.MakeMaterial(goalColor);
            currentRig.Visible = true; // CreateVisualCopy は表示中のメッシュだけ写す
            goal = FetchGhost.CreateVisualCopy(wristLink, "MoveIt Goal (wrist_roll_link)", mat).transform;
            currentRig.Visible = false;
        }
        ResetGoalToCurrent(); // ロボットの状態がまだ届いていなければ、届いたときに置く

        ros = ROSConnection.GetOrCreateInstance();
        ros.RegisterPublisher<PoseStampedMsg>(goalPoseTopic);
        ros.RegisterPublisher<EmptyMsg>(executeTopic);
        ros.RegisterPublisher<EmptyMsg>(stopTopic);
        ros.RegisterPublisher<Float64Msg>(gripperTopic);
        ros.Subscribe<StringMsg>(statusTopic, OnStatus);
        ros.Subscribe<StringMsg>(pickPlaceStatusTopic, msg => pickPlaceStatus = msg.data);
    }

    // ---- 操作 (VR の UI ボタンなどからも呼べる) ----

    /// <summary>目標の姿勢で計画する (結果は緑のゴーストで表示される)</summary>
    public void Plan()
    {
        executeWhenPlanned = false;
        PublishGoal();
    }

    /// <summary>直前の計画を実行する</summary>
    public void Execute() => ros.Publish(executeTopic, new EmptyMsg());

    /// <summary>計画して、成功したらそのまま実行する</summary>
    public void PlanAndExecute()
    {
        executeWhenPlanned = true;
        PublishGoal();
    }

    public void Stop()
    {
        executeWhenPlanned = false;
        MoveItPickPlaceQueue.Instance.ClearPending(); // 順番待ちの運搬も取り消す (安全のため)
        ros.Publish(stopTopic, new EmptyMsg());
    }

    /// <summary>目標を今の手先の位置に戻す (RViz の Goal State = current)</summary>
    public void ResetGoalToCurrent()
    {
        var state = FetchRobotState.Instance;
        if (!state.HasJoints || !state.TryGetBasePose(out var basePos, out var baseRot))
        {
            goalInitialized = false;
            return;
        }
        currentRig.SetBasePose(basePos, baseRot);
        currentRig.SetJoints(state.Joints);
        goalInitialized = true;
        goal.SetPositionAndRotation(wristLink.position, wristLink.rotation);
        lastGoalPos = goal.position;
        lastGoalRot = goal.rotation;
        goalMovedTime = -1f;
    }

    /// <summary>グリッパーの開き幅 [m] (0 = 閉, 0.1 = 全開)</summary>
    public void SetGripper(float width)
    {
        gripperWidth = Mathf.Clamp(width, 0f, 0.1f);
        ros.Publish(gripperTopic, new Float64Msg(gripperWidth));
    }

    /// <summary>
    /// 箱を置き場所へ運ぶ。target の位置 = 置いたときの箱の底面の中心、向き = 置いたときの箱の向き。
    /// 進み具合は PickPlaceStatus (/coground/pick_place/status)。止めるときは Stop()。
    /// </summary>
    public void PickAndPlace(MoveItPickable obj, Transform target)
    {
        // ゴーストで指定したときと同じ順番待ちに入れる (1 つずつ実行される)
        MoveItPickPlaceQueue.Instance.Enqueue(obj, target.position, target.rotation);
    }

    public string PickPlaceStatus => pickPlaceStatus;

    void PublishGoal()
    {
        // Unity の World 座標をそのまま ROS の world フレームとして送る (ROS 側で base_link に変換される)
        ros.Publish(goalPoseTopic, new PoseStampedMsg
        {
            header = new HeaderMsg { frame_id = "world" },
            pose = new PoseMsg
            {
                position = goal.position.To<FLU>(),
                orientation = goal.rotation.To<FLU>(),
            },
        });
    }

    void OnStatus(StringMsg msg)
    {
        status = msg.data;
        if (!executeWhenPlanned) return;
        if (status.StartsWith("planned"))
        {
            executeWhenPlanned = false;
            Execute();
        }
        else if (status.StartsWith("plan_failed") || status.StartsWith("rejected"))
        {
            executeWhenPlanned = false;
        }
    }

    void Update()
    {
        if (!goalInitialized)
        {
            ResetGoalToCurrent();
            if (!goalInitialized) return; // ロボットの状態がまだ届いていない
        }
        if (!planWhenGoalStops) return;
        if (goal.position != lastGoalPos || goal.rotation != lastGoalRot)
        {
            lastGoalPos = goal.position;
            lastGoalRot = goal.rotation;
            goalMovedTime = Time.time;
        }
        else if (goalMovedTime >= 0f && Time.time - goalMovedTime > goalStopSeconds)
        {
            goalMovedTime = -1f;
            Plan();
        }
    }

    // ---- 画面のパネル (Editor / PC での確認用) ----
    void OnGUI()
    {
        if (!showPanel || ros == null) return;
        var saved = GUI.matrix;
        GUI.matrix = Matrix4x4.Scale(new Vector3(panelScale, panelScale, 1f));

        GUILayout.BeginArea(new Rect(10, 10, 280, Screen.height / panelScale - 20), GUI.skin.box);
        scroll = GUILayout.BeginScrollView(scroll);
        GUILayout.Label("<b>MoveIt (arm)</b>", new GUIStyle(GUI.skin.label) { richText = true });
        GUILayout.Label($"Status: {status}", new GUIStyle(GUI.skin.label) { wordWrap = true });

        GUILayout.BeginHorizontal();
        if (GUILayout.Button("Plan")) Plan();
        if (GUILayout.Button("Execute")) Execute();
        GUILayout.EndHorizontal();
        if (GUILayout.Button("Plan & Execute")) PlanAndExecute();
        if (GUILayout.Button("Stop")) Stop();

        GUILayout.Space(6);
        GUILayout.BeginHorizontal();
        if (GUILayout.Button("Goal = current")) ResetGoalToCurrent();
#if UNITY_EDITOR
        if (GUILayout.Button("Select goal"))
        {
            UnityEditor.Selection.activeGameObject = goal.gameObject;
            UnityEditor.SceneView.lastActiveSceneView?.FrameSelected();
        }
#endif
        GUILayout.EndHorizontal();
        planWhenGoalStops = GUILayout.Toggle(planWhenGoalStops, "Auto Plan when goal stops");

        GUILayout.Space(6);
        GUILayout.Label($"Gripper: {gripperWidth * 100f:0} cm");
        GUILayout.BeginHorizontal();
        if (GUILayout.Button("Open")) SetGripper(0.1f);
        if (GUILayout.Button("Close")) SetGripper(0f);
        GUILayout.EndHorizontal();

        GUILayout.Space(10);
        GUILayout.Label("<b>Pick & Place</b>", new GUIStyle(GUI.skin.label) { richText = true });
        var pickables = MoveItPickable.All;
        var targets = MoveItPlaceTarget.All;
        if (pickables.Count == 0 || targets.Count == 0)
        {
            GUILayout.Label("Place a MoveItPickable (box to carry) and a MoveItPlaceTarget (placement) in the scene",
                            new GUIStyle(GUI.skin.label) { wordWrap = true });
        }
        else
        {
            GUILayout.Label("Box to carry");
            selectedPickable = GUILayout.SelectionGrid(Mathf.Min(selectedPickable, pickables.Count - 1),
                Names(pickables, x => x.ObjectName), 2);
            GUILayout.Label("Placement");
            selectedTarget = GUILayout.SelectionGrid(Mathf.Min(selectedTarget, targets.Count - 1),
                Names(targets, x => x.name), 2);
            if (GUILayout.Button("Carry")) PickAndPlace(pickables[selectedPickable], targets[selectedTarget].transform);
        }
        GUILayout.Label($"Status: {pickPlaceStatus}", new GUIStyle(GUI.skin.label) { wordWrap = true });
        var queue = MoveItPickPlaceQueue.Instance;
        if (queue.PendingCount > 0) GUILayout.Label($"Queued: {queue.PendingCount}");
        GUILayout.Label("You can also move and release the box's translucent ghost to carry it", new GUIStyle(GUI.skin.label) { wordWrap = true, fontSize = 10 });

        GUILayout.EndScrollView();
        GUILayout.EndArea();

        GUI.matrix = saved;
    }

    static string[] Names<T>(System.Collections.Generic.IReadOnlyList<T> items, System.Func<T, string> name)
    {
        var names = new string[items.Count];
        for (int i = 0; i < names.Length; i++) names[i] = name(items[i]);
        return names;
    }

    void OnDestroy()
    {
        if (goal != null && goal.name.StartsWith("MoveIt Goal")) Destroy(goal.gameObject);
        if (currentRig != null) Destroy(currentRig.gameObject);
    }
}
