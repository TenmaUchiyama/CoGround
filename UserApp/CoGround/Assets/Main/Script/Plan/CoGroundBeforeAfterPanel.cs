using System;
using Newtonsoft.Json.Linq;
using UnityEngine;
using UnityEngine.UI;
#if ENABLE_INPUT_SYSTEM
using UnityEngine.InputSystem;
#endif

/// <summary>
/// Before / After を切り替えるボタンのパネル (World Space Canvas)。
/// 押されたら CoGroundAfterView.SetMode を呼び、今のモードのボタンを強調する。
///
/// ■ 計画の再生と状態 (Show Plan Strip)
///   実行時にパネルの下に 1 段足す:
///     - 「Play plan」: 動作計画の Ghost (CoGroundTaskPlanPlayer) を再生 / 一時停止する。After を見ているときは Before に戻す
///       (After の間は Ghost を隠しているため)。最後まで再生していたら最初から
///     - 状態: 動作計画で確かめている間は「Checking if the robot can do it…」を目の前に出す (ロボットの上の吹き出しと同じ内容)。
///       実行中・計画の時刻と区切りも出す
///   パネルは LazyFollowHead で頭に付いてくるので、ロボットを見ていなくても分かる。
///
/// ■ 出すタイミング (Show Only When Ready)
///   オンなら、依頼の結果が出るまでパネルを隠す (依頼が無い間と、動作計画で確かめている間)。実行中は出す。
///   隠している間は X / Y のショートカットも効かない。確かめている途中であることは、ロボットの上の吹き出しで分かる。
///
/// ■ コントローラ (Controller Shortcuts)
///   VR ではパネルのボタンを押せないので、左手のボタンでも操作できる。
///     X = Before / After の切り替え、Y = 計画の再生 / 一時停止 (エディタでは V / P キー)
///   右手は録音 (トリガー) と依頼の送信 (B) に使っている。
///
/// ■ 使い方
///   - パネル本体は メニュー CoGround > Before・After パネルを作る で作る (Prefab/UI/BeforeAfterPanel.prefab)。
///   - afterView が空なら同じシーンから探す。無ければ見た目だけ切り替わる (UI シーンでの確認用)。
///   - インスペクタや AfterView のコンテキストメニューで切り替えた場合も、表示は追従する。
/// </summary>
public class CoGroundBeforeAfterPanel : MonoBehaviour
{
    [SerializeField] CoGroundAfterView afterView;

    [Header("UI (BeforeAfterPanelBuilder が設定する)")]
    [SerializeField] Button beforeButton;
    [SerializeField] Button afterButton;
    [SerializeField] Text beforeLabel;
    [SerializeField] Text afterLabel;
    [SerializeField] Text caption;

    [Header("色")]
    [SerializeField] Color activeColor = new Color(0.20f, 0.52f, 0.98f, 1f);
    [SerializeField] Color inactiveColor = new Color(0.22f, 0.24f, 0.28f, 1f);
    [SerializeField] Color activeTextColor = Color.white;
    [SerializeField] Color inactiveTextColor = new Color(0.72f, 0.75f, 0.80f, 1f);

    [Header("説明文")]
    [SerializeField, TextArea] string beforeCaption = "The room now";
    [SerializeField, TextArea] string afterCaption = "The room after tidying (objects that can't be tidied show the reason)";

    [Tooltip("AfterView が無いときの表示 (UI シーンでの確認用)")]
    [SerializeField] CoGroundAfterView.ViewMode previewMode = CoGroundAfterView.ViewMode.Before;

    [Header("出すタイミング")]
    [Tooltip("依頼の結果が出るまでパネルを隠す (依頼が無い間と、動作計画で確かめている間)")]
    [SerializeField] bool showOnlyWhenReady = true;

    [Header("計画の再生と状態 (実行時にパネルの下に足す)")]
    [SerializeField] bool showPlanStrip = true;
    [SerializeField] Color playColor = new Color(0.15f, 0.62f, 0.38f, 1f);
    [SerializeField] Color disabledColor = new Color(0.17f, 0.18f, 0.20f, 1f);
    [SerializeField] Color stripColor = new Color(0.14f, 0.15f, 0.18f, 1f);
    [SerializeField] Color checkingColor = new Color(1f, 0.82f, 0.3f, 1f);
    [SerializeField] Color readyColor = new Color(0.35f, 0.9f, 0.55f, 1f);
    [SerializeField] Color mutedColor = new Color(0.66f, 0.70f, 0.76f, 1f);

    [Header("コントローラ")]
    [SerializeField] bool controllerShortcuts = true;
    [Tooltip("Before / After を切り替える (既定: 左手 X)")]
    [SerializeField] OVRInput.RawButton toggleViewButton = OVRInput.RawButton.X;
    [Tooltip("計画を再生 / 一時停止する (既定: 左手 Y)")]
    [SerializeField] OVRInput.RawButton playPlanButton = OVRInput.RawButton.Y;
    [Tooltip("V / P キーでも操作する (エディタ確認用)")]
    [SerializeField] bool allowKeyboard = true;

    /// <summary>ボタンでモードが変わったとき</summary>
    public event Action<CoGroundAfterView.ViewMode> ModeChanged;

    public CoGroundAfterView.ViewMode Mode => afterView != null ? afterView.Mode : previewMode;

    CoGroundAfterView.ViewMode? shown;
    Canvas canvas;
    bool visible = true;

    // ---- 計画の再生と状態 ----
    const float StripHeight = 128f;
    bool stripBuilt;
    Button playButton;
    Image playImage;
    Text playLabel, statusLabel, detailLabel;

    void Start()
    {
        if (afterView == null) afterView = FindAnyObjectByType<CoGroundAfterView>();
        if (beforeButton != null) beforeButton.onClick.AddListener(ShowBefore);
        if (afterButton != null) afterButton.onClick.AddListener(ShowAfter);
        canvas = GetComponentInParent<Canvas>();
        BuildPlanStrip();
        Refresh();
        ApplyVisibility();
    }

    void OnDestroy()
    {
        if (beforeButton != null) beforeButton.onClick.RemoveListener(ShowBefore);
        if (afterButton != null) afterButton.onClick.RemoveListener(ShowAfter);
        if (playButton != null) playButton.onClick.RemoveListener(TogglePlanPlayback);
    }

    void Update()
    {
        ApplyVisibility();
        if (controllerShortcuts && visible)
        {
            if (OVRInput.GetDown(toggleViewButton) || (allowKeyboard && KeyDown('v'))) Toggle();
            if (OVRInput.GetDown(playPlanButton) || (allowKeyboard && KeyDown('p'))) TogglePlanPlayback();
        }
        // 他の経路 (インスペクタ・コンテキストメニュー) で切り替わったときも表示を合わせる
        if (shown != Mode) Refresh();
        RefreshStrip();
    }

    /// <summary>結果が出ているか (依頼があり、動作計画で確かめ終わった。または実行中)</summary>
    bool ResultReady()
    {
        var client = CoGroundServerClient.Instance;
        var state = client != null && client.IsConnected ? client.LatestState : null;
        if (state == null) return false;
        var mode = (string)state["execution"]?["mode"];
        if (mode == "running" || mode == "paused") return true;
        return CoGroundFuture.StageOf(state) == CoGroundFuture.Stage.Ready;
    }

    /// <summary>Canvas ごと隠す (GameObject は止めない。Update で結果を待ち続けるため)</summary>
    void ApplyVisibility()
    {
        var show = !showOnlyWhenReady || ResultReady();
        if (show == visible && (canvas == null || canvas.enabled == show)) return;
        visible = show;
        if (canvas != null) canvas.enabled = show;
    }

    void OnValidate()
    {
        if (beforeButton != null && afterButton != null) Refresh();
    }

    public void ShowBefore() => SetMode(CoGroundAfterView.ViewMode.Before);
    public void ShowAfter() => SetMode(CoGroundAfterView.ViewMode.After);
    public void Toggle() => SetMode(Mode == CoGroundAfterView.ViewMode.After ? CoGroundAfterView.ViewMode.Before : CoGroundAfterView.ViewMode.After);

    public void SetMode(CoGroundAfterView.ViewMode mode)
    {
        // このパネルの After は、最終 After (全部の step が終わった状態)。途中の時点は CoGroundSequencePanel で選ぶ
        if (afterView != null && mode == CoGroundAfterView.ViewMode.After) afterView.ShowFinal();
        else if (afterView != null) afterView.SetMode(mode);
        else previewMode = mode;
        Refresh();
        ModeChanged?.Invoke(mode);
    }

    /// <summary>計画の Ghost を再生 / 一時停止する。After を見ていたら Before に戻す (After の間は Ghost を隠すため)</summary>
    public void TogglePlanPlayback()
    {
        var player = CoGroundTaskPlanPlayer.Instance;
        if (player == null || !player.HasPlan) return;
        if (player.IsPlaying && Mode != CoGroundAfterView.ViewMode.After) { player.Pause(); return; }
        if (Mode == CoGroundAfterView.ViewMode.After) ShowBefore();
        if (player.Time >= player.Duration - 0.01f) player.Seek(0f);
        player.Play();
    }

    void Refresh()
    {
        var mode = Mode;
        shown = mode;
        var isAfter = mode == CoGroundAfterView.ViewMode.After;
        Paint(beforeButton, beforeLabel, !isAfter);
        Paint(afterButton, afterLabel, isAfter);
        if (caption != null) caption.text = isAfter ? afterCaption : beforeCaption;
    }

    void Paint(Button button, Text label, bool active)
    {
        if (button != null && button.targetGraphic != null) button.targetGraphic.color = active ? activeColor : inactiveColor;
        if (label != null) label.color = active ? activeTextColor : inactiveTextColor;
    }

    // ------------------------------------------------------------------ 計画の再生と状態

    /// <summary>パネルを下に伸ばし、再生ボタンと状態の行を足す (Prefab はそのまま)</summary>
    void BuildPlanStrip()
    {
        if (!showPlanStrip || stripBuilt || caption == null || beforeButton == null) return;
        var segment = beforeButton.transform.parent as RectTransform;
        if (segment == null) return;
        stripBuilt = true;

        // 下に StripHeight だけ伸ばし、下に付いていた説明文と Before / After の帯を上にずらす
        var root = (RectTransform)transform;
        root.sizeDelta += new Vector2(0f, StripHeight);
        var up = new Vector2(0f, StripHeight);
        caption.rectTransform.offsetMin += up;
        caption.rectTransform.offsetMax += up;
        segment.offsetMin += up;

        var sprite = (beforeButton.targetGraphic as Image)?.sprite;
        var font = caption.font;

        var strip = MakeImage(transform, "PlanStrip", sprite, stripColor);
        Anchor(strip.rectTransform, new Vector2(0, 0), new Vector2(1, 0), new Vector2(24, 14), new Vector2(-24, StripHeight - 4));

        playImage = MakeImage(strip.transform, "PlayPlanButton", sprite, playColor);
        Anchor(playImage.rectTransform, new Vector2(0, 0), new Vector2(0, 1), new Vector2(8, 8), new Vector2(200, -8));
        playButton = playImage.gameObject.AddComponent<Button>();
        playButton.targetGraphic = playImage;
        var colors = playButton.colors; // 色はここで塗る。ボタンは押したときの明暗だけ
        colors.normalColor = Color.white;
        colors.highlightedColor = new Color(1.15f, 1.15f, 1.15f, 1f);
        colors.pressedColor = new Color(0.8f, 0.8f, 0.8f, 1f);
        colors.selectedColor = Color.white;
        colors.disabledColor = Color.white;
        playButton.colors = colors;
        playButton.onClick.AddListener(TogglePlanPlayback);
        playLabel = MakeLabel(playImage.transform, "Label", font, 28, FontStyle.Bold, Color.white, TextAnchor.MiddleCenter);
        Anchor(playLabel.rectTransform, Vector2.zero, Vector2.one, Vector2.zero, Vector2.zero);

        statusLabel = MakeLabel(strip.transform, "Status", font, 23, FontStyle.Bold, mutedColor, TextAnchor.MiddleLeft);
        Anchor(statusLabel.rectTransform, new Vector2(0, 0.45f), new Vector2(1, 1), new Vector2(214, 0), new Vector2(-12, -6));
        detailLabel = MakeLabel(strip.transform, "Detail", font, 19, FontStyle.Normal, mutedColor, TextAnchor.MiddleLeft);
        Anchor(detailLabel.rectTransform, new Vector2(0, 0), new Vector2(1, 0.45f), new Vector2(214, 6), new Vector2(-12, 0));
    }

    string lastStatus, lastDetail, lastPlay;

    void RefreshStrip()
    {
        if (!stripBuilt) return;
        var player = CoGroundTaskPlanPlayer.Instance;
        var hasPlan = player != null && player.HasPlan;
        var playing = hasPlan && player.IsPlaying && Mode != CoGroundAfterView.ViewMode.After;

        // ---- 再生ボタン ----
        var playText = playing ? "Pause\n<size=18>(Y)</size>" : "Play plan\n<size=18>(Y)</size>";
        if (playText != lastPlay) { lastPlay = playText; playLabel.text = playText; }
        playButton.interactable = hasPlan;
        playImage.color = !hasPlan ? disabledColor : playing ? inactiveColor : playColor;
        playLabel.color = hasPlan ? Color.white : mutedColor;

        // ---- 状態 ----
        Status(out var status, out var color);
        var detail = "";
        if (hasPlan)
        {
            var phase = player.CurrentPhase;
            var phaseText = phase == null ? "" : "   " + phase.StepId + ": " +
                            (CoGroundTaskPlanPlayer.PhaseLabel.TryGetValue(phase.Name, out var l) ? l : phase.Name);
            detail = $"{player.Time:F1} / {player.Duration:F1} s{phaseText}";
        }
        detail += (detail == "" ? "" : "   ·   ") + "X: Before / After";
        if (status != lastStatus) { lastStatus = status; statusLabel.text = status; }
        statusLabel.color = color;
        if (detail != lastDetail) { lastDetail = detail; detailLabel.text = detail; }
    }

    /// <summary>目の前に出す状態の 1 行 (ロボットの上の「確認中」と同じ判定: CoGroundFuture.StageOf)</summary>
    void Status(out string text, out Color color)
    {
        color = mutedColor;
        var client = CoGroundServerClient.Instance;
        var state = client != null ? client.LatestState : null;
        if (client == null || !client.IsConnected) { text = "Not connected to the server"; return; }
        if (state == null) { text = "Waiting for the server…"; return; }

        var execution = state["execution"] as JObject;
        var mode = (string)execution?["mode"];
        if (mode == "running")
        {
            var current = execution["current"] as JObject;
            text = current != null ? $"Executing: {current["skill"]} {current["object_id"]}" : "Executing…";
            color = activeColor;
            return;
        }
        if (mode == "paused") { text = "Stopped: " + (string)execution["reason"]; color = checkingColor; return; }

        switch (CoGroundFuture.StageOf(state))
        {
            case CoGroundFuture.Stage.NoRequest:
                text = "No request yet. Hold the trigger and speak.";
                return;
            case CoGroundFuture.Stage.Checking:
                var progress = (string)state["motion"]?["progress"];
                var dots = new string('.', 1 + (int)(Time.time * 2f) % 3);
                text = "Checking if the robot can do it" + dots + (string.IsNullOrEmpty(progress) ? "" : "  " + progress);
                color = checkingColor;
                return;
            default:
                var player = CoGroundTaskPlanPlayer.Instance;
                text = player != null && player.HasPlan ? "Plan ready. Play it, or compare Before / After." : "Checked.";
                color = readyColor;
                return;
        }
    }

    static bool KeyDown(char key)
    {
#if ENABLE_INPUT_SYSTEM
        var k = Keyboard.current;
        if (k == null) return false;
        return key == 'v' ? k.vKey.wasPressedThisFrame : key == 'p' && k.pKey.wasPressedThisFrame;
#else
        return Input.GetKeyDown(key == 'v' ? KeyCode.V : KeyCode.P);
#endif
    }

    // ------------------------------------------------------------------ UI の部品 (BeforeAfterPanelBuilder と同じ作り)

    static Image MakeImage(Transform parent, string name, Sprite sprite, Color color)
    {
        var go = new GameObject(name, typeof(RectTransform), typeof(Image));
        go.transform.SetParent(parent, false);
        var image = go.GetComponent<Image>();
        image.sprite = sprite;
        image.type = sprite != null ? Image.Type.Sliced : Image.Type.Simple;
        image.pixelsPerUnitMultiplier = 0.4f;
        image.color = color;
        return image;
    }

    static Text MakeLabel(Transform parent, string name, Font font, int size, FontStyle style, Color color, TextAnchor align)
    {
        var go = new GameObject(name, typeof(RectTransform), typeof(Text));
        go.transform.SetParent(parent, false);
        var label = go.GetComponent<Text>();
        label.font = font != null ? font : Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
        label.fontSize = size;
        label.fontStyle = style;
        label.color = color;
        label.alignment = align;
        label.supportRichText = true;
        label.lineSpacing = 0.9f;
        label.horizontalOverflow = HorizontalWrapMode.Wrap;
        label.verticalOverflow = VerticalWrapMode.Overflow;
        label.raycastTarget = false;
        return label;
    }

    static void Anchor(RectTransform rect, Vector2 anchorMin, Vector2 anchorMax, Vector2 offsetMin, Vector2 offsetMax)
    {
        rect.anchorMin = anchorMin;
        rect.anchorMax = anchorMax;
        rect.offsetMin = offsetMin;
        rect.offsetMax = offsetMax;
    }
}
