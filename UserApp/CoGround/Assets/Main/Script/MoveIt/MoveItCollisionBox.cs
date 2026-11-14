using RosMessageTypes.Geometry;
using RosMessageTypes.Std;
using RosMessageTypes.Visualization;
using Unity.Robotics.ROSTCPConnector;
using Unity.Robotics.ROSTCPConnector.ROSGeometry;
using UnityEngine;

/// <summary>
/// この箱 (BoxCollider の形) を MoveIt の Planning Scene に衝突物体として登録する。
/// 机・棚・壁など、腕をぶつけたくない物に付ける (Cube を置いてこれを追加するだけでよい)。
///
///   このスクリプト ──/coground/scene/objects (MarkerArray)──▶ scene_sync.py ──▶ Planning Scene
///
/// 動かすとすぐ送り直し、止まっていても heartbeatSeconds ごとに送る
/// (ROS 側は 3 秒届かないと消すので、Play を止めれば自動で消える)。
/// 無効化・削除したときは ROS 側からも消す。
/// RViz の MotionPlanning (Scene Geometry) では緑の箱として見える。
/// </summary>
[RequireComponent(typeof(BoxCollider))]
public class MoveItCollisionBox : MonoBehaviour
{
    const string Topic = "/coground/scene/objects";
    static ROSConnection registeredOn; // Play のたびに ROSConnection が作り直されるので、接続ごとに登録する

    [Tooltip("Planning Scene での名前 (unity/<名前>)。空ならこの GameObject の名前。シーン内で重複させないこと")]
    [SerializeField] string objectName = "";
    [SerializeField] float heartbeatSeconds = 1f;

    BoxCollider box;
    ROSConnection ros;
    float nextSend;
    Vector3 lastPos, lastSize;
    Quaternion lastRot;

    string Id => string.IsNullOrEmpty(objectName) ? gameObject.name : objectName;

    /// <summary>Planning Scene での名前 (unity/ を除いた部分)</summary>
    public string ObjectName => Id;

    /// <summary>箱の大きさ (ワールドのスケール込み、箱のローカル軸ごと) [m]</summary>
    public Vector3 WorldSize
    {
        get
        {
            var b = box != null ? box : GetComponent<BoxCollider>();
            var s = Vector3.Scale(b.size, transform.lossyScale);
            return new Vector3(Mathf.Abs(s.x), Mathf.Abs(s.y), Mathf.Abs(s.z));
        }
    }

    void OnEnable()
    {
        box = GetComponent<BoxCollider>();
        ros = ROSConnection.GetOrCreateInstance();
        if (registeredOn != ros)
        {
            ros.RegisterPublisher<MarkerArrayMsg>(Topic);
            registeredOn = ros;
        }
        nextSend = 0f;
    }

    void Update()
    {
        Vector3 center = transform.TransformPoint(box.center);
        Vector3 size = Vector3.Scale(box.size, transform.lossyScale);
        Quaternion rot = transform.rotation;
        bool moved = center != lastPos || size != lastSize || rot != lastRot;
        if (!moved && Time.time < nextSend) return;

        lastPos = center; lastSize = size; lastRot = rot;
        nextSend = Time.time + heartbeatSeconds;
        Send(MarkerMsg.ADD, center, rot, size);
    }

    void OnDisable()
    {
        if (ros != null) Send(MarkerMsg.DELETE, Vector3.zero, Quaternion.identity, Vector3.zero);
    }

    void Send(int action, Vector3 center, Quaternion rot, Vector3 size)
    {
        // 箱のローカル軸: Unity の (右, 上, 前) = ROS の (-y, z, x) なので、大きさは (前, 右, 上) の順
        var marker = new MarkerMsg
        {
            header = new HeaderMsg { frame_id = "world" },
            ns = "unity",
            type = MarkerMsg.CUBE,
            action = action,
            text = Id,
            pose = new PoseMsg { position = center.To<FLU>(), orientation = rot.To<FLU>() },
            scale = new Vector3Msg(Mathf.Abs(size.z), Mathf.Abs(size.x), Mathf.Abs(size.y)),
            color = new ColorRGBAMsg(0.5f, 0.5f, 0.5f, 1f),
        };
        ros.Publish(Topic, new MarkerArrayMsg(new[] { marker }));
    }

    void OnDrawGizmosSelected()
    {
        var b = GetComponent<BoxCollider>();
        if (b == null) return;
        Gizmos.color = new Color(0.2f, 0.9f, 0.2f, 0.8f);
        Gizmos.matrix = transform.localToWorldMatrix;
        Gizmos.DrawWireCube(b.center, b.size);
    }
}
