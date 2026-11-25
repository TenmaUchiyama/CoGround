using System.Collections.Generic;
using TMPro;
using UnityEngine;
using UnityEngine.UI;

/// <summary>
/// 家庭ルールを MR で見せるタグ。Prefab (Assets/Main/Resources/RuleTag/) のルートに付いている。
/// 色で「何を伝えるか」、Prefab で「どこに貼るか」を分ける。
///
/// ■ 色 (CoGroundRuleStyle の ScriptableObject)
///   義務 = 青、禁止 = 赤、判断できない = 黄、計画できない = 灰、許可 = 紫 (既定)。
///   Style が空なら Resources/CoGroundRuleStyle を使う。アイコンを入れればアイコンも出す。
///
/// ■ Prefab
///   RuleBubble     物体の上の吹き出し (Interaction SDK UI Set の Tooltip が元)。ルート = 矢印の先
///   RuleSign       置き場所に立てる看板 (UI Set の Backplate が元) + 棒。ルート = 棒の根元
///   RuleFloorArea  床の斜線の模様 + 外枠 + 床に貼った文字。ルート = エリアの中心
///   見た目 (大きさ・余白・文字の大きさ・棒の長さ) は Prefab を開いて直してよい。
///   色と文字はこのスクリプトが入れる。作り直しはメニュー CoGround > ルール表示の Prefab を作る。
///
/// ■ 文字
///   1 行目 = 「Rule Id  Text」(例: N1  触らない)。Show Kind Label なら頭に【禁止】などの種類も出す。
///   Before と After で同じ Rule Id を使うと、どのルールが計画のどこに効いたかを目で追える。
///   2 行目 = Note (After の理由など。例: N1 に反するので残す)。空なら出さない。
///
/// ■ スクリプトから
///   Instantiate して Set(kind, ruleId, text, note)。床は SetArea(角のワールド座標)。
///   Follow(物体) で、再生中に物体に付いていく。
/// </summary>
[ExecuteAlways]
public class CoGroundRuleTag : MonoBehaviour
{
    [Header("ルール")]
    [SerializeField] CoGroundRuleKind kind = CoGroundRuleKind.Prohibition;
    [SerializeField] string ruleId = "N1";
    [SerializeField] string text = "Don't touch";
    [Tooltip("2 行目。After の理由など。空なら出さない")]
    [SerializeField] string note = "";
    [Tooltip("1 行目の頭に種類 (【義務】【禁止】など) を出す")]
    [SerializeField] bool showKindLabel;
    [Tooltip("配色。空なら既定 (Resources/CoGroundRuleStyle)")]
    [SerializeField] CoGroundRuleStyle style;

    [Header("床のエリア (RuleFloorArea だけ)")]
    [Tooltip("角 (一周する順。凸形)。3 つ未満なら、この GameObject を中心に Area Size の四角")]
    [SerializeField] List<Transform> areaCorners = new List<Transform>();
    [SerializeField] Vector2 areaSize = new Vector2(1f, 1f);

    [Header("再生中")]
    [Tooltip("付いていく物体 (空なら動かない)")]
    [SerializeField] Transform follow;
    [Tooltip("Facing を毎フレーム頭 (カメラ) の方へ向ける")]
    [SerializeField] bool faceCamera = true;
    [Tooltip("水平に回すだけにする (オフなら上下にも傾けて、真正面から見えるようにする)")]
    [SerializeField] bool yawOnly;

    [Header("Prefab の部品 (Prefab の中で設定済み)")]
    [SerializeField] TMP_Text titleText;
    [SerializeField] TMP_Text noteText;
    [Tooltip("Note が空のとき隠す")]
    [SerializeField] GameObject noteRoot;
    [Tooltip("種類のアイコン (配色にアイコンが無ければ隠す)")]
    [SerializeField] Image iconImage;
    [Tooltip("種類の色にする UI の板")]
    [SerializeField] Image[] colorImages = new Image[0];
    [Tooltip("種類の色にする Sprite (吹き出しの矢印)")]
    [SerializeField] SpriteRenderer[] colorSprites = new SpriteRenderer[0];
    [Tooltip("種類の色にする Renderer (床の模様・外枠)")]
    [SerializeField] Renderer[] colorRenderers = new Renderer[0];
    [Tooltip("種類の色を暗くして塗る Renderer (看板の棒)")]
    [SerializeField] Renderer[] darkRenderers = new Renderer[0];
    [Tooltip("頭の方へ向ける部分 (空なら回さない)")]
    [SerializeField] Transform facing;
    [SerializeField] MeshFilter areaFill;
    [SerializeField] LineRenderer areaOutline;
    [Tooltip("床の文字 (エリアの中心に置き直す)")]
    [SerializeField] Transform areaLabel;

    const float AreaLift = 0.004f;

    Vector3 followOffset;
    List<Vector3> areaWorldPoints; // SetArea で渡された角 (あれば areaCorners より優先)
    Mesh areaMesh;
    MaterialPropertyBlock block;

    public CoGroundRuleKind Kind => kind;
    public CoGroundRuleStyle Style { get => style != null ? style : CoGroundRuleStyle.Default; set { style = value; Apply(); } }
    public string RuleId => ruleId;

    public void Set(CoGroundRuleKind kind, string ruleId, string text, string note = "", bool showKindLabel = false)
    {
        this.kind = kind; this.ruleId = ruleId; this.text = text; this.note = note; this.showKindLabel = showKindLabel;
        Apply();
    }

    /// <summary>床のエリアの角 (ワールド座標、一周する順、凸形)。この GameObject は中心へ移る</summary>
    public void SetArea(IList<Vector3> worldPoints)
    {
        areaWorldPoints = new List<Vector3>(worldPoints);
        RebuildArea();
    }

    /// <summary>四角いエリアの大きさ (角を使わないとき)</summary>
    public void SetAreaSize(Vector2 size)
    {
        areaSize = size;
        RebuildArea();
    }

    /// <summary>全体の濃さ (1 = そのまま)。ほかの吹き出しを選んでいる間、薄くするのに使う</summary>
    public void SetOpacity(float value)
    {
        opacity = Mathf.Clamp01(value);
        foreach (var canvas in GetComponentsInChildren<Canvas>(true))
        {
            if (!canvas.isRootCanvas) continue;
            if (!canvas.TryGetComponent<CanvasGroup>(out var group)) group = canvas.gameObject.AddComponent<CanvasGroup>();
            group.alpha = opacity;
        }
        Apply();
    }
    float opacity = 1f;

    /// <summary>再生中、target に付いていく (今の位置関係を保つ)</summary>
    public void Follow(Transform target)
    {
        follow = target;
        if (target != null) followOffset = transform.position - target.position;
    }

    void OnEnable()
    {
        if (follow != null) followOffset = transform.position - follow.position;
        Apply();
        RebuildArea();
    }

    void OnDestroy() => DestroySafe(areaMesh);

#if UNITY_EDITOR
    void OnValidate()
    {
        // OnValidate の中で SetActive などをすると警告が出るので後で
        UnityEditor.EditorApplication.delayCall += () =>
        {
            if (this == null) return;
            Apply();
            RebuildArea();
        };
    }
#endif

    void LateUpdate()
    {
        if (!Application.isPlaying) return;
        if (follow != null) transform.position = follow.position + followOffset;
        if (!faceCamera || facing == null) return;
        var cam = ViewCamera();
        if (cam == null) return;
        var dir = facing.position - cam.position;
        if (yawOnly) dir.y = 0f;
        // UI は +Z 向きに見る人から読める。上はカメラの上に合わせる (頭を傾けても文字が傾かない)
        if (dir.sqrMagnitude > 1e-4f) facing.rotation = Quaternion.LookRotation(dir, yawOnly ? Vector3.up : cam.up);
    }

    static Transform cachedCamera;

    /// <summary>見ている人の頭。MainCamera のタグが無いリグ (OVRCameraRig など) でも、有効なカメラを探す</summary>
    static Transform ViewCamera()
    {
        if (cachedCamera != null && cachedCamera.gameObject.activeInHierarchy) return cachedCamera;
        var cam = Camera.main;
        if (cam == null)
            foreach (var c in Camera.allCameras)
                if (c.targetTexture == null && (cam == null || c.depth > cam.depth)) cam = c;
        cachedCamera = cam != null ? cam.transform : null;
        return cachedCamera;
    }

    string Title
    {
        get
        {
            var t = string.IsNullOrEmpty(ruleId) ? text : $"{ruleId}  {text}";
            return showKindLabel ? $"[{Style.Get(kind).label}] {t}" : t;
        }
    }

    /// <summary>色と文字を入れる</summary>
    public void Apply()
    {
        var entry = Style.Get(kind);
        var color = entry.color;
        var ink = entry.textColor;
        if (iconImage != null)
        {
            iconImage.sprite = entry.icon;
            iconImage.color = ink;
            iconImage.gameObject.SetActive(entry.icon != null);
        }
        if (titleText != null) { titleText.text = Title; titleText.color = ink; }
        if (noteText != null) { noteText.text = note; noteText.color = ink; }
        if (noteRoot != null) noteRoot.SetActive(!string.IsNullOrEmpty(note));
        foreach (var img in colorImages) if (img != null) img.color = color;
        foreach (var sr in colorSprites) if (sr != null) sr.color = new Color(color.r, color.g, color.b, color.a * opacity);
        foreach (var r in colorRenderers) Tint(r, color);
        var dark = Color.Lerp(color, Color.black, 0.3f);
        foreach (var r in darkRenderers) Tint(r, dark);
    }

    void Tint(Renderer r, Color c)
    {
        if (r == null) return;
        block ??= new MaterialPropertyBlock();
        r.GetPropertyBlock(block);
        block.SetColor("_BaseColor", c); // URP
        block.SetColor("_Color", c);     // Built-in
        r.SetPropertyBlock(block);
    }

    // ---- 床のエリア ----

    void RebuildArea()
    {
        if (areaFill == null && areaOutline == null) return;
        var pts = AreaPoints();
        if (pts.Count < 3) return;

        var center = Vector3.zero;
        float y = float.MaxValue;
        foreach (var p in pts) { center += p; y = Mathf.Min(y, p.y); }
        center /= pts.Count;
        center.y = y;
        if (areaWorldPoints != null) transform.position = center; // 角を渡されたら、この GameObject をエリアの中心へ

        var local = new Vector3[pts.Count];
        for (int i = 0; i < pts.Count; i++)
        {
            local[i] = transform.InverseTransformPoint(pts[i]);
            local[i].y = AreaLift;
        }
        var localCenter = transform.InverseTransformPoint(center);
        localCenter.y = AreaLift;

        if (areaFill != null)
        {
            // 三角形の扇 (凸形を前提)。UV はワールドの XZ で、模様の大きさをエリアによらずそろえる
            const float stripePeriod = 0.3f;
            var verts = new Vector3[pts.Count + 1];
            var uvs = new Vector2[pts.Count + 1];
            verts[0] = localCenter;
            uvs[0] = new Vector2(center.x, center.z) / stripePeriod;
            for (int i = 0; i < pts.Count; i++)
            {
                verts[i + 1] = local[i];
                uvs[i + 1] = new Vector2(pts[i].x, pts[i].z) / stripePeriod;
            }
            var tris = new List<int>();
            for (int i = 0; i < pts.Count; i++)
            {
                int a = i + 1, c = (i + 1) % pts.Count + 1;
                bool up = Vector3.Cross(verts[a] - verts[0], verts[c] - verts[0]).y > 0f; // 法線が上になる順に
                tris.AddRange(up ? new[] { 0, a, c } : new[] { 0, c, a });
            }
            if (areaMesh == null) areaMesh = new Mesh { name = "Rule Area", hideFlags = HideFlags.DontSave };
            areaMesh.Clear();
            areaMesh.vertices = verts;
            areaMesh.uv = uvs;
            areaMesh.triangles = tris.ToArray();
            areaMesh.RecalculateNormals();
            areaMesh.RecalculateBounds();
            areaFill.sharedMesh = areaMesh;
        }

        if (areaOutline != null)
        {
            areaOutline.useWorldSpace = false;
            areaOutline.loop = true;
            areaOutline.positionCount = local.Length;
            for (int i = 0; i < local.Length; i++) areaOutline.SetPosition(i, local[i] + Vector3.up * 0.002f);
        }

        if (areaLabel != null)
            areaLabel.localPosition = new Vector3(localCenter.x, areaLabel.localPosition.y, localCenter.z);
    }

    List<Vector3> AreaPoints()
    {
        if (areaWorldPoints != null && areaWorldPoints.Count >= 3) return areaWorldPoints;
        var pts = new List<Vector3>();
        foreach (var c in areaCorners) if (c != null) pts.Add(c.position);
        if (pts.Count >= 3) return pts;
        pts.Clear();
        var right = Vector3.ProjectOnPlane(transform.right, Vector3.up).normalized;
        var fwd = Vector3.ProjectOnPlane(transform.forward, Vector3.up).normalized;
        if (right.sqrMagnitude < 1e-4f) { right = Vector3.right; fwd = Vector3.forward; }
        var h = areaSize * 0.5f;
        var o = transform.position;
        pts.Add(o - right * h.x - fwd * h.y);
        pts.Add(o + right * h.x - fwd * h.y);
        pts.Add(o + right * h.x + fwd * h.y);
        pts.Add(o - right * h.x + fwd * h.y);
        return pts;
    }

    static void DestroySafe(Object o)
    {
        if (o == null) return;
        if (Application.isPlaying) Destroy(o);
        else DestroyImmediate(o);
    }
}
