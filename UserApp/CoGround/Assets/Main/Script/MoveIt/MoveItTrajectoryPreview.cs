using System.Collections.Generic;
using RosMessageTypes.Std;
using RosMessageTypes.Trajectory;
using Unity.Robotics.ROSTCPConnector;
using UnityEngine;

/// <summary>
/// MoveIt の計画結果 (/coground/arm/planned_trajectory) を、半透明のロボットで繰り返し再生する
/// (RViz の MotionPlanning の「Planned Path」と同じ表示)。
///
/// 取り込んだ fetch (ルート) に付ける。MoveItArmPanel を付けると自動で追加される。
/// 起動時に fetch を複製してゴーストを作る。ゴーストは物理で動かさず、関節角を直接書き込む。
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

    readonly Dictionary<string, ArticulationBody> ghostByLink = new Dictionary<string, ArticulationBody>();
    readonly List<(ArticulationBody real, ArticulationBody ghost)> pairs = new List<(ArticulationBody, ArticulationBody)>();
    ArticulationBody realRoot, ghostRoot;
    Renderer[] ghostRenderers;
    bool visible;

    JointTrajectoryMsg trajectory;
    float[] pointTimes;
    bool planned;
    float playTime;

    public bool IsShowing => visible;

    void Start()
    {
        CreateGhost();
        var ros = ROSConnection.GetOrCreateInstance();
        ros.Subscribe<JointTrajectoryMsg>(trajectoryTopic, OnTrajectory);
        ros.Subscribe<StringMsg>(statusTopic, OnStatus);
    }

    void CreateGhost()
    {
        // 非アクティブな親の下に複製すると、ゴースト側のスクリプトの Awake / Start が走らない
        var holder = new GameObject("_ghost_holder");
        holder.SetActive(false);
        var ghost = Instantiate(gameObject, holder.transform, true);
        ghost.name = name + " (planned path)";

        // ROS とやり取りする自前のスクリプト (このコンポーネント自身も含む) を外す
        var ownAssembly = typeof(MoveItTrajectoryPreview).Assembly;
        foreach (var mb in ghost.GetComponentsInChildren<MonoBehaviour>(true))
        {
            if (mb.GetType().Assembly == ownAssembly) DestroyImmediate(mb);
        }
        foreach (var c in ghost.GetComponentsInChildren<Collider>(true)) c.enabled = false;

        var material = ghostMaterial != null ? ghostMaterial : FetchGhost.MakeMaterial(ghostColor);
        // 元から表示されているもの (Visuals) だけ。Collisions のメッシュは元々非表示なので含めない
        ghostRenderers = System.Array.FindAll(ghost.GetComponentsInChildren<Renderer>(true), r => r.enabled);
        foreach (var r in ghostRenderers)
        {
            var mats = new Material[r.sharedMaterials.Length];
            for (int i = 0; i < mats.Length; i++) mats[i] = material;
            r.sharedMaterials = mats;
            r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            r.enabled = false;
        }

        ghost.transform.SetParent(null, true);
        Destroy(holder);

        var realByName = new Dictionary<string, ArticulationBody>();
        foreach (var b in GetComponentsInChildren<ArticulationBody>()) realByName[b.name] = b;
        foreach (var g in ghost.GetComponentsInChildren<ArticulationBody>())
        {
            g.useGravity = false;
            if (!realByName.TryGetValue(g.name, out var r)) continue;
            // コライダーを無効にしたので、質量・慣性は本体の値を使う
            g.automaticCenterOfMass = false;
            g.centerOfMass = r.centerOfMass;
            g.automaticInertiaTensor = false;
            g.inertiaTensor = r.inertiaTensor;
            g.inertiaTensorRotation = r.inertiaTensorRotation;
            if (g.isRoot)
            {
                g.immovable = true;
                ghostRoot = g;
                realRoot = r;
            }
            else if (g.dofCount > 0)
            {
                ghostByLink[g.name] = g;
                pairs.Add((r, g));
            }
        }
        Debug.Log($"[MoveItTrajectoryPreview] ゴーストを作成 (関節 {ghostByLink.Count} 個)");
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

    void FixedUpdate()
    {
        if (ghostRoot == null || realRoot == null) return;

        // 台車の位置は本体に合わせる
        if (ghostRoot.transform.position != realRoot.transform.position ||
            ghostRoot.transform.rotation != realRoot.transform.rotation)
        {
            ghostRoot.TeleportRoot(realRoot.transform.position, realRoot.transform.rotation);
        }

        // 計画に含まれない関節 (頭・指など) は本体と同じ角度にしておく
        foreach (var (real, ghost) in pairs) SetJoint(ghost, real.jointPosition[0]);

        bool show = planned && trajectory != null && trajectory.points.Length > 0;
        if (show) ApplyTrajectory(Time.fixedDeltaTime * playbackSpeed);
        SetVisible(show);
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
        {
            string link = names[k].EndsWith("_joint")
                ? names[k].Substring(0, names[k].Length - "_joint".Length) + "_link"
                : names[k];
            if (ghostByLink.TryGetValue(link, out var body))
            {
                SetJoint(body, Mathf.Lerp((float)p0[k], (float)p1[k], a));
            }
        }
    }

    // 関節角を直接書き込む (rad または m)。ドライブの目標も同じにして引き戻されないようにする
    static void SetJoint(ArticulationBody body, float position)
    {
        body.jointPosition = new ArticulationReducedSpace(position);
        body.jointVelocity = new ArticulationReducedSpace(0f);
        var drive = body.xDrive;
        drive.target = body.jointType == ArticulationJointType.PrismaticJoint ? position : position * Mathf.Rad2Deg;
        body.xDrive = drive;
    }

    void SetVisible(bool show)
    {
        if (show == visible) return;
        visible = show;
        foreach (var r in ghostRenderers) r.enabled = show;
    }

    void OnDestroy()
    {
        if (ghostRoot != null) Destroy(ghostRoot.gameObject);
    }
}
