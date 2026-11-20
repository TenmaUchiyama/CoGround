# R2 — Skeptic

## 1. Threat verification
- **MARCER (HRI'25) — full text read (NSF PAR manuscript). Threat confirmed in part.** Fig. 2(d): after approval "users can preview actions via AR digital twins showing the current, future, and final states of relevant objects, and simulated robot movements." The plan is LLM-generated from speech, so this is a *robot-predicted object end state, in situ, pre-execution*. Limits: shown per rule for relevant objects together with motion playback; no static whole-scene Before/After, no discrepancy marking, no cause display (authors: it "fell short in communicating system failures"). Study: N=15, no baseline, task completion (10/15 finished all three), SUS 70.83; no judgment-accuracy measure. One participant's rule left "no space for the final object" and was not debugged — an undetected goal-level error despite the preview.
- **X-OOHRI — full PDF read.** No diminished reality: real objects stay visible; participants themselves suggested "graying out moved real objects" (P6). No whole-scene end state. Auto resolution: the system proposes moving *other* objects, plays a preview, user confirms. Exploratory N=14, no baseline.
- **Hernández RA-L 2020 — full PDF read.** User places virtual objects as goals (multi-object, sequenced); the preview is robot *motion* only; approve / recompute / abort. No user study (stated as future work).
- **Diehl RO-MAN 2020 — abstract only.** Three AR designs vs RViz, N=18, error detection of a learned behaviour. Results **not verified**.
- **FORTNIoT — not re-verified** (repository returned 503). Snippet only: IMWUT 2020, between-subjects N=42, more accurate understanding of future behaviour. Design details unknown.

## 2. Concessions
- The state-vs-process × defect-type crossover is untested in HRI; I accept it as the strongest claim.
- Graded fulfilment judgment with d′/calibration is a defensible measurement contribution.
- DR of plan-affected objects is unbuilt in HRI (X-OOHRI participants asked for it). Defensible only as a study factor.

## 3. Rebuttals
- **Advocate claim 1 "High" → Med.** MARCER already shows robot-predicted final object states in situ. What remains is narrower: *static, whole-scene, juxtaposed, default* view.
- **Theorist's empty cell is not empty.** MARCER belongs in "robot-predicted × object outcome × in situ" (process and state mixed). The design-space table must be recoded; the residual cell is "state-only + discrepancy marking + cause link".
- **Crossover is untested but not theoretically new.** Tversky et al. 2002 (congruence; checked at citation/snippet level) predicts it; Höffler & Leutner 2007 found a small animation advantage (d≈0.37), and Ploetzner 2020 that animation helps when the change itself is what must be learned. All are learning studies, not verification of an agent's plan, so they set priors rather than pre-empt. Expect a small effect; Empiricist's dz≈0.5 is optimistic. Also unchecked [memory]: Gleicher 2011 (juxtaposition/superposition/explicit encoding) and Robertson 2008 (animation vs small multiples) — cite before claiming a new design axis.
- **Reviewer's 2×2 at N≈24–32** is underpowered for an interaction per error type.
- Theorist's omission point stands and cuts against everyone: a diff cannot show what did not move.

## 4. Answers
- **Advocate:** yes, X-OOHRI's Auto-resolve preview is auditing a robot proposal, but a local, feasibility-level one. "Robot proposes, user audits" is therefore not a new direction (also MARCER, SHRIMP, MRPilot). Only the *unit* (whole-scene goal satisfaction) survives.
- **Theorist:** yes — MARCER was mis-coded/omitted. PerceptTwin and SHRIMP playbacks also end on a final state, so "process" views contain the After frame; the manipulated factor is really *static, juxtaposed and exposure-controlled* vs embedded in playback.

## 5. Final ranking
Claims: (1) representation × defect-type effect on goal-satisfaction judgment; (2) request-anchored fulfilment marking for omissions, with graded judgment measures; (3) rule-linked repair performance after outcome-level detection.
Investigations: (1) crossover study with a MARCER-style playback-with-final-twins baseline, N≥48, pre-registered; (2) omission detection with/without request-anchored marking; (3) glance (fixed exposure) + DR ablation.

## 6. Vote
**Empirical state-vs-process**, system as apparatus. System framing fails against MARCER + X-OOHRI; AR-vs-2D is a secondary factor.
