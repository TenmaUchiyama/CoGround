# CoGround Literature Review — Shared Brief for All Agents

## Target system (CoGround)
AR interaction system for users who delegated a task to a semi-autonomous HOUSEHOLD robot (object manipulation, e.g. tidying).
BEFORE execution, the user checks the robot's plan result:
- Spatial Before (current) vs predicted After (post-execution) environment state, shown in situ (AR; possibly diminished reality to hide objects that will move).
- Design motto: "Understand the outcome at a glance. Explore the plan only when needed."
- Goal: user judges quickly/accurately/intuitively/low-load how far the requested task will be fulfilled.
- If parts are unfulfilled / plan problems exist: user can inspect intermediate plan states on demand, understand the cause (linked to object / action / constraint, e.g. household rules), and locally repair (change target, action, constraint) → replan.
- Execution-time progress monitoring is OUT of core scope (record as adjacent only).

## Hard rules
1. Do NOT restrict search to AR (2D GUIs, language, simulation previews, digital twins count).
2. Do NOT conclude easily that "nothing similar exists". Actively hunt for the closest work.
3. Separate what a paper IMPLEMENTS from what it EMPIRICALLY SHOWS.
4. Mark anything you could not confirm from the original paper page/abstract/PDF as `verified: false`. Never invent DOIs, authors, venues or numbers. If unsure, say so.
5. Do not assume CoGround is novel or AR is superior. Record negative/contrary AR results.
6. Concepts to keep separate per paper: **Task Interpretation** (how robot interpreted the request), **Plan Feasibility** (plan executable under constraints), **Goal Satisfaction** (predicted outcome satisfies user's desired state).

## Similarity axes (score 0–3, or NR = not reported; NR ≠ 0)
Purpose (help user understand goal fulfillment) · Timing (pre-execution preview) · Outcome Representation (predicted After state of environment) · Discrepancy Detection (intended vs predicted) · Explanation (cause linked to object/action/constraint) · Repair (local targeted modification) · Evaluation (speed/accuracy/load/repair performance measured)
0 not addressed · 1 conceptually related · 2 partially overlapping · 3 strongly overlapping

## Classification
Direct Match · Strongly Related · Partially Related · Methodologically Relevant · Background

## Search venues
ACM DL, IEEE Xplore, Google Scholar, Semantic Scholar, arXiv (flag preprint), HRI, CHI, UIST, ISMAR, VAM-HRI workshop, ICRA, IROS, RO-MAN, CoRL, THRI, IJCAI/AAAI/ICAPS (explainable planning). Years 2010–2026 (+ classics).
Do snowballing (backward & forward) from the strongest hits, and concept expansion (e.g. goal satisfaction → task completion / outcome prediction / success detection; plan repair → negotiation / correction / replanning; Before/After → future-state preview / anticipated outcome / digital twin / simulation preview; understanding → transparency / mental model accuracy / SA).
Also look at recent LLM-based robot planning works that show the plan to users for confirmation/correction before execution (2023–2026).

## Output (write to the file path you are given)
1. `## Search log` — queries used, sources, snowballing steps (brief).
2. `## Papers` — one block per paper:
```
### <short id e.g. Walker2018>
- Title / Authors / Year / Venue / DOI or URL
- verified: true|false (did you see the original abstract/page?) ; peer_reviewed: true|false
- Class: <classification>
- Concepts: Interpretation / Feasibility / GoalSatisfaction (which ones)
- What they do (implemented):
- What they evaluate (study design, N, conditions, DVs, main results incl. numbers if available):
- Overlap with CoGround:
- Differences:
- Scores: Purpose x | Timing x | Outcome x | Discrepancy x | Explanation x | Repair x | Evaluation x
- Notes / evidence quote or location in paper:
```
3. `## Agent summary` — top 5 closest works, key gaps, open doubts, and papers you think another agent should cross-check.

Aim for depth over breadth: ~15–30 well-documented papers is better than 60 shallow ones. Prioritize the closest works.
