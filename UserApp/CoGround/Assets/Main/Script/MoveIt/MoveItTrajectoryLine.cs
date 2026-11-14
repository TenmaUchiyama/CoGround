using System.Collections.Generic;
using RosMessageTypes.Std;
using RosMessageTypes.Trajectory;
using Unity.Robotics.ROSTCPConnector;
using UnityEngine;

/// <summary>
/// MoveIt の計画結果 (/coground/arm/planned_trajectory) で、エンドエフェクタが通る道を線で表示する。
///
/// 取り込んだ fetch (ルート) に付ける (MoveItTrajectoryPreview と一緒に使う)。
/// 緑のゴーストが計画を再生する 1 周目に、ゴーストの手先の位置を記録して線にする。
/// 順運動学を自分で計算しないので、Unity 上の URDF の形とずれない。
/// 点は fetch のローカル座標で持つので、台車が動いても線は台車について動く。
///
/// 表示するのは状態が planned の間 (showWhileExecuting なら executing の間も)。
/// </summary>
[RequireComponent(typeof(MoveItTrajectoryPreview))]
public class MoveItTrajectoryLine : MonoBehaviour
{
    [SerializeField] string trajectoryTopic = "/coground/arm/planned_trajectory";
    [SerializeField] string statusTopic = "/coground/arm/status";

    [Tooltip("線を引くリンク。wrist_roll_link = MoveIt の手先 (目標と同じ)。指先側なら gripper_link")]
    [SerializeField] string tipLinkName = "wrist_roll_link";

    [Header("見た目")]
    [Tooltip("線のマテリアル。未設定なら半透明の色から作る (Quest ビルドで表示されないときは指定する)")]
    [SerializeField] Material lineMaterial;
    [SerializeField] Color lineColor = new Color(0.1f, 1f, 0.4f, 0.9f);
    [SerializeField] float lineWidth = 0.008f;
    [Tooltip("この距離 [m] より近い点は記録しない")]
    [SerializeField] float minPointDistance = 0.003f;

    [Tooltip("実行中 (executing) も線を残す。実際の動きと計画を見比べる用")]
    [SerializeField] bool showWhileExecuting = true;

    MoveItTrajectoryPreview preview;
    Transform ghostTip;
    LineRenderer line;

    // fetch (このオブジェクト) のローカル座標
    readonly List<Vector3> localPoints = new List<Vector3>();
    Vector3[] worldPoints = new Vector3[0];
    bool recording;
    float lastPlayTime;
    string status = "";

    void Start()
    {
        preview = GetComponent<MoveItTrajectoryPreview>();

        line = new GameObject("MoveIt Planned Path Line").AddComponent<LineRenderer>();
        line.useWorldSpace = true;
        line.material = lineMaterial != null ? lineMaterial : FetchGhost.MakeMaterial(lineColor);
        line.startColor = line.endColor = lineColor;
        line.startWidth = line.endWidth = lineWidth;
        line.numCapVertices = 4;
        line.numCornerVertices = 2;
        line.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
        line.receiveShadows = false;
        line.positionCount = 0;
        line.enabled = false;

        var ros = ROSConnection.GetOrCreateInstance();
        ros.Subscribe<JointTrajectoryMsg>(trajectoryTopic, OnTrajectory);
        ros.Subscribe<StringMsg>(statusTopic, msg => status = msg.data);
    }

    void OnTrajectory(JointTrajectoryMsg msg)
    {
        // 新しい計画 (失敗時は空の軌道が来る) → 線を作り直す
        localPoints.Clear();
        line.positionCount = 0;
        recording = msg.points.Length > 0;
        lastPlayTime = 0f;
    }

    bool FindGhostTip()
    {
        if (ghostTip != null) return true;
        var ghost = preview.Ghost;
        if (ghost == null) return false; // Preview の Start がまだ
        foreach (var t in ghost.GetComponentsInChildren<Transform>(true))
        {
            if (t.name == tipLinkName) { ghostTip = t; return true; }
        }
        Debug.LogError($"[MoveItTrajectoryLine] ゴーストに {tipLinkName} が見つからない");
        enabled = false;
        return false;
    }

    // ゴーストの関節は FixedUpdate で書き込まれ、物理の更新後に Transform に反映されるので LateUpdate で読む
    void LateUpdate()
    {
        if (!FindGhostTip()) return;

        if (recording && preview.IsShowing) Record();

        bool show = localPoints.Count > 1 &&
                    (status.StartsWith("planned") || (showWhileExecuting && status.StartsWith("executing")));
        line.enabled = show;
        if (show) Draw();
    }

    void Record()
    {
        float t = preview.PlayTime;
        // 再生が最初に戻った (= 1 周終わった) か、最後まで来たら記録をやめる
        if (t < lastPlayTime || t >= preview.Duration)
        {
            if (t >= preview.Duration) AddPoint(ghostTip.position);
            recording = false;
            return;
        }
        lastPlayTime = t;
        AddPoint(ghostTip.position);
    }

    void AddPoint(Vector3 world)
    {
        var local = transform.InverseTransformPoint(world);
        if (localPoints.Count > 0 &&
            (local - localPoints[localPoints.Count - 1]).sqrMagnitude < minPointDistance * minPointDistance)
        {
            return;
        }
        localPoints.Add(local);
    }

    void Draw()
    {
        if (worldPoints.Length != localPoints.Count) worldPoints = new Vector3[localPoints.Count];
        for (int i = 0; i < localPoints.Count; i++) worldPoints[i] = transform.TransformPoint(localPoints[i]);
        line.positionCount = worldPoints.Length;
        line.SetPositions(worldPoints);
    }

    void OnDestroy()
    {
        if (line != null) Destroy(line.gameObject);
    }
}
