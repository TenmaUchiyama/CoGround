using System.Collections.Generic;
using RosMessageTypes.Sensor;
using Unity.Robotics.ROSTCPConnector;
using UnityEngine;

/// <summary>
/// ROS の /unity/joint_states を受け取り、URDF Importer で取り込んだ Fetch の関節に反映する。
/// 取り込んだ fetch (ルート) に付ける。fetch に付いている URDF Importer の Controller は外しておくこと。
///
/// 関節の対応: Fetch の URDF は「関節名の _joint を _link にしたもの = GameObject 名」になっている
///   例) shoulder_pan_joint -> shoulder_pan_link
/// URDF Importer の UrdfJoint などには依存しない (Quest ビルドでも動くように)。
/// </summary>
public class RosJointToFetch : MonoBehaviour
{
    [SerializeField] string topic = "/unity/joint_states";

    [Header("関節ドライブ (目標値に素早く追従させる)")]
    [SerializeField] float stiffness = 100000f;
    [SerializeField] float damping = 1000f;
    [SerializeField] float forceLimit = 1e9f;

    [Tooltip("台車 (ルートの ArticulationBody) を固定する。重力で崩れたり沈んだりしないように")]
    [SerializeField] bool fixBase = true;

    readonly Dictionary<string, ArticulationBody> linkByName = new Dictionary<string, ArticulationBody>();
    readonly HashSet<string> warnedMissing = new HashSet<string>();

    void Start()
    {
        foreach (var body in GetComponentsInChildren<ArticulationBody>())
        {
            linkByName[body.name] = body;
            if (body.isRoot && fixBase)
            {
                body.immovable = true;
            }
        }
        Debug.Log($"[RosJointToFetch] {linkByName.Count} 個の ArticulationBody を登録");

        ROSConnection.GetOrCreateInstance().Subscribe<JointStateMsg>(topic, OnJointStates);
    }

    // ROSConnection はメインスレッド (Update) でコールバックを呼ぶので、ここで直接触ってよい
    void OnJointStates(JointStateMsg msg)
    {
        int n = Mathf.Min(msg.name.Length, msg.position.Length);
        for (int i = 0; i < n; i++)
        {
            string jointName = msg.name[i];
            string linkName = jointName.EndsWith("_joint")
                ? jointName.Substring(0, jointName.Length - "_joint".Length) + "_link"
                : jointName;

            if (!linkByName.TryGetValue(linkName, out var body))
            {
                if (warnedMissing.Add(jointName))
                {
                    Debug.LogWarning($"[RosJointToFetch] {jointName} に対応する {linkName} が見つからない");
                }
                continue;
            }

            float position = (float)msg.position[i];
            var drive = body.xDrive;
            drive.stiffness = stiffness;
            drive.damping = damping;
            drive.forceLimit = forceLimit;
            // 回転関節は deg、直動関節 (torso_lift, 指など) は m
            drive.target = body.jointType == ArticulationJointType.PrismaticJoint
                ? position
                : position * Mathf.Rad2Deg;
            body.xDrive = drive;
        }
    }
}
