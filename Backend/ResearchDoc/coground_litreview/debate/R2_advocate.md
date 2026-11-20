# R2 — Advocate rebuttal

## 1. Concessions
- **Claim 1 (whole-scene After): High → Med.** "Nobody built it" stands (the Skeptic's 14 searches found no counterexample), but the Reviewer is right that a deterministic planner makes the After state technically trivial, and that today's build draws arcs and ghost playback, i.e. the process view.
- **Claim 3 (DR): Med → Low.** Study factor only.
- **Claim 5 (local repair): dropped. Claim 6 (three-concept split): evaluation factor only.**
- A plain Before/After diff is insufficient; the Theorist's omission point is correct.

## 2. Rebuttals
- **Skeptic, "novelty is empirical only":** the study needs an artefact that the Theorist's design space shows does not exist (robot-predicted × state × in situ). The system is a necessary apparatus contribution, not nothing.
- **Skeptic, "household rules are a content change":** a capability limit cannot be edited; a rule can. That adds a repair path (relax the constraint) X-OOHRI lacks. VeriPlan has it, but non-spatially. Still Low–Med.
- **Empiricist, "the diff must never mark what is unmet":** overreach. Split defects into *planner-known* (rule-blocked, infeasible: mark them; the user judges acceptability and repairs) and *planner-unknown* (interpretation errors: unmarked; the true detection test). Report d′ only on the latter.
- **Reviewer's 2×2 at N≈24–32** conflicts with the Empiricist's N=48 for one factor. Run state-vs-process first.

## 3. Answers
- **Omission problem:** request-anchored fulfilment marking. Every object the request covers gets an in-situ marker whether or not it moves: moved, already satisfied, or *stays: blocked by rule/action*, plus a one-line tally ("7 of 9"). Unmoved-but-requested objects thus become visible. Whether `planner.py` already emits such a per-object record I have not checked.
- **Why static After where PerceptTwin's video failed:** no evidence it will. The hypothesis rests on format congruence (a goal is a predicate over a state), no memory load from transient playback, and juxtaposition with Before. PerceptTwin tested none of these. A null is plausible.
- **Technical novelty surviving X-OOHRI + MRPilot:** none today. The only candidate is the fulfilment ledger rendered on non-moving objects, which is interaction, not technique. I concede the UIST systems framing.
- **DR given change blindness:** DR removes the Before referent and may hide the change. Its only plausible benefit is less clutter from doubled objects at 8–15 items. Offer it as a toggle and test it in the Skeptic's scaling ablation.
- **Interpretation errors with a rule planner:** they would enter where language becomes rules (the Reviewer reports an LLM front-end; I have not verified it).

## 4. Final ranking
**Claims**
1. State versus process representation × defect type for goal-satisfaction judgment (empirical).
2. Robot-predicted whole-scene After with request-anchored fulfilment marking, in situ (interaction).
3. Rule-anchored cause with rule-level repair, measured on repair DVs (interaction, Low–Med).

**Build / investigate**
1. In-headset After view plus fulfilment ledger, cause display and repair.
2. Empiricist's S1 with omission, side-effect and intermediate-only sub-types, and the planner-known/unknown split.
3. Read MARCER, X-OOHRI and Kari 2023 in full.

## 5. Vote
**Empirical, state-vs-process**, with the system as apparatus and the design space as a framing section. AR-vs-2D is a follow-up.
