using System;
using UnityEngine;

/// <summary>
/// VR 上の Fetch に付けて、シミュレーションか本物のロボットかを切り替える。
///
///   シミュレーション (Use Real Robot = false): この Fetch を普通のオブジェクトとして表示し、本物の代わりにする。
///                                             ROS の値で動き、つかんだ箱もこの Fetch の手に付く
///   本物のロボット   (Use Real Robot = true) : Play 開始時に、この Fetch を表示しない・当たり判定も切る。
///                                             下の一覧 (シミュレーションで Fetch を動かす・Fetch の位置を ROS に送るもの) も無効にする
///
/// どちらでも、計画のゴースト (FetchGhostRig) はこの Fetch を読まないので同じように出る。
/// インスペクタに一覧と今の状態を出す (Editor/FetchRobotModeInfoEditor)。
/// </summary>
[DisallowMultipleComponent]
[DefaultExecutionOrder(-1000)] // 一覧のコンポーネントの Awake / Start より先に止める
public class FetchRobotModeInfo : MonoBehaviour
{
    /// <summary>本物のロボットを使うときに無効にするもの</summary>
    public static readonly (Type type, string reason)[] DisableForRealRobot =
    {
        (typeof(RosJointToFetch), "ROS の関節角でこの Fetch を動かす"),
        (typeof(RosBasePoseToFetch), "ROS の台車の位置でこの Fetch を動かす / 初期位置を ROS に送る (NAV=true のシミュレーション用)"),
        (typeof(FetchBasePosePublisher), "この Fetch の位置を ROS の TF (world → base_link) として送る。本物では台車の位置は本物が決める"),
        (typeof(FetchCmdVelDriver), "cmd_vel でこの Fetch を動かす (シミュレーション用)"),
        (typeof(BaseNavigator), "Unity だけのナビでこの Fetch を動かす (ROS を使わない確認用)"),
    };

    [Tooltip("本物のロボットを使う。Play 開始時にこの Fetch を隠し、一覧のコンポーネントを無効にする。" +
             "false (シミュレーション) なら、この Fetch が本物の代わりになる")]
    [SerializeField] bool useRealRobot = false;

    public bool UseRealRobot => useRealRobot;

    /// <summary>シーンにシミュレーション用の Fetch (本物の代わり) があるか</summary>
    public static bool SimulatedRobotPresent()
    {
        var info = FindAnyObjectByType<FetchRobotModeInfo>();
        return info == null || !info.useRealRobot;
    }

    void Awake()
    {
        if (!useRealRobot) return;
        foreach (var (type, _) in DisableForRealRobot)
            if (GetComponent(type) is Behaviour b) b.enabled = false;
        foreach (var r in GetComponentsInChildren<Renderer>(true)) r.enabled = false;
        foreach (var c in GetComponentsInChildren<Collider>(true)) c.enabled = false;
        Debug.Log($"[FetchRobotModeInfo] 本物のロボットを使う: {name} を隠し、シミュレーション用のコンポーネントを無効にした");
    }
}
