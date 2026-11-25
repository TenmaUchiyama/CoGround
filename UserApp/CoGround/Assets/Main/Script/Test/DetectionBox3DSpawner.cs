using System.Collections.Generic;
using Meta.XR;
using Meta.XR.BuildingBlocks.AIBlocks;
using UnityEngine;

/// <summary>
/// 検出された物体の位置に「3D のワイヤーフレームボックス」と「ラベル」を置くデバッグ表示。
///
/// 2D → 3D・追跡・平滑化・固定は <see cref="DetectionPipeline"/> が行い（DR マスクと共通）、
/// このスクリプトはその結果（<see cref="DetectionPipeline.Tracks"/>）を描くだけ。
///
///   ObjectDetectionAgent ─▶ DetectionPipeline (DetectionLocator ─▶ DetectionTracker) ─▶ このスクリプト
///
/// ■ 使い方
///   [BuildingBlock] Object Detection の GameObject にこのコンポーネントを追加するだけ。
///   DetectionPipeline は無ければ自動で追加される（設定を変えたいときは自分で追加して Inspector で調整）。
///   （Meta 標準の 2D 枠を消したい場合は ObjectDetectionVisualizer の Show Bounding Boxes を OFF）
/// </summary>
public class DetectionBox3DSpawner : MonoBehaviour
{
    [Header("参照（空なら同じ GameObject から自動取得）")]
    [SerializeField] private ObjectDetectionAgent agent;
    [SerializeField] private DetectionPipeline pipeline;

    [Header("フィルタ")]
    [Tooltip("空なら全クラスを表示。例: \"cup\" にすると cup だけ表示。")]
    [SerializeField] private string onlyLabel = "";

    [Header("ボックスの見た目")]
    [Tooltip("線の太さ（メートル）")]
    [SerializeField] private float lineWidth = 0.005f;

    [Tooltip("追従中の箱の色")]
    [SerializeField] private Color boxColor = Color.cyan;

    [Tooltip("安定して固定された箱の色")]
    [SerializeField] private Color lockedColor = Color.green;

    [Header("デバッグ")]
    [Tooltip("推論に渡しているカメラ画像を視界の左下に小さく表示する（真っ黒なら画像が来ていない）")]
    [SerializeField] private bool showCameraPreview = true;

    private const string Tag = "[DetectBox3D]";

    // 毎回 Instantiate / Destroy しないよう、作ったボックスを使い回す
    private readonly List<DetectionBox> _boxes = new();
    private Material _lineMaterial;

    private PassthroughCameraAccess _cam;
    private GameObject _preview;
    private Renderer _previewRenderer;

    // ------------------------------------------------------------------
    // ライフサイクル
    // ------------------------------------------------------------------

    private void Awake()
    {
        if (agent == null) agent = GetComponent<ObjectDetectionAgent>();
        if (pipeline == null) pipeline = DetectionPipeline.GetOrCreate(agent);
        if (pipeline == null) Debug.LogError($"{Tag} ObjectDetectionAgent が見つかりません");
        _cam = FindAnyObjectByType<PassthroughCameraAccess>();

        // Sprites/Default はどのパイプラインでも使えて、色をそのまま出せる
        var shader = Shader.Find("Sprites/Default");
        if (shader == null) Debug.LogError($"{Tag} Shader 'Sprites/Default' が見つかりません（ビルドに含まれていない）。線が表示されません");
        _lineMaterial = new Material(shader);
    }

    private void OnDisable()
    {
        foreach (var b in _boxes) b.Hide();
    }

    private void Update()
    {
        UpdateCameraPreview();
        if (pipeline == null) return;

        int used = 0;
        foreach (var track in pipeline.Tracks)
        {
            // 数回検出されるまでは出さない（一瞬だけの誤検出を出さないため）
            if (!track.IsConfirmed) continue;
            if (!string.IsNullOrEmpty(onlyLabel) && !track.Label.StartsWith(onlyLabel)) continue;

            GetBox(used++).Show(track.Center, track.Rotation, track.Size,
                $"{track.Label} {track.Score:0.00}{(track.IsLocked ? " [locked]" : "")}",
                track.IsLocked ? lockedColor : boxColor);
        }

        // 今回使わなかったボックスは隠す
        for (int i = used; i < _boxes.Count; i++)
            _boxes[i].Hide();
    }

    // ------------------------------------------------------------------
    // デバッグ: 推論に渡しているカメラ画像を視界に表示
    // ------------------------------------------------------------------

    private void UpdateCameraPreview()
    {
        // カメラの許可が下りるまで PassthroughCameraAccess は無効のことがある。そのあいだ GetTexture を呼ぶとエラーになる
        if (!showCameraPreview || _cam == null || !_cam.isActiveAndEnabled || !_cam.IsPlaying || Camera.main == null)
        {
            if (_preview) _preview.SetActive(false);
            return;
        }

        if (_preview == null)
        {
            _preview = GameObject.CreatePrimitive(PrimitiveType.Quad);
            _preview.name = "DetectBox3D_CameraPreview";
            Destroy(_preview.GetComponent<Collider>());
            _previewRenderer = _preview.GetComponent<Renderer>();
            _previewRenderer.material = new Material(Shader.Find("Unlit/Texture"));
            _preview.transform.SetParent(Camera.main.transform, false);
            _preview.transform.localPosition = new Vector3(-0.15f, -0.12f, 0.5f);
        }

        _preview.SetActive(true);
        var tex = _cam.GetTexture();
        _previewRenderer.material.mainTexture = tex;
        float aspect = tex && tex.height > 0 ? (float)tex.width / tex.height : 4f / 3f;
        _preview.transform.localScale = new Vector3(0.15f * aspect, 0.15f, 1f);
    }

    private DetectionBox GetBox(int index)
    {
        while (_boxes.Count <= index)
            _boxes.Add(new DetectionBox($"DetectionBox_{_boxes.Count}", _lineMaterial, boxColor, lineWidth));
        return _boxes[index];
    }

    // ------------------------------------------------------------------

    private class DetectionBox
    {
        private readonly GameObject _root;      // 位置・回転だけを持つ（スケール 1）
        private readonly Transform _wire;       // 箱の大きさに合わせてスケール
        private readonly TextMesh _label;
        private readonly LineRenderer _line;

        public DetectionBox(string name, Material mat, Color color, float lineWidth)
        {
            _root = new GameObject(name);

            // --- ワイヤーフレーム（単位立方体の 12 辺を 1 本の線で一筆書き） ---
            var wireGo = new GameObject("Wire");
            wireGo.transform.SetParent(_root.transform, false);
            _wire = wireGo.transform;

            var lr = wireGo.AddComponent<LineRenderer>();
            lr.useWorldSpace = false;     // 頂点をローカル座標で持つ → Transform のスケールで箱が伸びる
            lr.material = mat;
            lr.startColor = lr.endColor = color;
            lr.startWidth = lr.endWidth = lineWidth;
            lr.positionCount = CubePath.Length;
            lr.SetPositions(CubePath);
            _line = lr;

            // --- ラベル（箱の上に表示） ---
            var labelGo = new GameObject("Label");
            labelGo.transform.SetParent(_root.transform, false);
            _label = labelGo.AddComponent<TextMesh>();
            // TextMesh はフォントを指定しないと何も表示されないので、Unity 内蔵フォントを使う
            var font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
            _label.font = font;
            labelGo.GetComponent<MeshRenderer>().sharedMaterial = font.material;
            _label.anchor = TextAnchor.LowerCenter;
            _label.characterSize = 0.01f;
            _label.fontSize = 48;
            _label.color = color;
        }

        public void Show(Vector3 center, Quaternion rotation, Vector3 size, string text, Color color)
        {
            _root.SetActive(true);
            _line.startColor = _line.endColor = color;
            _label.color = color;
            _root.transform.SetPositionAndRotation(center, rotation);
            _wire.localScale = size;

            _label.text = text;
            _label.transform.localPosition = new Vector3(0f, size.y * 0.5f + 0.01f, 0f);
            // ラベルは見ている人の方へ向ける。TextMesh は -Z 側から読めるので、+Z をカメラから離れる向きにする
            // (箱の Z は奥行き方向だが、回り込んでも読めるよう毎フレームカメラ基準で向ける。水平に回すだけ)
            var cam = Camera.main;
            var dir = cam != null ? _label.transform.position - cam.transform.position : rotation * Vector3.forward;
            dir.y = 0f;
            _label.transform.rotation = dir.sqrMagnitude > 1e-6f ? Quaternion.LookRotation(dir, Vector3.up) : rotation;
        }

        public void Hide() => _root.SetActive(false);
        public bool IsActive => _root.activeSelf;

        // 単位立方体（-0.5 ～ 0.5）の 12 辺をなぞる頂点列（一部の辺は往復して戻る）
        private static readonly Vector3[] CubePath =
        {
            B0, B1, B2, B3, B0,     // 底面を一周
            T0, T1, B1, T1,         // 縦の辺 B0-T0, B1-T1
            T2, B2, T2,             // 縦の辺 B2-T2
            T3, B3, T3,             // 縦の辺 B3-T3
            T0,                     // 上面を閉じる
        };

        private static Vector3 B0 => new(-0.5f, -0.5f, -0.5f);
        private static Vector3 B1 => new( 0.5f, -0.5f, -0.5f);
        private static Vector3 B2 => new( 0.5f, -0.5f,  0.5f);
        private static Vector3 B3 => new(-0.5f, -0.5f,  0.5f);
        private static Vector3 T0 => new(-0.5f,  0.5f, -0.5f);
        private static Vector3 T1 => new( 0.5f,  0.5f, -0.5f);
        private static Vector3 T2 => new( 0.5f,  0.5f,  0.5f);
        private static Vector3 T3 => new(-0.5f,  0.5f,  0.5f);
    }
}
