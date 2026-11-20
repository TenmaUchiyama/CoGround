using Oculus.Interaction.OVR.Editor.QuickActions;
using TMPro;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.UI;

/// <summary>
/// メニュー CoGround > Speech To Text (Quest) をセットアップ
///   1. 音声入力パネル (World Space Canvas) を Prefab/UI/SpeechToTextPanel.prefab に作る
///   2. 開いているシーンに
///      ・OVRCameraRig + Interaction Rig (無ければ。元の Main Camera は無効にする) とパススルー
///      ・PushToTalkTranscriber + PushToTalkControllerInput (無ければ)
///      ・SpeechToTextPanel の Prefab (頭の前に追従)
///      を置く。
/// 何度実行してもよい (パネルは作り直し、他は足りないものだけ足す)。
///
/// バッチ実行: -executeMethod SpeechToTextPanelBuilder.BuildIntoSpeechScene
/// </summary>
public static class SpeechToTextPanelBuilder
{
    const string PrefabDir = "Assets/Main/Prefab/UI";
    const string PrefabPath = PrefabDir + "/SpeechToTextPanel.prefab";
    const string SpeechScenePath = "Assets/Main/Scene/Test/SpeechToText.unity";
    const string ConfigPath = "Assets/Main/Secrets/MaiTranscribeConfig.asset";
    const string PanelName = "SpeechToTextPanel";
    const string TranscriberName = "SpeechToText";

    // コンパクト: Canvas は 360 x 160 px、1 px = 0.5 mm → 18 cm x 8 cm
    // 目の下 ~26 cm・前 ~42 cm に、顔の方へ傾けて置く (LazyFollowHead)。視界の中心は空ける
    const float Width = 360, Height = 160, MetersPerPixel = 0.0005f;
    const float Pad = 12;

    static readonly Color PanelColor = new Color(0.09f, 0.10f, 0.12f, 0.85f);
    static readonly Color TrackColor = new Color(0.14f, 0.15f, 0.18f, 1f);
    static readonly Color DividerColor = new Color(1f, 1f, 1f, 0.08f);
    static readonly Color TitleColor = new Color(0.92f, 0.94f, 0.97f, 1f);
    static readonly Color CaptionColor = new Color(0.70f, 0.74f, 0.80f, 1f);
    static readonly Color DimColor = new Color(0.55f, 0.58f, 0.64f, 1f);

    [MenuItem("CoGround/Speech To Text (Quest) をセットアップ")]
    public static void SetupMenu()
    {
        var prefab = BuildPrefab();
        SetupScene(prefab);
        EditorSceneManager.MarkSceneDirty(EditorSceneManager.GetActiveScene());
        Debug.Log("[SpeechToTextPanelBuilder] セットアップした。シーンを保存してから Play / ビルドする");
    }

    public static void BuildIntoSpeechScene()
    {
        EditorSceneManager.OpenScene(SpeechScenePath, OpenSceneMode.Single);
        var prefab = BuildPrefab();
        SetupScene(prefab);
        var scene = EditorSceneManager.GetActiveScene();
        EditorSceneManager.MarkSceneDirty(scene);
        EditorSceneManager.SaveScene(scene);
    }

    // ---- Prefab ----

    static GameObject BuildPrefab()
    {
        if (!AssetDatabase.IsValidFolder(PrefabDir)) AssetDatabase.CreateFolder("Assets/Main/Prefab", "UI");
        var font = RuleTagPrefabBuilder.EnsureJapaneseFont();
        var rounded = AssetDatabase.GetBuiltinExtraResource<Sprite>("UI/Skin/UISprite.psd");
        var knob = AssetDatabase.GetBuiltinExtraResource<Sprite>("UI/Skin/Knob.psd");

        var root = new GameObject(PanelName, typeof(RectTransform), typeof(Canvas), typeof(CanvasScaler));
        var canvas = root.GetComponent<Canvas>();
        canvas.renderMode = RenderMode.WorldSpace;
        var rootRect = (RectTransform)root.transform;
        rootRect.sizeDelta = new Vector2(Width, Height);
        rootRect.localScale = Vector3.one * MetersPerPixel;
        root.GetComponent<CanvasScaler>().dynamicPixelsPerUnit = 3;

        var bg = MakeImage(root.transform, "Background", rounded, PanelColor);
        Stretch(bg.rectTransform, 0, 0, 0, 0);
        bg.raycastTarget = false;

        // 1 行目: ● 状態 ............ 0:03.2
        var dot = MakeImage(root.transform, "StatusDot", knob, Color.white);
        dot.type = Image.Type.Simple;
        TopLeft(dot.rectTransform, Pad, 15, 12, 12);

        var status = MakeText(root.transform, "Status", font, "待機中", 18, FontStyles.Bold, TitleColor, TextAlignmentOptions.MidlineLeft);
        TopStretch(status.rectTransform, Pad + 20, Pad + 80, 8, 26);

        var timer = MakeText(root.transform, "Timer", font, "", 16, FontStyles.Normal, CaptionColor, TextAlignmentOptions.MidlineRight);
        TopStretch(timer.rectTransform, Width - Pad - 80, Pad, 8, 26);

        // 2 行目: 波形 (細い帯)
        var track = MakeImage(root.transform, "WaveformTrack", rounded, TrackColor);
        TopStretch(track.rectTransform, Pad, Pad, 38, 30);
        var wave = new GameObject("Waveform", typeof(RectTransform));
        wave.transform.SetParent(track.transform, false);
        var waveRect = (RectTransform)wave.transform;
        Stretch(waveRect, 8, 4, 8, 4);

        // 3 行目: ヒント / 警告
        var hint = MakeText(root.transform, "Hint", font, "トリガーを押しながら話してください", 12, FontStyles.Normal, CaptionColor, TextAlignmentOptions.MidlineLeft);
        TopStretch(hint.rectTransform, Pad, Pad, 70, 18);
        hint.textWrappingMode = TextWrappingModes.NoWrap;
        hint.overflowMode = TextOverflowModes.Ellipsis;

        var divider = MakeImage(root.transform, "Divider", null, DividerColor);
        divider.type = Image.Type.Simple;
        TopStretch(divider.rectTransform, Pad, Pad, 91, 1);

        // 4 行目: 認識結果 (最大 2 行。長いと縮小→省略)
        var transcript = MakeText(root.transform, "Transcript", font, "", 18, FontStyles.Normal, TitleColor, TextAlignmentOptions.TopLeft);
        TopStretch(transcript.rectTransform, Pad, Pad, 96, Height - 96 - 8);
        transcript.enableAutoSizing = true;
        transcript.fontSizeMin = 12;
        transcript.fontSizeMax = 18;
        transcript.overflowMode = TextOverflowModes.Ellipsis;

        var panel = root.AddComponent<SpeechToTextPanel>();
        var so = new SerializedObject(panel);
        so.FindProperty("statusDot").objectReferenceValue = dot;
        so.FindProperty("statusLabel").objectReferenceValue = status;
        so.FindProperty("timerLabel").objectReferenceValue = timer;
        so.FindProperty("waveformArea").objectReferenceValue = waveRect;
        so.FindProperty("barSprite").objectReferenceValue = rounded;
        so.FindProperty("hintLabel").objectReferenceValue = hint;
        so.FindProperty("transcriptLabel").objectReferenceValue = transcript;
        so.FindProperty("historyLabel").objectReferenceValue = null; // コンパクト版は履歴・フッターなし
        so.FindProperty("footerLabel").objectReferenceValue = null;
        so.FindProperty("barCount").intValue = 40;
        so.FindProperty("barGap").floatValue = 2f;
        so.FindProperty("barMinHeight").floatValue = 2f;
        so.ApplyModifiedPropertiesWithoutUndo();

        root.AddComponent<LazyFollowHead>();

        var prefab = PrefabUtility.SaveAsPrefabAsset(root, PrefabPath);
        Object.DestroyImmediate(root);
        return prefab;
    }

    // ---- シーン ----

    static void SetupScene(GameObject prefab)
    {
        EnsureRig();
        var transcriber = EnsureTranscriber();

        var old = GameObject.Find(PanelName);
        if (old != null) Undo.DestroyObjectImmediate(old);

        var instance = (GameObject)PrefabUtility.InstantiatePrefab(prefab);
        // 実行時は LazyFollowHead が頭の下前方に置き直す。エディタ上の初期位置もそれに近づける
        instance.transform.SetPositionAndRotation(new Vector3(0f, 1.34f, 0.42f), Quaternion.Euler(32f, 0f, 0f));
        var so = new SerializedObject(instance.GetComponent<SpeechToTextPanel>());
        so.FindProperty("transcriber").objectReferenceValue = transcriber;
        so.ApplyModifiedPropertiesWithoutUndo();
        Undo.RegisterCreatedObjectUndo(instance, "Speech To Text パネル");
        Selection.activeGameObject = instance;
    }

    static void EnsureRig()
    {
        var rig = Object.FindAnyObjectByType<OVRCameraRig>();
        if (rig == null)
        {
            Camera oldCamera = FindNonXrMainCamera();
            OVRQuickActionsAPI.AddOVRInteractionRig(generateAsEditableCopy: false);
            rig = Object.FindAnyObjectByType<OVRCameraRig>();
            if (rig != null && oldCamera != null)
            {
                Undo.RecordObject(oldCamera.gameObject, "Disable Main Camera");
                oldCamera.gameObject.SetActive(false);
            }
            Debug.Log("[SpeechToTextPanelBuilder] OVRCameraRig + Interaction Rig を追加した");
        }
        if (rig == null) return;

        // パススルー (MR): OVRManager で有効化し、背景を透明にして下にカメラ映像を敷く
        var manager = rig.GetComponent<OVRManager>();
        if (manager == null) manager = Object.FindAnyObjectByType<OVRManager>();
        if (manager != null && !manager.isInsightPassthroughEnabled)
        {
            Undo.RecordObject(manager, "Enable Passthrough");
            manager.isInsightPassthroughEnabled = true;
        }
        if (Object.FindAnyObjectByType<OVRPassthroughLayer>() == null)
            Undo.AddComponent<OVRPassthroughLayer>(rig.gameObject);

        var eye = rig.centerEyeAnchor != null ? rig.centerEyeAnchor.GetComponent<Camera>() : null;
        if (eye != null)
        {
            Undo.RecordObject(eye, "Transparent background");
            eye.clearFlags = CameraClearFlags.SolidColor;
            eye.backgroundColor = new Color(0f, 0f, 0f, 0f);
        }
    }

    static PushToTalkTranscriber EnsureTranscriber()
    {
        var t = Object.FindAnyObjectByType<PushToTalkTranscriber>(FindObjectsInactive.Include);
        if (t == null)
        {
            var go = GameObject.Find(TranscriberName);
            if (go == null)
            {
                go = new GameObject(TranscriberName);
                Undo.RegisterCreatedObjectUndo(go, "Speech To Text");
            }
            t = Undo.AddComponent<PushToTalkTranscriber>(go);
        }
        if (t.GetComponent<PushToTalkControllerInput>() == null)
            Undo.AddComponent<PushToTalkControllerInput>(t.gameObject);
        // 文字起こしを B ボタンで片付けの依頼 (task.request) として送る
        if (t.GetComponent<SpeechTaskRequester>() == null)
            Undo.AddComponent<SpeechTaskRequester>(t.gameObject);

        var so = new SerializedObject(t);
        var cfg = so.FindProperty("config");
        if (cfg.objectReferenceValue == null)
        {
            cfg.objectReferenceValue = AssetDatabase.LoadAssetAtPath<MaiTranscribeConfig>(ConfigPath);
            so.ApplyModifiedProperties();
            if (cfg.objectReferenceValue == null)
                Debug.LogWarning($"[SpeechToTextPanelBuilder] {ConfigPath} が無い。Create > CoGround > MAI Transcribe Config で作るか、環境変数を使う");
        }
        return t;
    }

    static Camera FindNonXrMainCamera()
    {
        foreach (var cam in Object.FindObjectsByType<Camera>(FindObjectsSortMode.None))
            if (cam.GetComponentInParent<OVRCameraRig>() == null && cam.CompareTag("MainCamera")) return cam;
        return null;
    }

    // ---- UI ヘルパー ----

    static Image MakeImage(Transform parent, string name, Sprite sprite, Color color)
    {
        var go = new GameObject(name, typeof(RectTransform), typeof(Image));
        go.transform.SetParent(parent, false);
        var image = go.GetComponent<Image>();
        image.sprite = sprite;
        image.type = sprite != null ? Image.Type.Sliced : Image.Type.Simple;
        image.pixelsPerUnitMultiplier = 0.4f;
        image.color = color;
        image.raycastTarget = false;
        return image;
    }

    static TextMeshProUGUI MakeText(Transform parent, string name, TMP_FontAsset font, string text, float size,
        FontStyles style, Color color, TextAlignmentOptions align)
    {
        var go = new GameObject(name, typeof(RectTransform));
        go.transform.SetParent(parent, false);
        var t = go.AddComponent<TextMeshProUGUI>();
        if (font != null) t.font = font;
        t.text = text;
        t.fontSize = size;
        t.fontStyle = style;
        t.color = color;
        t.alignment = align;
        t.textWrappingMode = TextWrappingModes.Normal;
        t.richText = true;
        t.raycastTarget = false;
        return t;
    }

    /// <summary>左上から (x, y) の位置に w x h</summary>
    static void TopLeft(RectTransform rect, float x, float y, float w, float h)
    {
        rect.anchorMin = rect.anchorMax = new Vector2(0, 1);
        rect.pivot = new Vector2(0.5f, 0.5f);
        rect.sizeDelta = new Vector2(w, h);
        rect.anchoredPosition = new Vector2(x + w / 2, -(y + h / 2));
    }

    /// <summary>横は左右の余白、縦は上から top の位置に高さ h</summary>
    static void TopStretch(RectTransform rect, float left, float right, float top, float h) =>
        Anchor(rect, new Vector2(0, 1), new Vector2(1, 1), new Vector2(left, -(top + h)), new Vector2(-right, -top));

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
