# R1 — Theorist position: novelty at the level of framing and design knowledge

Tags: [A] agent files; [W] citation/abstract checked by web search this round; [M] from memory, unverified.

## Stance summary
- The three concepts are **not** new: Goal Satisfaction vs Feasibility is validation vs verification [M], SA Level-3 projection (Endsley [A]) and PerceptTwin's "logic vs consistency" split [A].
- "Outcome-first, process-on-demand" is "overview first, details on demand" (Shneiderman [M]) plus feedforward (Vermeulen et al., CHI 2013 [W]). It becomes a contribution only with **boundary conditions**.
- The defensible novelty is a testable **representation × error-type** claim plus a design space with an empty cell. Both are unproven.

## Novelty claims ranked

| # | Claim | Type | Closest threat | Strength |
|---|---|---|---|---|
| 1 | State (After-diff) displays favour detecting Goal Satisfaction errors; process displays favour Feasibility errors; neither exposes Interpretation errors unless anchored to the request. | design-knowledge / empirical | PerceptTwin [A]: process video helped feasibility, not final-state errors; never compared with a state view. Rosen 2019 (feasibility, AR), Sukkerd 2020 (goal, 2D) [A]. | **High**, once tested (nobody tested it) |
| 2 | Design space of pre-execution plan review; CoGround = robot-predicted × whole-scene outcome diff × in situ × cause-linked × local repair. | design-knowledge | Suzuki 2022; Walker 2023 [A, full text unread]. No "whose goal" axis found. | Med |
| 3 | "Outcome-level grounding": the After state is the robot's evidence of understanding; repair is the acceptance phase (Clark & Brennan 1991 [W, citation only]). | design-knowledge (framing) | Kiesler, RO-MAN 2005 [W, citation only]; Sibirtseva 2018 [A]; model reconciliation (Chakraborti, IJCAI 2017 [W]); FORTNIoT (IMWUT 2020, N=42: predicted smart-home states improved understanding) [W]; "HRI Grounding" RA-L 2026 [A, unverified]. | Med-Low |
| 4 | Outcome-first, process-on-demand as a principle. | design-knowledge | Shneiderman [M]; SAT (Chen 2014), Polaris, SHRIMP [A]. | Low as stated; Med with boundary conditions |
| 5 | The three-concept split itself. | design-knowledge | PerceptTwin; V&V; SA. | Low (analytic lens only) |

Claim 1 survives because theory predicts it. Tversky et al. 2002 [W]: graphics work when format is congruent with the concept. A goal is a predicate over a *state*; a precondition failure belongs to a *transition*. PerceptTwin's null on final-state errors fits; nobody ran the crossover.

Claim 3 is weak: unlike model reconciliation, CoGround externalises consequences rather than changing the human's model, but FORTNIoT already offers predicted future state as feedforward for delegated automation.

**Where the After state hides problems (predicted, untested):**
1. **Omissions.** An unfulfilled sub-goal is an object that did *not* move, so it produces no diff. The core Goal Satisfaction failure is what a Before/After diff shows worst (cf. change blindness [M]). It needs request-anchored marking (intended vs predicted).
2. **Intermediate-only violations** (a rule broken mid-plan, restored by the end).
3. **Side effects** on unmentioned objects.
4. **Non-state goals** (order, "wipe", "don't pass near X").
5. **Point prediction.** A wrong interpretation renders as a coherent, plausible scene.

**Design space (coded from agent files; re-verify):**

| System | Shown | Whose goal | Where | Cause link | Repair |
|---|---|---|---|---|---|
| GhostObjects / X-OOHRI | object target pose | user-authored | in situ | capability limits (X-OOHRI) | local |
| ImageInThat | state sequence + diff | user-authored | 2D | none | step edit |
| Polaris | action/state timeline | robot plan from user goals | 2D | weak | goal spec |
| SHRIMP / PerceptTwin | process playback | robot-predicted | detached sim | preconditions | local / none |
| MRPilot | path, commitments | robot-predicted | in situ (VR) | rationale | local + global |
| CE-MRS / VeriPlan | text, table | robot-predicted | detached | constraint | local |
| **CoGround** | whole-scene outcome diff | robot-predicted | in situ | object / action / rule | local |

Outcome-state views so far are user-authored (no interpretation gap can arise); robot-predicted views are process-based. The empty cell is "nobody built it" only.

## What to investigate next (ranked)
1. **Crossover experiment**, same medium, information parity: representation (After-diff / process playback / both) × seeded defect type (three concepts; sub-types omission, commission, side effect, intermediate-only). DVs: d′, criterion, RT, confidence. Secures claim 1 independent of AR.
2. **Build request-anchored fulfilment marking**; test omission detection with and without it.
3. **"On demand" vs "on exception"**: push process detail when an intermediate violation or side effect exists; compare with pull.
4. **Publish the design space** after reading Walker 2023, MARCER, "Uncertain Pointer" (CHI'26) [A, unread].
5. AR vs 2D only as a secondary factor.

## Biggest risk
The planner is rule-based (SYSTEM_OVERVIEW, skimmed). If users author the rules, Goal Satisfaction collapses into rule verification, the "whose goal" axis blurs, and CoGround reads as X-OOHRI + SHRIMP + ImageInThat integrated. With AR nulls (Sibirtseva, Qu 2026 [A]) no claim remains.

## Questions to the other debaters
1. Empiricist: can omission and intermediate-only defects be seeded at matched salience across conditions?
2. Systems: can the planner emit a per-request fulfilment record and side effects?
3. AR advocate: which hiding case does in-situ rendering fix that a parity-matched 2D diff does not?
4. Sceptic: did I mis-code any robot-predicted whole-scene outcome preview as process-based (MARCER?)
