using System.Collections.Generic;
using Newtonsoft.Json;
using UnityEngine;

/// <summary>
/// scene.update で送る型。サーバー側の定義は Backend/grounding_server/coground_server/models.py (リモート japan-lab)。
///
/// ■ シミュレーションと検出で同じ型を使う
///   どちらも SceneObjectDto を作って送る。違うのは observation.source と、属性の source だけ。
///     - シミュレーション: CoGroundSceneObject が作る (source = "simulation"、属性は "ground_truth")
///     - 検出 (後で): ICoGroundSceneSource を実装したコンポーネントが作る (source = "detection")
///   CoGroundSceneReporter が全部を集めて 1 つの SceneSnapshotDto にして送る。
///
/// ■ 省略してよいもの
///   role / group はサーバーがカテゴリ表 (coground_server/taxonomy.py) から埋める。
///   region_id (どの領域にあるか) は、省略するとサーバーが求める (中心を含むいちばん小さい box の領域)。
///   place_zone を持つ物体 (シンク、ごみ箱、机) は、その物体と同じ ID の領域になる。
///   ルールの target_region や Plan の region_id には、その ID (例: "sink_1") がそのまま入る。
/// </summary>
public class SceneSnapshotDto
{
    [JsonProperty("frame")] public string Frame = "unity_world";
    [JsonProperty("captured_at", NullValueHandling = NullValueHandling.Ignore)] public float? CapturedAt;
    [JsonProperty("objects")] public List<SceneObjectDto> Objects = new List<SceneObjectDto>();
}

public class SceneObjectDto
{
    [JsonProperty("id")] public string Id;
    /// <summary>正規化したカテゴリ (CoGroundCategory の名前)。検出器の生のラベルは observation.detector_label</summary>
    [JsonProperty("category")] public string Category;
    /// <summary>item / receptacle / surface。null ならサーバーが埋める</summary>
    [JsonProperty("role", NullValueHandling = NullValueHandling.Ignore)] public string Role;
    [JsonProperty("group", NullValueHandling = NullValueHandling.Ignore)] public string Group;
    /// <summary>bbox の中心 (Unity ワールド座標)</summary>
    [JsonProperty("position")] public float[] Position;
    [JsonProperty("rotation")] public float[] Rotation;
    /// <summary>bbox の大きさ (ローカル軸)</summary>
    [JsonProperty("size", NullValueHandling = NullValueHandling.Ignore)] public float[] Size;
    [JsonProperty("attributes")] public Dictionary<string, AttributeDto> Attributes = new Dictionary<string, AttributeDto>();
    /// <summary>いまどの領域にあるか。null ならサーバーが埋める</summary>
    [JsonProperty("region_id", NullValueHandling = NullValueHandling.Ignore)] public string RegionId;
    /// <summary>receptacle / surface のみ: 物を置ける・入れられる範囲。この物体と同じ ID の領域になる</summary>
    [JsonProperty("place_zone", NullValueHandling = NullValueHandling.Ignore)] public BoxDto PlaceZone;
    [JsonProperty("observation")] public ObservationDto Observation = new ObservationDto();
}

public class BoxDto
{
    [JsonProperty("center")] public float[] Center;
    [JsonProperty("rotation")] public float[] Rotation;
    [JsonProperty("size")] public float[] Size;

    public static BoxDto From(Vector3 center, Quaternion rotation, Vector3 size) => new BoxDto
    {
        Center = SceneJson.V(center), Rotation = SceneJson.Q(rotation), Size = SceneJson.V(size),
    };
}

public class AttributeDto
{
    /// <summary>bool / float / string</summary>
    [JsonProperty("value")] public object Value;
    /// <summary>ground_truth / detector / vlm / user</summary>
    [JsonProperty("source")] public string Source = AttributeSource.GroundTruth;
    [JsonProperty("confidence", NullValueHandling = NullValueHandling.Ignore)] public float? Confidence;
}

public class ObservationDto
{
    /// <summary>simulation / detection / manual</summary>
    [JsonProperty("source")] public string Source = ObjectSource.Simulation;
    [JsonProperty("detector_label", NullValueHandling = NullValueHandling.Ignore)] public string DetectorLabel;
    [JsonProperty("confidence", NullValueHandling = NullValueHandling.Ignore)] public float? Confidence;
    /// <summary>tracked / occluded / lost</summary>
    [JsonProperty("tracking")] public string Tracking = TrackingState.Tracked;
    [JsonProperty("last_seen", NullValueHandling = NullValueHandling.Ignore)] public float? LastSeen;
    [JsonProperty("image_id", NullValueHandling = NullValueHandling.Ignore)] public string ImageId;
}

public static class ObjectSource
{
    public const string Simulation = "simulation", Detection = "detection", Manual = "manual";
}

public static class AttributeSource
{
    public const string GroundTruth = "ground_truth", Detector = "detector", Vlm = "vlm", User = "user";
}

public static class TrackingState
{
    public const string Tracked = "tracked", Occluded = "occluded", Lost = "lost";
}

/// <summary>
/// カテゴリ。名前がそのまま category の文字列になる。
/// サーバーのカテゴリ表 (coground_server/taxonomy.py の CATEGORIES) と揃える。
/// 検出器は表に無い名前を送ってもよい (サーバーは item / other として扱う)。
/// </summary>
public enum CoGroundCategory
{
    // 食器
    plate, bowl, cup, mug, glass,
    // カトラリー
    fork, spoon, knife, chopsticks,
    // ごみ
    can, plastic_bottle, paper_cup, tissue, wrapper, food_waste,
    // 入れる場所 (receptacle)
    sink, trash_bin, dish_rack,
    // 置く場所 (surface)
    table, shelf,
}

/// <summary>
/// 属性の語彙 (サーバーの taxonomy.ATTRIBUTES と同じ)。
///   material   : glass | ceramic | plastic | metal | paper | wood
///   fragile    : true | false
///   dirty      : true | false
///   contents   : empty | liquid | food
///   waste_type : burnable | plastic | can | bottle (ごみ箱では受け付ける分別)
/// </summary>
public static class AttributeKey
{
    public const string Material = "material", Fragile = "fragile", Dirty = "dirty",
        Contents = "contents", WasteType = "waste_type";
}

/// <summary>シーンの物体を出すもの。シミュレーションでも検出でも、これを実装して CoGroundSceneReporter に登録する。</summary>
public interface ICoGroundSceneSource
{
    void CollectObjects(List<SceneObjectDto> into);
}

public static class SceneJson
{
    public static float[] V(Vector3 v) => new[] { v.x, v.y, v.z };
    public static float[] Q(Quaternion q) => new[] { q.x, q.y, q.z, q.w };
}
