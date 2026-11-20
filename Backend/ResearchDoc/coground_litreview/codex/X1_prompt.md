You are Agent X (Critical Reviewer) in an HRI literature review. You work INDEPENDENTLY of other agents: do NOT read files under ../agents/.
Read ../00_brief.md for the target system (CoGround), rules, scoring and output format.

Task: try to FALSIFY CoGround's novelty. Use live web search extensively (ACM DL, IEEE Xplore, arXiv, Semantic Scholar, Google Scholar, HRI/CHI/UIST/ISMAR/ICRA/IROS/RO-MAN/CoRL 2015–2026).
Answer each, citing concrete papers (title, authors, year, venue, URL; mark verified true/false — never invent):
1. Does work with essentially the same purpose already exist (user assesses BEFORE execution whether a robot's plan will fulfil their requested household task)?
2. Is the same experience realized WITHOUT AR (2D GUI, simulation video, digital twin, image generation, language)?
3. Has Before/After (current vs predicted end state) outcome understanding already been built or evaluated, for robots or for other automation (e.g. smart home automation preview, code/diff preview, CAD, LLM agent plan preview)?
4. Are failure-cause explanation and plan repair already integrated in one pre-execution system?
5. Is "goal–plan discrepancy" already covered by another concept name (e.g. expectation mismatch, model reconciliation, goal misalignment, specification error, verification of task outcome)?
6. Is CoGround's contribution a new function, a new combination, or a new empirical finding? Which is defensible?
7. Evaluation critique: risks of assuming AR is faster; information unfairness in AR vs 2D; confusing comprehension speed with interaction speed; subjective clarity used as accuracy; confusing outcome prediction with feasibility. Cite studies with negative/null AR results.

Write output to X1_independent_falsification.md (in the current directory) with: Search log; Paper blocks (brief format, focus on the 10–20 most threatening papers); Answers to Q1–Q7; Verdict table of candidate novelty claims (Defensible / Weak / Not defensible + evidence).
