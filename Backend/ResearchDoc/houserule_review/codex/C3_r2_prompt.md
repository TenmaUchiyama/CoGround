Round 2 of the house-rule novelty debate. You are the INDEPENDENT ARBITER (different model family). No tools: do not try shell, file or web tools. Below are your own round-1 paper and the three Claude debaters' round-1 papers.
Write ≤450 words (English): (1) Where the Claude debaters are wrong or overclaim, and where they corrected you; (2) Adjudicate the key disputes: is per-object deferral more than RuleGraph-with-one-chunk-per-object (give the decisive behavioural test case); how to state the decomposition hypothesis given RuleBench (NL > FOL in most cases; counterfactual drop) and ShieldAgent (+10.2% over complete-policy prompting); does star/circle with a ground-truth 'mark' attribute reduce to string matching and how to make it non-trivial; fairness of a skip/ask option for raw-text arms; (3) Final top-3 claims (unit, status) and ONE outcome-agnostic contribution sentence + precise retraction conditions; (4) Vote: primary framing = evaluation benchmark / method (decomposition) / system (undetermined) / HRI.

===== debate/R1_codex.md =====
### Stance summary

A and B are established mechanisms, and C’s rule representation has clear precedents.  
D’s household swap is an evaluation candidate. Whether decomposition improves generalization under that swap is a scientific question.  
Per-object deferral with named missing facts has a testable consequence. The supplied evidence establishes neither an equivalent robot evaluation nor a null result.

### Claims table

| Claim | Unit | Closest prior | Status | Strength |
|---|---|---|---|---|
| A. Transfer taught rules to new objects | method | Tan, Video Demonstration, Figs. 1–2. Jain §3, §5.2 establishes attribute-conditioned transfer. | 既出 | H |
| B. Reuse rules on independent requests | method | Tan, Fig. 1 bottom. AgentSpec §3.2, §5.2 checks actions. Wu §III-B, Table I retrieves at scene level, with rule authorship unspecified. | 既出 | H |
| C. Decomposed rule representation | method | AgentSpec §3.2, §5.3. ODRL 2.2 Rule and conflict property. Meneguzzi & Luck §§1–2. ADICO is a structural precedent. | 既出 | H |
| C. Decomposition improves held-out applicability | method | Safety Chip Table I compares LTL with text. RuleGraph §4.6, Table 4 ablates per-rule verification. I2 confirms VIMA §3 holds out texture–object combinations. | 証拠不足 | H |
| D. Partial completion | system | RuleGraph §4.1, Table 1 measures joint success on simulated instruction chunks. | 既出 | H |
| D. Paired household swap with joint completion | evaluation | RuleGraph Table 1 and PARSEC §§IV, VI, Table II cover complementary axes. PARSEC’s identical object sets are unverified. | 差分候補 | M |
| Per-object hold with named missing facts and continued execution | system | SafeGate §IV, Stage 3 defers whole commands. VFM §3, App. A.1 merges inapplicable and undeterminable. | 差分候補 | M |
| Resident confirmation and scope edits with visible diffs | HRI | AgentSpec §1 anticipates user review. Safety Chip §III-C uses expert verification. | 差分候補 | L |

### What to investigate/build/measure

1. **Randomize the household policy.** Replay identical scenes and later requests with opposite star/circle prohibitions. Counterbalance marks across material, hazard, position and placement difficulty. Use opaque object IDs and fresh sessions. Supply marks only through explicit ground-truth attributes or a shared perception pipeline. Include a rule-blind control and a separate fragility condition. Score zero forbidden contacts **and** correct completion of every permitted object, then require both households to pass. Report violation and completion rates separately.

2. **Isolate decomposition.** Hold out target × condition × action triples while exposing their constituent elements during teaching. Include scope matches and misses. Compare full raw text, retrieved raw text, AgentSpec-like trigger/check/enforce, and CoGround. Hold facts, candidate actions and execution policy fixed. Give all matchers the same oracle shortlist for the applicability comparison, then evaluate retrieval separately. Cross text and fields with the same judge to isolate representation from executor changes. Use oracle and compiled rules to expose compilation errors. Score rule applicability per object and candidate action before defaults run. Compare expressible cases across all arms and test richer cases against a trigger baseline with equivalent semantics.

3. **Specify and test the semantics.** [own knowledge, unverified] ABAC-style predicates can encode scope and target, defeasible priority can encode linked permissions, and runtime verification can check selected trace segments. Strong Kleene evaluation plus an applicability decision and missing-fact provenance can produce the four verdicts. The tuple alone establishes no new logic. Preregister cases where a false scope masks a missing attribute, a relevant unknown holds one object while independent objects proceed, and requester identity changes only the linked prohibition. Replay a plan predicted compliant whose observed trace contains contact inside the forbidden window. Include an incomplete trace to test when a verdict can become final. Measure false acts, false holds and permitted completion under controlled missingness.

4. **Test HRI separately.** Measure resident correction accuracy and teaching effort with and without scope confirmation and diffs.

### Contribution sentence + retraction conditions

**Conditional contribution:** “On held-out rule combinations, explicit rule decomposition improves per-object applicability and joint cleanup success over matched raw-text and trigger–check–enforce baselines in paired trials that vary only resident-taught rules.”

Withdraw the improvement claim if paired confidence bounds fail preregistered minimum gains on either outcome, or if the gains disappear with matched rule access and enforcement. Scope any ground-truth-only gain to ground-truth inputs. Withdraw evaluation novelty if equivalent prior paired evidence is verified.

### Biggest risk

A favorable comparison could measure better retrieval, extra semantics, or fortunate default cleanup while leaving applicability unchanged.

### Questions to other debaters

- Which nearest prior could run the identical household swap with resident rules?
- What trace or requester counterexample would distinguish CoGround from a semantics-matched trigger–check–enforce implementation?
===== debate/R1_advocate.md =====
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

===== debate/R1_skeptic.md =====
# R1 — Skeptic / prior-art attacker

**Stance.** Every CoGround mechanism (A–D) is prior art, under one name or another. The remaining "evaluation" difference recombines existing designs: same scene with different users or values, rules that conflict with model defaults, and joint success. What I could not knock down is listed at the end.

**New evidence from this round** (10 web searches, 2026-11-19):
- **FLEX** (Lee, Dennler, Sucholutsky, Bobu, arXiv 2610.28893, CoRL 2026) **[V-full]**.
  - A correction such as "don't spill on my laptop" is generalised to a category (electronics, flammable, fragile). The generalisation runs over text object properties that are *assumed to be given* (§4).
  - FLEX beats an unscaffolded single-LLM-call baseline (USF scores 0.64 on ADD-only; §5.1, Table 1).
  - Gaps: every participant shares one predefined preference per task (§5.3), so there is **no rule swap**. Rules are commonsense-aligned. The output is a trajectory cost, not the choice of objects to touch. The N=12 study ran in simulation.
- **RuleBench** (Sun et al., arXiv 2407.08440v4) **[V-part]**.
  - LLMs follow **natural-language rules better than formal (FOL) rules** "in most cases" (§4.3, Table 1).
  - Performance drops significantly on **counterfactual rules** (§4.5, Table 2).
- **ShieldAgent** (ICML 2025, arXiv 2503.22738) **[V-part]**. It compiles policies into action-based rule circuits and checks only the circuits relevant to the action. It beats "Direct prompt (complete policy)" and per-rule traversal by +10.2% accuracy (§5.2, Table 2). The test is not on held-out combinations.
- **RobotValues** (2606.03312; S3 **[V-partial]**). Same household image with a different target value. Accuracy is 13–25% when the target conflicts with the model's default. There is no execution.
- **DynaGuard** (ICLR 2026) **[V-meta + secondary]** and **RuLES** (arXiv 2311.04235) **[V-meta]**. Both evaluate arbitrary user-written prohibit/mandate rules.
- **Null searches.** No paper swaps rules on the same scene with forbidden/permitted scoring. No paper defers per object while the rest of the request executes (KnowNo, CLARA, OntoPlan and ASK-TO-ACT come closest; abstracts only). No paper runs a decomposed-vs-raw deontic ablation on held-out embodied combinations.

## Claims table

| Claim | Unit | Closest prior | Status | Strength |
|---|---|---|---|---|
| (a) Paired household swap + joint metric | evaluation | PARSEC (same environment instance, several users, §IV); RoboGuard App. D-B (the environment changes too); RobotValues; RuleBench counterfactual; RuleGraph TSR; NormAct; CCAI | 差分候補: each ingredient has been measured, but never combined on a robot | L–M |
| (b) Per-object undetermined + `missing` list, rest executes | system | SafeGate R3 (whole command); VFM (collapses N/A, App. A.1); Kwon 2024; RuleGraph | 差分候補 (small; "nobody built") | L |
| (c) Arbitrary resident rules → new instances | method | Tan 2019; Brawer HRI 2023; Kasenberg 2019; FLEX; DynaGuard | 既出 | — |
| (d) Decomposition helps on untaught combinations | method | AgentSpec/ADICO/ODRL; Safety Chip Table I; ShieldAgent Table 2; FLEX USF. **Against:** RuleBench Table 1 | 証拠不足; the prior evidence is *mixed*, not absent | L |
| `pending` scope confirmed by the resident | HRI | Safety Chip (expert verification); AgentSpec ("user review", §1); nl2spec | 既出 in spirit | L |

## What to investigate / build / measure (ranked)
1. **Spec §5-3 with five arms.**
   - Arms: raw full text; retrieved raw text; ShieldAgent/AgentSpec-like per-action rules without deontic types; full (N,S,T,C); commonsense-only.
   - Use held-out object × rule pairs, including cases where the condition holds and where it does not.
   - Run each arm with ground-truth attributes and with perceived attributes.
2. **Swap with counterfactual (star/circle) rules plus a "fragile" control.** Report both-correct per pair and the drop from commonsense-aligned to counterfactual rules.
3. **False-hold vs false-act rates under attribute noise.** Compare against a whole-command defer (SafeGate-like) and a forced-binary verdict.
4. **Check whether PARSEC's object sets are identical across users.**

## Contribution sentence
"On a paired household-swap protocol (same scene and broad request, resident rules uncorrelated with commonsense), per-object applicability over decomposed rules with an explicit undetermined verdict yields higher joint success (no forbidden contact, all permitted objects completed) than raw-text, retrieved-text and AgentSpec-style baselines on held-out object–rule combinations."

**Retract if:**
- (i) the AgentSpec/ShieldAgent-like arm or the retrieved-text arm falls within the confidence interval of the full method;
- (ii) the gain appears only with ground-truth attributes;
- (iii) the gain appears only on commonsense-aligned rules;
- (iv) `undetermined` lowers false-act only at a proportionate cost in false-hold;
- (v) a prior work already swaps rule sets on an identical scene and instruction with per-object joint scoring. In that case drop the protocol claim and keep only the method claim.

## What I could NOT knock down
- No verified work fixes the scene and the instruction, swaps **resident-taught** rule sets, and scores forbidden avoidance and permitted completion jointly per object.
- No work ablates deontic decomposition against raw and retrieved text on held-out embodied combinations. Given RuleBench, the result would be informative in either direction.
- No system combines a per-object undetermined verdict carrying the missing facts with execution of the remaining objects.

## Biggest risk
The decomposition gain may vanish against the ShieldAgent/AgentSpec-like arm. That would leave only a benchmark that reviewers can call a recombination of PARSEC, RobotValues and RuleGraph TSR.

## Questions to other debaters
- Can anyone verify PARSEC object-set identity, or RoboGuard App. D-B on an identical environment?
- Is per-object deferral anything more than RuleGraph with one chunk per object? What is the evidence?

===== debate/R1_reviewer.md =====
# R1 — PC Reviewer + Experimenter

**Stance.** I would reject a paper claiming A–D as written. None of the mechanisms is new (I2 §4: AgentSpec + RuleGraph + SafeGate together reproduce them). What survives is one result that nobody has measured: on the same scene and the same request, swapping between households rules that commonsense cannot guess, scored jointly per object, with an ablation of the decomposition. That result counts only if the experiment below is actually run.

## Likely top-3 rejection reasons

1. **"This is a recombination of existing parts."** A is shown by Tan 2019 (S1 and S3), TidyBot (70 unseen real objects, 85.0%), RoboGuard (per-entity LTL over perceived maps) and Jain 2013 (fragile/sharp attributes transfer to new objects). B is shown by Wu 2611.18026 (rules selected from a stored set for a later task and image, Table I), AgentSpec (rules that persist across tasks, compiled from NL by an LLM, 95.56/70.96, §5.3) and Tan S2 (refusing a later command). D's execution side is shown by RuleGraph (refuse the harmful parts and complete the rest, TSR 84.54 / ASR 0, Table 1).
2. **"C is asserted, not shown, and may be confounded with commonsense."** Decomposed representations already exist: AgentSpec trigger/check/enforce (§3.2), ODRL, ADICO and Meneguzzi 2009. Structured-beats-raw results also exist. Safety Chip, per S3's reading of its Table I: raw NL 38–56% safety vs 84% (LTL, unverified) / 100% (LTL, expert-verified); S3's own summary of the same table quotes NL as 54–62%, so the exact NL figure should be checked in the PDF before citing. RuleGraph Table 4 (TSR −10.3 pt without per-rule nodes). Without a raw-text arm and an AgentSpec-like arm on held-out combinations, C has no support. If the rules are commonsense ("don't touch fragile"), the LLM's prior explains the success (TidyBot measured this confound once: commonsense 45.6% vs 91.2%).
3. **"Evaluation is on ground-truth symbols, and the undetermined verdict is not new."** Unity attributes are ground truth, demos are small, and the verdict design is SafeGate's DEFER1 on critical unknowns plus VFM's per-criterion N/A (which explicitly discusses separating inapplicable from undeterminable). False-hold and false-act rates are not measured. Deferring per object looks like RuleGraph with one chunk per object. A further HRI objection: claiming residents teach easily needs a user study.

## Claims table

| Claim | Unit | Closest prior | Status | Strength |
|---|---|---|---|---|
| A: a taught rule applies to new instances | method | Tan 2019, TidyBot, RoboGuard, Jain 2013 | 既出 | H |
| B: stored rules × later request | method | Wu 2611.18026, AgentSpec, DROC | 既出 (per-object × action granularity only a small 差分) | H |
| C: decomposition helps on held-out combinations | method / effect | AgentSpec, ODRL, Safety Chip T.I | representation 既出, effect 証拠不足 | M |
| D: household swap with joint success | evaluation | RuleGraph TSR, PARSEC, RoboGuard App. D-B | 差分候補 (nobody has measured it) | M |
| Per-object undetermined while the rest runs | method (small) | SafeGate R3, VFM | 差分候補 | L–M |

## Experiment (spec §5 made concrete)

**Rule sets.** There are 5 swap families. Each family is a crossover pair of households: H_A forbids touching ★ and permits ○, H_B does the reverse. Each household also has one obligation (where things go), one scope (time or requester) and one exception. Marks are stickers assigned at random and balanced across material (glass, ceramic, plastic, paper) and category, so mark and material are uncorrelated (χ² check reported). One extra commonsense **control** family uses "don't touch fragile". That gives 12 rule sets.

**Scenes.** 24 table scenes with 8–12 objects each: 2–4 ★, 2–4 ○, the rest unmarked. Instructions are fixed ("片づけて").

**Splits.** Teaching examples use instance set I_t, and evaluation never reuses those instances. The category split holds out whole categories (rules taught on cups, tested on bowls and vases). Combination cells (target × condition × action) are each seen individually but never seen together, and the condition is balanced between holding and not holding.

**Arms.** All arms get the same perception, rules and candidate actions.
1. Full rule text in the prompt.
2. Raw rule text retrieved (top-k with BGE, as in Wu).
3. AgentSpec-like rules (trigger/check/enforce, with no deontic types and no exceptions).
4. CoGround R = (N, S, T, W, φ).

Every arm gets an explicit "skip/ask" option so the comparison of undetermined handling is fair. Arms 3 and 4 are each run twice: with an oracle-verified compile, and with the LLM compile. This separates compile errors from matching errors.

**Conditions.** GT attributes vs perception (Unity render → detector/VLM estimates of mark, category and fragile). In 25% of objects one rule-relevant attribute is masked.

**Trials.** GT condition: 24 scenes × 5 families × 2 households = 240 episodes per arm, 3 LLM seeds each. A McNemar test with 10 pt discordance (15/5), α = 0.05/3 and power 0.8 needs about 206 pairs, so 240 is enough. Perception condition: 120 episodes per arm. Control family: 48 per arm. Real robot: 2 families × 6 scenes × 2 households × {CoGround, best baseline} × 3 repetitions = 144 episodes, reported descriptively with Wilson CIs.

**Metrics.** These are fixed in advance and computed separately for the instance, category and combination splits.
- **Primary: joint success.** No forbidden contact AND every permitted object correctly put away.
- **Pair success.** Both households of a pair correct on the same scene.
- Forbidden-violation rate and permitted-completion rate.
- Applicability precision and recall per object × action, using a mixed-effects model clustered by scene.
- On masked objects: deferral precision (deferred objects whose GT verdict actually depended on the missing fact) and wrong-execution rate (objects acted on that turn out to be violations).
- The key statistic is the interaction **arm × rule type (★/○ vs fragile)**.

**Feasibility.** `norms/evaluate.py` already returns Kleene 3-valued, per-object × per-rule verdicts with `missing`, and `planner.py` (`plan_task`) defers per row while planning the rest. Arm 4 is therefore deterministic once R exists. Arms 1–3 and the scene generator still need to be built (about 2–3 weeks). The marks need a `mark` attribute and target predicate (`Target.matches` reads attributes).

**Reportable outcomes.**
- **Decomposition wins** (≥10 pt joint success over arms 2 and 3 on the combination and category splits, holding under perception). Claim a *limited* method contribution, naming the splits where it held.
- **Null.** Retract C. Publish the swap benchmark plus the finding that raw-text LLMs equal decomposition when the rules are arbitrary. The arm × rule-type interaction is still new.
- **Decomposition loses.** Publish a negative result with an error breakdown (compile vs perception vs matching), which tells people where structure hurts.

## Venue and minimum evidence

The paper survives at **ICRA/IROS/RA-L, framed as evaluation**. HRI/RO-MAN needs an added teaching-burden user study (n ≥ 16 within-subjects, time to teach and correct, measured as spec §6 allows). CoRL fits only if decomposition wins under perception. The minimum evidence is the GT-condition swap with all 4 arms and the fragile control, plus ≥1 real-robot swap pair.

## Contribution sentence

"On a same-scene, same-request household-swap benchmark with rules that commonsense cannot guess, we measure, per object, whether robots avoid forbidden objects while completing permitted ones, and show that [decomposed matching / raw-text prompting] achieves X% pair success on untaught combinations versus Y% for the strongest baseline."

**Retract it if:**
- a prior paper reports a same-scene rule swap with joint scoring;
- the difference from arms 2 and 3 is under 10 pt or its CI crosses 0;
- the gain disappears in the ★/○ condition (that is, it is only a commonsense effect);
- the gain comes only from oracle compilation.

## Biggest risk

The LLM compile is the bottleneck. If arm 4 needs the oracle compile to win, C becomes a claim about a hand-written DSL, which is AgentSpec.

## Questions to other debaters

1. Does anyone have a verified same-scene rule-swap result in PARSEC (identical object sets?) or NormAct?
2. Is the "skip/ask" option for the raw-text arms a fair baseline, or does it favour CoGround?
3. Should RuleGraph adapted to one chunk per object be a fifth arm?
