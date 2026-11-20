# R1 — Empiricist position

## Stance summary
- CoGround as a system is a recombination (X-OOHRI, MRPilot, SHRIMP, Previewed Reality each cover parts); "nobody built exactly this" is true but weak.
- The defensible gap is empirical: no study measures goal-satisfaction judgment over a predicted After state, and the nearest result is a null (PerceptTwin: execution video helped feasibility errors, not wrong-final-state errors, N=93).
- The novel independent variable is **state vs process** representation, crossed with **defect type**. In-situ vs 2D is a well-trodden IV with mixed results; diff/juxtaposition is a sub-factor of state.

## Novelty claims ranked

| Claim | Type | Closest threat | Strength |
|---|---|---|---|
| C1. An After-state view improves detection of goal-satisfaction defects where process playback does not (representation × defect-type interaction) | empirical | PerceptTwin (process only, null on "logic" errors); Polaris ("expectations matched" marginal, p≈.08) | **High**: untested by anyone |
| C2. Graded fulfilment judgment (full / partial / rule-blocked) with d′, criterion and confidence calibration | empirical | Sukkerd 2020 (correctness + confidence, navigation, text); Rosen 2019 (d′, binary collision) | **High** as a measure; needs C1 to matter |
| C3. In-situ vs 2D with information parity for task-level outcome judgment | empirical | Rosen 2019 (AR win, degraded point-cloud monitor baseline, feasibility only); Sibirtseva 2018 (HMD most errors, parity design); Wozniak 2023 (no accuracy difference); Qu 2026 (Level-1 SA only) | **Med**: the gap is real, the prior leans null |
| C4. Glance-first judgment dissociates from repair; explanation raises repair but not judgment | design-knowledge | CE-MRS (62.7% vs 29.5% resolved, correctness judgment unchanged); VizXP (comprehension up, correction n.s.); SHRIMP (editing raised TLX, plan-only no benefit) | **Med**: a replication in a spatial domain, not a first |
| C5. The integrated AR Before/After + drill-down + rule-linked repair system | system | X-OOHRI, MRPilot, Wang 2023, Previewed Reality | **Low** alone |

## What to investigate next

**S1 (run first): State vs Process × Defect type, medium held constant.**
- *Hypothesis:* State+Diff yields higher d′ than Process for goal-satisfaction defects, with no advantage (or a deficit) for feasibility defects.
- *Conditions (within-subjects, all in the HMD, same plan, same scene graph, request text always visible):* (a) Process: in-situ ghost playback ending on the final state; (b) State: After snapshot with Before toggle; (c) State+Diff: the same, with moved objects highlighted. The diff marks *what changes*, never *what is unmet*; otherwise the system, not the user, does the detection.
- *Tasks:* tidying plans, 50% seeded. Defects: interpretation (wrong object/destination), feasibility (blocked/unreachable step), goal-satisfaction (partial fulfilment; rule-blocked item). Response: fulfilment level (full / partial / blocked), then localize the object, then confidence.
- *DVs:* d′ and criterion per defect type, time-to-correct-judgment, localization accuracy, calibration, NASA-TLX. Two phases: fixed 5 s exposure (glance), then unlimited.
- *Outcomes:* **State wins on goal defects only**: first evidence that representation must match defect type, and an explanation of the PerceptTwin null. **Null** (pre-registered equivalence test): goal-satisfaction errors are not a display problem but a reference problem, since the user's intent is not externalized (consistent with Sukkerd's preference-misaligned drop, OR≈0.36); this redirects the design toward showing the interpreted goal. **State loses**: snapshots hide process defects and shift the criterion toward approval, so "understand at a glance" is hazardous without forced or signalled drill-down.
- *Sample size:* Rosen's large effect (η²=.55, N=32) came from a handicapped baseline, so plan for dz≈0.5: N=48 (Latin square), 36 trials per condition, trial-level mixed models. By my rough calculation this also supports an equivalence bound near ±0.45 dz; a tighter null needs more.
- *Confounds:* answer leakage through the diff; playback duration vs snapshot (hence the fixed-exposure phase); defect salience (pilot and balance); rule knowledge (train and test beforehand); registration error; 50% base rate inflating vigilance.

**S2: Medium (in-situ AR vs parity 2D) for the S1-winning representation.**
- 2D rendered from the same scene graph at the user's viewpoint, HMD worn in both (Walker 2018 control), no mouse navigation penalty.
- *Hypothesis:* AR advantage only for defects needing metric spatial judgment (clearance, reachability), none for symbolic ones (wrong object, rule).
- *Outcomes:* AR wins: Rosen replicated without the handicap, at task level. Null: Rosen's effect was baseline-driven, strengthening Sibirtseva and Wozniak. AR loses: an HMD cost for outcome review. Each outcome is reportable, but only because parity is strict.
- N≈32–48; main confound is novelty and order (Gadre 2019 found strong order effects).

**S3: Glance → explain → repair.**
- Rule-linked explanation on/off after a detected defect. DVs: repair success, time, replan iterations, over-repair (CE-MRS extraneous corrections 1.33 vs 5.24), post-explanation judgment accuracy, TLX.
- *Hypothesis:* explanation raises repair and cuts over-repair without changing judgment accuracy. Novel only if the dissociation appears in a spatial domain; otherwise it is confirmatory.

**Why S1 first:** it isolates the one factor nobody has manipulated, it is tied to a published null, all three outcomes change the design, and it needs no 2D build. S2 run first risks a fourth AR-vs-screen null with nothing new to say.

## Biggest risk
The S1 effect may be small or absent because goal-satisfaction errors depend on the user's unstated preferences, not on perception. Then CoGround's central motto is unsupported, and the contribution becomes a well-powered negative result that is harder to publish at HRI/CHI. Second risk: PerceptTwin's per-condition accuracies are only in a figure, so the baseline rate for power planning is unknown.

## Questions to the other debaters
1. System advocates: which claim survives if S1 is null?
2. If the diff highlights unmet goals, is the user judging anything, or just reading the planner's verdict? How is that evaluated?
3. Who has verified Diehl 2020 (AR vs RViz error detection, N=18) and Liu 2026 (spatial embedding vs 2D overview)? Either could pre-empt C3.
4. Is diminished reality an independent factor worth a condition, given Taylor 2020 (less effort, worse efficiency and preference)?
