using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Threading;
using System.Threading.Tasks;
using Meta.XR.BuildingBlocks.AIBlocks;
using Newtonsoft.Json;
using UnityEngine;
using UnityEngine.Networking;
using Debug = UnityEngine.Debug;

/// <summary>
/// Meta の ObjectDetectionAgent から、サーバーの YOLO-World（detector コンテナ, :8001）を呼ぶ provider。
///
///   ObjectDetectionAgent ── カメラ画像を JPEG に（captureMaxResolution, 既定 640px）
///      │ DetectAsync(jpeg)                       ← ここがこのクラス
///      ▼
///   POST {endpoint}/detect（image/jpeg）
///      │ {"predictions":[{"label","score","box":[xmin,ymin,xmax,ymax]}]}  ← Meta の形式そのまま
///      ▼
///   Agent が元の画像サイズに戻し、OnBoxesUpdated → DetectionPipeline（3D 化・追跡）→ DR / 表示
///
/// ■ 使い方
///   1. Project で Create > CoGround > YOLO-World Detector Provider を作り、Endpoint を設定する
///   2. [BuildingBlock] Object Detection の ObjectDetectionAgent の Provider Asset に入れる
///   3. Player Settings > Allow downloads over HTTP を Always allowed にする（http:// で送るため）
///
/// ■ サーバーの返事
///   429（推論中）はそのフレームを捨てる。503（検出が無効）や接続エラーは警告を出して次のフレームでまたやり直す。
///   語彙（Send Vocabulary）はサーバーが再起動すると既定に戻るので、接続できなかった後は送り直す。
///
/// ■ つながっているかの確かめ方
///   - Editor：このアセットの ⋮ メニュー > Test Connection（Quest なしで /health と /detect を 1 回ずつ呼ぶ）
///   - 実機：logcat を "[YoloWorld]" で絞る。最初の送信・最初の応答・5 秒ごとの往復時間が出る
///     （送信のログが 1 つも出ないなら、ObjectDetectionAgent がこの provider を呼んでいない）
///   - サーバー：ブラウザで {endpoint}/detect/ui の「Live from clients」に、届いた画像と検出結果が出る
/// </summary>
[CreateAssetMenu(menuName = "CoGround/YOLO-World Detector Provider", fileName = "CoGroundYoloWorldProvider")]
public sealed class CoGroundYoloWorldProvider : AIProviderBase, IObjectDetectionTask
{
    [Serializable]
    public class VocabularyEntry
    {
        [Tooltip("YOLO-World に渡す言葉（例: plastic bottle）")]
        [JsonProperty("prompt")] public string prompt;
        [Tooltip("結果のラベル = scene.update の category（例: plastic_bottle）")]
        [JsonProperty("label")] public string label;
    }

    [Header("サーバー")]
    [Tooltip("detector コンテナの URL（/detect は付けない）。例: http://100.110.93.117:8001")]
    [SerializeField] private string endpoint = "http://100.110.93.117:8001";

    [Tooltip("1 回の検出の待ち時間の上限 [秒]。")]
    [SerializeField, Min(1)] private int timeoutSeconds = 2;

    [Header("語彙（任意）")]
    [Tooltip("ON なら、最初の検出の前に下の語彙をサーバーに送る（PUT /detect/vocabulary）。\n" +
             "OFF ならサーバーの語彙（detection_vocab.json か、ブラウザの /detect/ui で変えたもの）を使う。\n" +
             "語彙はサーバー全体で 1 つなので、ほかのクライアントにも効く。")]
    [SerializeField] private bool sendVocabulary = false;

    [SerializeField] private List<VocabularyEntry> vocabulary = new()
    {
        new VocabularyEntry { prompt = "plastic bottle", label = "plastic_bottle" },
        new VocabularyEntry { prompt = "cup", label = "cup" },
        new VocabularyEntry { prompt = "mug", label = "mug" },
    };

    [Header("デバッグ")]
    [Tooltip("この秒数ごとに、往復時間などをログに出す（logcat では \"[YoloWorld]\" で絞り込める）。0 で無効。")]
    [SerializeField] private float statsLogInterval = 5f;

    private const string Tag = "[YoloWorld]";

    protected override InferenceType DefaultSupportedTypes => InferenceType.LocalServer;

    // ScriptableObject はエディタでは Play をまたいで残るので、Play ごとの状態は番号で区別する
    private static int s_playSession;
    [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.SubsystemRegistration)]
    private static void NewPlaySession() => s_playSession++;

    [NonSerialized] private int _vocabularySentSession = -1;
    [NonSerialized] private int _firstSendLoggedSession = -1;
    [NonSerialized] private int _firstReplyLoggedSession = -1;
    [NonSerialized] private float _nextWarnTime;
    [NonSerialized] private Stats _stats;

    private struct Stats
    {
        public int Session, Ok, Busy, Failed, Count;
        public double SumMs, MaxMs;
        public long SumBytes;
        public float NextLogTime;
    }

    // ------------------------------------------------------------------
    // IObjectDetectionTask
    // ------------------------------------------------------------------

    public async Task<string> DetectAsync(byte[] imageJpgOrPng, CancellationToken ct = default)
    {
        if (imageJpgOrPng == null || imageJpgOrPng.Length == 0) return null;

        if (sendVocabulary && _vocabularySentSession != s_playSession)
            await PushVocabularyAsync(ct);

        if (_firstSendLoggedSession != s_playSession)
        {
            _firstSendLoggedSession = s_playSession;
            Debug.Log($"{Tag} 最初のフレームを送信: {imageJpgOrPng.Length / 1024}KB → {Url("/detect")}");
        }

        var watch = Stopwatch.StartNew();
        using var req = new UnityWebRequest(Url("/detect"), UnityWebRequest.kHttpVerbPOST)
        {
            uploadHandler = new UploadHandlerRaw(imageJpgOrPng) { contentType = "image/jpeg" },
            downloadHandler = new DownloadHandlerBuffer(),
            timeout = timeoutSeconds,
        };
        req.SetRequestHeader("Content-Type", "image/jpeg");
        await SendAsync(req, ct);
        watch.Stop();

        if (req.result == UnityWebRequest.Result.Success)
        {
            Record(ok: true, busy: false, watch.Elapsed.TotalMilliseconds, imageJpgOrPng.Length);
            if (_firstReplyLoggedSession != s_playSession)
            {
                _firstReplyLoggedSession = s_playSession;
                Debug.Log($"{Tag} 最初の応答 ({watch.Elapsed.TotalMilliseconds:0}ms): {req.downloadHandler.text}");
            }
            return req.downloadHandler.text;
        }

        if (req.responseCode == 429)
        {
            // サーバーが前の画像を処理中。キューは無いので、このフレームは捨てる
            Record(ok: false, busy: true, 0, 0);
            return null;
        }

        Record(ok: false, busy: false, 0, 0);
        // 接続できなかった = サーバーが再起動したかもしれないので、語彙は送り直す
        if (req.responseCode == 0 || req.responseCode == 503) _vocabularySentSession = -1;
        Warn(req.responseCode == 503
            ? $"{Tag} 検出が無効です（503）。detector コンテナを起動してください（make up）: {endpoint}"
            : $"{Tag} {Url("/detect")} に失敗: {req.responseCode} {req.error} " +
              "（Allow downloads over HTTP、サーバーの起動、Tailscale の接続を確認）");
        return null;
    }

    public Task<ObjectDetectionPrediction[]> DetectAsync(RenderTexture src, CancellationToken ct = default) =>
        throw new NotSupportedException(
            $"{nameof(CoGroundYoloWorldProvider)} は ObjectDetectionAgent の JPEG 経由（DetectAsync(byte[])）でだけ使う");

    // ------------------------------------------------------------------
    // 接続テスト（Editor でアセットの ⋮ メニューから。Quest なしで使える）
    // ------------------------------------------------------------------

    [ContextMenu("Test Connection")]
    private async void TestConnection()
    {
        Debug.Log($"{Tag} 接続テスト: {endpoint}");
        using (var health = UnityWebRequest.Get(Url("/health")))
        {
            health.timeout = 5;
            await SendAsync(health, default);
            if (health.result != UnityWebRequest.Result.Success)
            {
                Debug.LogError($"{Tag} /health に届きません: {health.responseCode} {health.error}" +
                               "（サーバーの起動 make up、Tailscale、endpoint の IP を確認）", this);
                return;
            }
            Debug.Log($"{Tag} /health OK: {health.downloadHandler.text}", this);
        }

        // 灰色の 640x480 の画像を 1 枚送る（何も検出されないのが正常）
        var tex = new Texture2D(640, 480, TextureFormat.RGB24, false);
        var pixels = new Color32[640 * 480];
        for (var i = 0; i < pixels.Length; i++) pixels[i] = new Color32(128, 128, 128, 255);
        tex.SetPixels32(pixels);
        var jpeg = tex.EncodeToJPG();
        if (Application.isPlaying) Destroy(tex); else DestroyImmediate(tex);

        var watch = Stopwatch.StartNew();
        using var req = new UnityWebRequest(Url("/detect"), UnityWebRequest.kHttpVerbPOST)
        {
            uploadHandler = new UploadHandlerRaw(jpeg) { contentType = "image/jpeg" },
            downloadHandler = new DownloadHandlerBuffer(),
            timeout = 10,
        };
        req.SetRequestHeader("Content-Type", "image/jpeg");
        await SendAsync(req, default);
        if (req.result == UnityWebRequest.Result.Success)
            Debug.Log($"{Tag} /detect OK ({watch.Elapsed.TotalMilliseconds:0}ms): {req.downloadHandler.text}" +
                      $"  → ブラウザの {Url("/detect/ui")} の Live に灰色の画像が出ていれば成功", this);
        else
            Debug.LogError($"{Tag} /detect に失敗: {req.responseCode} {req.error} {req.downloadHandler?.text}", this);
    }

    // ------------------------------------------------------------------

    private async Task PushVocabularyAsync(CancellationToken ct)
    {
        var body = JsonConvert.SerializeObject(new { entries = vocabulary });
        using var req = new UnityWebRequest(Url("/detect/vocabulary"), UnityWebRequest.kHttpVerbPUT)
        {
            uploadHandler = new UploadHandlerRaw(System.Text.Encoding.UTF8.GetBytes(body)) { contentType = "application/json" },
            downloadHandler = new DownloadHandlerBuffer(),
            timeout = timeoutSeconds,
        };
        req.SetRequestHeader("Content-Type", "application/json");
        await SendAsync(req, ct);

        if (req.result == UnityWebRequest.Result.Success)
        {
            _vocabularySentSession = s_playSession;
            Debug.Log($"{Tag} 語彙を送信: {vocabulary.Count} 件");
        }
        else
        {
            // 422 = 語彙の形が不正（ラベルは英小文字・数字・_、prompt の重複不可）。直るまで毎回送り直す
            Warn($"{Tag} 語彙の送信に失敗: {req.responseCode} {req.error} {req.downloadHandler?.text}");
        }
    }

    private string Url(string path) => endpoint.TrimEnd('/') + path;

    private static Task SendAsync(UnityWebRequest req, CancellationToken ct)
    {
        var tcs = new TaskCompletionSource<bool>();
        req.SendWebRequest().completed += _ => tcs.TrySetResult(true);
        if (ct.CanBeCanceled) ct.Register(() => { if (!req.isDone) req.Abort(); });
        return tcs.Task;
    }

    private void Warn(string message)
    {
        if (Time.realtimeSinceStartup < _nextWarnTime) return;
        _nextWarnTime = Time.realtimeSinceStartup + 5f;
        Debug.LogWarning(message, this);
    }

    private void Record(bool ok, bool busy, double ms, int bytes)
    {
        if (statsLogInterval <= 0f) return;
        if (_stats.Session != s_playSession) _stats = new Stats { Session = s_playSession };

        if (ok)
        {
            _stats.Ok++;
            _stats.Count++;
            _stats.SumMs += ms;
            _stats.MaxMs = Math.Max(_stats.MaxMs, ms);
            _stats.SumBytes += bytes;
        }
        else if (busy) _stats.Busy++;
        else _stats.Failed++;

        if (Time.realtimeSinceStartup < _stats.NextLogTime) return;
        _stats.NextLogTime = Time.realtimeSinceStartup + statsLogInterval;
        if (_stats.Count > 0)
        {
            // 往復 = JPEG の送信 + サーバーの推論 + 返事（Quest 側の JPEG 化は含まない）
            Debug.Log($"{Tag} 往復 平均={_stats.SumMs / _stats.Count:0}ms 最大={_stats.MaxMs:0}ms " +
                      $"JPEG={_stats.SumBytes / _stats.Count / 1024}KB | 成功={_stats.Ok} 429={_stats.Busy} 失敗={_stats.Failed} " +
                      $"(直近 {statsLogInterval:0}s)");
        }
        _stats.Count = 0;
        _stats.SumMs = _stats.MaxMs = 0;
        _stats.SumBytes = 0;
        _stats.Ok = _stats.Busy = _stats.Failed = 0;
    }
}
