using System.Collections.Generic;
using UnityEngine;

/// <summary>
/// 台車を目標 (Nav Goal) まで動かす簡単なナビゲーション。ROS は使わず Unity の中だけで計画・実行する。
///
///   1. 目標を置く: 画面のパネルで「クリックで目標を置く」を有効にして床をクリック (ドラッグで向き)、
///      または「目標を選択」→ Scene ビューで Nav Goal を動かす
///   2. Plan: 障害物 (コライダー) を避ける道を計画する (BaseNavPlanner)。目標を動かして止めると自動で計画する
///        - 青のゴースト = 目標で止まったときのロボット
///        - 緑のゴースト = 計画どおりに動くロボット (繰り返し再生。パネルのスライダーで好きな位置に止められる)
///        - 水色の線     = これから通る道 (Future Path)。実行中は残りの道だけを表示する
///   3. Execute: 計画と同じ動き (BaseNavPath) で台車のルートを動かす。Stop で止める
///
/// 取り込んだ fetch (ルート) に付ける。台車は FetchCmdVelDriver と同じく TeleportRoot で動かすので、
/// FetchBasePosePublisher があれば ROS 側の TF もそのまま追従する (実行中に cmd_vel を送らないこと)。
/// </summary>
public class BaseNavigator : MonoBehaviour
{
    public enum NavState { Idle, Planned, PlanFailed, Executing, Succeeded, Stopped }

    [Header("台車")]
    [Tooltip("台車のルート (base_link の ArticulationBody)。未設定なら子から自動で探す")]
    [SerializeField] ArticulationBody root;
    [Tooltip("直進の最高速度 [m/s]")]
    [SerializeField] float linearSpeed = 0.5f;
    [Tooltip("回転の最高速度 [deg/s]")]
    [SerializeField] float angularSpeed = 60f;

    [Header("計画 (障害物 = 台車の高さにあるコライダー)")]
    [Tooltip("台車の半径 [m]。腕を伸ばしたまま動くなら大きめに")]
    [SerializeField] float robotRadius = 0.35f;
    [SerializeField] float cellSize = 0.1f;
    [Tooltip("台車の底からこの高さの範囲にあるものを障害物とみなす [m]")]
    [SerializeField] Vector2 obstacleHeight = new Vector2(0.05f, 1.6f);
    [SerializeField] LayerMask obstacleMask = ~0;
    [Tooltip("目標を動かして止めたら自動で計画する")]
    [SerializeField] bool planWhenGoalStops = true;
    [SerializeField] float goalStopSeconds = 0.4f;

    [Header("目標")]
    [Tooltip("目標の Transform (位置と向き)。未設定なら作る")]
    [SerializeField] Transform goal;

    [Header("見た目")]
    [SerializeField] Color goalColor = new Color(1f, 0.5f, 0f, 0.9f);
    [SerializeField] Color goalGhostColor = new Color(0.3f, 0.55f, 1f, 0.3f);
    [SerializeField] Color previewGhostColor = new Color(0.2f, 1f, 0.3f, 0.3f);
    [SerializeField] Color pathColor = new Color(0.2f, 0.85f, 1f, 0.9f);
    [SerializeField] float pathWidth = 0.03f;
    [Tooltip("線を台車の底からどれだけ上に描くか [m]")]
    [SerializeField] float pathHeight = 0.02f;
    [Tooltip("緑のゴーストの再生速度 (1 = 実行と同じ速さ)")]
    [SerializeField] float previewSpeed = 1.5f;
    [SerializeField] float holdAtEnd = 0.8f;
    [SerializeField] bool drawBlockedCells = true;

    [Header("画面のパネル (OnGUI)")]
    [SerializeField] bool showPanel = true;
    [SerializeField] float panelScale = 1.5f;

    public NavState State { get; private set; } = NavState.Idle;
    public string Status { get; private set; } = "Place a goal, then Plan";
    public BaseNavPath Path { get; private set; }
    public Transform Goal => goal;
    /// <summary>緑のゴーストの再生位置 [s]</summary>
    public float PreviewTime { get => previewTime; set { previewTime = Mathf.Clamp(value, 0f, Path?.Duration ?? 0f); } }
    public bool PreviewPaused { get; set; }

    readonly BaseNavPlanner planner = new BaseNavPlanner();
    readonly List<Vector3> points = new List<Vector3>();
    Quaternion planRotation; // 計画したときの台車の向き (ゴーストと実行はこれを基準に回す)
    float planYaw;
    float previewTime, execTime;

    GameObject goalGhost, previewGhost;
    Material goalGhostMaterial, previewGhostMaterial;
    LineRenderer pathLine;

    Vector3 lastGoalPos;
    Quaternion lastGoalRot;
    float goalMovedTime = -1f;

    // パネル・クリック
    bool placing;
    bool dragging;
    Vector3 dragStart;
    Rect panelScreenRect;

    void Start()
    {
        if (root == null)
            foreach (var body in GetComponentsInChildren<ArticulationBody>())
                if (body.isRoot) { root = body; break; }
        if (root == null)
        {
            Debug.LogError("[BaseNavigator] 台車のルートの ArticulationBody が見つからない", this);
            enabled = false;
            return;
        }

        goalGhostMaterial = FetchGhost.MakeMaterial(goalGhostColor);
        previewGhostMaterial = FetchGhost.MakeMaterial(previewGhostColor);
        pathLine = MakeLine("Nav Future Path", null, pathColor, pathWidth, true);
        pathLine.enabled = false;

        if (goal == null) goal = new GameObject("Nav Goal").transform;
        BuildGoalMarker();
        ResetGoalToCurrent();
    }

    // ---- 操作 (VR の UI ボタンなどからも呼べる) ----

    /// <summary>今の位置から目標までを計画する</summary>
    public bool Plan()
    {
        if (State == NavState.Executing) { Status = "Can't plan while executing (Stop first)"; return false; }
        ClearPlan();

        planner.RobotRadius = robotRadius;
        planner.CellSize = cellSize;
        planner.MinHeight = obstacleHeight.x;
        planner.MaxHeight = obstacleHeight.y;
        planner.Mask = obstacleMask;
        planner.Ignore = transform;

        var start = root.transform.position;
        var target = goal.position;
        target.y = start.y;
        if (!planner.TryPlan(start, target, points, out var error))
        {
            State = NavState.PlanFailed;
            Status = "Planning failed: " + error;
            return false;
        }

        planRotation = root.transform.rotation;
        planYaw = YawOf(root.transform);
        Path = BaseNavPath.Build(points, planYaw, YawOf(goal), linearSpeed, angularSpeed);
        previewTime = 0f;

        // ゴーストは今の姿勢 (腕など) の見た目を写す
        goalGhost = FetchGhost.CreateVisualCopy(root.transform, "Nav Goal Ghost", goalGhostMaterial);
        previewGhost = FetchGhost.CreateVisualCopy(root.transform, "Nav Preview Ghost", previewGhostMaterial);
        PlaceAt(goalGhost.transform, Path.Duration);
        PlaceAt(previewGhost.transform, 0f);

        State = NavState.Planned;
        Status = $"Planned: {Path.Length:F2} m, {Path.Duration:F1} s ({points.Count - 2} turns)";
        DrawPath(Path.Waypoints);
        return true;
    }

    /// <summary>直前の計画を実行する (計画後に台車が動いていたら計画し直す)</summary>
    public void Execute()
    {
        if (State == NavState.Executing) return;
        if (State != NavState.Planned || Moved()) { if (!Plan()) return; }
        execTime = 0f;
        State = NavState.Executing;
        Status = "Executing";
        if (previewGhost != null) previewGhost.SetActive(false);
    }

    public void PlanAndExecute()
    {
        if (Plan()) Execute();
    }

    public void Stop()
    {
        if (State != NavState.Executing && State != NavState.Planned) return;
        ClearPlan();
        State = NavState.Stopped;
        Status = "Stopped";
    }

    /// <summary>目標を今の台車の位置・向きに戻す</summary>
    public void ResetGoalToCurrent()
    {
        var yaw = YawOf(root.transform);
        goal.SetPositionAndRotation(root.transform.position, Quaternion.Euler(0f, yaw, 0f));
        lastGoalPos = goal.position;
        lastGoalRot = goal.rotation;
        goalMovedTime = -1f;
    }

    /// <summary>目標を置く (位置と向き [deg])。planWhenGoalStops なら少し後に自動で計画する</summary>
    public void SetGoal(Vector3 position, float yaw)
    {
        goal.SetPositionAndRotation(position, Quaternion.Euler(0f, yaw, 0f));
    }

    // ---- 毎フレーム ----

    void Update()
    {
        WatchGoal();

        if (State == NavState.Planned && Path != null && previewGhost != null)
        {
            if (!PreviewPaused)
            {
                previewTime += Time.deltaTime * previewSpeed;
                if (previewTime > Path.Duration + holdAtEnd) previewTime = 0f;
            }
            PlaceAt(previewGhost.transform, Mathf.Min(previewTime, Path.Duration));
        }
    }

    void FixedUpdate()
    {
        if (State != NavState.Executing || Path == null) return;

        execTime += Time.fixedDeltaTime;
        Path.Sample(execTime, out var pos, out var yaw);
        root.TeleportRoot(pos, RotationAt(yaw));

        Path.RemainingPoints(execTime, points);
        DrawPath(points);

        if (execTime >= Path.Duration)
        {
            ClearPlan();
            State = NavState.Succeeded;
            Status = "Arrived";
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
                 && State != NavState.Executing)
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

    // 計画時の台車の向きを yaw だけ回す (傾きなど yaw 以外はそのまま)
    Quaternion RotationAt(float yaw) => Quaternion.AngleAxis(yaw - planYaw, Vector3.up) * planRotation;

    void PlaceAt(Transform ghost, float t)
    {
        Path.Sample(t, out var pos, out var yaw);
        ghost.SetPositionAndRotation(pos, RotationAt(yaw));
    }

    bool Moved()
    {
        if (Path == null || Path.Waypoints.Count == 0) return true;
        return Vector3.Distance(root.transform.position, Path.Waypoints[0]) > 0.05f ||
               Mathf.Abs(Mathf.DeltaAngle(YawOf(root.transform), planYaw)) > 3f;
    }

    void ClearPlan()
    {
        Path = null;
        if (goalGhost != null) Destroy(goalGhost);
        if (previewGhost != null) Destroy(previewGhost);
        goalGhost = previewGhost = null;
        if (pathLine != null) pathLine.enabled = false;
    }

    void DrawPath(IReadOnlyList<Vector3> pts)
    {
        pathLine.positionCount = pts.Count;
        for (int i = 0; i < pts.Count; i++) pathLine.SetPosition(i, pts[i] + Vector3.up * pathHeight);
        pathLine.enabled = pts.Count > 1;
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
        var floor = new Plane(Vector3.up, root.transform.position);
        if (!floor.Raycast(ray, out var d)) return false;
        point = ray.GetPoint(d);
        return true;
    }

    // ---- 画面のパネル (Editor / PC での確認用) ----

    void OnGUI()
    {
        if (!showPanel || root == null) return;
        HandleClick(Event.current);

        var saved = GUI.matrix;
        GUI.matrix = Matrix4x4.Scale(new Vector3(panelScale, panelScale, 1f));
        float w = 260f, x = Screen.width / panelScale - w - 10f;
        var area = new Rect(x, 10f, w, 330f);
        panelScreenRect = new Rect(area.x * panelScale, area.y * panelScale, area.width * panelScale, area.height * panelScale);

        GUILayout.BeginArea(area, GUI.skin.box);
        GUILayout.Label("<b>Navigation (base)</b>", new GUIStyle(GUI.skin.label) { richText = true });
        GUILayout.Label($"Status: {Status}", new GUIStyle(GUI.skin.label) { wordWrap = true });

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

        if (State == NavState.Planned && Path != null)
        {
            GUILayout.Space(4);
            GUILayout.Label($"Preview {Mathf.Min(previewTime, Path.Duration):F1} / {Path.Duration:F1} s");
            float t = GUILayout.HorizontalSlider(Mathf.Min(previewTime, Path.Duration), 0f, Path.Duration);
            if (!Mathf.Approximately(t, Mathf.Min(previewTime, Path.Duration)))
            {
                PreviewPaused = true;
                previewTime = t;
            }
            GUILayout.Space(8);
            if (GUILayout.Button(PreviewPaused ? "Play" : "Pause")) PreviewPaused = !PreviewPaused;
        }
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

    void OnDrawGizmosSelected()
    {
        if (drawBlockedCells) planner.DrawGizmos();
    }

    void OnDestroy()
    {
        ClearPlan();
        if (pathLine != null) Destroy(pathLine.gameObject);
    }
}
