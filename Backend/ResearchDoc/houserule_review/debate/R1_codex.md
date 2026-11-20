### Stance summary

A and B are established mechanisms, and C’s rule representation has clear precedents.  
D’s household swap is an evaluation candidate. Whether decomposition improves generalization under that swap is a scientific question.  
Per-object deferral with named missing facts has a testable consequence. The supplied evidence establishes neither an equivalent robot evaluation nor a null result.

### Claims table

| Claim | Unit | Closest prior | Status | Strength |
|---|---|---|---|---|
| A. Transfer taught rules to new objects | method | Tan, Video Demonstration, Figs. 1–2. Jain §3, §5.2 establishes attribute-conditioned transfer. | 既出 | H |
| B. Reuse rules on independent requests | method | Tan, Fig. 1 bottom. AgentSpec §3.2, §5.2 checks actions. Wu §III-B, Table I retrieves at scene level, with rule authorship unspecified. | 既出 | H |
| C. Decomposed rule representation | method | AgentSpec §3.2, §5.3. ODRL 2.2 Rule and conflict property. Meneguzzi & Luck §§1–2. ADICO is a structural precedent. | 既出 | H |
| C. Decomposition improves held-out applicability | method | Safety Chip Table I compares LTL with text. RuleGraph §4.6, Table 4 ablates per-rule verification. I2 confirms VIMA §3 holds out texture–object combinations. | 証拠不足 | H |
| D. Partial completion | system | RuleGraph §4.1, Table 1 measures joint success on simulated instruction chunks. | 既出 | H |
| D. Paired household swap with joint completion | evaluation | RuleGraph Table 1 and PARSEC §§IV, VI, Table II cover complementary axes. PARSEC’s identical object sets are unverified. | 差分候補 | M |
| Per-object hold with named missing facts and continued execution | system | SafeGate §IV, Stage 3 defers whole commands. VFM §3, App. A.1 merges inapplicable and undeterminable. | 差分候補 | M |
| Resident confirmation and scope edits with visible diffs | HRI | AgentSpec §1 anticipates user review. Safety Chip §III-C uses expert verification. | 差分候補 | L |

### What to investigate/build/measure

1. **Randomize the household policy.** Replay identical scenes and later requests with opposite star/circle prohibitions. Counterbalance marks across material, hazard, position and placement difficulty. Use opaque object IDs and fresh sessions. Supply marks only through explicit ground-truth attributes or a shared perception pipeline. Include a rule-blind control and a separate fragility condition. Score zero forbidden contacts **and** correct completion of every permitted object, then require both households to pass. Report violation and completion rates separately.

2. **Isolate decomposition.** Hold out target × condition × action triples while exposing their constituent elements during teaching. Include scope matches and misses. Compare full raw text, retrieved raw text, AgentSpec-like trigger/check/enforce, and CoGround. Hold facts, candidate actions and execution policy fixed. Give all matchers the same oracle shortlist for the applicability comparison, then evaluate retrieval separately. Cross text and fields with the same judge to isolate representation from executor changes. Use oracle and compiled rules to expose compilation errors. Score rule applicability per object and candidate action before defaults run. Compare expressible cases across all arms and test richer cases against a trigger baseline with equivalent semantics.

3. **Specify and test the semantics.** [own knowledge, unverified] ABAC-style predicates can encode scope and target, defeasible priority can encode linked permissions, and runtime verification can check selected trace segments. Strong Kleene evaluation plus an applicability decision and missing-fact provenance can produce the four verdicts. The tuple alone establishes no new logic. Preregister cases where a false scope masks a missing attribute, a relevant unknown holds one object while independent objects proceed, and requester identity changes only the linked prohibition. Replay a plan predicted compliant whose observed trace contains contact inside the forbidden window. Include an incomplete trace to test when a verdict can become final. Measure false acts, false holds and permitted completion under controlled missingness.

4. **Test HRI separately.** Measure resident correction accuracy and teaching effort with and without scope confirmation and diffs.

### Contribution sentence + retraction conditions

**Conditional contribution:** “On held-out rule combinations, explicit rule decomposition improves per-object applicability and joint cleanup success over matched raw-text and trigger–check–enforce baselines in paired trials that vary only resident-taught rules.”

Withdraw the improvement claim if paired confidence bounds fail preregistered minimum gains on either outcome, or if the gains disappear with matched rule access and enforcement. Scope any ground-truth-only gain to ground-truth inputs. Withdraw evaluation novelty if equivalent prior paired evidence is verified.

### Biggest risk

A favorable comparison could measure better retrieval, extra semantics, or fortunate default cleanup while leaving applicability unchanged.

### Questions to other debaters

- Which nearest prior could run the identical household swap with resident rules?
- What trace or requester counterexample would distinguish CoGround from a semantics-matched trigger–check–enforce implementation?