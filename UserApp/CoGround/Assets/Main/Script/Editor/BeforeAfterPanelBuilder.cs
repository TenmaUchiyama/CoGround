using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.UI;

/// <summary>
/// メニュー CoGround > Before・After パネルを作る
/// Before / After 切り替えパネル (World Space Canvas) を Prefab/UI/BeforeAfterPanel.prefab に作り、
/// 開いているシーンの Main Camera の正面に置く。マウスで押せるよう EventSystem も足す。
///
/// RoboSim に入れるときは Prefab を置き、Canvas に ISDK の Ray / Poke を付ける。
/// バッチ実行: -executeMethod BeforeAfterPanelBuilder.BuildIntoUIScene (UI.unity を開いて置き、保存する)
/// </summary>
public static class BeforeAfterPanelBuilder
{
    const string PrefabDir = "Assets/Main/Prefab/UI";
    const string PrefabPath = PrefabDir + "/BeforeAfterPanel.prefab";
    const string FontPath = "Assets/Main/Fonts/NotoSansJP-Regular.otf";
    const string UIScenePath = "Assets/Main/Scene/UI.unity";
    const string PanelName = "BeforeAfterPanel";

    // Canvas は 640 x 300 px、1 px = 0.5 mm → 32 cm x 15 cm
    const float Width = 640, Height = 300, MetersPerPixel = 0.0005f;

    static readonly Color PanelColor = new Color(0.09f, 0.10f, 0.12f, 0.92f);
    static readonly Color TrackColor = new Color(0.14f, 0.15f, 0.18f, 1f);
    static readonly Color TitleColor = new Color(0.92f, 0.94f, 0.97f, 1f);
    static readonly Color CaptionColor = new Color(0.70f, 0.74f, 0.80f, 1f);

    [MenuItem("CoGround/Before・After パネルを作る")]
    public static void BuildMenu()
    {
        var prefab = BuildPrefab();
        PlaceInScene(prefab);
        EditorSceneManager.MarkSceneDirty(EditorSceneManager.GetActiveScene());
    }

    public static void BuildIntoUIScene()
    {
        EditorSceneManager.OpenScene(UIScenePath, OpenSceneMode.Single);
        var prefab = BuildPrefab();
        PlaceInScene(prefab);
        var scene = EditorSceneManager.GetActiveScene();
        EditorSceneManager.MarkSceneDirty(scene);
        EditorSceneManager.SaveScene(scene);
        Debug.Log($"[BeforeAfterPanelBuilder] {PrefabPath} を作り {UIScenePath} に置いた");
    }

    static GameObject BuildPrefab()
    {
        if (!AssetDatabase.IsValidFolder(PrefabDir)) AssetDatabase.CreateFolder("Assets/Main/Prefab", "UI");
        var font = AssetDatabase.LoadAssetAtPath<Font>(FontPath);
        if (font == null) font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
        var rounded = AssetDatabase.GetBuiltinExtraResource<Sprite>("UI/Skin/UISprite.psd");

        // Canvas
        var root = new GameObject(PanelName, typeof(RectTransform), typeof(Canvas), typeof(CanvasScaler), typeof(GraphicRaycaster));
        var canvas = root.GetComponent<Canvas>();
        canvas.renderMode = RenderMode.WorldSpace;
        var rootRect = (RectTransform)root.transform;
        rootRect.sizeDelta = new Vector2(Width, Height);
        rootRect.localScale = Vector3.one * MetersPerPixel;
        root.GetComponent<CanvasScaler>().dynamicPixelsPerUnit = 3; // 文字をくっきり

        var bg = MakeImage(root.transform, "Background", rounded, PanelColor);
        Stretch(bg.rectTransform, 0, 0, 0, 0);

        var title = MakeLabel(root.transform, "Title", font, "表示の切り替え", 30, FontStyle.Bold, TitleColor, TextAnchor.MiddleLeft);
        Anchor(title.rectTransform, new Vector2(0, 1), new Vector2(1, 1), new Vector2(28, -70), new Vector2(-28, -18));

        // 2 つのボタンを並べる (セグメント)
        var track = MakeImage(root.transform, "Segment", rounded, TrackColor);
        Anchor(track.rectTransform, new Vector2(0, 0), new Vector2(1, 1), new Vector2(24, 76), new Vector2(-24, -80));

        var beforeButton = SegmentButton(track.transform, "BeforeButton", rounded, font, "Before\n<size=24>いま</size>", 0f, 0.5f, out var beforeLabel);
        var afterButton = SegmentButton(track.transform, "AfterButton", rounded, font, "After\n<size=24>片付け後</size>", 0.5f, 1f, out var afterLabel);

        var caption = MakeLabel(root.transform, "Caption", font, "いまの部屋", 24, FontStyle.Normal, CaptionColor, TextAnchor.MiddleLeft);
        Anchor(caption.rectTransform, new Vector2(0, 0), new Vector2(1, 0), new Vector2(28, 16), new Vector2(-28, 68));

        var panel = root.AddComponent<CoGroundBeforeAfterPanel>();
        var so = new SerializedObject(panel);
        so.FindProperty("beforeButton").objectReferenceValue = beforeButton;
        so.FindProperty("afterButton").objectReferenceValue = afterButton;
        so.FindProperty("beforeLabel").objectReferenceValue = beforeLabel;
        so.FindProperty("afterLabel").objectReferenceValue = afterLabel;
        so.FindProperty("caption").objectReferenceValue = caption;
        so.ApplyModifiedPropertiesWithoutUndo();

        var prefab = PrefabUtility.SaveAsPrefabAsset(root, PrefabPath);
        Object.DestroyImmediate(root);
        return prefab;
    }

    static void PlaceInScene(GameObject prefab)
    {
        var old = GameObject.Find(PanelName);
        if (old != null) Object.DestroyImmediate(old);

        var instance = (GameObject)PrefabUtility.InstantiatePrefab(prefab);
        var cam = Camera.main;
        if (cam != null)
        {
            // カメラの 0.6 m 前、カメラの方を向ける (Canvas の表は -Z 側から見える)
            var forward = Vector3.ProjectOnPlane(cam.transform.forward, Vector3.up).normalized;
            if (forward.sqrMagnitude < 0.01f) forward = Vector3.forward;
            instance.transform.position = cam.transform.position + forward * 0.6f;
            instance.transform.rotation = Quaternion.LookRotation(forward, Vector3.up);
        }
        Undo.RegisterCreatedObjectUndo(instance, "Before・After パネル");
        Selection.activeGameObject = instance;

        if (Object.FindAnyObjectByType<EventSystem>() == null)
        {
            var es = new GameObject("EventSystem", typeof(EventSystem), typeof(StandaloneInputModule));
            Undo.RegisterCreatedObjectUndo(es, "EventSystem");
        }
    }

    static Button SegmentButton(Transform parent, string name, Sprite sprite, Font font, string text, float xMin, float xMax, out Text label)
    {
        var image = MakeImage(parent, name, sprite, Color.white);
        Anchor(image.rectTransform, new Vector2(xMin, 0), new Vector2(xMax, 1), new Vector2(6, 6), new Vector2(-6, -6));
        var button = image.gameObject.AddComponent<Button>();
        button.targetGraphic = image;
        var colors = button.colors; // 色は CoGroundBeforeAfterPanel が塗る。ここは押したときの明暗だけ
        colors.normalColor = Color.white;
        colors.highlightedColor = new Color(1.15f, 1.15f, 1.15f, 1f);
        colors.pressedColor = new Color(0.8f, 0.8f, 0.8f, 1f);
        colors.selectedColor = Color.white;
        colors.colorMultiplier = 1.2f;
        button.colors = colors;

        label = MakeLabel(image.transform, "Label", font, text, 40, FontStyle.Bold, Color.white, TextAnchor.MiddleCenter);
        Stretch(label.rectTransform, 0, 0, 0, 0);
        label.lineSpacing = 0.9f;
        label.raycastTarget = false;
        return button;
    }

    static Image MakeImage(Transform parent, string name, Sprite sprite, Color color)
    {
        var go = new GameObject(name, typeof(RectTransform), typeof(Image));
        go.transform.SetParent(parent, false);
        var image = go.GetComponent<Image>();
        image.sprite = sprite;
        image.type = UnityEngine.UI.Image.Type.Sliced;
        image.pixelsPerUnitMultiplier = 0.4f; // 角を大きめに丸める
        image.color = color;
        return image;
    }

    static Text MakeLabel(Transform parent, string name, Font font, string text, int size, FontStyle style, Color color, TextAnchor align)
    {
        var go = new GameObject(name, typeof(RectTransform), typeof(Text));
        go.transform.SetParent(parent, false);
        var label = go.GetComponent<Text>();
        label.font = font;
        label.text = text;
        label.fontSize = size;
        label.fontStyle = style;
        label.color = color;
        label.alignment = align;
        label.supportRichText = true;
        label.horizontalOverflow = HorizontalWrapMode.Wrap;
        label.verticalOverflow = VerticalWrapMode.Overflow;
        label.raycastTarget = false;
        return label;
    }

    static void Stretch(RectTransform rect, float left, float bottom, float right, float top) =>
        Anchor(rect, Vector2.zero, Vector2.one, new Vector2(left, bottom), new Vector2(-right, -top));

    static void Anchor(RectTransform rect, Vector2 anchorMin, Vector2 anchorMax, Vector2 offsetMin, Vector2 offsetMax)
    {
        rect.anchorMin = anchorMin;
        rect.anchorMax = anchorMax;
        rect.offsetMin = offsetMin;
        rect.offsetMax = offsetMax;
    }
}
