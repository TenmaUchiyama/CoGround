# House-Rule Novelty Debate — common brief

Base: /home/fetch_tbd_lab/tenma/CoGround/Backend/ResearchDoc/houserule_review
Evidence to read (all): 00_brief.md (claims A–D, what CoGround implements), ../HouseRule_Research.md (spec §5–6: minimum experiments, judgment rules, deliverables),
search/S1_hri_norms.md, S2_perception_household.md, S3_symbolic_planning.md (searchers), search/I1_crossread.md and I2_crossread_codex_verify.md (independent re-reads — these OVERRIDE searcher descriptions where they disagree), codex/C1_recall.md (Codex recall; verified/corrected in I2).

State after search (consensus so far): A 既出 (Tan 2019, TidyBot, RoboGuard, Jain 2013, FLEX?); B 既出 as mechanism (Wu 2611.18026, RoboGuard, AgentSpec, DROC, Tan Scen.2); C representation 既出 (AgentSpec, ADICO, ODRL, SLEEC, Meneguzzi), effect 証拠不足; D mechanism largely done (RuleGraph partial completion, SafeGate deferral, VFM verdicts) but the paired same-scene/same-instruction household-swap evaluation with joint success is a 差分候補. Small difference: per-object "undetermined" verdict with missing facts while the rest of the request still runs.

Debate questions:
 Q1. Is anything left that can be claimed as NOVEL (method / system / evaluation / HRI)? Be precise about which unit.
 Q2. What should be investigated, built or measured so the remaining difference becomes a defensible contribution (spec §5 experiments: household-only swap with star/circle marks uncorrelated with material/danger; held-out combinations; decomposition ablation incl. an AgentSpec-like arm; GT-attribute vs perception conditions; joint success metric)?
 Q3. The final "contribution sentence" (1 sentence) and the precise conditions under which it must be retracted.

Rules: evidence-bound; cite papers with §/Table from the files; never invent; distinguish "nobody built" / "nobody measured" / "measured, null". Do not assume novelty.
Output (≤ 800 words, English): Stance summary (3 lines) · Claims table (claim | unit: method/system/evaluation/HRI | closest prior | status 既出/差分候補/証拠不足 | strength H/M/L) · What to investigate/build/measure (ranked, concrete) · Contribution sentence + retraction conditions · Biggest risk · Questions to other debaters.
