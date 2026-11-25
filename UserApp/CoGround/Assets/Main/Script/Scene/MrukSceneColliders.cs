using System.Collections.Generic;
using Meta.XR.MRUtilityKit;
using UnityEngine;

/// <summary>
/// MRUK の部屋 (Scene Data) のアンカーを箱コライダーにして、Navigation と MoveIt の両方に渡す。
///
///   MRUK のアンカー ──▶ 箱 (BoxCollider) ─┬─ MoveItCollisionBox ──▶ Planning Scene (腕の衝突)
///                                          └─ NavMapPublisher が Physics で拾う ──▶ move_base の地図
///
///   - 体積のあるアンカー (TABLE, COUCH, STORAGE など) = VolumeBounds の箱
///   - 平面のアンカー (WALL_FACE, FLOOR, CEILING など) = PlaneRect に厚みを付けた箱 (面の裏側に出す)
///   - FLOOR は NavMapPublisher の床にする。MoveIt には送らない (台車が常に床と衝突してしまうため)
///
/// シーンに MRUK プレハブを置き、適当な GameObject にこれを付ける。
/// 実機がなくても、MRUK の Data Source を Prefab / JSON にすればエディタで動く。
/// 部屋の Unity ワールド座標をそのまま ROS の world として送るので、ロボットも同じ座標系に置くこと。
/// </summary>
public class MrukSceneColliders : MonoBehaviour
{
    [Tooltip("床を渡す先。未設定ならシーンから探す")]
    [SerializeField] NavMapPublisher navMap;

    [Tooltip("箱を作らないラベル (壁に貼り付いた枠や、形が箱でないもの)")]
    [SerializeField] MRUKAnchor.SceneLabels ignoreLabels =
        MRUKAnchor.SceneLabels.DOOR_FRAME | MRUKAnchor.SceneLabels.WINDOW_FRAME |
        MRUKAnchor.SceneLabels.WALL_ART | MRUKAnchor.SceneLabels.GLOBAL_MESH |
        MRUKAnchor.SceneLabels.INVISIBLE_WALL_FACE;

    [Tooltip("箱は作るが MoveIt には送らないラベル (Navigation だけで使う)")]
    [SerializeField] MRUKAnchor.SceneLabels noMoveItLabels = MRUKAnchor.SceneLabels.FLOOR;

    [Tooltip("平面 (壁・床・天井) に付ける厚み [m]")]
    [SerializeField] float planeThickness = 0.05f;

    [Tooltip("生成する箱のレイヤー (NavMapPublisher の obstacleMask に含まれること)")]
    [SerializeField] int colliderLayer = 0;

    [Tooltip("ロボット (この Transform 以下のコライダーとは物理的にぶつけない)。未設定なら RosJointToFetch を探す")]
    [SerializeField] Transform robot;

    readonly List<GameObject> spawned = new List<GameObject>();
    Collider[] robotColliders = new Collider[0];

    void Start()
    {
        if (MRUK.Instance == null)
        {
            Debug.LogError("[MrukSceneColliders] MRUK がシーンにない。MRUK プレハブを置くこと");
            enabled = false;
            return;
        }
        if (navMap == null) navMap = FindAnyObjectByType<NavMapPublisher>();
        MRUK.Instance.RegisterSceneLoadedCallback(Rebuild); // 読み込み済みならその場で呼ばれる
    }

    void OnDestroy() => Clear();

    /// <summary>読み込まれている全部の部屋から箱を作り直す (部屋を読み込み直した後に呼んでもよい)</summary>
    public void Rebuild()
    {
        Clear();

        // 読み込まれている部屋を全部使う (リビング + キッチンのように複数あっても 1 枚の地図にする)
        var rooms = MRUK.Instance != null ? MRUK.Instance.Rooms : null;
        if (rooms == null || rooms.Count == 0)
        {
            Debug.LogWarning("[MrukSceneColliders] 部屋がない");
            return;
        }
        var anchors = new List<MRUKAnchor>();
        foreach (var room in rooms) if (room != null) anchors.AddRange(room.Anchors);

        if (robot == null)
        {
            var r = FindAnyObjectByType<RosJointToFetch>();
            if (r != null) robot = r.transform;
            else Debug.LogWarning("[MrukSceneColliders] ロボットが見つからない。部屋の箱とロボットが物理的にぶつかる");
        }
        robotColliders = robot != null ? robot.GetComponentsInChildren<Collider>(true) : new Collider[0];

        var floors = new List<Collider>();
        int index = 0, sentToMoveIt = 0;
        foreach (var anchor in anchors)
        {
            if (anchor == null || (anchor.Label & ignoreLabels) != 0) continue;

            Vector3 center, size;
            if (anchor.VolumeBounds is Bounds volume) // 机などは平面 (天板) も持つので、体積を先に見る
            {
                center = volume.center;
                size = volume.size;
            }
            else if (anchor.PlaneRect is Rect rect)
            {
                // 平面はアンカーのローカル XY、法線は +Z (部屋の内側)。厚みは裏側 (-Z) に出す
                center = new Vector3(rect.center.x, rect.center.y, -planeThickness * 0.5f);
                size = new Vector3(rect.width, rect.height, planeThickness);
            }
            else continue;

            // Planning Scene での名前になるので、部屋の中で重複させない
            var go = new GameObject($"mruk_{anchor.Label}_{index++}".ToLowerInvariant());
            go.layer = colliderLayer;
            go.transform.SetParent(anchor.transform, false);
            var box = go.AddComponent<BoxCollider>();
            box.center = center;
            box.size = size;
            // 箱は地図と MoveIt のためのもの。ロボットとぶつけると、部屋の中に置かれたロボットの関節
            // (ArticulationBody) が箱から押し出されて部品が飛び散るので、物理の衝突だけ切る
            foreach (var rc in robotColliders) if (rc != null) Physics.IgnoreCollision(box, rc, true);
            spawned.Add(go);

            if ((anchor.Label & MRUKAnchor.SceneLabels.FLOOR) != 0) floors.Add(box);
            if ((anchor.Label & noMoveItLabels) == 0)
            {
                go.AddComponent<MoveItCollisionBox>();
                sentToMoveIt++;
            }
        }

        if (navMap != null) navMap.SetFloors(floors);
        else Debug.LogWarning("[MrukSceneColliders] NavMapPublisher がない。Navigation の地図は送られない");
        if (floors.Count == 0) Debug.LogWarning("[MrukSceneColliders] FLOOR のアンカーがない。Navigation の地図は作れない");

        Debug.Log($"[MrukSceneColliders] 部屋 {rooms.Count} 個、箱 {spawned.Count} 個 (MoveIt {sentToMoveIt} 個、床 {floors.Count} 個)");
    }

    void Clear()
    {
        if (spawned.Count > 0 && navMap != null) navMap.SetFloors(new List<Collider>()); // 消える床を参照させない
        foreach (var go in spawned)
        {
            if (go != null) Destroy(go); // MoveItCollisionBox が OnDisable で ROS 側からも消す
        }
        spawned.Clear();
    }
}
