using System.Collections.Generic;
using UnityEngine;

/// <summary>
/// Diminished Reality のお試し: 右コントローラの先にマスクの箱を付けて、箱の中だけ背景のスキャン (LivingModel など) を見せる。
/// 箱を物にかぶせると、その物が消えたように見える (スキャンが現実に合っていれば)。
///
/// ■ 背景
///   Background の下の Renderer のマテリアルを、DR 用のマテリアルに差し替える。
///   - メッシュ: Background DR Material (DR/StencilReadTextured)
///   - スプラット (SplatXR/SplatShader): 元のマテリアルを複製して、シェーダーだけ DR/StencilReadSplat にしたもの
///   Background の下にスプラットがあるときは、スプラットだけで DR をする。
///   メッシュはスキャンを動かしているあいだだけ出す (位置合わせ用。それ以外で出すとパススルーを覆ってしまう)。
///   DR を切ったとき・SplatOffsetPlacer でスキャンを動かしているあいだは、元のマテリアルに戻して全体を見せる (位置合わせ用)。
///   スプラットは、DR を切ったときは出さない (パススルーだけになる)。
///
/// ■ 操作 (右コントローラ)
///   右スティック押し込み … DR の ON / OFF
///   (箱の大きさと位置は Inspector の Box Size / Box Offset)
///
/// ■ 見た目
///   マスクの箱は色を描かないので、Show Outline が ON のときは箱の枠を線で描く。
/// </summary>
public class DRHandMask : MonoBehaviour
{
    [Header("背景")]
    [Tooltip("背景のスキャン (この下の Renderer を全部使う)")]
    [SerializeField] Transform background;
    [Tooltip("DR 用のマテリアル (Shader: DR/StencilReadTextured、Texture: スキャンのテクスチャ)")]
    [SerializeField] Material backgroundDrMaterial;
    [Tooltip("スキャンを動かしているあいだは DR を止めて、全体を見せる")]
    [SerializeField] SplatOffsetPlacer splatPlacer;
    [Tooltip("スプラットの DR 用シェーダー (DR/StencilReadSplat)。ビルドに入れるためにここで参照する。空なら Shader.Find")]
    [SerializeField] Shader splatDrShader;

    [Header("スプラットの DR (背景がスプラットのとき)")]
    [Tooltip("箱の輪郭に近いほど透明にしてパススルーと混ぜる幅 [m]。0 でくっきり切れる")]
    [SerializeField, Range(0f, 0.2f)] float splatFeatherWidth = 0.03f;
    [Tooltip("毎フレーム変わるざらつき (パススルーのノイズに合わせる)")]
    [SerializeField, Range(0f, 0.2f)] float splatGrain = 0.03f;
    [Tooltip("ON: スキャンが薄い所でも実物を透けさせない (薄い所は少し暗くなる)")]
    [SerializeField] bool splatNoSeeThrough;

    [Header("マスクの箱")]
    [Tooltip("未設定なら OVRCameraRig の右コントローラのアンカー")]
    [SerializeField] Transform rightController;
    [Tooltip("箱の大きさ (左右, 高さ, 前後) [m]")]
    [SerializeField] Vector3 boxSize = new Vector3(0.25f, 0.25f, 0.25f);
    [Tooltip("箱の中心 (コントローラから見た位置) [m]")]
    [SerializeField] Vector3 boxOffset = new Vector3(0f, 0f, 0.2f);
    [Tooltip("空なら Resources の DR_StencilMask シェーダーから作る")]
    [SerializeField] Material maskMaterial;
    [SerializeField] bool drOn = true;

    [Header("見た目")]
    [SerializeField] bool showOutline = true;
    [SerializeField] Color outlineColor = new Color(0.2f, 1f, 0.6f, 0.8f);
    [SerializeField] float outlineWidth = 0.003f;

    const OVRInput.Controller Right = OVRInput.Controller.RTouch;

    Transform root;     // 箱の中心 (スケール 1)
    Transform cube;     // マスク (スケール = 大きさ)
    LineRenderer outline;
    Material createdMaskMaterial;
    Material outlineMaterial;

    const string SplatShaderName = "SplatXR/SplatShader";

    // alignOnly: スプラットがあるときのメッシュ。DR には使わず、スキャンを動かしているあいだだけ出す
    readonly List<(Renderer renderer, Material[] original, Material[] dr, bool enabled, bool splat, bool alignOnly)> backgrounds = new();
    readonly List<Material> createdSplatMaterials = new();
    bool showingDr;
    bool started;

    void Start()
    {
        if (rightController == null)
        {
            var rig = FindAnyObjectByType<OVRCameraRig>();
            if (rig != null) rightController = rig.rightControllerAnchor;
        }
        if (rightController == null)
        {
            Debug.LogError("[DRHandMask] 右コントローラのアンカーが見つからない。Right Controller を設定すること", this);
            enabled = false;
            return;
        }

        BuildBox();
        CollectBackground();
        started = true;
        Apply(force: true);
        Debug.Log($"[DRHandMask] 準備できた (背景の Renderer {backgrounds.Count} 個。右スティック押し込み: DR の ON / OFF)", this);
    }

    void Update()
    {
        if (OVRInput.GetDown(OVRInput.Button.PrimaryThumbstick, Right))
        {
            drOn = !drOn;
            Debug.Log($"[DRHandMask] DR {(drOn ? "ON" : "OFF")}", this);
        }
        Apply(force: false);
    }

    void OnValidate()
    {
        if (!started) return;
        ApplyBoxShape();
        foreach (var m in createdSplatMaterials) if (m != null) ApplySplatDrSettings(m);
    }

    // ---- マスクの箱 ----

    void BuildBox()
    {
        root = new GameObject("DR Hand Mask Box").transform;
        root.SetParent(rightController, false);

        if (maskMaterial == null)
        {
            var shader = Resources.Load<Shader>("DR_StencilMask");
            if (shader == null) Debug.LogError("[DRHandMask] Resources に DR_StencilMask シェーダーが無い", this);
            else maskMaterial = createdMaskMaterial = new Material(shader);
        }

        var go = GameObject.CreatePrimitive(PrimitiveType.Cube);
        go.name = "mask";
        Destroy(go.GetComponent<Collider>()); // 検出やほかのレイに当たらないように
        cube = go.transform;
        cube.SetParent(root, false);
        var r = go.GetComponent<MeshRenderer>();
        r.sharedMaterial = maskMaterial;
        r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
        r.receiveShadows = false;
        go.AddComponent<DRMaskShaderGlobals>(); // 縁をぼかすために箱の位置をシェーダーへ渡す

        outline = root.gameObject.AddComponent<LineRenderer>();
        outline.useWorldSpace = false;
        outline.loop = false;
        outline.widthMultiplier = outlineWidth;
        outlineMaterial = FetchGhost.MakeMaterial(outlineColor);
        outline.sharedMaterial = outlineMaterial;
        outline.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
        outline.receiveShadows = false;

        ApplyBoxShape();
    }

    void ApplyBoxShape()
    {
        if (root == null) return;
        root.localPosition = boxOffset;
        cube.localScale = boxSize;

        // 12 本の辺を 1 本の線でなぞる (下の 4 点 0-3、上の 4 点 4-7)
        var h = boxSize / 2f;
        var c = new[]
        {
            new Vector3(-h.x, -h.y, -h.z), new Vector3(h.x, -h.y, -h.z), new Vector3(h.x, -h.y, h.z), new Vector3(-h.x, -h.y, h.z),
            new Vector3(-h.x,  h.y, -h.z), new Vector3(h.x,  h.y, -h.z), new Vector3(h.x,  h.y, h.z), new Vector3(-h.x,  h.y, h.z),
        };
        int[] path = { 0, 1, 2, 3, 0, 4, 5, 1, 5, 6, 2, 6, 7, 3, 7, 4 };
        outline.positionCount = path.Length;
        for (int i = 0; i < path.Length; i++) outline.SetPosition(i, c[path[i]]);
        outline.widthMultiplier = outlineWidth;
        if (outlineMaterial != null) outlineMaterial.color = outlineColor;
    }

    // ---- 背景 ----

    void CollectBackground()
    {
        if (background == null)
        {
            Debug.LogWarning("[DRHandMask] Background が未設定。箱の中に何も出ない", this);
            return;
        }
        var renderers = background.GetComponentsInChildren<Renderer>(true);
        bool hasSplat = false;
        foreach (var r in renderers) hasSplat |= IsSplat(r);
        if (hasSplat && splatDrShader == null) splatDrShader = Shader.Find("DR/StencilReadSplat");
        if (hasSplat && splatDrShader == null)
        {
            Debug.LogError("[DRHandMask] シェーダー DR/StencilReadSplat が見つからない。Splat Dr Shader を設定すること", this);
            hasSplat = false;
        }
        if (!hasSplat && backgroundDrMaterial == null)
        {
            Debug.LogWarning("[DRHandMask] Background DR Material が未設定。背景のマテリアルをそのまま使う (DR/StencilReadTextured になっていなければ全体が見える)", this);
        }

        foreach (var r in renderers)
        {
            bool splat = hasSplat && IsSplat(r);
            var original = r.sharedMaterials;
            if (hasSplat && !splat)
            {
                backgrounds.Add((r, original, original, r.enabled, false, true));
                continue;
            }

            var dr = new Material[original.Length];
            for (int i = 0; i < dr.Length; i++)
            {
                if (splat && original[i] != null)
                {
                    // 元のマテリアルの値 (大きさ、色の調整) をそのまま使う
                    var m = new Material(original[i]) { name = original[i].name + " (DR)", shader = splatDrShader };
                    m.renderQueue = original[i].renderQueue;
                    ApplySplatDrSettings(m);
                    createdSplatMaterials.Add(m);
                    dr[i] = m;
                }
                else if (splat) dr[i] = null;
                else dr[i] = backgroundDrMaterial != null ? backgroundDrMaterial : original[i];
            }
            backgrounds.Add((r, original, dr, r.enabled, splat, false));
        }
        // 位置合わせ用のスキャンのメッシュ (Aligner の Source) が背景の外にあるときも、DR の間は隠す
        var scan = splatPlacer != null && splatPlacer.Aligner != null ? splatPlacer.Aligner.Source : null;
        if (hasSplat && scan != null && !scan.IsChildOf(background))
        {
            foreach (var r in scan.GetComponentsInChildren<Renderer>(true))
                backgrounds.Add((r, r.sharedMaterials, r.sharedMaterials, r.enabled, false, true));
        }
        Debug.Log($"[DRHandMask] 背景: {(hasSplat ? "スプラット" : "メッシュ")}", this);
    }

    /// <summary>DR/StencilReadSplat だけにある値 (元の SplatXR のマテリアルには無い)</summary>
    void ApplySplatDrSettings(Material m)
    {
        m.SetInt("_StencilRef", 1);
        m.SetFloat("_FeatherWidth", splatFeatherWidth);
        m.SetFloat("_Grain", splatGrain);
        m.SetFloat("_AlphaDstBlend", (float)(splatNoSeeThrough
            ? UnityEngine.Rendering.BlendMode.One
            : UnityEngine.Rendering.BlendMode.OneMinusSrcAlpha));
    }

    static bool IsSplat(Renderer r)
    {
        foreach (var m in r.sharedMaterials)
            if (m != null && m.shader != null && m.shader.name == SplatShaderName) return true;
        return false;
    }

    void Apply(bool force)
    {
        bool aligning = splatPlacer != null && splatPlacer.IsSplatMode;
        bool dr = drOn && !aligning;

        if (root != null)
        {
            cube.gameObject.SetActive(dr);
            outline.enabled = showOutline && dr;
        }
        // 元のスプラットのマテリアル (色の調整) を変えたら、すぐ DR 用にも入れる (Play 中に色を合わせるため)
        if (dr) SyncSplatMaterials();

        // SplatXR の LoD レンダラーは自分の Start でマテリアルを付け直すので、ずれていたら付け直す
        if (!force && dr == showingDr && !SplatMaterialChanged(dr)) return;
        showingDr = dr;

        // DR のとき: DR 用のマテリアルで描く (箱の中だけ見える)。
        // DR でないとき: 元のマテリアルで全体を見せる。スプラットがあって元から隠していた Renderer は、スキャンを動かすときだけ出す。
        foreach (var (r, original, drMaterials, wasEnabled, splat, alignOnly) in backgrounds)
        {
            if (r == null) continue;
            if (alignOnly)
            {
                r.sharedMaterials = original;
                r.enabled = aligning;
                continue;
            }
            r.sharedMaterials = dr ? drMaterials : original;
            r.enabled = splat ? dr || aligning : dr || wasEnabled || aligning;
        }
    }

    /// <summary>元のスプラットのマテリアルの値を DR 用の複製に入れる (DR だけの値は DRHandMask の設定で上書き)</summary>
    void SyncSplatMaterials()
    {
        foreach (var (_, original, drMaterials, _, splat, _) in backgrounds)
        {
            if (!splat) continue;
            for (int i = 0; i < drMaterials.Length; i++)
            {
                if (drMaterials[i] == null || original[i] == null) continue;
                int queue = drMaterials[i].renderQueue;
                drMaterials[i].CopyPropertiesFromMaterial(original[i]);
                ApplySplatDrSettings(drMaterials[i]);
                drMaterials[i].renderQueue = queue;
            }
        }
    }

    bool SplatMaterialChanged(bool dr)
    {
        foreach (var (r, original, drMaterials, _, splat, _) in backgrounds)
        {
            if (!splat || r == null) continue;
            var expected = dr ? drMaterials : original;
            if (expected.Length > 0 && r.sharedMaterial != expected[0]) return true;
        }
        return false;
    }

    void OnDestroy()
    {
        foreach (var (r, original, _, wasEnabled, _, _) in backgrounds)
        {
            if (r == null) continue;
            r.sharedMaterials = original;
            r.enabled = wasEnabled;
        }
        foreach (var m in createdSplatMaterials) if (m != null) Destroy(m);
        if (createdMaskMaterial != null) Destroy(createdMaskMaterial);
        if (outlineMaterial != null) Destroy(outlineMaterial);
        if (root != null) Destroy(root.gameObject);
    }
}
