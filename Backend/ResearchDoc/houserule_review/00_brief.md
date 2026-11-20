# House-Rule Novelty Review — shared brief for all agents

Spec (authoritative, read fully): /home/fetch_tbd_lab/tenma/CoGround/Backend/ResearchDoc/HouseRule_Research.md
Today: 2026-11-19. No lower year bound.

## What CoGround actually implements (context; do not assume novelty)
grounding_server (/home/fetch_tbd_lab/tenma/CoGround/Backend/grounding_server, README.md §家庭ルールと依頼, coground_server/norms/model.py):
- A resident states house rules in natural language; an LLM compiles them (`norms.compile`) into R = (N, S, T, C), C = (W, φ):
  N norm = obligation / prohibition / permission; S scope = when (home clock time, requester, state such as near_child);
  T target = which objects/regions via attribute predicates (e.g. fragile = true, category = plate); W window = which part of plan/execution to check (whole / at_contact / during_base_motion / at_place_complete); φ predicate (contact, placed_in, ...).
  Rules whose scope/region cannot be resolved from words go to `pending` and are not used until the user confirms (no silent completion).
- Exceptions (`exception_of`: permission overriding a prohibition, e.g. "only when I ask"), corrections of scope / attributes / zones, with diff of what changed.
- Later a separate request ("片づけて", `task.request`) fixes the target objects; for each object the server judges destination (obligation) and graspability (prohibition) and makes a plan. Objects that cannot be handled become `deferred` steps with a human-readable reason — the feasible part of the request is executed.
- Verdicts are 3-valued + undetermined: violated / compliant / not_applicable / undetermined (with `missing` facts, e.g. attr:fragile unknown → hold). basis = predicted (on the plan) or observed.
- Object attributes come from the scene (Unity / perception); residents can correct attributes.
- AR (Quest) preview of the plan with reasons (see the earlier review in ../coground_litreview/debate/DEBATE_REPORT.md for the AR-side novelty discussion — not the focus here).

## Claims to test (from the spec)
A. Apply a taught rule to other objects (new instances).
B. Match stored rules against a later, independent request; select relevant rules; change the behaviour on target objects.
C. Decomposing rules into target / applicability condition / normative directive helps judgement on untaught combinations (judge "method precedence" and "evidence of effect" separately).
D. Reflecting household-specific rule differences while completing the feasible part of a broad request (same scene, same instruction, different house rules; measure both avoidance of forbidden objects and completion of permitted ones).

## Comparison-table row format (one row = paper × experimental condition)
| Paper (URL) | Condition/demo | Evidence location (§/Fig/Table) | Rule origin (resident explicit / inferred from examples / designer / commonsense) | Rule representation (raw text / decomposed target-condition-action-deontic; who decomposes) | Novelty unit (unseen instance / unseen category / new attribute×action combination / unseen household/scene; vs foundation-model pretraining) | Perception input (GT names/attrs / estimated from images / from human teaching; unknown-attribute handling) | Instruction matching (single constrained instruction vs reuse of earlier rules for a different request; scene-level rule retrieval vs per-object/per-action applicability) | Decision & evidence (manipulation choice / action prohibition / partial execution / asking; concept / implementation / qualitative demo / controlled quantitative eval) | Match with claims A–D | Differences |
Write "未確認 (unverified)" for any cell you could not confirm in the original text. Separate demos of one paper are separate rows; never merge them into a single proof.

## Rules
- Verify in the original (arXiv abs/HTML/PDF, ACM DL, IEEE Xplore, proceedings, author PDFs). Never invent titles, authors, venues, numbers. Mark verified true/false per paper.
- Record search log: date, database, query, inclusion/exclusion reason.
- Hunt for the STRONGEST refutation of each claim from your area. Do backward/forward citation chasing on direct competitors (Semantic Scholar API may rate-limit; fall back to arXiv listing / Google Scholar "cited by" via web search / OpenAlex https://api.openalex.org/works?search=...).
- Also note different names for the same idea (e.g., deontic constraints, normative reasoning, social norms, contextual integrity, preference-conditioned rearrangement, safety constraints, LTL constraints, "personalized rules", "instructable agent").

## Output file sections
1. Search log  2. Comparison table (rows as above)  3. Per-claim verdict from your area: A/B/C/D → 既出 (already done) / 差分候補 (difference candidate) / 証拠不足 (insufficient evidence), with the deciding papers  4. Top-3 strongest counterexamples with why  5. Papers another agent should re-read  6. What remains unverified.
