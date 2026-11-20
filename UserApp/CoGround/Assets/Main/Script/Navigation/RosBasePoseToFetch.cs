using RosMessageTypes.Geometry;
using RosMessageTypes.Std;
using Unity.Robotics.ROSTCPConnector;
using Unity.Robotics.ROSTCPConnector.ROSGeometry;
using UnityEngine;

/// <summary>
/// 台車の位置を ROS から受け取って Unity のロボットを置く (NAV=true 用。台車の位置の正解は ROS 側)。
///
///   Play 開始時: Unity の base_link の位置 ──/coground/robot/initial_pose──▶ fake_base_driver (そこに台車を置く)
///   以後:       fake_base_driver ──/unity/base_pose──▶ このスクリプト ──TeleportRoot──▶ 台車
///
/// move_base が cmd_vel を出す → fake_base_driver が積分 → ここで表示、の流れなので Unity からは台車を動かさない。
/// そのため有効な間は、同じロボットの BaseNavigator (Unity だけのナビ) と FetchCmdVelDriver を無効にする。
/// NAV=false (Unity が位置を決める構成) で使うときは、このコンポーネントを無効にすること。
///
/// 取り込んだ fetch (ルート) に付ける。
/// </summary>
public class RosBasePoseToFetch : MonoBehaviour
{
    [SerializeField] string poseTopic = "/unity/base_pose";
    [SerializeField] string initialPoseTopic = "/coground/robot/initial_pose";

    [Tooltip("台車のルート (ArticulationBody)。未設定なら子から自動で探す")]
    [SerializeField] ArticulationBody root;
    [Tooltip("base_link。未設定なら子から名前で探す (無ければルート)")]
    [SerializeField] Transform baseLink;

    [Tooltip("Play 開始時に Unity 上の位置を ROS に送って、ROS の台車をそこに置く")]
    [SerializeField] bool sendInitialPose = true;
    [SerializeField] float initialPoseRetrySeconds = 0.5f;

    ROSConnection ros;
    bool synced;           // ROS 側の台車が Unity の初期位置に置かれたことを確認した
    Vector3 sentPos;
    Quaternion sentRot;
    float nextSend;

    bool hasTarget;
    Vector3 targetPos;
    Quaternion targetRot;

    public bool Synced => synced;

    // Awake で止めると、止めたコンポーネントの Start (目標の印を作るなど) も走らない
    void Awake()
    {
        if (!enabled) return; // Awake は無効なコンポーネントでも呼ばれる (NAV=false でこれを外しているとき)
        var nav = GetComponent<BaseNavigator>();
        if (nav != null && nav.enabled) { nav.enabled = false; Debug.Log("[RosBasePoseToFetch] BaseNavigator (Unity だけのナビ) を無効にした"); }
        var cmd = GetComponent<FetchCmdVelDriver>();
        if (cmd != null && cmd.enabled) { cmd.enabled = false; Debug.Log("[RosBasePoseToFetch] FetchCmdVelDriver を無効にした (teleop は ROS 側の fake_base_driver が受ける)"); }
    }

    void Start()
    {
        if (root == null)
            foreach (var body in GetComponentsInChildren<ArticulationBody>())
                if (body.isRoot) { root = body; break; }
        if (root == null)
        {
            Debug.LogError("[RosBasePoseToFetch] 台車のルートの ArticulationBody が見つからない", this);
            enabled = false;
            return;
        }
        if (baseLink == null)
        {
            foreach (var t in GetComponentsInChildren<Transform>())
                if (t.name == "base_link") { baseLink = t; break; }
            if (baseLink == null) baseLink = root.transform;
        }

        ros =ROSConnection.GetOrCreateInstance();
        ros.RegisterPublisher<PoseStampedMsg>(initialPoseTopic);
        ros.Subscribe<PoseStampedMsg>(poseTopic, OnPose);

        sentPos = baseLink.position;
        sentRot = baseLink.rotation;
        synced = !sendInitialPose;
    }

    /// <summary>今の Unity 上の位置に ROS の台車を置き直す (ROS を再起動したときなど)</summary>
    public void ResendInitialPose()
    {
        sentPos = baseLink.position;
        sentRot = baseLink.rotation;
        synced = false;
        nextSend = 0f;
    }

    void Update()
    {
        if (synced || Time.time < nextSend) return;
        nextSend = Time.time + initialPoseRetrySeconds;
        ros.Publish(initialPoseTopic, new PoseStampedMsg
        {
            header = new HeaderMsg { frame_id = "world" },
            pose = new PoseMsg { position = sentPos.To<FLU>(), orientation = sentRot.To<FLU>() },
        });
    }

    void OnPose(PoseStampedMsg msg)
    {
        var pos = msg.pose.position.From<FLU>();
        var rot = msg.pose.orientation.From<FLU>();

        if (!synced)
        {
            // fake_base_driver は初期位置が届くまで原点を出し続けるので、送った位置が返ってくるまで待つ
            float yawDiff = Mathf.Abs(Mathf.DeltaAngle(rot.eulerAngles.y, sentRot.eulerAngles.y));
            if (Vector3.Distance(pos, sentPos) > 0.03f || yawDiff > 2f) return;
            synced = true;
            Debug.Log("[RosBasePoseToFetch] ROS の台車を Unity の位置に置いた。以後 ROS の位置に追従する");
        }

        targetPos = pos;
        targetRot = rot;
        hasTarget = true;
    }

    void FixedUpdate()
    {
        if (!hasTarget) return;
        hasTarget = false;

        // base_link をその位置に置くためのルートの位置 (base_link とルートが別の場合も合わせる)
        var rootT = root.transform;
        var localRot = Quaternion.Inverse(rootT.rotation) * baseLink.rotation;
        var localPos = Quaternion.Inverse(rootT.rotation) * (baseLink.position - rootT.position);
        var rootRot = targetRot * Quaternion.Inverse(localRot);
        var rootPos = targetPos - rootRot * localPos;
        root.TeleportRoot(rootPos, rootRot);
    }
}
