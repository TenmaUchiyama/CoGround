# R2 — Empiricist rebuttal

## 1. Concessions
- **Theorist's omission problem is right.** My S1 rule left State unable to mark an unmoved object, and State+Diff pulls attention away from it. S1 as written was biased against its own hypothesis.
- Three representations × three defect types at N=48 is too thin. I drop the State-without-diff condition.
- Reviewer: the State view is not built; the current arcs and ghost playback are my Process condition.

## 2. Rebuttals
- **Reviewer's 2×2 plus text at N≈24–32:** five conditions leave too few signal trials per defect type. That N rests on Rosen's effect (η²=.55), which came from a degraded monitor baseline; Gadre 2019 adds strong order effects.
- **Advocate's "High" for Claim 1** is "nobody built it" only; the Advocate's own risk section says so.
- **DR stays out.** Taylor 2020 and Skeptic's change-detection evidence (Kim et al., which I have not checked) make it a confound.
- **Skeptic Q1:** nothing guarantees State wins. The reason to expect it: a goal is a predicate over a state (Theorist's congruence argument), and playback is transient while the request must be held in memory. Hence the pre-registered equivalence test.

## 3. Answers
- **Fulfilment marking without doing the detection:** add *request anchors* in both conditions. Each object the robot bound to the request gets a neutral marker, with no fulfilled/unmet verdict. An omission then shows as an anchored object with no change; a wrong binding exposes an interpretation error. Verdict marking is a follow-up, with some verdicts seeded wrong to measure over-reliance.
- **Matched salience:** not by matching types. Rotate each seeded plan through both conditions across participants and model item as a random effect, so item salience cancels within item. Omission, commission and side-effect fit this. Intermediate-only is invisible in State by construction; I keep it as a declared probe outside the headline contrast.
- **2×2 vs medium-fixed:** medium-fixed first. A 2D arm rendered from the same scene graph can run between-subjects as a replication, not as an AR-vs-2D claim.
- **Interpretation errors:** harvest real misparses of ambiguous requests from the LLM front-end the Reviewer describes (I have not verified it in the build) and replay them deterministically.
- **Headline DV:** d′ on goal-satisfaction defects, State vs Process; assumed dz≈0.5. PerceptTwin's "up to 18%" on consistency errors is the only anchor.

## 4. Final design
1. Within-subjects, all in HMD, robot static, request text visible.
2. Conditions: Process (ghost playback ending on final state) vs State+Diff (After, Before toggle, moved objects highlighted).
3. Request anchors in both; no verdicts.
4. 40 plans per condition, 20 seeded.
5. Defects: interpretation 4, feasibility 4, omission 4, commission 4, side-effect 2, intermediate-only 2.
6. Plans rotated across conditions; Latin-square order.
7. Response: fulfilment level, localize object, confidence.
8. Phases: 5 s exposure, then unlimited.
9. DVs: d′, criterion, time-to-correct-judgment, localization, calibration, NASA-TLX.
10. Trial-level mixed models; equivalence test pre-registered.
11. N=48.
12. Optional 2D replication arm, between-subjects.

## 5. Top-3 novelty claims
1. Representation × defect-type crossover, including omissions (empirical).
2. Graded fulfilment judgment with calibration under neutral request anchoring (empirical).
3. Parity-matched 2D replication of claim 1 (empirical, secondary).

## 6. Vote
Empirical state-vs-process.
