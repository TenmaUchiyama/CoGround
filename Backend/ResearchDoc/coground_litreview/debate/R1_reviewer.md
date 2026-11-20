# R1 — Senior PC Reviewer (CHI / UIST / HRI)

## Stance summary
- As a system, CoGround is a recombination and would be rejected today; every component has a 2024–2026 precedent.
- The defensible gap is empirical: nobody has tested, with information parity, whether an outcome-first Before/After view improves goal-satisfaction judgment. The closest tests are null (PerceptTwin "logic" errors) or marginal (Polaris).
- Submit one question-driven study paper to HRI, with the system as apparatus. Claim no "first" and no "AR is better".

## Mock reviews: top 3 rejection reasons per submission type
| Submission | R1 | R2 | R3 |
|---|---|---|---|
| (a) Systems, UIST/CHI | Incremental: X-OOHRI/GhostObjects already give Quest twins at target poses, constraint tags, local resolution and preview; MRPilot gives MR pre-execution review with local/global repair; SHRIMP (UIST'26) gives preview plus edit | Thin technical depth: deterministic rule planner, ground-truth scene, kinematic fake execution, so the After state is trivially known | X-OOHRI's excuse for an exploratory N=14 study ("no comparable systems exist") is no longer available |
| (b) Empirical, HRI | Handicapped baseline, as in Rosen 2019 (degraded monitor), MRPilot (chat), ImageInThat (step-wise text) | Contrary evidence ignored: PerceptTwin, Polaris, SHRIMP (higher TLX, no success gain), CE-MRS (no correctness gain), Sibirtseva 2018 (HMD most errors) | Ecological validity: seeded defects, simulated robot, student sample |
| (c) Combined | Neither half is deep | Confounded contribution: AR vs After-state vs explanation vs repair | Overclaiming |

## Novelty claims ranked
| Claim | Type | Closest threat | Strength |
|---|---|---|---|
| Outcome-first (After-state) preview changes accuracy/speed of goal-satisfaction judgment vs process-first playback, per error type | empirical | PerceptTwin (video; logic n.s.), Polaris (p≈.08), Sukkerd 2020 (text) | **High**; untested, and publishable even if null |
| Parity-matched AR vs 2D on a task-level After-state judgment | empirical | Rosen 2019, Sibirtseva 2018 | Med-High |
| Glance-then-drill-down reduces the inspection cost that SHRIMP exposed | design-knowledge | SHRIMP, MRPilot (situated view plus Mini-Map) | Med |
| Cause linked to household norm, followed by local repair and replan, with repair measured | interaction | VeriPlan (rules, sliders), X-OOHRI (tags), CE-MRS (62.7% vs 29.5% resolved) | Low-Med |
| Diminished reality to hide objects that will move | interaction | Remixed Reality; Taylor 2020 (DR hurt efficiency) | Low; only a study factor |
| Integrated pipeline | system | X-OOHRI, MRPilot, SHRIMP | **Low** |

**Delta sentence that survives:** "Prior systems preview robot plans as processes (timelines, playback, paths) and report subjective transparency; we test whether a robot-predicted After state, shown against the current scene, lets users judge more accurately and faster how far a request will be fulfilled, separately for interpretation, feasibility and goal-satisfaction errors, and whether norm-linked explanations turn detection into successful repair."

**Claims to avoid:** "first to preview robot plans in AR"; "first Before/After"; "AR is better"; "LLM-powered robot"; "explanations improve understanding" (CE-MRS and VizXP show understanding and repair dissociate); "household deployment". Cite MRPilot as a preprint. Give Rosen's numbers with the version (arXiv 16%/62%, IJRR 15%/38%).

## Scope reviewers will and will not require
- **LLM planner: not required.** A deterministic planner gives controlled, reproducible seeded defects. The existing LLM front-end (language to rules, norms and task targets) is enough to motivate interpretation errors. Do not call the planner LLM-based.
- **Real-robot execution: not required for the judgment study.** Rosen kept the robot static; MRPilot used VR; PerceptTwin used online videos. The current build is kinematic simulation with fake MoveIt execution, and the paper must say so. An HRI reviewer will still ask for a physical-space session and a video of a real Fetch executing one approved plan.
- **Real household: not required.** A lab room with real furniture and 8–12 objects is sufficient. Ground-truth scene state is acceptable if declared; show registration error.

## What to investigate next (ranked)
1. **Build what the claim needs.** The current AR view draws object-to-destination arcs and ghost-robot playback, which is the process view the paper argues against. Per SYSTEM_OVERVIEW.md (Unity code not inspected), the After-state rendering, fulfilment summary, in-headset reason display and in-headset repair are not there yet; planning is triggered from a Web UI.
2. **Core study**, within-subjects, N≈24–32, counterbalanced: After-state vs process preview (the MRPilot/SHRIMP-style baseline) × AR vs parity-matched 2D rendered from the same scene graph, plus a text plan list. Half the plans carry seeded defects of the three types. DVs: d′, criterion, decision time, fulfilment-degree error, confidence calibration, TLX.
3. **Glance test:** 3–5 s exposure vs unlimited, with drill-down logs.
4. **Repair study:** norm-linked cause vs none; cause-identification F1 (Das 2021), repair success, time, extraneous edits (CE-MRS).
5. **Read in full** X-OOHRI, MARCER and Diehl 2020, whose evaluations remain partly unverified.
6. DR ablation, only if time allows.

**Minimum evidence for acceptance:** items 1–2 with a fair baseline and effects reported per error type, plus either item 3 or 4. A null result on goal-satisfaction errors is still a contribution if the study is powered and pre-registered.

**Recommended framing and venue:** an empirical paper at HRI (CHI as the alternative), titled around the question rather than the system. UIST only if a real technical novelty emerges; I see none now.

## Biggest risk
The After-state view does not beat a well-built process preview, or a parity-matched 2D view matches AR. PerceptTwin, SHRIMP and Sibirtseva make this plausible. A system-first paper dies on that result; a question-first paper survives it.

## Questions to the other debaters
1. Which single DV is the headline, and what effect size have you assumed?
2. If AR equals 2D under parity, what remains of the contribution?
3. Can anyone name a technical novelty that survives X-OOHRI plus MRPilot?
4. Is "household norm" operationally different from VeriPlan's rules or X-OOHRI's preconditions for a participant?
5. How are defects seeded so salience is matched across the three error types?
