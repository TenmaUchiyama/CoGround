using System;
using UnityEngine;

/// <summary>ルールが計画に「何を伝えるか」。色を分ける。</summary>
public enum CoGroundRuleKind
{
    Obligation,  // 義務       青
    Prohibition, // 禁止       赤
    Undecided,   // 判断できない 黄
    Infeasible,  // 計画できない 灰
    Permission,  // 許可       紫
}

/// <summary>
/// ルール表示の配色 (種類 → 名前・板の色・文字の色・アイコン)。
///
/// ■ 使い方
///   既定のアセットは Assets/Main/Resources/CoGroundRuleStyle.asset。ここを Inspector で直すと、
///   すべての吹き出し・看板・床 (CoGroundRuleTag) に反映される。
///   別の配色を試すときは Create > CoGround > Rule Style で作り、CoGroundRuleTag の Style に入れる。
///   アセットが無くても、コードの既定値で動く。
///
/// ■ スクリプトから
///   CoGroundRuleStyle.MainColor(kind) / TextColor(kind) / Label(kind) は既定のアセットを見る。
///   アセットごとに引くときは style.Get(kind)。
/// </summary>
[CreateAssetMenu(menuName = "CoGround/Rule Style", fileName = "CoGroundRuleStyle")]
public class CoGroundRuleStyle : ScriptableObject
{
    [Serializable]
    public class Entry
    {
        public CoGroundRuleKind kind;
        [Tooltip("【】の中や見出しに出す名前")]
        public string label;
        [Tooltip("板・吹き出し・床の模様の色")]
        public Color color = Color.white;
        [Tooltip("板の上の文字の色 (明るい板なら黒にする)")]
        public Color textColor = Color.white;
        [Tooltip("色だけに頼らず種類を見分けるためのアイコン (空なら出さない)")]
        public Sprite icon;

        public Entry() { }

        public Entry(CoGroundRuleKind kind, string label, Color color, Color textColor)
        {
            this.kind = kind; this.label = label; this.color = color; this.textColor = textColor;
        }
    }

    public const string ResourcePath = "CoGroundRuleStyle";

    static readonly Color Ink = new Color(0.12f, 0.12f, 0.12f);

    [SerializeField] Entry[] entries = Defaults();

    static Entry[] Defaults() => new[]
    {
        new Entry(CoGroundRuleKind.Obligation, "Obligation", new Color(0.16f, 0.42f, 0.92f), Color.white),
        new Entry(CoGroundRuleKind.Prohibition, "Prohibition", new Color(0.86f, 0.18f, 0.18f), Color.white),
        new Entry(CoGroundRuleKind.Undecided, "Undecidable", new Color(0.98f, 0.80f, 0.12f), Ink),
        new Entry(CoGroundRuleKind.Infeasible, "Infeasible", new Color(0.45f, 0.47f, 0.50f), Color.white),
        new Entry(CoGroundRuleKind.Permission, "Permission", new Color(0.56f, 0.30f, 0.86f), Color.white),
    };

    static CoGroundRuleStyle defaultStyle;
    static bool isFallback;
    static Entry[] fallback;

    /// <summary>既定の配色 (Resources/CoGroundRuleStyle。無ければコードの既定値)</summary>
    public static CoGroundRuleStyle Default
    {
        get
        {
            if (defaultStyle != null && !isFallback) return defaultStyle;
            var loaded = Resources.Load<CoGroundRuleStyle>(ResourcePath);
            if (loaded != null)
            {
                if (isFallback && defaultStyle != null) DestroyImmediate(defaultStyle);
                defaultStyle = loaded;
                isFallback = false;
            }
            else if (defaultStyle == null)
            {
                // アセットが無いときはコードの既定値 (後でアセットができたら、そちらに切り替える)
                defaultStyle = CreateInstance<CoGroundRuleStyle>();
                defaultStyle.hideFlags = HideFlags.HideAndDontSave;
                isFallback = true;
            }
            return defaultStyle;
        }
    }

    public Entry Get(CoGroundRuleKind kind)
    {
        if (entries != null)
            foreach (var e in entries)
                if (e != null && e.kind == kind) return e;
        // アセットから消された種類はコードの既定値
        fallback ??= Defaults();
        foreach (var e in fallback)
            if (e.kind == kind) return e;
        return fallback[0];
    }

    public static Color MainColor(CoGroundRuleKind kind) => Default.Get(kind).color;
    public static Color TextColor(CoGroundRuleKind kind) => Default.Get(kind).textColor;
    public static string Label(CoGroundRuleKind kind) => Default.Get(kind).label;

#if UNITY_EDITOR
    void OnValidate()
    {
        // 色を変えたら、開いているシーンのタグに反映する
        UnityEditor.EditorApplication.delayCall += () =>
        {
            if (this == null) return;
            foreach (var t in FindObjectsByType<CoGroundRuleTag>(FindObjectsInactive.Include, FindObjectsSortMode.None))
                t.Apply();
        };
    }
#endif
}
