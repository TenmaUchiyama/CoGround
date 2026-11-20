# B2 — Evaluation Researcher: Empirical evidence on AR/spatial vs 2D/non-spatial representations of robot plans, intent and predicted outcomes

Agent: B2 (Stream B). Date: 2026-11-19.
Question: What empirical evidence exists about AR/spatial vs 2D/non-spatial (and other) representations for understanding robot plans, intentions and predicted outcomes (speed, accuracy, clarity, cognitive load, error detection, repair), and which study designs were used?

Verification convention: `verified: true` = I read the original abstract (via OpenAlex/arXiv/publisher metadata) AND, where numbers are given, read them in the full text (arXiv / author PDF). `verified: partial` = abstract verified, but study details/numbers come from a secondary source or snippet (flagged inline). `verified: false` = not confirmed from an original source. Numbers I could not see are written "not verified" / "not reported".

---

## Search log

- Tools: WebSearch; OpenAlex API (abstracts + DOIs); arXiv API/PDFs parsed with `pdftotext`; author-hosted PDFs (Brown H2R, ASU, Monash, Unibas). Semantic Scholar API was rate-limited (429); ResearchGate/ACM full texts returned 403.
- Seed queries: "Communicating robot motion intent with augmented reality"; "mixed-reality head-mounted displays robot arm motion intent 2D display"; "end-user robot programming mixed reality 2D monitor"; "comparison of visualisation methods disambiguating verbal requests HMD projector monitor"; "augmented reality interface to verify robot learning"; "AR vs 2D display robot plan verification error detection NASA-TLX"; "AR HMD vs tablet robot programming workload"; "AR robot intent no significant difference workload"; "VR vs screen correcting robot perception errors"; "explanations robot failures fault recovery non-experts"; "visualization vs text plan explanation user study"; "LLM robot plan AR preview validate before execution"; "in-situ projection vs HMD vs paper assembly comparison"; "hologram in my hand AR vs desktop".
- Snowballing: backward from Rosen 2019 related work (Ruddle, Sousa Santos HMD-vs-desktop literature; Bach 2018) and from Sibirtseva 2018 (Rosen; Andersen); forward from Walker 2018 / Rosen 2019 (Gadre 2019, Diehl 2020, Newbury 2022, Wozniak 2023, Macciò 2022, MARCER 2025); from Andersen 2016 to Kalpagam Ganesan 2018; from Stadler 2016 to Frank 2017 and HMD-vs-tablet theses; from Tang 2003 to Blattgerste 2017, Büttner 2016, Funk 2017 (contrary assembly evidence).
- Concept expansion: "plan understanding" → collision prediction / intent clarity / verification of taught behaviour / reference disambiguation; "repair" → program adaptation / perception-error correction / plan correction after explanation / fault recovery.

---

## Papers

### Rosen2019 (IJRR) / Rosen2017 (arXiv/ISRR version)
- Title / Authors / Year / Venue / DOI: "Communicating and controlling robot arm motion intent through mixed-reality head-mounted displays" / E. Rosen, D. Whitney, E. Phillips, G. Chien, J. Tompkin, G. Konidaris, S. Tellex / 2019 / IJRR / https://doi.org/10.1177/0278364919842925. Earlier version: "Communicating Robot Arm Motion Intent Through Mixed Reality Head-mounted Displays", arXiv:1708.03655 (2017; ISRR 2017 per common citation — venue of arXiv version not stated on arXiv page).
- verified: true (IJRR abstract; full text of arXiv version read) ; peer_reviewed: true (IJRR)
- Class: Strongly Related (methodologically the closest "find the error in the plan" AR-vs-2D study)
- Concepts: Plan Feasibility (collision / no collision of planned motion)
- What they do (implemented): HoloLens visualization of MoveIt-planned Baxter arm trajectories (ghosted future arm poses, colour-coded over time) overlaid on the real robot; ROS Reality bridge; gesture adjustment of goal pose (IJRR version).
- What they evaluate: see Evidence Matrix.
- Overlap with CoGround: pre-execution inspection of a robot plan in situ; binary judgment "will this plan fail (collide)?" = discrepancy detection; measured speed, accuracy (incl. signal detection d'), NASA-TLX, SUS.
- Differences: motion-level (trajectory), not task-level outcome state; no After-state of objects; no explanation of causes; repair only as goal-pose adjustment (not evaluated as repair performance in the arXiv version).
- Scores: Purpose 2 | Timing 3 | Outcome 1 | Discrepancy 3 | Explanation 0 | Repair 1 | Evaluation 3
- Evidence Matrix:
  - N: 32 (15 m, 17 f; age 20–55, M=26)
  - Task: label each planned arm motion as colliding / non-colliding with block towers on a table, "as quickly and accurately as possible".
  - Conditions: (1) No visualization (watch real arm move, press e-stop if collision predicted); (2) Monitor: RViz-like 3D scene on desk monitor, robot model with future arm poses + Kinect point cloud of environment, mouse/keyboard camera control; (3) MR: HoloLens, "similar 3D visualization" overlaid on the real world (no point cloud needed).
  - IVs: interface (within-subjects). No-visualization always first; Monitor/MR order alternated.
  - DVs: true positive/negative rates, accuracy, d' (SDT), labeling time (Monitor vs MR only), NASA-TLX, SUS, custom collision-predictability Likert, preference.
  - Instruments: NASA-TLX, SUS, custom 7-pt items, forced-choice preference.
  - Key results (arXiv version): accuracy MR M=0.76 (SD 0.19) > Monitor 0.66 (0.14) > NoVis 0.60 (0.12); RM-ANOVA Wilks Λ=0.619, F(2,30)=9.244, p=.001, η²=.381; MR>Monitor p=.001; Monitor vs NoVis n.s. (p=.065). d': MR 1.79 (0.88) > Monitor 0.94 (0.58), NoVis 0.82 (0.66), F(2,30)=18.378, p<.001, η²=.551. Time: MR 11.95 s (SD 8.42) vs Monitor 19.39 s (SD 19.28), t(31)=3.415, p<.001. NASA-TLX: MR 35.39 < NoVis 37.11 < Monitor 42.32; F(2,30)=3.693, p=.037; only MR<Monitor significant (p=.040). SUS: NoVis 38.91 ≥ MR 37.88 > Monitor 28.31 (MR vs NoVis n.s.). Preference: 32/32 enjoyed MR most; 30/32 preferred MR. Headline: arXiv abstract states +16% accuracy and −62% time vs next best; IJRR abstract states +15% accuracy and −38% time (numbers differ between versions — cite the version you use).
  - Authors' limitations: overlay misalignment, long setup, physically moving around robot sometimes difficult; monitor's poor showing attributed to cumbersome mouse navigation.
  - Confounds (my assessment): NOT information-equivalent — the monitor showed a point cloud of the environment (degraded) whereas MR used the real scene; monitor required mouse camera navigation vs natural head motion; no-visualization condition fixed first (order confound); arm moved only in NoVis.
  - Applicability to CoGround: the strongest template for a "detect the problem in the plan before execution" task with SDT analysis; but advantage may partly stem from viewpoint control and environment fidelity, not "AR per se".
  - Evidence strength: Direct
- Notes: arXiv PDF Sec. 3.2–3.4 and Results ("Accuracy", "Task Time", "Subjective Workload").

### Gadre2019
- Title / Authors / Year / Venue / DOI: "End-User Robot Programming Using Mixed Reality" / S. Y. Gadre, E. Rosen, G. Chien, E. Phillips, S. Tellex, G. Konidaris / 2019 / ICRA / https://doi.org/10.1109/ICRA.2019.8793988
- verified: true (author PDF h2r.cs.brown.edu/wp-content/uploads/gadre19.pdf read) ; peer_reviewed: true
- Class: Methodologically Relevant
- Concepts: Plan Feasibility (program creation and adaptation)
- What they do: HoloLens waypoint programming of a Baxter arm with in-situ preview of the program vs a 2D monitor RViz-like waypoint interface.
- What they evaluate: see matrix.
- Overlap with CoGround: includes an "adapted task" where users modify an existing program to new conditions — the closest measured analogue to local plan repair in AR vs 2D.
- Differences: programming from scratch by users rather than checking an autonomous plan; no outcome/After-state visualization.
- Scores: Purpose 1 | Timing 2 | Outcome 1 | Discrepancy 0 | Explanation 0 | Repair 2 | Evaluation 3
- Evidence Matrix:
  - N: 20 (completion-time t-tests on 18 because 2 failed the 2D primitive task)
  - Task: (a) primitive pick-and-place program; (b) adapted task: modify one's own program to a changed task.
  - Conditions: 2D monitor + keyboard/mouse (RViz-like camera navigation) vs MR HoloLens.
  - IVs: interface (within-subjects, counterbalanced).
  - DVs: completion rate, completion time, NASA-TLX, SUS (7-pt variant), custom naturalness survey.
  - Key results: primitive time 2D M=189.44 s (SD 105.33) vs MR 132.50 s (SD 92.40), t(17)=2.77, p=.013, d=0.57; adapted time 2D 263.98 s (123.88) vs MR 145.28 s (108.43), t(17)=5.656, p<.001, d=1.02; completion 20/20 MR vs 18/20 2D; NASA-TLX MR 31.54 (15.69) vs 2D 46.13 (15.59), t(19)=4.07, p=.001, d=0.93; usability MR 5.8 vs 2D 3.82, t(19)=7.73, p<.001, d=1.83.
  - Authors' limitations: significant ORDER effects — 2D rated lower on usability and naturalness when used after MR (t(18)=3.17, p=.008, d=1.46; t(18)=4.29, p=.002).
  - Applicability: AR advantage was larger for the modification (repair-like) task (d=1.02) than for creation (d=0.57); supports measuring repair time separately. Again 2D used mouse navigation of 3D scene (interaction confound).
  - Evidence strength: Indirect
- Notes: Results section G.1–G.5.

### Sibirtseva2018
- Title / Authors / Year / Venue / DOI: "A Comparison of Visualisation Methods for Disambiguating Verbal Requests in Human-Robot Interaction" / E. Sibirtseva, D. Kontogiorgos, O. Nykvist, H. Karaoguz, I. Leite, J. Gustafson, et al. (full author list not verified beyond first six) / 2018 / IEEE RO-MAN / https://doi.org/10.1109/ROMAN.2018.8525554 (arXiv:1801.08760)
- verified: true (arXiv full text read) ; peer_reviewed: true
- Class: Strongly Related (display-modality comparison for showing the robot's *interpretation* of a request)
- Concepts: Task Interpretation
- What they do: YuMi robot picks Lego blocks from verbal requests; robot's candidate referents (its hypothesis of what the user meant) highlighted in real time.
- What they evaluate: see matrix.
- Overlap with CoGround: visualizing how the robot interpreted a request so the user can catch/correct misinterpretation; compares HMD vs projector vs monitor with matched content (highlights).
- Differences: single-object reference, not a multi-step plan or After state.
- Scores: Purpose 2 | Timing 2 | Outcome 0 | Discrepancy 2 | Explanation 0 | Repair 1 | Evaluation 3
- Evidence Matrix:
  - N: 29 (12 f, 17 m)
  - Task: collaborative Lego building; participant describes blocks verbally; robot highlights candidates until disambiguated.
  - Conditions: MO = monitor showing top-down webcam video with highlight overlay; "AR" = projector highlights on the table; "MR" = HoloLens 3D highlights. (Note authors' labels: their "AR" is projection, "MR" is HMD.)
  - IVs: modality (within-subjects, randomised order).
  - DVs: request time, error rate (wrong block described or picked), engagement, observability, display interference (Presence Inventory / Presence Questionnaire items), preference.
  - Key results: request time no condition effect F(2,14)=1.19, p=.33 (significant order/learning effect instead). Error rate effect F(2,56)=3.22, p<.05, η²=.10: projector M=.01 < monitor .02 < HMD .04; projector < HMD significant (post hoc; reported p value in text appears garbled "p = 1.0"); monitor vs others n.s. HMD rated most engaging; overall preference for projector.
  - Authors' limitations: HMD novelty/unfamiliarity (first requests excluded for warm-up), HMD tracking based on spatial mapping, non-native English speakers.
  - Applicability: CONTRARY evidence: the HMD produced the most errors and no speed gain; projection (in-situ but device-free) best. Information content roughly equal across conditions (same highlights) — a better parity design than Rosen.
  - Evidence strength: Direct (for interpretation display), Indirect for plan outcome
- Notes: arXiv Sec. 5–6.

### Diehl2020
- Title / Authors / Year / Venue / DOI: "Augmented Reality interface to verify Robot Learning" / M. Diehl, A. Plopski, H. Kato, K. Ramirez-Amaro / 2020 / IEEE RO-MAN / https://doi.org/10.1109/RO-MAN47096.2020.9223502
- verified: partial (abstract verified via OpenAlex/Chalmers; full results NOT seen) ; peer_reviewed: true
- Class: Strongly Related
- Concepts: Plan Feasibility, Goal Satisfaction (did the robot learn the task correctly before execution)
- What they do: AR verification interface: virtual simulation of the learned behaviour embedded in the real environment, time-coupled with a semantic description of the current action; three interface/visualization-technology designs vs traditional simulation (RViz).
- What they evaluate: user study, N=18, "effectiveness ... regarding error detection capabilities".
- Overlap with CoGround: pre-execution verification of learned task + error detection + semantic (language) annotation of steps — very close in purpose.
- Differences: learning-from-demonstration context; no explicit After-state/diminished reality; repair not reported in abstract.
- Scores: Purpose 3 | Timing 3 | Outcome 2 | Discrepancy 3 | Explanation 1 | Repair NR | Evaluation 2
- Evidence Matrix:
  - N: 18
  - Task: detect errors in a taught robot behaviour before execution (details not verified)
  - Conditions: three AR designs (device combinations not verified — likely HMD/tablet variants) vs RViz-like simulation
  - IVs / DVs / instruments: not verified
  - Key results: not verified (abstract only states AR gives "more realistic feedback than traditional simulations with a lower cost of not having to model the entire environment")
  - Authors' limitations: not verified
  - Applicability: highest-priority paper to obtain full text — it is the closest prior "AR vs simulation for error detection before execution" study.
  - Evidence strength: Direct (pending verification)

### Walker2018
- Title / Authors / Year / Venue / DOI: "Communicating Robot Motion Intent with Augmented Reality" / M. Walker, H. Hedayati, J. Lee, D. Szafir / 2018 / ACM/IEEE HRI / https://doi.org/10.1145/3171221.3171253
- verified: partial (abstract verified; N/design from a third-party seminar slide deck, Univ. Hamburg TAMS 2019) ; peer_reviewed: true
- Class: Partially Related
- Concepts: Plan Feasibility (motion intent), not Goal Satisfaction
- What they do: four HoloLens designs for drone flight intent: NavPoints (path + waypoints + timers), Arrows, Gaze (virtual eye), Utilities (implicit).
- What they evaluate: see matrix.
- Overlap: AR intent for future robot motion; measured clarity + efficiency.
- Differences: during-execution (concurrent) intent, not pre-execution outcome check; baseline is physical cues not a 2D display.
- Scores: Purpose 1 | Timing 1 | Outcome 1 | Discrepancy 0 | Explanation 0 | Repair 0 | Evaluation 3
- Evidence Matrix:
  - N: 60 (40 m, 20 f) — from slides, not verified in paper
  - Task: build beaded strings at workstations shared with a drone for 8 min; vacate station (≥2 m) when robot comes.
  - Conditions: 5 between-subjects: baseline (HoloLens worn, no AR cue; robot orientation only), NavPoints, Arrows, Gaze, Utilities.
  - DVs: task performance/efficiency, intent clarity, robot usability/teammate perception.
  - Key results: abstract: "several of our AR designs significantly improved objective task efficiency over a baseline"; slides: NavPoints, Arrows, Gaze significant vs baseline; NavPoints best for intent clarity. Exact statistics not verified.
  - Authors' limitations (slides): HoloLens uncomfortable; generalizability limited by design/task/measures; between-subjects with small cells.
  - Applicability: explicit path/waypoint (NavPoints) > implicit cues for clarity → favour explicit predicted-state rendering. Baseline wore the HMD (controls for device burden — good design element).
  - Evidence strength: Indirect

### Hedayati2018
- Title / Authors / Year / Venue / DOI: "Improving Collocated Robot Teleoperation with Augmented Reality" / H. Hedayati, M. Walker, D. Szafir / 2018 / ACM/IEEE HRI / https://doi.org/10.1145/3171221.3171251
- verified: partial (abstract only) ; peer_reviewed: true
- Class: Methodologically Relevant
- Concepts: none directly (teleoperation SA)
- What they do: AR teleoperation interfaces for an aerial robot that spatially integrate the robot's camera feed (designs reportedly named Frustum, Callout, Peripherals — names from the group's patent, not verified in paper).
- What they evaluate: 48 participants, environmental inspection task; "several objective and subjective performance benefits over existing systems" that split attention between robot and a separate camera feed.
- Overlap: evidence that spatially co-locating robot-centric information with the world reduces divided attention vs a separate 2D feed.
- Differences: teleoperation, no planning.
- Scores: Purpose 0 | Timing 0 | Outcome 0 | Discrepancy 0 | Explanation 0 | Repair 0 | Evaluation 2
- Evidence Matrix: N=48; task: aerial inspection; conditions: AR designs vs non-AR baseline (exact conditions not verified); DVs/results: not verified beyond abstract; limitations: not verified; applicability: supports the "split-attention cost of 2D displays" rationale; Evidence strength: Supporting

### Szafir2015
- Title / Authors / Year / Venue / DOI: "Communicating Directionality in Flying Robots" / D. Szafir, B. Mutlu, T. Fong / 2015 / ACM/IEEE HRI / https://doi.org/10.1145/2696454.2696475
- verified: partial (abstract) ; peer_reviewed: true
- Class: Background
- Concepts: motion intent
- What they do / evaluate: on-robot light signals for flight direction vs no-signal baseline; participants predicted robot intent. "Three of our designs significantly improved viewer response time and accuracy over the baseline"; signal form trades off precision, generalizability, usability.
- Overlap: response time + accuracy of intent prediction as DVs (template for "prediction task" measures).
- Differences: not AR, not plan outcome.
- Scores: Purpose 0 | Timing 1 | Outcome 0 | Discrepancy 0 | Explanation 0 | Repair 0 | Evaluation 2
- Evidence Matrix: N not verified; task: predict drone direction; conditions: several light designs vs baseline; DVs: response time, accuracy, perceptions; results: as abstract (stats not verified); Evidence strength: Supporting

### Andersen2016
- Title / Authors / Year / Venue / DOI: "Projecting robot intentions into human environments" / R. S. Andersen, O. Madsen, T. B. Moeslund, H. Ben Amor / 2016 / IEEE RO-MAN / https://doi.org/10.1109/ROMAN.2016.7745145
- verified: partial (abstract) ; peer_reviewed: true
- Class: Partially Related
- Concepts: Plan Feasibility (next manipulation site, workspace safety)
- What they do: object-aware projection of task info and robot intentions onto tracked physical objects.
- What they evaluate: "preliminary usability study" comparing projection vs monitor vs printed text; "on average, the user effectiveness and satisfaction is higher with the projection based approach". A 2021 secondary source (arXiv 2104.03547) reports projector produced fewer errors — not verified.
- Overlap: object-anchored display of robot's next actions vs 2D monitor / text, same task info.
- Differences: during collaboration; preliminary, likely small N.
- Scores: Purpose 1 | Timing 2 | Outcome 1 | Discrepancy 0 | Explanation 0 | Repair 0 | Evaluation 2
- Evidence Matrix: N not verified; task: collaborative car-door-like assembly (not verified); conditions: projection / monitor / printed text; DVs: effectiveness, satisfaction; stats: not reported/not verified; limitations: preliminary study; applicability: one of few three-way spatial vs 2D vs text comparisons; Evidence strength: Indirect

### KalpagamGanesan2018
- Title / Authors / Year / Venue / DOI: "Better Teaming Through Visual Cues: How Projecting Imagery in a Workspace Can Improve Human-Robot Collaboration" / R. Kalpagam Ganesan, Y. K. Rathore, H. M. Ross, H. Ben Amor / 2018 / IEEE Robotics & Automation Magazine / https://doi.org/10.1109/MRA.2018.2815655
- verified: partial (abstract via OpenAlex; numbers from search snippets of the magazine/ASU thesis) ; peer_reviewed: true (magazine)
- Class: Partially Related
- Concepts: task instructions + robot intention
- What they do: projection mapping of task instructions and robot intentions onto tracked objects.
- What they evaluate: within-subjects car-door assembly with robot; projected vs printed vs mobile-display instructions; snippet: total task time lowest for projection, one-way ANOVA F(2,42)=8.07, p<.01; translation/rotation alignment errors smaller with projection; lower variance in instruction-reading time. N not verified (df suggest ~22 if within-subjects; not verified).
- Overlap / Differences: as Andersen2016.
- Scores: Purpose 1 | Timing 1 | Outcome 1 | Discrepancy 0 | Explanation 0 | Repair 0 | Evaluation 2
- Evidence Matrix: N not verified; conditions: projection / printed / mobile display; DVs: time, alignment errors, subjective; key result F(2,42)=8.07 p<.01 (snippet, not verified); Evidence strength: Indirect

### Chadalavada2015
- Title / Authors / Year / Venue / DOI: "That's on my mind! Robot to human intention communication through on-board projection on shared floor space" / R. T. Chadalavada, H. Andreasson, R. Krug, A. J. Lilienthal / 2015 / ECMR / https://doi.org/10.1109/ECMR.2015.7403771
- verified: partial (abstract) ; peer_reviewed: true
- Class: Background
- Concepts: motion intent
- What they do/evaluate: forklift projects planned trajectory/occupied space on floor; "simple information, such as the trajectory and the space to be occupied ... is able to effectively improve human response". N/stats not verified.
- Scores: Purpose 0 | Timing 1 | Outcome 1 | Discrepancy 0 | Explanation 0 | Repair 0 | Evaluation 1
- Evidence Matrix: N not verified; conditions: projection vs no projection (not verified); Evidence strength: Supporting

### Stadler2016
- Title / Authors / Year / Venue / DOI: "Augmented reality for industrial robot programmers: Workload analysis for task-based, augmented reality-supported robot control" / S. Stadler, K. Kain, M. Giuliani, N. Mirnig, G. Stollnberger, M. Tscheligi / 2016 / IEEE RO-MAN / https://doi.org/10.1109/ROMAN.2016.7745108
- verified: partial (abstract) ; peer_reviewed: true
- Class: Methodologically Relevant
- Concepts: none (robot control)
- What they do: tablet-based AR showing task-based info while controlling a Sphero robot.
- What they evaluate: within-subjects, 19 professional industrial robot programmers; tasks: TCP teaching, trajectory teaching, overlap teaching; NASA-TLX dimensions + completion time. "Task-based information in the tablet-based AR interface decreases the mental demand ... At the same time, however, the programmers' task completion time increases."
- Overlap: AR adds info → lower mental demand but slower — a speed/load trade-off directly relevant to "at a glance".
- Scores: Purpose 0 | Timing 0 | Outcome 0 | Discrepancy 0 | Explanation 0 | Repair 0 | Evaluation 2
- Evidence Matrix: N=19; task: 3 programming tasks; conditions: tablet AR with task info vs without (not verified in detail); DVs: NASA-TLX subscales, time; stats: not verified; limitations: Sphero proxy for industrial robot; applicability: CONTRARY on speed; Evidence strength: Indirect

### Frank2017
- Title / Authors / Year / Venue / DOI: "Mobile Mixed-Reality Interfaces That Enhance Human–Robot Interaction in Shared Spaces" / J. A. Frank, M. Moorhead, V. Kapila / 2017 / Frontiers in Robotics and AI / https://doi.org/10.3389/frobt.2017.00020
- verified: partial (abstract) ; peer_reviewed: true
- Class: Methodologically Relevant
- Concepts: none (commanding manipulation)
- What they do/evaluate: tablet MR interface pointed at workspace vs conventional egocentric (robot-mounted camera) and exocentric (environment camera) views for object-manipulation commands. Result: "comparable task performance and user experiences" — i.e., no clear advantage — "at the expense of some physical workload".
- Scores: Purpose 0 | Timing 0 | Outcome 0 | Discrepancy 0 | Explanation 0 | Repair 0 | Evaluation 2
- Evidence Matrix: N not verified; conditions: MR tablet vs egocentric vs exocentric camera interfaces; DVs: task performance, UX, workload; result: comparable (NULL), added physical workload for handheld MR; Evidence strength: Indirect

### Chan2022
- Title / Authors / Year / Venue / DOI: "Design and Evaluation of an Augmented Reality Head-Mounted Display Interface for Human Robot Teams Collaborating in Physically Shared Manufacturing Tasks" / W. P. Chan, G. Hanks, M. Sakr, H. Zhang, T. Zuo, H. F. M. Van der Loos, E. Croft / 2022 / arXiv:2203.08343 (journal version: ACM THRI per later citations — not verified)
- verified: true (arXiv text read) ; peer_reviewed: false (as verified; preprint)
- Class: Methodologically Relevant
- Concepts: none (task allocation/programming)
- What they do/evaluate: HoloLens interface to program/command a robot assistant in simulated CFRP manufacturing vs a joystick (teach-pendant proxy); conditions H (human only), J1/AR1 (predefined task division), J2/AR2 (free division); J vs AR counterbalanced; N=26 (extending an earlier n=10 study). Abstract: AR "feels more novel" but joystick "feels more dependable"; AR reduced physical demand and completion time and increased robot utilization.
- Scores: Purpose 0 | Timing 1 | Outcome 0 | Discrepancy 0 | Explanation 0 | Repair 0 | Evaluation 2
- Evidence Matrix: N=26; DVs: completion time, robot utilization, NASA-TLX, SUS, UEQ-like UX; numeric stats not extracted (not verified); mixed result (dependability favours non-AR); Evidence strength: Supporting

### Newbury2022
- Title / Authors / Year / Venue / DOI: "Visualizing Robot Intent for Object Handovers with Augmented Reality" / R. Newbury, A. Cosgun, T. Crowley-Davis, W. P. Chan, T. Drummond, E. Croft / 2022 / IEEE RO-MAN / https://doi.org/10.1109/RO-MAN53752.2022.9900524 (arXiv:2103.04055)
- verified: true (arXiv full text read) ; peer_reviewed: true
- Class: Partially Related
- Concepts: Task Interpretation (robot's object pose estimate) / Feasibility (intended grasp)
- What they do: HoloLens shows virtual object at robot's estimated pose and the intended gripper grasp pose before the handover.
- What they evaluate: 2×2 within (AR vs No AR) × (with vs without simulated pose-estimation error); N=16; 12 handovers each; subjective fluency, trust, predictability, safety, mental load (Likert), ART ANOVA.
- Overlap: showing the robot's internal estimate lets users detect and compensate for robot errors — analogous to Discrepancy Detection.
- Differences: real-time handover, no plan/After state.
- Scores: Purpose 1 | Timing 2 | Outcome 1 | Discrepancy 2 | Explanation 0 | Repair 1 | Evaluation 2
- Evidence Matrix: N=16; key results: trust 3.06 → 3.94 with AR (significant); fluency 3.16 → 3.56 (n.s.); simulated error significantly reduced fluency and increased mental load; AR benefit larger under error for fluency (Kruskal-Wallis H(1)=6.960, p=.003) and safety (H=3.767, p=.037); predictability difference 0.91 (Likert) between AR and No AR. Limitations: error condition always second (fixed order), subjective-only DVs; Evidence strength: Indirect

### ArevaloArboleda2021
- Title / Authors / Year / Venue / DOI: "Assisting Manipulation and Grasping in Robot Teleoperation with Augmented Reality Visual Cues" / S. Arévalo Arboleda, F. Rücker, T. Dierks, J. Gerken / 2021 / CHI / https://doi.org/10.1145/3411764.3445398
- verified: partial (abstract) ; peer_reviewed: true
- Class: Background
- What they evaluate: two AR cue designs vs baseline for co-located teleoperated pick-and-place; "performance improvements in different levels ... with trade-offs in terms of time, accuracy". N/stats not verified.
- Scores: Purpose 0 | Timing 0 | Outcome 0 | Discrepancy 0 | Explanation 0 | Repair 0 | Evaluation 2
- Evidence Matrix: N not verified; DVs time/accuracy/subjective; result: trade-offs (not uniformly better); Evidence strength: Supporting

### Gruenefeld2020
- Title / Authors / Year / Venue / DOI: "Mind the ARm: Realtime Visualization of Robot Motion Intent in Head-Mounted Augmented Reality" / U. Gruenefeld, L. Prädel, J. Illing, T. Stratmann, S. Drolshagen, M. Pfingsthorn / 2020 / Mensch und Computer / https://doi.org/10.1145/3404983.3405509
- verified: partial (abstract) ; peer_reviewed: true
- Class: Methodologically Relevant
- What they evaluate: three AR visualizations (Path, Preview, Volume) compared while users do a cognitive side task in a shared workspace; Preview and Path required significantly longer head rotations; Volume shortest head rotation, perceived safest, allowed closer proximity without safety shutdowns. N/stats not verified. No non-AR baseline.
- Overlap: compares AR *encodings* of future robot state (ghost preview vs path vs swept volume) — relevant for choosing After-state encoding; head rotation as an attention-cost measure.
- Scores: Purpose 0 | Timing 1 | Outcome 1 | Discrepancy 0 | Explanation 0 | Repair 0 | Evaluation 2
- Evidence Matrix: N not verified; conditions: Path / Preview / Volume (within, not verified); DVs: head rotation, proximity, perceived safety; Evidence strength: Indirect

### Bolano2019
- Title / Authors / Year / Venue / DOI: "Transparent Robot Behavior Using Augmented Reality in Close Human-Robot Interaction" / G. Bolano, C. Juelg, A. Roennau, R. Dillmann / 2019 / IEEE RO-MAN / https://doi.org/10.1109/RO-MAN46459.2019.8956296
- verified: partial (abstract) ; peer_reviewed: true
- Class: Partially Related
- What they do: projection-based AR shows planned motion, task state, possible collisions and plan changes; "evaluated in different setups" — abstract does not describe a controlled comparative user study (not verified).
- Overlap: displays plan changes + predicted collisions (feasibility issues) in situ.
- Scores: Purpose 1 | Timing 2 | Outcome 1 | Discrepancy 1 | Explanation 1 | Repair 0 | Evaluation NR
- Evidence Matrix: N not reported in abstract; Evidence strength: Supporting (implementation, not empirical comparison)

### Chandan2021 (ARROCH)
- Title / Authors / Year / Venue / DOI: "ARROCH: Augmented Reality for Robots Collaborating with a Human" / K. Chandan, V. Kudalkar, X. Li, S. Zhang / 2021 / ICRA / https://doi.org/10.1109/ICRA48506.2021.9561144 (arXiv:2109.10400)
- verified: true (arXiv text read) ; peer_reviewed: true
- Class: Partially Related
- Concepts: Plan Feasibility (multi-robot plans/intentions), human feedback to replanning
- What they do: tablet AR showing multiple robots' current states and planned trajectories through walls; human feedback adjusts robot plans.
- What they evaluate: N=11 students, each did trials with RViz-based non-AR baseline and ARROCH (random order); collaborative delivery; individual and team completion time; questionnaire. ARROCH faster (reported 0.01<p<0.05) and better questionnaire scores; plus simulation comparison against AR baselines.
- Overlap: AR vs RViz for understanding robot plans, with bidirectional feedback.
- Differences: execution-time collaboration; tiny N; no training on either interface.
- Scores: Purpose 1 | Timing 1 | Outcome 1 | Discrepancy 0 | Explanation 0 | Repair 1 | Evaluation 2
- Evidence Matrix: N=11; conditions: RViz vs AR tablet (within); DVs: individual/team completion time, questionnaire; key result: AR faster, p between .01 and .05 (exact stats not reported); limitations: small N, students, no training; Evidence strength: Indirect

### Wozniak2023
- Title / Authors / Year / Venue / DOI: "Happily Error After: Framework Development and User Study for Correcting Robot Perception Errors in Virtual Reality" / M. K. Wozniak, R. Stower, P. Jensfelt, A. Pereira / 2023 / arXiv:2306.14589 (earlier: "What you see is (not) what you get: A VR Framework for Correcting Robot Errors", arXiv:2301.04919, HRI'23 companion?) — publication venue of the full study not verified (likely RO-MAN 2023)
- verified: true (arXiv text read) ; peer_reviewed: unknown (not verified)
- Class: Partially Related
- Concepts: Task Interpretation (perception error), repair
- What they do: VR digital twin of a Franka scene; users add/move missed objects to fix robot perception before robot acts; vs screen (keyboard/mouse) interface.
- What they evaluate: N=56, within-subjects (VR vs screen), 4 trials each (1 training); DVs: time to add object, time to place, final distance (placement accuracy), n-missing, enjoyment, preference.
- Overlap: measured *repair* of a robot's world model in an immersive 3D vs 2D screen — directly analogous to CoGround's local repair step.
- Differences: VR not AR; perception not plan errors.
- Scores: Purpose 1 | Timing 2 | Outcome 1 | Discrepancy 2 | Explanation 0 | Repair 3 | Evaluation 3
- Evidence Matrix: N=56; key results: training trial VR slower to add object (Wilcoxon V=223, p<.001); no difference in time to place (p=.065) or final distance (p=.608); in experimental phase NO difference in placement accuracy (H2a not supported); significant learning across trials in VR but not screen (interaction); VR more immersive/enjoyable and preferred. Limitations: distance metric imperfect (bounding-box), order effects (second interface always faster); Evidence strength: Indirect

### Das2021
- Title / Authors / Year / Venue / DOI: "Explainable AI for Robot Failures: Generating Explanations that Improve User Assistance in Fault Recovery" / D. Das, S. Banerjee, S. Chernova / 2021 / ACM/IEEE HRI / https://doi.org/10.1145/3434073.3444657 (arXiv:2101.01625)
- verified: true (arXiv text read) ; peer_reviewed: true
- Class: Methodologically Relevant
- Concepts: Plan Feasibility (failure cause), repair (solution identification)
- What they do: explanations of failure causes in a household pick-and-place plan (simulated home), varying content: action-based, context-based, ± history.
- What they evaluate: between-subjects, 5 conditions (None, AB, CB, AB-H, CB-H), AMT, 80 recruited / 70 analysed (13–15 per condition); visual stimuli: GIFs of actions + 3 views of final state; DVs: Failure Identification (FId) and Solution Identification (SId) F1.
- Overlap: measured users' ability to identify *cause* and *fix* of a plan failure from visual end-state + explanation — CoGround's explanation→repair loop, without AR.
- Differences: post-failure (not pre-execution prediction); 2D GIF stimuli; no AR comparison.
- Scores: Purpose 1 | Timing 0 | Outcome 2 | Discrepancy 1 | Explanation 3 | Repair 2 | Evaluation 3
- Evidence Matrix: N=70; key results: context presence → FId F(2,67)=6.95, p=.0018 (CB > None t=3.729 p=.0012; CB > AB t=2.923 p=.014); SId trend F(2,67)=2.92 p=.06 with CB > None t(67)=3.12 p=.007; history → FId effect (p=.04), History > None t(67)=3.447 p=.003; SId History > None t(67)=3.1857 p=.006. Limitations: online, simulated, non-expert filter excluded 10 who scored 100% at baseline; Evidence strength: Indirect (representation *content*, not spatial modality)

### Kumar2022 (VizXP)
- Title / Authors / Year / Venue / DOI: "VizXP: A Visualization Framework for Conveying Explanations to Users in Model Reconciliation Problems" / A. Kumar, S. L. Vasileiou, M. Bancilhon, A. Ottley, W. Yeoh / 2022 / ICAPS / https://doi.org/10.1609/icaps.v32i1.19860
- verified: true (author PDF read) ; peer_reviewed: true
- Class: Methodologically Relevant
- Concepts: Plan Feasibility (model differences), repair (plan correction)
- What they do: graphical visualization of model-reconciliation explanations (state evolution over plan) vs text.
- What they evaluate: between-subjects, 200 crowd participants (169 analysed; 4 scenarios × 50); Task 1 make a valid plan; Task 2 receive explanation of model errors, answer comprehension questions, then correct plan without the test function.
- Overlap: explanation → comprehension → plan correction pipeline with visual vs non-visual representation, correction ratio and correction time as DVs.
- Differences: abstract planning domain, no robot, no AR.
- Scores: Purpose 1 | Timing 2 | Outcome 1 | Discrepancy 1 | Explanation 3 | Repair 2 | Evaluation 3
- Evidence Matrix: key results: correction ratio 69.8% (viz) vs 62.7% (text), n.s. (p=.41); correction time 203.35 s vs 251.05 s, n.s. (p=.48); comprehension 5.40 vs 4.76 of 7, significant (Kruskal-Wallis, p=.022). → better understanding did NOT translate into significantly better repair. Evidence strength: Indirect

### Bambusek2019
- Title / Authors / Year / Venue / DOI: "Combining Interactive Spatial Augmented Reality with Head-Mounted Display for End-User Collaborative Robot Programming" / D. Bambušek, Z. Materna, M. Kapinus, V. Beran, P. Smrž / 2019 / IEEE RO-MAN / https://doi.org/10.1109/RO-MAN46459.2019.8956315
- verified: partial (abstract via search snippets) ; peer_reviewed: true
- Class: Methodologically Relevant
- What they evaluate: N=20 within-subjects; two pick-and-place tasks (create from scratch + update existing program); SAR touch table + HoloLens vs baseline (robot arms + touch table, no HMD); "better in qualitative measures by 33.84% and by 28.46% in quantitative measures". Stats not verified.
- Scores: Purpose 0 | Timing 1 | Outcome 1 | Discrepancy 0 | Explanation 0 | Repair 2 | Evaluation 2
- Evidence Matrix: N=20; includes program-update task (repair-like); details not verified; Evidence strength: Indirect

### Quintero2018
- Title / Authors / Year / Venue / DOI: "Robot Programming Through Augmented Trajectories in Augmented Reality" / C. P. Quintero, S. Li, M. K. X. J. Pan, W. P. Chan, H. F. M. Van der Loos, E. A. Croft / 2018 / IROS / https://doi.org/10.1109/IROS.2018.8593700
- verified: partial (abstract) ; peer_reviewed: true
- Class: Background
- What they do/evaluate: HoloLens trajectory specification, virtual previews of robot motion, online reprogramming; pilot study vs kinesthetic teaching (contact-surface and free-space paths). Results/N not verified.
- Scores: Purpose 0 | Timing 2 | Outcome 1 | Discrepancy 0 | Explanation 0 | Repair 1 | Evaluation 1
- Evidence Matrix: pilot, N not verified; Evidence strength: Supporting

### Tang2003
- Title / Authors / Year / Venue / DOI: "Comparative Effectiveness of Augmented Reality in Object Assembly" / A. Tang, C. Owen, F. Biocca, W. Mou / 2003 / CHI / https://doi.org/10.1145/642611.642626
- verified: partial (abstract via NJIT/dblp snippets) ; peer_reviewed: true
- Class: Background
- What they evaluate: in-situ 3D AR instructions vs conventional media (printed manual, screen instructions — conditions not verified in detail) for Duplo assembly; AR reduced error rate by 82%, especially cumulative errors; lower measured mental effort. N/stats not verified.
- Evidence Matrix: Supporting (human assembly, not robot-plan understanding — classic "AR offloads mental transformation" argument)
- Scores: Purpose 0 | Timing 0 | Outcome 0 | Discrepancy 0 | Explanation 0 | Repair 0 | Evaluation 2

### Blattgerste2017
- Title / Authors / Year / Venue / DOI: "Comparing Conventional and Augmented Reality Instructions for Manual Assembly Tasks" / J. Blattgerste, B. Strenge, P. Renner, T. Pfeiffer, K. Essig / 2017 / PETRA / https://doi.org/10.1145/3056540.3056547
- verified: partial (abstract via search snippets) ; peer_reviewed: true
- Class: Background
- What they evaluate: Lego Duplo benchmark; smartphone AR, HoloLens, Epson Moverio, paper. "Participants solved the task fastest using the paper instructions, but made less errors with AR assistance on the Microsoft HoloLens". Follow-up (PETRA'18, "In-situ instructions exceed side-by-side instructions...") found in-situ HMD instructions beat side-by-side on errors, time and task load.
- Evidence Matrix: N/stats not verified; CONTRARY on speed (paper fastest), pro-AR on errors; Evidence strength: Supporting
- Scores: all 0 except Evaluation 2

### Funk2017 / Buttner2016
- Funk2017: "Working with Augmented Reality? A Long-Term Analysis of In-Situ Instructions at the Assembly Workplace" / M. Funk, A. Bächler, L. Bächler, T. Kosch, T. Heidenreich, A. Schmidt / 2017 / PETRA / https://doi.org/10.1145/3056540.3056548 — verified: partial (abstract); 11 workdays in industry; in-situ projection DECREASED performance of expert workers, learning benefit for untrained workers.
- Buttner2016: "Using Head-Mounted Displays and In-Situ Projection for Assistive Systems: A Comparison" / S. Büttner, M. Funk, O. Sand, C. Röcker / 2016 / PETRA / https://doi.org/10.1145/2910674.2910679 — verified: partial (metadata); results only secondhand (citing papers: HMD slower than in-situ projection / paper) → treat as not verified.
- Class: Background ; Evidence strength: Supporting (contrary: expertise reversal and HMD cost)
- Scores: all 0 except Evaluation 2

### Bach2018
- Title / Authors / Year / Venue / DOI: "The Hologram in My Hand: How Effective is Interactive Exploration of 3D Visualizations in Immersive Tangible Augmented Reality?" / B. Bach, R. Sicat, J. Beyer, M. Cordeil, H. Pfister / 2018 / IEEE TVCG 24(1) / https://doi.org/10.1109/TVCG.2017.2745941
- verified: partial (abstract via snippets) ; peer_reviewed: true
- Class: Background
- What they evaluate: N=15; four 3D-visualization tasks of varying spatial-perception and interaction demands; HoloLens tangible AR vs tablet AR vs desktop. "Generally the desktop environment is still fastest and most precise in almost all cases"; each environment excelled at certain tasks.
- Evidence Matrix: CONTRARY (non-robot) — immersive AR not automatically better for reading 3D spatial data; Evidence strength: Supporting
- Scores: all 0 except Evaluation 2

### MARCER2025
- Title / Authors / Year / Venue / DOI: "MARCER: Multimodal Augmented Reality for Composing and Executing Robot Tasks" / B. Ikeda, M. Gramopadhye, L. Nekervis, D. J. Szafir / 2025 / ACM/IEEE HRI / https://doi.org/10.1109/HRI61500.2025.10974232
- verified: partial (abstract) ; peer_reviewed: true
- Class: Partially Related
- Concepts: Task Interpretation (LLM → action plan), Feasibility (validate program)
- What they do: LLM translates NL task descriptions into trigger-action plans; AR used to parameterize/validate programs with in-context visual previews.
- What they evaluate: usability exploration (design/implementation/evaluation); no AR-vs-2D comparison stated in abstract; N/metrics not verified.
- Scores: Purpose 2 | Timing 3 | Outcome 1 | Discrepancy 1 | Explanation 1 | Repair 2 | Evaluation 1
- Evidence Matrix: N not verified; Evidence strength: Supporting (LLM+AR preview exists, but no comparative evidence)

### Maccio2022
- Title / Authors / Year / Venue / DOI: "Mixed Reality as Communication Medium for Human-Robot Collaboration" / S. Macciò, A. Carfì, F. Mastrogiovanni / 2022 / arXiv:2206.15380 (venue not verified)
- verified: partial (arXiv abstract) ; peer_reviewed: false (as verified)
- Class: Background
- What: HMD hologram superimposed on robot previews future movements; preliminary user study suggests "improved and more natural collaboration". N/stats not verified.
- Evidence strength: Supporting

### Suzuki2022 (survey)
- "Augmented Reality and Robotics: A Survey and Taxonomy for AR-enhanced Human-Robot Interaction and Robotic Interfaces" / R. Suzuki, A. Karim, T. Xia, H. Hedayati, N. Marquardt / 2022 / CHI / https://doi.org/10.1145/3491102.3517719 — verified: true (abstract); 460 papers incl. an "evaluation strategies" dimension. Class: Background. Use to cross-check the share of AR-HRI papers with comparative baselines (not extracted here).

---

## Contrary / null results

Studies where AR/spatial was NOT better on some measure, or where the advantage is confounded:

1. **Sibirtseva2018** — HoloLens condition had the HIGHEST error rate (.04 vs projector .01, monitor .02) and no speed advantage (request time n.s.); users preferred projector. Same information content across conditions (one of the better parity designs) → the HMD *device* cost (registration, FOV, novelty) can outweigh spatial benefits.
2. **Stadler2016** — tablet AR reduced mental demand but INCREASED task completion time for professional programmers.
3. **Frank2017** — handheld MR interface gave only *comparable* performance/UX to egocentric/exocentric camera views, with extra physical workload.
4. **Rosen2017/2019** — despite large accuracy gains, SUS was highest for *no visualization*; MR workload not significantly lower than no visualization; the 2D monitor was not better than no visualization at all. And the 2D baseline was handicapped (point cloud + mouse navigation), so the AR effect is an upper bound.
5. **Gadre2019** — strong order effects (2D penalized after MR) inflate subjective differences.
6. **Wozniak2023** (VR vs screen repair) — no difference in placement accuracy; VR initially slower (training trial); only learning-rate advantage.
7. **Kumar2022 (VizXP)** — visual explanation improved comprehension, but plan-correction success and correction time differences were NOT significant → understanding ≠ repair performance.
8. **Newbury2022** — AR did not significantly improve perceived fluency (only trust); benefits concentrated in error conditions.
9. **Chan2022** — users perceived joystick as more dependable than AR HMD despite AR being faster.
10. **Walker2018** — not all AR designs helped (Utilities apparently not significant per secondary slides); HMD reported uncomfortable.
11. **Arevalo Arboleda2021** — AR cues produced trade-offs between time and accuracy rather than uniform gains.
12. **Blattgerste2017** — paper instructions fastest (AR fewer errors). **Funk2017** — in-situ projection decreased expert performance over long-term use. **Büttner2016** (secondhand) — HMD slower than projection.
13. **Bach2018** — desktop fastest and most precise in almost all 3D-visualization tasks vs HoloLens and tablet AR.

Synthesis: AR/spatial advantages are most consistent for (a) **spatial-relation judgments between robot plan and the physical world** (collision, reach, location) and (b) **reducing attention switching**. They are weaker or reversed for **speed in simple tasks**, **experts**, **HMD comfort/registration**, and when the 2D baseline is not handicapped. No study I found compares AR vs a 2D display *with information parity* on a **task-level predicted-outcome (After-state) judgment** — this is a real evidence gap for CoGround.

---

## Reusable study designs for CoGround

### Candidate conditions (within-subjects, counterbalanced with Latin square; avoid Rosen's fixed-first baseline)
- C1 **AR in-situ Before/After** (CoGround; HMD), with on-demand intermediate states.
- C2 **2D screen Before/After** with *identical content*: same rendered After-state of the same scene (e.g., rendered from the user's viewpoint or fixed overview + free camera), same icons/labels, same on-demand step list. Ideally a screen view generated from the same 3D scene graph to guarantee parity (render-from-AR-pipeline).
- C3 **Text/list plan** (LLM-style step list + predicted final state description) — the realistic non-spatial baseline for LLM-planning systems.
- Optional C4 **Projection** (Sibirtseva/Andersen show projection can beat HMD), or **AR without After-state (path/step overlay only)** to isolate the value of outcome representation vs plan representation.
- Device-burden control: have participants wear the HMD in all conditions (Walker2018 baseline wore HoloLens) or use video-see-through tablet for both.

### Tasks
- **"Find the problem in the plan" (signal detection)**: present N plans per condition, of which ~50% contain a seeded defect; types aligned to the three concepts: (i) Task Interpretation error (wrong object/target location), (ii) Plan Feasibility error (unreachable/blocked/collision), (iii) Goal Satisfaction shortfall (task only partially fulfilled, household rule violated). Response: "OK / Not OK" + localize the problem (object/action/constraint). Follows Rosen2019 (collision labeling) and Das2021 (failure identification).
- **Fulfilment-degree judgment**: "How much of the request will be fulfilled?" (e.g., % or which items) — measures "at a glance" understanding.
- **Cause identification**: choose cause category + object (Das2021 FId).
- **Local repair**: modify target/action/constraint, trigger replan; success if replanned plan is valid & satisfies goal (VizXP correction ratio; Gadre adapted-task; Wozniak correction).
- Glance condition: limited exposure time (e.g., 3–5 s) before answering, to test "at a glance"; then unlimited exploration condition.

### Metrics
- Detection: hit rate, false alarm rate, accuracy, **d′ and criterion c** (Rosen2019 SDT approach — handles response bias).
- Localization accuracy (correct object/action/constraint), cause-identification F1 (Das2021).
- Time: time-to-first-decision, total inspection time, number/duration of on-demand drill-downs (interaction logs), head rotation/gaze dispersion (Gruenefeld2020).
- Repair: success ratio, time to valid repair, number of replan iterations, unnecessary edits (Wozniak observed over-correction).
- Subjective: NASA-TLX (raw), SUS, SART or SAGAT-style probes for situation awareness of plan state, confidence per decision (calibration: confidence vs correctness), trust (e.g., Newbury trust item), preference.
- Comprehension questions (VizXP) separately from repair performance (they can dissociate).

### Confounds to control
- **Information parity** between AR and 2D (same objects, same predicted states, same labels, same drill-down) — Rosen's monitor had degraded environment (point cloud); Sibirtseva kept highlights equal.
- **Viewpoint/navigation cost**: 2D with mouse-based 3D navigation penalizes 2D (Rosen, Gadre). Offer fixed good viewpoints or same free-view control, or report it as part of the treatment explicitly.
- **Order and novelty effects**: counterbalance; include training/warm-up trials and exclude them (Sibirtseva excluded first requests; Wozniak training trial); test for order × condition interaction (Gadre found strong order effects).
- **HMD comfort, FOV, registration error** (Walker, Rosen, Sibirtseva) — report registration accuracy; consider wearing HMD in all conditions.
- **Defect salience** must be matched across conditions and types (balanced defect set, pre-piloted difficulty).
- **Expertise** (Funk2017 expertise reversal; Stadler professionals) — stratify or measure robotics/AR experience.
- **Speed–accuracy trade-off**: instruct "as quickly and accurately as possible" and analyse jointly (inverse efficiency or SDT + RT).
- **Execution-time vs pre-execution**: keep the robot static during inspection (Rosen MR/monitor conditions) so the plan, not motion, is judged.

### Recommended minimum design (derived)
2 (Representation: AR vs 2D, parity-matched) × 2 (Plan correctness: defect vs no defect) within-subjects, plus defect-type factor (Interpretation / Feasibility / GoalSatisfaction); N ≈ 24–32 (Rosen N=32, Gadre N=20 gave medium–large effects d≈0.6–1.0 on time); primary DVs d′ and decision time; secondary repair success/time, NASA-TLX, SUS, SART.

---

## Agent summary

**Top 5 closest empirical works (for evaluation evidence):**
1. **Rosen2019/2017** — AR vs monitor vs none for judging whether a planned arm motion collides (pre-execution, SDT analysis): MR +accuracy (0.76 vs 0.66), d′ 1.79 vs 0.94, faster (11.95 vs 19.39 s), lower TLX vs monitor. Direct, but the 2D baseline is handicapped.
2. **Diehl2020** — AR vs RViz simulation to verify a learned robot behaviour before execution, error detection, N=18. Closest purpose; RESULTS NOT VERIFIED (full text needed).
3. **Sibirtseva2018** — HMD vs projector vs monitor for showing the robot's interpretation; HMD had most errors, projector preferred, no time difference. Direct contrary evidence with good information parity.
4. **Gadre2019** — MR vs 2D programming incl. program adaptation (repair-like): MR faster (d=0.57 creation, d=1.02 adaptation), lower TLX; order effects.
5. **Das2021 + Kumar2022 (VizXP)** — non-AR evidence that *content* (context + history) improves failure/solution identification, and that better comprehension does not necessarily yield significantly better plan correction.
(Also notable for repair: **Wozniak2023** VR vs screen correction of robot perception errors — no accuracy difference.)

**Key gaps:**
- No study found that compares AR vs 2D (with information parity) for judging a **task-level predicted After-state / goal satisfaction** of a household robot plan.
- Almost no studies measure **repair performance** after detecting a plan problem in AR (Gadre's adapted task and Wozniak's VR correction are the nearest).
- Most AR-vs-2D robot studies confound representation with navigation/interaction method and environment fidelity; few use SDT; small N and novelty effects common.
- Execution-time intent studies (Walker, Gruenefeld, Chadalavada, Newbury) dominate; pre-execution outcome-preview evaluations are rare.

**Open doubts:**
- Diehl2020 results; Walker2018 N/design (from third-party slides); Andersen2016 and Kalpagam Ganesan 2018 numbers (snippets only); Büttner2016 results (secondhand); Rosen headline percentages differ between arXiv (16%/62%) and IJRR (15%/38%) versions.
- Wozniak2023 and Chan2022 peer-review venues not verified.

**Suggested cross-checks for other agents:**
- Obtain full text of **Diehl2020** (RO-MAN) and any follow-up by Diehl/Ramirez-Amaro on AR verification and explanation of robot failures.
- A-stream agents: check **MARCER2025** and LLM-plan preview systems for any comparative evaluations; check SHRIMP (simulation plan validation, reportedly 2026, N=35 — not verified by me).
- Check Suzuki2022 survey's evaluation-strategy section and Walker et al. VAM-HRI survey for additional AR-vs-baseline comparisons, especially any with null results.
- Check Kapinus/Materna (ARCOR/ARTable) follow-ups and Ikeda & Szafir AR debugging work for "find the bug" tasks.
