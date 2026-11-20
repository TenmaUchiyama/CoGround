"""依頼の結果を、住人に伝える形にする（設計ガイド §1 の 5、§2 の「説明・訂正」）。

    「コップは下段に収納しました。皿は割れ物に触れないという取り決めに従って机に残しました」

文はテンプレートで作る（LLM は使わない）。物体ごとに、結果・理由・根拠にした取り決めの原文を返し、
「全部」に対する未達成も数える。訂正があれば、その前後で変わった項目も返す。

物体ごとの judgments は、対象の条件（属性 = 値）との照合の結果を、合わなかったものも含めて並べる:

    「割れ物ではない（fragile = false。VLM の判断）ので、『割れ物には触らない』は当てはまらない」

VLM が自信を持って間違えると、ルールは「非該当」になって黙って素通りする。照合の結果を見せておけば、
住人がその場で気づいて直せる（objects.set_attribute。住人の訂正は VLM の答えより優先する）。
"""

from __future__ import annotations

from typing import Any

from ..models import SceneObject
from .model import NormRule
from .task import TaskRecord, TaskRow

BASIS = {"predicted": "predicted", "observed": "observed"}
VALUE = {"violated": "violated", "compliant": "compliant", "not_applicable": "not applicable", "undetermined": "undetermined"}


def build_report(task: TaskRecord, norms: list[NormRule], holds: list[dict[str, Any]] | None = None,
                 objects: list[SceneObject] | None = None) -> dict[str, Any]:
    """holds are the records of stopping the base during execution (monitor.py). For each object, the reason and time of stopping are attached.

    objects（いまのシーンの物体）を渡すと、行ごとに judgments（対象の条件との照合。非該当も含む）を付ける。"""
    by_id = {n.id: n for n in norms}
    rows = [_row(r, by_id) for r in task.rows]
    seen = {o.id: o for o in objects or []}
    for row in rows:
        obj = seen.get(row["object_id"])
        row["judgments"] = judgments(obj, norms) if obj is not None else []
    for row in rows:
        row["holds"] = [h for h in holds or [] if h.get("object_id") == row["object_id"]]
    counts = task.counts()
    summary = f"Stored {counts['done']} of {counts['total']} items."
    return {
        "task_id": task.id, "text": task.text, "requester": task.requester,
        "counts": counts,
        "summary": summary,
        "message": " ".join([summary, *(r["sentence"] for r in rows)]),
        "rows": rows,
        "corrections": [c.model_dump(mode="json") for c in task.corrections],
    }


def _row(row: TaskRow, norms: dict[str, NormRule]) -> dict[str, Any]:
    reasons = [
        {
            "rule_id": rid, "original_text": norms[rid].original_text if rid in norms else None,
            "value": v.value, "basis": v.basis, "label": f"{VALUE[v.value]} ({BASIS[v.basis]})",
        }
        for rid, v in row.verdicts.items() if v.value != "not_applicable"
    ]
    return {
        "object_id": row.object_id, "label": row.label, "exec_state": row.exec_state,
        "destination": row.destination, "destination_rule_ids": row.destination_rule_ids,
        "sentence": _sentence(row, norms),
        "reasons": reasons,
        "route": row.route,
        "missing": [m.model_dump(mode="json") for m in row.missing],
    }


SOURCE = {"vlm": "judged by the VLM", "user": "corrected by a resident", "detector": "from the detector",
          "ground_truth": "given by the scene"}


def judgments(obj: SceneObject, norms: list[NormRule]) -> list[dict[str, Any]]:
    """物体 1 つを、物体が対象のルールすべての対象条件と照合した結果（合わなかったものも含む）。

    matches: true（該当） / false（非該当） / null（属性の値が無く、分からない）。
    attribute・expected・actual・source は、属性 = 値で選ぶルールのときだけ入る。"""
    out: list[dict[str, Any]] = []
    for rule in norms:
        t = rule.target
        if rule.norm == "permission" or t.kind != "object" or (t.where is None and t.id is None):
            continue
        matches = t.matches(obj)
        item: dict[str, Any] = {"rule_id": rule.id, "original_text": rule.original_text, "matches": matches}
        if t.id is not None and obj.id != t.id:
            item["sentence"] = f"Not the object this agreement names ({t.id}), so \"{rule.original_text}\" doesn't apply."
        elif t.where is None:
            item["sentence"] = f"This is the object \"{rule.original_text}\" names, so it applies."
        else:
            key, expected, actual = t.where.attribute, t.where.equals, obj.value(t.where.attribute)
            attribute = obj.attributes.get(key)
            source = attribute.source if attribute is not None else None
            item.update({"attribute": key, "expected": expected, "actual": actual, "source": source,
                         "confidence": attribute.confidence if attribute is not None else None})
            how = f" ({SOURCE.get(source, source)})" if source else ""
            if matches is None:
                item["sentence"] = (f"Whether {key} is {_show(expected)} isn't known, so \"{rule.original_text}\" "
                                    f"can't be decided yet.")
            elif matches:
                item["sentence"] = f"{key} is {_show(actual)}{how}, so \"{rule.original_text}\" applies."
            else:
                item["sentence"] = (f"{key} is {_show(actual)}{how}, not {_show(expected)}, so \"{rule.original_text}\" "
                                    f"doesn't apply.")
        out.append(item)
    return out


def _show(value: Any) -> str:
    return str(value).lower() if isinstance(value, bool) else str(value)


def _sentence(row: TaskRow, norms: dict[str, NormRule]) -> str:
    name = f"{row.label or row.object_id} ({row.object_id})"
    where = f" The specified storage location is {row.destination}." if row.destination else ""
    state = row.exec_state
    if state == "done":
        return f"Stored {name} in {row.destination}."
    if state == "deferred":
        blocking = next((rid for rid, v in row.verdicts.items() if v.value == "violated" and v.basis == "predicted"), None)
        if blocking is not None and blocking in norms:
            if norms[blocking].target.kind == "zone":
                return f"Left {name} without carrying it, because there's no path that doesn't violate the agreement \"{norms[blocking].original_text}\".{where}"
            return f"Left {name} without moving it, following the agreement \"{norms[blocking].original_text}\".{where}"
        if row.missing:
            lacking = ", ".join(_fact(m.entity_id, m.key) for m in row.missing)
            return f"{name} is on hold because information needed to decide ({lacking}) is missing.{where}"
        return f"{name} is on hold ({row.reason}).{where}"
    if state == "pending":
        return f"{name} will be carried to {row.destination}."
    if state == "in_progress":
        return f"Carrying {name} to {row.destination}."
    if state == "placed_unverified":
        return f"Placed {name}. Checking whether it's in {row.destination}."
    if state == "misplaced":
        return f"Placed {name}, but it's in a different place than specified ({row.reason})."
    if state == "unverified":
        return f"Placed {name}, but couldn't confirm that it's in {row.destination}."
    return f"Couldn't carry {name} ({row.reason})."


def _fact(entity_id: str | None, key: str) -> str:
    what = {"clock": "time", "requester": "requester", "object_region": "current location", "zone_shape": "area",
            "base_pose": "base position", "person_pose": "person position", "base_speed": "base speed", "holding": "what the robot holds",
            "region_capacity": "free space"}.get(key)
    if what is None:
        what = f"attribute {key.removeprefix('attr:')}" if key.startswith("attr:") else key
    return f"{what} of {entity_id}" if entity_id else what
