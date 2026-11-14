using RosMessageTypes.Geometry;
using Unity.Robotics.ROSTCPConnector;
using UnityEngine;

/// <summary>
/// ROS の速度指令 (cmd_vel) を受け取り、Unity 上で Fetch の台車を動かす。
/// Gazebo なしの構成用。台車の位置は Unity が決め、FetchBasePosePublisher が ROS の TF に反映する。
///
///   make teleop ──/teleop/cmd_vel──▶ このスクリプト (速度を積分して台車を移動)
///                                      └ FetchBasePosePublisher ──▶ TF world→base_link
///
/// 取り込んだ fetch に付ける (RosJointToFetch / FetchBasePosePublisher と同じ GameObject でよい)。
/// Gazebo と同時に使わないこと (Gazebo も同じ cmd_vel で台車を動かすので位置が食い違う)。
/// </summary>
public class FetchCmdVelDriver : MonoBehaviour
{
    [SerializeField] string topic = "/teleop/cmd_vel";

    [Tooltip("台車のルート (base_link の ArticulationBody)。未設定なら子から自動で探す")]
    [SerializeField] ArticulationBody root;

    [Tooltip("この秒数だけ指令が来なければ止める (通信が切れたときの安全策)")]
    [SerializeField] float commandTimeout = 0.5f;

    [Header("安全のための上限 (Fetch の台車の仕様程度)")]
    [SerializeField] float maxLinear = 1.0f;   // m/s
    [SerializeField] float maxAngular = 1.5f;  // rad/s

    [Header("向きが合わないときの調整")]
    [Tooltip("前後が逆に動くときにチェック")]
    [SerializeField] bool invertForward = false;
    [Tooltip("左右の旋回が逆になるときにチェック")]
    [SerializeField] bool invertTurn = false;

    TwistMsg lastCmd;
    float lastCmdTime = float.NegativeInfinity;

    void Start()
    {
        if (root == null)
        {
            foreach (var body in GetComponentsInChildren<ArticulationBody>())
            {
                if (body.isRoot) { root = body; break; }
            }
        }
        if (root == null)
        {
            Debug.LogError("[FetchCmdVelDriver] ルートの ArticulationBody が見つからない");
            enabled = false;
            return;
        }
        ROSConnection.GetOrCreateInstance().Subscribe<TwistMsg>(topic, OnCmdVel);
        Debug.Log($"[FetchCmdVelDriver] {topic} を購読、台車のルート = {root.name}");
    }

    // ROSConnection はメインスレッドでコールバックを呼ぶ
    void OnCmdVel(TwistMsg msg)
    {
        lastCmd = msg;
        lastCmdTime = Time.time;
    }

    void FixedUpdate()
    {
        if (lastCmd == null || Time.time - lastCmdTime > commandTimeout) return;

        // ROS (base_link 基準): linear.x = 前, linear.y = 左, angular.z = 左回りが正
        float forward = Mathf.Clamp((float)lastCmd.linear.x, -maxLinear, maxLinear);
        float left = Mathf.Clamp((float)lastCmd.linear.y, -maxLinear, maxLinear); // Fetch は差動二輪なので通常 0
        float yawRate = Mathf.Clamp((float)lastCmd.angular.z, -maxAngular, maxAngular);
        if (invertForward) forward = -forward;
        if (invertTurn) yawRate = -yawRate;
        if (forward == 0f && left == 0f && yawRate == 0f) return;

        float dt = Time.fixedDeltaTime;
        Transform t = root.transform;

        // 床の上だけで動かす (傾いていても上下には動かさない)
        Vector3 fwd = Vector3.ProjectOnPlane(t.forward, Vector3.up).normalized;
        Vector3 leftDir = Vector3.Cross(fwd, Vector3.up); // Unity (左手系) で fwd × up = 左
        Vector3 pos = t.position + (fwd * forward + leftDir * left) * dt;

        // Unity の Y 軸回転は上から見て右回りが正なので、ROS の左回り正とは符号が逆
        Quaternion rot = Quaternion.AngleAxis(-yawRate * Mathf.Rad2Deg * dt, Vector3.up) * t.rotation;

        // ArticulationBody のルートは transform を直接書き換えても正しく動かないので TeleportRoot を使う
        root.TeleportRoot(pos, rot);
    }
}
