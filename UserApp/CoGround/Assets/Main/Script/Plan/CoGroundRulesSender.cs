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
///   コンテキストメニューの「片付けデモのルールを入れる」で、ゴミと割れ物のルールを入れる。
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
        [Tooltip("「触らない」ルールにする (条件に合う物にロボットが触れることを禁止する。norms.set で送る。Target Region は見ない)")]
        public bool noTouch;
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
            if (r.noTouch || string.IsNullOrWhiteSpace(r.targetRegion)) continue;
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
    /// 「触らない」ルール (noTouch) を家庭ルールの形 (NormRule。禁止 + contact) にする。norms.set で送る。
    /// </summary>
    public List<JObject> BuildNoTouchNorms()
    {
        var list = new List<JObject>();
        for (int i = 0; i < rules.Count; i++)
        {
            var r = rules[i];
            if (!r.noTouch || string.IsNullOrWhiteSpace(r.attribute)) continue;
            var condition = $"{r.attribute} = {r.equals}";
            list.Add(JObject.FromObject(new
            {
                id = string.IsNullOrWhiteSpace(r.id) ? $"rule_{i + 1}" : r.id.Trim(),
                original_text = string.IsNullOrWhiteSpace(r.text) ? $"Don't touch {condition}" : r.text,
                norm = "prohibition",
                target = new { kind = "object", where = new { attribute = r.attribute.Trim(), equals = ParseValue(r.equals) } },
                requirement = new { predicate = "contact" },
                source = "demo",
            }));
        }
        return list;
    }

    /// <summary>
    /// 閉じた語彙の検出 (CoGroundYoloWorldProvider の 6 つ) 用のルール。置き場所は EnvironmentBoxes の箱の名前。
    ///   食器 (plate / mug / glass)  → sink
    ///   紙くず (paper_scrap)        → trash_box
    ///   はさみ・包丁 (危ない物)      → 触らない
    /// shelf_lower / shelf_upper は今は使わない (割り当てる物が無い)。
    /// </summary>
    [ContextMenu("閉じた語彙のルールを入れる")]
    public void UseClosedVocabularyRules()
    {
        rules = new List<RuleEntry>
        {
            new RuleEntry { id = "dishes_to_sink",   text = "Put dishes in the sink",         attribute = "group",    equals = "dish",        targetRegion = "sink" },
            new RuleEntry { id = "paper_to_trash",   text = "Throw paper scraps in the trash", attribute = "category", equals = "paper_scrap", targetRegion = "trash_box" },
            new RuleEntry { id = "no_touch_knife",   text = "Don't touch knives (dangerous)",  attribute = "category", equals = "knife",       noTouch = true },
            new RuleEntry { id = "no_touch_scissors", text = "Don't touch scissors (dangerous)", attribute = "category", equals = "scissors",   noTouch = true },
        };
#if UNITY_EDITOR
        UnityEditor.EditorUtility.SetDirty(this);
#endif
    }

    /// <summary>
    /// 片付けデモ (TidyDemoSetup) のルール。ゴミ → trash_bin と、割れ物に触らない。
    /// ゴミは group = trash でなく trash 属性で決める (pet_bottle は group = trash だが、デモでは捨てない物)。
    /// 「それ以外は箱へ」は家庭ルールではないので入れない。どのルールにも当たらない物は、
    /// 依頼が無いときは運ばず、依頼 (task.request) の対象なら「収納先を決めるルールが無い」で保留になる。
    /// 割れ物ルールは行き先が無いので BuildRules で落ち、rules.set では送られない (触らないは家庭ルール norms.set の仕事)。
    /// </summary>
    [ContextMenu("片付けデモのルールを入れる")]
    public void UseTidyDemoRules()
    {
        rules = new List<RuleEntry>
        {
            new RuleEntry { id = "trash",   text = "Throw trash in the trash bin",           attribute = AttributeKey.Trash,   equals = "true", targetRegion = "trash_bin" },
            new RuleEntry { id = "fragile", text = "Don't touch fragile items", attribute = AttributeKey.Fragile, equals = "true"},
        };
#if UNITY_EDITOR
        UnityEditor.EditorUtility.SetDirty(this);
#endif
    }

    [ContextMenu("Send Rules")]
    public void SendRules()
    {
        Send(BuildRules());
        // 「触らない」ルールがあるときだけ norms.set を送る (norms.set は家庭ルールを丸ごと置き換えるので、
        // 無いときに空を送って、声で登録したルールを消さないようにする)
        var norms = BuildNoTouchNorms();
        if (norms.Count > 0) SendNorms(norms);
    }

    [ContextMenu("Clear Rules On Server")]
    public void ClearRules() => Send(new List<RuleDto>());

    async void SendNorms(List<JObject> norms)
    {
        var c = Client;
        if (c == null || !c.IsConnected) return;
        try
        {
            var result = await c.RequestAsync("norms.set", new { norms });
            Debug.Log($"[CoGroundRulesSender] norms.set: norms={result["norms"]} steps={result["steps"]}");
        }
        catch (CoGroundRpcException e)
        {
            Debug.LogWarning($"[CoGroundRulesSender] norms.set failed: {e.Message} {e.Details}", this);
        }
    }

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
