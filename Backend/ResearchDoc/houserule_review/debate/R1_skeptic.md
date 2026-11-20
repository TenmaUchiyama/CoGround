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
