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
