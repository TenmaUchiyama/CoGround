using System.Collections.Generic;
using UnityEngine;

/// <summary>
/// 箱の置き場所。MoveItArmPanel の Pick &amp; Place で選べるようになる。
/// 机の上面に置く: この位置 = 置いたときの箱の底面の中心、この向き = 置いたときの箱の向き。
/// 再生中は半透明の薄い板で場所を表示する (コライダーは無いので Planning Scene には入らない)。
/// </summary>
public class MoveItPlaceTarget : MonoBehaviour
{
    static readonly List<MoveItPlaceTarget> all = new List<MoveItPlaceTarget>();

    /// <summary>シーン内の置き場所 (有効なものだけ)</summary>
    public static IReadOnlyList<MoveItPlaceTarget> All => all;

    [SerializeField] Color color = new Color(0.2f, 0.6f, 1f, 0.35f);
    [Tooltip("表示する板の大きさ (左右, 前後) [m]")]
    [SerializeField] Vector2 markerSize = new Vector2(0.08f, 0.08f);
    [Tooltip("未設定なら半透明のマテリアルを作る")]
    [SerializeField] Material material;

    void OnEnable() => all.Add(this);
    void OnDisable() => all.Remove(this);

    void Start()
    {
        var plate = GameObject.CreatePrimitive(PrimitiveType.Cube);
        plate.name = "marker";
        Destroy(plate.GetComponent<Collider>());
        plate.transform.SetParent(transform, false);
        plate.transform.localPosition = new Vector3(0f, 0.001f, 0f);
        plate.transform.localScale = new Vector3(markerSize.x, 0.002f, markerSize.y);
        var r = plate.GetComponent<MeshRenderer>();
        r.sharedMaterial = material != null ? material : FetchGhost.MakeMaterial(color);
        r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
    }

    void OnDrawGizmos()
    {
        Gizmos.color = new Color(color.r, color.g, color.b, 1f);
        Gizmos.matrix = transform.localToWorldMatrix;
        Gizmos.DrawWireCube(new Vector3(0f, 0.001f, 0f), new Vector3(markerSize.x, 0.002f, markerSize.y));
        Gizmos.DrawLine(Vector3.zero, Vector3.forward * markerSize.y * 0.6f); // 前 (箱の向き)
    }
}
