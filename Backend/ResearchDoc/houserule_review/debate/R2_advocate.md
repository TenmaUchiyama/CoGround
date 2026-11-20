# R2 — ADVOCATE rebuttal

## 1. Concessions
- Evidence on C-effect is mixed. RuleBench Table 1 favours natural language; ShieldAgent Table 2 favours structure.
- W and the basis tags are enabling detail, not claims.
- (iii) is not claimed without a user study.
- All attributes so far are ground truth. `vlm.py` offers only off and mock.

## 2. Rebuttals
- **"Recombination."** PARSEC, RobotValues and RuleGraph each measure a different axis. None measures resident-rule swap × per-object joint completion. Spec §6 counts an unmeasured outcome as an evaluation contribution.
- **"RuleGraph with one chunk per object."** RuleGraph's state is complete JSON (I2 R1). It has no unknowns, so the cases below cannot be expressed in it.

## 3. Answers
**Behaviour differences** (`norms/evaluate.py`, run in the `grounding_server:dev` image):
- **False scope masking.** Rule: "★: don't touch 18–22". For a cup with ★ unknown:
  - at 10:00 → `not_applicable`, so the cup is handled;
  - at 20:00 → `undetermined` [`attr:star`].

  Defer-on-any-unknown would hold it at 10:00; `unknown_as=false` would touch it at 20:00.
- **Requester-linked exception.** Rule: "don't touch ★ unless alice asks".
  - Requester alice → `not_applicable`.
  - Requester bob → `violated`.
  - Requester unknown → `undetermined`, missing only `requester`.

  A separate fragile prohibition is unaffected throughout, so the question is precise.
- **Holding one object.** `planner.py` defers per row while planning the rest. (not re-run end to end).

**Hypothesis to pre-register:**
- H0: on single-factor rules, decomposed ≈ raw within ±5 pt joint success.
- H1: the decomposed − raw gap is larger for ★/● combined with scope, exception or missing facts than for fragile (an arm × rule-type × factor-count interaction).

**Is skip/ask for the raw-text arms fair?** Yes, it is required. Give every arm the same output, {act, skip, ask + named fact}, and score ask-precision.

## 4. Top-3 claims
1. Paired household swap with counterfactual rules and joint/pair success. Unit: evaluation. Status: 差分候補 (nobody measured).
2. Scope-aware per-object undetermined + `missing` while the rest executes. Unit: system. Status: 差分候補, small.
3. Decomposition effect on held-out combinations. Unit: method. Status: 証拠不足, reported either way.

**Contribution sentence.** "On a paired household-swap protocol (same scene and request, with resident rules uncorrelated with commonsense), we measure whether per-object rule decomposition with an explicit undetermined verdict changes joint success, false-act and false-hold rates relative to matched raw-text, retrieved-text and trigger–check–enforce arms that have identical skip/ask options."

**Retract if:**
- a verified prior same-scene resident-rule swap with joint scoring exists;
- there is no significant arm × rule-type interaction;
- undetermined trades false-act for false-hold one-for-one.

Scope any ground-truth-only effect to ground truth.

## 5. Vote
**Evaluation benchmark** is primary. The system claim (undetermined) is secondary and is tested inside the benchmark.
