using RosMessageTypes.Geometry;
using RosMessageTypes.Std;
using Unity.Robotics.ROSTCPConnector;
using Unity.Robotics.ROSTCPConnector.ROSGeometry;
using UnityEngine;

/// <summary>
/// Unity の World 上でのロボット (base_link) の位置・向きを ROS に送る。
/// ROS 側はこれを TF (world -> base_link) にするので、以降は Unity の World 座標を
/// frame_id "world" のまま /coground/arm/goal_pose などに送れる。
///
/// 取り込んだ fetch に付け、baseLink に fetch 配下の base_link を割り当てる。
/// ロボットを Unity 上で動かせば (つかんで置き直すなど)、ROS 側の TF も追従する。
/// </summary>
public class FetchBasePosePublisher : MonoBehaviour
{
    [SerializeField] string topic = "/coground/robot/base_pose";
    [SerializeField] Transform baseLink;
    [Tooltip("送信レート (Hz)。位置が変わっていなくても送る (ROS 側の再起動に備える)")]
    [SerializeField] float rateHz = 10f;

    ROSConnection ros;
    float nextTime;

    void Start()
    {
        if (baseLink == null)
        {
            baseLink = transform;
            Debug.LogWarning("[FetchBasePosePublisher] baseLink 未設定のため自身の Transform を使う");
        }
        ros = ROSConnection.GetOrCreateInstance();
        ros.RegisterPublisher<PoseStampedMsg>(topic);
    }

    void Update()
    {
        if (Time.time < nextTime) return;
        nextTime = Time.time + 1f / rateHz;

        ros.Publish(topic, new PoseStampedMsg
        {
            header = new HeaderMsg { frame_id = "world" },
            pose = new PoseMsg
            {
                position = baseLink.position.To<FLU>(),
                orientation = baseLink.rotation.To<FLU>(),
            },
        });
    }
}
