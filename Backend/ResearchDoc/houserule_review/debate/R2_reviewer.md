# R2 — Reviewer meta-review

**(1) Highest score now:** the paired household-swap **evaluation**. All four papers: nobody measured it. Second: the per-object undetermined verdict (false-acts vs false-holds).

**(2) Adjudication**
- **Decomposition.** RuleBench (Table 1: NL beats FOL) vs ShieldAgent (Table 2: rule circuits +10.2 over full-policy prompt) is mixed, so preregister C as **two-sided**: "the representation changes per-object applicability on held-out combinations". Null or negative results are reportable.
- **Arms.**
  - ShieldAgent and AgentSpec share one arm (A3).
  - RuleGraph with one chunk per object changes the executor, not the representation: a deferral baseline.
  - Only two primary comparisons (A4 vs A2, A4 vs A3, α = .025 each). The rest are secondary, so ~200 pairs suffice.
- **Skip/ask fairness.** All arms output {act, leave, defer + missing} into the same executor. They share an oracle shortlist (Codex); retrieval is scored separately; a forced-binary variant is also reported.
- **String matching.** A GT `mark` attribute reduces the task to string equality (skeptic is right). Make it non-trivial with:
  - perceived stickers (small, rotated, occluded);
  - paraphrased rule text ("cups with the little star");
  - indirect reference ("same sticker as my mug");
  - distractors (asterisk/pentagon stickers, star-patterned objects, printed stars on packaging).

  GT becomes an upper bound only.
- **Opaque IDs and fresh sessions** (Codex) are adopted.

**(3) Revised experiment**
1. 5 ★⇄○ crossover families plus a fragile control. Marks counterbalanced across material, hazard, position, difficulty.
2. 24 scenes, 8–12 objects each, ≥2 distractor marks per scene. Rule text literal / paraphrased / indirect.
3. Splits: instance, category, and held-out target×condition×action combinations, scope holding and not.
4. Representation arms (same executor): A1 full text, A2 retrieved text, A3 AgentSpec/ShieldAgent-like, A4 CoGround. A3/A4: oracle and compiled rules.
5. Deferral arms: B0 rule-blind, B1 RuleGraph per object, B2 whole-command defer, B3 forced binary.
6. Conditions: perceived marks (primary), GT (upper bound), 25% of attributes masked.
7. Sim: 24×5×2 = 240 paired episodes per arm per condition, 3 seeds.
8. Real: 144 episodes (2 families × 6 scenes × 2 households × {A4, best of A2/A3} × 3).
9. Primary metric: pair success. Secondary: violation rate, completion rate, per-object × action P/R, false-act, false-hold.

**(4) Contribution sentence:** "On a paired household-swap protocol (same scene and broad request, perceived resident rules uncorrelated with commonsense), we measure how rule representation and per-object undetermined handling affect joint avoid-and-complete success on held-out object–rule combinations."

**Retract if:**
- verified prior work already runs an identical-scene swap of resident rules with joint per-object scoring (check PARSEC and NormAct first);
- every arm hits ceiling on ★/○ under perception and paraphrase;
- any directional claim fails its preregistered bound.

**(5) Vote:** primary framing is the **evaluation benchmark**. Decomposition and undetermined are findings within it; HRI is separate.
