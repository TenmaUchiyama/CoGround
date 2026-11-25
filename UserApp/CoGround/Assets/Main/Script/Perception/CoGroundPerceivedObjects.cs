using System;
using System.Collections.Generic;
using Newtonsoft.Json;
using UnityEngine;

/// <summary>
/// カメラで認識した物体を、ルール照合のシーン (scene.update) に入れる。
///
///   CoGroundFrameSender ─ POST /perception/frame (RGB + 深度)
///      │ 答え: 物体ごとの object_id・種類・3D の位置と大きさ (サーバーが検出し、新しい物体だけ VLM に聞く)
///      ▼
///   CoGroundPerceivedObjects (ここ) … 物体を object_id ごとに覚える
///      │ ICoGroundSceneSource
///      ▼
///   CoGroundSceneReporter ─ scene.update (observation.source = detection)
///      ▼
///   サーバー: 物体 ID で VLM の答えを引いて属性を付け (COGROUND_VLM=perception)、ルールと照合して Plan を作る
///
/// ■ 使い方
///   CoGroundFrameSender と CoGroundSceneReporter があるシーンの GameObject に付ける (参照は空なら自動で探す)。
///   机 (place_zone 付きの CoGroundSceneObject) は、これまでどおり CoGroundSceneReporter が送る。
///   サーバーは、物体の中心が机の place_zone に入っていれば「机の上」にする。
///
/// ■ 属性
///   ここからは送らない。サーバーが同じ object_id で VLM の答えを引く。
///   VLM が聞き直したとき (ルールが増えたなど) は、位置が同じでも scene.update を送り直す。
///
/// ■ 種類
///   VLM が答えた種類がカテゴリ表 (CoGroundCategory) にあればそれを使い、無ければ検出器のクラスを使う。
///   検出器のクラスは observation.detector_label に入る。
///
/// ■ 見えなくなった物体
///   フレームに写っていないだけの物体は残す (頭を別の方へ向けただけかもしれない)。
///   サーバーが「あった場所が空いている」「無くなった」「別の物体と同じだった」と答えた物体は消す。
/// </summary>
public class CoGroundPerceivedObjects : MonoBehaviour, ICoGroundSceneSource
{
    [Header("参照 (空なら自動で探す)")]
    [SerializeField] private CoGroundFrameSender frameSender;
    [SerializeField] private CoGroundSceneReporter reporter;

    [Header("送る物体")]
    [Tooltip("VLM が答えた種類がカテゴリ表にあれば、検出器のクラスより優先する。")]
    [SerializeField] private bool preferVlmCategory = true;

    [Tooltip("検出の確信度がこれより低い物体は送らない。")]
    [SerializeField, Range(0f, 1f)] private float minConfidence = 0f;

    [Header("デバッグ")]
    [SerializeField] private bool logObjects = true;

    private const string Tag = "[Perceived]";

    private class Perceived
    {
        public string Id, Category, DetectorClass;
        public float Confidence, LastSeen;
        public Vector3 Position, Size;
    }

    private readonly Dictionary<string, Perceived> _objects = new();

    /// <summary>いま覚えている物体の数。</summary>
    public int Count => _objects.Count;

    /// <summary>認識した物体の箱 (ワールド軸に沿った中心と大きさ [m])。覚えていなければ false。</summary>
    public bool TryGetBox(string objectId, out Vector3 center, out Vector3 size)
    {
        if (objectId != null && _objects.TryGetValue(objectId, out var o))
        {
            center = o.Position;
            size = o.Size;
            return true;
        }
        center = size = Vector3.zero;
        return false;
    }

    private void Awake()
    {
        if (!frameSender) frameSender = FindAnyObjectByType<CoGroundFrameSender>();
        if (!reporter) reporter = FindAnyObjectByType<CoGroundSceneReporter>();
        if (!frameSender) Debug.LogWarning($"{Tag} CoGroundFrameSender が見つからない (認識結果が届かない)", this);
        if (!reporter) Debug.LogWarning($"{Tag} CoGroundSceneReporter が見つからない (scene.update に入らない)", this);
        else reporter.AddSource(this);
    }

    private void OnEnable()
    {
        if (frameSender) frameSender.onResult.AddListener(OnFrameResult);
    }

    private void OnDisable()
    {
        if (frameSender) frameSender.onResult.RemoveListener(OnFrameResult);
    }

    /// <summary>覚えている物体をすべて消す (サーバーの記憶は消さない)。</summary>
    [ContextMenu("認識した物体を消す")]
    public void Clear()
    {
        _objects.Clear();
        if (reporter) reporter.SendNow();
    }

    public void CollectObjects(List<SceneObjectDto> into)
    {
        foreach (var o in _objects.Values)
        {
            if (o.Confidence < minConfidence) continue;
            into.Add(new SceneObjectDto
            {
                Id = o.Id,
                Category = o.Category,
                Position = SceneJson.V(o.Position),
                Rotation = SceneJson.Q(Quaternion.identity), // サーバーの箱はワールド軸に沿っている
                Size = SceneJson.V(o.Size),
                Observation = new ObservationDto
                {
                    Source = ObjectSource.Detection,
                    DetectorLabel = o.DetectorClass,
                    Confidence = o.Confidence,
                    Tracking = TrackingState.Tracked,
                    LastSeen = o.LastSeen,
                },
            });
        }
    }

    /// <summary>POST /perception/frame の答え (JSON)。CoGroundFrameSender.onResult から呼ばれる。</summary>
    public void OnFrameResult(string json)
    {
        ResultDto result;
        try { result = JsonConvert.DeserializeObject<ResultDto>(json); }
        catch (JsonException e)
        {
            Debug.LogWarning($"{Tag} 答えを読めない: {e.Message}", this);
            return;
        }
        if (result?.Objects == null) return; // 記録だけ (analyze=false) のときは物体が無い

        // サーバーが「もうそこに無い」と答えた物体
        var gone = new List<string>();
        if (result.Frame != null)
        {
            if (result.Frame.Displaced != null) gone.AddRange(result.Frame.Displaced);
            if (result.Frame.Missing != null) gone.AddRange(result.Frame.Missing);
            if (result.Frame.Merged != null) gone.AddRange(result.Frame.Merged.Keys);
        }
        foreach (var id in gone) _objects.Remove(id);

        int unlocated = 0;
        foreach (var o in result.Objects)
        {
            // 深度が足りず 3D にできなかった検出は、位置が無いので送れない
            if (string.IsNullOrEmpty(o.ObjectId) || o.Position == null || o.Position.Length != 3 ||
                o.Size == null || o.Size.Length != 3)
            {
                unlocated++;
                continue;
            }
            _objects[o.ObjectId] = new Perceived
            {
                Id = o.ObjectId,
                Category = ChooseCategory(o.Category, o.Class),
                DetectorClass = o.Class,
                Confidence = Mathf.Clamp01(o.Confidence),
                LastSeen = Time.time,
                Position = new Vector3(o.Position[0], o.Position[1], o.Position[2]),
                Size = new Vector3(Mathf.Abs(o.Size[0]), Mathf.Abs(o.Size[1]), Mathf.Abs(o.Size[2])),
            };
        }

        if (logObjects)
        {
            var parts = new List<string>();
            foreach (var o in _objects.Values) parts.Add($"{o.Id}({o.Category}) {o.Position:F2}");
            Debug.Log($"{Tag} 物体 {_objects.Count} 個: {string.Join(", ", parts)}" +
                      (unlocated > 0 ? $" / 3D にできなかった検出 {unlocated} 個" : "") +
                      (gone.Count > 0 ? $" / 消した: {string.Join(", ", gone)}" : ""), this);
        }

        // VLM が答え直したときは、位置が同じでも送り直す (サーバーが属性を付け直す)。
        // 位置や物体の増減は、CoGroundSceneReporter が自分で見つけて送る
        if (reporter && result.Vlm != null && result.Vlm.Calls > 0) reporter.SendNow();
    }

    private string ChooseCategory(string vlmCategory, string detectorClass)
    {
        if (preferVlmCategory && !string.IsNullOrWhiteSpace(vlmCategory) &&
            Enum.IsDefined(typeof(CoGroundCategory), vlmCategory.Trim()))
        {
            return vlmCategory.Trim();
        }
        return string.IsNullOrWhiteSpace(detectorClass) ? "unknown" : detectorClass.Trim();
    }

    // ---- POST /perception/frame の答えのうち、ここで使う部分 (サーバーの perception/schema.py の AnalyzeResult) ----

    private class ResultDto
    {
        [JsonProperty("objects")] public List<ObjectDto> Objects;
        [JsonProperty("vlm")] public VlmDto Vlm;
        [JsonProperty("frame")] public FrameDto Frame;
    }

    private class ObjectDto
    {
        [JsonProperty("object_id")] public string ObjectId;
        [JsonProperty("class")] public string Class;
        [JsonProperty("category")] public string Category;
        [JsonProperty("confidence")] public float Confidence;
        [JsonProperty("position")] public float[] Position;
        [JsonProperty("size")] public float[] Size;
    }

    private class VlmDto
    {
        [JsonProperty("calls")] public int Calls;
    }

    private class FrameDto
    {
        [JsonProperty("displaced")] public List<string> Displaced;
        [JsonProperty("missing")] public List<string> Missing;
        [JsonProperty("merged")] public Dictionary<string, string> Merged;
    }
}
