using System.Collections.Generic;
using RosMessageTypes.Geometry;
using RosMessageTypes.Sensor;
using Unity.Robotics.ROSTCPConnector;
using Unity.Robotics.ROSTCPConnector.ROSGeometry;
using UnityEngine;

/// <summary>
/// ロボットの「今の状態」(関節角と台車の位置) を ROS から受け取って持っておく。ゴーストはここから今の状態を読む。
/// VR 上の Fetch オブジェクト (本物) の Transform や ArticulationBody は読まない。
///
///   関節角   ◀── /unity/joint_states (JointState)
///   台車の位置 ◀── /unity/base_pose   (PoseStamped。NAV=true のとき fake_base_driver が出す)
///
/// NAV=false (台車の位置は Unity の Fetch が正。FetchBasePosePublisher がそれを ROS に送る構成) のときは
/// /unity/base_pose が来ないので、FetchBasePosePublisher が送っている base_link をそのまま使う。
/// 本物のロボットを使うときは FetchBasePosePublisher を無効にするので、この代わりは使われない。
///
/// シーンに置く必要はない (FetchRobotState.Instance で自動で作られる)。トピックを変えるときはシーンに置く。
/// </summary>
public class FetchRobotState : MonoBehaviour
{
    [SerializeField] string jointStatesTopic = "/unity/joint_states";
    [SerializeField] string basePoseTopic = "/unity/base_pose";

    static FetchRobotState instance;

    public static FetchRobotState Instance
    {
        get
        {
            if (instance == null)
            {
                instance = FindAnyObjectByType<FetchRobotState>();
                if (instance == null) instance = new GameObject("FetchRobotState").AddComponent<FetchRobotState>();
            }
            return instance;
        }
    }

    readonly Dictionary<string, float> joints = new Dictionary<string, float>();
    bool subscribed;
    bool hasRosBasePose;
    Vector3 rosBasePosition;
    Quaternion rosBaseRotation = Quaternion.identity;

    /// <summary>今の関節角 (関節名 → rad または m)。まだ何も届いていなければ空</summary>
    public IReadOnlyDictionary<string, float> Joints => joints;
    public bool HasJoints => joints.Count > 0;

    void Awake()
    {
        if (instance == null) instance = this;
        Subscribe();
    }

    void Subscribe()
    {
        if (subscribed) return;
        subscribed = true;
        var ros = ROSConnection.GetOrCreateInstance();
        ros.Subscribe<JointStateMsg>(jointStatesTopic, OnJointStates);
        ros.Subscribe<PoseStampedMsg>(basePoseTopic, OnBasePose);
    }

    void OnJointStates(JointStateMsg msg)
    {
        int n = Mathf.Min(msg.name.Length, msg.position.Length);
        for (int i = 0; i < n; i++) joints[msg.name[i]] = (float)msg.position[i];
    }

    void OnBasePose(PoseStampedMsg msg)
    {
        rosBasePosition = msg.pose.position.From<FLU>();
        rosBaseRotation = msg.pose.orientation.From<FLU>();
        hasRosBasePose = true;
    }

    /// <summary>今の base_link の World の位置・向き。分からなければ false</summary>
    public bool TryGetBasePose(out Vector3 position, out Quaternion rotation)
    {
        if (hasRosBasePose)
        {
            position = rosBasePosition;
            rotation = rosBaseRotation;
            return true;
        }
        // NAV=false: Unity の Fetch が正 (FetchBasePosePublisher が ROS に送っている位置と同じものを使う)
        var publisher = FindAnyObjectByType<FetchBasePosePublisher>();
        if (publisher != null && publisher.isActiveAndEnabled && publisher.BaseLink != null)
        {
            position = publisher.BaseLink.position;
            rotation = publisher.BaseLink.rotation;
            return true;
        }
        position = default;
        rotation = Quaternion.identity;
        return false;
    }
}
