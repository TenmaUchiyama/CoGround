using RosMessageTypes.Std;
using RosMessageTypes.Trajectory;
using Unity.Robotics.ROSTCPConnector;
using UnityEngine;

/// <summary>
/// MoveIt の計画結果 (/coground/arm/planned_trajectory) を、半透明のロボット (全身) で繰り返し再生する
/// (RViz の MotionPlanning の「Planned Path」と同じ表示)。
///
/// MoveItArmPanel を付けると自動で追加される。
/// ゴーストは見た目だけの Fetch (FetchGhostRig。Resources/FetchGhostModel) で、VR 上の Fetch (本物) は読まない・複製しない。
///   台車の位置と、計画に含まれない関節 (頭・指など) = 今のロボットの状態 (FetchRobotState = ROS の joint_states / 台車の位置)
///   腕の関節                                          = 計画の軌道
/// 表示するのは状態が planned の間だけ (実行・失敗・新しい計画の開始で消える)。
/// </summary>
public class MoveItTrajectoryPreview : MonoBehaviour
{
    [SerializeField] string trajectoryTopic = "/coground/arm/planned_trajectory";
    [SerializeField] string statusTopic = "/coground/arm/status";

    [Tooltip("ゴーストのマテリアル。未設定なら半透明の緑を作る (Quest ビルドで表示されないときは指定する)")]
    [SerializeField] Material ghostMaterial;
    [SerializeField] Color ghostColor = new Color(0.2f, 1f, 0.3f, 0.35f);
    [Tooltip("再生速度 (1 = 計画どおりの速さ)")]
    [SerializeField] float playbackSpeed = 1f;
    [Tooltip("最後の姿勢で止める秒数 (その後、最初から繰り返す)")]
    [SerializeField] float holdAtEnd = 0.8f;

    FetchGhostRig rig;
    JointTrajectoryMsg trajectory;
    float[] pointTimes;
    bool planned;
    float playTime;

    public bool IsShowing => rig != null && rig.Visible;
    /// <summary>ゴースト (見た目だけの Fetch)。Start の後で使える</summary>
    public FetchGhostRig Rig => rig;
    /// <summary>ゴーストのルート。Start の後で使える</summary>
    public GameObject Ghost => rig != null ? rig.gameObject : null;
    /// <summary>今表示している軌道の再生位置 [s] (計画の時間軸。0 に戻ると次の周)</summary>
    public float PlayTime => playTime;
    /// <summary>今の計画の長さ [s]。計画が無ければ 0</summary>
    public float Duration => pointTimes != null && pointTimes.Length > 0 ? pointTimes[pointTimes.Length - 1] : 0f;

    void Start()
    {
        var material = ghostMaterial != null ? ghostMaterial : FetchGhost.MakeMaterial(ghostColor);
        rig = FetchGhostRig.Create(name + " (planned path)", material);
        if (rig == null) { enabled = false; return; }
        _ = FetchRobotState.Instance; // 今のロボットの状態を受け取り始める

        var ros = ROSConnection.GetOrCreateInstance();
        ros.Subscribe<JointTrajectoryMsg>(trajectoryTopic, OnTrajectory);
        ros.Subscribe<StringMsg>(statusTopic, OnStatus);
    }

    void OnTrajectory(JointTrajectoryMsg msg)
    {
        trajectory = msg;
        playTime = 0f;
        pointTimes = new float[msg.points.Length];
        for (int i = 0; i < msg.points.Length; i++)
        {
            var t = msg.points[i].time_from_start;
            pointTimes[i] = t.sec + t.nanosec * 1e-9f;
        }
    }

    void OnStatus(StringMsg msg)
    {
        // planned の間だけ表示する (latch で届く古い計画も、状態が planned でなければ出さない)
        planned = msg.data.StartsWith("planned");
        playTime = 0f;
    }

    // ゴーストを動かすのはここだけ
    void Update()
    {
        if (rig == null) return;
        var state = FetchRobotState.Instance;
        // 台車の位置は隠している間も合わせておく (MoveItTrajectoryLine が実行中も線を台車に付けて描くため)
        bool baseKnown = state.TryGetBasePose(out var basePos, out var baseRot);
        if (baseKnown) rig.SetBasePose(basePos, baseRot);

        bool show = baseKnown && planned && trajectory != null && trajectory.points.Length > 0;
        rig.Visible = show;
        if (!show) return;

        rig.SetJoints(state.Joints);
        ApplyTrajectory(Time.deltaTime * playbackSpeed);
    }

    void ApplyTrajectory(float dt)
    {
        int n = pointTimes.Length;
        float duration = pointTimes[n - 1];
        playTime += dt;
        if (playTime > duration + holdAtEnd) playTime = 0f;
        float t = Mathf.Min(playTime, duration);

        int i = 0;
        while (i < n - 1 && pointTimes[i + 1] < t) i++;
        int j = Mathf.Min(i + 1, n - 1);
        float span = pointTimes[j] - pointTimes[i];
        float a = span > 1e-6f ? Mathf.Clamp01((t - pointTimes[i]) / span) : 1f;

        var names = trajectory.joint_names;
        var p0 = trajectory.points[i].positions;
        var p1 = trajectory.points[j].positions;
        for (int k = 0; k < names.Length && k < p0.Length && k < p1.Length; k++)
            rig.SetJoint(names[k], Mathf.Lerp((float)p0[k], (float)p1[k], a));
    }

    void OnDestroy()
    {
        if (rig != null) Destroy(rig.gameObject);
    }
}
