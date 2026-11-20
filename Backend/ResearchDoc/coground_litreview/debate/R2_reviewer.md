# R2 — Reviewer meta-review

## 1. Highest-scoring contribution
The Empiricist's S1, sharpened by the Theorist's omission analysis. It manipulates the one factor nobody has manipulated, is tied to a published null (PerceptTwin), and every outcome is interpretable. The Theorist's congruence argument supplies the "why". The Advocate's interaction claims and the design space are supporting material.

## 2. Adjudications
- **S1 vs my 2×2.** S1 is the better first paper; I withdraw the 2×2 as the opening study. Crossing medium dilutes power and invites a fourth AR-vs-screen null. AR as apparatus does not hurt at HRI or CHI if nothing is claimed for it (MRPilot ran in VR, PerceptTwin online). It would hurt at UIST. Add S2 as a smaller second study if time allows.
- **System-marked unmet goals.** With marking, the study tests reliance on the planner's verdict, not detection. That is still worth testing: marks are computed against the robot's *interpreted* request, so interpretation errors and side effects stay unmarked. Keep S1's three conditions unmarked and add marking as a fourth. Its key DV is criterion shift on defects the marker misses.
- **Advocate's delta over X-OOHRI.** Real but narrower than stated. X-OOHRI's Auto resolution already previews a robot-proposed action sequence, so "robot-predicted" alone is not the delta. What survives is a whole-scene outcome of a delegated multi-object request whose interpretation can be wrong.

## 3. Answers
- *Skeptic Q2:* partly incorrect. `grounding_server/README.md` documents LLM compilation of language into rules and norms, and LLM selection of target objects, so interpretation errors can arise and be seeded.
- *Skeptic Q4:* same scene graph, same HMD, same request text; pre-register and publish a null.
- *Theorist Q2:* the server already records per-object results, with reasons on deferred steps. Side-effect reporting is not documented.
- *Empiricist Q1:* if S1 is null, only the "reference problem" finding and the marking condition survive.
- *Advocate Q3:* unknown; make object count (about 3 / 8 / 15) a factor.

## 4. Revised delta sentence
"Pre-execution previews show robot plans as processes and have not helped users detect wrong final states; we test whether showing the robot-predicted After state against the current scene improves judgment of how far a delegated request will be fulfilled, for which error types it helps or hides problems (notably omissions), and what request-anchored marking changes."

## 5. Go/no-go checklist (priority order)
1. Read MARCER and X-OOHRI in full; a robot-predicted whole-scene outcome view in either is a no-go for the interaction claim.
2. Build the in-headset After view with Before toggle, plus the diff variant.
3. Build ghost playback ending on the final state, matched in information.
4. Seeded-defect set: three concepts plus omission, side effect, intermediate-only; salience piloted.
5. Request-anchored fulfilment marking as a fourth condition.
6. Pre-register S1: N=48, d′ and criterion per defect type, 5 s glance phase, equivalence bounds.
7. Verify Diehl 2020; obtain PerceptTwin's per-condition accuracies for power planning.
8. Optional: parity 2D view (S2); in-headset repair (S3).

## 6. Vote
**Empirical, state vs process**, with the system as apparatus and the design space as discussion.
