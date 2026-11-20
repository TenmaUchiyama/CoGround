# R1 — Skeptic / prior-art attacker

Verification marks: [A] = documented in agent files; [W] = found in my own web search (14 queries), abstract/snippet level only unless stated.

## Stance summary
- CoGround's pipeline (AR twins at goal poses → flag problem → explain → locally repair → replan) is a recombination of X-OOHRI + GhostObjects + Polaris + VeriPlan/CE-MRS; no single stage is new.
- The one unbuilt piece (whole-scene robot-predicted After vs Before, with diminished reality) is an untested display variant whose nearest evidence is null or negative (PerceptTwin, Polaris, Taylor 2020).
- Any defensible novelty is therefore empirical, not system-level, and does not exist until a parity-controlled study is run.

## Novelty claims ranked (by how well they survive attack)

| # | Claim | Type | Closest threat | Strength |
|---|---|---|---|---|
| 1 | Objective speed/accuracy of judging *degree* of goal fulfilment from a spatial Before/After, AR vs 2D with information parity | empirical | PerceptTwin [A] (N=93, final-state errors n.s.), Rosen 2019 [A] (feasibility only, handicapped baseline), Sukkerd 2020 [A] (non-spatial), FORTNIoT [W] (IMWUT 2020, N=42: predicted future home states improved accuracy of understanding; not spatial, not robot) | **Med** — nobody tested it; I could not knock it down |
| 2 | Diminished reality to hide objects the plan will move | interaction | Remixed Reality [A] (erase/move real objects, CHI'18); Kari et al. "Scene Responsiveness" [W] (UIST'23; virtualised real objects appear moved — Kari co-authors X-OOHRI; mechanism not confirmed by me); DR furniture replacement [W] (Siltanen ISMAR'14; Purdue 2018 thesis reporting a *reversed* user effect, snippet only); Taylor 2020 [A] (DR hurt efficiency/preference) | **Med-Low** as technique; "not yet in a robot plan preview" is a domain transfer |
| 3 | Glance-first outcome, plan on demand | design-knowledge | MRPilot [A] (Mini-Map overview + situated view; local vs global repair); glanceable-AR literature [A]; Polaris timeline [A] | **Low-Med** — survives only if glanceability is measured objectively (B1 found no such study) |
| 4 | Explanations linked to *household rules* plus local rule repair | interaction | VeriPlan [A] (rule violations + flexibility sliders), CE-MRS [A] (why-not + spec repair, 62.7% vs 29.5%), Eifler [A], RoboCritics [A]; X-OOHRI tags [A] | **Low** — swapping capability limits for user rules is a content change |
| 5 | In-situ AR After state of robot-moved objects | system | GhostObjects [A] ("visualize anticipated outcomes"), X-OOHRI [A], Previewed Reality [A], Wang 2023 [A], Hernández et al. RA-L 2020 [W, abstract verified] (AR goal specs, preview/approve/modify), ARDIE [W] (arXiv 2023 preprint, "visualize future object interactions"; evaluation unverified) | **Low** |
| 6 | Separating Interpretation / Feasibility / Goal Satisfaction | design-knowledge | PerceptTwin's consistency-vs-logic split [A]; Endsley/SAT levels [A] | **Low** as a concept; usable only as an evaluation factor |
| 7 | The integrated pipeline | system | X-OOHRI (E3/R3, same Quest + twins stack) | **Low** — "X-OOHRI with a planner" |

Concept separation: claims 1–3, 5 concern **Goal Satisfaction**; claim 4 **Plan Feasibility**/rule compliance; **Task Interpretation** is currently unaddressed by CoGround — with a rule-based planner there is no interpretation ambiguity to reveal, unlike MARCER/MRPilot/SHRIMP.

Additional [W] context: He & Lim (CHI'26 workshop, arXiv 2603.11677) already frame "simulation-in-the-loop" outcome preview for LLM agents as a paradigm (perspective paper, no study). Kim, Han & Cho (arXiv 2308.12476) show change detection in AR is disruption- and change-type dependent (removals easier than colour/size) — a direct warning that a DR "After" may hide the very changes it should expose.

## What I could NOT knock down
1. No verified paper renders a **robot-predicted, whole-scene After state in situ juxtaposed with Before** for multi-object household tasks. My 14 searches (AR goal/end-state preview, DR future previews, interior-design DR, smart-home what-if, LLM-agent previews) found no counterexample. This is "nobody built it", not "it works".
2. No study measures **graded goal-fulfilment judgment** (speed, accuracy, calibration) over spatial outcomes, nor AR-vs-2D at information parity for it.
3. No study measures **repair performance after an AR-detected goal discrepancy** (Gadre and Wozniak are only near).
4. DR applied to plan-affected objects in HRI: no counterexample found (X-OOHRI full text not re-read by me; PDF fetch failed).

## What to investigate next (ranked)
1. **Parity-controlled study**: in-situ Before/After (±DR) vs 2D before/after images (ImageInThat-style) vs plan-arc/timeline (Polaris-style), seeded errors of three types (interpretation, feasibility, goal). DVs: d′, RT, calibration, TLX. Pre-register; a null is likely and publishable.
2. **Attack PerceptTwin's null directly**: show that a static After diff beats simulated playback specifically for final-state errors. This is the single result that would convert claim 1 to High.
3. **DR ablation**: After-with-DR vs ghost-only vs arcs, measuring missed changes (change blindness) and scaling with number of moved objects (3/8/15).
4. **Glance test**: exposure-limited (e.g., 2 s/5 s) judgment accuracy, then on-demand drill-down usage logs — otherwise the motto is unfalsifiable.
5. **Repair DVs** from CE-MRS/Das: fraction of seeded errors resolved, extraneous edits, time-to-fix.
6. Read in full: X-OOHRI, MARCER, Diehl 2020, ARDIE, Kari 2023.

## Biggest risk
The current build (rule-based planner, ghost objects, "object → destination" arcs with labels, simulated Fetch) is, to a reviewer, TidyBot-style rules + GhostObjects + X-OOHRI repair. If the study then reproduces PerceptTwin/Polaris/SHRIMP — outcome preview does not improve goal-error detection, and exploration raises workload — the paper has neither system nor empirical novelty. A weak chat/text baseline (MRPilot, ImageInThat pattern) would not rescue it.

## Questions to the other debaters
1. Why would a static in-situ After succeed on final-state errors where PerceptTwin's full simulation video did not?
2. With a deterministic rule planner, what Task Interpretation error can CoGround even display?
3. What does DR add over GhostObjects-style twins plus arcs, given Taylor 2020 and AR change-blindness evidence?
4. Which baseline will you accept as information-equivalent, and will you publish a null?
5. Is "household rule" explanation more than VeriPlan's rule-violation view re-skinned in AR?
