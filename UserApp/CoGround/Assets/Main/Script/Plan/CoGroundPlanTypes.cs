using System.Collections.Generic;
using Newtonsoft.Json;
using UnityEngine;

/// <summary>
/// state.updated の rules / plan の型。サーバー側の定義は Backend/grounding_server/coground_server/models.py
/// (Rule / Plan / Step / Placement / Pose)。座標は Unity のワールド座標。
///
/// Plan は、サーバーがシーンとルールから作る (coground_server/planner.py)。
/// ルールが無ければ state の plan は null。step になるのは「ルールに合い、行き先がいまの場所と違う物」だけ。
/// </summary>
public class RuleDto
{
    [JsonProperty("id")] public string Id;
    /// <summary>可視化で見せる文。例: 割れ物は棚の下段に置く</summary>
    [JsonProperty("text")] public string Text;
    /// <summary>null なら「それ以外」(条件のあるルールのどれにも合わなかった物に使う)</summary>
    [JsonProperty("condition")] public RuleConditionDto Condition;
    /// <summary>行き先の領域の ID (place_zone を持つ物体の ID。例: sink_1)</summary>
    [JsonProperty("target_region")] public string TargetRegion;
    /// <summary>speech / demo / script</summary>
    [JsonProperty("source")] public string Source = "script";
}

public class RuleConditionDto
{
    /// <summary>属性のキー (AttributeKey)、または category / group / role</summary>
    [JsonProperty("attribute")] public string Attribute;
    /// <summary>bool / float / string</summary>
    [JsonProperty("equals")] public object EqualsValue;
}

public class PlanDto
{
    [JsonProperty("id")] public string Id;
    [JsonProperty("version")] public int Version;
    [JsonProperty("base_scene_version")] public int BaseSceneVersion;
    [JsonProperty("steps")] public List<StepDto> Steps = new List<StepDto>();
}

public class StepDto
{
    [JsonProperty("id")] public string Id;
    /// <summary>実行順 (0 始まり)</summary>
    [JsonProperty("index")] public int Index;
    [JsonProperty("object_id")] public string ObjectId;
    [JsonProperty("from")] public PlacementDto From;
    /// <summary>行き先が決まらなければ null (ambiguous / unmatched)</summary>
    [JsonProperty("to")] public PlacementDto To;
    [JsonProperty("rule_id")] public string RuleId;
    [JsonProperty("candidate_rule_ids")] public List<string> CandidateRuleIds = new List<string>();
    /// <summary>StepStatus のどれか</summary>
    [JsonProperty("status")] public string Status;
    [JsonProperty("locked")] public bool Locked;
    [JsonProperty("trajectory_id")] public string TrajectoryId;
    [JsonProperty("message")] public string Message;
    /// <summary>この step に関係する家庭ルールの判定 (依頼 task.request から作った Plan だけに出る)</summary>
    [JsonProperty("verdicts")] public List<VerdictDto> Verdicts = new List<VerdictDto>();
}

/// <summary>家庭ルールの判定 (サーバー側は models.py の Verdict)。</summary>
public class VerdictDto
{
    [JsonProperty("rule_id")] public string RuleId;
    /// <summary>VerdictValue のどれか</summary>
    [JsonProperty("value")] public string Value;
    /// <summary>predicted (計画の予測) / observed (実行中の観測)</summary>
    [JsonProperty("basis")] public string Basis;
    [JsonProperty("entity_id")] public string EntityId;
    /// <summary>未確定のとき、何が分かれば結論が出るか</summary>
    [JsonProperty("missing")] public List<MissingFactDto> Missing = new List<MissingFactDto>();
    [JsonProperty("detail")] public string Detail;
}

public class MissingFactDto
{
    [JsonProperty("entity_id")] public string EntityId;
    /// <summary>attr:fragile / clock / requester / object_region / zone_shape / base_pose / base_speed / person_pose /
    /// holding / region_capacity。見せる言葉は CoGroundNormText.Missing</summary>
    [JsonProperty("key")] public string Key;
}

public static class VerdictValue
{
    public const string Violated = "violated", Compliant = "compliant", NotApplicable = "not_applicable", Undetermined = "undetermined";

    public static string Label(string value) =>
        value == Violated ? "Violated" : value == Compliant ? "Compliant" : value == Undetermined ? "Undetermined" : "Not applicable";
}

public class PlacementDto
{
    [JsonProperty("region_id")] public string RegionId;
    [JsonProperty("pose")] public PoseDto Pose;
}

// PoseDto は Scene/CoGroundSceneTypes.cs で定義 (scene.update と plan で共通)

public static class StepStatus
{
    /// <summary>ok: 計画できた / ambiguous: 合うルールが複数あって決められない / unmatched: 行き先が無い / infeasible: MoveIt で計画できない</summary>
    public const string Ok = "ok", Ambiguous = "ambiguous", Unmatched = "unmatched", Infeasible = "infeasible";
    /// <summary>deferred: 家庭ルールによる保留 (禁止に反する予測、判定する情報が足りない、収納先を決める取り決めが無い)。to が入っていても運ばない</summary>
    public const string Deferred = "deferred";
}
