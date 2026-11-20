# A2 — Spatial Preview Researcher (Stream A)

Focus: robot plan / motion-intent visualization in AR/MR, ghost robots and virtual surrogates, future-state and predicted-environment visualization (object end positions, goal-state rendering, before/after comparison, digital-twin and simulation preview), augmented and diminished reality for robots, AR robot programming with task preview, end-user AR task specification for household and rearrangement robots. Non-AR equivalents (2D, VR, simulation) are included.

## Search log

**Seed: Suzuki et al. CHI 2022 survey.** I downloaded the arXiv PDF (2203.03254) and extracted the relevant taxonomy text.
- Under "Information-3. Plan and Activity" the survey lists "1) a plan of the robot's motion and behavior, 2) simulation results of the programmed behavior, 3) visualization of a target and goal, 4) progress of the current task".
- Under "Virtual Replica and Ghost Effects" it cites [76, 169, 372, 451, 494] and the ghost effect [51, 372].
- Under "Purpose-1 Facilitate Programming" it covers simulated behaviors, GhostAR [51], and home automation (Roboshop [263]).
- All of the survey's examples are robot-centric (trajectory, target pose, simulated arm motion). None renders the predicted state of the environment after a multi-object task.

**Web queries** (WebSearch, standard and extended):
- "augmented reality robot preview predicted outcome object rearrangement before execution user study"
- "mixed reality household robot plan preview goal state visualization tidying user verification"
- "diminished reality robot task preview objects"
- "augmented reality robot programming pick-and-place virtual object preview final placement end-user"
- "LLM robot plan visualization augmented reality user verify correct plan before execution"
- "scene editing as teleoperation digital twin"
- "augmented reality visualize robot task plan symbolic states PDDL intermediate states"
- "robot simulation preview of manipulation outcome before execution digital twin trust error detection"
- "Robotist/ViPO" (no hit; this surfaced Previewed Reality)
- "robot rearrangement goal image shown to user for approval"
- "AR robot before/after end-state visualization object placement comprehension"
- "user study comparing representations of robot task plan for detecting plan errors before execution" (this surfaced PerceptTwin)
- "digital twin household robot preview before execution mixed reality"
- "AR household tidying user specifies destinations LLM"
- "MR predicted object states ghost objects pick-and-place HoloLens"
- "Remixed Reality"
- "goal configuration preview user edits rearrangement"
- "Projection-aware task planning Chakraborti"
- "robot vacuum AR coverage preview"
- Name lookups for Walker 2018/2019, Rosen 2019, MARCER, RoboVisAR, Arévalo Arboleda 2020

**Verification sources:** arXiv abstract and HTML pages (MRPilot, ImageInThat, GhostObjects, X-OOHRI, PerceptTwin, SHRIMP, RoboCritics, ARROCH, HoloSpot, Newbury, Wang 2023, Qu 2026, Walker 2023 survey); PDFs read with pdftotext (Previewed Reality IROS'17, Gadre 2019, X-OOHRI full text, Weidner 2023, Suzuki 2022). The Semantic Scholar API was heavily rate-limited, so I used it only for a few lookups and forward-citation lists.

**Snowballing:**
- *Backward from GhostObjects and X-OOHRI related work:* HoloSpot, Marcer ("AR to display virtual outcomes"), X-HR Training (Wang 2023), GhostAR, RoboVisAR, V.Ra, Rosen, Walker.
- *Backward from ImageInThat related work:* "AR virtual surrogates", "scene editing as teleoperation" (SEaT), "asynchronous assembly goals in VR", Black et al. on image-editing diffusion for goal images, Li et al. on simulation evaluation with digital twins.
- *Backward from MRPilot related work:* Walker 2018/2023, Suzuki 2022, Hedayati 2018, Chen & Barnes 2014 (plan and rationale transparency).
- *Forward via the S2 citations endpoint:*
  - ImageInThat is cited by SHRIMP (UIST'26), RoboCritics (HRI'26), GhostObjects, and an HRI-LLM systematic review (CHI'26).
  - GhostObjects is cited by X-OOHRI and "Delegate the Details" (ISMAR'26).
  - X-OOHRI is cited by MRPilot, Qu et al. 2026 (AR vs mobile SA), and Uncertain Pointer (CHI'26, situated feedforward).
  - Walker 2018 is cited by MRPilot, ERUPT (XR motion-planner toolkit), and MRPoS.
- *Concept expansion:* future state → "near-future perception" (Previewed Reality); digital twin → PerceptTwin and SEaT; plan-verification accuracy → PerceptTwin and Rosen; diminished reality → InvisibleRobot / Taylor 2020, Remixed Reality, mediated reality.

**What I did not find, despite active hunting:** a paper that renders the *predicted post-execution state of a multi-object household scene* in situ (AR), juxtaposes it with the current state (before/after or diff), uses diminished reality to hide objects that will move, and evaluates how fast and accurately users judge goal satisfaction. The closest pieces are spread across several works: X-OOHRI, GhostObjects, ImageInThat, PerceptTwin, MRPilot, SHRIMP, Wang 2023, and Previewed Reality. This is an observation from my search, not a novelty claim; other agents should keep searching (see cross-check list).

## Papers

### Wang2026_XOOHRI
- Title / Authors / Year / Venue / DOI or URL: Explainable OOHRI: Communicating Robot Capabilities and Limitations as Augmented Reality Affordances / Lauren W. Wang, Mohamed Kari, Parastoo Abtahi / 2026 / HRI 2026 / DOI 10.1145/3757279.3785569, arXiv 2601.14587
- verified: true (arXiv abstract and full PDF text read) ; peer_reviewed: true
- Class: Strongly Related
- Concepts: Feasibility (primary). Interpretation is partial (object-oriented commands). Goal satisfaction is implicit, because the twin shows the target pose.
- What they do (implemented):
  - AR on Quest with life-size, world-aligned virtual twins (GhostObjects) placed in a simulated environment. A VLM encodes object properties and robot limits into object-oriented structures.
  - Users directly manipulate twins to issue tasks (pick-and-place, fill, vacuum area).
  - Feasibility is checked per action precondition (reach, aperture, payload, collision). Infeasible objects or placements turn red.
  - "Explanation tags" name the limiting precondition (e.g., "Too high to reach").
  - Mixed-initiative resolutions: Auto (move other objects to make the action feasible), Alternative (different object of the same class, or a different pose), Ignore, or a user-driven fix.
  - Choosing a resolution plays an animated "Preview" of the action sequence. Everything happens before execution, and the robot runs after the user confirms.
- What they evaluate: an exploratory (non-controlled) study with N=14 (12 male, aged 18–25), think-aloud, in two parts (pick-and-place plus fill; vacuum area). All participants resolved the constraints, either proactively or after reading the tags (they recalled virtually repositioning objects in 12 cases, physically opening doors in 10, and choosing system alternatives in 2). Workload on NASA-TLX was low, with slightly higher mental demand attributed to AR unfamiliarity. SUS was 79.3. There was no baseline and no measure of accuracy or speed of outcome judgment.
- Overlap with CoGround: pre-execution, in-situ AR; a predicted object target pose is visible on a life-size twin; failure causes are linked to object, action, and constraint; local repair (alternative object or pose, auto-resolve) with a preview.
- Differences: the user authors the goal per object, so there is no robot-generated plan to audit. There is no whole-scene "After" view and no before/after comparison. Explanations cover robot capability limits only, not household rules or user preferences. Evaluation is exploratory, with no goal-satisfaction judgment measure.
- Scores: Purpose 2 | Timing 3 | Outcome 2 | Discrepancy 2 | Explanation 3 | Repair 3 | Evaluation 1
- Notes / evidence quote or location in paper: Sec. 3 "Color coding … red indicates an action limitation"; "Explanation tags … labeling constraint causes"; "Choosing a resolution may trigger a Preview animation". Sec. 6: "As no comparable systems exist … we opted for an exploratory study."

### Wang2025_GhostObjects
- Title / Authors / Year / Venue / DOI or URL: GhostObjects: Instructing Robots by Manipulating Spatially Aligned Virtual Twins in Augmented Reality / Lauren W. Wang, Parastoo Abtahi / 2025 / UIST 2025 Adjunct / DOI 10.1145/3746058.3758451, arXiv 2508.11022
- verified: true (S2 abstract and arXiv HTML) ; peer_reviewed: true (adjunct/poster-level)
- Class: Partially Related
- Concepts: Interpretation (the user specifies the goal precisely); goal state specification
- What they do (implemented): world-aligned, life-size virtual twins in AR. Users move twins to the desired goal pose (e.g., a home-tidying example that snaps blocks into a basket), with lasso multi-select and snap-back to default. The authors say the twins "help them visualize the anticipated outcomes of robot tasks."
- What they evaluate: none. There are two walkthrough scenarios, and the paper says further evaluation is future work.
- Overlap with CoGround: the goal state is shown as twins overlaid at their real-world target poses, in a tidying scenario.
- Differences: the goal is user-authored rather than robot-predicted. There is no plan, no discrepancy check, no before/after view, and no study.
- Scores: Purpose 1 | Timing 3 | Outcome 2 | Discrepancy 0 | Explanation 0 | Repair 1 | Evaluation 0
- Notes: its related work names "co-located virtual objects … as non-interactive previews of instruction outcomes" as an existing idea, but cites no specific paper for it. Worth hunting.

### Mahadevan2025_ImageInThat
- Title / Authors / Year / Venue / DOI or URL: ImageInThat: Manipulating Images to Convey User Instructions to Robots / Karthik Mahadevan, Blaine Lewis, Jiannan Li, Bilge Mutlu, Anthony Tang, Tovi Grossman / 2025 / HRI 2025 / DOI 10.1109/HRI61500.2025.10974179, arXiv 2503.15500
- verified: true (abstract and HTML full text) ; peer_reviewed: true
- Class: Strongly Related (non-AR, 2D)
- Concepts: Interpretation and GoalSatisfaction (the user authors the state sequence directly)
- What they do (implemented):
  - A 2D timeline of environment images. The first step is the initial state, and each later step is an edited image (move object, toggle fixture).
  - Changed objects are highlighted, and hovering over a step animates the difference from the selected step. This is effectively a before/after diff between states.
  - An LLM proposes goal locations and "plausible next steps". Captions are auto-generated and editable. The edited images are translated into robot code.
- What they evaluate:
  - Within-subjects study, N=10, comparing against a text-based natural-language baseline. Four kitchen tasks.
  - Time: 110.8 s vs 363.88 s (p<.001).
  - Total errors: 2.26 vs 2.55 (not significant). Missing steps: 1.26 vs 2.0 (p<.05).
  - Confidence: 6.42 vs 4.71 (p<.001). SUS: 87.75 vs 61.75 (p<.001).
  - Image-to-code success: 10/10, 10/10, 8/10, 7/10.
- Overlap with CoGround: an explicit state-based (image) representation of intermediate and goal states, with change highlighting between steps; it supports inspecting intermediate states.
- Differences: these are user-authored instructions, not a preview of a robot plan's predicted outcome. It is 2D, not in situ. There is no physics or feasibility check (the authors note uncertainty about whether the robot understood "on top"). There is no explanation of failures, and correction is one-way only.
- Scores: Purpose 2 | Timing 3 | Outcome 2 | Discrepancy 1 | Explanation 0 | Repair 2 | Evaluation 2
- Notes: the text baseline is a worst case (step-by-step), and the sample is small. Both are acknowledged in the paper.

### Gauthier2026_PerceptTwin
- Title / Authors / Year / Venue / DOI or URL: PerceptTwin: Semantic Scene Reconstruction for Iterative LLM Planning and Verification / Charlie Gauthier, Sacha Morin, Liam Paull / 2026 / ICRA 2026 (per arXiv comments) / arXiv 2606.04226
- verified: true (abstract and HTML text) ; peer_reviewed: true (ICRA acceptance stated on arXiv; not checked in IEEE Xplore)
- Class: Strongly Related (methodologically very relevant)
- Concepts: separates Feasibility ("consistency": precondition violations) from GoalSatisfaction ("logic": all skills execute but the final state may be wrong).
- What they do (implemented): automatically builds an interactive simulation (digital twin) from the robot's semantic perception map, using open-vocabulary objects, generated 3D assets, affordances, and commonsense condition checks. LLM plans are executed in simulation before running on hardware. An LLM judge checks correctness and preference alignment, and simulator feedback is used for iterative replanning.
- What they evaluate:
  - Automatic: plan success improves by about 39% on average across GPT-5, GPT-5 Mini, and GPT-5 Nano planners.
  - Human plan verification: an online A/B test with N=93. Participants predicted whether a plan would succeed or fail. Baseline: point-cloud video plus scene image. Treatment: a video of the plan executing in the PerceptTwin simulation plus the image. Scenarios: Blocks, Cones, Kitchen.
  - Accuracy improved in both question categories, but only the consistency (precondition) category was significant ("up to 18%" improvement). The logic/final-state category was **not** significant.
  - The authors attribute part of the effect to humans mis-reading skill names (assuming two-armed, human-like execution).
- Overlap with CoGround: a pre-execution preview of the simulated plan outcome, including the object end state. It measures human accuracy in judging plan success, and its consistency/logic split corresponds to the Feasibility/GoalSatisfaction distinction.
- Differences: the preview is a video, not in situ, and has no before/after juxtaposition. There is no interactive inspection or repair by the human, and explanations are hard-coded precondition error messages. The task is binary success prediction, not judging degree of fulfillment.
- Scores: Purpose 3 | Timing 3 | Outcome 2 | Discrepancy 2 | Explanation 1 | Repair 0 (human) | Evaluation 3
- Notes: the important finding for CoGround is that a simulation-execution video did **not** significantly help users detect wrong final states ("logic" failures). This is a contrary data point on whether showing an outcome preview alone supports goal-satisfaction judgment. The exact accuracies are only in Fig. 7, which I did not read as text.

### Yang2026_MRPilot
- Title / Authors / Year / Venue / DOI or URL: MRPilot: Supervising and Intervening LLM-Based Multi-Robot Teams through Mixed Reality / Xiaoran Yang, Xun Qian, Yang Zhan, Nathan Tran, Ziyi Liu, Qiao Jin / 2026 / arXiv preprint (no venue listed) / arXiv 2610.07477
- verified: true (abstract and HTML) ; peer_reviewed: false (preprint)
- Class: Strongly Related
- Concepts: Interpretation (the Forming stage resolves references), Feasibility (dependencies, conflicts, coverage), with partial Goal satisfaction
- What they do (implemented):
  - MR system with four stages: Forming, Reviewing (pre-execution), Following, Repairing. Plans are "structured commitments" with a rationale field.
  - Reviewing presents two candidate plans in a synchronized situated MR view and a Mini-Map overview, showing paths, assignment, order, and dependencies. It does **not** visualize predicted object end states.
  - Repair can be local (edit one field of one robot's commitment, e.g., the place) or global (LLM regenerates the plan). Checkpoints allow reverting.
- What they evaluate:
  - Within-subjects study, N=20, in a VR-simulated two-story home. Baseline: a text/voice LLM chat interface with the same planner.
  - Plan Selection time: 110.58 s → 37.01 s (p<.001). Prompts: 12.4 → 8.4.
  - NASA-TLX Mental Demand: 75.25 → 23.00. SART overall SA: Mdn 7 → 33.5.
  - Trust (MDMT), transparency (TOROS), and perceived control all improved (p≤.01).
- Overlap with CoGround: pre-execution review in a household setting, an "overview vs situated" split similar to "glance vs explore", and local repair of a specific field followed by replanning.
- Differences: it is multi-robot, focused on assignment and paths, and does not render the post-execution environment state. There is no before/after view and no discrepancy visualization against the user's intent. The baseline is weak (chat only), and the study is in VR, not real AR.
- Scores: Purpose 2 | Timing 3 | Outcome 1 | Discrepancy 1 | Explanation 2 | Repair 3 | Evaluation 3
- Notes: the very large effect sizes against a chat baseline should be interpreted with caution.

### Schroder2026_SHRIMP
- Title / Authors / Year / Venue / DOI or URL: SHRIMP: Iterative Refinement of Robot Task Plans / Mya Schroder, Yuna Hwang, Callie Y. Kim, Leqian Cheng, Jeffrey Li-cheng Liu, Chenchen Zheng, Xinning He, Bilge Mutlu / 2026 / UIST 2026 / arXiv 2608.08884
- verified: true (abstract and HTML) ; peer_reviewed: true
- Class: Strongly Related (non-AR, simulation preview)
- Concepts: Interpretation (NL → hierarchical primitive plan) and Feasibility (automatic grasp-target, arm-arm, and arm/object collision checks); goal satisfaction is judged by the user in simulation.
- What they do (implemented): an LLM generates a hierarchical primitive plan. Users can run the whole plan or step through it in an Isaac Sim digital twin, so they "spot problems like unintended object motion or poor placement." Repair options: re-prompt, reorder or add primitives, edit pose parameters (a red arrow shows the target pose), and revert through task history.
- What they evaluate:
  - Within-subjects ablation, N=35. Conditions: Plan+Edit, Plan-Only, No-Plan. Tasks: set table, prepare snack, clean table.
  - Plan+Edit vs No-Plan: autonomy 3.50 vs 3.15 (p=.007); TOROS transparency 4.77 vs 4.34 (p=.026).
  - Workload was higher with Plan+Edit than Plan-Only (37.86 vs 29.92, p=.002).
  - No differences in task success or SUS (all below average).
  - **Plan-Only did not beat No-Plan**: seeing the plan alone was not enough. No error-detection metric was reported.
- Overlap with CoGround: a pre-execution outcome preview in simulation (including object placement), stepping through intermediate states, and local repair.
- Differences: the preview is on a 2D desktop rather than in situ, and the view is the robot/simulation rather than a summarized before/after of the environment. There is no discrepancy highlighting and no explanation linked to cause. Errors are not measured.
- Scores: Purpose 2 | Timing 3 | Outcome 2 | Discrepancy 1 | Explanation 1 | Repair 3 | Evaluation 2
- Notes: a useful contrary result: plan visibility without editing gave no benefit, and editing increased workload.

### Kim2026_RoboCritics
- Title / Authors / Year / Venue / DOI or URL: RoboCritics: Enabling Reliable End-to-End LLM Robot Programming through Expert-Informed Critics / Callie Y. Kim, Nathan Thomas White, Evan He, Frederic Sala, Bilge Mutlu / 2026 / HRI 2026 / arXiv 2603.06842
- verified: true (abstract only) ; peer_reviewed: true
- Class: Partially Related
- Concepts: Feasibility (safety and motion violations)
- What they do (implemented): critics analyze motion-level execution traces of LLM-generated robot programs for joint-speed violations, collisions, and unsafe end-effector poses. They show transparent feedback with one-click fixes and feed structured messages back to the LLM. Web interface with a UR3e robot.
- What they evaluate: between-subjects study, N=18, against a baseline LLM interface. RoboCritics reduced safety violations, improved execution quality, and changed how users verified and refined programs. Numbers were not read.
- Overlap with CoGround: pre-execution detection of plan problems with explanation and targeted one-click repair.
- Differences: only motion and safety feasibility, not environment outcome or goal satisfaction; not AR.
- Scores: Purpose 1 | Timing 3 | Outcome 0 | Discrepancy 2 | Explanation 2 | Repair 3 | Evaluation 2
- Notes: check the full text for whether the trace is shown in simulation.

### Wang2023_XHRTraining
- Title / Authors / Year / Venue / DOI or URL: Explainable Human-Robot Training and Cooperation with Augmented Reality / Chao Wang, Anna Belardinelli, Stephan Hasler, Theodoros Stouraitis, Daniel Tanneberg, Michael Gienger / 2023 / CHI 2023 Extended Abstracts / DOI 10.1145/3544549.3583889, arXiv 2302.01039
- verified: true (arXiv abstract and HTML; CHI EA venue confirmed via the X-OOHRI reference list) ; peer_reviewed: true (extended abstract)
- Class: Strongly Related (concept); thin evidence
- Concepts: Interpretation and Feasibility (plan validation)
- What they do (implemented): Use case 2: a STRIPS planner composes learned skills into a plan for a novel kitchen task (e.g., "prepare an ice tea"). **Before execution**, the robot's virtual avatar executes the plan on holographic digital twins of the real objects in AR, and the user approves or corrects the plan by speech.
- What they evaluate: nothing (demo/use-case paper).
- Overlap with CoGround: the closest conceptual precedent for an "in-situ simulated plan outcome on object twins, then validate" household workflow.
- Differences: robot-centric animation rather than an at-a-glance After state; the correction mechanism is not described; no study.
- Scores: Purpose 2 | Timing 3 | Outcome 2 | Discrepancy 0 | Explanation 0 | Repair 1 | Evaluation 0
- Notes: quote: "Before execution, the robot will ask the user to validate the plan in AR."

### Horikawa2017_PreviewedReality
- Title / Authors / Year / Venue / DOI or URL: Previewed Reality: Near-future perception system / Yuta Horikawa, Asuka Egashira, Kazuto Nakashima, Akihiro Kawamura, Ryo Kurazume / 2017 / IROS 2017. Journal version: Egashira et al., Advanced Robotics 35(1):19–30, 2021 (journal not checked by me).
- verified: true for IROS'17 (full PDF read) ; peer_reviewed: true
- Class: Partially Related
- Concepts: none of the three directly. The goal is safety and anticipation; it forecasts physical outcomes.
- What they do (implemented): an informationally structured environment (ROS-TMS) tracks furniture, objects, humans, and robots. A dynamics simulator (Gazebo) forecasts near-future events from the current real state, such as a robot failing a grasp and the object bouncing away, and renders them from the user's tracked viewpoint as AR overlays (VR HMD with a stereo camera; v2.0 uses HoloLens).
- What they evaluate: only system validation (viewpoint registration, virtual robot motion followed by the real robot). There is no user study.
- Overlap with CoGround: renders the **predicted future physical state, including objects**, in situ from the user's viewpoint, in a home or service context.
- Differences: the aim is safety and hazard awareness, not task fulfillment. There is no plan inspection or repair, and no user evaluation.
- Scores: Purpose 1 | Timing 3 | Outcome 2 | Discrepancy 0 | Explanation 0 | Repair 0 | Evaluation 0
- Notes: Fig. 12 shows "Dynamic simulation of object grasping by Gazebo … the robot fails to grasp the object, which then bounces away." A good classic precedent for "future-state AR", and often missed by HRI surveys.

### Ikeda2025_MARCER
- Title / Authors / Year / Venue / DOI or URL: MARCER: Multimodal Augmented Reality for Composing and Executing Robot Tasks / Bryce Ikeda, Maitrey Gramopadhye, LillyAnn Nekervis, Daniel Szafir (author order reported inconsistently) / 2025 / HRI 2025, pp. 529–539 / DOI 10.1109/HRI61500.2025.10974232
- verified: false (only the author's project page and a search-result summary were seen; full text not read) ; peer_reviewed: true
- Class: Partially Related
- Concepts: Interpretation (LLM turns NL into trigger-action programs)
- What they do (implemented): an LLM combined with trigger-action programming and AR. AR provides "real-time, visual previews and feedback" for parameterizing and validating programs. The X-OOHRI paper characterizes MARCER as using "AR to display virtual outcomes". A 2024 poster mentions a digital twin used to preview robot activities.
- What they evaluate: a usability evaluation is mentioned; details are unknown.
- Overlap with CoGround: LLM plan with AR preview for validation before execution.
- Differences: unclear whether the preview shows the object/environment end state or only robot motion.
- Scores: Purpose 1 | Timing 3 | Outcome NR | Discrepancy NR | Explanation NR | Repair NR | Evaluation NR
- Notes: **cross-check needed** (full text should be open since March 2026).

### Li2022_SEaT
- Title / Authors / Year / Venue / DOI or URL: Scene Editing as Teleoperation: A Case Study in 6DoF Kit Assembly / Yulong Li, Shubham Agrawal, Jen-Shuo Liu, Steven K. Feiner, Shuran Song (author list from memory; search results confirmed only Li, Agrawal, and Liu) / 2021 arXiv, IROS 2022 (venue from memory) / arXiv 2110.04450
- verified: false for venue and full author list (abstract-level content seen through search results) ; peer_reviewed: unknown
- Class: Partially Related
- Concepts: Interpretation (scene-centric goal specification)
- What they do (implemented): scene completion builds digital twins of real objects. Users specify the goal scene by manipulating the twins, and "action snapping" refines the input before the robot plan is generated.
- What they evaluate: simulation and real-robot experiments, plus a user study with N=10 against end-effector teleoperation; SEaT was significantly better in efficiency and success.
- Overlap with CoGround: goal-state (After) representation using object twins; the robot works toward the edited scene.
- Differences: the user authors the goal rather than reviewing a robot-predicted outcome; industrial kitting, not household.
- Scores: Purpose 1 | Timing 3 | Outcome 2 | Discrepancy 0 | Explanation 0 | Repair 1 | Evaluation 2

### Rosen2019_MRIntent
- Title / Authors / Year / Venue / DOI or URL: Communicating and controlling robot arm motion intent through mixed-reality head-mounted displays / Eric Rosen, David Whitney, Elizabeth Phillips, Gary Chien, James Tompkin, George Konidaris, Stefanie Tellex / 2019 / IJRR 38(12–13):1513–1526. Earlier version: ISRR 2017 / Springer "Robotics Research" 2020 (arXiv 1708.03655).
- verified: true (bibliographic details confirmed in the Suzuki references and search records; abstract-level content via search summary) ; peer_reviewed: true
- Class: Methodologically Relevant
- Concepts: Feasibility (collision judgment)
- What they do (implemented): HoloLens overlay of a planned Baxter arm motion as a ghost replica. Users can adjust the end-effector goal pose with gestures.
- What they evaluate: within-subjects study, N=32. Users classified planned motions as colliding or not colliding with table objects, comparing MR, a 2D display, and no visualization. MR gave **+16% accuracy and −62% time** relative to the next-best condition.
- Overlap with CoGround: the canonical evidence that in-situ preview improves both speed and accuracy of pre-execution judgment. Its binary-judgment task paradigm can be adapted to goal satisfaction.
- Differences: shows arm trajectory, not environment outcome; single motion, not a multi-step task.
- Scores: Purpose 1 | Timing 3 | Outcome 1 | Discrepancy 1 | Explanation 0 | Repair 1 | Evaluation 3

### Walker2018_MotionIntentAR
- Title / Authors / Year / Venue / DOI or URL: Communicating Robot Motion Intent with Augmented Reality / Michael Walker, Hooman Hedayati, Jennifer Lee, Daniel Szafir / 2018 / HRI 2018, pp. 316–324 / DOI 10.1145/3171221.3171253
- verified: true (bibliographic details confirmed in Suzuki 2022 refs; abstract via search summary) ; peer_reviewed: true
- Class: Background / Methodologically Relevant
- Concepts: none (motion intent)
- What they do (implemented): AR cues for aerial robot flight intent, including NavPoints, Arrows, Gaze, and Utilities.
- What they evaluate: a user study against a physical-orientation baseline. The designs improved task efficiency, with trade-offs in clarity and in perception of the robot as a teammate. Detailed numbers were not read.
- Overlap with CoGround: foundational design space for explicit vs implicit future-information cues.
- Differences: shows robot trajectory, not object or environment outcome.
- Scores: Purpose 0 | Timing 2 | Outcome 0 | Discrepancy 0 | Explanation 0 | Repair 0 | Evaluation 2

### Walker2019_VirtualSurrogates
- Title / Authors / Year / Venue / DOI or URL: Robot Teleoperation with Augmented Reality Virtual Surrogates / Michael E. Walker, Hooman Hedayati, Daniel Szafir / 2019 / HRI 2019, pp. 202–210 / DOI 10.1109/HRI.2019.8673306
- verified: true (bibliographic details; abstract-level summary) ; peer_reviewed: true
- Class: Partially Related
- Concepts: none (teleoperation)
- What they do (implemented): the user controls a virtual surrogate (ghost) robot, which gives foresight into where the real robot will go. Two interfaces: real-time control and waypoint delegation.
- What they evaluate: a user study (details not read).
- Overlap with CoGround: the "ghost" future-state concept, applied to the robot's own pose.
- Differences: robot pose only; teleoperation, not autonomous plan review.
- Scores: Purpose 0 | Timing 2 | Outcome 1 | Discrepancy 0 | Explanation 0 | Repair 1 | Evaluation NR

### Gadre2019_MREndUser
- Title / Authors / Year / Venue / DOI or URL: End-User Robot Programming Using Mixed Reality / Samir Yitzhak Gadre, Eric Rosen, Gary Chien, Elizabeth Phillips, Stefanie Tellex, George Konidaris / 2019 / ICRA 2019 (venue from memory; the PDF header did not show it) / h2r.cs.brown.edu/wp-content/uploads/gadre19.pdf
- verified: true (PDF abstract read; venue not confirmed) ; peer_reviewed: true (likely)
- Class: Methodologically Relevant
- Concepts: Feasibility (obstacles)
- What they do (implemented): HoloLens interface to create and edit waypoints, group them, preview the resulting action, then execute.
- What they evaluate: within-subjects study, N=20, MR vs 2D, two pick-and-place tasks. More users completed tasks with MR, in significantly less time, with lower NASA-TLX, higher usability, and higher naturalness.
- Overlap with CoGround: an MR-vs-2D comparison of preview-then-execute.
- Differences: shows motion, not outcome; the user authors the program.
- Scores: Purpose 0 | Timing 3 | Outcome 1 | Discrepancy 0 | Explanation 0 | Repair 2 | Evaluation 2

### Cao2019_GhostAR
- Title / Authors / Year / Venue / DOI or URL: GhostAR: A Time-space Editor for Embodied Authoring of Human-Robot Collaborative Task with Augmented Reality / Yuanzhi Cao, Tianyi Wang, Xun Qian, Pawan S. Rao, Manav Wadhawan, Ke Huo, Karthik Ramani / 2019 / UIST 2019 / DOI 10.1145/3332165.3347902
- verified: false for the abstract (the ACM page returned 403; bibliographic details confirmed in the Suzuki and X-OOHRI reference lists) ; peer_reviewed: true
- Class: Partially Related
- Concepts: none (authoring)
- What they do (implemented): users author human-robot collaborative tasks by role-playing. Human "ghosts" and robot trajectories are edited along a spatio-temporal timeline, with semi-transparent replicas giving a ghost effect.
- What they evaluate: not read.
- Overlap with CoGround: timeline and ghost representation of states over time, which is a precedent for "explore intermediate states".
- Differences: authoring, not reviewing a robot plan's outcome.
- Scores: Purpose 0 | Timing 2 | Outcome 1 | Discrepancy 0 | Explanation 0 | Repair 1 | Evaluation NR

### Chakraborti2018_ProjectionAware
- Title / Authors / Year / Venue / DOI or URL: Projection-Aware Task Planning and Execution for Human-in-the-Loop Operation of Robots in a Mixed-Reality Workspace / Tathagata Chakraborti, Sarath Sreedharan, Anagha Kulkarni, Subbarao Kambhampati / 2018 / IROS 2018, pp. 4476–4482 / DOI 10.1109/IROS.2018.8593830
- verified: false (bibliographic record and summary only) ; peer_reviewed: true
- Class: Partially Related
- Concepts: Interpretation (legibility of intentions)
- What they do (implemented): a task planner that trades plan cost against how well the plan reveals future intentions through MR projections (HoloLens). This is the explainable-planning (ICAPS UISP) link.
- What they evaluate: a joint human-robot activity demonstration; user-study details not read.
- Overlap with CoGround: links symbolic task plans to MR projection of future intent.
- Differences: optimizes legibility, not outcome review or repair.
- Scores: Purpose 1 | Timing 2 | Outcome 1 | Discrepancy 0 | Explanation 1 | Repair 0 | Evaluation NR
- Notes: hand to the A3 (explanation) agent.

### Chandan2021_ARROCH
- Title / Authors / Year / Venue / DOI or URL: ARROCH: Augmented Reality for Robots Collaborating with a Human / Kishan Chandan, Vidisha Kudalkar, Xiang Li, Shiqi Zhang / 2021 arXiv; ICRA 2021 (venue from memory, not shown on arXiv) / arXiv 2109.10400
- verified: true (arXiv abstract; venue unverified) ; peer_reviewed: unknown
- Class: Partially Related
- Concepts: Feasibility (team plan)
- What they do (implemented): AR see-through visualization of multi-robot states and planned actions in multi-room settings. Human feedback is incorporated into robot replanning.
- What they evaluate: real-robot delivery tasks with participants, where ARROCH beat a non-AR approach on user experience and team efficiency; in simulation it beat AR baselines.
- Overlap with CoGround: AR plan view combined with feedback, then replanning.
- Differences: navigation and delivery; no object end-state view.
- Scores: Purpose 1 | Timing 2 | Outcome 0 | Discrepancy 0 | Explanation 0 | Repair 2 | Evaluation 2

### Newbury2022_HandoverAR
- Title / Authors / Year / Venue / DOI or URL: Visualizing Robot Intent for Object Handovers with Augmented Reality / Rhys Newbury, Akansel Cosgun, Tysha Crowley-Davis, Wesley P. Chan, Tom Drummond, Elizabeth Croft / 2022 / RO-MAN 2022 / arXiv 2103.04055
- verified: true ; peer_reviewed: true
- Class: Background
- Concepts: Interpretation (the robot's belief about the object)
- What they do (implemented): AR shows the robot's belief about the object pose and its planned gripper grasp.
- What they evaluate: N=16, 12 handovers each. AR improved subjective experience and reduced handover time. Benefits for perceived safety and fluency were larger **when the robot made localization errors**.
- Overlap with CoGround: showing the robot's belief about object state helps humans detect robot misinterpretation.
- Differences: real-time handover, a single object.
- Scores: Purpose 1 | Timing 2 | Outcome 1 | Discrepancy 2 | Explanation 0 | Repair 1 | Evaluation 2

### ArevaloArboleda2020_AugmentedCues
- Title / Authors / Year / Venue / DOI or URL: There's More than Meets the Eye: Enhancing Robot Control through Augmented Visual Cues / Stephanie Arévalo Arboleda, Tim Dierks, Franziska Rücker, Jens Gerken / 2020 / HRI 2020 Companion, pp. 104–106 / DOI 10.1145/3371382.3378240
- verified: false (bibliographic details only; the claim that it shows a "ghost of grasped object at the placement location, color-coded for fit" comes from a search snippet) ; peer_reviewed: true (late-breaking report)
- Class: Partially Related
- Concepts: Feasibility (placement fit)
- What they do (implemented): AR visual cues for teleoperated pick-and-place, reportedly including a ghost of the object at the placement location that changes color depending on whether it fits.
- What they evaluate: not read.
- Overlap with CoGround: an object end-pose ghost with a feasibility color code.
- Differences: teleoperation; a single object.
- Scores: Purpose 1 | Timing 2 | Outcome 2 | Discrepancy 1 | Explanation 0 | Repair 0 | Evaluation NR

### SolerGarcia2024_HoloSpot
- Title / Authors / Year / Venue / DOI or URL: HoloSpot: Intuitive Object Manipulation via Mixed Reality Drag-and-Drop / Pablo Soler Garcia et al. (Pollefeys, Blum, Bauer) / 2024 / arXiv preprint (submitted to ICRA 2025) / arXiv 2410.11110
- verified: true ; peer_reviewed: false (as of the arXiv page)
- Class: Background
- Concepts: Interpretation (goal specification)
- What they do (implemented): a world-in-miniature "dollhouse" of a scanned room. Users drag and drop virtual objects to command Spot pick-and-place.
- What they evaluate: end-to-end testing, plus a user study reporting intuitive controls (N not given).
- Overlap with CoGround: miniature twin of a room with object goal placement. This is a candidate "overview" (WiM) representation for an After state.
- Differences: user-authored; no prediction or plan review.
- Scores: Purpose 0 | Timing 2 | Outcome 1 | Discrepancy 0 | Explanation 0 | Repair 0 | Evaluation 1

### Taylor2020_DRTelemanipulation
- Title / Authors / Year / Venue / DOI or URL: Diminished Reality for Close Quarters Robotic Telemanipulation / Ada V. Taylor, Ayaka Matsumoto, Elizabeth J. Carter, Alexander Plopski, Henny Admoni / 2020 / IROS 2020 (author list partly from memory). Preliminary version: "InvisibleRobot: Facilitating Robot Manipulation Through Diminished Reality", ISMAR 2019 Adjunct.
- verified: false (only search-result snippets and CMU listings; abstract page not opened, the CMU page returned 404) ; peer_reviewed: true
- Class: Methodologically Relevant
- Concepts: none
- What they do (implemented): an OST-HMD makes the robot arm appear transparent (diminished reality) so occluded objects become visible during telemanipulation.
- What they evaluate: according to the snippet, DR reduced user effort but had **drawbacks in task efficiency and user preference**.
- Overlap with CoGround: the only robot-specific DR user study found; directly relevant to CoGround's idea of using DR to hide objects that will move.
- Differences: it hides the robot, not objects; teleoperation, not plan preview.
- Scores: Purpose 0 | Timing 0 | Outcome 0 | Discrepancy 0 | Explanation 0 | Repair 0 | Evaluation 2
- Notes: a negative or mixed result for DR. Cross-check needed.

### Lindlbauer2018_RemixedReality
- Title / Authors / Year / Venue / DOI or URL: Remixed Reality: Manipulating Space and Time in Augmented Reality / David Lindlbauer, Andrew D. Wilson / 2018 / CHI 2018 / DOI 10.1145/3173574.3173703
- verified: true (MSR page summary; abstract-level) ; peer_reviewed: true
- Class: Methodologically Relevant
- Concepts: none
- What they do (implemented): a live 3D reconstruction from external depth cameras lets the user erase, move, copy, or recolor real objects and pause or replay time. This is a taxonomy of spatial, appearance, and temporal manipulations.
- What they evaluate: no user experiment (conceptual and system paper).
- Overlap with CoGround: technical and conceptual basis for showing a "moved" physical object in its future location while diminishing its current one, i.e., an in-situ before/after.
- Differences: no robot.
- Scores: Purpose 0 | Timing 0 | Outcome 1 | Discrepancy 0 | Explanation 0 | Repair 0 | Evaluation 0

### Weidner2023_MediatedReality
- Title / Authors / Year / Venue / DOI or URL: Perspectives on Mediated Reality for an Enhanced Automation Experience / Florian Weidner, Tobias Schwandt, Lewis Chuang, Wolfgang Broll / 2023 / AutomationXP23 workshop at CHI 2023, CEUR-WS Vol-3394 / https://ceur-ws.org/Vol-3394/short7.pdf
- verified: true (PDF text read) ; peer_reviewed: true (workshop position paper)
- Class: Background
- Concepts: none
- What they do (implemented): a position paper proposing combined AR and DR (mediated reality) for human-automation interaction. One scenario hides parts of a robot or machine and highlights a problem in human-robot work.
- What they evaluate: nothing.
- Overlap with CoGround: argues for DR and AR in automation transparency.
- Differences: vision only.
- Scores: Purpose 1 | Timing 0 | Outcome 0 | Discrepancy 0 | Explanation 1 | Repair 0 | Evaluation 0

### Qu2026_ARvsMobileSA
- Title / Authors / Year / Venue / DOI or URL: Better Situational Awareness in AR-HRC? A Comparative Study of Augmented Reality and Mobile Interfaces for Human-Robot Collaboration / Zhehan Qu, Christian Fronk, Jaewoong Jeong, Pavel Manakhov, Maria Gorlatova / 2026 / arXiv preprint / arXiv 2609.01461
- verified: true ; peer_reviewed: false
- Class: Methodologically Relevant (contrary AR evidence)
- Concepts: none
- What they do (implemented): an AR interface vs a mobile interface with equivalent information, for search-and-rescue human-robot collaboration.
- What they evaluate: between-subjects study, N=30, SAGAT at all three SA levels plus eye tracking. AR improved only perception-level robot SA. There was **no gain in higher-level robot SA or in environmental SA**, and gaze moved to the conformal visuals rather than the physical environment.
- Overlap with CoGround: a caution that in-situ overlays may not improve comprehension or projection (SA levels 2 and 3), which is exactly what judging goal satisfaction requires.
- Differences: monitoring during execution; safety domain.
- Scores: Purpose 0 | Timing 0 | Outcome 0 | Discrepancy 0 | Explanation 0 | Repair 0 | Evaluation 3
- Notes: quote: "Freeing the eyes from a screen is not the same as directing them to the world."

### Kapelyukh2023_DALLEBot
- Title / Authors / Year / Venue / DOI or URL: DALL-E-Bot: Introducing Web-Scale Diffusion Models to Robotics / Ivan Kapelyukh, Vitalis Vosylius, Edward Johns / 2023 / IEEE RA-L (accepted April 2023; earlier CoRL 2022 workshop) / arXiv 2210.02438
- verified: false (search-result summary only; venue from the RA-L preprint header shown in search results) ; peer_reviewed: true
- Class: Background
- Concepts: GoalSatisfaction (a generated goal image)
- What they do (implemented): a diffusion model "imagines" a goal image of a tidy arrangement, and the robot rearranges objects to match it. Fully autonomous; there is no user approval step.
- What they evaluate: users rated the final real-world arrangements after execution ("how happy would you be").
- Overlap with CoGround: an explicit rendered goal-state image exists inside the pipeline and could be shown to the user before execution, but it is not used that way.
- Differences: no human-facing pre-execution preview.
- Scores: Purpose 1 | Timing 0 | Outcome 2 (internal, not shown to the user) | Discrepancy 0 | Explanation 0 | Repair 0 | Evaluation 1

### Suzuki2022_ARRoboticsSurvey
- Title / Authors / Year / Venue / DOI or URL: Augmented Reality and Robotics: A Survey and Taxonomy for AR-enhanced Human-Robot Interaction and Robotic Interfaces / Ryo Suzuki, Adnan Karim, Tian Xia, Hooman Hedayati, Nicolai Marquardt / 2022 / CHI 2022 / arXiv 2203.03254
- verified: true (PDF text) ; peer_reviewed: true
- Class: Background
- Concepts: n/a
- What they do: a taxonomy over 460 papers. The relevant categories are "Plan and Activity" (motion plan, **simulation results**, **target/goal visualization**, task progress), "Virtual Replica and Ghost Effects", and "Facilitate Programming".
- Overlap with CoGround: provides the vocabulary. Its future-work section asks to "connect explainable robotics with AR to better visualize the robot's decision-making process embedded in real-world" and describes "explorable" what-if visualizations.
- Differences: every cited plan/activity example is robot-centric (trajectory, target position, simulated arm). None is an environment end-state for multi-object tasks.
- Scores: n/a (survey)

### Walker2023_VAMHRISurvey
- Title / Authors / Year / Venue / DOI or URL: Virtual, Augmented, and Mixed Reality for Human-Robot Interaction: A Survey and Virtual Design Element Taxonomy / Michael Walker, Thao Phung, Tathagata Chakraborti, Tom Williams, Daniel Szafir / 2022 arXiv; ACM THRI 2023 (venue from memory and the brief, not confirmed on the page) / arXiv 2202.11249
- verified: true (arXiv abstract; THRI venue unverified) ; peer_reviewed: true (likely)
- Class: Background
- What they do: a VDE taxonomy with four categories of virtual design elements, and a 30-year history.
- Notes: I did not read the full text. Its categories should be checked for any "virtual entity / environment-state" element showing predicted world state.

## Agent summary

**Top 5 closest works (Stream A):**
1. **X-OOHRI (Wang, Kari, Abtahi, HRI 2026).** Pre-execution AR with life-size object twins at their target poses; constraint explanations tied to object, action, and precondition; local repair through Auto or Alternative resolutions with an animated preview. Scores P2 T3 O2 D2 E3 R3 Ev1. Missing: a robot-generated plan to audit, a whole-scene before/after view, household-rule constraints, and a controlled evaluation.
2. **PerceptTwin (Gauthier et al., ICRA 2026).** A simulated-execution video of LLM plans before execution. N=93 human verification study. Separates "consistency" (feasibility) from "logic" (final-state correctness). Scores P3 T3 O2 D2 E1 R0 Ev3. **Contrary finding:** the simulation video improved detection of precondition failures significantly, but did **not** significantly improve detection of wrong final states.
3. **MRPilot (Yang et al., 2026 preprint).** MR review-before-execution in a (VR-simulated) home, with situated and overview views, rationales, and local or global repair. N=20 with large gains over an LLM chat baseline. Scores P2 T3 O1 D1 E2 R3 Ev3. Missing: rendering of object end states.
4. **SHRIMP (Schroder et al., UIST 2026).** LLM hierarchical plan with step-through digital-twin simulation (object placement visible) and local parameter editing. N=35 ablation. Scores P2 T3 O2 D1 E1 R3 Ev2. **Contrary findings:** Plan-Only was no better than No-Plan, editing raised workload, and task success was unchanged.
5. **ImageInThat (Mahadevan et al., HRI 2025).** A 2D timeline of edited scene images with change highlighting and an animated diff between steps. N=10, about 3x faster than text. Scores P2 T3 O2 D1 E0 R2 Ev2. Its instruction-side state representation is the closest to a before/after diff.

Close runners-up: Wang et al. CHI EA 2023 (an AR avatar executes the plan on holographic object twins for validation before execution; concept only, no study); Previewed Reality (Kurazume lab, IROS 2017; simulator-predicted future object states rendered in situ; no user study); Rosen et al. IJRR 2019 (the canonical evidence that MR plan preview improves pre-execution judgment: +16% accuracy, −62% time).

**Key gaps observed (from my search, not a novelty claim):**
- None of the papers I verified renders the *robot-predicted, post-execution state of the whole environment* in situ, juxtaposed with the current state (before/after or diff), for multi-object household tasks.
- Diminished reality has been used for robots only to hide the robot itself (Taylor/Admoni). It has not been used to hide objects that a plan will move. Remixed Reality (CHI'18) provides the technique without the robot context.
- No study measures speed and accuracy of judging the *degree* of goal fulfillment. PerceptTwin and Rosen measure binary success or collision judgments.
- Explanations in the AR systems cover robot capability or precondition limits (X-OOHRI, PerceptTwin, RoboCritics), not household rules or user preferences.

**Contrary or negative evidence to keep:**
- PerceptTwin: no significant gain for final-state ("logic") errors.
- SHRIMP: seeing the plan alone gave no benefit, and editing increased workload.
- Qu et al. 2026: AR improved only Level-1 SA, with no gain in comprehension or projection.
- Taylor et al. 2020: DR reduced effort but hurt efficiency and preference.
- Several large AR effects come from weak baselines (MRPilot vs chat, ImageInThat vs step-wise text).

**Open doubts:**
- MARCER's preview content (robot motion or object outcomes) is unverified.
- Venue and author details for SEaT, Gadre, ARROCH, and Walker 2023 THRI are partly from memory.
- Arévalo Arboleda 2020's ghost-placement claim comes only from a search snippet.
- PerceptTwin's per-condition accuracy numbers are only in a figure.
- GhostObjects mentions "co-located virtual objects used as non-interactive previews of instruction outcomes" without a citation; there may be an uncited precedent.

**Papers for other agents to cross-check:**
- **A1 (task/goal):** PerceptTwin (logic vs consistency split); DALL-E-Bot and Dream2Real (goal imagination usable as a preview); TidyBot (preference-based placement; no preview).
- **A3 (explanation/repair):** X-OOHRI (constraint tags plus resolution), RoboCritics (critics with one-click fix), Chakraborti et al. IROS 2018 (projection-aware planning), MRPilot (local vs global repair).
- **B1 (comprehension):** Rosen 2019 (judgment accuracy and time), Qu 2026 (SA levels with AR), Newbury 2022 (AR helps more when the robot errs), MRPilot (SART).
- **B2 (evaluation):** the PerceptTwin N=93 A/B paradigm, the SHRIMP ablation design, and Taylor 2020 DR (full text needed).
- **Still to fetch in full:** MARCER (HRI'25), Walker 2023 THRI taxonomy, the "Uncertain Pointer" situated-feedforward paper (CHI'26), ERUPT (XR motion-planner toolkit, arXiv 2510.02464), "Delegate the Details" (ISMAR'26), and Liu et al. 2026 (spatial embedding vs 2D overview, cited by MRPilot). The last is relevant to the "glance vs explore" design.
