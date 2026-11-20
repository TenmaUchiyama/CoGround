# R1 — ADVOCATE

**Stance summary**
1. I concede that A, B and the rule representation (C-method) are not new. AgentSpec, RoboGuard, Tan 2019, DROC, ODRL and Meneguzzi already cover them.
2. One claim is defensible. CoGround judges each object × action and keeps "not applicable" separate from "undetermined" (which lists the missing facts). It defers only the undetermined objects and runs the rest. The test uses **resident-arbitrary rules** (star/circle) in a **paired household swap**. This is an evaluation/system contribution, not a new mechanism.
3. Today this is "nobody measured", not "nobody built". The protocol has not been run. Real attribute perception is not built: `vlm.py` offers only `off` and `mock`, so attributes come from Unity ground truth.

**Claims table**

| Claim | Unit | Closest prior | Status | Strength |
|---|---|---|---|---|
| (i) Star/circle rules that commonsense cannot predict, applied per object × action inside a broad request | evaluation | TidyBot: commonsense 45.6% vs 91.2% (placement only, v2 Tab. 2/4). VLTSafe and Kwon (commonsense). VIMA T12/13 (constraint given in the prompt) | 差分候補: nobody measured (S2: 2 searches) | M |
| (ii) 4-valued per-object verdict + `missing`. Defer only those objects, execute the rest | system | SafeGate R3 (whole-command DEFER1, Table II). VFM (N/A merges both cases, §3/App. A.1). RuleGraph (chunk-level, Table 1) | 差分候補, small. Built in `evaluate.py` (Kleene logic; undetermined only when `missing` is non-empty) and `planner.py` | M (mechanism) / L (novelty) |
| (iii) Resident corrections (attribute / scope / zone / exception) with a row diff | HRI | Kasenberg 2019, Brawer HRI 2023, nl2spec | 証拠不足. Built (`AttributeCorrection.changes`), but no user study | L |
| (iv) Paired household swap with joint success | evaluation | PARSEC (placement only). RoboGuard App. D-B (environment changes too). RuleGraph TSR (fixed rules) | 差分候補 (I1 §4, I2 §4) | H (design), unmeasured |
| (v) Window W + predicted/observed basis | method | LTL temporal scoping (RoboGuard, Safety Chip). SafeGate guards. AgentSpec triggers | 既出 in substance | L |
| C-effect | method | No one has ablated it (AgentSpec has no raw-text arm) | 証拠不足 for everyone | open |

**What to investigate, build or measure (ranked)**
1. **Paired swap (spec §5-1, §5-4).**
   - Setup: same desk, same objects, same "片づけて". Household A keeps ★ cups, household B keeps ● cups. The marks are uncorrelated with material or danger. Keep a "fragile" control.
   - Metrics: joint success, violation rate, completion rate, pair-both-correct rate, and per object × action precision/recall.
   - Baselines:
     - X: AgentSpec-like predicates + RuleGraph per object (I2 §4)
     - SafeGate-style whole-command deferral
     - commonsense only
2. **Undetermined ablation.**
   - Hide or corrupt ★/●/fragile on k% of objects.
   - Arms: CoGround vs (a) Boolean `unknown_as=false` (already in `Target`), (b) whole-command defer, (c) VFM-style N/A collapse.
   - Metrics: false-act, false-hold, joint success, number of questions.
   - The claim survives only if it beats (a) and (b) at an equal false-act rate.
3. **Decomposition ablation (§5-3).**
   - Arms: full text, retrieved raw text, AgentSpec-like decomposition (no deontic types or exceptions), full (N,S,T,C).
   - Run on held-out combinations, with ground-truth attributes and with perception.
4. **A real VLM/OCR `AttributeProvider`**, so perception errors and matching errors can be measured separately.
5. **A user study for (iii)**, only if (iii) is claimed: time to repair a wrong scope, and resident prediction accuracy with vs without the diff.

**Contribution sentence**
"Same scene, same broad request, different households: the rules cannot be predicted from commonsense. Under these conditions, per-object, per-action judgement against resident-taught rules — with an explicit undetermined verdict that defers only the undecidable objects — achieves higher joint success (no forbidden contact, all permitted objects completed) than whole-command deferral, Boolean checking, or commonsense planning."

**Retract if**
- composite X or the Boolean arm matches it on joint success at an equal false-act rate;
- the gain appears only on the fragile rule and not on ★/●;
- a prior same-scene, same-instruction resident-rule swap with joint scoring is found (re-check PARSEC's object identity and NormAct's appendix);
- the gain disappears under perception.

**Biggest risk**
(ii) collapses into "SafeGate + RuleGraph at per-object granularity". I2 §4 calls that adaptation straightforward. If X performs equally well, only protocol (iv) survives, and only if it exposes failures that existing metrics hide.

**Questions to other debaters**
1. Does any paper measure partial completion per **object** while deferring unknowns? Are RuleGraph's Compound chunks ever single objects?
2. Is ★/● a strawman, given that a VLM reading the rule text predicts it trivially? Which commonsense arm is fair?
3. Should W and predicted/observed be dropped from the claim or kept as enabling detail?
4. If PARSEC's object sets are identical across users, does (iv) shrink to "PARSEC + prohibitions"?
