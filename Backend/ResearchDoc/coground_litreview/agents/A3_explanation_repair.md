# A3 — Explanation & Repair Researcher (Stream A)

Focus: XAIP with users, model reconciliation, unsolvability / "why not" / contrastive explanations, counterfactual failure explanations, situated (AR) explanations, interactive plan repair, constraint negotiation, pre-execution correction of LLM robot plans, robot failure explanation, rule-aware household robots.

Date of search: 2026-11-19. All "verified: true" entries were checked against an arXiv abstract page, proceedings page (IJCAI, RSS, ICAPS/AAAI OJS, NASA NTRS) or the paper's full PDF. Numbers come from the PDF only where the notes say so.

---

## Search log

**Web queries (WebSearch, standard unless noted):**
1. `model reconciliation augmented reality robot explanation user study` → found Besch et al. ICRA 2026, Moorman et al. 2025 (bidirectional MR, proposal only), Luebbers RSS 2023 (AR justification; left to the AR agent), Zahedi HRI 2019 LBR.
2. `LLM robot plan correction before execution user interface study household` → found SHRIMP (UIST 2026), RoboCritics (HRI 2026), VerifyLLM (no users), the LLM-judge planner (no users).
3. `explaining unsolvable planning problems user "why not" robot study` → found Sreedharan et al. IJCAI 2019.
4. `ImageInThat ...` → found Mahadevan et al. HRI 2025.
5. `Eifler Hoffmann iterative planning with plan-space explanations tool and user study` → found the XAIP'20 tool, the XAIP'21 study (N=40/domain), and the ICAPS 2022 study (N=100/domain).
6. `Raman Kress-Gazit explaining impossible high-level robot behaviors` → found TRO 2013, RSS 2013, and the unsynthesizable cores paper.
7. `Das Banerjee Chernova Explainable AI for robot failures` → HRI 2021 (I read the full PDF).
8. `SHRIMP ...` → I read the full PDF (UIST '26).
9. `Chakraborti projection-aware ... IROS 2018` → I read the full PDF.
10. `Diehl Ramirez-Amaro Why did I fail` → RA-L 2022.
11. `Krarup contrastive explanations of plans through model restrictions` → JAIR 2021 (I read the full PDF for both user studies).
12. `"Plan Explanations as Model Reconciliation" empirical study` → HRI 2019 version (I read the PDF), IJCAI 2017 original.
13. `RADAR-X ...` → AAAI 2021 demo, ICAPS 2022 industry track.
14. `"Sorry Dave ..." RSS 2013` → RSS proceedings page.
15. `augmented reality preview LLM-generated robot task plan verify edit before execution user study` → found MARCER (HRI 2025) and **X-OOHRI (HRI 2026)**, which I read in full.
16. `household robot explains why goal cannot be achieved ... LLM planning user study` → found Fouilhé et al. (EUMAS 2026; I read the HTML for study numbers), COMMET (no user study seen), Nilsson/Wohlrab preference explanations.
17. `counterfactual explanations robot task planning user study "why not"` → found CE-MRS (RA-L 2024; I read the HTML), HELM (IJCAI 2018), Amir et al.
18. `interactive plan repair human robot user modifies constraints replanning explanation interface study` → found iRoPro (RO-MAN 2019), Merlo et al. 2025, Plover (GUI agents), PARSEC.
19. `augmented reality explanations robot failure situated explanation user study recovery` → found X-OOHRI again and Happily Error After (VR).
20. `Khanna explanation strategies ... RO-MAN 2023`, `REFLECT ... CoRL 2023`, `REX ... DIS 2024`, `VeriPlan ... CHI 2025`, `Briggs Scheutz "Sorry, I can't do that"`, `VizXP`, `What Impact Do My Preferences Have`, `Evaluating Plan-Property Dependencies ICAPS 2022`.
21. (extended) `HRI 2025 2026 user study LLM robot plan preview simulation digital twin approve edit before execution mixed reality household tidying` → found only a Springer 2026 digital-twin plus Blockly end-user development paper (not verified).

**Snowballing (Semantic Scholar Graph API `/paper/{id}/citations`):**
- Forward from **Das et al. HRI 2021** (arXiv:2101.01625). Relevant citing papers: X-OOHRI (HRI 2026), REX (DIS 2024), "Enabling Novices to Diagnose Robot Failures by Aligning Users' Mental Models" (UMAP 2025), "Interpretable Robot Failure Attribution for Remote Robot Supervisors" (RO-MAN 2026), "Closing the Communication Loop for Robotic Failures: Multi-Turn, BT-Grounded Explanations with LLMs" (ICRA 2026), "Robot Arms Too Short? Explaining Motion Planning Failures using Design Optimization" (RO-MAN 2025), "Generating Environment-based Explanations of Motion Planner Failure" (ICRA 2024), "Templated vs. Generative: Explaining Robot Failures" (RO-MAN 2024), "Multimodal Coherent Explanation Generation of Robot Failures" (IROS 2024). I did not read these in depth; they are listed for cross-checking.
- Forward from **Chakraborti et al. HRI 2019 empirical MR study** (arXiv:1802.01013) → VizXP (ICAPS 2022), Eifler et al. ICAPS 2022, Krarup JAIR 2021, Zahedi HRI 2019 LBR, "Bridging the Human-Agent Representation Gap for Decision-Making Explanations in Autonomous Robots" (RO-MAN 2025), OBJUST (REFSQ 2024).
- Forward from **Eifler & Hoffmann XAIP'20** (arXiv:2011.09705) → VizXP, the logic-based explanation framework (JAIR 2022).
- Forward from **X-OOHRI** (arXiv:2601.14587) → only 2 citing papers so far (AR-HRC SA comparison 2026; "Uncertain Pointer", CHI 2026). Neither is in scope.
- Backward from X-OOHRI → it cites GhostAR, HoloSpot and timeline-based task editing, which are the AR agent's domain. It states "no comparable systems exist for visually communicating robot limitations via object-oriented interactions".
- Backward from Krarup / Eifler → Hauser's minimum-constraint-removal explanations of motion planning failure (background only, not verified).

The Semantic Scholar API rate-limited (HTTP 429) once. The Das query succeeded on retry.

---

## Papers

### WangKariAbtahi2026_XOOHRI
- Title / Authors / Year / Venue / DOI or URL: *Explainable OOHRI: Communicating Robot Capabilities and Limitations as Augmented Reality Affordances* / Lauren W. Wang, Mohamed Kari, Parastoo Abtahi / 2026 / ACM/IEEE HRI 2026 (Edinburgh) / https://arxiv.org/abs/2601.14587
- verified: true (abstract plus full PDF read) ; peer_reviewed: true (HRI 2026 accepted)
- Class: **Strongly Related** (closest AR work on explaining *why* a requested action is infeasible, tied to object/robot constraints, with in-situ local repair and previews before execution)
- Concepts: Feasibility (primary). Interpretation is partial: object-oriented commands reduce ambiguity. GoalSatisfaction is implicit: the target object's virtual twin is placed at the desired pose, but whole-task fulfillment is not assessed.
- What they do (implemented):
  - The user instructs a robot by directly manipulating "GhostObjects", which are virtual twins aligned with the physical scene, in AR through radial action menus.
  - A VLM encodes object properties into object-oriented classes (XObject/XRobot). A decision-tree feasibility module checks reachability, graspability and manipulability against robot limits and a simulated world state.
  - When an action is infeasible, the GhostObject turns red and an **explanation tag** names the limiting precondition (e.g., "Too high to reach"). This updates live as the user drags the object.
  - The **mixed-initiative resolution** menu offers four options:
    - *Auto*: manipulate other objects so the target action becomes feasible. It plays a **preview animation** of the action sequence.
    - *Alternative*: suggest a different object of the same class, or another target pose. It is previewed.
    - *Ignore*.
    - *User-driven*: add Virtual preparatory actions, or give physical help.
  - Confirmed actions are published to ROS2 for a physical robot.
- What they evaluate:
  - Design: an IRB-approved **exploratory study** with no baseline condition ("we opted for an exploratory study rather than a controlled experiment"). N=14 (12 male, 2 female, aged 18–25), using think-aloud.
  - Tasks: Part 1 was pick-and-place plus fill; Part 2 was vacuum plus higher-level instructions.
  - Measures: self-reported and factual understanding of capabilities and limitations (5-point Likert), NASA-TLX, SUS, and interviews.
  - Results: all participants completed the tasks. AR interaction time per subtask was M=114 s (SD=53 s). **All participants were able to resolve the constraints**, either proactively or after using the explanation tags: 12 virtually repositioned objects, 10 physically opened doors, and 2 picked system alternatives. SUS was 79.3 and TLX workload was low. Participants mentioned the unfamiliarity of AR.
  - The VLM backend reached 98.7% categorical accuracy on object property encoding. VLM outputs were manually verified for the study.
- Overlap with CoGround: pre-execution, in-situ AR; the cause of infeasibility is linked to an object or robot constraint; local repair by changing the object, the pose, preparatory actions, or accepting a system resolution; preview animations of the resolution.
- Differences:
  - The unit is a single object-level action, not a full multi-step task plan.
  - There is no global "Before vs predicted After" scene and no glanceable summary of how much of the task will be fulfilled.
  - There are no household *rules* or preferences, only physical capability limits.
  - Feasibility is a binary per action, not goal satisfaction.
  - There is no controlled comparison, so repair accuracy and speed are not compared with a baseline.
- Scores: Purpose 2 | Timing 3 | Outcome 2 | Discrepancy 2 | Explanation 3 | Repair 3 | Evaluation 2
- Notes / evidence: Sec. 3.2 (color coding, explanation tags, preview), Sec. 3.4 ("When infeasibility is detected, the system raises an explanation ε(e) that identifies the limiting preconditions"), Sec. 3.5 (Auto / Alternative / Ignore), and Sec. 5 study ("Fourteen participants", "All participants were able to resolve the constraints"). The search snippet's "in-home user study" description does not match the PDF; the PDF describes a lab study.

### Schneider2024_CEMRS
- Title / Authors / Year / Venue / DOI or URL: *CE-MRS: Contrastive Explanations for Multi-Robot Systems* / Ethan Schneider, Daniel Wu, Devleena Das, Sonia Chernova / 2024 / IEEE RA-L vol. 9, pp. 10121–10128 / https://arxiv.org/abs/2410.08408
- verified: true (abstract plus HTML full text) ; peer_reviewed: true
- Class: **Strongly Related** (methodologically the best example of explanation → user finds the cause → local repair of the specification, with repair accuracy measured)
- Concepts: Feasibility and plan quality. Discrepancy between the system solution and the user's expectation. Interpretation in the sense of an error in the domain specification.
- What they do (implemented):
  - Natural-language contrastive explanations for multi-robot task allocation, scheduling and motion planning.
  - Before execution, the user reviews the solution and poses a foil in a "User Sandbox" (e.g., "why is robot X not assigned to task Y?"). The system returns a foil solution and an explanation.
  - The user then edits domain values (robot traits, speeds, task requirements) one at a time to fix specification errors.
- What they evaluate:
  - Design: N=22 in person, between subjects (11 CE-MRS vs 11 CMAoE tabular baseline). Six emergency-response scenarios, 4 of which had 5 injected errors each.
  - Error resolution: 62.7%±23.5% of errors resolved with CE-MRS vs 29.5%±9.4% with the baseline. Trait and requirement errors were significantly better (p<0.001 and p<0.01). Speed errors showed no significant difference.
  - Extraneous corrections: 1.33±0.60 vs 5.24±5.63.
  - Correctness judgment did **not** improve after explanation (post-explanation classification 18.2% vs 22.7%).
- Overlap with CoGround: pre-execution review of a plan result, "why not" foils, cause linked to specific attributes or constraints, local repair, and measured repair accuracy and efficiency.
- Differences: multi-robot emergency domain, not household. Tabular and text interface, no spatial After state. Users repair the *model specification*, not the user goal. No AR.
- Scores: Purpose 2 | Timing 3 | Outcome 1 | Discrepancy 2 | Explanation 3 | Repair 3 | Evaluation 3
- Notes: this is a useful negative result for CoGround: explanations improved repair but not users' overall judgment of whether the solution was correct. That bears on CoGround's "judge at a glance" goal.

### Schroder2026_SHRIMP
- Title / Authors / Year / Venue / DOI or URL: *SHRIMP: Iterative Refinement of Robot Task Plans* / Mya Schroder, Yuna Hwang, Callie Y. Kim, Leqian Cheng, Jeffrey Li-cheng Liu, Chenchen Zheng, Xinning He, Bilge Mutlu / 2026 / UIST '26 (Detroit) / DOI 10.1145/3830398.3830644; arXiv:2608.08884
- verified: true (full PDF read) ; peer_reviewed: true
- Class: **Strongly Related** (LLM robot plan shown, edited and simulated before execution)
- Concepts: Interpretation (language → primitives), Feasibility (validation checks). GoalSatisfaction is judged by the user through the simulation.
- What they do (implemented):
  - An LLM plus vision turns a natural-language task (e.g., "Clean up the table") into a **hierarchical primitive plan** of high-level primitives (pick_and_place, pour) and low-level primitives (move_to_pose, grasp, …) with editable parameters.
  - Users iteratively refine the plan through re-prompting or explicit edits to primitives and parameters, and **validate each revision in simulation** before executing on a bimanual physical robot.
  - Automatic plan validation checks viability, e.g., that grasp primitives target the correct objects.
- What they evaluate:
  - Design: within-subjects ablation, N=35, about 50 minutes. Conditions were Plan+Edit, Plan-Only and No-Plan. Tasks were Set the Table, Prepare (drink?) and Clean the Table.
  - Measures: perceived autonomy, TOROS transparency, NASA-TLX, SUS, success and time. Analyzed with mixed models.
  - Plan+Edit vs No-Plan: higher perceived autonomy (M 3.50 vs 3.15, p=.007) and transparency (TOROS M 4.77 vs 4.34, p=.026).
  - Plan+Edit vs Plan-Only: **higher task load** (TLX 37.86 vs 29.92, p=.002).
  - **No significant differences in SUS or task success.** Viewing the plan alone (Plan-Only) gave no benefit over No-Plan.
- Overlap with CoGround: pre-execution preview of the robot plan via simulation, local repair of actions and parameters, household-like kitchen tabletop tasks, and an evaluation including load.
- Differences: the representation is a step list plus simulation playback, not an at-a-glance After state. No explicit causal explanation of *why* the goal will not be met. No household rules. Desktop GUI, not AR.
- Scores: Purpose 2 | Timing 3 | Outcome 2 | Discrepancy 1 | Explanation 1 | Repair 3 | Evaluation 3
- Notes: evidence relevant to CoGround's motto ("explore the plan only when needed"): exposing and editing the full plan raised workload without improving success. Viewing the plan alone did not help.

### Eifler2022_PlanPropertyDependencies
- Title / Authors / Year / Venue / DOI or URL: *Evaluating Plan-Property Dependencies: A Web-Based Platform and User Study* / Rebecca Eifler, Martim Brandao, Amanda Coles, Jeremy Frank, Jörg Hoffmann / 2022 / ICAPS 2022 (vol. 32, pp. 687–691) / DOI 10.1609/icaps.v32i1.19858. Earlier versions: Eifler & Hoffmann, XAIP'20, arXiv:2011.09705; Eifler et al., *Plan-Property Dependencies are Useful: A User Study*, XAIP'21, NASA NTRS 20210015671.
- verified: true (ICAPS OJS listing via search, NTRS abstract and arXiv abstract) ; peer_reviewed: true (ICAPS) / workshop for the earlier versions
- Class: **Strongly Related** (explains *why a desired goal or property cannot be satisfied* and supports iterative goal modification, evaluated at scale)
- Concepts: GoalSatisfaction (which soft goals or properties can be jointly satisfied) and Feasibility (oversubscription).
- What they do (implemented): an iterative planning web tool. The user asks "why does the plan not satisfy p?" and the system answers "because then we would have to forgo q", using plan-property entailments (minimal unsolvable goal subsets / MUGS). The user then picks which properties to enforce and replans.
- What they evaluate: crowd-worker studies comparing users with and without explanations. ICAPS 2022: N=100 per domain × 3 domains (per search snippet of ICAPS page; I did not read the full PDF). XAIP'21: N=40 per domain on Prolific, about 40 minutes. Result: users with explanations found **better trade-offs** (higher utility of the chosen property set).
- Overlap with CoGround: users understand which goals cannot all be met and why (conflict with another goal or constraint), then modify enforced goals and replan. Evaluated with task outcome quality.
- Differences: abstract logistics / NoMystery-style domains. No spatial or physical representation. Not a robot. Explanation is goal-goal conflict, not object, action or rule in a scene. Not a pre-execution check of a robot's plan result.
- Scores: Purpose 2 | Timing 2 | Outcome 0 | Discrepancy 2 | Explanation 3 | Repair 2 | Evaluation 3
- Notes: N=100/domain comes from a search snippet of the ICAPS page. Confirm against the full paper before citing.

### Fouilhe2026_LLMGoalConflict
- Title / Authors / Year / Venue / DOI or URL: *Exploring Plan Space through Conversation: An Agentic Framework for LLM-Mediated Explanations in Planning* / Guilhem Fouilhé, Rebecca Eifler, Antonin Poché, Sylvie Thiébaux, Nicholas Asher / 2026 / EUMAS 2026 (accepted; DOI 10.1007/978-3-032-39395-1_37) / https://arxiv.org/abs/2603.02070
- verified: true (abstract plus HTML results section) ; peer_reviewed: true (per arXiv comment)
- Class: Partially Related
- Concepts: GoalSatisfaction (goal-conflict explanations)
- What they do: multi-agent LLM framework that translates free-form user questions ("why can't I have A and B?") into formal goal-conflict queries in the IPEXCO iterative planning platform. Users revise enforced goals at each iteration.
- What they evaluate: Prolific, N=131, between subjects (65 template-based vs 66 LLM). "Parents' Afternoon" task with 19 goals and 224 conflicts, 15-minute limit. Time was about 14 minutes in both groups. Mean utility 20.8 vs 20.5, not significant. 15.2% vs 13.8% reached the maximum. The LLM group asked fewer questions (11.4 vs 22.8) and rated the system more helpful (significant on two items). 91% translation accuracy.
- Overlap: why-not / goal-conflict explanation → user modifies goals, with an objective outcome measure.
- Differences: not robotic, not spatial, no After state.
- Scores: Purpose 2 | Timing 2 | Outcome 0 | Discrepancy 2 | Explanation 3 | Repair 2 | Evaluation 3
- Notes: a null result on objective utility. The LLM interface improved perceived helpfulness, not decision quality.

### Sreedharan2019_Unsolvability
- Title / Authors / Year / Venue / DOI or URL: *Why Can't You Do That HAL? Explaining Unsolvability of Planning Tasks* / Sarath Sreedharan, Siddharth Srivastava, David Smith, Subbarao Kambhampati / 2019 / IJCAI 2019 / arXiv version: *Why Couldn't You do that? Explaining Unsolvability of Classical Planning Problems in the Presence of Plan Advice*, arXiv:1903.08218
- verified: true (arXiv abstract; IJCAI listing via mlanthology) ; peer_reviewed: true
- Class: Partially Related (foundational for "why is the goal not achievable")
- Concepts: Feasibility (unsolvability) and GoalSatisfaction (unachievable subgoal)
- What they do: use hierarchical abstractions to find the minimal abstraction level and the **unachievable subgoal / landmark** that makes the problem unsolvable. They also handle user plan advice that makes the problem unsolvable.
- What they evaluate: computational efficiency on benchmarks plus "user studies" (per abstract) showing that the explanations help users. I did not extract N or effect sizes; treat these as unknown.
- Overlap: explains *why* a requested goal cannot be achieved, framed as a robot refusing a request. The cause is a specific subgoal or precondition.
- Differences: no visualization of outcome, no repair interface, classical planning benchmarks.
- Scores: Purpose 2 | Timing 2 | Outcome 0 | Discrepancy 1 | Explanation 3 | Repair 0 | Evaluation 1
- Notes: user-study details are NR in what I read.

### Raman2013_SorryDave
- Title / Authors / Year / Venue / DOI or URL: *Sorry Dave, I'm Afraid I Can't Do That: Explaining Unachievable Robot Tasks Using Natural Language* / Vasumathi Raman, Constantine Lignos, Cameron Finucane, Kenton C. T. Lee, Mitch Marcus, Hadas Kress-Gazit / 2013 / RSS IX / DOI 10.15607/RSS.2013.IX.023. Companion: Raman & Kress-Gazit, *Explaining Impossible High-Level Robot Behaviors*, IEEE T-RO 2013 (implemented in LTLMoP, with an interactive game for exploring causes). Follow-up: *Unsynthesizable Cores*, arXiv:1409.1455.
- verified: true for RSS (proceedings abstract). T-RO details: false (only via search snippets; the PDF fetch failed).
- peer_reviewed: true
- Class: Partially Related (classic "explain unachievable task → user repairs specification")
- Concepts: Feasibility (unsynthesizable / unrealizable specs) and Interpretation (NL → LTL)
- What they do: natural-language task → GR(1) LTL. If the specification is unsynthesizable, the system finds a minimal unsatisfiable or unrealizable core and explains it in natural language, so that the user "work[s] with the robot to identify a concise cause of failure and arrive at a usable controller". Hospital assistant examples.
- What they evaluate: the RSS paper uses illustrative examples; no user study was confirmed. A search snippet says a later journal version ("Provably correct reactive control from natural language", Autonomous Robots) has a simulated search-and-rescue user study (unverified).
- Overlap: explanation of why the commanded task is impossible, tied to specific specification clauses, followed by user repair of the specification before execution.
- Differences: no visual or spatial outcome. Formal specifications, not household goals. Evaluation NR.
- Scores: Purpose 2 | Timing 3 | Outcome 0 | Discrepancy 1 | Explanation 3 | Repair 2 | Evaluation NR

### Das2021_XAIRobotFailures
- Title / Authors / Year / Venue / DOI or URL: *Explainable AI for Robot Failures: Generating Explanations that Improve User Assistance in Fault Recovery* / Devleena Das, Siddhartha Banerjee, Sonia Chernova / 2021 / ACM/IEEE HRI 2021 / DOI 10.1145/3434073.3444657; arXiv:2101.01625
- verified: true (abstract plus PDF) ; peer_reviewed: true
- Class: Partially Related (explanation → user identifies the cause and the solution; household pick-and-place)
- Concepts: Feasibility (execution failure cause)
- What they do: explanations of the cause of a failure during plan execution for non-experts. Explanation types: action-based (AB), context-based (CB), and each with history (AB-H, CB-H). An encoder-decoder model generates explanations automatically.
- What they evaluate:
  - Design: MTurk. 80 recruited, 70 analyzed, about 13–15 per condition. Baseline stage, then an explanation stage on 12 failures shown as GIF snapshots in a simulated home.
  - Measures: F1 for Failure Identification (FId) and Solution Identification (SId).
  - Results: context-based explanations with history were most effective (e.g., CB-H vs None, t(37)=2.561, p=.038 on one measure). Model-generated explanations generalized to an unseen office environment and were as effective as scripted ones.
- Overlap: measures whether the user correctly identifies the *cause* and the *repair*, in a household manipulation setting.
- Differences: the timing is post-failure (execution time), not a pre-execution preview. No predicted After state. The user chooses a solution from options and does not actually modify the plan.
- Scores: Purpose 1 | Timing 1 | Outcome 1 | Discrepancy 1 | Explanation 3 | Repair 2 | Evaluation 3
- Notes: the FId/SId metric design can be borrowed for CoGround's evaluation of "understanding the cause".

### Diehl2022_WhyDidIFail
- Title / Authors / Year / Venue / DOI or URL: *Why Did I Fail? A Causal-Based Method to Find Explanations for Robot Failures* / Maximilian Diehl, Karinne Ramirez-Amaro / 2022 / IEEE RA-L 7(4), 8925–8932 / DOI 10.1109/LRA.2022.3188889; arXiv:2204.04483
- verified: true (arXiv abstract) ; peer_reviewed: true
- Class: Methodologically Relevant
- Concepts: Feasibility (failure causation)
- What they do: learn a causal Bayesian network from simulation. Contrastive explanation = the nearest success state, found by BFS over causal variables (e.g., "the upper cube was stacked too high and too far to the right").
- What they evaluate: sim-to-real prediction accuracy of 70% and 72% (cube stacking, sphere dropping). **No user study.**
- Overlap: counterfactual "what would have to change for success", which is effectively a minimal repair suggestion grounded in object parameters. The causal model can also *predict* failure before execution (their later work, "explain, predict and prevent", RAS 2023, not verified here).
- Differences: low-level manipulation parameters, no user interaction, no outcome visualization.
- Scores: Purpose 1 | Timing 1 | Outcome 1 | Discrepancy 1 | Explanation 3 | Repair 1 | Evaluation 0

### Krarup2021_ContrastiveModelRestrictions
- Title / Authors / Year / Venue / DOI or URL: *Contrastive Explanations of Plans through Model Restrictions* / Benjamin Krarup, Senka Krivic, Daniele Magazzeni, Derek Long, Michael Cashmore, David E. Smith / 2021 / JAIR 72, 533–612 / DOI 10.1613/jair.1.12813; arXiv:2103.15575
- verified: true (JAIR page via search and full PDF) ; peer_reviewed: true
- Class: Partially Related
- Concepts: Feasibility and GoalSatisfaction (user-imposed constraints)
- What they do: each contrastive user question ("why A rather than B?", "why not action X?") is compiled into a PDDL2.1 constraint, a restricted hypothetical plan (HPlan) is generated, and the two plans are compared side by side. The user iterates restrictions; this is effectively interactive constraint negotiation.
- What they evaluate:
  - Study 1: N=15. Users' plan questions are predominantly contrastive (χ²(2,168)=273.25, p<0.00001), which leads to a taxonomy of questions.
  - Study 2: N=20 (10 vs 10). Full framework with highlighted plan diffs vs HPlan only. Explanation Satisfaction median 4.0 vs 3.0 (t=5.57, p≈1e-7). Time spent was 24.2 vs 21.1 minutes. Most used questions: remove or add actions.
- Overlap: users add or remove actions and constraints to explore alternatives and compare plan outcomes. Diff highlighting is analogous to Before/After differences.
- Differences: warehouse planning domain. Satisfaction is the only outcome measure; no repair accuracy. Not a robot and not spatial.
- Scores: Purpose 1 | Timing 2 | Outcome 1 | Discrepancy 1 | Explanation 2 | Repair 2 | Evaluation 2

### Valmeekam2021_RADARX
- Title / Authors / Year / Venue / DOI or URL: *RADAR-X: An Interactive Interface Pairing Contrastive Explanations with Revised Plan Suggestions* / Karthik Valmeekam, Sarath Sreedharan, Sailik Sengupta, Subbarao Kambhampati / 2021 / AAAI 2021 demo (pp. 16051–16053); XAIP'20; ICAPS 2022 industry track version / arXiv:2011.09644
- verified: true (listings and abstract via search) ; peer_reviewed: true (demo track)
- Class: Partially Related
- Concepts: GoalSatisfaction (latent preferences) and Feasibility
- What they do: the user poses a foil (an alternative plan). The system gives a minimally contrastive explanation, treats the foil as evidence of latent preferences, and proposes **revised plans** in three interaction modes.
- What they evaluate: NR (demo; no user study found).
- Overlap: why-not explanation followed by repair suggestions through dialogue.
- Differences: decision-support GUI, not a robot. No outcome visualization. No evaluation.
- Scores: Purpose 1 | Timing 2 | Outcome 0 | Discrepancy 1 | Explanation 2 | Repair 2 | Evaluation NR

### Chakraborti2017_ModelReconciliation
- Title / Authors / Year / Venue / DOI or URL: *Plan Explanations as Model Reconciliation: Moving Beyond Explanation as Soliloquy* / Tathagata Chakraborti, Sarath Sreedharan, Yu Zhang, Subbarao Kambhampati / 2017 / IJCAI-17, pp. 156–163 / DOI 10.24963/ijcai.2017/23
- verified: true (IJCAI proceedings page) ; peer_reviewed: true
- Class: Background (foundational theory)
- Concepts: Feasibility and optimality under mismatched human/robot models
- What they do: an explanation is the minimal set of model updates to the human's model that makes the robot's plan optimal in that model (MCE/MME).
- What they evaluate: computational only.
- Overlap: frames user confusion as a model mismatch. In CoGround terms, a user's "why is this object not moved?" is resolved by revealing a rule, precondition or object state the user did not know.
- Differences: no UI, no repair by the user, no outcome visualization.
- Scores: Purpose 1 | Timing 1 | Outcome 0 | Discrepancy 1 | Explanation 3 | Repair 0 | Evaluation 0

### Chakraborti2019_MREmpirical
- Title / Authors / Year / Venue / DOI or URL: *Plan Explanations as Model Reconciliation — An Empirical Study* / Tathagata Chakraborti, Sarath Sreedharan, Sachin Grover, Subbarao Kambhampati / 2019 / ACM/IEEE HRI 2019 (Daegu) / arXiv:1802.01013
- verified: true (abstract plus PDF) ; peer_reviewed: true (HRI 2019 per ASU Pure record)
- Class: Methodologically Relevant
- Concepts: Feasibility and optimality
- What they do: a mock search-and-rescue task with a robot (internal agent) and a human commander (external). The human's map differs from the robot's, and explanations are given as model differences annotated on the map.
- What they evaluate:
  - Study 1: N=22 analyzed (12 in C1, 10 in C2). Participants generated explanations themselves; they used model differences and contrastive (MCE-like) explanations.
  - Study 2: a gamified evaluation in which participants judged the plan as optimal or satisficing, could request an explanation at a point cost, and could pass. Trust dynamics were also measured. I did not extract Study 2 numbers.
- Overlap: the user evaluates the robot plan *before* accepting it and requests explanations on demand. This is close to "explore the plan only when needed". Explanations are spatial annotations on a map.
- Differences: optimality judgment rather than goal satisfaction. No repair. 2D map.
- Scores: Purpose 2 | Timing 3 | Outcome 1 | Discrepancy 2 | Explanation 3 | Repair 0 | Evaluation 2
- Notes: the on-demand explanation-at-a-cost design is analogous to CoGround's progressive disclosure.

### Kumar2022_VizXP
- Title / Authors / Year / Venue / DOI or URL: *VizXP: A Visualization Framework for Conveying Explanations to Users in Model Reconciliation Problems* / Ashwin Kumar, Stylianos Loukas Vasileiou, Melanie Bancilhon, Alvitta Ottley, William Yeoh / 2022 / ICAPS 2022, pp. 701–709 / DOI 10.1609/icaps.v32i1.19860
- verified: true (ICAPS listing via search) ; peer_reviewed: true
- Class: Methodologically Relevant
- Concepts: Feasibility
- What they do: visualizes the state and action space and model-reconciliation explanations (domain-based and problem-based).
- What they evaluate: a user study comparing visualization vs text-only. Understanding was better with visualization, best combined with text (per the project page). N not extracted.
- Overlap: evidence that visual explanation representations beat text for planning explanations.
- Differences: abstract planning visualization, not situated. No repair.
- Scores: Purpose 1 | Timing 1 | Outcome 1 | Discrepancy 1 | Explanation 2 | Repair 0 | Evaluation 2

### Chakraborti2018_ProjectionAware
- Title / Authors / Year / Venue / DOI or URL: *Projection-Aware Task Planning and Execution for Human-in-the-Loop Operation of Robots in a Mixed-Reality Workspace* / Tathagata Chakraborti, Sarath Sreedharan, Anagha Kulkarni, Subbarao Kambhampati / 2018 / IROS 2018, pp. 4476–4482 / DOI 10.1109/IROS.2018.8593830
- verified: true (PDF read) ; peer_reviewed: true
- Class: Partially Related (XAIP plus AR, from the model-reconciliation group)
- Concepts: Interpretation (intent communication)
- What they do: HoloLens projections reveal the robot's future intentions. Projection-aware planning trades plan cost against intent revelation. The human can interact with holograms, e.g., gaze-select a tool, which forces the robot to replan.
- What they evaluate: demonstration only; no user study in the PDF.
- Overlap: AR plus planner integration and human-triggered replanning.
- Differences: execution-time intent projection, not a pre-execution outcome check. No explanation of failure.
- Scores: Purpose 1 | Timing 2 | Outcome 1 | Discrepancy 0 | Explanation 1 | Repair 1 | Evaluation 0

### Besch2026_MRAssistive
- Title / Authors / Year / Venue / DOI or URL: *Model Reconciliation through Explainability and Collaborative Recovery in Assistive Robotics* / Britt Besch, Tai Mai, Jeremias Thun, Markus Huff, Jörn Vogel, Freek Stulp, Samuel Bustamante / 2026 / ICRA 2026 (accepted) / arXiv:2601.06552
- verified: true (abstract plus HTML) ; peer_reviewed: true (accepted)
- Class: Partially Related
- Concepts: Feasibility (unknown object or action, missing precondition) and Interpretation
- What they do:
  - An LLM predicts and explains divergences between the robot's model and the user's mental model, with no formal user model. Divergence types: unknown object type, unknown object instance, unknown action type, blocked action with an unmet precondition, false divergence.
  - The user then **corrects** the robot by natural-language rebuttal (e.g., "the drawer is actually closed!"), which is mapped to a PDDL state overwrite. For an unknown object instance, a VLM localizes the object or the user teleoperates to it.
  - Wheelchair-mounted manipulator plus digital twin.
- What they evaluate: **no user study** ("a future user study would be appropriate"). Unit tests on 40 episodes × 3 runs: 100% object localization, 78.79% precondition explanation (92.42% with a term dictionary), 78.12% recovery suggestions. Real-robot qualitative demo.
- Overlap: explanation linked to the object, action or precondition, followed by local user repair of the world model so that the task becomes feasible.
- Differences: language only. No outcome or After visualization. No human evaluation.
- Scores: Purpose 2 | Timing 2 | Outcome 0 | Discrepancy 2 | Explanation 3 | Repair 2 | Evaluation 0

### Lee2025_VeriPlan
- Title / Authors / Year / Venue / DOI or URL: *VeriPlan: Integrating Formal Verification and LLMs into End-User Planning* / Christine P. Lee, David Porfirio, Xinyu Jessica Wang, Kevin Zhao, Bilge Mutlu / 2025 / CHI '25 / arXiv:2502.17898
- verified: true (abstract) ; peer_reviewed: true
- Class: Partially Related (rule-aware verification of LLM plans, with the user adjusting constraints)
- Concepts: GoalSatisfaction (rule satisfaction) and Feasibility
- What they do: an LLM planner plus a rule translator (rules extracted from the prompt and refined with the user), **flexibility sliders** (how strictly each rule must hold), and a model checker that verifies the LLM plan against the rules and reports violations.
- What they evaluate: within subjects, N=12, compared with LLM output without verification. Improvements in perceived quality, usability and satisfaction. Details not extracted.
- Overlap: closely matches "household rules" as constraints. Violations are surfaced, and the user locally relaxes or tightens constraints.
- Differences: everyday human planning (not robot execution). Text UI. No spatial outcome.
- Scores: Purpose 2 | Timing 3 | Outcome 0 | Discrepancy 2 | Explanation 2 | Repair 2 | Evaluation 2

### Kim2026_RoboCritics
- Title / Authors / Year / Venue / DOI or URL: *RoboCritics: Enabling Reliable End-to-End LLM Robot Programming through Expert-Informed Critics* / Callie Y. Kim, Nathan Thomas White, Evan He, Frederic Sala, Bilge Mutlu / 2026 / HRI 2026 / arXiv:2603.06842
- verified: true (abstract) ; peer_reviewed: true
- Class: Partially Related
- Concepts: Feasibility (safety and motion constraints)
- What they do: expert-designed critics analyze **motion-level execution traces** (simulated) of LLM-generated robot programs for joint-speed limits, collisions and unsafe end-effector poses. Flagged issues are shown with **one-click fixes**, and structured feedback goes back to the LLM for iterative refinement. UR3e robot, web UI.
- What they evaluate: between subjects, N=18 vs a baseline LLM interface. Fewer safety violations, better execution quality, and changed verification and revision behaviour (no numbers extracted).
- Overlap: pre-execution detection of problems linked to a specific action or constraint, plus local repair.
- Differences: industrial arm programming. Safety constraints, not user goals. No After state.
- Scores: Purpose 1 | Timing 3 | Outcome 1 | Discrepancy 2 | Explanation 2 | Repair 3 | Evaluation 3

### Mahadevan2025_ImageInThat
- Title / Authors / Year / Venue / DOI or URL: *ImageInThat: Manipulating Images to Convey User Instructions to Robots* / Karthik Mahadevan, Blaine Lewis, Jiannan Li, Bilge Mutlu, Anthony Tang, Tovi Grossman / 2025 / HRI 2025 / arXiv:2503.15500
- verified: true (abstract) ; peer_reviewed: true
- Class: Partially Related (cross-check with the outcome-representation agent)
- Concepts: Interpretation (user specifies the desired After state)
- What they do: a timeline-style editor where users drag objects in images of the environment to define desired states. Edits become pick-and-place instructions and are captioned for confirmation. The system suggests likely next instructions.
- What they evaluate: kitchen tasks (simulated) vs a text baseline. Faster with ImageInThat, and preferred. Different error types; extraneous steps were added. Image-to-code succeeded 7/10.
- Overlap: Before/After image representation of goal states, and direct manipulation to change targets.
- Differences: the user *authors* the goal state; it is not a robot-predicted outcome. No explanation of infeasibility.
- Scores: Purpose 1 | Timing 3 | Outcome 2 | Discrepancy 1 | Explanation 0 | Repair 2 | Evaluation 3

### Ikeda2025_MARCER
- Title / Authors / Year / Venue / DOI or URL: *MARCER: Multimodal Augmented Reality for Composing and Executing Robot Tasks* / Bryce Ikeda, Maitrey Gramopadhye, LillyAnn Nekervis, Daniel Szafir / 2025 / HRI 2025, pp. 529–539 / DOI 10.1109/HRI61500.2025.10974232
- verified: false (bibliographic metadata and project page summary only; full paper not read) ; peer_reviewed: true
- Class: Partially Related (cross-check with the AR agent)
- Concepts: Interpretation and Feasibility
- What they do (per project page and poster): an LLM converts speech or text into trigger-action robot programs. The AR interface lets users parameterize and validate them, set virtual constraints, and preview robot activity via a digital twin.
- What they evaluate: unknown (not confirmed).
- Scores: Purpose 1 | Timing 3 | Outcome 2 | Discrepancy NR | Explanation NR | Repair 2 | Evaluation NR

### Lee2024_REX
- Title / Authors / Year / Venue / DOI or URL: *REX: Designing User-centered Repair and Explanations to Address Robot Failures* / Christine P. Lee, Pragathi Praveena, Bilge Mutlu / 2024 / DIS '24 / DOI 10.1145/3643834.3661559; arXiv:2405.16710
- verified: true (abstract) ; peer_reviewed: true
- Class: Methodologically Relevant
- Concepts: Feasibility (conflicts from human error, multi-user conflicts, hardware limits)
- What they do: vignette scenarios in which a robot performs *automated* repair plus explanation.
- What they evaluate: online N=162 and in-person N=24 (Temi robot). Automated repair plus explanation increased trust, satisfaction and utility. The preferred strategy depended on risk severity and type. Users wanted to know the data behind a repair and its privacy risks.
- Overlap: explanation-plus-repair design space in home-like scenarios.
- Differences: the robot repairs (not the user). Post-failure. No outcome preview.
- Scores: Purpose 1 | Timing 1 | Outcome 0 | Discrepancy 1 | Explanation 2 | Repair 1 | Evaluation 2

### Khanna2023_ExplanationStrategiesFailures
- Title / Authors / Year / Venue / DOI or URL: *Effects of Explanation Strategies to Resolve Failures in Human-Robot Collaboration* / Parag Khanna, Elmira Yadollahi, Mårten Björkman, Iolanda Leite, Christian Smith / 2023 / IEEE RO-MAN 2023, pp. 1829–1836 / DOI 10.1109/RO-MAN57019.2023.10309394; arXiv:2309.10127
- verified: true (abstract) ; peer_reviewed: true
- Class: Methodologically Relevant
- Concepts: Feasibility (execution failure)
- What they do: in a shelf-filling task, the robot explains its failure (action / cause / history levels) and how to resolve it (handover, or the human completes the step).
- What they evaluate: resolution success depended on explanation level × failure type. Novices were more satisfied, and satisfaction depended on previous rounds. N not extracted.
- Overlap: explanation level affects repair success, i.e., measured repair performance.
- Differences: execution time. Physical help, not plan modification.
- Scores: Purpose 1 | Timing 0 | Outcome 0 | Discrepancy 1 | Explanation 2 | Repair 2 | Evaluation 2

### Liu2023_REFLECT
- Title / Authors / Year / Venue / DOI or URL: *REFLECT: Summarizing Robot Experiences for Failure Explanation and Correction* / Zeyi Liu, Arpit Bahety, Shuran Song / 2023 / CoRL 2023 / arXiv:2306.15724
- verified: true (abstract via search listings) ; peer_reviewed: true
- Class: Background (adjacent: execution-time)
- Concepts: GoalSatisfaction (subgoal success verification) and Feasibility (plan errors)
- What they do: an LLM over hierarchical multisensory summaries verifies each subgoal. On failure it explains the cause (execution vs planning error), and a correction planner produces a recovery plan. Evaluated on the RoboFail dataset.
- What they evaluate: explanation and correction accuracy on RoboFail; no user study.
- Overlap: explicit goal-condition verification plus causal explanation plus corrective plan, in household (AI2-THOR plus real) tasks.
- Differences: post-execution and fully automatic.
- Scores: Purpose 1 | Timing 0 | Outcome 1 | Discrepancy 2 | Explanation 2 | Repair 1 | Evaluation 1

### Briggs2015_SorryICantDoThat
- Title / Authors / Year / Venue / DOI or URL: *"Sorry, I Can't Do That": Developing Mechanisms to Appropriately Reject Directives in Human-Robot Interactions* / Gordon Briggs, Matthias Scheutz / 2015 / AAAI Fall Symposium (AI for HRI) / https://cdn.aaai.org/ocs/11709/11709-51307-1-PB.pdf
- verified: false (search snippets and press coverage only; full title from memory, so confirm it) ; peer_reviewed: true (symposium, lightly reviewed)
- Class: Background
- Concepts: Feasibility (knowledge, capacity, timing, social role, normative / safety felicity conditions)
- What they do: the robot rejects commands whose felicity conditions fail and gives a specific explanation. The human can supply information that satisfies the failed condition (e.g., "I will catch you").
- What they evaluate: video demonstrations.
- Overlap: rule- and norm-aware refusal with an explanation that invites a local repair. A conceptual precursor of CoGround's rule-linked explanations.
- Scores: Purpose 1 | Timing 2 | Outcome 0 | Discrepancy 1 | Explanation 2 | Repair 1 | Evaluation 0

### Liang2019_iRoPro
- Title / Authors / Year / Venue / DOI or URL: *End-User Programming of Low- and High-Level Actions for Robotic Task Planning* (iRoPro) / Ying Siu Liang, Damien Pellier, Humbert Fiorino, Sylvie Pesty / 2019 / IEEE RO-MAN 2019 / arXiv:2103.14342
- verified: true (abstract) ; peer_reviewed: true
- Class: Methodologically Relevant
- Concepts: Feasibility (PDDL preconditions and effects)
- What they do: users teach actions by demonstration with inferred, editable conditions and use a PDDL task planner. When planning fails, a debug menu summarizes the domain with natural-language hints (per a search snippet; not confirmed in the paper).
- What they evaluate: N=21, eight tasks. Users of varying backgrounds could learn and use the system.
- Overlap: users edit action preconditions after a plan failure, i.e., model repair by the end user.
- Scores: Purpose 1 | Timing 2 | Outcome 0 | Discrepancy 1 | Explanation 1 | Repair 2 | Evaluation 2

### Brandao2021_ExplainMotionPlanning
- Title / Authors / Year / Venue / DOI or URL: *Towards Providing Explanations for Robot Motion Planning* / Martim Brandão, Gerard Canal, Senka Krivić, Daniele Magazzeni / 2021 / ICRA 2021, pp. 3927–3933
- verified: false (metadata via the author PDF listing and dblp snippet; content not read) ; peer_reviewed: true
- Class: Background
- Concepts: Feasibility
- What they do: a taxonomy of motion-planning explanations (cost, constraints, parameters, robot design, environment) for failure and contrastive questions, with an associated user study (not verified). The environment-based failure explanation line (Hauser's minimum constraint removal; ICRA 2024 "Generating Environment-based Explanations of Motion Planner Failure"; RO-MAN 2025 "Robot Arms Too Short?") is the motion-level analogue of "which object blocks the goal".
- Scores: Purpose 1 | Timing 1 | Outcome 0 | Discrepancy 1 | Explanation 2 | Repair 1 | Evaluation NR

### Wohlrab2024_OBJUST
- Title / Authors / Year / Venue / DOI or URL: *What Impact do my Preferences Have? A Framework for Explanation-Based Elicitation of Quality Objectives for Robotic Mission Planning* / Rebekka Wohlrab, Michael Vierhauser, Erik Nilsson / 2024 / REFSQ 2024
- verified: false (search snippet of the abstract only) ; peer_reviewed: true
- Class: Methodologically Relevant
- Concepts: GoalSatisfaction (preferences vs plan)
- What they do: visual and textual contrastive explanations of generated mission plans help users understand the impact of their preference settings, then adjust them.
- What they evaluate: reported improved understanding (details unverified).
- Scores: Purpose 1 | Timing 2 | Outcome 1 | Discrepancy 1 | Explanation 2 | Repair 2 | Evaluation NR

---

## Agent summary

### Top 5 closest works (to CoGround's "understand why the goal is not met → locally repair" loop)
1. **X-OOHRI** (Wang, Kari, Abtahi, HRI 2026)
   - Scores: P2 T3 O2 D2 E3 R3 Ev2.
   - The only verified system combining in-situ AR, pre-execution infeasibility detection tied to object and robot constraints, explanation tags, preview animations of resolutions, and user or system local repair.
   - Gaps: per-action scope, no whole-scene Before/After, no household rules, exploratory N=14 with no baseline.
2. **CE-MRS** (Schneider, Wu, Das, Chernova, RA-L 2024)
   - Scores: P2 T3 O1 D2 E3 R3 Ev3.
   - Pre-execution solution review, "why not" foils, local repair of specification errors.
   - Measured repair accuracy: 62.7% vs 29.5% errors resolved.
   - Explanations did *not* improve users' overall correctness judgment.
3. **SHRIMP** (Schroder … Mutlu, UIST 2026)
   - Scores: P2 T3 O2 D1 E1 R3 Ev3.
   - LLM plan, hierarchical primitives, simulation preview and local edits before execution.
   - N=35: higher control and transparency, but higher TLX and no success gain. Viewing the plan alone did not help.
4. **Eifler et al. plan-property dependencies** (ICAPS 2022; XAIP'20/'21)
   - Scores: P2 T2 O0 D2 E3 R2 Ev3.
   - "Why not p? Because then not q" goal-conflict explanations with iterative goal modification.
   - Large crowd studies showing better trade-offs. Follow-up: **Fouilhé et al. EUMAS 2026** (LLM-mediated, N=131, null on utility).
5. **Das, Banerjee, Chernova** (HRI 2021)
   - Scores: P1 T1 O1 D1 E3 R2 Ev3.
   - Household pick-and-place. Context-plus-history explanations improve users' failure *and* solution identification (F1).
   - Post-failure rather than pre-execution, but its evaluation metrics transfer directly.

Honourable mentions: Besch et al. ICRA 2026 (LLM model reconciliation plus user correction of object and precondition beliefs; no user study), VeriPlan CHI 2025 (rule verification of LLM plans with adjustable rule flexibility; N=12), RoboCritics HRI 2026 (critics flag violations with one-click fixes before execution; N=18), Raman et al. RSS 2013 / T-RO 2013 (explain unsynthesizable robot tasks, then the user fixes the spec), and Sreedharan et al. IJCAI 2019 (unachievable-subgoal explanations).

### Key gaps observed (evidence, not novelty claims)
- **No verified work combines all of the following:** (a) a robot-predicted After state of the whole scene, (b) goal-satisfaction discrepancy vs the user's request, (c) a cause linked to object, action or *household rule*, and (d) local repair with replanning, evaluated on repair accuracy and time. Each element exists separately: (a) in ImageInThat, MARCER, SHRIMP's simulation; (b) in Eifler, Fouilhé, REFLECT; (c) in X-OOHRI, Besch, VeriPlan, Raman; (d) in CE-MRS, X-OOHRI, SHRIMP.
- XAIP explanation work (model reconciliation, unsolvability, plan-property dependencies) is evaluated almost exclusively in abstract, non-spatial domains with text or 2D UIs. VizXP shows that visualization beats text there, but nothing in that line is situated or physical.
- Robot failure explanation work (Das, Khanna, Diehl, REX, REFLECT) is mostly **post-failure / execution-time**, which is adjacent to CoGround's scope.
- **Repair performance is rarely measured.** CE-MRS (fraction of errors resolved, extraneous edits), Das (solution-identification F1), Khanna (resolution success) and Eifler (trade-off quality) are the exceptions, and they are good templates for CoGround's DVs.
- **Contrary and negative results to note:**
  - CE-MRS: explanations did not improve correctness judgment.
  - SHRIMP: plan exposure plus editing raises workload, plan-only gives no benefit, and task success is unchanged.
  - Fouilhé: an LLM explanation interface did not improve objective utility.
  - X-OOHRI: users reported AR unfamiliarity and some needed technical support.
  - These cut against assuming that richer plan or explanation exposure improves outcomes.

### Open doubts
- The ICAPS 2022 N=100/domain figure for Eifler et al. comes from a search snippet. The XAIP'21 figure is N=40/domain (NTRS). Confirm against the PDF.
- Sreedharan IJCAI 2019 user-study N and results were not extracted.
- Raman T-RO 2013 content and the Autonomous Robots user study are unverified (PDF fetch failed).
- MARCER's evaluation is unknown (not read).
- The Briggs & Scheutz title is from memory and snippets.
- The Brandão ICRA 2021 user-study claim is unverified.

### Papers another agent should cross-check
- **AR / outcome-preview agent:** MARCER (HRI 2025) evaluation; ImageInThat (HRI 2025; image-based goal-state editing); X-OOHRI's precursor OOHRI and the cited GhostAR / HoloSpot; *Happily Error After* (VR correction of robot perception errors, arXiv:2306.14589, N=56 per snippet); the Springer 2026 digital-twin plus Blockly end-user development paper (Intelligent Service Robotics, doi 10.1007/s11370-026-00758-7, unverified); Luebbers et al. RSS 2023 (AR justifications).
- **LLM-planning agent:** "Closing the Communication Loop for Robotic Failures: Multi-Turn, BT-Grounded Explanations with LLMs" (ICRA 2026); Merlo et al. 2025 (arXiv:2507.20870, NL refinement of video-derived plans); COMMET (arXiv:2509.04836, household human-induced conflicts); "Do What? Teaching VLA Models to Reject the Impossible" (arXiv:2508.16292); CLARA (arXiv:2306.10376, infeasible-command classification); Plover (arXiv:2607.15193, plan-centric steering of GUI agents: an inspect/revise-before-execute design analogue).
- **Failure-explanation / evaluation agent:** "Enabling Novices to Diagnose Robot Failures by Aligning Users' Mental Models" (UMAP 2025); "Interpretable Robot Failure Attribution for Remote Robot Supervisors" (RO-MAN 2026); "Robot Arms Too Short? Explaining Motion Planning Failures using Design Optimization" (RO-MAN 2025); "Generating Environment-based Explanations of Motion Planner Failure" (ICRA 2024); Diehl & Ramirez-Amaro's "explain, predict and prevent failures" (RAS 2023), which predicts failure *before* execution and is closest to CoGround's timing in that line.
