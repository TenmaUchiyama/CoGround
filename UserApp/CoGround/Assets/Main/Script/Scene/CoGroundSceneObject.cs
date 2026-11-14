using System;
using System.Collections.Generic;
using System.Globalization;
using UnityEngine;

/// <summary>
/// シミュレーション用の物体 (食器、ごみ、シンク、ごみ箱、机など) に付ける。
/// CoGroundSceneReporter がこれを集めて scene.update で送る。値はすべて真値 (ground_truth) として送る。
///
/// ■ 設定
///   - Category: 物体の種類。role (item / receptacle / surface) はサーバーがカテゴリから決める
///   - Attributes: 属性の真値 (例: fragile = true、material = glass)。語彙は AttributeKey
///   - Place Zone: シンク・ごみ箱・机など「置く / 入れる場所」だけ設定する。
///     子に空の GameObject を作り、その位置・向き・スケール (= 大きさ [m]) で範囲を表す。
///     机なら上面の上の空間、ごみ箱なら内側。サーバーはこれをこの物体と同じ ID の領域にし、
///     物体の中心がこの範囲に入っていると、その物体の region_id をこの ID にする
///
/// ■ 位置と大きさ
///   BoxCollider があればその箱、無ければ MeshFilter のメッシュの範囲、どちらも無ければ Renderer の範囲を使う。
///
/// ■ ID
///   Object Id が空なら、MoveItCollisionBox の名前 (無ければ GameObject の名前) を使う。MoveIt と ID を揃えるため。
/// </summary>
public class CoGroundSceneObject : MonoBehaviour, ICoGroundSceneSource
{
    [Serializable]
    public class AttributeEntry
    {
        public string key;
        [Tooltip("true / false、数値、文字列のどれか")]
        public string value;
    }

    static readonly List<CoGroundSceneObject> all = new List<CoGroundSceneObject>();

    /// <summary>シーン内の物体 (有効なものだけ)</summary>
    public static IReadOnlyList<CoGroundSceneObject> All => all;

    [Tooltip("空なら MoveItCollisionBox の名前、無ければ GameObject の名前")]
    [SerializeField] string objectId = "";
    [SerializeField] CoGroundCategory category = CoGroundCategory.cup;
    [SerializeField] List<AttributeEntry> attributes = new List<AttributeEntry>();
    [Tooltip("置く / 入れる場所の範囲 (receptacle・surface のみ)。位置・向き・スケール = 範囲の中心・向き・大きさ")]
    [SerializeField] Transform placeZone;

    public string Id
    {
        get
        {
            if (!string.IsNullOrEmpty(objectId)) return objectId;
            var box = GetComponent<MoveItCollisionBox>();
            return box != null ? box.ObjectName : gameObject.name;
        }
    }

    public CoGroundCategory Category => category;

    void OnEnable() => all.Add(this);
    void OnDisable() => all.Remove(this);

    public void CollectObjects(List<SceneObjectDto> into) => into.Add(ToDto());

    public SceneObjectDto ToDto()
    {
        GetBounds(out var center, out var rotation, out var size);
        var dto = new SceneObjectDto
        {
            Id = Id,
            Category = category.ToString(),
            Position = SceneJson.V(center),
            Rotation = SceneJson.Q(rotation),
            Size = SceneJson.V(size),
            Observation = new ObservationDto { Source = ObjectSource.Simulation, Tracking = TrackingState.Tracked, LastSeen = Time.time },
        };
        foreach (var a in attributes)
        {
            if (string.IsNullOrWhiteSpace(a.key)) continue;
            dto.Attributes[a.key.Trim()] = new AttributeDto { Value = ParseValue(a.value), Source = AttributeSource.GroundTruth };
        }
        if (placeZone != null)
            dto.PlaceZone = BoxDto.From(placeZone.position, placeZone.rotation, Abs(placeZone.lossyScale));
        return dto;
    }

    /// <summary>bbox の中心 (ワールド)・向き・大きさ (ローカル軸、m)</summary>
    void GetBounds(out Vector3 center, out Quaternion rotation, out Vector3 size)
    {
        var scale = Abs(transform.lossyScale);
        if (TryGetComponent<BoxCollider>(out var bc))
        {
            center = transform.TransformPoint(bc.center);
            rotation = transform.rotation;
            size = Vector3.Scale(bc.size, scale);
            return;
        }
        if (TryGetComponent<MeshFilter>(out var mf) && mf.sharedMesh != null)
        {
            var b = mf.sharedMesh.bounds;
            center = transform.TransformPoint(b.center);
            rotation = transform.rotation;
            size = Vector3.Scale(b.size, scale);
            return;
        }
        // 子にメッシュがある場合など: ワールド軸の範囲 (向きは無し)
        var renderers = GetComponentsInChildren<Renderer>();
        if (renderers.Length > 0)
        {
            var b = renderers[0].bounds;
            for (int i = 1; i < renderers.Length; i++) b.Encapsulate(renderers[i].bounds);
            center = b.center;
            rotation = Quaternion.identity;
            size = b.size;
            return;
        }
        center = transform.position;
        rotation = transform.rotation;
        size = scale;
    }

    static object ParseValue(string s)
    {
        s = (s ?? "").Trim();
        if (bool.TryParse(s, out var b)) return b;
        if (float.TryParse(s, NumberStyles.Float, CultureInfo.InvariantCulture, out var f)) return f;
        return s;
    }

    static Vector3 Abs(Vector3 v) => new Vector3(Mathf.Abs(v.x), Mathf.Abs(v.y), Mathf.Abs(v.z));

    void OnDrawGizmosSelected()
    {
        if (placeZone == null) return;
        Gizmos.color = new Color(0.2f, 0.9f, 0.4f, 0.8f);
        Gizmos.matrix = Matrix4x4.TRS(placeZone.position, placeZone.rotation, Vector3.one);
        Gizmos.DrawWireCube(Vector3.zero, Abs(placeZone.lossyScale));
    }
}
