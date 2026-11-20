using System;
using System.Collections.Generic;
using System.Threading.Tasks;
using Meta.XR;
using Meta.XR.BuildingBlocks.AIBlocks;
using Meta.XR.EnvironmentDepth;
using UnityEngine;

/// <summary>
/// Image Segmentation Building Block の使い方を確認するための最小サンプル。
/// 検出した物体の「マスク（形）」の上の点を 3D 化し、点群と 3D ボックスとラベルを表示する。
///
/// ■ なぜ標準の ImageSegmentationVisualizer では何も出ないのか
///   標準の Visualizer は DepthTextureAccess（= EnvironmentDepthManager のデプス画像）が必須。
///   デプス画像が来ないと Draw3D の最初で何も描かずに return する。
///   このプロジェクトでは EnvironmentDepthManager が使えない状態なので、代わりに
///   EnvironmentRaycastManager（Passthrough Camera API サンプルと同じ方式）で 3D 化する。
///
/// ■ Segmentation の結果（SegmentationResult）の中身
///   numObjects            … 検出した物体の数
///   boxes[i*4 + 0..3]     … 矩形 (中心X, 中心Y, 幅, 高さ)。0..1 に正規化済み（画像の左上が原点）
///   classIds[i], scores[i]… クラス番号とスコア。labels[classIds[i]] でクラス名
///   masks                 … 物体ごとに maskWidth × maskHeight の 0..1（1 に近いほど物体）
///                           画像全体に対するマスクで、矩形の外にもにじむことがあるので矩形内だけ使う
///
/// ■ このスクリプトがやること
///   1. ImageSegmentationAgent.OnSegmentationUpdated を受け取る
///   2. 物体ごとに、矩形の中を格子状にサンプリングし、マスクが「物体」の点だけ残す
///   3. その点へパススルーカメラからレイを飛ばし、EnvironmentRaycastManager で現実の面に当てる → 3D 点
///   4. 3D 点の広がりから箱（位置・幅・高さ・奥行き）を作る。奥行きも点から実測（見えている面の分だけ）
///   5. デバッグ用に、カメラ画像＋マスクを視界の左下に表示する
///
/// ■ 使い方
///   [BuildingBlock] Image Segmentation の GameObject にこのコンポーネントを追加するだけ。
/// </summary>
public class SegmentationBox3DSpawner : MonoBehaviour
{
    [Header("参照（空なら自動取得）")]
    [SerializeField] private ImageSegmentationAgent agent;

    [Header("フィルタ")]
    [Tooltip("このスコア未満の物体は無視する")]
    [Range(0, 1)] [SerializeField] private float minScore = 0.5f;

    [Tooltip("空なら全クラス。例: \"cup\"")]
    [SerializeField] private string onlyLabel = "";

    [Header("3D 化")]
    [Tooltip("矩形の中を N×N の格子でサンプリングする（多いほど正確だが重い）")]
    [Range(3, 16)] [SerializeField] private int gridSize = 8;

    [Tooltip("マスクの値がこれ以上なら「物体の画素」とみなす")]
    [Range(0, 1)] [SerializeField] private float maskThreshold = 0.5f;

    [Tooltip("3D 点がこれ未満なら箱を作らない")]
    [SerializeField] private int minPoints = 4;

    [Tooltip("奥行きの最小値（メートル）。見えている面しか測れないので薄くなりすぎないように")]
    [SerializeField] private float minDepth = 0.03f;

    [Header("表示")]
    [SerializeField] private bool showPoints = true;
    [SerializeField] private float pointSize = 0.01f;
    [SerializeField] private float lineWidth = 0.005f;

    [Header("デバッグ")]
    [SerializeField] private bool logDetections = true;
    [SerializeField] private float statusLogInterval = 3f;
    [Tooltip("カメラ画像とマスクを視界の左下に表示する")]
    [SerializeField] private bool showCameraPreview = true;

    private const string Tag = "[SegBox3D]";

    // 物体ごとの色（マスク・点・箱で共通）
    private static readonly Color[] Palette =
    {
        Color.cyan, Color.magenta, Color.yellow, Color.green,
        new(1f, 0.5f, 0f), new(0.5f, 0.6f, 1f), Color.red, Color.white,
    };

    private PassthroughCameraAccess _cam;
    private EnvironmentRaycastManager _raycast;

    private readonly List<WireBox> _boxes = new();
    private Material _lineMaterial;

    // 点群の描画（DrawMeshInstanced で一括描画）
    private Mesh _pointMesh;
    private Material _pointMaterial;
    // 物体ごとに (点の行列リスト, 色) を持ち、物体単位で色を変えて描く
    private readonly List<(List<Matrix4x4> matrices, Color color)> _pointGroups = new();
    private MaterialPropertyBlock _pointProps;

    // プレビュー
    private GameObject _preview, _maskOverlay;
    private Texture2D _maskTexture;
    private Color32[] _maskPixels;

    // 状態ログ用
    private int _callbackCount, _objectCount, _boxCount, _noPointsCount;
    private string _lastRaycastStatus = "-";
    private float _nextStatusTime;

    // ------------------------------------------------------------------
    // ライフサイクル
    // ------------------------------------------------------------------

    private void Awake()
    {
        if (agent == null) agent = GetComponent<ImageSegmentationAgent>();
        _cam = FindAnyObjectByType<PassthroughCameraAccess>();

        _raycast = FindAnyObjectByType<EnvironmentRaycastManager>();
        if (_raycast == null && EnvironmentRaycastManager.IsSupported)
            _raycast = gameObject.AddComponent<EnvironmentRaycastManager>();

        Debug.Log($"{Tag} Awake: agent={(agent ? "OK" : "なし")}, passthroughCamera={(_cam ? "OK" : "なし")}, " +
                  $"EnvironmentRaycastManager.IsSupported={EnvironmentRaycastManager.IsSupported}, " +
                  $"EnvironmentDepthManager.IsSupported={EnvironmentDepthManager.IsSupported}");

        _lineMaterial = new Material(Shader.Find("Sprites/Default"));

        _pointMesh = Resources.GetBuiltinResource<Mesh>("Cube.fbx");
        _pointMaterial = new Material(Shader.Find("Sprites/Default")) { enableInstancing = true };
        _pointProps = new MaterialPropertyBlock();
    }

    private void Start()
    {
        // 標準の Visualizer はデプス画像が無いと何も描かないので、その環境では止めておく（ログが静かになる）
        var std = GetComponent<ImageSegmentationVisualizer>();
        if (std && std.enabled && !EnvironmentDepthManager.IsSupported)
        {
            Debug.LogWarning($"{Tag} EnvironmentDepthManager 非対応 → 標準の ImageSegmentationVisualizer を無効化し、" +
                             "EnvironmentRaycastManager で 3D 化します");
            std.enabled = false;
        }
    }

    private void OnEnable()
    {
        // Agent は推論を投げっぱなしにしているので、例外がログに出ない。未観測の Task 例外を拾う。
        TaskScheduler.UnobservedTaskException += OnUnobservedTaskException;
        if (agent == null) { Debug.LogError($"{Tag} ImageSegmentationAgent が見つかりません"); return; }
        agent.OnSegmentationUpdated += OnSegmentation;
    }

    private void OnDisable()
    {
        TaskScheduler.UnobservedTaskException -= OnUnobservedTaskException;
        if (agent != null) agent.OnSegmentationUpdated -= OnSegmentation;
    }

    private static void OnUnobservedTaskException(object sender, UnobservedTaskExceptionEventArgs e)
    {
        Debug.LogError($"{Tag} 推論タスクで例外（Agent 内部で握りつぶされていたもの）:\n{e.Exception}");
        e.SetObserved();
    }

    private void Update()
    {
        DrawPoints();
        UpdatePreview();

        if (statusLogInterval <= 0f || Time.time < _nextStatusTime) return;
        _nextStatusTime = Time.time + statusLogInterval;

        // 未観測 Task 例外は GC のタイミングで通知されるので、デバッグ用に GC を回す
        GC.Collect();
        GC.WaitForPendingFinalizers();

        // 見方:
        //   callbacks が増えない   → 推論結果が 0 件（カメラ画像が来ていない / 何も写っていない）
        //   noPoints が増える      → マスクはあるが 3D 化に失敗（lastRaycast を見る: NotReady / NoHit / NotSupported）
        var tex = _cam ? _cam.GetTexture() : null;
        Debug.Log($"{Tag} status: cameraPlaying={(_cam && _cam.IsPlaying)}, " +
                  $"texture={(tex ? $"{tex.width}x{tex.height}" : "null")}, " +
                  $"raycast={(_raycast ? "OK" : "なし")}, lastRaycast={_lastRaycastStatus}, " +
                  $"callbacks={_callbackCount}, objects={_objectCount}, boxes={_boxCount}, noPoints={_noPointsCount}");
    }

    // ------------------------------------------------------------------
    // Segmentation の結果を受け取るたびに呼ばれる
    // ------------------------------------------------------------------

    private void OnSegmentation(SegmentationResult r)
    {
        // Agent の非同期タスク内から呼ばれ、例外は握りつぶされるので、ここで全部拾う
        try { HandleSegmentation(r); }
        catch (Exception e) { Debug.LogException(e); }
    }

    private void HandleSegmentation(SegmentationResult r)
    {
        _callbackCount++;
        _pointGroups.Clear();

        var tex = _cam ? _cam.GetTexture() : null;
        if (!tex) return;

        // 結果が出た時点のカメラ姿勢を使う（推論にかかった時間分のずれは残る。改善プランの Step 1 で対応予定）
        Pose pose = _cam.GetCameraPose();

        if (showCameraPreview) BeginMaskTexture(r);

        int used = 0;
        var points = new List<Vector3>();

        for (int i = 0; i < r.numObjects; i++)
        {
            string label = r.labels != null && r.classIds[i] < r.labels.Length ? r.labels[r.classIds[i]] : $"cls_{r.classIds[i]}";
            float score = r.scores[i];
            if (score < minScore) continue;
            if (!string.IsNullOrEmpty(onlyLabel) && label != onlyLabel) continue;
            _objectCount++;

            Color color = Palette[i % Palette.Length];

            // ① 矩形（0..1、左上原点、中心＋幅高さ）→ 左上・右下
            float cx = r.boxes[i * 4 + 0], cy = r.boxes[i * 4 + 1];
            float w = r.boxes[i * 4 + 2], h = r.boxes[i * 4 + 3];
            float u0 = Mathf.Clamp01(cx - w * 0.5f), v0 = Mathf.Clamp01(cy - h * 0.5f);
            float u1 = Mathf.Clamp01(cx + w * 0.5f), v1 = Mathf.Clamp01(cy + h * 0.5f);

            if (showCameraPreview) PaintMask(r, i, u0, v0, u1, v1, color);

            // ② 矩形内を格子サンプリング → マスクが物体の点だけ → ③ レイキャストで 3D 点に
            points.Clear();
            for (int gx = 0; gx < gridSize; gx++)
            for (int gy = 0; gy < gridSize; gy++)
            {
                // セルの中心を使う（矩形の端は背景になりやすいので含めない）
                float u = Mathf.Lerp(u0, u1, (gx + 0.5f) / gridSize);
                float v = Mathf.Lerp(v0, v1, (gy + 0.5f) / gridSize);

                if (MaskValue(r, i, u, v) < maskThreshold) continue;

                // 画像は上が v=0、ビューポートは下が 0 なので反転
                Ray ray = _cam.ViewportPointToRay(new Vector2(u, 1f - v), pose);
                if (_raycast == null) continue;
                bool ok = _raycast.Raycast(ray, out EnvironmentRaycastHit hit);
                _lastRaycastStatus = hit.status.ToString();
                if (ok) points.Add(hit.point);
            }

            if (points.Count < minPoints)
            {
                _noPointsCount++;
                if (logDetections) Debug.LogWarning($"{Tag}   {label} {score:0.00}: 3D 点が足りない ({points.Count}/{minPoints})");
                continue;
            }

            // ④ 3D 点から箱を作る
            BuildBox(points, pose.position, out Vector3 center, out Quaternion rot, out Vector3 size);
            GetBox(used++).Show(center, rot, size, $"{label} {score:0.00}", color);
            _boxCount++;

            if (showPoints)
            {
                var matrices = new List<Matrix4x4>(points.Count);
                foreach (var p in points) matrices.Add(Matrix4x4.TRS(p, Quaternion.identity, Vector3.one * pointSize));
                _pointGroups.Add((matrices, color));
            }

            if (logDetections)
                Debug.Log($"{Tag}   {label} {score:0.00}: points={points.Count} center={center:F2} " +
                          $"size=({size.x:F2},{size.y:F2},{size.z:F2})m 距離={Vector3.Distance(pose.position, center):F2}m");
        }

        for (int i = used; i < _boxes.Count; i++) _boxes[i].Hide();
        if (showCameraPreview)
        {
            _maskTexture.SetPixels32(_maskPixels);
            _maskTexture.Apply();
        }
    }

    /// <summary>マスクの値（0..1）を、画像上の正規化座標 (u, v) で取り出す。</summary>
    private static float MaskValue(SegmentationResult r, int obj, float u, float v)
    {
        int mx = Mathf.Clamp((int)(u * r.maskWidth), 0, r.maskWidth - 1);
        int my = Mathf.Clamp((int)(v * r.maskHeight), 0, r.maskHeight - 1);
        float m = r.masks[obj * r.maskWidth * r.maskHeight + my * r.maskWidth + mx];
        return r.maskAreLogits ? 1f / (1f + Mathf.Exp(-m)) : m;
    }

    /// <summary>
    /// 3D 点の集まりから箱を作る。
    /// 向き: カメラ→物体の方向を水平にしたもの（机の上の物を想定して傾けない）
    /// 大きさ: その向きの座標軸で、点の最小〜最大を測る
    /// </summary>
    private void BuildBox(List<Vector3> points, Vector3 cameraPos,
        out Vector3 center, out Quaternion rot, out Vector3 size)
    {
        Vector3 mean = Vector3.zero;
        foreach (var p in points) mean += p;
        mean /= points.Count;

        Vector3 forward = mean - cameraPos;
        forward.y = 0f;
        if (forward.sqrMagnitude < 1e-6f) forward = Vector3.forward;
        rot = Quaternion.LookRotation(forward.normalized, Vector3.up);

        // 箱のローカル座標で最小・最大を取る
        Quaternion inv = Quaternion.Inverse(rot);
        Vector3 min = Vector3.positiveInfinity, max = Vector3.negativeInfinity;
        foreach (var p in points)
        {
            Vector3 l = inv * (p - mean);
            min = Vector3.Min(min, l);
            max = Vector3.Max(max, l);
        }

        size = max - min;
        // 見えているのは手前の面だけなので、奥行きは薄く出やすい。最低限の厚みを持たせ、奥側に伸ばす
        if (size.z < minDepth)
        {
            max.z = min.z + minDepth;
            size.z = minDepth;
        }
        center = mean + rot * ((min + max) * 0.5f);
    }

    // ------------------------------------------------------------------
    // 表示: 点群
    // ------------------------------------------------------------------

    private void DrawPoints()
    {
        if (!showPoints) return;
        // 物体ごとに色を変えて一括描画（1 物体あたり最大 gridSize^2 = 256 点なので 1023 個の上限に収まる）
        foreach (var (matrices, color) in _pointGroups)
        {
            _pointProps.SetColor("_Color", color);
            Graphics.DrawMeshInstanced(_pointMesh, 0, _pointMaterial, matrices, _pointProps);
        }
    }

    // ------------------------------------------------------------------
    // 表示: カメラ画像＋マスクのプレビュー（視界の左下）
    // ------------------------------------------------------------------

    private void UpdatePreview()
    {
        if (!showCameraPreview || _cam == null || Camera.main == null)
        {
            if (_preview) _preview.SetActive(false);
            return;
        }

        if (_preview == null)
        {
            _preview = CreateQuad("SegBox3D_CameraPreview", Shader.Find("Unlit/Texture"), Camera.main.transform);
            _preview.transform.localPosition = new Vector3(-0.15f, -0.12f, 0.5f);
            // マスクはカメラ画像の少し手前に半透明で重ねる
            _maskOverlay = CreateQuad("SegBox3D_MaskOverlay", Shader.Find("Sprites/Default"), _preview.transform);
            _maskOverlay.transform.localPosition = new Vector3(0f, 0f, -0.001f);
        }

        _preview.SetActive(true);
        var tex = _cam.GetTexture();
        _preview.GetComponent<Renderer>().material.mainTexture = tex;
        float aspect = tex && tex.height > 0 ? (float)tex.width / tex.height : 4f / 3f;
        _preview.transform.localScale = new Vector3(0.15f * aspect, 0.15f, 1f);
        if (_maskTexture) _maskOverlay.GetComponent<Renderer>().material.mainTexture = _maskTexture;
    }

    private static GameObject CreateQuad(string name, Shader shader, Transform parent)
    {
        var go = GameObject.CreatePrimitive(PrimitiveType.Quad);
        go.name = name;
        Destroy(go.GetComponent<Collider>());
        go.GetComponent<Renderer>().material = new Material(shader);
        go.transform.SetParent(parent, false);
        return go;
    }

    private void BeginMaskTexture(SegmentationResult r)
    {
        if (_maskTexture == null || _maskTexture.width != r.maskWidth || _maskTexture.height != r.maskHeight)
        {
            _maskTexture = new Texture2D(r.maskWidth, r.maskHeight, TextureFormat.RGBA32, false)
                { filterMode = FilterMode.Point, wrapMode = TextureWrapMode.Clamp };
            _maskPixels = new Color32[r.maskWidth * r.maskHeight];
        }
        Array.Clear(_maskPixels, 0, _maskPixels.Length);
    }

    /// <summary>物体 obj のマスク（矩形内のみ）をプレビュー用テクスチャに色付きで描く。</summary>
    private void PaintMask(SegmentationResult r, int obj, float u0, float v0, float u1, float v1, Color color)
    {
        int W = r.maskWidth, H = r.maskHeight;
        int x0 = (int)(u0 * W), x1 = Mathf.Min(W - 1, (int)(u1 * W));
        int y0 = (int)(v0 * H), y1 = Mathf.Min(H - 1, (int)(v1 * H));
        var c = (Color32)new Color(color.r, color.g, color.b, 0.5f);
        for (int y = y0; y <= y1; y++)
        for (int x = x0; x <= x1; x++)
        {
            float m = r.masks[obj * W * H + y * W + x];
            if (r.maskAreLogits) m = 1f / (1f + Mathf.Exp(-m));
            if (m < maskThreshold) continue;
            // マスクは上が y=0、Texture2D は下が y=0 なので上下反転して書く
            _maskPixels[(H - 1 - y) * W + x] = c;
        }
    }

    // ------------------------------------------------------------------
    // 表示: ワイヤーフレームの箱 + ラベル
    // ------------------------------------------------------------------

    private WireBox GetBox(int index)
    {
        while (_boxes.Count <= index)
            _boxes.Add(new WireBox($"SegBox_{_boxes.Count}", _lineMaterial, lineWidth));
        return _boxes[index];
    }

    private class WireBox
    {
        private readonly GameObject _root;
        private readonly Transform _wire;
        private readonly LineRenderer _line;
        private readonly TextMesh _label;

        public WireBox(string name, Material mat, float lineWidth)
        {
            _root = new GameObject(name);

            var wireGo = new GameObject("Wire");
            wireGo.transform.SetParent(_root.transform, false);
            _wire = wireGo.transform;
            _line = wireGo.AddComponent<LineRenderer>();
            _line.useWorldSpace = false;   // ローカル頂点 → Transform のスケールで箱の大きさになる
            _line.material = mat;
            _line.startWidth = _line.endWidth = lineWidth;
            _line.positionCount = CubePath.Length;
            _line.SetPositions(CubePath);

            var labelGo = new GameObject("Label");
            labelGo.transform.SetParent(_root.transform, false);
            _label = labelGo.AddComponent<TextMesh>();
            var font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
            _label.font = font;
            labelGo.GetComponent<MeshRenderer>().sharedMaterial = font.material;
            _label.anchor = TextAnchor.LowerCenter;
            _label.characterSize = 0.01f;
            _label.fontSize = 48;
        }

        public void Show(Vector3 center, Quaternion rot, Vector3 size, string text, Color color)
        {
            _root.SetActive(true);
            _root.transform.SetPositionAndRotation(center, rot);
            _wire.localScale = size;
            _line.startColor = _line.endColor = color;
            _label.text = text;
            _label.color = color;
            _label.transform.localPosition = new Vector3(0f, size.y * 0.5f + 0.01f, 0f);
            _label.transform.localRotation = Quaternion.Euler(0f, 180f, 0f); // ユーザー側を向ける
        }

        public void Hide() => _root.SetActive(false);

        // 単位立方体の 12 辺を一筆書きする頂点列
        private static readonly Vector3[] CubePath =
        {
            new(-.5f, -.5f, -.5f), new(.5f, -.5f, -.5f), new(.5f, -.5f, .5f), new(-.5f, -.5f, .5f), new(-.5f, -.5f, -.5f),
            new(-.5f, .5f, -.5f), new(.5f, .5f, -.5f), new(.5f, -.5f, -.5f), new(.5f, .5f, -.5f),
            new(.5f, .5f, .5f), new(.5f, -.5f, .5f), new(.5f, .5f, .5f),
            new(-.5f, .5f, .5f), new(-.5f, -.5f, .5f), new(-.5f, .5f, .5f),
            new(-.5f, .5f, -.5f),
        };
    }
}
