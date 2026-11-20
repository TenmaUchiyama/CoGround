using System.Collections.Generic;
using System.Globalization;
using Newtonsoft.Json.Linq;

/// <summary>
/// 家庭ルール (state.norms の 1 件) を、見せる言葉にする。ルールの枠は 原文 + 規範・条件・対象・内容。
///
/// ■ 内容と条件の言い方は、サーバーの語彙から読む
///   state.vocabulary (Backend/grounding_server/coground_server/norms/vocabulary.py の export) に、内容・条件ごとの
///   言い方 (phrase。{region} などは引数で埋める)・実行中の応答・変化か状態か、が入っている。
///   Unity 側は内容の名前を自分で持たない。サーバーに内容を足しても、ここに手を入れなくてよい。
///   語彙が届いていなければ、名前をそのまま出す。
///
/// ■ 使い方
///   CoGroundNormText.Content(norm, state)     「the base enters the zone」
///   CoGroundNormText.Conditions(norm, state)  「18:00–23:00 · unless box_white has no free space」(無ければ空)
///   CoGroundNormText.Judgment(j)              「N1 doesn't apply: fragile = false (VLM)」
///   CoGroundNormText.Missing(key, entity)     「free space of box_white」
/// </summary>
public static class CoGroundNormText
{
    /// <summary>内容の言い方 (requirement.predicate + args)</summary>
    public static string Content(JToken norm, JToken state)
    {
        var requirement = norm?["requirement"];
        var name = (string)requirement?["predicate"];
        if (string.IsNullOrEmpty(name)) return "";
        var args = requirement["args"] as JObject ?? new JObject();
        // 対象が領域のルールは、その領域が引数 zone になる
        if (args["zone"] == null && (string)norm["target"]?["kind"] == "zone" && norm["target"]?["id"] != null)
            args = new JObject(args) { ["zone"] = norm["target"]["id"] };
        return Phrase(Entry(state, "contents", name), name, args);
    }

    /// <summary>条件 (時刻・依頼者・状態) を 1 行にする。条件が無ければ空</summary>
    public static string Conditions(JToken norm, JToken state)
    {
        var scope = norm?["scope"];
        if (scope == null || scope.Type != JTokenType.Object) return "";
        var parts = new List<string>();
        string from = (string)scope["from"], until = (string)scope["until"];
        if (!string.IsNullOrEmpty(from) && !string.IsNullOrEmpty(until)) parts.Add($"{from}–{until}");
        else if (!string.IsNullOrEmpty(from)) parts.Add($"from {from}");
        else if (!string.IsNullOrEmpty(until)) parts.Add($"until {until}");
        var requester = (string)scope["requester"];
        if (!string.IsNullOrEmpty(requester)) parts.Add($"only when {requester} asks");
        var when = Condition(scope["when"], state, true);
        if (!string.IsNullOrEmpty(when)) parts.Add(when);
        return string.Join(" · ", parts);
    }

    /// <summary>状態についての条件 (scope.when)。all は AND、negate は NOT</summary>
    static string Condition(JToken c, JToken state, bool top)
    {
        if (c == null || c.Type != JTokenType.Object) return "";
        var negate = (bool?)c["negate"] == true;
        string body;
        if (c["all"] is JArray all && all.Count > 0)
        {
            var inner = new List<string>();
            foreach (var child in all)
            {
                var t = Condition(child, state, false);
                if (!string.IsNullOrEmpty(t)) inner.Add(t);
            }
            body = string.Join(" and ", inner);
            if (negate) return $"unless ({body})";
            return top ? "when " + body : body;
        }
        var name = (string)c["predicate"];
        if (string.IsNullOrEmpty(name)) return "";
        body = Phrase(Entry(state, "conditions", name) ?? Entry(state, "contents", name), name, c["args"] as JObject);
        if (!top) return negate ? "not " + body : body;
        return (negate ? "unless " : "when ") + body;
    }

    /// <summary>条件が読んでいる領域 (base_in_zone の zone)。床に範囲を見せるのに使う</summary>
    public static List<string> ConditionZones(JToken norm)
    {
        var zones = new List<string>();
        Collect(norm?["scope"]?["when"], zones);
        return zones;
    }

    static void Collect(JToken c, List<string> zones)
    {
        if (c == null || c.Type != JTokenType.Object) return;
        if (c["all"] is JArray all)
            foreach (var child in all) Collect(child, zones);
        if ((string)c["predicate"] == "base_in_zone" && (string)c["args"]?["zone"] is string zone && !zones.Contains(zone))
            zones.Add(zone);
    }

    /// <summary>実行中に破りそうになったときの応答 (replan / hold)。語彙が無ければ null</summary>
    public static string Response(JToken norm, JToken state) =>
        (string)Entry(state, "contents", (string)norm?["requirement"]?["predicate"])?["response"];

    /// <summary>内容の対象がロボット自身か (止まる・速さの上限など)</summary>
    public static bool IsAboutRobot(JToken norm) => (string)norm?["target"]?["kind"] == "robot";

    /// <summary>
    /// 物体とルールの対象条件の照合 (state.judgments[object_id] の 1 件) を 1 行にする。
    /// 例: 「N1 doesn't apply: fragile = false (VLM)」。属性で選ばないルール (個体の指定) は、サーバーの文をそのまま使う。
    /// </summary>
    public static string Judgment(JToken j)
    {
        if (j == null) return "";
        var id = (string)j["rule_id"];
        var attribute = (string)j["attribute"];
        if (string.IsNullOrEmpty(attribute)) return (string)j["sentence"] ?? "";
        var matches = j["matches"];
        var source = SourceLabel((string)j["source"]);
        var by = string.IsNullOrEmpty(source) ? "" : $" ({source})";
        if (matches == null || matches.Type == JTokenType.Null)
            return $"{id} can't be decided: {attribute} is unknown";
        return (bool)matches
            ? $"{id} applies: {attribute} = {Show(j["actual"])}{by}"
            : $"{id} doesn't apply: {attribute} = {Show(j["actual"])}{by}";
    }

    /// <summary>値の出どころ (Attribute.source) の言い方</summary>
    public static string SourceLabel(string source)
    {
        switch (source)
        {
            case "vlm": return "VLM";
            case "user": return "resident";
            case "detector": return "detector";
            case "ground_truth": return "scene";
            default: return source ?? "";
        }
    }

    /// <summary>未確定のとき足りない事実 (MissingFact) の言い方</summary>
    public static string Missing(string key, string entityId)
    {
        string what;
        if (key != null && key.StartsWith("attr:")) what = key.Substring(5);
        else
            switch (key)
            {
                case "clock": what = "time"; break;
                case "requester": what = "who asked"; break;
                case "object_region": what = "current location"; break;
                case "zone_shape": what = "area"; break;
                case "base_pose": what = "base position"; break;
                case "base_speed": what = "base speed"; break;
                case "person_pose": what = "where people are"; break;
                case "holding": what = "what the robot holds"; break;
                case "region_capacity": what = "free space"; break;
                default: what = key ?? "?"; break;
            }
        return string.IsNullOrEmpty(entityId) ? what : $"{what} of {entityId}";
    }

    // ---- 部品 ----

    static JToken Entry(JToken state, string table, string name)
    {
        if (string.IsNullOrEmpty(name) || !(state?["vocabulary"]?[table] is JArray entries)) return null;
        foreach (var e in entries)
            if ((string)e["name"] == name) return e;
        return null;
    }

    /// <summary>言い方の {引数} を埋める。引数が無ければ語彙の既定値、それも無ければ ?</summary>
    static string Phrase(JToken entry, string name, JObject args)
    {
        var phrase = (string)entry?["phrase"];
        if (string.IsNullOrEmpty(phrase)) return name; // 語彙がまだ届いていない
        var sb = new System.Text.StringBuilder();
        for (int i = 0; i < phrase.Length; i++)
        {
            var close = phrase[i] == '{' ? phrase.IndexOf('}', i) : -1;
            if (close < 0) { sb.Append(phrase[i]); continue; }
            var key = phrase.Substring(i + 1, close - i - 1);
            var value = args?[key] ?? entry["defaults"]?[key];
            sb.Append(value == null || value.Type == JTokenType.Null ? "?" : Show(value));
            i = close;
        }
        return sb.ToString();
    }

    static string Show(JToken value)
    {
        if (value == null || value.Type == JTokenType.Null) return "unknown";
        switch (value.Type)
        {
            case JTokenType.Boolean: return (bool)value ? "true" : "false";
            case JTokenType.Float: return ((double)value).ToString("0.##", CultureInfo.InvariantCulture);
            default: return value.ToString();
        }
    }
}
