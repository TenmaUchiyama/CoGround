using System;
using UnityEngine;
using UnityEngine.UI;

/// <summary>
/// Before / After を切り替えるボタンのパネル (World Space Canvas)。
/// 押されたら CoGroundAfterView.SetMode を呼び、今のモードのボタンを強調する。
///
/// ■ 使い方
///   - パネル本体は メニュー CoGround > Before・After パネルを作る で作る (Prefab/UI/BeforeAfterPanel.prefab)。
///   - afterView が空なら同じシーンから探す。無ければ見た目だけ切り替わる (UI シーンでの確認用)。
///   - VR (RoboSim) で押すには、Canvas に ISDK の Ray / Poke を付ける
///     (Hierarchy で Canvas を右クリック > Interaction SDK > Add Ray Interaction to Canvas など)。
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

    /// <summary>ボタンでモードが変わったとき</summary>
    public event Action<CoGroundAfterView.ViewMode> ModeChanged;

    public CoGroundAfterView.ViewMode Mode => afterView != null ? afterView.Mode : previewMode;

    CoGroundAfterView.ViewMode? shown;

    void Start()
    {
        if (afterView == null) afterView = FindAnyObjectByType<CoGroundAfterView>();
        if (beforeButton != null) beforeButton.onClick.AddListener(ShowBefore);
        if (afterButton != null) afterButton.onClick.AddListener(ShowAfter);
        Refresh();
    }

    void OnDestroy()
    {
        if (beforeButton != null) beforeButton.onClick.RemoveListener(ShowBefore);
        if (afterButton != null) afterButton.onClick.RemoveListener(ShowAfter);
    }

    // 他の経路 (インスペクタ・コンテキストメニュー) で切り替わったときも表示を合わせる
    void Update()
    {
        if (shown != Mode) Refresh();
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
}
