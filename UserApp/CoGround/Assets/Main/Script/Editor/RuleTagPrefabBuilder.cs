using System.IO;
using TMPro;
using UnityEditor;
using UnityEngine;
using UnityEngine.TextCore.LowLevel;
using UnityEngine.UI;

/// <summary>
/// メニュー CoGround > ルール表示の Prefab を作る
/// Interaction SDK の UI Set (Tooltip / Backplate) を元に、ルール表示の Prefab を Assets/Main/Resources/RuleTag/ に作る。
///   RuleBubble.prefab     物体の上の吹き出し
///   RuleSign.prefab       置き場所の看板 (棒付き)
///   RuleFloorArea.prefab  床のエリア (模様・外枠・床の文字)
/// UI Set の中身はコピーするので、パッケージを更新しても壊れない。作った後は Prefab を開いて自由に直してよい
/// (もう一度このメニューを押すと上書きするので、手で直した後は押さないこと)。
/// 日本語用の TMP Font Asset (NotoSansJP) と、既定の配色 (Assets/Main/Resources/CoGroundRuleStyle.asset) も、無ければ作る。
/// </summary>
public static class RuleTagPrefabBuilder
{
    public const string Dir = "Assets/Main/Resources/RuleTag"; // 実行中に Resources.Load で読む
    public const string BubblePath = Dir + "/RuleBubble.prefab";
    public const string SignPath = Dir + "/RuleSign.prefab";
    public const string FloorPath = Dir + "/RuleFloorArea.prefab";
    const string MaterialDir = Dir + "/Materials";

    const string UISet = "Packages/com.meta.xr.sdk.interaction/Runtime/Sample/Objects/UISet/Prefabs/";
    const string TooltipPath = UISet + "Tooltip/Tooltip.prefab";
    const string BackplatePath = UISet + "Backplate/EmptyUIBackplateWithCanvas.prefab";
    const string FontPath = "Assets/Main/Fonts/NotoSansJP-Regular.otf";
    const string FontAssetPath = "Assets/Main/Fonts/NotoSansJP-Regular SDF.asset";

    /// <summary>UI の 1 ピクセルの大きさ (m)</summary>
    const float PixelSize = 0.0012f;
    const float BubbleWidth = 300f, SignWidth = 340f, PoleHeight = 0.35f;

    [MenuItem("CoGround/ルール表示の Prefab を作る")]
    static void BuildFromMenu()
    {
        if (Exists() && !EditorUtility.DisplayDialog("ルール表示の Prefab",
                $"{Dir} の Prefab を作り直す (手で直した所は消える)。よいか?", "作り直す", "やめる"))
            return;
        BuildAll();
    }

    public static bool Exists() =>
        AssetDatabase.LoadAssetAtPath<GameObject>(BubblePath) != null &&
        AssetDatabase.LoadAssetAtPath<GameObject>(SignPath) != null &&
        AssetDatabase.LoadAssetAtPath<GameObject>(FloorPath) != null;

    /// <summary>3 つの Prefab を作る (あれば上書き)。UI Set が無ければ false</summary>
    public static bool BuildAll()
    {
        var tooltip = AssetDatabase.LoadAssetAtPath<GameObject>(TooltipPath);
        var backplate = AssetDatabase.LoadAssetAtPath<GameObject>(BackplatePath);
        if (tooltip == null || backplate == null)
        {
            Debug.LogError($"[RuleTagPrefabBuilder] UI Set の prefab が見つからない (Meta XR Interaction SDK)\n{TooltipPath}\n{BackplatePath}");
            return false;
        }
        EnsureFolder(Dir);
        EnsureFolder(MaterialDir);
        var font = EnsureJapaneseFont();
        EnsureStyleAsset();

        Save(BuildBubble(tooltip, font), BubblePath);
        Save(BuildSign(backplate, font), SignPath);
        Save(BuildFloor(font), FloorPath);
        AssetDatabase.SaveAssets();
        Debug.Log($"[RuleTagPrefabBuilder] {Dir} に Prefab を作った");
        return true;
    }

    // ---- 吹き出し ----

    static GameObject BuildBubble(GameObject tooltipAsset, TMP_FontAsset font)
    {
        var root = new GameObject("RuleBubble");
        var so = Begin(root);

        // ルート = 矢印の先。Canvas の下端をここに合わせ、中身に合わせて上へ伸びる
        var canvas = MakeCanvas(root.transform, "Canvas", new Vector2(BubbleWidth, 10f));
        var stack = canvas.gameObject.AddComponent<VerticalLayoutGroup>();
        stack.childAlignment = TextAnchor.LowerCenter;
        stack.childControlWidth = stack.childControlHeight = true;
        stack.childForceExpandWidth = true;
        stack.childForceExpandHeight = false;
        canvas.gameObject.AddComponent<ContentSizeFitter>().verticalFit = ContentSizeFitter.FitMode.PreferredSize;

        var tip = Object.Instantiate(tooltipAsset, canvas, false);
        tip.name = "Tooltip";
        DestroyChild(tip.transform, "Elements/Space (1)");
        DestroyChild(tip.transform, "TooltipArrowUp");

        // 高さを文字に合わせる (元の Prefab は高さが固定)
        Column(tip.GetComponent<VerticalLayoutGroup>());
        var elements = tip.transform.Find("Elements");
        var row = elements.GetComponent<HorizontalLayoutGroup>();
        if (row != null) { row.childControlHeight = true; row.childForceExpandHeight = false; row.spacing = 6f; }
        var icon = elements.Find("Icon")?.GetComponent<Image>();
        if (icon != null) icon.preserveAspect = true;
        var elementsLayout = elements.GetComponent<LayoutElement>();
        if (elementsLayout != null) { elementsLayout.minHeight = 36f; elementsLayout.preferredHeight = -1f; }
        var textCol = elements.Find("Text").GetComponent<VerticalLayoutGroup>();
        Column(textCol);
        textCol.spacing = 2f;
        textCol.padding = new RectOffset(4, 4, 6, 6);

        var arrow = tip.transform.Find("TooltipArrowDown");
        arrow.gameObject.SetActive(true);
        var arrowLayout = GetOrAdd<LayoutElement>(arrow.gameObject);
        arrowLayout.minHeight = arrowLayout.preferredHeight = 10f;

        var title = elements.Find("Text/Title").GetComponent<TMP_Text>();
        var sub = elements.Find("Text/Subtitle").GetComponent<TMP_Text>();
        StyleText(title, font, 20f, true);
        StyleText(sub, font, 16f, false);

        so.FindProperty("titleText").objectReferenceValue = title;
        so.FindProperty("noteText").objectReferenceValue = sub;
        so.FindProperty("noteRoot").objectReferenceValue = sub.gameObject;
        so.FindProperty("iconImage").objectReferenceValue = icon;
        SetArray(so, "colorImages", elements.GetComponent<Image>());
        SetArray(so, "colorSprites", arrow.GetComponentsInChildren<SpriteRenderer>(true));
        so.FindProperty("facing").objectReferenceValue = root.transform;
        End(so, CoGroundRuleKind.Prohibition, "N1", "触らない", "N1 に反するので残す");
        return root;
    }

    // ---- 看板 ----

    static GameObject BuildSign(GameObject backplateAsset, TMP_FontAsset font)
    {
        var root = new GameObject("RuleSign");
        var so = Begin(root);

        // ルート = 棒の根元 (置き場所の上面に置く)
        var pole = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
        Object.DestroyImmediate(pole.GetComponent<Collider>());
        pole.name = "Pole";
        pole.transform.SetParent(root.transform, false);
        pole.transform.localPosition = new Vector3(0f, PoleHeight * 0.5f, 0f);
        pole.transform.localScale = new Vector3(0.015f, PoleHeight * 0.5f, 0.015f);
        var poleRenderer = pole.GetComponent<Renderer>();
        poleRenderer.sharedMaterial = SolidMaterial();
        poleRenderer.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;

        var board = new GameObject("Board").transform;
        board.SetParent(root.transform, false);
        board.localPosition = new Vector3(0f, PoleHeight, 0f);

        // Backplate の Canvas だけを使う (ボタン用のポーク・テーマの部品は要らない)
        var copy = Object.Instantiate(backplateAsset);
        var canvas = (RectTransform)copy.transform.Find("CanvasRoot");
        canvas.SetParent(board, false);
        Object.DestroyImmediate(copy);
        DestroyChild(canvas, "ISDK_PokeInteraction");
        canvas.name = "Canvas";
        canvas.localPosition = Vector3.zero;
        canvas.localRotation = Quaternion.identity;
        canvas.localScale = Vector3.one * PixelSize;
        canvas.pivot = new Vector2(0.5f, 0f);
        canvas.sizeDelta = new Vector2(SignWidth, 10f);
        var row = GetOrAdd<HorizontalLayoutGroup>(canvas.gameObject);
        row.padding = new RectOffset();
        row.childControlWidth = row.childControlHeight = true;
        row.childForceExpandWidth = row.childForceExpandHeight = true;
        var fit = GetOrAdd<ContentSizeFitter>(canvas.gameObject);
        fit.horizontalFit = ContentSizeFitter.FitMode.Unconstrained;
        fit.verticalFit = ContentSizeFitter.FitMode.PreferredSize;

        var plate = canvas.Find("UIBackplate");
        var col = GetOrAdd<VerticalLayoutGroup>(plate.gameObject);
        Column(col);
        col.padding = new RectOffset(18, 18, 12, 12);
        col.spacing = 4f;

        var icon = AddIcon(plate, 40f);
        var title = AddText(plate, "Title", font, 30f, true);
        var note = AddText(plate, "Note", font, 22f, false);
        so.FindProperty("iconImage").objectReferenceValue = icon;

        so.FindProperty("titleText").objectReferenceValue = title;
        so.FindProperty("noteText").objectReferenceValue = note;
        so.FindProperty("noteRoot").objectReferenceValue = note.gameObject;
        SetArray(so, "colorImages", plate.GetComponent<Image>());
        SetArray(so, "darkRenderers", poleRenderer);
        so.FindProperty("facing").objectReferenceValue = board;
        End(so, CoGroundRuleKind.Obligation, "O1", "皿はここへ", "");
        return root;
    }

    // ---- 床のエリア ----

    static GameObject BuildFloor(TMP_FontAsset font)
    {
        var root = new GameObject("RuleFloorArea");
        var so = Begin(root);

        var fill = new GameObject("Fill", typeof(MeshFilter), typeof(MeshRenderer));
        fill.transform.SetParent(root.transform, false);
        var fillRenderer = fill.GetComponent<MeshRenderer>();
        fillRenderer.sharedMaterial = FloorMaterial();
        fillRenderer.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
        fillRenderer.receiveShadows = false;

        var outline = new GameObject("Outline").AddComponent<LineRenderer>();
        outline.transform.SetParent(root.transform, false);
        outline.useWorldSpace = false;
        outline.loop = true;
        outline.startWidth = outline.endWidth = 0.02f;
        outline.numCornerVertices = 2;
        outline.alignment = LineAlignment.View;
        outline.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
        outline.receiveShadows = false;
        outline.sharedMaterial = LineMaterial();

        // 床に貼った文字 (上から読む。手前 = -Z 側から読める向き)
        var label = new GameObject("Label").transform;
        label.SetParent(root.transform, false);
        label.localPosition = new Vector3(0f, 0.007f, 0f);
        label.localRotation = Quaternion.Euler(90f, 0f, 0f);
        var canvas = MakeCanvas(label, "Canvas", new Vector2(10f, 10f));
        canvas.pivot = new Vector2(0.5f, 0.5f);
        var fit = canvas.gameObject.AddComponent<ContentSizeFitter>();
        fit.horizontalFit = fit.verticalFit = ContentSizeFitter.FitMode.PreferredSize;
        var row = canvas.gameObject.AddComponent<HorizontalLayoutGroup>();
        row.childControlWidth = row.childControlHeight = true;
        row.childForceExpandWidth = row.childForceExpandHeight = false;

        var panel = new GameObject("Panel", typeof(RectTransform), typeof(Image));
        panel.transform.SetParent(canvas, false);
        var col = panel.AddComponent<VerticalLayoutGroup>();
        Column(col);
        col.padding = new RectOffset(16, 16, 8, 8);
        col.spacing = 2f;
        var icon = AddIcon(panel.transform, 30f);
        var title = AddText(panel.transform, "Title", font, 26f, true, wrap: false);
        var note = AddText(panel.transform, "Note", font, 20f, false, wrap: false);
        so.FindProperty("iconImage").objectReferenceValue = icon;

        so.FindProperty("titleText").objectReferenceValue = title;
        so.FindProperty("noteText").objectReferenceValue = note;
        so.FindProperty("noteRoot").objectReferenceValue = note.gameObject;
        SetArray(so, "colorImages", panel.GetComponent<Image>());
        SetArray(so, "colorRenderers", fillRenderer, outline);
        so.FindProperty("areaFill").objectReferenceValue = fill.GetComponent<MeshFilter>();
        so.FindProperty("areaOutline").objectReferenceValue = outline;
        so.FindProperty("areaLabel").objectReferenceValue = label;
        so.FindProperty("facing").objectReferenceValue = null;
        End(so, CoGroundRuleKind.Prohibition, "N3", "18時以降 立入禁止", "");
        return root;
    }

    // ---- 部品 ----

    static SerializedObject Begin(GameObject root) => new SerializedObject(root.AddComponent<CoGroundRuleTag>());

    static void End(SerializedObject so, CoGroundRuleKind kind, string id, string text, string note)
    {
        so.FindProperty("kind").enumValueIndex = (int)kind;
        so.FindProperty("ruleId").stringValue = id;
        so.FindProperty("text").stringValue = text;
        so.FindProperty("note").stringValue = note;
        so.ApplyModifiedPropertiesWithoutUndo();
        ((CoGroundRuleTag)so.targetObject).Apply();
    }

    static void SetArray(SerializedObject so, string name, params Object[] values)
    {
        var p = so.FindProperty(name);
        p.arraySize = values.Length;
        for (int i = 0; i < values.Length; i++) p.GetArrayElementAtIndex(i).objectReferenceValue = values[i];
    }

    static void Save(GameObject root, string path)
    {
        PrefabUtility.SaveAsPrefabAsset(root, path);
        Object.DestroyImmediate(root);
    }

    static RectTransform MakeCanvas(Transform parent, string name, Vector2 size)
    {
        var go = new GameObject(name, typeof(RectTransform), typeof(Canvas));
        go.GetComponent<Canvas>().renderMode = RenderMode.WorldSpace;
        var rt = (RectTransform)go.transform;
        rt.SetParent(parent, false);
        rt.pivot = new Vector2(0.5f, 0f);
        rt.sizeDelta = size;
        rt.localScale = Vector3.one * PixelSize;
        return rt;
    }

    static void Column(VerticalLayoutGroup col)
    {
        if (col == null) return;
        col.childAlignment = TextAnchor.UpperCenter;
        col.childControlWidth = col.childControlHeight = true;
        col.childForceExpandWidth = true;
        col.childForceExpandHeight = false;
    }

    /// <summary>種類のアイコン (配色にアイコンが無ければ CoGroundRuleTag が隠す)</summary>
    static Image AddIcon(Transform parent, float size)
    {
        var go = new GameObject("Icon", typeof(RectTransform), typeof(Image));
        go.transform.SetParent(parent, false);
        var img = go.GetComponent<Image>();
        img.preserveAspect = true;
        img.raycastTarget = false;
        var le = go.AddComponent<LayoutElement>();
        le.minHeight = le.preferredHeight = size;
        go.SetActive(false);
        return img;
    }

    static TMP_Text AddText(Transform parent, string name, TMP_FontAsset font, float size, bool bold, bool wrap = true)
    {
        var go = new GameObject(name, typeof(RectTransform));
        go.transform.SetParent(parent, false);
        var t = go.AddComponent<TextMeshProUGUI>();
        StyleText(t, font, size, bold);
        t.textWrappingMode = wrap ? TextWrappingModes.Normal : TextWrappingModes.NoWrap;
        return t;
    }

    static void StyleText(TMP_Text t, TMP_FontAsset font, float size, bool bold)
    {
        if (font != null) t.font = font;
        t.fontSize = size;
        t.enableAutoSizing = false;
        t.fontStyle = bold ? FontStyles.Bold : FontStyles.Normal;
        t.alignment = TextAlignmentOptions.Center;
        t.textWrappingMode = TextWrappingModes.Normal;
        t.overflowMode = TextOverflowModes.Overflow;
        t.raycastTarget = false;
    }

    static T GetOrAdd<T>(GameObject go) where T : Component
    {
        var c = go.GetComponent<T>();
        return c != null ? c : go.AddComponent<T>();
    }

    static void DestroyChild(Transform root, string path)
    {
        var t = root.Find(path);
        if (t != null) Object.DestroyImmediate(t.gameObject);
    }

    static void EnsureFolder(string path)
    {
        if (AssetDatabase.IsValidFolder(path)) return;
        EnsureFolder(Path.GetDirectoryName(path).Replace('\\', '/'));
        AssetDatabase.CreateFolder(Path.GetDirectoryName(path).Replace('\\', '/'), Path.GetFileName(path));
    }

    // ---- マテリアル (色は CoGroundRuleTag が MaterialPropertyBlock で塗る) ----

    static Material SolidMaterial() => LoadOrCreate(MaterialDir + "/RuleTagSolid.mat", () =>
        new Material(Shader.Find("Universal Render Pipeline/Lit") ?? Shader.Find("Standard")));

    static Material LineMaterial() => LoadOrCreate(MaterialDir + "/RuleTagLine.mat", () =>
    {
        var m = TransparentMaterial();
        SetColor(m, Color.white);
        return m;
    });

    static Material FloorMaterial() => LoadOrCreate(MaterialDir + "/RuleTagFloor.mat", () =>
    {
        var m = TransparentMaterial();
        var stripes = StripeTexture();
        m.mainTexture = stripes;
        if (m.HasProperty("_BaseMap")) m.SetTexture("_BaseMap", stripes);
        if (m.HasProperty("_Cull")) m.SetFloat("_Cull", 0f); // 下からも見える
        SetColor(m, Color.white);
        return m;
    });

    /// <summary>FetchGhost と同じ半透明 (URP Lit Transparent) を元にする</summary>
    static Material TransparentMaterial()
    {
        var template = Resources.Load<Material>("FetchGhostURP");
        return template != null ? new Material(template) : FetchGhost.MakeMaterial(Color.white);
    }

    static void SetColor(Material m, Color c)
    {
        if (m.HasProperty("_BaseColor")) m.SetColor("_BaseColor", c);
        if (m.HasProperty("_Color")) m.SetColor("_Color", c);
    }

    static Material LoadOrCreate(string path, System.Func<Material> create)
    {
        var m = AssetDatabase.LoadAssetAtPath<Material>(path);
        if (m != null) return m;
        m = create();
        AssetDatabase.CreateAsset(m, path);
        return m;
    }

    /// <summary>白の斜線 (濃い帯と薄い帯)。色は Base Color を掛けて付ける</summary>
    static Texture2D StripeTexture()
    {
        string path = MaterialDir + "/RuleTagStripes.asset";
        var tex = AssetDatabase.LoadAssetAtPath<Texture2D>(path);
        if (tex != null) return tex;
        const int n = 64;
        tex = new Texture2D(n, n, TextureFormat.RGBA32, false) { name = "RuleTagStripes", wrapMode = TextureWrapMode.Repeat };
        var px = new Color[n * n];
        for (int y = 0; y < n; y++)
            for (int x = 0; x < n; x++)
                px[y * n + x] = new Color(1f, 1f, 1f, (x + y) % n < n / 2 ? 0.55f : 0.12f);
        tex.SetPixels(px);
        tex.Apply();
        AssetDatabase.CreateAsset(tex, path);
        return tex;
    }

    /// <summary>既定の配色アセット (Resources/CoGroundRuleStyle) が無ければ、コードの既定値で作る</summary>
    public static CoGroundRuleStyle EnsureStyleAsset()
    {
        const string path = "Assets/Main/Resources/" + CoGroundRuleStyle.ResourcePath + ".asset";
        var style = AssetDatabase.LoadAssetAtPath<CoGroundRuleStyle>(path);
        if (style != null) return style;
        EnsureFolder("Assets/Main/Resources");
        style = ScriptableObject.CreateInstance<CoGroundRuleStyle>();
        AssetDatabase.CreateAsset(style, path);
        AssetDatabase.SaveAssets();
        return style;
    }

    /// <summary>NotoSansJP から動的な TMP Font Asset を作る (使った文字だけ atlas に入る)</summary>
    public static TMP_FontAsset EnsureJapaneseFont()
    {
        var fa = AssetDatabase.LoadAssetAtPath<TMP_FontAsset>(FontAssetPath);
        if (fa != null) return fa;
        var src = AssetDatabase.LoadAssetAtPath<Font>(FontPath);
        if (src == null)
        {
            Debug.LogWarning($"[RuleTagPrefabBuilder] {FontPath} が無い。日本語が豆腐になる");
            return null;
        }
        fa = TMP_FontAsset.CreateFontAsset(src, 64, 6, GlyphRenderMode.SDFAA, 1024, 1024, AtlasPopulationMode.Dynamic, true);
        fa.name = "NotoSansJP-Regular SDF";
        AssetDatabase.CreateAsset(fa, FontAssetPath);
        foreach (var tex in fa.atlasTextures)
        {
            tex.name = fa.name + " Atlas";
            AssetDatabase.AddObjectToAsset(tex, fa);
        }
        fa.material.name = fa.name + " Material";
        AssetDatabase.AddObjectToAsset(fa.material, fa);
        AssetDatabase.SaveAssets();
        return fa;
    }
}
