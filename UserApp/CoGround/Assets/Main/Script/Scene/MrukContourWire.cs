using System.Collections.Generic;
using Meta.XR.MRUtilityKit;
using UnityEngine;
#if ENABLE_INPUT_SYSTEM
using UnityEngine.InputSystem;
#endif

/// <summary>
/// MRUK の部屋の輪郭を線 (ワイヤー) で描く。ボタンで表示 / 非表示を切り替える。
/// Gizmos と違って Quest の中でも見える (LineRenderer)。
///
///   - 平面 (壁・床・天井・ドア枠など) = PlaneBoundary2D の輪郭 (無ければ PlaneRect の四角)
///   - 体積 (机・棚など) = VolumeBounds の箱の 12 辺
///
///   切り替え: toggleButton (既定は左スティックの押し込み。左手 X / Y は Before・After パネルが使う)。エディタでは C キーでも切り替わる
///
/// 部屋を読み込んだときに作る。部屋を読み直したら Rebuild() を呼ぶ。
/// </summary>
public class MrukContourWire : MonoBehaviour
{
    [Header("切り替え")]
    [SerializeField] OVRInput.RawButton toggleButton = OVRInput.RawButton.LThumbstick;
    [Tooltip("C キーでも切り替える (エディタ確認用)")]
    [SerializeField] bool allowKeyboard = true;
    [SerializeField] bool visibleOnStart = true;

    [Header("見た目")]
    [SerializeField] float lineWidth = 0.008f;
    [Tooltip("線のマテリアル (全部この 1 つで描く)。空ならラベルの色ごとに FetchGhost と同じ URP のマテリアルを作る")]
    [SerializeField] Material lineMaterial;

    // 自動で作ったマテリアル (色ごと)。旧式の Sprites/Default は Single Pass Instanced で片目がずれて黒く出るので使わない
    readonly Dictionary<Color, Material> autoMaterials = new Dictionary<Color, Material>();
    [Tooltip("描かないラベル")]
    [SerializeField] MRUKAnchor.SceneLabels hideLabels = MRUKAnchor.SceneLabels.GLOBAL_MESH;

    readonly List<GameObject> lines = new List<GameObject>();
    bool visible;

    public bool Visible
    {
        get => visible;
        set
        {
            visible = value;
            foreach (var go in lines) if (go != null) go.SetActive(visible);
        }
    }

    void Start()
    {
        visible = visibleOnStart;
        if (MRUK.Instance == null)
        {
            Debug.LogError("[MrukContourWire] MRUK がシーンにない");
            enabled = false;
            return;
        }
        MRUK.Instance.RegisterSceneLoadedCallback(Rebuild);
    }

    void Update()
    {
        if (OVRInput.GetDown(toggleButton) || (allowKeyboard && ToggleKeyDown())) Visible = !Visible;
    }

    void OnDestroy()
    {
        Clear();
        foreach (var m in autoMaterials.Values) if (m != null) Destroy(m);
        autoMaterials.Clear();
    }

    /// <summary>今読み込まれている部屋から線を作り直す</summary>
    public void Rebuild()
    {
        Clear();
        if (MRUK.Instance == null) return;

        foreach (var room in MRUK.Instance.Rooms)
        {
            if (room == null) continue;
            foreach (var a in room.Anchors)
            {
                if (a == null || (a.Label & hideLabels) != 0) continue;
                var points = Outline(a);
                if (points == null) continue;

                var go = new GameObject($"contour_{a.Label}".ToLowerInvariant());
                go.transform.SetParent(a.transform, false);
                var lr = go.AddComponent<LineRenderer>();
                lr.useWorldSpace = false;
                lr.loop = a.VolumeBounds == null; // 箱は一筆書きの経路で描くので閉じない
                lr.positionCount = points.Count;
                lr.SetPositions(points.ToArray());
                lr.widthMultiplier = lineWidth;
                var color = ColorOf(a.Label);
                lr.sharedMaterial = GetMaterial(color);
                lr.startColor = lr.endColor = color;
                lr.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
                lr.receiveShadows = false;
                lr.numCornerVertices = 0;
                go.SetActive(visible);
                lines.Add(go);
            }
        }
        Debug.Log($"[MrukContourWire] 輪郭 {lines.Count} 本");
    }

    /// <summary>アンカーのローカル座標での輪郭。形が無ければ null</summary>
    static List<Vector3> Outline(MRUKAnchor a)
    {
        if (a.VolumeBounds is Bounds b) // 机などは天板の平面も持つので、体積を先に見る
        {
            Vector3 mn = b.min, mx = b.max;
            var b0 = new Vector3(mn.x, mn.y, mn.z); var b1 = new Vector3(mx.x, mn.y, mn.z);
            var b2 = new Vector3(mx.x, mx.y, mn.z); var b3 = new Vector3(mn.x, mx.y, mn.z);
            var t0 = new Vector3(mn.x, mn.y, mx.z); var t1 = new Vector3(mx.x, mn.y, mx.z);
            var t2 = new Vector3(mx.x, mx.y, mx.z); var t3 = new Vector3(mn.x, mx.y, mx.z);
            // 12 辺をすべて通る一筆書き (縦の辺のうち 3 本は往復する)
            return new List<Vector3> { b0, b1, b2, b3, b0, t0, t1, b1, t1, t2, b2, t2, t3, b3, t3, t0 };
        }

        var pts = new List<Vector3>();
        if (a.PlaneBoundary2D != null && a.PlaneBoundary2D.Count >= 3)
        {
            foreach (var p in a.PlaneBoundary2D) pts.Add(new Vector3(p.x, p.y, 0f));
            return pts;
        }
        if (a.PlaneRect is Rect r)
        {
            pts.Add(new Vector3(r.xMin, r.yMin, 0f));
            pts.Add(new Vector3(r.xMax, r.yMin, 0f));
            pts.Add(new Vector3(r.xMax, r.yMax, 0f));
            pts.Add(new Vector3(r.xMin, r.yMax, 0f));
            return pts;
        }
        return null;
    }

    static Color ColorOf(MRUKAnchor.SceneLabels label)
    {
        if ((label & MRUKAnchor.SceneLabels.FLOOR) != 0) return new Color(0.3f, 0.9f, 0.3f);
        if ((label & MRUKAnchor.SceneLabels.CEILING) != 0) return new Color(0.7f, 0.7f, 0.7f);
        if ((label & (MRUKAnchor.SceneLabels.WALL_FACE | MRUKAnchor.SceneLabels.INNER_WALL_FACE)) != 0) return new Color(0.3f, 0.6f, 1f);
        if ((label & (MRUKAnchor.SceneLabels.DOOR_FRAME | MRUKAnchor.SceneLabels.WINDOW_FRAME | MRUKAnchor.SceneLabels.WALL_ART)) != 0) return new Color(1f, 0.9f, 0.2f);
        return new Color(1f, 0.45f, 0.2f); // 家具など
    }

    Material GetMaterial(Color color)
    {
        if (lineMaterial != null) return lineMaterial;
        if (!autoMaterials.TryGetValue(color, out var mat))
        {
            // ゴーストや経路の線と同じマテリアル (VR の両目で正しく描ける)。色はマテリアル側に持たせる
            mat = FetchGhost.MakeMaterial(color);
            mat.name = "MrukContourWire (auto)";
            autoMaterials[color] = mat;
        }
        return mat;
    }

    void Clear()
    {
        foreach (var go in lines) if (go != null) Destroy(go);
        lines.Clear();
    }

    static bool ToggleKeyDown()
    {
#if ENABLE_INPUT_SYSTEM
        return Keyboard.current != null && Keyboard.current.cKey.wasPressedThisFrame;
#else
        return Input.GetKeyDown(KeyCode.C);
#endif
    }
}
