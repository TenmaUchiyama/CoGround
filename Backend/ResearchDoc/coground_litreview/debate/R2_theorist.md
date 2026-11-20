# R2 — Theorist rebuttal

## 1. Concessions
- Reviewer and Empiricist: the paper is empirical; my design space is a discussion-section frame, not the headline.
- "Outcome-level grounding" (my claim 3) is dropped as a novelty claim. FORTNIoT and He & Lim (Skeptic [W]) occupy it.
- AR vs 2D is secondary. Skeptic's Kim et al. evidence supports my omission point better than my unverified change-blindness citation.

## 2. Rebuttals
**Empiricist's rule ("the diff marks what changes, never what is unmet").** Right about the verdict, wrong as stated. Three layers must be separated: (a) change diff, (b) *scope*: which objects the request was interpreted to cover, (c) verdict (unmet). Showing (b) is not answer leakage; it externalises the interpreted goal. Without it an omission leaves no visual trace and S1 is biased against State.
Second, goal defects split by planner knowledge. *Planner-known* shortfalls (rule-blocked) should simply be told to the user. *Planner-unknown* shortfalls (the plan satisfies the robot's reading, not the user's) are the only ones needing human judgment. S1 must seed and report both separately.

**Skeptic: "no Task Interpretation with a rule planner."** Incorrect for the built system. `grounding_server/README.md` (read this round) documents `rules.compile`, `norms.compile` and `task.request` with `interpret: true`: an LLM turns language into rules, norms and target objects, with `pending`/`unresolved` states. The planner is deterministic; its inputs are interpreted. This also weakens my R1 risk: rules are user-uttered but robot-interpreted.

## 3. Answers
- Skeptic Q1 / Advocate Q2: a static After should beat playback only on end-state-observable defects (congruence, Tversky 2002), and only with scope marking. Otherwise I predict a null.
- Empiricist Q2: with verdict marking the user reads, not judges; evaluate that as calibration (reliance when the verdict is wrong), not detection.
- Advocate Q3: at scale, aggregate by request clause, not plan step. Untested.
- Reviewer Q4: a norm differs from a precondition only if it is user-uttered and can be misinterpreted.

## 4. The one contribution
*An interpretation error is invisible in the plan and visible only in its consequences. We show that a robot-predicted end state, marked with the scope the robot attributed to the request, lets users catch errors the planner cannot know about, and we identify the defect classes where an end state hides the problem and process must be pushed.*

**Push process detail when:** (i) an intermediate state violates a norm the final state satisfies; (ii) the plan moves objects outside the interpreted scope; (iii) the norm is temporal or path-based, not a state predicate; (iv) interpretation was pending or unresolved; (v) feasibility margin is low.
**Falsified if** process-first matches outcome-first on end-state defects, or pull-only users do not miss (i)–(iii).

## 5. Final ranking
Claims: (1) representation × defect-type interaction, with the planner-known/unknown split; (2) scope-marked After state as the display of interpretation; (3) push conditions for process detail.
Investigations: (1) Empiricist's S1 plus scope marking and the known/unknown split; (2) pull vs push on (i)–(iii); (3) build the After view; read MARCER.

## 6. Vote
**Empirical state-vs-process**, with the design space as discussion.
