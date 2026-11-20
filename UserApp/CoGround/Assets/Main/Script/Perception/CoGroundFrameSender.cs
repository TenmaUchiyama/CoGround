using System;
using System.Collections;
using System.Collections.Generic;
using Meta.XR;
using Meta.XR.EnvironmentDepth;
using Newtonsoft.Json;
using UnityEngine;
using UnityEngine.Events;
using UnityEngine.Experimental.Rendering;
using UnityEngine.Networking;
using UnityEngine.Rendering;

/// <summary>
/// パススルーの RGB・環境深度・撮影時のカメラを 1 フレーム分まとめて、grounding_server の perception に送る。
///
///   PassthroughCameraAccess ─ RGB（JPEG）、撮影時刻、撮影時のカメラ姿勢、内部パラメータ
///   EnvironmentDepthManager ─ 深度テクスチャ（左目）と、ワールド → 深度カメラの行列
///      │  POST {endpoint}/perception/frame（multipart: rgb, depth, meta）
///      ▼
///   サーバーが深度を RGB に合わせ、物体を 3D にして、同じ物体に同じ ID を付ける。新しい物体だけ VLM に聞く
///   （Backend/grounding_server/coground_server/perception/frame.py, pipeline.py）
///
/// ■ 使い方
///   1. PassthroughCameraAccess があるシーン（ObjectDetection.unity など）の空の GameObject に付ける。
///      EnvironmentDepthManager が無ければ自動で足す（深度には USE_SCENE の許可が要る）
///   2. Endpoint に grounding_server（:8000）を入れる
///   3. 右コントローラーの A（Send Button）で 1 フレーム送る。Send Interval を 0 より大きくすると、その間隔で送り続ける
///   4. 結果はブラウザの {endpoint}/perception/ui の Recent runs と、logcat の "[Frame]"。
///      run の depth_overlay.jpg（RGB に深度を色で重ねたもの）で、深度の位置が物体に合っているかを確かめる
///
/// ■ 記録（あとで PC で流し直す）
///   Record Name に名前（例: phase0_initial）を入れると、サーバーの logs/sequences/&lt;名前&gt;/&lt;番号&gt;/ に
///   rgb.jpg・depth.bin・meta.json がそのまま残る。Record Only なら解析しない（VLM も呼ばない）。
///   流し直し: docker compose exec grounding_server python scripts/perception_replay.py logs/sequences/&lt;名前&gt; --reset
///
/// ■ 撮るときのコツ
///   - 頭を止めてから送る（RGB と深度は撮影時刻が少し違う。頭が止まっていればずれない）
///   - 机から 40〜80 cm。深度は解像度が低いので、遠い小さな物体は 3D にできない（結果の source が unlocated になる）
/// </summary>
public class CoGroundFrameSender : MonoBehaviour
{
    [Header("サーバー")]
    [Tooltip("grounding_server の URL（/perception は付けない）。例: http://100.110.93.117:8000")]
    [SerializeField] private string endpoint = "http://100.110.93.117:8000";

    [Tooltip("1 回の送信の待ち時間の上限 [秒]。新しい物体があると VLM を呼ぶので、数秒かかる。")]
    [SerializeField, Min(1)] private int timeoutSeconds = 60;

    [Header("送るタイミング")]
    [Tooltip("このボタンを押すと 1 フレーム送る。")]
    [SerializeField] private OVRInput.Button sendButton = OVRInput.Button.One;

    [Tooltip("0 より大きいと、この間隔 [秒] で送り続ける（前の送信が終わってから数える）。0 ならボタンだけ。")]
    [SerializeField, Min(0)] private float sendInterval = 0f;

    [Header("記録")]
    [Tooltip("空でなければ、サーバーに logs/sequences/<名前>/<番号>/ として残す（英数字・_・- だけ）。")]
    [SerializeField] private string recordName = "";

    [Tooltip("残すだけで解析しない（VLM も呼ばない）。")]
    [SerializeField] private bool recordOnly = false;

    [Header("画像")]
    [SerializeField, Range(50, 100)] private int jpegQuality = 90;

    [Header("深度")]
    [Tooltip("深度から手を除く（手が物体として写り込まないように）。")]
    [SerializeField] private bool removeHands = true;

    [Header("参照（空なら自動で探す）")]
    [SerializeField] private PassthroughCameraAccess cameraAccess;
    [SerializeField] private EnvironmentDepthManager depthManager;
    [Tooltip("Hidden/CoGround/DepthCopy（Resources にあるので、空なら自動で読む）")]
    [SerializeField] private Shader depthCopyShader;

    [Header("結果")]
    [Tooltip("サーバーの答え（JSON）を受け取る。表示に使う。")]
    public UnityEvent<string> onResult = new();

    public string LastResult { get; private set; }
    public bool Busy => _busy;

    private const string Tag = "[Frame]";
    private static readonly int DepthTextureId = Shader.PropertyToID("_EnvironmentDepthTexture");
    private static readonly int ReprojectionId = Shader.PropertyToID("_EnvironmentDepthReprojectionMatrices");

    private Material _copyMaterial;
    private RenderTexture _depthCopy;
    private bool _busy;
    private float _nextAutoSend;
    private int _sent;

    private void Start()
    {
        if (!cameraAccess) cameraAccess = FindAnyObjectByType<PassthroughCameraAccess>();
        if (!depthManager) depthManager = FindAnyObjectByType<EnvironmentDepthManager>();
        if (!depthManager && EnvironmentDepthManager.IsSupported)
            depthManager = gameObject.AddComponent<EnvironmentDepthManager>();
        if (depthManager) depthManager.RemoveHands = removeHands;
        if (!depthCopyShader) depthCopyShader = Shader.Find("Hidden/CoGround/DepthCopy");
        if (depthCopyShader) _copyMaterial = new Material(depthCopyShader);

        Debug.Log($"{Tag} 準備: camera={(cameraAccess ? "OK" : "なし")} depth={(depthManager ? "OK" : "なし")} " +
                  $"(IsSupported={EnvironmentDepthManager.IsSupported}) shader={(depthCopyShader ? "OK" : "なし")} → {Url()}");
        if (!cameraAccess || !depthManager || !_copyMaterial)
            Debug.LogError($"{Tag} PassthroughCameraAccess / EnvironmentDepthManager / DepthCopy シェーダーのどれかが無いので送れません", this);
    }

    private void OnDestroy()
    {
        if (_copyMaterial) Destroy(_copyMaterial);
        if (_depthCopy) _depthCopy.Release();
    }

    private void Update()
    {
        if (_busy) return;
        bool pressed = OVRInput.GetDown(sendButton);
        bool auto = sendInterval > 0f && Time.time >= _nextAutoSend;
        if (pressed || auto) SendFrame();
    }

    /// <summary>次に届いた RGB の画像で 1 フレーム送る（ボタン以外から呼んでもよい）。</summary>
    [ContextMenu("Send Frame")]
    public void SendFrame()
    {
        if (_busy || !cameraAccess || !depthManager || !_copyMaterial) return;
        StartCoroutine(CaptureAndSend());
    }

    private IEnumerator CaptureAndSend()
    {
        _busy = true;
        try
        {
            // RGB が新しくなったフレームで、深度と一緒に取る
            float deadline = Time.realtimeSinceStartup + 2f;
            while (!(cameraAccess.IsPlaying && cameraAccess.IsUpdatedThisFrame && depthManager.IsDepthAvailable))
            {
                if (Time.realtimeSinceStartup > deadline)
                {
                    Debug.LogWarning($"{Tag} カメラか深度が来ません（IsPlaying={cameraAccess.IsPlaying} " +
                                     $"depth={depthManager.IsDepthAvailable}）。カメラと USE_SCENE の許可を確認", this);
                    yield break;
                }
                yield return null;
            }

            // ---- この瞬間のカメラ ----
            Pose pose = cameraAccess.GetCameraPose();
            Vector2Int size = cameraAccess.CurrentResolution;
            double timestamp = new DateTimeOffset(cameraAccess.Timestamp.ToUniversalTime()).ToUnixTimeMilliseconds() / 1000.0;
            var intrinsics = Intrinsics(pose, size);

            // ---- この瞬間の深度（テクスチャと行列は同じ onBeforeRender で更新されるので、ここで両方取れば揃う）----
            var depthTexture = Shader.GetGlobalTexture(DepthTextureId);
            var matrices = Shader.GetGlobalMatrixArray(ReprojectionId);
            if (depthTexture == null || matrices == null || matrices.Length == 0)
            {
                Debug.LogWarning($"{Tag} 深度テクスチャがまだありません", this);
                yield break;
            }
            Matrix4x4 reprojection = matrices[0]; // 左目
            EnsureDepthCopy(depthTexture.width, depthTexture.height);
            Graphics.Blit(Texture2D.blackTexture, _depthCopy, _copyMaterial);

            byte[] jpeg = null, depthBytes = null;
            string error = null;
            var rgbRequest = AsyncGPUReadback.Request(cameraAccess.GetTexture(), 0, TextureFormat.RGBA32, r =>
            {
                if (r.hasError) { error = "RGB の読み出しに失敗"; return; }
                // readback は下の行から。テクスチャと同じ並びなので、そのまま JPEG にすると上が上になる
                using var encoded = ImageConversion.EncodeNativeArrayToJPG(r.GetData<byte>(), GraphicsFormat.R8G8B8A8_SRGB,
                    (uint)r.width, (uint)r.height, 0, jpegQuality);
                jpeg = encoded.ToArray();
            });
            var depthRequest = AsyncGPUReadback.Request(_depthCopy, 0, r =>
            {
                if (r.hasError) { error = "深度の読み出しに失敗"; return; }
                depthBytes = r.GetData<byte>().ToArray();
            });
            while (!rgbRequest.done || !depthRequest.done) yield return null;
            if (error != null || jpeg == null || depthBytes == null)
            {
                Debug.LogWarning($"{Tag} {error ?? "読み出しに失敗"}", this);
                yield break;
            }

            string meta = JsonConvert.SerializeObject(new
            {
                timestamp,
                device = SystemInfo.deviceModel,
                rgb = new
                {
                    width = size.x, height = size.y,
                    fx = intrinsics.x, fy = intrinsics.y, cx = intrinsics.z, cy = intrinsics.w,
                    pose = new
                    {
                        position = new[] { pose.position.x, pose.position.y, pose.position.z },
                        rotation = new[] { pose.rotation.x, pose.rotation.y, pose.rotation.z, pose.rotation.w },
                    },
                },
                depth = new
                {
                    width = _depthCopy.width, height = _depthCopy.height, format = "rgba32f_uv",
                    reprojection = RowMajor(reprojection),
                },
            });

            yield return Post(jpeg, depthBytes, meta);
        }
        finally
        {
            _busy = false;
            _nextAutoSend = Time.time + sendInterval;
        }
    }

    private IEnumerator Post(byte[] jpeg, byte[] depth, string meta)
    {
        var form = new List<IMultipartFormSection>
        {
            new MultipartFormFileSection("rgb", jpeg, "rgb.jpg", "image/jpeg"),
            new MultipartFormFileSection("depth", depth, "depth.bin", "application/octet-stream"),
            new MultipartFormDataSection("meta", meta),
        };
        var query = new List<string>();
        if (!string.IsNullOrWhiteSpace(recordName)) query.Add("record=" + UnityWebRequest.EscapeURL(recordName.Trim()));
        if (recordOnly) query.Add("analyze=false");
        string url = Url() + (query.Count > 0 ? "?" + string.Join("&", query) : "");

        float started = Time.realtimeSinceStartup;
        using var req = UnityWebRequest.Post(url, form);
        req.timeout = timeoutSeconds;
        yield return req.SendWebRequest();
        float seconds = Time.realtimeSinceStartup - started;
        _sent++;

        if (req.result != UnityWebRequest.Result.Success)
        {
            Debug.LogWarning($"{Tag} 送信に失敗 ({req.responseCode}): {req.error} {req.downloadHandler?.text}" +
                             "（サーバーの起動、Tailscale、Allow downloads over HTTP を確認）", this);
            yield break;
        }
        LastResult = req.downloadHandler.text;
        Debug.Log($"{Tag} #{_sent} {jpeg.Length / 1024}KB + 深度 {depth.Length / 1024}KB, {seconds:0.0}s: {Summary(LastResult)}");
        onResult.Invoke(LastResult);
    }

    /// <summary>
    /// 送る画像の画素での (fx, fy, cx, cy)。画像の行は上から、カメラ座標の y は下向き（サーバーの約束）。
    /// SDK の ViewportPointToRay（ビューポートの y は上向き）を 4 点で測って求めるので、SDK の切り抜きの計算に依存しない。
    /// </summary>
    private Vector4 Intrinsics(Pose pose, Vector2Int size)
    {
        Vector2 Slope(Vector2 viewport)
        {
            Vector3 d = Quaternion.Inverse(pose.rotation) * cameraAccess.ViewportPointToRay(viewport, pose).direction;
            return new Vector2(d.x / d.z, d.y / d.z);
        }
        Vector2 left = Slope(new Vector2(0f, 0.5f)), right = Slope(new Vector2(1f, 0.5f));
        Vector2 bottom = Slope(new Vector2(0.5f, 0f)), top = Slope(new Vector2(0.5f, 1f));
        float fx = size.x / (right.x - left.x);
        float fy = size.y / (top.y - bottom.y);
        return new Vector4(fx, fy, -left.x * fx, top.y * fy);
    }

    private void EnsureDepthCopy(int width, int height)
    {
        if (_depthCopy && _depthCopy.width == width && _depthCopy.height == height) return;
        if (_depthCopy) _depthCopy.Release();
        _depthCopy = new RenderTexture(width, height, 0, GraphicsFormat.R32G32B32A32_SFloat)
        {
            name = "CoGroundDepthCopy",
            filterMode = FilterMode.Point,
        };
        _depthCopy.Create();
    }

    private static float[] RowMajor(Matrix4x4 m)
    {
        var values = new float[16];
        for (int row = 0; row < 4; row++)
            for (int col = 0; col < 4; col++)
                values[row * 4 + col] = m[row, col];
        return values;
    }

    private string Url() => endpoint.TrimEnd('/') + "/perception/frame";

    /// <summary>ログ用の 1 行: 物体ごとの ID と、初めて / 同じ / 動いた。</summary>
    private static string Summary(string json)
    {
        try
        {
            var result = JsonConvert.DeserializeObject<ResultView>(json);
            if (result?.objects == null) return json.Length > 200 ? json.Substring(0, 200) : json;
            var parts = new List<string>();
            foreach (var o in result.objects)
            {
                var part = $"{o.object_id ?? "unlocated"}:{o.track ?? o.source}({o.category ?? o.@class})";
                // ルールが使っている属性について、VLM が答えた値と根拠 (例: fragile=false ← material: plastic)
                if (o.evidence != null && o.attributes != null)
                    foreach (var e in o.evidence)
                        part += $" {e.Key}={(o.attributes.TryGetValue(e.Key, out var v) ? v : "?")}←{e.Value}";
                parts.Add(part);
            }
            return $"objects=[{string.Join(", ", parts)}] vlm_calls={result.vlm?.calls} " +
                   $"located={result.frame?.located} depth={result.frame?.depth_coverage:P0}" +
                   (result.frame?.displaced?.Count > 0 ? $" displaced=[{string.Join(", ", result.frame.displaced)}]" : "");
        }
        catch (JsonException)
        {
            return json;
        }
    }

    private class ResultView
    {
        public List<ObjectView> objects;
        public VlmView vlm;
        public FrameView frame;
    }

    private class ObjectView
    {
        public string object_id, track, source, category, @class;
        /// <summary>material / fragility / appearance と、ルールが使っている属性 (聞いたものだけ)</summary>
        public Dictionary<string, string> attributes;
        /// <summary>ルールが使っている属性ごとの、VLM の判断の根拠</summary>
        public Dictionary<string, string> evidence;
    }

    private class VlmView
    {
        public int calls;
    }

    private class FrameView
    {
        public int located;
        public float depth_coverage;
        public List<string> displaced;
    }
}
