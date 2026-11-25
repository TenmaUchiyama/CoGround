using System.Text;
using Meta.XR.MRUtilityKit;
using UnityEngine;

/// <summary>
/// MRUK の部屋 (Scene Data) を見るだけのテスト。
/// Play 中、アンカーごとに箱 (体積 = VolumeBounds、平面 = PlaneRect) とラベル名を Scene ビューに描く。
/// 読み込めたアンカーの一覧は Console にも出す。
/// 箱の作り方は MrukSceneColliders と同じなので、ROS に送る前の形の確認にも使える。
/// Game ビューで見るときは Gizmos ボタンをオンにする。
/// </summary>
public class SceneDataGizmos : MonoBehaviour
{
    [Tooltip("平面 (壁・床・天井) を描くときの厚み [m]")]
    [SerializeField] float planeThickness = 0.05f;
    [SerializeField] bool drawLabels = true;
    [Tooltip("描かないラベル")]
    [SerializeField] MRUKAnchor.SceneLabels hideLabels = MRUKAnchor.SceneLabels.GLOBAL_MESH;

    void Start()
    {
        if (MRUK.Instance == null)
        {
            Debug.LogError("[SceneDataGizmos] MRUK がシーンにない");
            return;
        }
        MRUK.Instance.RegisterSceneLoadedCallback(LogAnchors);
    }

    void LogAnchors()
    {
        var sb = new StringBuilder();
        foreach (var room in MRUK.Instance.Rooms)
        {
            sb.AppendLine($"[SceneDataGizmos] 部屋 {room.name}: アンカー {room.Anchors.Count} 個");
            foreach (var a in room.Anchors)
            {
                string shape = TryGetBox(a, out _, out var size) ? $"{size.x:F2} x {size.y:F2} x {size.z:F2} m" : "形なし";
                string kind = a.VolumeBounds.HasValue ? "体積" : a.PlaneRect.HasValue ? "平面" : "-";
                sb.AppendLine($"  {a.Label,-20} {kind}  {shape}  位置 {a.transform.position:F2}");
            }
        }
        Debug.Log(sb.ToString());
    }

    /// <summary>アンカーのローカル座標での箱 (MrukSceneColliders と同じ作り方)</summary>
    bool TryGetBox(MRUKAnchor anchor, out Vector3 center, out Vector3 size)
    {
        if (anchor.VolumeBounds is Bounds volume)
        {
            center = volume.center;
            size = volume.size;
            return true;
        }
        if (anchor.PlaneRect is Rect rect)
        {
            center = new Vector3(rect.center.x, rect.center.y, -planeThickness * 0.5f);
            size = new Vector3(rect.width, rect.height, planeThickness);
            return true;
        }
        center = size = Vector3.zero;
        return false;
    }

    static Color ColorOf(MRUKAnchor.SceneLabels label)
    {
        if ((label & MRUKAnchor.SceneLabels.FLOOR) != 0) return new Color(0.3f, 0.8f, 0.3f);
        if ((label & MRUKAnchor.SceneLabels.CEILING) != 0) return new Color(0.6f, 0.6f, 0.6f);
        if ((label & (MRUKAnchor.SceneLabels.WALL_FACE | MRUKAnchor.SceneLabels.INNER_WALL_FACE)) != 0) return new Color(0.3f, 0.6f, 1f);
        if ((label & (MRUKAnchor.SceneLabels.DOOR_FRAME | MRUKAnchor.SceneLabels.WINDOW_FRAME | MRUKAnchor.SceneLabels.WALL_ART)) != 0) return new Color(1f, 0.9f, 0.2f);
        return new Color(1f, 0.4f, 0.2f); // 家具など
    }

    void OnDrawGizmos()
    {
        if (!Application.isPlaying || MRUK.Instance == null) return;

        foreach (var room in MRUK.Instance.Rooms)
        {
            if (room == null) continue;
            foreach (var a in room.Anchors)
            {
                if (a == null || (a.Label & hideLabels) != 0) continue;
                if (!TryGetBox(a, out var center, out var size)) continue;

                var c = ColorOf(a.Label);
                Gizmos.matrix = a.transform.localToWorldMatrix;
                Gizmos.color = new Color(c.r, c.g, c.b, 0.15f);
                Gizmos.DrawCube(center, size);
                Gizmos.color = c;
                Gizmos.DrawWireCube(center, size);
#if UNITY_EDITOR
                if (drawLabels) UnityEditor.Handles.Label(a.transform.TransformPoint(center), a.Label.ToString());
#endif
            }
        }
        Gizmos.matrix = Matrix4x4.identity;
    }
}
