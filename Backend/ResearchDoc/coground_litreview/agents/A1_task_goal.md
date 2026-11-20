# A1 — Task & Goal Researcher (Stream A, RQ-A)

RQ-A: To what extent have existing HRI systems supported users in assessing, understanding, and repairing discrepancies between intended task outcomes and robots' planned outcomes **before execution**?

Date of search: 2026-11-19. Agent: A1.

## Search log

**Sources:** WebSearch (general web, standard + extended modes), arXiv abstract and HTML pages, ACM/IEEE metadata via Crossref API, NSF PAR, author pages, Semantic Scholar Graph API. The Semantic Scholar API hit HTTP 429 rate limits after the first call, probably because other agents share the quota, so most snowballing went through web search instead.

**Queries (abbrev.):**
1. LLM robot task plan user verification before execution AR household
2. DALL-E-Bot diffusion goal image tidying user study
3. VeriPlan formal verification LLM end-user planning CHI 2025
4. RoboCritics LLM robot programming critics
5. MARCER mixed reality LLM robot programming digital twin preview
6. robot communicates task interpretation before execution, user confirms, preview predicted outcome (extended)
7. "Expressing robot incapability" Kwon Huang Dragan
8. household robot tidying user preview rearrangement plan AR goal-state visualization (extended)
9. robot visualizes predicted end/goal state before execution, user approves (extended)
10. human-robot task delegation household expectations
11. LLM robot plan NL explanation, user correction before execution, household 2024
12. AR robot task plan visualization, detect errors before execution
13. explainable AI for robot failures (Das/Chernova); proactive failure explanation
14. KnowNo / robots that ask for help
15. explaining plan unsolvability (Sreedharan); model reconciliation (Chakraborti)
16. robot clarification of ambiguous instruction, user study
17. generated image of predicted outcome, robot instruction confirmation
18. communicating robot capabilities (Cha/Dragan/Srinivasa)
19. non-expert users predict whether robot plan will succeed (plan verification)
20. household rules / constraints + user edits LLM plan
21. Robi Butler / plan visualization household LLM
22. before/after visualization robot rearrangement (extended); Dream2Real
23. shared mental model / misinterpretation detection LLM robot
24. LLM robot infeasible instruction, reports unfulfillable parts
25. smart-home multimodal disambiguation (image interpretations)

**Snowballing:**
- Forward citations (Semantic Scholar) of **VeriPlan (CHI'25)**. New hits: MRPilot (arXiv 2610.07477), RoboCritics (HRI'26), U-Define (arXiv 2605.02765), Distill (DIS'26).
- Forward citations of **MARCER (HRI'25)**. New hits: SHRIMP (UIST'26), Explainable OOHRI / X-OOHRI (HRI'26), GhostObjects (UIST Adj.'25), "HRI Grounding: Evidence That Operators Authorize and Correct AI Multi-Robot Plans…" (RA-L 2026; I could not open it, so it stays unverified), "A digital twin-enabled environment for end-user development of robot tasks" (Intell. Service Robotics 2026; not opened).
- Forward citations of **Polaris (HRI'24)** and SHRIMP failed with HTTP 429. I found Polaris's relation to SHRIMP and Distill through web search instead.
- Backward: Polaris's related-work table cites **RoVer** (Porfirio et al.; plan feedback via pre/postcondition checking). I did not open it, so another agent should cross-check it.
- Concept expansion: goal satisfaction led to plan success prediction (PerceptTwin) and goal imagination (DALL-E-Bot, Dream2Real). Repair led to plan editing (SHRIMP), rule sliders (VeriPlan) and critics with one-click fixes (RoboCritics). Interpretation led to disambiguation (Calò & De Russis, CLARA, KnowNo).

---

## Papers

### MRPilot2026
- Title / Authors / Year / Venue / DOI or URL: "MRPilot: Supervising and Intervening LLM-Based Multi-Robot Teams through Mixed Reality". Xiaoran Yang, Xun Qian, Yang Zhan, Nathan Tran, Ziyi Liu, Qiao Jin. 2026. arXiv 2610.07477 (cs.HC; no venue listed). https://arxiv.org/abs/2610.07477
- verified: true (abstract + HTML read) ; peer_reviewed: false (preprint)
- Class: Strongly Related
- Concepts: Interpretation (Forming stage: resolving ambiguous referents), Feasibility (capability-gap assistance; dependencies and conflicts), GoalSatisfaction (only partly: "coverage" relations between plans)
- What they do (implemented): A mixed reality (MR) system with four stages for supervising an LLM multi-robot planner: Forming, Reviewing (check plans **before execution**), Following, and Repairing. The LLM produces two candidate plans. Each plan consists of "commitments" with fields robot / action / referent / place / receiver / waits / rationale. The views are a situated MR view (predicted paths, labels, bounding boxes) and a Mini-Map overview (execution order). Repair can be **local** (Action Bar per robot, editing single fields such as *place*, with delete and revert) or **global** (re-prompt to regenerate the whole commitment set).
- What they evaluate: Formative study with N=12 non-experts. Main study: within-subjects, N=20, in a VR-simulated two-story home. Baseline is a conversational LLM interface with the same planner. 9 events per task covering 8 intervention types. Results with MRPilot: faster in 7 of 8 intervention types, e.g. plan selection 110.6 s vs 37.0 s (t(19)=−7.19, p<.001) and capability-gap assistance 144.0 s vs 59.9 s (p=.003); fewer prompts (12.4 vs 8.4, p<.001); lower NASA-TLX on all subscales; higher SART, trust, TOROS transparency and perceived control (all p<.01).
- Overlap with CoGround: Reviewing a plan in situ before execution, local field-level repair vs global replanning, household setting, workload and situation awareness (SA) measures.
- Differences: There is no predicted **After** environment state; plans are shown as paths and commitments. The paper does not measure the accuracy of goal-fulfillment judgments. Explanation is weak: the authors note the visualizations show "what and where but not why". The tasks are multi-robot delivery and supervision, and execution monitoring (Following) is included, whereas for CoGround that is adjacent.
- Scores: Purpose 2 | Timing 3 | Outcome 1 | Discrepancy 2 | Explanation 1 | Repair 3 | Evaluation 2
- Notes: Results are from the HTML (Sec. 4.1, results section). The comparison is against a chat baseline, not against another visual interface.

### SHRIMP2026
- Title / Authors / Year / Venue: "SHRIMP: Iterative Refinement of Robot Task Plans". Mya Schroder, Yuna Hwang, Callie Y. Kim, Leqian Cheng, Jeffrey Li-cheng Liu, Chenchen Zheng, Xinning He, Bilge Mutlu. 2026. UIST '26 (arXiv 2608.08884).
- verified: true (abstract + HTML) ; peer_reviewed: true (accepted to UIST'26 per arXiv comment)
- Class: Strongly Related
- Concepts: Interpretation (the primitive sequence shows how the LLM read the prompt), Feasibility (physics simulation), GoalSatisfaction (implicit, through playback)
- What they do: An LLM turns natural language into a hierarchical robot-primitive plan. The user replicates the scene in a digital twin, then runs physics simulation with full or step-by-step playback **before** running on a physical robot. Repair options: re-prompting, reordering or adding primitives, editing parameters (end-effector pose shown as a red arrow), and reverting through Task History.
- What they evaluate: Within-subjects ablation, N=35, conditions Plan+Edit / Plan-Only / No-Plan. Tasks: set the table, prepare a snack, clean the table. Plan+Edit vs No-Plan: perceived autonomy 3.50 vs 3.15 (p=.007) and TOROS transparency 4.77 vs 4.34 (p=.026). NASA-TLX was **higher** for Plan+Edit (37.9) than Plan-Only (29.9; p=.002). There was **no significant difference in task success or SUS**, and usability was below average in all conditions. Plan-Only alone did not differ from the others.
- Overlap: Pre-execution simulation preview of an LLM plan in household-like kitchen tasks, with local plan edits and iterative replanning.
- Differences: There is no at-a-glance After-state summary; the user must watch the simulation. The paper does not directly measure whether users detected discrepancies, and does not link explanations to constraints. It is desktop/digital-twin, not in-situ. The paper is a negative/contrary data point: plan visibility plus editing **raised workload** and did not improve task success.
- Scores: Purpose 2 | Timing 3 | Outcome 2 | Discrepancy 1 | Explanation 1 | Repair 3 | Evaluation 2
- Notes: P8 quote: "I was able to see where the task I entered could be shown differently by the system." 19 participants said that viewing the primitives improved their understanding.

### Polaris2024 (Porfirio, Roberts, Hiatt)
- Title / Authors / Year / Venue / DOI: "Goal-Oriented End-User Programming of Robots". David Porfirio, Mark Roberts, Laura M. Hiatt. HRI 2024. arXiv 2403.13988.
- verified: true (abstract + PDF text) ; peer_reviewed: true
- Class: Strongly Related
- Concepts: GoalSatisfaction (programs are goal predicates; checkpoints are constrained to match the world state after an action), Feasibility (a planner fills gaps; compile and feasibility failures), Interpretation (whether the plan matches user expectations)
- What they do: Users specify goal predicates or checkpoints (a "goal automaton"), and an off-the-shelf planner synthesizes a branching plan. The **Plan Visualizer** exposes the plan **before runtime** as a timeline of actions and resulting world states. It is used for a household **tidying scenario** (dishes to drying rack to cupboard).
- What they evaluate: Between-subjects study, plan-vis vs no-vis, N=32 (27 for post-execution measures). Plan quality (human effort) was significantly better with plan-vis (U=182.5, p=.017). Effects were only marginal (p≈.08–.10) for perceived competence, satisfaction, usefulness and an "expectations matched" questionnaire (overall α=.80). Usage patterns: 8 "intended use", 2 "unsuccessful use" (relied heavily on the visualizer but could not fix errors; feasibility 0.5/4), 4 "no-use". Robot familiarity correlated with most outcomes.
- Overlap: The pre-execution plan preview exists specifically to "ensure that user expectations match robot performance". The task is household tidying, and expectations-matched is a direct proxy for goal-satisfaction judgment.
- Differences: 2D web GUI with a timeline of states, not a spatial Before/After view. No automatic discrepancy highlighting. Repair means editing the goal automaton, not targeted local repair. Some users could not repair even after seeing errors.
- Scores: Purpose 3 | Timing 3 | Outcome 2 | Discrepancy 1 | Explanation 1 | Repair 2 | Evaluation 2
- Notes: The hypothesis H2 "helps match user expectations to robot task performance" is only marginally supported. This is important evidence that a plan preview alone does not reliably align expectations.

### PerceptTwin2026
- Title / Authors / Year / Venue: "PerceptTwin: Semantic Scene Reconstruction for Iterative LLM Planning and Verification". Charlie Gauthier, Sacha Morin, Liam Paull. ICRA 2026 (arXiv 2606.04226).
- verified: true (abstract + HTML) ; peer_reviewed: true (accepted ICRA 2026, per arXiv comment)
- Class: Strongly Related (on evaluation design) / Methodologically Relevant
- Concepts: Feasibility (skill preconditions), GoalSatisfaction ("logic" questions: whether the final state is correct), Interpretation (an LLM judge checks fit with human preferences)
- What they do: Builds an interactive simulation automatically from the robot's open-vocabulary semantic map, so LLM plans can be simulated before hardware execution. Shows explicit error messages for precondition violations. An LLM judge receives before/after state diffs.
- What they evaluate: Human plan-verification study, N=93, A/B design: point-cloud video vs PerceptTwin plan-execution video. The task is to **predict plan success/failure**. Question types: logic (all skills run, final state right or wrong) vs consistency (precondition failure). Accuracy improved in both types but was **significant only for consistency** failures (up to +18%). Logic (goal-satisfaction) errors were not significantly better detected. Planner success rose about 39% with simulation feedback.
- Overlap: The DV of "can the user tell whether the plan will achieve the goal" is almost exactly CoGround's core judgment. The design separates feasibility errors from goal-satisfaction errors.
- Differences: The preview is a full execution video, not an at-a-glance After state. There is no repair UI for users, and it is not in situ.
- Scores: Purpose 2 | Timing 3 | Outcome 2 | Discrepancy 2 | Explanation 2 | Repair 0 | Evaluation 3
- Notes: Accuracy values per condition were not reported in the text (they are in Fig. 7). Evidence that execution-video previews help detect **feasibility** errors but not clearly **goal-satisfaction** errors directly motivates a CoGround-style outcome representation.

### XOOHRI2026
- Title / Authors / Year / Venue / DOI: "Explainable OOHRI: Communicating Robot Capabilities and Limitations as Augmented Reality Affordances". Lauren W. Wang, Mohamed Kari, Parastoo Abtahi. HRI 2026. DOI 10.1145/3757279.3785569 (as listed on arXiv 2601.14587).
- verified: true (abstract only; HTML returned 404) ; peer_reviewed: true
- Class: Strongly Related
- Concepts: Feasibility (capabilities and limitations per object/action), Interpretation (object-oriented commands)
- What they do: An AR interface with signifiers, radial menus, color coding and **explanation tags** that show what the robot can and cannot do with each object. A VLM encodes object properties and robot limits into object-oriented structures. Users manipulate world-aligned virtual twins to command the robot, and the system supports "mixed-initiative resolution". Integrated with a physical robot.
- What they evaluate: A user study (N and numbers not in the abstract). Participants issued object-oriented commands effectively, formed accurate mental models of robot limitations, and engaged in mixed-initiative resolution.
- Overlap: Explanations of why the robot cannot do something are tied to the **object and constraint**, in situ AR, before commanding, with resolution.
- Differences: Communicates capability before the request, not a predicted outcome of a whole multi-step plan. No Before/After goal-satisfaction summary.
- Scores: Purpose 2 | Timing 3 | Outcome 1 | Discrepancy 2 | Explanation 3 | Repair 2 | Evaluation NR
- Notes: The full paper needs checking for N, DVs and whether limitations are shown at the plan level. Predecessor: GhostObjects (UIST Adj.'25).

### VeriPlan2025
- Title / Authors / Year / Venue / DOI: "VeriPlan: Integrating Formal Verification and LLMs into End-User Planning". Christine Lee, David Porfirio, Xinyu Jessica Wang, Kevin Zhao, Bilge Mutlu. CHI 2025. DOI 10.1145/3706598.3714113.
- verified: true (abstract + HTML) ; peer_reviewed: true
- Class: Partially Related (not a robot system; strong on constraint-linked discrepancy and repair)
- Concepts: Feasibility / constraint satisfaction (rules = user constraints). GoalSatisfaction is expressed as rule compliance.
- What they do: An LLM generates a plan. A rule translator turns user natural-language constraints into formal rules, which the user can confirm or regenerate. A model checker returns validity or a **list of violated rules**. A mind-map view links plan, rules and conflicts. **Flexibility sliders** set rule strictness (hard vs soft), and the LLM replans up to 3 iterations.
- What they evaluate: Within-subjects, N=12, ablation of 4 conditions (full / no sliders / no translator / checker only). Scenarios: hospital navigation, dinner-party cooking, weekly scheduling. The full system had higher usefulness (vs C2 p=.047, C3 p=.009, C4 p=.026), performance and satisfaction. Ease of use did not differ.
- Overlap: Discrepancies linked explicitly to the **constraint** violated, constraint-level repair, then replan. This maps closely to CoGround's household-rules concept.
- Differences: Not physical, not spatial, no outcome state visualization, no robot.
- Scores: Purpose 2 | Timing 3 | Outcome 0 | Discrepancy 3 | Explanation 3 | Repair 3 | Evaluation 2
- Notes: P3: "This structure makes it much clearer to see what the plan was, where the conflict happened, and why it occurred." Follow-up: U-Define (arXiv 2605.02765; hard vs soft constraints, not verified in detail).

### RoboCritics2026
- Title / Authors / Year / Venue: "RoboCritics: Enabling Reliable End-to-End LLM Robot Programming through Expert-Informed Critics". Callie Y. Kim, (White, He, Sala), Bilge Mutlu. HRI 2026, pp. 914–923. arXiv 2603.06842.
- verified: partial (abstract via search snippets / researchr listing; full author first names not confirmed) ; peer_reviewed: true
- Class: Partially Related
- Concepts: Feasibility (joint speed, collisions, unsafe poses)
- What they do: Expert-written "critics" analyze motion-level execution traces of LLM-generated robot programs, surface the issues, and offer **one-click fixes** that are sent back to the LLM.
- What they evaluate: Between-subjects, N=18, UR3e arm, vs an LLM baseline without critics. Reported: fewer safety violations, better execution quality, and better user verification and debugging behaviors. Numbers not confirmed.
- Overlap: Pre-execution issue detection linked to an action/constraint, with targeted fixes.
- Differences: Safety and motion feasibility, not goal satisfaction. Users are programmers, not delegators.
- Scores: Purpose 1 | Timing 3 | Outcome 1 | Discrepancy 2 | Explanation 2 | Repair 3 | Evaluation 2
- Notes: I did not confirm whether the critics run on simulated traces before physical execution (very likely, but `verified: false` for that detail).

### MARCER2025
- Title / Authors / Year / Venue / DOI: "MARCER: Multimodal Augmented Reality for Composing and Executing Robot Tasks". Bryce Ikeda, Maitrey Gramopadhye, LillyAnn Nekervis, Daniel Szafir. HRI 2025, pp. 529–539. DOI 10.1109/HRI61500.2025.10974232.
- verified: true (abstract) ; peer_reviewed: true
- Class: Partially Related
- Concepts: Interpretation (LLM language to trigger-action plan), Feasibility (validate programs)
- What they do: An LLM converts natural-language task descriptions plus environmental context into trigger-action plans. AR lets users set parameters and constraints, edit plans, **validate programs**, and see real-time visual previews in the workspace. The 2024 poster mentions a digital-twin preview before execution and a groceries-to-shelves example.
- What they evaluate: The paper says it includes an evaluation, but I could not access N, design or results → `verified: false` for evaluation.
- Overlap: LLM plan, in situ AR preview, user edit before execution.
- Differences: Programming paradigm (trigger-action). It is unclear whether goal-level outcome summaries exist.
- Scores: Purpose 2 | Timing 3 | Outcome 2 | Discrepancy NR | Explanation NR | Repair 2 | Evaluation NR
- Notes: Should be cross-checked by the AR agent (full text on IEEE / NSF PAR, now public).

### Diehl2020
- Title / Authors / Year / Venue / DOI: "Augmented Reality interface to verify Robot Learning". Maximilian Diehl, Alexander Plopski, Hirokazu Kato, Karinne Ramirez-Amaro. RO-MAN 2020, pp. 378–383. DOI 10.1109/RO-MAN47096.2020.9223502.
- verified: true (abstract, Chalmers record) ; peer_reviewed: true
- Class: Strongly Related (closest older "verify before execution" study)
- Concepts: Interpretation (did the robot learn the task correctly), Feasibility
- What they do: AR overlays a virtual simulation of the taught behavior on the real environment, synchronized with a semantic description of the current action, so users can verify the robot's learned task **before execution**. Three AR/visualization designs are compared with RViz-like simulators.
- What they evaluate: N=18. DV: effectiveness for **error detection**. The abstract says AR gave more realistic feedback at lower cost. Numbers not read.
- Overlap: Pre-execution error detection in situ, with semantic step labels.
- Differences: Replays the whole execution, no outcome summary, no repair UI, learned (LfD) tasks.
- Scores: Purpose 2 | Timing 3 | Outcome 2 | Discrepancy 2 | Explanation 1 | Repair 0 | Evaluation 2
- Notes: A 2024 Chalmers MSc thesis (D. Gad, HoloLens 2 per-action replay to spot plan errors) is a follow-up. It is not peer-reviewed and not verified in detail.

### LeMasurier2024
- Title / Authors / Year / Venue / DOI: "Reactive or Proactive? How Robots Should Explain Failures". Gregory LeMasurier, Alvika Gautam, Zhao Han, Jacob W. Crandall, Holly A. Yanco. HRI 2024. DOI 10.1145/3610977.3634963.
- verified: true (PDF read) ; peer_reviewed: true
- Class: Partially Related
- Concepts: Feasibility (assumption checkers on behavior trees predict upcoming failure)
- What they do: Compares a Reactive system (explains after failure) with a Proactive system (predicts and explains issues **in advance**, using assumption checkers) and a third condition.
- What they evaluate: Online video study (Prolific), N=186 after exclusions, 3 between-subjects conditions. The Proactive system gave higher perceived intelligence (Kruskal–Wallis χ²(2)=56.47, p<.001) and trust, and its explanations were rated more understandable and timely. Also measured: accuracy of identifying the failure cause, and confidence.
- Overlap: Communicating failures before they happen, explanations linked to cause, measuring whether users identify the cause.
- Differences: Proactive means during execution, before the failing step, not before the whole task starts. Verbal explanations only, no outcome visualization, no repair. Warehouse-like setting.
- Scores: Purpose 1 | Timing 2 | Outcome 0 | Discrepancy 2 | Explanation 3 | Repair 0 | Evaluation 2

### Das2021
- Title / Authors / Year / Venue: "Explainable AI for Robot Failures: Generating Explanations that Improve User Assistance in Fault Recovery". Devleena Das, Siddhartha Banerjee, Sonia Chernova. HRI 2021. arXiv 2101.01625.
- verified: true (arXiv listing/abstract via search) ; peer_reviewed: true
- Class: Background / Methodologically Relevant
- Concepts: Feasibility (failure cause)
- What they do: Generates failure explanations (context of failure plus action history) for non-experts **after the robot halts**.
- What they evaluate: Explanations with context and history were the most effective for non-experts identifying failures and solutions. About 89.7% generation accuracy (2020 preprint).
- Overlap: Cause explanation linked to action/object, aimed at non-experts, helping them choose a repair.
- Differences: Post-failure, during execution, not pre-execution.
- Scores: Purpose 1 | Timing 0 | Outcome 0 | Discrepancy 1 | Explanation 3 | Repair 2 | Evaluation 2

### Kwon2018
- Title / Authors / Year / Venue: "Expressing Robot Incapability". Minae Kwon, Sandy H. Huang, Anca D. Dragan. HRI 2018. arXiv 1810.08167.
- verified: true ; peer_reviewed: true
- Class: Background
- Concepts: Feasibility (incapability), Interpretation (what the robot is trying to do)
- What they do: Trajectory optimization produces motions that resemble a successful attempt while respecting the failure constraint, so they communicate **what** the robot tries and **why** it cannot.
- What they evaluate: Video user study. Participants identified the goal and the failure reason better, and perceptions of the robot improved.
- Overlap: Communicates the cause of a goal not being achieved.
- Differences: At execution time, motion-based, no preview, no repair.
- Scores: Purpose 1 | Timing 0 | Outcome 0 | Discrepancy 1 | Explanation 2 | Repair 0 | Evaluation 2

### Cha2015
- Title / Authors / Year / Venue: "Perceived Robot Capability". Elizabeth Cha, Anca D. Dragan, Siddhartha S. Srinivasa. 2015. Venue: RO-MAN 2015 to my recollection; one search snippet said HRI. **Venue unverified.**
- verified: false (only the CMU RI listing title and snippets seen) ; peer_reviewed: true (likely)
- Class: Background
- Concepts: user mental model of capability
- What they do / evaluate: Separates perceived from true capability and documents under- and over-perception. Related work: Cha et al. HRI 2013 (capability and acceptance), Nikolaidis et al. HRI 2017 (robot fails intentionally to reveal its capabilities).
- Overlap: Motivates why users misjudge what a delegated robot will achieve.
- Differences: No pre-execution plan preview.
- Scores: Purpose 1 | Timing 0 | Outcome 0 | Discrepancy 1 | Explanation 0 | Repair 0 | Evaluation 1

### Chakraborti2018 (model reconciliation)
- Title / Authors / Year / Venue: "Plan Explanations as Model Reconciliation — An Empirical Study". Tathagata Chakraborti, Sarath Sreedharan, Sachin Grover, Subbarao Kambhampati. HRI 2018 (arXiv 1802.01013).
- verified: true (arXiv listing via search; full text not read) ; peer_reviewed: true
- Class: Methodologically Relevant
- Concepts: Interpretation and Feasibility (mismatch between the human model and the robot model)
- What they do: Plan explanations as model updates that make the robot's plan optimal or feasible in the human's model, with an empirical user study.
- Overlap: Theory for explaining **why** the plan differs from what the user expected.
- Differences: No spatial outcome, no local user repair (the explanation updates the user's model).
- Scores: Purpose 1 | Timing 2 | Outcome 0 | Discrepancy 2 | Explanation 3 | Repair 0 | Evaluation 1
- Related: Sreedharan et al. "Why Can't You Do That HAL? Explaining Unsolvability of Planning Tasks" (IJCAI 2019) explains unsolvability through abstractions, with a user study. Directly relevant to "why can't the request be fulfilled" (verified: true via mlanthology listing).

### Besch2026 (LLM model reconciliation, assistive)
- Title / Authors / Year / Venue: "Model Reconciliation through Explainability and Collaborative Recovery in Assistive Robotics". Britt Besch, Tai Mai, Jeremias Thun, Markus Huff, Jörn Vogel, Freek Stulp, Samuel Bustamante. ICRA 2026 (arXiv 2601.06552).
- verified: true (abstract) ; peer_reviewed: true
- Class: Partially Related
- Concepts: Interpretation (model divergence, e.g. an object missing from the robot's world model)
- What they do: An LLM predicts and explains differences between the robot's and the human's mental models, and the human then corrects the robot. Tested on a wheelchair-based mobile manipulator and its digital twin.
- What they evaluate: "Experiments". A user study is not stated in the abstract (NR).
- Scores: Purpose 2 | Timing 2 | Outcome 1 | Discrepancy 2 | Explanation 2 | Repair 2 | Evaluation NR
- Related: Moorman et al., "Bi-Directional Mental Model Reconciliation for HRI with LLMs", AAAI 2025 ToM workshop (arXiv 2503.07547). Verified title and authors. A "37% fewer misinterpretations" claim comes only from a third-party site and is **unverified**.

### DALLEBot2023
- Title / Authors / Year / Venue: "DALL-E-Bot: Introducing Web-Scale Diffusion Models to Robotics". Ivan Kapelyukh, Vitalis Vosylius, Edward Johns. IEEE RA-L 2023 (arXiv 2210.02438).
- verified: true (abstract) ; peer_reviewed: true
- Class: Partially Related (outcome representation)
- Concepts: GoalSatisfaction (imagines the tidy goal image)
- What they do: Builds a caption prompt from detected objects, generates a **goal image of the tidied scene** with DALL-E 2, and rearranges objects to match it. Zero-shot tidying.
- What they evaluate: About 3,000 user ratings. DALL-E-Bot arrangements were rated higher than geometric and random baselines. Also completes partial arrangements.
- Overlap: An explicit predicted **After image** for tidying, the same Outcome-representation concept as CoGround.
- Differences: The goal image is used by the robot, not shown to the user for confirmation or repair before execution. Users rated outcomes after the fact.
- Scores: Purpose 1 | Timing 1 | Outcome 3 | Discrepancy 0 | Explanation 0 | Repair 0 | Evaluation 1
- Related: Dream2Real (Kapelyukh, Ren, Alzugaray, Johns; ICRA 2024; arXiv 2312.04533) imagines candidate rearranged 3D scenes (NeRF renders) and lets a VLM score them against the instruction. It is likewise not user-facing (verified: true).

### TidyBot2023
- Title / Authors / Year / Venue: "TidyBot: Personalized Robot Assistance with Large Language Models". Jimmy Wu, Rika Antonova, Adam Kan, Marion Lepert, Andy Zeng, Shuran Song, Jeannette Bohg, Szymon Rusinkiewicz, Thomas Funkhouser. Autonomous Robots 2023 / IROS 2023 (arXiv 2305.05658).
- verified: true ; peer_reviewed: true
- Class: Background (household tidying preferences)
- Concepts: Interpretation (LLM summarizes user placement preferences into rules)
- What they do / evaluate: Few-shot preference summarization reaches 91.2% accuracy on unseen objects in the benchmark and puts away 85.0% of objects in the real world.
- Overlap: Household rules for tidying (constraint concept).
- Differences: No user-facing pre-execution check. Preferences are learned, not inspected or repaired.
- Scores: Purpose 1 | Timing 0 | Outcome 0 | Discrepancy 0 | Explanation 0 | Repair 0 | Evaluation 1

### ImageInThat2025
- Title / Authors / Year / Venue: "ImageInThat: Manipulating Images to Convey User Instructions to Robots". Karthik Mahadevan, Blaine Lewis, Jiannan Li, Bilge Mutlu, Anthony Tang, Tovi Grossman. HRI 2025 (Crossref confirms the HRI'25 proceedings; arXiv 2503.15500).
- verified: true ; peer_reviewed: true
- Class: Partially Related
- Concepts: GoalSatisfaction (the user specifies desired intermediate and goal states as images)
- What they do: The user specifies the task by directly manipulating images in a timeline. The result is a sequence of **desired state images** that become robot instructions.
- What they evaluate: Kitchen manipulation tasks vs text-based instructions. Participants were faster with ImageInThat and preferred it. N not in the abstract (a search snippet says 10, **unverified**).
- Overlap: Represents goals as visual world states (After-like images) and lets users reason in the state space rather than the action space.
- Differences: The images are the user's intended state, not the robot's predicted state. No discrepancy detection. Showing the robot's understanding back to the user is mentioned only as future work (per snippet, unverified).
- Scores: Purpose 2 | Timing 2 | Outcome 2 | Discrepancy 0 | Explanation 0 | Repair 1 | Evaluation 2

### GenComUI2025
- Title / Authors / Year / Venue / DOI: "GenComUI: Exploring Generative Visual Aids as Medium to Support Task-Oriented Human-Robot Communication". Yate Ge, Meiying Li, Xipeng Huang, Yuanda Hu, Qi Wang, Xiaohua Sun, Weiwei Guo. CHI 2025. DOI 10.1145/3706598.3714238.
- verified: true (abstract) ; peer_reviewed: true
- Class: Partially Related
- Concepts: Interpretation (visual feedback of how the robot understood a spatial task)
- What they do: An LLM generates visual aids (map annotations, paths, animations) on the robot's screen during verbal task specification, giving continuous visual feedback and confirmation before a task program is produced.
- What they evaluate: N=20 vs a voice-only baseline. Visual aids improved communication. Per a search snippet, efficiency and accuracy gains held for complex but not simple tasks (unverified detail).
- Overlap: Feedback on interpretation before execution.
- Differences: Navigation and spatial tasks on a 2D screen, not manipulation outcome states. No discrepancy explanation or repair targeting.
- Scores: Purpose 2 | Timing 3 | Outcome 1 | Discrepancy 1 | Explanation 0 | Repair 1 | Evaluation 2

### CaloDeRussis2024
- Title / Authors / Year / Venue / DOI: "Enhancing smart home interaction through multimodal command disambiguation". Tommaso Calò, Luigi De Russis. Personal and Ubiquitous Computing 28(6):985–1000, 2024. DOI 10.1007/s00779-024-01827-3. (First names from my recollection and the Polito record; the full paper was not opened.)
- verified: partial (repository record + author press summary; the Springer page was paywalled) ; peer_reviewed: true
- Class: Partially Related
- Concepts: Interpretation (presents 3 candidate interpretations, as text or **generated images of the resulting state**, e.g. "make the room cozier")
- What they evaluate: N=13 user study. Users found the multimodal disambiguation helpful. A snippet says textual options were slightly more effective (**unverified**). This would be a contrary data point against image-based outcome previews.
- Overlap: Shows **anticipated outcome images** for the user to confirm intent before acting.
- Differences: Smart home (not a robot), interpretation only, no plan, no repair.
- Scores: Purpose 2 | Timing 3 | Outcome 2 | Discrepancy 1 | Explanation 0 | Repair 1 | Evaluation 2

### KnowNo2023
- Title / Authors / Year / Venue: "Robots That Ask For Help: Uncertainty Alignment for Large Language Model Planners". Allen Z. Ren et al. CoRL 2023 (PMLR v229; arXiv 2307.01928).
- verified: true ; peer_reviewed: true
- Class: Background
- Concepts: Interpretation (ambiguity leads to asking the human before acting)
- What they do / evaluate: Conformal prediction over LLM plan options; the robot asks when the prediction set is not a singleton. It needed 10–24% less help than baselines at guaranteed success levels.
- Overlap: Pre-execution resolution of interpretation uncertainty.
- Differences: The robot initiates and asks a multiple-choice question; no outcome preview, no user-side inspection. No HCI evaluation of user understanding.
- Scores: Purpose 1 | Timing 3 | Outcome 0 | Discrepancy 1 | Explanation 0 | Repair 1 | Evaluation 0
- Related: CLARA (arXiv 2306.10376) classifies commands as clear / ambiguous / **infeasible** and explains them (not verified in detail). RAIDER (arXiv 2503.17703) flags ambiguity and unfeasibility with explanations in a simulated household (not verified).

### Prospection2019
- Title / Authors / Year / Venue: "Prospection: Interpretable Plans From Language By Predicting the Future". Chris Paxton, Yonatan Bisk, Jesse Thomason, Arunkumar Byravan, Dieter Fox. ICRA 2019 (arXiv 1903.08309).
- verified: true ; peer_reviewed: true
- Class: Partially Related (concept precursor)
- Concepts: Interpretation, GoalSatisfaction (predicts future intermediate goal states from language)
- What they do: Maps language to intermediate subgoals and predicts future world states, so plans are interpretable. According to a search snippet (unverified), the paper suggests showing the predicted subgoals to the user for confirmation before execution.
- What they evaluate: Crowd-sourced commands in simulation; no user study of the previews.
- Scores: Purpose 2 | Timing 2 | Outcome 2 | Discrepancy 0 | Explanation 0 | Repair 0 | Evaluation 0

### Distill2026
- Title / Authors / Year / Venue: "Distill: Uncovering the True Intent behind Human-Robot Communication". Ting Li, David Porfirio. DIS 2026 (arXiv 2605.14262).
- verified: partial (abstract via search) ; peer_reviewed: true
- Class: Partially Related
- Concepts: Interpretation (from over-specified task steps to the true goal: remove steps, generalize meanings, relax ordering)
- What they evaluate: Crowdsourced study of a web interface (details not verified).
- Overlap: Separates the user's real goal from the literal instruction, which is foundational for judging goal satisfaction.
- Scores: Purpose 2 | Timing 2 | Outcome 0 | Discrepancy 1 | Explanation 0 | Repair 1 | Evaluation NR

### ITP2023 (adjacent)
- "Interactive Task Planning with Language Models". Boyi Li, Philipp Wu, Pieter Abbeel, Jitendra Malik. arXiv 2310.10645 → TMLR 2025 (per search, venue not confirmed on the page). verified: partial. Class: Background. GPT-4 planner that replans from user feedback during execution (milk-tea making); no pre-execution outcome check.
- Scores: Purpose 1 | Timing 1 | Outcome 0 | Discrepancy 0 | Explanation 0 | Repair 2 | Evaluation 0

---

## Agent summary

**Top 5 closest works (to CoGround's pre-execution "will my request be fulfilled?" judgment plus repair):**
1. **MRPilot (arXiv 2026, preprint)**: in-situ MR Reviewing stage before execution, local field-level vs global repair, household (VR), N=20 with workload, SA and trust benefits vs a chat baseline. Missing: an After-state outcome view and "why" explanations. Scores P2 T3 O1 D2 E1 R3 Ev2.
2. **Polaris (HRI'24)**: Plan Visualizer showing plan and world states before runtime in a **tidying** scenario. Its explicit goal is matching user expectations, but the effect on "expectations matched" was only **marginal** (p≈.08). P3 T3 O2 D1 E1 R2 Ev2.
3. **SHRIMP (UIST'26)**: LLM plan with simulation preview and local primitive edits. N=35: higher transparency and autonomy, but **higher workload and no task-success gain**. P2 T3 O2 D1 E1 R3 Ev2.
4. **PerceptTwin (ICRA'26)**: N=93 study of humans **predicting plan success**. Simulation video helped detect feasibility (precondition) failures significantly, but **not** goal/final-state ("logic") errors. P2 T3 O2 D2 E2 R0 Ev3.
5. **VeriPlan (CHI'25)** and **X-OOHRI (HRI'26)**, tied. VeriPlan links violations to user constraints and offers rule-level repair through sliders (not a robot). X-OOHRI gives object-linked AR explanations of capability and limits with mixed-initiative resolution. Both score E3; neither shows a predicted outcome state.

**Key gaps (as far as A1 found; this is not a claim of novelty):**
- No verified robot system shows the user a **predicted post-execution environment state (After) vs current (Before)** as the primary summary for judging goal satisfaction. Existing previews are step timelines (Polaris), full simulation playback (SHRIMP, PerceptTwin, Diehl 2020), or path/commitment views (MRPilot). Predicted goal images do exist (DALL-E-Bot, Dream2Real) but are consumed by the robot, not by the user.
- Task Interpretation, Plan Feasibility and Goal Satisfaction are rarely separated. PerceptTwin is the only study I found whose evaluation distinguishes feasibility errors from final-state (goal) errors, and the goal-error detection there was not significantly improved.
- Explanations linked to object/constraint exist (VeriPlan, X-OOHRI, RoboCritics, LeMasurier) but are not combined with an outcome-level summary plus drill-down.
- Evaluations mostly measure workload, trust, transparency and usability. Few measure the **accuracy/speed of judging goal fulfillment** (exceptions: PerceptTwin accuracy; Diehl error detection; Polaris "expectations matched").

**Contrary / cautionary evidence to keep:**
- SHRIMP: viewing plus editing raised NASA-TLX and did not improve task success.
- Polaris: preview effects on expectation matching were only marginal, and some users could see but not fix errors.
- PerceptTwin: execution-video preview did not significantly help detect goal-level errors.
- Calò & De Russis (snippet, unverified): text options were slightly more effective than image options.

**Open doubts:**
- MARCER's evaluation (N, results) and whether its preview shows outcome states: not verified.
- X-OOHRI study N and DVs: not verified (HTML 404).
- RoboCritics: whether critics run on simulated traces before execution; numbers not verified.
- The RA-L 2026 paper "HRI Grounding: Evidence That Operators Authorize and Correct AI Multi-Robot Plans Through a Generated Supervisory Interface" appeared in MARCER's forward citations but could not be opened (unverified).
- Cha 2015 venue (RO-MAN vs HRI) unverified.

**Papers other agents should cross-check:**
- AR / visualization agent: MARCER (full text), X-OOHRI, GhostObjects, Diehl 2020 plus the 2024 Chalmers HoloLens thesis, MRPilot, Rosen et al. (Brown, HoloLens arm-motion preview: 16% accuracy gain, 62% time reduction; not verified by A1), "A digital twin-enabled environment for end-user development of robot tasks" (Intell. Service Robotics 2026).
- Explainable planning agent: Chakraborti 2018, Sreedharan IJCAI 2019 (unsolvability), Besch ICRA 2026, Moorman 2025, RoVer (Porfirio et al., cited in Polaris).
- LLM-planning / HCI agent: VeriPlan → U-Define (arXiv 2605.02765), RoboCritics, SHRIMP, PerceptTwin, CLARA, RAIDER (arXiv 2503.17703), InteLiPlan (arXiv 2409.14506), Robi Butler (ICRA 2025, arXiv 2409.20548), LLM-Personalize (COLING 2025).
- Evaluation-methods agent: PerceptTwin's success-prediction protocol (logic vs consistency questions) and Polaris's "expectations matched" questionnaire are reusable DV designs for CoGround.
