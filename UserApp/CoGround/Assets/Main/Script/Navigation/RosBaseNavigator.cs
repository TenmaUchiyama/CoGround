using System.Collections.Generic;
using RosMessageTypes.Geometry;
using RosMessageTypes.Nav;
using RosMessageTypes.Std;
using Unity.Robotics.ROSTCPConnector;
using Unity.Robotics.ROSTCPConnector.ROSGeometry;
using UnityEngine;

/// <summary>
/// 台車のナビゲーションを ROS (move_base) にやらせる。Unity は目標を置いて送り、結果を表示するだけ (NAV=true 用)。
///
///   目標を置く ──/coground/base/goal_pose──▶ base_command_server → move_base が計画 (make_plan)
///   経路を表示 ◀──/coground/base/planned_path── (実行中は move_base が実際に使っている経路)
///   Execute   ──/coground/base/execute──▶ move_base → cmd_vel → fake_base_driver
///   台車が動く ◀──/unity/base_pose── RosBasePoseToFetch (Fetch を動かす) と FetchRobotState (ゴーストや目標に使う)
///   状態       ◀──/coground/base/status──
///
/// 目標の置き方・見た目は BaseNavigator (Unity だけのナビ) と同じ:
///   画面のパネルで「クリックで目標を置く」→ 床をクリック (ドラッグで向き)、または「目標を選択」→ Scene ビューで動かす。
///   目標を動かして止めると自動で計画を頼む。
///   - 青のゴースト = 目標で止まったときのロボット
///   - 緑のゴースト = 経路に沿って動くおおよその様子 (move_base の実際の動きとは少し違う)
///   - 水色の線     = move_base が計画した経路
///
/// どの GameObject に付けてもよい (今は fetch に付いている)。VR 上の Fetch (本物) は読まない:
///   今の台車の位置 = FetchRobotState (ROS の /unity/base_pose)、ゴースト = 見た目だけの Fetch (FetchGhostRig)。
/// </summary>
public class RosBaseNavigator : MonoBehaviour
{
    [Header("ROS トピック")]
    [SerializeField] string goalTopic = "/coground/base/goal_pose";
    [SerializeField] string executeTopic = "/coground/base/execute";
    [SerializeField] string stopTopic = "/coground/base/stop";
    [SerializeField] string pathTopic = "/coground/base/planned_path";
    [SerializeField] string statusTopic = "/coground/base/status";

    [Header("台車")]
    [Tooltip("目標の輪の大きさ [m] (move_base の robot_radius と同じくらい)")]
    [SerializeField] float robotRadius = 0.3f;

    [Header("目標")]
    [Tooltip("目標の Transform (位置と向き)。未設定なら作る")]
    [SerializeField] Transform goal;
    [Tooltip("目標を動かして止めたら自動で計画を頼む")]
    [SerializeField] bool planWhenGoalStops = true;
    [SerializeField] float goalStopSeconds = 0.4f;

    [Header("見た目")]
    [SerializeField] Color goalColor = new Color(1f, 0.5f, 0f, 0.9f);
    [SerializeField] Color goalGhostColor = new Color(0.3f, 0.55f, 1f, 0.3f);
    [SerializeField] Color previewGhostColor = new Color(0.2f, 1f, 0.3f, 0.3f);
    [SerializeField] Color pathColor = new Color(0.2f, 0.85f, 1f, 0.9f);
    [SerializeField] float pathWidth = 0.03f;
    [Tooltip("線を台車の底からどれだけ上に描くか [m]")]
    [SerializeField] float pathHeight = 0.02f;
    [Tooltip("緑のゴーストの速さ [m/s]")]
    [SerializeField] float previewSpeed = 0.6f;
    [SerializeField] float holdAtEnd = 0.8f;

    [Header("画面のパネル (OnGUI)")]
    [SerializeField] bool showPanel = true;
    [SerializeField] float panelScale = 1.5f;

    /// <summary>ROS の状態 (ready / planning / planned / plan_failed / executing / succeeded / exec_failed / stopped / rejected …)</summary>
    public string State { get; private set; } = "";
    public string Status { get; private set; } = "(Not connected: waiting for base_command_server status. Was it started with NAV=true?)";
    public Transform Goal => goal;
    public IReadOnlyList<Vector3> PathPoints => path;

    ROSConnection ros;
    bool requested; // このセッションで目標を送った (それまでの latch された古い経路は表示しない)
    readonly List<Vector3> path = new List<Vector3>();
    readonly List<float> pathDist = new List<float>();
    float previewTime;

    FetchGhostRig goalGhost, previewGhost;
    bool goalPending; // 台車の位置がまだ分からないので、分かったら目標を今の位置に置く
    Material goalGhostMaterial, previewGhostMaterial;
    LineRenderer pathLine;

    Vector3 lastGoalPos;
    Quaternion lastGoalRot;
    float goalMovedTime = -1f;

    bool placing, dragging;
    Vector3 dragStart;
    Rect panelScreenRect;

    void Start()
    {
        goalGhostMaterial = FetchGhost.MakeMaterial(goalGhostColor);
        previewGhostMaterial = FetchGhost.MakeMaterial(previewGhostColor);
        pathLine = MakeLine("Nav Planned Path (ROS)", null, pathColor, pathWidth, true);
        pathLine.enabled = false;

        if (goal == null) goal = new GameObject("Nav Goal (ROS)").transform;
        BuildGoalMarker();
        ResetGoalToCurrent();

        ros = ROSConnection.GetOrCreateInstance();
        ros.RegisterPublisher<PoseStampedMsg>(goalTopic);
        ros.RegisterPublisher<EmptyMsg>(executeTopic);
        ros.RegisterPublisher<EmptyMsg>(stopTopic);
        ros.Subscribe<PathMsg>(pathTopic, OnPath);
        ros.Subscribe<StringMsg>(statusTopic, OnStatus);
    }

    // ---- 操作 (VR の UI ボタンなどからも呼べる) ----

    /// <summary>今の目標で計画を頼む (結果は planned_path と status で返ってくる)</summary>
    public void Plan()
    {
        if (State == "executing") { Status = "Can't plan while executing (Stop first)"; return; }
        ClearPlan();
        requested = true;
        ros.Publish(goalTopic, new PoseStampedMsg
        {
            header = new HeaderMsg { frame_id = "world" },
            pose = new PoseMsg
            {
                position = goal.position.To<FLU>(),
                orientation = Quaternion.Euler(0f, YawOf(goal), 0f).To<FLU>(),
            },
        });
        Status = "Plan requested";
    }

    /// <summary>直前の計画を実行する (ROS 側が今の位置から計画し直してから動かす)</summary>
    public void Execute()
    {
        if (!requested) { Status = "Place a goal and Plan first"; return; }
        ros.Publish(executeTopic, new EmptyMsg());
    }

    public void PlanAndExecute()
    {
        Plan();
        executeWhenPlanned = true;
    }
    bool executeWhenPlanned;

    public void Stop()
    {
        executeWhenPlanned = false;
        ros.Publish(stopTopic, new EmptyMsg());
    }

    /// <summary>目標を今の台車の位置・向きに戻す</summary>
    public void ResetGoalToCurrent()
    {
        if (!FetchRobotState.Instance.TryGetBasePose(out var basePos, out var baseRot))
        {
            goalPending = true;
            return;
        }
        goalPending = false;
        goal.SetPositionAndRotation(basePos, Quaternion.Euler(0f, BaseNavPath.YawOf(baseRot * Vector3.forward), 0f));
        lastGoalPos = goal.position;
        lastGoalRot = goal.rotation;
        goalMovedTime = -1f;
    }

    /// <summary>目標を置く (位置と向き [deg])。planWhenGoalStops なら少し後に自動で計画を頼む</summary>
    public void SetGoal(Vector3 position, float yaw)
    {
        goal.SetPositionAndRotation(position, Quaternion.Euler(0f, yaw, 0f));
    }

    // ---- ROS から ----

    void OnPath(PathMsg msg)
    {
        if (!requested) return;
        path.Clear();
        pathDist.Clear();
        float y = FloorY;
        float d = 0f;
        foreach (var p in msg.poses)
        {
            var v = p.pose.position.From<FLU>();
            v.y = y;
            if (path.Count > 0) d += Vector3.Distance(path[path.Count - 1], v);
            path.Add(v);
            pathDist.Add(d);
        }
        DrawPath();
        // status (planned) が経路より先に届いた場合
        if (State == "planned" && goalGhost != null && previewGhost == null && path.Count > 1)
        {
            previewGhost = MakeGhost("Nav Preview Ghost (ROS)", previewGhostMaterial);
            previewTime = 0f;
        }
    }

    void OnStatus(StringMsg msg)
    {
        string text = msg.data;
        int colon = text.IndexOf(':');
        State = (colon >= 0 ? text.Substring(0, colon) : text).Trim();
        string detail = colon >= 0 ? text.Substring(colon + 1).Trim() : "";

        switch (State)
        {
            case "waiting": Status = "Waiting for move_base to start"; break;
            case "ready": Status = "Ready: place a goal, then Plan"; break;
            case "planning": Status = "Planning (move_base)"; break;
            case "planned":
                Status = $"Planned: {detail}";
                if (requested) ShowGhosts();
                if (executeWhenPlanned) { executeWhenPlanned = false; Execute(); }
                break;
            case "plan_failed": Status = "Planning failed: " + detail; executeWhenPlanned = false; ClearPlan(); break;
            case "executing":
                Status = "Executing " + detail;
                DestroyGhost(ref previewGhost);
                break;
            case "succeeded": Status = "Arrived"; ClearPlan(); break;
            case "exec_failed": Status = "Execution failed: " + detail; ClearPlan(); break;
            case "stopped": Status = "Stopped"; ClearPlan(); break;
            case "rejected": Status = "Rejected: " + detail; executeWhenPlanned = false; break;
            default: Status = text; break;
        }
    }

    // ---- 毎フレーム ----

    void Update()
    {
        if (goalPending) ResetGoalToCurrent();
        WatchGoal();

        if (previewGhost != null && path.Count > 1)
        {
            float length = pathDist[pathDist.Count - 1];
            float duration = length / Mathf.Max(previewSpeed, 0.01f);
            previewTime += Time.deltaTime;
            if (previewTime > duration + holdAtEnd) previewTime = 0f;
            PlaceAlongPath(previewGhost, Mathf.Min(previewTime / Mathf.Max(duration, 1e-3f), 1f) * length);
        }
    }

    void WatchGoal()
    {
        if (goal.position != lastGoalPos || goal.rotation != lastGoalRot)
        {
            lastGoalPos = goal.position;
            lastGoalRot = goal.rotation;
            goalMovedTime = Time.time;
        }
        else if (planWhenGoalStops && !dragging && goalMovedTime >= 0f && Time.time - goalMovedTime > goalStopSeconds
                 && State != "executing")
        {
            goalMovedTime = -1f;
            Plan();
        }
    }

    // ---- 補助 ----

    static float YawOf(Transform t)
    {
        var f = Vector3.ProjectOnPlane(t.forward, Vector3.up);
        return f.sqrMagnitude < 1e-6f ? t.eulerAngles.y : BaseNavPath.YawOf(f);
    }

    // 台車の底 (base_link) の高さ。台車の位置が分からなければ目標の高さ
    float FloorY => FetchRobotState.Instance.TryGetBasePose(out var p, out _) ? p.y : goal.position.y;

    // 見た目だけの Fetch を、今のロボットの関節角 (腕・頭など) で作る
    static FetchGhostRig MakeGhost(string ghostName, Material material)
    {
        var ghost = FetchGhostRig.Create(ghostName, material);
        if (ghost == null) return null;
        ghost.SetJoints(FetchRobotState.Instance.Joints);
        ghost.Visible = true;
        return ghost;
    }

    static void DestroyGhost(ref FetchGhostRig ghost)
    {
        if (ghost != null) Destroy(ghost.gameObject);
        ghost = null;
    }

    void ShowGhosts()
    {
        DestroyGhost(ref goalGhost);
        DestroyGhost(ref previewGhost);
        goalGhost = MakeGhost("Nav Goal Ghost (ROS)", goalGhostMaterial);
        if (goalGhost != null)
        {
            var g = goal.position;
            g.y = FloorY;
            goalGhost.SetBasePose(g, Quaternion.Euler(0f, YawOf(goal), 0f));
        }

        if (path.Count > 1)
        {
            previewGhost = MakeGhost("Nav Preview Ghost (ROS)", previewGhostMaterial);
            previewTime = 0f;
        }
    }

    // 経路の始点から距離 s の位置。向きは進む方向 (最後だけ目標の向きへ回す)
    void PlaceAlongPath(FetchGhostRig ghost, float s)
    {
        int i = 1;
        while (i < path.Count - 1 && pathDist[i] < s) i++;
        float seg = pathDist[i] - pathDist[i - 1];
        float k = seg > 1e-6f ? Mathf.Clamp01((s - pathDist[i - 1]) / seg) : 1f;
        var pos = Vector3.Lerp(path[i - 1], path[i], k);

        // 少し先を見て向きを決める (経路の細かいガタつきでゴーストが揺れないように)
        float ahead = s + 0.2f;
        int j = i;
        while (j < path.Count - 1 && pathDist[j] < ahead) j++;
        var dir = path[j] - pos;
        float length = pathDist[pathDist.Count - 1];
        float yaw = dir.sqrMagnitude > 1e-4f ? BaseNavPath.YawOf(dir) : YawOf(goal);
        float blend = Mathf.InverseLerp(length - 0.3f, length, s); // 終点の手前で目標の向きへ
        yaw = Mathf.LerpAngle(yaw, YawOf(goal), blend);
        ghost.SetBasePose(pos, Quaternion.Euler(0f, yaw, 0f));
    }

    void ClearPlan()
    {
        DestroyGhost(ref goalGhost);
        DestroyGhost(ref previewGhost);
        path.Clear();
        pathDist.Clear();
        if (pathLine != null) pathLine.enabled = false;
    }

    void DrawPath()
    {
        pathLine.positionCount = path.Count;
        for (int i = 0; i < path.Count; i++) pathLine.SetPosition(i, path[i] + Vector3.up * pathHeight);
        pathLine.enabled = path.Count > 1;
    }

    LineRenderer MakeLine(string name, Transform parent, Color color, float width, bool worldSpace)
    {
        var line = new GameObject(name).AddComponent<LineRenderer>();
        if (parent != null) line.transform.SetParent(parent, false);
        line.useWorldSpace = worldSpace;
        line.material = FetchGhost.MakeMaterial(color);
        line.startColor = line.endColor = color;
        line.startWidth = line.endWidth = width;
        line.numCapVertices = 4;
        line.numCornerVertices = 4;
        line.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
        line.receiveShadows = false;
        return line;
    }

    // 目標の印: 台車の大きさの輪と、向きの矢印 (目標のローカル座標なので一緒に動く)
    void BuildGoalMarker()
    {
        const int n = 48;
        var ring = MakeLine("Ring", goal, goalColor, 0.015f, false);
        ring.loop = true;
        ring.positionCount = n;
        for (int i = 0; i < n; i++)
        {
            float a = i * Mathf.PI * 2f / n;
            ring.SetPosition(i, new Vector3(Mathf.Sin(a) * robotRadius, pathHeight, Mathf.Cos(a) * robotRadius));
        }
        var arrow = MakeLine("Arrow", goal, goalColor, 0.02f, false);
        float h = pathHeight, len = robotRadius * 1.4f, head = robotRadius * 0.4f;
        arrow.positionCount = 5;
        arrow.SetPositions(new[]
        {
            new Vector3(0f, h, 0f), new Vector3(0f, h, len),
            new Vector3(-head * 0.6f, h, len - head), new Vector3(0f, h, len), new Vector3(head * 0.6f, h, len - head),
        });
    }

    bool RayToFloor(Vector2 guiPos, out Vector3 point)
    {
        point = default;
        var cam = Camera.main;
        if (cam == null) return false;
        var ray = cam.ScreenPointToRay(new Vector3(guiPos.x, Screen.height - guiPos.y, 0f));
        var floor = new Plane(Vector3.up, new Vector3(0f, FloorY, 0f));
        if (!floor.Raycast(ray, out var d)) return false;
        point = ray.GetPoint(d);
        return true;
    }

    // ---- 画面のパネル (Editor / PC での確認用) ----

    void OnGUI()
    {
        if (!showPanel || ros == null) return;
        HandleClick(Event.current);

        var saved = GUI.matrix;
        GUI.matrix = Matrix4x4.Scale(new Vector3(panelScale, panelScale, 1f));
        float w = 260f, x = Screen.width / panelScale - w - 10f;
        var area = new Rect(x, 10f, w, 260f);
        panelScreenRect = new Rect(area.x * panelScale, area.y * panelScale, area.width * panelScale, area.height * panelScale);

        GUILayout.BeginArea(area, GUI.skin.box);
        GUILayout.Label("<b>Navigation (base, ROS move_base)</b>", new GUIStyle(GUI.skin.label) { richText = true });
        GUILayout.Label($"Status: {Status}", new GUIStyle(GUI.skin.label) { wordWrap = true });
        if (!FetchRobotState.Instance.TryGetBasePose(out _, out _))
            GUILayout.Label("(Waiting for ROS base pose: /unity/base_pose)", new GUIStyle(GUI.skin.label) { wordWrap = true });

        GUILayout.BeginHorizontal();
        if (GUILayout.Button("Plan")) Plan();
        if (GUILayout.Button("Execute")) Execute();
        GUILayout.EndHorizontal();
        GUILayout.BeginHorizontal();
        if (GUILayout.Button("Plan & Execute")) PlanAndExecute();
        if (GUILayout.Button("Stop")) Stop();
        GUILayout.EndHorizontal();

        GUILayout.Space(4);
        placing = GUILayout.Toggle(placing, "Click to place goal (drag for heading)");
        GUILayout.BeginHorizontal();
        if (GUILayout.Button("Goal = current")) ResetGoalToCurrent();
#if UNITY_EDITOR
        if (GUILayout.Button("Select goal")) UnityEditor.Selection.activeTransform = goal;
#endif
        GUILayout.EndHorizontal();
        GUILayout.EndArea();
        GUI.matrix = saved;
    }

    void HandleClick(Event e)
    {
        if (!placing || !e.isMouse || e.button != 0) return;
        switch (e.type)
        {
            case EventType.MouseDown:
                if (panelScreenRect.Contains(e.mousePosition) || !RayToFloor(e.mousePosition, out var p)) return;
                dragging = true;
                dragStart = p;
                goal.position = p;
                e.Use();
                break;
            case EventType.MouseDrag:
                if (!dragging || !RayToFloor(e.mousePosition, out var q)) return;
                var dir = Vector3.ProjectOnPlane(q - dragStart, Vector3.up);
                if (dir.magnitude > 0.1f) goal.rotation = Quaternion.LookRotation(dir, Vector3.up);
                e.Use();
                break;
            case EventType.MouseUp:
                if (!dragging) return;
                dragging = false;
                if (!planWhenGoalStops) Plan();
                e.Use();
                break;
        }
    }

    void OnDestroy()
    {
        ClearPlan();
        if (pathLine != null) Destroy(pathLine.gameObject);
    }
}
