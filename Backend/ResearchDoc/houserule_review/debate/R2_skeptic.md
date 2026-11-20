# R2 — Skeptic

## 1. Verification (3 full-text PDF reads, 2026-11-19)

- **(a) PARSEC §IV [V-full].** Object sets were "sampled", and workers "only arrange the objects they considered relevant". The paper never says the object sets are identical across users, and it is placement only. **Not a refutation.**
- **(b) RoboGuard App. D-B [V-full].** The disaster rule set ran in the large indoor space and the construction set outdoors, each with different safe tasks (Table A.II). **No swap is on the same environment and task.**
- **(c) Safety Chip Table I [V-full].**
  - Safety rate with **raw NL = 54–62%**: NL 56/56, NL\* 54/62.
  - Formal arms reach 84/94, and 100/100 with expert verification.
  - The 38% (and 30%) belong to the Base model, which receives no constraints, so the "38–56%" range is wrong.
  - Spot robot: NL 34% vs Safety Chip 100%.

## 2. Concessions
- PARSEC and D-B are near-misses. The paired swap remains unmeasured.
- Nobody has built a per-object hold with `missing` that also continues the rest of the request.
- Safety Chip's "formal > raw" result is real. RuleBench (NL > FOL) is QA, so the prior is mixed rather than negative.

## 3. Rebuttals
- **Star/circle becomes string matching in the GT condition.** With `mark=star` given and the rule naming ★, every arm should hit the ceiling, which makes a 10-pt gap unreachable. Removing the commonsense prior does not make the test hard. The test becomes informative only if one of these holds:
  - the marks must be **perceived**;
  - the rule's referent differs from the attribute name ("grandma's cups", taught to be ★ separately);
  - ★ interacts with scope or exception (requester, time);
  - several rules coexist (RuleBench noise rules).
- **240 episodes is optimistic.**
  - Scenes are reused across families.
  - Temp-0 seeds are near-duplicates.
  - Arm 4 is deterministic once R exists.
  - Fix: use a scene-clustered GLMM, and pre-register a ceiling rule that drops any split where every arm scores ≥95%.
- **Advocate (ii) at strength M is premature.** False-act/false-hold have not been measured, so it is L until they are.

## 4. Top-3 defensible claims
1. **Paired household swap with per-object joint scoring and an arm × rule-type (★/● vs fragile) interaction.** Unit: evaluation. Status: 差分候補.
2. **Per-object undetermined + `missing` while the rest executes, with false-act/false-hold measured under masking.** Unit: system. Status: 差分候補 (small).
3. **Decomposition effect on held-out combinations.** Unit: method. Status: 証拠不足. To be reported as an outcome, not asserted.

**Sentence (outcome-agnostic):** "We introduce a paired household-swap benchmark (same scene and request, resident rules uncorrelated with commonsense, GT vs perceived attributes) and report joint/pair success and per-object deferral false-act/false-hold for raw-text, retrieved-text, trigger–check–enforce and deontic-decomposed matchers on held-out object–rule combinations."

**Retract if any of these holds:**
- an equivalent prior paired evaluation is verified;
- all arms hit the ceiling on every non-control split;
- the rules are only mark-name lookups, with no referent, scope or exception indirection;
- there are no perception results (then scope the claim to GT inputs).

## 5. Vote
**Primary framing: evaluation benchmark.** System (undetermined) is secondary. Method (decomposition) only if it wins.
