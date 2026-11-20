using UnityEngine;

/// <summary>
/// 家具 (机・箱・ごみ箱など、place_zone を持つ CoGroundSceneObject) の「ロボットが止まって作業する位置」。
/// 家具の子に空の GameObject を作って付ける (メニュー CoGround > 止まる位置を追加 でも作れる)。いくつ置いてもよい。
///
///   - 位置 = 止まったときの台車 (base_link) の中心。高さは使わない (床に置いておくと見やすい)
///   - 向き = 台車の正面。青い矢印 (Transform の +Z) を家具の方へ向ける
///   - Scene ビューに、台車の大きさの円 (半径 0.28 m) と正面の矢印が出る
///
/// CoGroundSceneObject が scene.update の approach_poses に入れて送る。動作計画 (Plan) は、
/// この家具から物を取る・この家具に置くとき、まずここに止まれるか試す (物体に近い順)。
/// だめなとき (届かない、通れない、ぶつかる) だけ、物体のまわりから自動で選ぶ。
/// どちらになったかは、Web UI の Plan の表 (動作計画の欄) と ROS のログ ([plan]) に出る。
///
/// 目安: 台車の中心を家具の縁から 0.35〜0.40 m 離す (move_base は、台車の半径 0.30 m より障害物に近い位置には止まれない)。
/// 腕が届くのは、台車の中心から前に 0.35〜0.8 m、左右に 0.35 m くらいまで。
/// </summary>
public class CoGroundApproachPoint : MonoBehaviour
{
    const float BaseRadius = 0.28f;  // Fetch の台車

    void OnDrawGizmos() => Draw(0.55f);
    void OnDrawGizmosSelected() => Draw(1f);

    void Draw(float alpha)
    {
        var p = transform.position;
        var fwd = Vector3.ProjectOnPlane(transform.forward, Vector3.up);
        if (fwd.sqrMagnitude < 1e-6f) fwd = Vector3.forward;
        fwd.Normalize();
        var color = new Color(0.1f, 0.85f, 1f, alpha);
#if UNITY_EDITOR
        UnityEditor.Handles.color = color;
        UnityEditor.Handles.DrawWireDisc(p, Vector3.up, BaseRadius);
        UnityEditor.Handles.ArrowHandleCap(0, p, Quaternion.LookRotation(fwd, Vector3.up), 0.45f, EventType.Repaint);
        var owner = GetComponentInParent<CoGroundSceneObject>();
        UnityEditor.Handles.Label(p + Vector3.up * 0.05f, $"{(owner != null ? owner.Id : "?")} 止まる位置");
#else
        Gizmos.color = color;
        Gizmos.DrawLine(p, p + fwd * 0.45f);
#endif
    }
}
