using System.Collections.Generic;
using UnityEngine;

/// <summary>
/// (確認用) ゴースト (FetchGhostRig) の関節の回し方が、本物の Fetch (ArticulationBody) と一致しているかを確かめる。
/// 本物の Fetch (RosJointToFetch が付いたもの) に付けて Play する。ROS から関節角が届いている状態で、
/// 数秒ごとに「本物と同じ台車の位置・関節角にしたゴースト」と本物の各リンクの位置を比べ、ずれの最大をログに出す。
/// ずれが 1 cm 以下なら一致している。確認が終わったら外す (このスクリプトだけは確認のために本物を読む)。
/// </summary>
public class FetchGhostRigCheck : MonoBehaviour
{
    [SerializeField] float intervalSeconds = 3f;
    [Tooltip("ゴーストを表示して見比べる")]
    [SerializeField] bool showGhost = true;

    FetchGhostRig rig;
    readonly List<(Transform real, Transform ghost)> links = new List<(Transform, Transform)>();
    Transform realBase;
    float next;

    void Start()
    {
        rig = FetchGhostRig.Create("Ghost Check", FetchGhost.MakeMaterial(new Color(1f, 0.2f, 0.8f, 0.4f)));
        if (rig == null) { enabled = false; return; }
        foreach (var body in GetComponentsInChildren<ArticulationBody>())
        {
            if (body.name == "base_link") realBase = body.transform;
            if (rig.TryGetLink(body.name, out var g)) links.Add((body.transform, g));
        }
        if (realBase == null) realBase = transform;
        rig.Visible = showGhost;
    }

    void LateUpdate()
    {
        if (rig == null) return;
        // 本物と同じ台車の位置 + 本物の関節角 (ArticulationBody の jointPosition) にする
        rig.SetBasePose(realBase.position, realBase.rotation);
        foreach (var body in GetComponentsInChildren<ArticulationBody>())
        {
            if (body.isRoot || body.dofCount == 0) continue;
            string joint = body.name.EndsWith("_link") ? body.name.Substring(0, body.name.Length - 5) + "_joint" : body.name;
            rig.SetJoint(joint, body.jointPosition[0]);
        }

        if (Time.time < next) return;
        next = Time.time + intervalSeconds;
        float worst = 0f;
        string worstName = "";
        foreach (var (real, ghost) in links)
        {
            float d = Vector3.Distance(real.position, ghost.position);
            if (d > worst) { worst = d; worstName = real.name; }
        }
        string verdict = worst <= 0.01f ? "一致" : "ずれている (関節の向き・軸を確認)";
        Debug.Log($"[FetchGhostRigCheck] リンク {links.Count} 個、最大のずれ {worst * 100f:F1} cm ({worstName}): {verdict}");
    }

    void OnDestroy()
    {
        if (rig != null) Destroy(rig.gameObject);
    }
}
