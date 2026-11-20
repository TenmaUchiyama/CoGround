using System;
using System.Collections.Generic;
using System.Reflection;
using System.Text;
using System.Threading.Tasks;
using Meta.XR;
using Meta.XR.BuildingBlocks.AIBlocks;
using Meta.XR.EnvironmentDepth;
using UnityEngine;

/// <summary>
/// 物体検出 → 3D の箱 の共通処理。DetectionBox3DSpawner（デバッグ表示）と DRMaskFollowDetection（DR マスク）が
/// どちらもここの <see cref="Tracks"/> を読む。
///
///   ObjectDetectionAgent
///      │ 矩形 + 撮影時のカメラ姿勢     ← 推論はこのスクリプトから呼び、呼んだ瞬間の姿勢を保存する
///      ▼
///   DetectionLocator   … 2D → 3D（複数点のレイキャスト、机の面に合わせた箱）
///      │ 物体ごとの 3D 箱（1 フレーム分）
///      ▼
///   DetectionTracker   … 対応づけ・平滑化・固定
///      │ 安定した 3D 箱
///      ▼
///   Tracks
///
/// ■ 使い方
///   [BuildingBlock] Object Detection の GameObject に付ける。
///   Spawner / DR は、付いていなければ自動で追加する（<see cref="GetOrCreate"/>）。
///
/// ■ 計測
///   物体を動かさずに 10 秒ほど置き、logcat を "[DetectStats]" で絞り込む。
///   目安: 中心のばらつき 2cm 以下、サイズのばらつき 10% 以下。
/// </summary>
public class DetectionPipeline : MonoBehaviour
{
    [Header("参照（空なら自動取得）")]
    [SerializeField] private ObjectDetectionAgent agent;
    [SerializeField] private PassthroughCameraAccess cameraAccess;

    [Header("推論の呼び出し")]
    [Tooltip("Agent の自動推論を止め、このスクリプトから推論を呼ぶ。\n" +
             "呼んだ瞬間のカメラ姿勢を保存できるので、推論中に頭を動かしても箱がずれない。")]
    [SerializeField] private bool driveInference = true;

    [Tooltip("推論を呼ぶ最小間隔 [秒]。0 = 前の推論が終わり次第すぐ。")]
    [SerializeField] private float inferenceInterval = 0f;

    [Header("2D → 3D")]
    [SerializeField] private DetectionLocatorSettings locator = new();

    [Tooltip("環境レイキャストが当たらないとき、シーン内のコライダー（机のスキャン等）にレイを当てる。")]
    [SerializeField] private bool usePhysicsFallback = false;

    [SerializeField] private LayerMask physicsLayers = ~0;

    [Header("追跡・平滑化・固定")]
    [SerializeField] private DetectionTrackerSettings tracker = new();

    [Header("デバッグ")]
    [Tooltip("検出のたびに Debug.Log を出す（logcat では \"[Detect]\" で絞り込める）。")]
    [SerializeField] private bool logDetections = false;

    [Tooltip("この秒数ごとに、状態と物体ごとのばらつきをログに出す。0 で無効。")]
    [SerializeField] private float statusLogInterval = 3f;

    [Tooltip("Agent 内部で握りつぶされた推論タスクの例外を出すため、状態ログのたびに GC を走らせる（重いのでデバッグ時だけ）。")]
    [SerializeField] private bool collectGarbageForTaskExceptions = false;

    private const string Tag = "[Detect]";
    private const string StatsTag = "[DetectStats]";

    // ObjectDetectionAgent は「自動推論の間隔」と「推論中フラグ」を公開していないので、リフレクションで触る
    private static readonly FieldInfo IntervalField = typeof(ObjectDetectionAgent).GetField(
        "detectEveryNFrames", BindingFlags.Instance | BindingFlags.NonPublic);
    private static readonly FieldInfo BusyField = typeof(ObjectDetectionAgent).GetField(
        "_busy", BindingFlags.Instance | BindingFlags.NonPublic);

    private EnvironmentRaycastManager _envRaycast;
    private DetectionLocator _locator;
    private DetectionTracker _tracker;
    private readonly List<LocatedBox> _measurements = new();
    private readonly List<Collider> _ignoredColliders = new();
    private Func<Vector3, bool> _isInView;

    private bool _driving;
    private object _originalInterval;
    private bool _hasCapturedPose;
    private Pose _capturedPose;
    private Vector2 _capturedTexSize;
    private float _nextInferenceTime;

    private float _nextStatusTime;
    private int _inferenceCount, _callbackCount, _locatedCount, _locateFailCount;
    private string _lastRaycastStatus = "-";

    /// <summary>追跡中の物体。表示には IsConfirmed のものだけ使う。</summary>
    public IReadOnlyList<DetectionTrack> Tracks => _tracker.Tracks;

    public ObjectDetectionAgent Agent => agent;
    public PassthroughCameraAccess CameraAccess => cameraAccess;

    /// <summary>Agent と同じ GameObject の DetectionPipeline を返す。無ければ追加する。</summary>
    public static DetectionPipeline GetOrCreate(ObjectDetectionAgent agent)
    {
        var existing = agent ? agent.GetComponent<DetectionPipeline>() : FindAnyObjectByType<DetectionPipeline>();
        if (existing) return existing;
        if (!agent) agent = FindAnyObjectByType<ObjectDetectionAgent>();
        return agent ? agent.gameObject.AddComponent<DetectionPipeline>() : null;
    }

    /// <summary>コライダーへのレイキャスト（机のスキャン等）も使う。ignore は当たっても無視するコライダー。</summary>
    public void EnablePhysicsFallback(LayerMask layers, IEnumerable<Collider> ignore = null)
    {
        usePhysicsFallback = true;
        physicsLayers = layers;
        if (ignore == null) return;
        foreach (var c in ignore)
            if (c && !_ignoredColliders.Contains(c)) _ignoredColliders.Add(c);
    }

    /// <summary>追跡をやり直す（固定も解除）。label を指定するとそのラベルだけ。</summary>
    public void ResetTracks(string label = null) => _tracker.Reset(label);

    public DetectionTrackStats GetStats(DetectionTrack track) => _tracker.GetStats(track);

    // ------------------------------------------------------------------
    // ライフサイクル
    // ------------------------------------------------------------------

    private void Awake()
    {
        if (!agent) agent = GetComponent<ObjectDetectionAgent>();
        if (!agent) agent = FindAnyObjectByType<ObjectDetectionAgent>();
        if (!cameraAccess) cameraAccess = FindAnyObjectByType<PassthroughCameraAccess>();

        // 環境レイキャスト（Passthrough Camera API サンプルと同じ方式）。シーンに無ければ自分に追加する
        _envRaycast = FindAnyObjectByType<EnvironmentRaycastManager>();
        if (_envRaycast == null && EnvironmentRaycastManager.IsSupported)
            _envRaycast = gameObject.AddComponent<EnvironmentRaycastManager>();

        _tracker = new DetectionTracker(tracker);
        _locator = new DetectionLocator(cameraAccess, RaycastSurface, locator);
        _isInView = IsInView;

        Debug.Log($"{Tag} Awake: agent={(agent ? "OK" : "なし")}, passthroughCamera={(cameraAccess ? "OK" : "なし")}, " +
                  $"envRaycast={(_envRaycast ? "OK" : "なし")} (IsSupported={EnvironmentRaycastManager.IsSupported})");
    }

    private void Start()
    {
        // Quest Link / エディタで Environment Depth が使えないと、Meta の ObjectDetectionVisualizer が
        // TryProject 内で NullReferenceException を投げ、OnBoxesUpdated の後続の購読者（＝このスクリプト）まで
        // 届かなくなる。なのでデプスが無い環境では Visualizer を止める。
        var visualizer = agent ? agent.GetComponent<ObjectDetectionVisualizer>() : null;
        if (!EnvironmentDepthManager.IsSupported && visualizer && visualizer.enabled)
        {
            Debug.LogWarning($"{Tag} EnvironmentDepthManager 非対応 → ObjectDetectionVisualizer を無効化");
            visualizer.enabled = false;
        }
    }

    private void OnEnable()
    {
        // Agent は推論を「_ = RunDetection()」で投げっぱなしにしているので、未観測の Task 例外を拾ってログに出す
        TaskScheduler.UnobservedTaskException += OnUnobservedTaskException;

        if (!agent || !cameraAccess)
        {
            Debug.LogError($"{Tag} ObjectDetectionAgent / PassthroughCameraAccess が見つかりません", this);
            return;
        }
        agent.OnBoxesUpdated += OnBoxesUpdated;

        _driving = false;
        if (driveInference)
        {
            if (IntervalField != null && BusyField != null)
            {
                _originalInterval = IntervalField.GetValue(agent);
                IntervalField.SetValue(agent, 0); // 自動推論を止める（手動呼び出しのみ）
                _driving = true;
            }
            else
            {
                Debug.LogWarning($"{Tag} ObjectDetectionAgent の内部フィールドが見つからないため、推論の呼び出しは Agent に任せます。" +
                                 "姿勢は結果を受け取った時点のものを使うので、頭を動かすと箱がずれます。");
            }
        }
    }

    private void OnDisable()
    {
        TaskScheduler.UnobservedTaskException -= OnUnobservedTaskException;
        if (!agent) return;
        agent.OnBoxesUpdated -= OnBoxesUpdated;
        if (_driving) IntervalField.SetValue(agent, _originalInterval);
        _driving = false;
        _hasCapturedPose = false;
    }

    private static void OnUnobservedTaskException(object sender, UnobservedTaskExceptionEventArgs e)
    {
        Debug.LogError($"{Tag} 推論タスクで例外（Agent 内部で握りつぶされていたもの）:\n{e.Exception}");
        e.SetObserved();
    }

    private void Update()
    {
        if (agent && cameraAccess && cameraAccess.IsPlaying)
        {
            _tracker.Tick(Time.deltaTime, _isInView);

            // 前の推論が終わっていたら次を呼ぶ。Agent は呼ばれた瞬間のカメラ画像を使うので、
            // 同じ瞬間の姿勢（= その画像のタイムスタンプでの姿勢）を保存しておく。
            if (_driving && agent.isActiveAndEnabled && !(bool)BusyField.GetValue(agent) &&
                Time.time >= _nextInferenceTime)
            {
                var tex = cameraAccess.GetTexture();
                if (tex)
                {
                    _capturedPose = cameraAccess.GetCameraPose();
                    _capturedTexSize = new Vector2(tex.width, tex.height);
                    _hasCapturedPose = true;
                    _nextInferenceTime = Time.time + inferenceInterval;
                    _inferenceCount++;
                    agent.CallInference();
                }
            }
        }

        if (statusLogInterval > 0f && Time.time >= _nextStatusTime)
        {
            _nextStatusTime = Time.time + statusLogInterval;
            LogStatus();
        }
    }

    // ------------------------------------------------------------------
    // 検出結果を受け取るたびに呼ばれる
    //  ※ Agent は「スコアが minConfidence 以上の検出が 1 件以上ある」ときしか呼ばない
    // ------------------------------------------------------------------

    private void OnBoxesUpdated(List<BoxData> boxes)
    {
        // Agent の async タスクの中で呼ばれ、例外は握りつぶされるので、ここで全部拾ってログに出す
        try { HandleBoxes(boxes); }
        catch (Exception e) { Debug.LogError($"{Tag} {e}", this); }
    }

    private void HandleBoxes(List<BoxData> boxes)
    {
        if (boxes == null || !cameraAccess.IsPlaying) return;
        _callbackCount++;

        // 撮影時の姿勢。自分で推論を呼んでいないときは、仕方なく「今」の姿勢を使う
        Pose pose;
        Vector2 texSize;
        if (_driving && _hasCapturedPose)
        {
            pose = _capturedPose;
            texSize = _capturedTexSize;
        }
        else
        {
            var tex = cameraAccess.GetTexture();
            if (!tex) return;
            pose = cameraAccess.GetCameraPose();
            texSize = new Vector2(tex.width, tex.height);
        }

        _measurements.Clear();
        foreach (var b in boxes)
        {
            // BoxData は position.xy = (xmin, ymin)、scale.xy = (xmax, ymax) [カメラ画像のピクセル]
            if (!_locator.TryLocate(b.position.x, b.position.y, b.scale.x, b.scale.y, texSize, pose, out var located))
            {
                _locateFailCount++;
                if (logDetections) Debug.LogWarning($"{Tag}   3D 化に失敗: {b.label} (lastRaycast={_lastRaycastStatus})");
                continue;
            }

            SplitLabel(b.label, out located.Label, out located.Score);
            _measurements.Add(located);
            _locatedCount++;

            if (logDetections)
                Debug.Log($"{Tag}   {b.label}: center={located.Center:F2} size={located.Size:F2} via {located.Method}");
        }

        _tracker.Update(_measurements, Time.time);
    }

    /// <summary>"cup 0.87" → ("cup", 0.87)。クラス名に空白が入ることがあるので最後の空白で分ける。</summary>
    private static void SplitLabel(string raw, out string label, out float score)
    {
        label = raw ?? "";
        score = 0f;
        int i = label.LastIndexOf(' ');
        if (i > 0 && float.TryParse(label.Substring(i + 1), System.Globalization.NumberStyles.Float,
                System.Globalization.CultureInfo.InvariantCulture, out float parsed))
        {
            score = parsed;
            label = label.Substring(0, i);
        }
    }

    // ------------------------------------------------------------------
    // レイキャスト / 視界判定
    // ------------------------------------------------------------------

    private bool RaycastSurface(Ray ray, out Vector3 point, out Vector3 normal)
    {
        if (_envRaycast && EnvironmentRaycastManager.IsSupported)
        {
            bool ok = _envRaycast.Raycast(ray, out EnvironmentRaycastHit hit, locator.maxRayDistance);
            _lastRaycastStatus = hit.status.ToString();
            if (ok)
            {
                point = hit.point;
                normal = hit.normal;
                return true;
            }
        }

        if (usePhysicsFallback)
        {
            var hits = Physics.RaycastAll(ray, locator.maxRayDistance, physicsLayers, QueryTriggerInteraction.Ignore);
            float best = float.PositiveInfinity;
            RaycastHit bestHit = default;
            foreach (var h in hits)
            {
                if (h.distance >= best || _ignoredColliders.Contains(h.collider)) continue;
                best = h.distance;
                bestHit = h;
            }
            if (best < float.PositiveInfinity)
            {
                point = bestHit.point;
                normal = bestHit.normal;
                return true;
            }
        }

        point = normal = default;
        return false;
    }

    /// <summary>今のカメラ画像に写る位置か（写っているのに検出されない＝見失った、と数えるため）。</summary>
    private bool IsInView(Vector3 world)
    {
        Pose pose = cameraAccess.GetCameraPose();
        if ((Quaternion.Inverse(pose.rotation) * (world - pose.position)).z < 0.1f) return false;
        Vector2 vp = cameraAccess.WorldToViewportPoint(world, pose);
        return vp.x > 0.05f && vp.x < 0.95f && vp.y > 0.05f && vp.y < 0.95f;
    }

    // ------------------------------------------------------------------
    // 状態と計測のログ
    // ------------------------------------------------------------------

    private void LogStatus()
    {
        if (collectGarbageForTaskExceptions)
        {
            // 未観測 Task 例外は GC のタイミングでしか通知されない
            GC.Collect();
            GC.WaitForPendingFinalizers();
        }

        // 見方:
        //   cameraPlaying=false → パススルーカメラの権限/起動の問題（推論を始めない）
        //   callbacks が増えない → 推論結果が 0 件、または minConfidence 未満で全部捨てられている
        //   locateFail が増える  → レイが当たっていない（lastRaycast を見る）
        Debug.Log($"{Tag} status: cameraPlaying={(cameraAccess && cameraAccess.IsPlaying)}, " +
                  $"poseSync={(_driving ? "撮影時" : "受信時")}, inferences={_inferenceCount}, callbacks={_callbackCount}, " +
                  $"located={_locatedCount}, locateFail={_locateFailCount}, lastRaycast={_lastRaycastStatus}, " +
                  $"tracks={_tracker.Tracks.Count}");

        // 物体ごとのばらつき。raw = 平滑化前、out = 平滑化後（実際に表示/DR に使う値）
        var sb = new StringBuilder();
        foreach (var t in _tracker.Tracks)
        {
            if (!t.IsConfirmed) continue;
            var s = _tracker.GetStats(t);
            if (s.Count < 2) continue;
            sb.Clear();
            sb.Append($"{StatsTag} {t.Label}#{t.Id} n={s.Count} ({tracker.statsWindowSeconds:0}s) {(t.IsLocked ? "固定" : "追従")} via {t.Method} | ");
            sb.Append($"raw: 中心σ={s.RawCenterStd * 100f:0.0}cm サイズ={s.MeanRawSize.x:0.00}x{s.MeanRawSize.y:0.00}x{s.MeanRawSize.z:0.00}m ");
            sb.Append($"サイズσ=({s.RawSizeCv.x:P0},{s.RawSizeCv.y:P0},{s.RawSizeCv.z:P0}) | ");
            sb.Append($"out: 中心σ={s.OutCenterStd * 100f:0.0}cm サイズσ=({s.OutSizeCv.x:P0},{s.OutSizeCv.y:P0},{s.OutSizeCv.z:P0})");
            Debug.Log(sb.ToString());
        }
    }
}
