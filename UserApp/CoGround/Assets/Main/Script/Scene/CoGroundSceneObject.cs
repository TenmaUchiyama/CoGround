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
///     机なら上面の上の空間、ごみ箱なら内側。選択中は黄色の枠で見える (見た目や BoxCollider には追従しない)。
///     サーバーはこれをこの物体と同じ ID の領域にし、
///     物体の中心がこの範囲に入っていると、その物体の region_id をこの ID にする
///   - 止まる位置: 置く場所 (place_zone を持つ物) には、子に CoGroundApproachPoint を置いて
///     「ロボットが止まって作業する位置と向き」を決めておける (approach_poses で送る)。Inspector のボタンで足せる
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

    /// <summary>置く / 入れる場所の範囲 (無ければ null)</summary>
    public Transform PlaceZone => placeZone;
    /// <summary>置く場所 (place_zone を持つ。箱・ごみ箱・机など)</summary>
    public bool IsPlace => placeZone != null;
    /// <summary>ロボットが止まって作業する位置 (子の CoGroundApproachPoint)</summary>
    public CoGroundApproachPoint[] ApproachPoints => GetComponentsInChildren<CoGroundApproachPoint>();

    /// <summary>ロボットが運べる物 (MoveItPickable が付いている)</summary>
    public bool IsPickable => GetComponent<MoveItPickable>() != null;

    /// <summary>実行中に作った物体の設定 (Inspector で設定する代わり)。EnvironmentBoxPlaces が使う</summary>
    public void Configure(string id, CoGroundCategory category, Transform placeZone)
    {
        objectId = id;
        this.category = category;
        this.placeZone = placeZone;
    }

    /// <summary>ID で探す (無ければ null)</summary>
    public static CoGroundSceneObject Find(string id)
    {
        foreach (var o in all) if (o.Id == id) return o;
        return null;
    }

    /// <summary>運べる物の一覧</summary>
    public static List<CoGroundSceneObject> Items()
    {
        var r = new List<CoGroundSceneObject>();
        foreach (var o in all) if (o.IsPickable) r.Add(o);
        return r;
    }

    /// <summary>置く場所の一覧 (includeSurfaces = false なら机・棚を除く)</summary>
    public static List<CoGroundSceneObject> Places(bool includeSurfaces = false)
    {
        var r = new List<CoGroundSceneObject>();
        foreach (var o in all)
        {
            if (!o.IsPlace) continue;
            if (!includeSurfaces && (o.category == CoGroundCategory.table || o.category == CoGroundCategory.shelf)) continue;
            r.Add(o);
        }
        return r;
    }

    /// <summary>属性の値 (bool / float / string)。無ければ false</summary>
    public bool TryGetAttribute(string key, out object value)
    {
        foreach (var a in attributes)
        {
            if (a.key != null && a.key.Trim() == key) { value = ParseValue(a.value); return true; }
        }
        value = null;
        return false;
    }

    /// <summary>bool の属性 (無い・bool でなければ false)。例: GetBool(AttributeKey.Fragile)</summary>
    public bool GetBool(string key) => TryGetAttribute(key, out var v) && v is bool b && b;

    public bool IsFragile => GetBool(AttributeKey.Fragile);
    public bool IsTrash => GetBool(AttributeKey.Trash);

    /// <summary>ワールド座標の点がこの物の place_zone の中にあるか</summary>
    public bool ZoneContains(Vector3 worldPoint)
    {
        if (placeZone == null) return false;
        Vector3 local = Quaternion.Inverse(placeZone.rotation) * (worldPoint - placeZone.position);
        Vector3 half = Abs(placeZone.lossyScale) / 2f;
        return Mathf.Abs(local.x) <= half.x && Mathf.Abs(local.y) <= half.y && Mathf.Abs(local.z) <= half.z;
    }

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
        foreach (var a in ApproachPoints)
        {
            if (!a.isActiveAndEnabled) continue;
            (dto.ApproachPoses ??= new List<PoseDto>()).Add(PoseDto.From(a.transform.position, a.transform.rotation));
        }
        return dto;
    }

    /// <summary>
    /// サーバーに送っている姿勢 (bbox の中心と向き) を、この物体の Transform から見た姿勢に直すための値。
    /// 送った姿勢を pose とすると、Transform は pose * (返り値の localPosition, localRotation) にある。
    /// </summary>
    public void GetTransformInReportedFrame(out Vector3 localPosition, out Quaternion localRotation)
    {
        GetBounds(out var center, out var rotation, out _);
        var inv = Quaternion.Inverse(rotation);
        localPosition = inv * (transform.position - center);
        localRotation = inv * transform.rotation;
    }

    /// <summary>サーバーに送っている箱 (bbox の中心・向き・大きさ [m])。Renderer を切っていても同じ値</summary>
    public void GetBox(out Vector3 center, out Quaternion rotation, out Vector3 size) =>
        GetBounds(out center, out rotation, out size);

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

    // place_zone は黄色 (MoveItCollisionBox の当たり判定の緑と見分けるため)。
    // この物体を選んだときだけでなく、place_zone 自身を選んだときも描く (place_zone は空の GameObject で、自分では何も描かないため)
    void OnDrawGizmos()
    {
        if (placeZone == null) return;
#if UNITY_EDITOR
        var sel = UnityEditor.Selection.activeTransform;
        if (sel == null || (sel != transform && sel != placeZone)) return;
#else
        return;
#endif
        Gizmos.color = new Color(1f, 0.85f, 0.1f, 0.9f);
        Gizmos.matrix = Matrix4x4.TRS(placeZone.position, placeZone.rotation, Vector3.one);
        Gizmos.DrawWireCube(Vector3.zero, Abs(placeZone.lossyScale));
#if UNITY_EDITOR
        UnityEditor.Handles.color = Gizmos.color;
        UnityEditor.Handles.Label(placeZone.position + Vector3.up * Abs(placeZone.lossyScale).y / 2f, $"{Id} place_zone");
#endif
    }
}
