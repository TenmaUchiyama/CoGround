# R1 — Advocate (interaction & system design)

## Stance summary

- CoGround's defensible novelty is an **interaction pattern**, not a component: auditing a *robot-predicted, whole-scene After state* in situ as the first and default view, with plan, cause and repair disclosed only on demand.
- Every component has a precedent. What no verified system has is the *direction* (robot proposes, user audits the outcome), the *unit* (whole scene, not per object or per step) and the *entry point* (outcome first, plan second).
- This is a "nobody built it" claim only. Nobody has tested it either, and the nearest tests of outcome previews (PerceptTwin, Polaris, SHRIMP) are null or marginal.

## Novelty claims ranked

| # | Claim | Type | Closest threat | Why it survives (or not) | Strength |
|---|---|---|---|---|---|
| 1 | Goal Satisfaction is judged from an in-situ, juxtaposed Before/After of the robot-predicted whole-scene end state. | interaction | X-OOHRI and GhostObjects (life-size twins at target poses); Wang 2023 (avatar runs the plan on holographic twins); Previewed Reality (simulator-predicted object states in situ) | In X-OOHRI and GhostObjects the *user* authors the goal one object at a time, so there is nothing to audit. Wang 2023 and Previewed Reality are robot-predicted but play a process, not a static end state compared with the present; neither has a study. A2 found no verified whole-scene Before/After. | High |
| 2 | Outcome-first progressive disclosure: the After state is the default, and the plan's intermediate states appear only when the user asks. | interaction / design-knowledge | MRPilot (mini-map overview plus situated view); Polaris (timeline of world states); SHRIMP (step-through simulation) | All three are plan-first: the user reads steps, paths or commitments to infer the outcome. MRPilot does not render object end states at all. But "overview then detail" is a generic principle; the claim holds only if the layering is shown to matter. | Med |
| 3 | Diminished reality hides objects the plan will move, so the After view is a clean scene instead of ghosts overlaid on the originals. | interaction (technique) | Remixed Reality (erase and move real objects, no robot); Taylor 2020 (DR hides the robot arm; unverified) | No verified robot work diminishes plan-affected objects, but the technique is borrowed and Taylor's DR result was mixed. | Med |
| 4 | Unfulfilled parts of the After state link to a cause at object, action or *household-rule* level, in situ. | interaction / system | X-OOHRI (explanation tags, score E3); VeriPlan (violated-rule list); RoboCritics | X-OOHRI explains robot capability limits only. VeriPlan links to user rules but is non-spatial and not a robot. A user-defined rule anchored to the object in the scene is unoccupied, but it is a recombination. | Med |
| 5 | Local repair (target, action or rule) from within the outcome view, with replanning that refreshes the After state. | system | X-OOHRI (Auto / Alternative, R3); MRPilot (field-level edits, R3); CE-MRS; SHRIMP | **Conceded.** Well covered; only the entry point (an outcome discrepancy) differs. | Low |
| 6 | The interface keeps Task Interpretation, Plan Feasibility and Goal Satisfaction visually distinct. | design-knowledge | PerceptTwin (separates "consistency" from "logic" in its evaluation only) | No interface exposes the split to the user. It is currently a framing, not a built feature. | Low–Med |

**Conceded as not new:** pre-execution AR preview (Rosen 2019); life-size object twins (GhostObjects); constraint tags with resolutions (X-OOHRI); local versus global repair (MRPilot); rule verification with replanning (VeriPlan); state diffs between steps (ImageInThat, 2D and user-authored); tidying-plan preview (Polaris).

## What to investigate next (ranked)

1. **Read MARCER (HRI 2025) in full.** X-OOHRI describes it as using "AR to display virtual outcomes", and all agents left it unverified. If it renders robot-predicted object end states, Claim 1 drops to Med.
2. **Confirm what is actually built.** The system overview I read documents a rule-based planner (one step per object), Ghost objects and plan display. I found no mention there of Before/After, DR, cause links or repair, so Claims 1–4 are design claims until implemented.
3. **Build the After view in three renderings** (ghost overlay; DR plus relocated twins; A/B toggle) and compare them. This secures Claim 3.
4. **Test outcome-first against plan-first with identical information**, in AR and on a 2D screen. DVs: accuracy and d′ of the fulfilment judgment, time, and *degree* of fulfilment (not binary), with seeded Goal Satisfaction errors kept separate from Feasibility errors. PerceptTwin found no significant gain here, so a positive result would be the paper.
5. **Make household rules first-class objects in the scene**: a violated rule anchored to the object it blocks, editable as hard or soft (cf. VeriPlan sliders). Measure fraction of errors resolved and extraneous edits (CE-MRS metrics).
6. **Measure the glance**: exposure-limited judgment. B1 found no objective glanceability measure for robot outcome displays.

## Biggest risk

A static After state may not help. PerceptTwin's simulation preview did not significantly improve detection of wrong final states; Polaris's expectation match was marginal (p≈.08); SHRIMP raised workload without improving success. If the outcome view shows *what* without marking *what is unmet*, CoGround becomes "X-OOHRI plus a planner" and reviewers will read it as integration.

## Questions to the other debaters

1. Sceptic: is "robot-predicted versus user-authored goal state" a real interaction difference, or would X-OOHRI's Auto-resolve preview already count as auditing a robot proposal?
2. Empiricist: given PerceptTwin's null on final-state errors, what explicit discrepancy marking would you require before an outcome view is worth testing?
3. Anyone: does a whole-scene After remain glanceable beyond roughly ten moved objects, or does it need aggregation that reintroduces a plan-like summary?
