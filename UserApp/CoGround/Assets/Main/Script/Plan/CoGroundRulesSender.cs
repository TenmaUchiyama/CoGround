using System;
using System.Collections.Generic;
using System.Globalization;
using Newtonsoft.Json.Linq;
using UnityEngine;

/// <summary>
/// インスペクタに書いたルールを、グラウンディングサーバーに rules.set で送る (ルール全体を置き換える)。
/// 自然言語からルールを作る処理 (rules.compile) ができるまでの、確認用の入口。
///
/// ■ 例 (tabletop のシーン)
///   Attribute = group,      Equals = dish,     Target Region = sink_1              (食器はシンクへ)
///   Attribute = waste_type, Equals = burnable, Target Region = trash_bin_burnable  (燃えるごみは燃えるごみ箱へ)
///   Attribute = fragile,    Equals = true,     Target Region = shelf_lower         (割れ物は棚の下段へ)
///   Otherwise = true,                          Target Region = box_1               (それ以外は箱にしまう)
///
/// ■ 「それ以外」のルール (Otherwise)
///   条件のあるルールのどれにも合わなかった物 (role = item) を、Target Region へ運ぶ。Attribute / Equals は見ない。
///
/// ■ 片付けデモ (TidyDemoSetup のシーン)
///   コンテキストメニューの「片付けデモのルールを入れる」で、ゴミ・割れ物・しまう物の 3 つのルールを入れる。
///
/// Target Region は、place_zone を持つ物体 (CoGroundSceneObject) の ID。
/// サーバーはルールを受け取ると Plan を作り直し、state.updated で配る (CoGroundPlanView が描く)。
/// サーバーでは片付けルールも家庭ルール (norms.set。「割れ物に触るな」など) と同じ並びに入る。rules.set は片付けルールだけを置き換え、家庭ルールは消さない。
/// </summary>
public class CoGroundRulesSender : MonoBehaviour
{
    [Serializable]
    public class RuleEntry
    {
        [Tooltip("空なら rule_1, rule_2, ... を付ける")]
        public string id;
        [Tooltip("可視化で見せる文")]
        public string text;
        [Tooltip("「それ以外」のルールにする (条件のあるルールのどれにも合わなかった物に使う。Attribute / Equals は見ない)")]
        public bool otherwise;
        [Tooltip("属性のキー (fragile, material, waste_type など)、または category / group / role")]
        public string attribute = "group";
        [Tooltip("true / false、数値、文字列のどれか")]
        public string equals = "dish";
        [Tooltip("行き先の領域の ID (place_zone を持つ物体の ID)")]
        public string targetRegion;
    }

    [SerializeField] CoGroundServerClient client;
    [SerializeField] List<RuleEntry> rules = new List<RuleEntry>();
    [SerializeField] bool sendOnConnect = true;

    CoGroundServerClient Client => client != null ? client : CoGroundServerClient.Instance;
    CoGroundServerClient subscribed;

    void Start()
    {
        subscribed = Client;
        if (subscribed == null) { Debug.LogWarning("[CoGroundRulesSender] CoGroundServerClient が見つからない", this); return; }
        subscribed.Connected += OnConnected;
        if (subscribed.IsConnected) OnConnected();
    }

    void OnDestroy()
    {
        if (subscribed != null) subscribed.Connected -= OnConnected;
    }

    void OnConnected()
    {
        if (sendOnConnect) SendRules();
    }

    public List<RuleDto> BuildRules()
    {
        var list = new List<RuleDto>();
        for (int i = 0; i < rules.Count; i++)
        {
            var r = rules[i];
            if (string.IsNullOrWhiteSpace(r.targetRegion)) continue;
            if (!r.otherwise && string.IsNullOrWhiteSpace(r.attribute)) continue;
            var condition = r.otherwise ? "otherwise" : $"{r.attribute} = {r.equals}";
            list.Add(new RuleDto
            {
                Id = string.IsNullOrWhiteSpace(r.id) ? $"rule_{i + 1}" : r.id.Trim(),
                Text = string.IsNullOrWhiteSpace(r.text) ? $"{condition} → {r.targetRegion}" : r.text,
                Condition = r.otherwise ? null : new RuleConditionDto { Attribute = r.attribute.Trim(), EqualsValue = ParseValue(r.equals) },
                TargetRegion = r.targetRegion.Trim(),
            });
        }
        return list;
    }

    /// <summary>
    /// 片付けデモ (TidyDemoSetup) の 3 つのルール。ゴミ → trash_bin、割れ物 → box_2、それ以外 (しまう物) → box_1。
    /// ゴミは group = trash でなく trash 属性で決める (pet_bottle は group = trash だが、デモでは捨てない物)。
    /// 割れ物かつゴミの物があると、行き先が 2 つになり ambiguous (人に聞く) になる。
    /// </summary>
    [ContextMenu("片付けデモのルールを入れる")]
    public void UseTidyDemoRules()
    {
        rules = new List<RuleEntry>
        {
            new RuleEntry { id = "trash",   text = "Throw trash in the trash bin",           attribute = AttributeKey.Trash,   equals = "true", targetRegion = "trash_bin" },
            new RuleEntry { id = "fragile", text = "Don't touch fragile items", attribute = AttributeKey.Fragile, equals = "true"},
            new RuleEntry { id = "store",   text = "Put everything else in the box (box_1)",   otherwise = true,                                    targetRegion = "box_1" },
        };
#if UNITY_EDITOR
        UnityEditor.EditorUtility.SetDirty(this);
#endif
    }

    [ContextMenu("Send Rules")]
    public void SendRules() => Send(BuildRules());

    [ContextMenu("Clear Rules On Server")]
    public void ClearRules() => Send(new List<RuleDto>());

    async void Send(List<RuleDto> list)
    {
        var c = Client;
        if (c == null || !c.IsConnected) { Debug.LogWarning("[CoGroundRulesSender] サーバーに接続していない", this); return; }
        try
        {
            var result = await c.RequestAsync("rules.set", new { rules = list });
            Debug.Log($"[CoGroundRulesSender] rules.set: rules={result["rules"]} steps={result["steps"]}");
            if (result["unknown_regions"] is JArray unknown && unknown.Count > 0)
                Debug.LogWarning($"[CoGroundRulesSender] シーンに無い領域がある: {unknown.ToString(Newtonsoft.Json.Formatting.None)}", this);
        }
        catch (CoGroundRpcException e)
        {
            Debug.LogWarning($"[CoGroundRulesSender] rules.set failed: {e.Message} {e.Details}", this);
        }
    }

    static object ParseValue(string s)
    {
        s = (s ?? "").Trim();
        if (bool.TryParse(s, out var b)) return b;
        if (float.TryParse(s, NumberStyles.Float, CultureInfo.InvariantCulture, out var f)) return f;
        return s;
    }
}
