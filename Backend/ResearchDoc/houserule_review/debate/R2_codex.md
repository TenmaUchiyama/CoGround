**Round 2 ruling**

The Advocate overclaims an unmeasured win. The Skeptic’s “nobody built it” exceeds the search evidence, and a baseline estimate inside CoGround’s confidence interval does not establish equivalence. The Reviewer shows how prior components could reproduce the behavior. That leaves equivalence to be tested. A trigger baseline stripped of exceptions also confounds representation with expressivity. The Skeptic corrected my treatment of the decomposition evidence as too sparse. The Reviewer corrected my baseline design by giving raw-text arms a skip/ask option.

**Decisive test.** Give one cleanup request with A missing a rule-relevant mark, B known permitted, and C known forbidden. B must finish before any reply, C must remain untouched, and the system must ask specifically for A’s mark. Supply a permitting answer and check that only A resumes. Replay with the rule’s scope false for A and require A to proceed without asking. Compare against RuleGraph with one chunk per object and matched facts, semantics, and execution permissions. If it reproduces these observable behaviors, object-level chunking plus the matched checker accounts for the claimed distinction.

**Decomposition.** RuleBench favors NL over FOL in most cases and reports a counterfactual drop. ShieldAgent reports +10.2% accuracy over complete-policy prompting, with action-relevant policy selection bundled into the comparison. Test whether decomposition improves applicability and joint success on held-out target × condition × action combinations against retrieved text and an expressivity-matched trigger baseline. Match rule access and enforcement, and report compilation errors separately.

**Marks and abstention.** With a ground-truth `mark` and an unconditional ban, applicability reduces to equality. Keep that case as a rule-adherence control. Counterbalance marks across objects and test held-out combinations with scope, exceptions, and relevant missing facts. Report perceived marks separately. Give raw-text arms the same per-object skip/ask interface, answer access, and question budget. Score pre-answer progress and post-answer completion separately.

**Top three**

1. **Paired household swap with joint scoring — evaluation, candidate novelty, unrun.**
2. **Selective deferral with named missing facts — system, implemented as reported, distinctiveness unresolved.**
3. **Decomposition improves held-out applicability and joint success — method effect, open hypothesis.**

“We specify a paired household-swap benchmark that fixes the scene and request, varies resident-taught rules, and jointly scores forbidden-contact avoidance and permitted-object completion.”

Withdraw benchmark novelty if verified prior work already combines those elements. Withdraw system distinctiveness if the matched chunk baseline passes the behavioral test. Claim a decomposition advantage only if paired confidence bounds clear preregistered minimum gains on both outcomes against both matched baselines. Scope any oracle-only gain to oracle inputs.

**Vote: evaluation benchmark.**