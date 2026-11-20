# B1 — Comprehension Researcher (Stream B)

**Question:** How have HRI, HCI, and AR studies conceptualized and measured users' speed, accuracy, clarity, and cognitive effort when understanding robot plans, capabilities, intentions, and predicted task outcomes?

**What "verified" means here:** `verified: true (full text)` means I read the PDF text (arXiv or author copy). `verified: true (abstract)` means I saw the abstract or publisher/repository record but not the methods section. `verified: false` means I relied on secondary sources only. All numbers below come from text I read; where I only saw an abstract, I give no numbers beyond the abstract's own.

Similarity scores (7 axes) are mostly `NR` for this stream. They are given only for papers that study plan or outcome understanding directly.

---

## Search log

**Sources:** WebSearch (Google-like), arXiv full-text PDFs (downloaded and converted with pdftotext, then grepped for methods and results), author PDFs (CMU RI, USC ICT), UCF STARS repository abstracts, DTIC, PubMed, Frontiers, DBLP and IEEE/ACM listings in search snippets.

**Queries (abridged):**
- Situation awareness: SAT model, Chen et al. 2014 ARL-TR-6905, Chen et al. 2018 TIES, Mercado 2016 Human Factors, Selkowitz 2017 Cognitive Systems Research, Stowers 2020 THMS, Endsley SAGAT 1988/1995.
- Glanceability: Matthews glanceable peripheral displays, Blascheck glanceable visualization smartwatch, Gouveia glanceable feedback, Lu & Bowman Glanceable AR.
- Legibility and prediction: Dragan legibility/predictability 2013, Kwon "expressing robot incapability", Huang "enabling robots to communicate their objectives", Huang "critical states".
- AR intent: Rosen MR-HMD motion intent (IJRR), Walker AR drone intent.
- XAI metrics: Hoffman "Metrics for XAI" (arXiv 2018 and Frontiers 2023), Sanneman & Shah SAFE-AI, Anderson "mental models of mere mortals", Kulesza "too much too little", Lage HCOMP 2019, Amir HIGHLIGHTS.
- Explainable planning with comprehension tests: Sukkerd contrastive MDP explanation, Chakraborti model reconciliation empirical study, Das "XAI for robot failures".
- Trust calibration: Wang/Pynadath/Hill HRI 2016, Okamura & Yamada PLOS ONE 2020, Lee & See 2004, Schaefer TPS-HRI.
- Cognitive offloading: Risko & Gilbert 2016.
- Concept expansion: "predict robot task outcome before execution user study accuracy response time household". This surfaced Porfirio et al. HRI 2024 (Polaris Plan Visualizer, a tidying scenario).

**Snowballing:**
- Backward from Chen 2018 to Chen 2014, Mercado 2016, Selkowitz 2017, and Stowers 2020.
- Backward from Hoffman 2018 to its mental-model elicitation task table (prediction, glitch detector, self-explanation, diagramming, retrospection).
- Forward from Dragan 2013 to Kwon 2018, Huang 2019, and Huang 2018.
- Forward from Amir 2018 to Huber 2021 and Septon (noted only).
- From the Rosen preprint's related work: there is a note that a prior AR-intent study found "no accuracy increase" (ref [25] in Rosen). I did not identify that reference; it should be cross-checked.

---

## Papers

### Endsley1995
- Title / Authors / Year / Venue / DOI: "Measurement of Situation Awareness in Dynamic Systems" / M. R. Endsley / 1995 / Human Factors 37(1):65–84 / 10.1518/001872095779049499. SAGAT itself originates in Endsley 1988 (Proc. HFS / NAECON). I did not see the 1988 paper itself.
- verified: true (abstract, via scilit/citedrive records); peer_reviewed: true
- Class: Methodologically Relevant
- Concepts: none directly. SA Level 3 ("projection of future status") maps onto Goal Satisfaction prediction.
- Construct defined: SA = perception of elements (L1), comprehension of their meaning (L2), and projection of their near-future status (L3).
- Measures/instruments: The paper reviews performance, subjective, questionnaire, and freeze-probe measures. SAGAT is the freeze-probe method: the simulation is halted, displays are blanked, and the operator answers queries that are scored against ground truth (objective accuracy per SA level).
- What they do: methodological review.
- What they evaluate: comparison of the advantages and limitations of SA measures; no single experiment.
- Overlap with CoGround: SAGAT-style queries ("Will the mug be on the shelf after execution?") give an objective, per-level accuracy test of outcome comprehension. L3 corresponds to the predicted After state.
- Differences: built for dynamic, continuous monitoring (cockpit), whereas CoGround is a static pre-execution review. Freeze-probe interruption is less natural when the display is already static, so query-after-display is the analogue.
- Scores: all NR
- Evidence strength: Supporting (methodological)
- Notes: Critiques (e.g., de Winter et al. 2018/2019) argue that SAGAT depends on memory recall. For CoGround, consider "display-present" queries such as SPAM (Situation Present Assessment Method, Durso et al.) to measure response time as well as accuracy. I did not verify SPAM here.

### Chen2014_SAT
- Title / Authors / Year / Venue / URL: "Situation Awareness-Based Agent Transparency" / J. Y. C. Chen, K. Procci, M. Boyce, J. Wright, A. Garcia, M. Barnes / 2014 / ARL-TR-6905 (Army Research Laboratory tech report) / https://apps.dtic.mil/sti/pdfs/ADA600351.pdf
- verified: true (DTIC record and abstract); peer_reviewed: false (technical report)
- Class: Background (core framework)
- Concepts: Interpretation (L1: current plan/goal), Feasibility (L2: reasoning/constraints), GoalSatisfaction (L3: projected outcome and uncertainty)
- Construct defined: agent transparency. SAT L1 = the agent's current actions and plans; L2 = its reasoning process; L3 = its projection of future outcomes, including uncertainty.
- Measures/instruments: framework only. Downstream studies use operator performance (correct decisions), response time, SA queries, trust scales, and NASA-TLX.
- What they do: propose the SAT model and review interface designs for showing agent information and uncertainty.
- What they evaluate: no new experiment.
- Overlap with CoGround: CoGround's "outcome at a glance" is essentially SAT L3 surfaced first. "Explore plan on demand" exposes L1 and L2. This gives a principled way to label CoGround's display layers.
- Differences: military multi-UxV supervision; no spatial After-state rendering.
- Scores: Purpose 2 | Timing 1 | Outcome 1 | Discrepancy NR | Explanation 1 | Repair NR | Evaluation NR
- Evidence strength: Supporting (conceptual)

### Chen2018_SAT_TIES
- Title / Authors / Year / Venue / DOI: "Situation awareness-based agent transparency and human-autonomy teaming effectiveness" / Chen, Lakhmani, Stowers, Selkowitz, Wright, Barnes / 2018 / Theoretical Issues in Ergonomics Science 19(3):259–282 / 10.1080/1463922X.2017.1315750
- verified: true (abstract); peer_reviewed: true
- Class: Background
- Concepts: Interpretation, Feasibility, GoalSatisfaction (as SAT L1–L3)
- Construct defined: SAT, extended to bidirectional transparency (the agent also models the human).
- Measures/instruments: review of three programs: Autonomous Squad Member, IMPACT multi-UxV planning, and a plan recommendation agent. The underlying studies used decision accuracy, response time, trust, workload, and SA.
- What they evaluate: review. Reported trend: transparency improves performance and trust calibration. Higher transparency increased trust only up to a point, and adding uncertainty information did not further raise trust (from abstract-level summaries).
- Overlap with CoGround: theoretical justification that showing projected outcomes (L3) supports correct accept/reject decisions about agent plans.
- Differences: not spatial or in situ; plan recommendation rather than delegated manipulation.
- Scores: Purpose 2 | Timing 2 | Outcome 1 | Discrepancy 1 | Explanation 1 | Repair NR | Evaluation 1
- Evidence strength: Indirect (review of studies measuring plan-acceptance correctness)

### Mercado2016
- Title / Authors / Year / Venue / DOI: "Intelligent Agent Transparency in Human–Agent Teaming for Multi-UxV Management" / Mercado, Rupp, Chen, Barnes, Barber, Procci / 2016 / Human Factors 58(3):401–415 / 10.1177/0018720815621206
- verified: true (abstract); peer_reviewed: true
- Class: Methodologically Relevant
- Concepts: Feasibility, GoalSatisfaction (judging whether the agent's recommended plan is correct)
- Construct defined: agent transparency (SAT levels, manipulated as 3 levels).
- Measures/instruments: operator performance (correctness of plan choice, given that the agent was wrong 3 of 8 times per block), response time, trust, subjective and objective workload, perceived usability.
- What they do: an intelligent agent recommends a primary and a secondary plan for each mission. The operator accepts the recommended plan or chooses the alternative.
- What they evaluate: within-subjects design, 3 transparency levels × 8 missions each; the agent's recommendation was incorrect 3/8 times in each block. Performance, trust, and usability increased with transparency. Workload and response time did not increase. N is not seen in the abstract.
- Overlap with CoGround: very close as a paradigm. The user must judge whether an autonomous plan is acceptable, with ground-truth wrong plans seeded. This gives objective decision accuracy plus RT, which is a template for CoGround's "detect unfulfilled sub-goals" task.
- Differences: 2D map GUI; military; no physical After state; no repair beyond choosing the alternative plan.
- Scores: Purpose 2 | Timing 3 | Outcome 1 | Discrepancy 2 | Explanation 1 | Repair 1 | Evaluation 3
- Evidence strength: Direct (judgment of plan correctness, measured objectively)
- Notes: Seeding a known fraction of incorrect plans is an important design pattern for measuring calibration (hits vs. false alarms).

### Selkowitz2017
- Title / Authors / Year / Venue / DOI: "Using agent transparency to support situation awareness of the Autonomous Squad Member" / Selkowitz, Lakhmani, Chen / 2017 / Cognitive Systems Research 46:13–25 / 10.1016/j.cogsys.2017.02.003
- verified: true (abstract); peer_reviewed: true
- Class: Methodologically Relevant
- Concepts: GoalSatisfaction (L3 projection)
- Construct defined: SA of the robot teammate (SAT levels 1, 1+2, 1+2+3, plus a variant).
- Measures/instruments: SA (with confidence in SA), trust, workload, cognitive processing, perceived usability. The exact SA instrument (likely SAGAT-style queries) is not confirmed from the abstract.
- What they evaluate: N = 60, dual task (monitoring the robot plus threat detection), 4 interfaces. Higher SAT levels gave greater SA, cognitive processing, and trust. There was no difference in workload or usability. A related HFES 2016 paper reported the best SA and trust when outcome predictions (L3) were shown.
- Overlap with CoGround: evidence that adding projected outcomes improves SA without a workload cost. The SA-with-confidence measure supports calibration analysis.
- Differences: monitoring during execution (adjacent to CoGround's scope); military.
- Scores: Purpose 2 | Timing 1 | Outcome 1 | Discrepancy NR | Explanation 1 | Repair NR | Evaluation 2
- Evidence strength: Indirect

### Stowers2020_IMPACT
- Title / Authors / Year / Venue / DOI: "The IMPACT of Agent Transparency on Human Performance" / Stowers, Kasdaglis, Rupp, Newton, Chen, Barnes / 2020 / IEEE Trans. Human-Machine Systems 50(3):245–253 / 10.1109/THMS.2020.2978041
- verified: true (abstract); peer_reviewed: true
- Class: Methodologically Relevant
- Concepts: Feasibility, GoalSatisfaction
- Construct defined: agent transparency (3 levels) as a decision aid for base defense with heterogeneous UxVs.
- Measures/instruments: decision performance, trust calibration, perceived workload, task completion time.
- What they evaluate: high transparency gave better performance and trust calibration, with no significant increase in perceived workload, but at a small cost in timeliness (slower completion).
- Overlap with CoGround: an explicit **speed–accuracy trade-off of richer plan information**, contrary to Mercado 2016's "no RT cost". CoGround should expect and report a possible speed cost of plan detail, which is consistent with its "detail on demand" motto.
- Differences: same as Mercado.
- Scores: Purpose 2 | Timing 3 | Outcome 1 | Discrepancy 1 | Explanation 1 | Repair NR | Evaluation 3
- Evidence strength: Direct (decision accuracy on agent plans plus timing)
- Notes: Record as mixed or contrary evidence: transparency is not free in time.

### Matthews2006_2007_Glanceability
- Title / Authors / Year / Venue / URL: "Designing Glanceable Peripheral Displays" (Matthews, Forlizzi, Rohrbach), UC Berkeley EECS-2006-113; and "Designing and Evaluating Glanceable Peripheral Displays" (T. Matthews, PhD dissertation, EECS-2007-56) / https://www2.eecs.berkeley.edu/Pubs/TechRpts/2007/EECS-2007-56.html
- verified: true (abstract and tech report pages); peer_reviewed: false (tech report / dissertation; a related DIS 2006 paper exists, not verified)
- Class: Background (definition)
- Concepts: none
- Construct defined: **glanceability** = "enabling users to understand information quickly and easily" (2006 report), framed as "quick intake of visual information with low cognitive effort" (2007 dissertation abstract). Peripheral-display evaluation criteria (Matthews et al., Activity Theory paper, abstract-level only): appeal, learnability, awareness, effects of breakdowns, distraction.
- Measures/instruments: The 2006 report studied abstraction and design variables (e.g., icons vs. text) for glanceable reading. I did not verify the exact lab metrics; they are reportedly time-limited exposure and recognition accuracy.
- Overlap with CoGround: provides the canonical definition behind the "understand the outcome at a glance" motto. Glanceability implies both speed (short exposure) and low effort.
- Differences: secondary-task peripheral displays, not plan review.
- Scores: all NR
- Evidence strength: Supporting (definition)

### Blascheck2019_GlanceableVis
- Title / Authors / Year / Venue / DOI: "Glanceable Visualization: Studies of Data Comparison Performance on Smartwatches" / Blascheck, Besançon, Bezerianos, Lee, Isenberg / 2019 (InfoVis 2018) / IEEE TVCG 25(1) / https://hal.archives-ouvertes.fr/hal-01851306
- verified: true (abstract); peer_reviewed: true
- Class: Methodologically Relevant
- Concepts: none
- Construct defined: glanceability operationalized as the **minimum exposure time** at which a simple comparison task can be performed accurately.
- Measures/instruments: a staircase procedure varying stimulus display time to find the threshold exposure duration for a data comparison task; chart type (bar, donut, radial bar) × data size (7, 12, 24).
- What they evaluate: 2 perception studies. Threshold times were <300 ms for bar, <220 ms for donut, and <1780 ms for radial bar charts (abstract). An IVAPP 2021 replication was done on a laptop.
- Overlap with CoGround: **the most rigorous objective glanceability protocol found.** CoGround could adapt a staircase on Before/After exposure time for the question "Is the task fully fulfilled? Y/N", or "Which object is not in its goal place?".
- Differences: abstract charts, not spatial 3D scenes or AR.
- Scores: all NR
- Evidence strength: Supporting (method transfer)

### Gouveia2016_GlanceableFeedback
- Title / Authors / Year / Venue / DOI: "Exploring the design space of glanceable feedback for physical activity trackers" / Gouveia, Pereira, Karapanos, Munson, Hassenzahl / 2016 / UbiComp '16 / 10.1145/2971648.2971754. Also "You have 5 seconds: designing glanceable feedback for physical activity trackers" (2015, UbiComp adjunct).
- verified: true (abstract-level from repository records); peer_reviewed: true
- Class: Background
- Construct defined: glances as brief (about 5 s) sessions of checking status with no further interaction. The 2015 paper reports that >70% of tracker use is of this kind.
- Measures/instruments: field deployment of 4 concepts, measuring usage logs and behavior change. Not a comprehension test.
- Overlap with CoGround: an operational time budget (about 5 s) for a "glance".
- Differences: no plan or robot content; behavioral rather than comprehension outcomes.
- Scores: all NR
- Evidence strength: Supporting

### LuBowman2021_GlanceableAR
- Title / Authors / Year / Venue / DOI: "Evaluating the Potential of Glanceable AR Interfaces for Authentic Everyday Uses" / Feiyu Lu, Doug A. Bowman / 2021 / IEEE VR 2021, pp. 768–777 / 10.1109/VR50410.2021.00104
- verified: false (only project pages and a bibliographic record seen); peer_reviewed: true
- Class: Background
- Construct defined: Glanceable AR, meaning always-on peripheral AR information that is accessed with a glance.
- Measures/instruments: an in-the-wild deployment (Magic Leap One, N = 6 per project page) with subjective usefulness and distraction ratings; a prior video-prototype survey.
- Overlap with CoGround: AR-specific glanceability framing; reports that participants found the AR interface less distracting than existing devices.
- Differences: personal information (calendar, etc.), not robot plans; subjective only.
- Scores: all NR
- Evidence strength: Supporting

### Dragan2013_Legibility
- Title / Authors / Year / Venue / DOI: "Legibility and Predictability of Robot Motion" / A. D. Dragan, K. C. T. Lee, S. S. Srinivasa / 2013 / HRI '13, pp. 301–308 / 10.1109/HRI.2013.6483603
- verified: true (full text, CMU RI PDF); peer_reviewed: true
- Class: Methodologically Relevant
- Concepts: Interpretation (goal inference from motion)
- Construct defined: **Predictability** = motion matches what an observer expects given a known goal (goal → action inference). **Legibility** = motion lets an observer quickly and confidently infer the correct goal (action → goal inference).
- Measures/instruments:
  - Predictability: the participant imagines and **draws** the expected trajectory, then watches the video and rates "how much it matched what you expected" on a 1–7 Likert scale.
  - Legibility: the participant watches the video and **stops it as soon as they know the goal**. Time and prediction correctness are recorded and combined into a Guttman-style score and a probability-correct-over-time curve (chance = 0.5 at t = 0).
- What they evaluate: N = 432 on MTurk (split across the predictability and legibility sub-experiments), with attention-check exclusions. Three characters (point robot, HERB, human) × 2 trajectories. Predictability main effect for trajectory: F(1,310) = 21.88, p < .001. The hypothesis held for the point robot and the human but not HERB, where expectations varied (a follow-up with 5 novices gave 5 different expected trajectories). Legible trajectories gave a higher probability of correct inference at all times.
- Overlap with CoGround: the canonical **"stop when you know" time-to-correct-inference** paradigm, which combines speed and accuracy. Directly adaptable as "reveal the After view progressively, or let the user respond as soon as they can judge fulfillment".
- Differences: intention (which goal), not the outcome of a multi-step plan; video, not AR.
- Scores: Purpose 1 | Timing 1 | Outcome NR | Discrepancy NR | Explanation NR | Repair NR | Evaluation 3
- Evidence strength: Indirect (intention inference, measured objectively)
- Notes: The HERB result shows that user expectations of complex robots are heterogeneous. This argues for measuring prior expectation explicitly, e.g., a prediction before the display is shown.

### Kwon2018_Incapability
- Title / Authors / Year / Venue / URL: "Expressing Robot Incapability" / M. Kwon, S. H. Huang, A. D. Dragan / 2018 / HRI '18 / arXiv:1810.08167
- verified: true (full text arXiv); peer_reviewed: true
- Class: Methodologically Relevant
- Concepts: Interpretation (goal), Feasibility (cause of incapability)
- Construct defined: understanding of (a) what the robot is trying to do and (b) why it fails.
- Measures/instruments: **goal recognition** via an open-ended answer, then ratings of 4 plausible goals (1 correct), then a ranking. **Cause-of-incapability recognition** via ratings of 5 plausible causes (1 correct). Perception and collaboration-willingness scales.
- What they evaluate: pilot studies (N = 60 each, MTurk) on timing and repetition. In the main study, incapability-expressing motions significantly increased the rating of the correct goal (F(1,119) = 19.43, p < .0001) and improved cause recognition.
- Overlap with CoGround: the **"rate plausible alternatives, one of which is correct"** format is a good objective-ish measure of understanding the *cause* of non-fulfillment (object / action / constraint), which maps to CoGround's explanation layer.
- Differences: robot motion during an attempt, not a pre-execution plan preview.
- Scores: Purpose 1 | Timing NR | Outcome NR | Discrepancy 1 | Explanation 2 | Repair NR | Evaluation 3
- Evidence strength: Indirect

### Huang2019_CommunicateObjectives
- Title / Authors / Year / Venue / DOI: "Enabling Robots to Communicate their Objectives" / S. H. Huang, D. Held, P. Abbeel, A. D. Dragan / 2019 (RSS 2017 conference version) / Autonomous Robots 43(2):309–326 / arXiv:1702.03465
- verified: true (full text arXiv html); peer_reviewed: true
- Class: Methodologically Relevant
- Concepts: Interpretation (objective), GoalSatisfaction (anticipating behavior in novel situations)
- Construct defined: the user's ability to correctly anticipate robot behavior in novel situations, used as a proxy for an accurate mental model of the robot's objective.
- Measures/instruments: **prediction test**. In 6 new environments, the participant picks which of 4 trajectories the car would take and gives a 1–7 confidence rating. The score is +confidence if correct and −confidence if incorrect.
- What they evaluate: main study N = 191 recruited, 161 analyzed, 6 between-subjects conditions. The best approximate-inference teaching model (Euclidean, deterministic) beat exact-inference IRL (p = .025). In a baseline study (n = 28 analyzed), the best model vs. random was not significant (p = .23). In a coverage study (n = 53 analyzed), coverage-augmented teaching beat random (p = .049).
- Overlap with CoGround: **confidence-weighted prediction accuracy** gives a single calibration-aware comprehension score.
- Differences: driving simulation; teaching by examples, not plan preview.
- Scores: Purpose 1 | Timing 1 | Outcome 1 | Discrepancy NR | Explanation NR | Repair NR | Evaluation 3
- Evidence strength: Indirect

### Huang2018_CriticalStates
- Title / Authors / Year / Venue / URL: "Establishing Appropriate Trust via Critical States" / S. H. Huang, K. Bhatia, P. Abbeel, A. D. Dragan / 2018 / IROS 2018, pp. 3929–3936 / arXiv:1810.08174
- verified: true (full text arXiv, methods skimmed); peer_reviewed: true
- Class: Methodologically Relevant
- Concepts: Feasibility, GoalSatisfaction (deploy or not)
- Construct defined: appropriate trust = correct deploy/no-deploy decisions and correct take-over decisions given the policy's true flaws.
- Measures/instruments: a query phase (baseline), an exposure phase (critical states vs. other summaries), then **binary deploy and take-control decisions at query states** with known correct answers, plus Likert statements.
- What they evaluate: showing critical states led to more appropriate deployment and take-over decisions (abstract). I did not extract N.
- Overlap with CoGround: behavioral trust-calibration measure (decision correctness against ground truth) applicable to "approve the plan vs. repair it".
- Differences: Pong and driving domains; learned policies.
- Scores: Purpose 2 | Timing 2 | Outcome 1 | Discrepancy 1 | Explanation NR | Repair NR | Evaluation 3
- Evidence strength: Direct (decision about whether to deploy, a pre-execution judgment)

### Rosen2019_MRIntent
- Title / Authors / Year / Venue / DOI: "Communicating and controlling robot arm motion intent through mixed-reality head-mounted displays" / E. Rosen, D. Whitney, E. Phillips, G. Chien, J. Tompkin, G. Konidaris, S. Tellex / 2019 / IJRR 38(12–13):1513–1526 (preprint arXiv:1708.03655, ISRR 2017)
- verified: true (full text of preprint; IJRR abstract via search); peer_reviewed: true
- Class: Strongly Related (method)
- Concepts: Feasibility (collision or not)
- Construct defined: understanding where the robot will move, measured as classification of whether a planned motion collides.
- Measures/instruments: **binary classification of planned arm motions (collide / not collide)**, scored with true/false positive/negative rates, accuracy, and precision; task completion time; SUS; NASA-TLX.
- What they evaluate: N = 32, within-subjects, 3 interfaces (no visualization, 2D monitor RViz-like, MR HoloLens). Compared with the next-best interface (2D), MR reduced completion time by 7.4 s on average (−62%), increased accuracy by 16%, and increased precision by 11% (preprint numbers; the journal version may differ).
- Overlap with CoGround: **closest objective AR pre-execution comprehension study**. It previews a plan in situ and asks the user to judge a plan property (feasibility/safety) quickly and accurately, which matches CoGround's speed and accuracy constructs.
- Differences: judges collision (feasibility), not goal satisfaction; single motion, no After-state rendering; no repair beyond goal-pose adjustment.
- Scores: Purpose 2 | Timing 3 | Outcome 1 | Discrepancy 2 | Explanation NR | Repair 1 | Evaluation 3
- Evidence strength: Direct
- Notes: Rosen's related work cites an AR study "with no accuracy increase" (ref [25]). Cross-check needed as possible contrary evidence.

### Walker2018_ARIntent
- Title / Authors / Year / Venue / DOI: "Communicating Robot Motion Intent with Augmented Reality" / M. Walker, H. Hedayati, J. Lee, D. Szafir / 2018 / HRI '18, pp. 316–324 / 10.1145/3171221.3171253
- verified: true (abstract); peer_reviewed: true
- Class: Partially Related
- Concepts: Interpretation (motion intent)
- Measures/instruments: objective task efficiency (completion time) and subjective perceptions (intent clarity, robot as teammate). Exact items not verified.
- What they evaluate: several AR designs improved objective task efficiency over an embodied-cue baseline, with trade-offs between intent clarity and perceptions of the robot as a teammate (abstract).
- Overlap with CoGround: AR intent; shows that "clarity" and teammate perception can trade off.
- Differences: drone navigation, measured during execution; no outcome comprehension test.
- Scores: Purpose 1 | Timing 1 | Outcome NR | Discrepancy NR | Explanation NR | Repair NR | Evaluation 2
- Evidence strength: Supporting

### Hoffman2018_2023_XAIMetrics
- Title / Authors / Year / Venue / DOI: "Metrics for Explainable AI: Challenges and Prospects" (arXiv:1812.04608, 2018) and "Measures for explainable AI: Explanation goodness, user satisfaction, mental models, curiosity, trust, and human-AI performance" (Frontiers in Computer Science 5, 2023, 10.3389/fcomp.2023.1096257) / R. R. Hoffman, S. T. Mueller, G. Klein, J. Litman
- verified: true (2018 full text; 2023 abstract); peer_reviewed: 2018 false (arXiv), 2023 true
- Class: Methodologically Relevant (instrument source)
- Construct defined: six areas: explanation goodness (a priori, rated by researchers), explanation satisfaction (a posteriori, rated by users), mental model/understanding, curiosity, appropriate trust and reliance, and human-XAI work-system performance.
- Measures/instruments:
  - **Explanation Satisfaction Scale (Appendix C):** 5-point agree/disagree items, e.g., "From the explanation, I understand how the [software] works", "This explanation ... is satisfying" (others cover detail sufficiency, completeness, usefulness to goals, accuracy, and trust/confidence; the reverse-scored "irrelevant details" item was flagged as confusing). Cronbach's α = 0.86. In a small discriminant test (N = 8), good vs. bad explanations scored M = 42.75 vs. 30.00, d = 1.5, marginal p.
  - **Explanation Goodness Checklist (Appendix A).**
  - **Mental-model elicitation tasks:** Prediction Task ("users predict what the AI will do"; recommended with a confidence rating plus a free-text justification or counterfactual probe), Glitch Detector Task, Self-Explanation / Teach-back, Cued Retrospection, Diagramming / Concept mapping, and ShadowBox Lite.
  - **Trust:** a minimal two-item version ("Do you trust the machine's outputs?" for trust, "Would you follow the machine's advice?" for reliance); trust scales are reviewed in Appendix D.
- Overlap with CoGround: gives ready-made instruments for "clarity" (Explanation Satisfaction) and understanding (prediction task with confidence). The authors explicitly warn that performance on different elicitation tasks may not align (diagram adequacy did not match prediction performance; St.-Cyr & Burns 2002), so CoGround should use more than one.
- Scores: all NR
- Evidence strength: Supporting (instrument)

### SannemanShah2022_SAFEAI
- Title / Authors / Year / Venue / DOI: "The Situation Awareness Framework for Explainable AI (SAFE-AI) and Human Factors Considerations for XAI Systems" / L. Sanneman, J. A. Shah / 2022 / IJHCI 38(18–20):1772–1788 / 10.1080/10447318.2022.2081282 (earlier version: EXTRAAMAS 2020, 10.1007/978-3-030-51924-7_6)
- verified: true (abstract); peer_reviewed: true
- Class: Methodologically Relevant
- Construct defined: XAI levels mapped to SA levels: L1 = what the AI did or decided, L2 = why, L3 = what it will do next (projection). Also covers workload considerations for the content and frequency of explanations, and trust calibration.
- Measures/instruments: proposes evaluating XAI with SA measures (SAGAT-style queries per level), workload, and trust calibration. Their empirical reward-explanation study (RA-L 2022, 7(4):8956–8963) was not verified in detail.
- Overlap with CoGround: the most direct bridge from SA measurement to explanation evaluation. CoGround's query battery can be organized by SAFE-AI levels.
- Scores: all NR
- Evidence strength: Supporting (framework)

### Anderson2020_MentalModelsRL
- Title / Authors / Year / Venue / DOI: "Mental Models of Mere Mortals with Explanations of Reinforcement Learning" / A. Anderson, J. Dodge, et al. / 2020 / ACM TiiS 10(2), Art. 15 / 10.1145/3366485 (preprint arXiv:1903.09708)
- verified: true (full text preprint, methods skimmed); peer_reviewed: true
- Class: Methodologically Relevant
- Construct defined: mental-model quality, measured by (1) post-task explanations and (2) **accuracy of predicting the agent's next action at each decision point**.
- Measures/instruments: action prediction accuracy at decision points; open-ended mental-model descriptions, coded.
- What they evaluate: N = 124 in-lab, 4 between-subjects treatments (Control, Saliency, Rewards, Everything). In some situations, the "Everything" group predicted worse than all others (abstract). This is evidence of **information overload: more explanation can reduce prediction accuracy**.
- Overlap with CoGround: supports CoGround's "minimal at a glance, detail on demand" principle; provides a prediction-accuracy protocol.
- Differences: RTS game agent; not physical outcomes.
- Scores: all NR
- Evidence strength: Indirect

### Kulesza2013_MentalModels
- Title / Authors / Year / Venue / DOI: "Too much, too little, or just right? Ways explanations impact end users' mental models" / Kulesza, Stumpf, Burnett, Yang, Kwan, Wong / 2013 / IEEE VL/HCC, pp. 3–10 / 10.1109/VLHCC.2013.6645235
- verified: true (abstract); peer_reviewed: true
- Class: Background
- Construct defined: mental-model fidelity as a function of explanation **soundness** (how truthful each element is) and **completeness** (how much of the system is described).
- Measures/instruments: mental-model questionnaires scored against ground truth (details not verified).
- What they evaluate: completeness mattered more than soundness for building accurate mental models (via secondary summary; verify).
- Overlap with CoGround: guidance on how much of the plan the "explore" layer must show.
- Scores: all NR
- Evidence strength: Indirect

### Sukkerd2020_ContrastiveMDP
- Title / Authors / Year / Venue / URL: "Tradeoff-Focused Contrastive Explanation for MDP Planning" / R. Sukkerd, R. Simmons, D. Garlan / 2020 / IEEE RO-MAN 2020 / arXiv:2004.12960
- verified: true (full text); peer_reviewed: true
- Class: Strongly Related (evaluation method)
- Concepts: GoalSatisfaction (is the plan best for the user's preferences?), Feasibility (tradeoffs)
- Construct defined: understanding of the planner's tradeoff rationale, operationalized as the user's ability to **correctly determine whether the agent's proposed plan is the best one with respect to a given (hypothetical) user preference**.
- Measures/instruments: binary correctness; confidence; a **"Reliable Confidence Score"** from −4 to +4 (sign = correct or incorrect, magnitude = confidence); analyzed with mixed-effects regression with random intercepts for participants and items.
- What they evaluate: N = 106 recruited on MTurk, 99 valid (49 control / 50 treatment), 3 questions each (297 data points), drawn from 48 unique question items, in a mobile-robot navigation domain. With explanations, the odds of being correct were about **3.8× higher** (95% CI [2.03, 7.12]). Confidence was +0.42 (d = 0.43). Score was +1.72 (d = 0.62). "Preference-misaligned" scenarios (where the plan is NOT best for the user) reduced correctness (OR ≈ 0.36).
- Overlap with CoGround: **closest to a "goal satisfaction judgment" test.** The user decides whether a pre-execution plan satisfies their preferences. The aligned vs. misaligned scenario manipulation corresponds to CoGround's fulfilled vs. unfulfilled plans. Errors were higher for misaligned plans, which is exactly the case CoGround targets.
- Differences: text and 2D map explanation; navigation cost tradeoffs rather than object-placement outcomes; no repair.
- Scores: Purpose 3 | Timing 3 | Outcome 1 | Discrepancy 2 | Explanation 2 | Repair 0 | Evaluation 3
- Evidence strength: Direct

### Das2021_RobotFailureXAI
- Title / Authors / Year / Venue / URL: "Explainable AI for Robot Failures: Generating Explanations that Improve User Assistance in Fault Recovery" / D. Das, S. Banerjee, S. Chernova / 2021 / HRI '21, pp. 351–360 / arXiv:2101.01625
- verified: true (full text); peer_reviewed: true
- Class: Strongly Related (evaluation method for the explanation and repair layer)
- Concepts: Feasibility (cause of failure), Repair (solution identification)
- Construct defined: the user's ability to identify the **cause of a failure** and the **solution** for it.
- Measures/instruments: **Failure Identification (FId)** and **Solution Identification (SId)** scored with F1 against ground truth, comparing a pre-explanation baseline block with an explanation block (within-subject improvement). The study used GIFs of actions leading to the failure plus 3 views of the final environment state.
- What they evaluate: N = 80 recruited, 70 analyzed (those at 100% baseline were excluded), 13–15 per condition, 5 conditions (None, Action-Based, Context-Based, AB-History, CB-History), household pick-and-place. Context had a significant effect on FId (F(2,67) = 6.95, p = .0018). History had a significant effect on FId (F(2,67) = 3.36, p = .04). The effect on SId was marginal or mixed. CB-H was best for non-experts.
- Overlap with CoGround: an objective test of "understand the cause linked to object/action/context, then pick the fix". This can transfer to CoGround's explore-and-repair stage (cause identification F1 → repair correctness).
- Differences: explains failures during or after execution, not predicted pre-execution unfulfillment; text explanations, not AR.
- Scores: Purpose 2 | Timing 1 | Outcome 1 | Discrepancy 2 | Explanation 3 | Repair 2 | Evaluation 3
- Evidence strength: Direct (cause and solution understanding, measured objectively)

### Chakraborti2019_ModelReconciliationStudy
- Title / Authors / Year / Venue / URL: "Plan Explanations as Model Reconciliation – An Empirical Study" / T. Chakraborti, S. Sreedharan, S. Grover, S. Kambhampati / 2019 / HRI '19 / arXiv:1802.01013
- verified: true (preprint full text skimmed); peer_reviewed: true
- Class: Partially Related
- Concepts: Feasibility (plan correctness and optimality)
- Construct defined: explanation as reconciling the human's model with the robot's model so that the robot's plan appears correct and optimal.
- Measures/instruments: Study 1: participants generated explanations (N = 12 in C1, 10 in C2). Study 2: participants (preprint: 27) judged plans on 12 maps with random explanation types; subjective responses and explanation requests were recorded.
- What they evaluate: model-reconciliation explanations were feasible for conveying plan correctness and optimality. About one third of the time, participants still asked for explanations even when the plan was explicable (preprint).
- Overlap with CoGround: users can't always tell when a plan is fine; "request explanation" rate is a behavioral calibration indicator.
- Differences: search-and-rescue map; no spatial outcome view.
- Scores: Purpose 2 | Timing 3 | Outcome NR | Discrepancy 1 | Explanation 2 | Repair NR | Evaluation 2
- Evidence strength: Indirect
- Notes: Verify HRI'19 final N; the preprint and final versions may differ.

### Porfirio2024_Polaris
- Title / Authors / Year / Venue / DOI: "Goal-Oriented End-User Programming of Robots" / D. Porfirio, M. Roberts, L. M. Hiatt / 2024 / HRI '24 / 10.1145/3610977.3634974 (arXiv:2403.13988)
- verified: true (full text); peer_reviewed: true
- Class: Strongly Related
- Concepts: Interpretation (goal predicates → plan), Feasibility (plan feasibility score), GoalSatisfaction (expectations matched)
- Construct defined: whether the user's expectations of robot behavior match the actual robot performance ("expectations matched": overall / what / when / why).
- What they do (implemented): goal-predicate EUP tool with an off-the-shelf task planner. A **Plan Visualizer exposes the planner's output before runtime**; clicking an action shows the world state resulting from that action, i.e., intermediate predicted states.
- Measures/instruments: plan quality (feasibility score 0–4, human-effort cost, runtime score); a custom expectations-matched questionnaire (4 factors × 5 items, 7-point, α ≈ 0.78–0.80); RoSAS competence; SUS; USE; NASA-TLX.
- What they evaluate: N = 32 (17 plan-vis, 15 no-vis), with 27 for post-execution measures, in a tidying scenario (wash plate and cup). Significant: plan quality in human effort (U = 182.5, p = .017). Marginal (p < .1): usefulness, satisfaction, competence, expectations overall and "why". Within plan-vis, Plan Visualizer usage correlated strongly with expectations matched (overall ρ = 0.831, p < .001). Robot familiarity correlated with most measures. "Intended use" participants averaged a feasibility score of 3.63/4; "no-use" averaged 0.75.
- Overlap with CoGround: household tidying; pre-execution plan preview with intermediate state inspection; users fix their goal specification after seeing the plan. Very close to CoGround's "explore plan on demand → repair" loop.
- Differences: 2D GUI; the user authors goals (rather than delegating via a request); expectation match is self-reported only (no objective comprehension test); no glanceable After summary.
- Scores: Purpose 2 | Timing 3 | Outcome 2 | Discrepancy 2 | Explanation 1 | Repair 2 | Evaluation 2
- Evidence strength: Indirect (subjective expectation match plus objective plan quality)
- Notes: Should be cross-checked by the Stream A (closest-work) agent.

### Wang2016_TrustCalibrationExplanations
- Title / Authors / Year / Venue / DOI: "Trust Calibration within a Human-Robot Team: Comparing Automatically Generated Explanations" / N. Wang, D. V. Pynadath, S. G. Hill / 2016 / HRI '16, pp. 109–116
- verified: true (full text); peer_reviewed: true
- Class: Methodologically Relevant
- Construct defined: subjective trust = perceived trustworthiness (ability, benevolence, integrity); behavioral trust = **compliance** with robot recommendations; team performance = **proportion of correct decisions**; transparency/understanding items.
- Measures/instruments: post-mission surveys; compliance rate; correct-decision rate; robot ability (high/low) × explanation type.
- What they evaluate: N = 160 recruited on MTurk, 140 analyzed; simulated reconnaissance. Ability had significant effects on trust and correct decisions (e.g., F(1,134) = 11.67, p < .001 for correct decisions). Explanations improved transparency, trust, and team performance (abstract).
- Overlap with CoGround: compliance relative to robot correctness is the standard behavioral calibration measure (appropriate reliance).
- Scores: Purpose 1 | Timing 1 | Outcome NR | Discrepancy 1 | Explanation 2 | Repair NR | Evaluation 3
- Evidence strength: Indirect

### OkamuraYamada2020_AdaptiveTrustCalibration
- Title / Authors / Year / Venue / DOI: "Adaptive trust calibration for human-AI collaboration" / K. Okamura, S. Yamada / 2020 / PLOS ONE 15(2):e0229132 / 10.1371/journal.pone.0229132
- verified: true (abstract); peer_reviewed: true
- Class: Methodologically Relevant
- Construct defined: over-trust and under-trust as mismatches between reliance behavior and actual AI capability. Calibration is detected from choice behavior.
- Measures/instruments: **signal-detection sensitivity d′** on reliance decisions; trust calibration cues (TCC) presented on detected miscalibration.
- What they evaluate: one TCC group had significantly higher d′ than the no-TCC group.
- Overlap with CoGround: **d′ / criterion c** as a calibration metric for "accept plan vs. flag problem" decisions on seeded good and bad plans.
- Scores: all NR
- Evidence strength: Supporting (metric)

### LeeSee2004_TrustAutomation
- Title / Authors / Year / Venue / DOI: "Trust in Automation: Designing for Appropriate Reliance" / J. D. Lee, K. A. See / 2004 / Human Factors 46(1):50–80 / 10.1518/hfes.46.1.50_30392
- verified: true (abstract, PubMed); peer_reviewed: true
- Class: Background
- Construct defined: appropriate reliance; trust **calibration** (trust matches capability), **resolution** (how precisely trust discriminates capability levels), and **specificity** (component- or time-specific trust). The definitions are from secondary summaries; verify the wording.
- Overlap with CoGround: "resolution" maps to whether users trust fulfilled sub-goals while distrusting unfulfilled ones within a plan, i.e., per-object calibration.
- Scores: all NR
- Evidence strength: Supporting

### Schaefer2016_TPSHRI
- Title / Authors / Year / Venue / DOI: "Measuring Trust in Human Robot Interactions: Development of the 'Trust Perception Scale-HRI'" / K. E. Schaefer / 2016 / chapter in Robust Intelligence and Trust in Autonomous Systems (Springer) / 10.1007/978-1-4899-7668-0_10
- verified: false (secondary sources: HRI scale database, citing papers); peer_reviewed: true (book chapter)
- Class: Background
- Measures/instruments: 40 items ("What percentage of the time will this robot..." on 0–100% in 10% steps); a 14-item subset is suggested, but the database notes that only 11 items are identifiable in the text.
- Overlap with CoGround: a pre/post subjective trust measure, to be paired with behavioral calibration.
- Scores: all NR
- Evidence strength: Supporting

### AmirAmir2018_HIGHLIGHTS
- Title / Authors / Year / Venue: "HIGHLIGHTS: Summarizing Agent Behavior to People" / D. Amir, O. Amir / 2018 / AAMAS '18
- verified: true (abstract-level from repository records); peer_reviewed: true
- Class: Methodologically Relevant
- Construct defined: users' ability to assess agent capabilities from a summary of important states.
- Measures/instruments: capability assessment correctness, helpfulness ratings. Follow-ups (Huber et al. 2021) used "choose the better-performing agent" tasks.
- What they evaluate: participants assessed agent capabilities more successfully with HIGHLIGHTS than with baseline summaries.
- Overlap with CoGround: summarizing many states into a few important ones is analogous to showing only the outcome-relevant Before/After differences.
- Scores: all NR
- Evidence strength: Indirect

### Lage2019_HumanSimulatability
- Title / Authors / Year / Venue: "Human Evaluation of Models Built for Interpretability" / Lage, Chen, He, Narayanan, Kim, Gershman, Doshi-Velez / 2019 / HCOMP 2019, pp. 59–67
- verified: true (abstract); peer_reviewed: true
- Class: Methodologically Relevant
- Construct defined: interpretability as **human simulatability**: forward simulation (predict output), verification (is this output consistent?), and counterfactual (what change flips it?).
- Measures/instruments: response time, accuracy, and subjective difficulty per task. Exact numbers not verified.
- Overlap with CoGround: the three task types map neatly onto CoGround's predict-outcome (forward), check-goal-satisfaction (verification), and repair (counterfactual: "what change makes it satisfy?").
- Scores: all NR
- Evidence strength: Supporting (method)

### RiskoGilbert2016_CognitiveOffloading
- Title / Authors / Year / Venue / DOI: "Cognitive Offloading" / E. F. Risko, S. J. Gilbert / 2016 / Trends in Cognitive Sciences 20(9):676–688 / 10.1016/j.tics.2016.07.002
- verified: false (secondary descriptions only); peer_reviewed: true
- Class: Background
- Construct defined: the use of physical action to alter the information-processing requirements of a task so as to reduce cognitive demand. A metacognitive account of when people offload.
- Overlap with CoGround: an in-situ After view offloads the mental simulation of plan effects onto the display. The measurable consequences are reduced workload and RT, plus possible over-reliance (users stop checking), so offloading should be paired with calibration measures.
- Scores: all NR
- Evidence strength: Supporting

### Tabrez2020_MentalModelSurvey
- Title / Authors / Year / Venue / DOI: "A Survey of Mental Modeling Techniques in Human–Robot Teaming" / A. Tabrez, M. B. Luebbers, B. Hayes / 2020 / Current Robotics Reports 1:259–267 / 10.1007/s43154-020-00019-0
- verified: true (abstract); peer_reviewed: true
- Class: Background
- Construct defined: first-order vs. second-order mental models; evaluation methods and metrics for mental modeling in HRT.
- Overlap with CoGround: an entry point for mental-model accuracy metrics in HRI. Recommended for snowballing by another agent.
- Scores: all NR
- Evidence strength: Supporting

---

## Cross-cutting observations

1. **Objective comprehension tests in the literature come in 5 families:**
   - (a) Binary plan-property judgment with seeded ground truth: Rosen collisions, Mercado/Stowers wrong plans, Sukkerd "is the plan best for this preference", Huang 2018 deploy/take-over.
   - (b) Forced-choice prediction among alternatives, often confidence-weighted: Huang 2019, Kwon 2018, Anderson 2020, Hoffman's Prediction Task.
   - (c) Time-to-correct-inference: Dragan 2013 "stop when you know"; Blascheck staircase exposure threshold.
   - (d) SA queries per level: SAGAT/SAT studies, SAFE-AI.
   - (e) Cause and solution identification scored as F1: Das 2021.
2. **Speed–accuracy and information-load trade-offs are real and sometimes contrary:**
   - Stowers 2020 found that higher transparency cost timeliness.
   - Anderson 2020 found that the "Everything" explanation sometimes reduced prediction accuracy.
   - Mercado 2016 found no RT or workload cost.
   - Walker 2018 found a trade-off between clarity and teammate perception.
   - CoGround should therefore measure speed and accuracy jointly, not assume "more info = better".
3. **Misaligned / unfulfilled cases are where users fail.** In Sukkerd 2020 the odds of being correct were about 0.36× in preference-misaligned scenarios. CoGround's evaluation must oversample unfulfilled plans and report hit rate and false-alarm rate separately.
4. **Subjective-only "expectations matched"** (Porfirio 2024) is common in plan-preview EUP work. **No study found measured objective goal-satisfaction judgment speed and accuracy for a spatial Before/After outcome preview** for a household manipulation plan. Rosen 2019 (feasibility, AR) and Sukkerd 2020 (goal satisfaction, 2D/text) are the two nearest halves. This is a gap statement for the comprehension measures, not a novelty claim for CoGround overall.
5. **Glanceability** has a clear definition (Matthews) and one rigorous objective protocol (Blascheck staircase exposure time), but has not been applied to robot plan or outcome displays in the works found.

---

## Construct → Measure table

Proposed operationalization for CoGround. The core task: participants view a plan result for a delegated tidying task, of which some fraction is seeded with unfulfilled sub-goals or constraint violations, and judge fulfillment.

| Construct | Definition for CoGround | Primary objective measure | Secondary / subjective measure | Source precedent |
|---|---|---|---|---|
| **Speed (glanceability)** | Time to reach a correct judgment of how far the request will be fulfilled | (1) Decision RT from display onset to a "fully / partially / not fulfilled" response (correct trials only, plus inverse-efficiency score RT/accuracy). (2) **Exposure-threshold staircase**: minimum Before/After exposure at which fulfillment judgment reaches about 75–80% accuracy. (3) Optional "stop when you know" progressive reveal. | Number and duration of glances or head turns in AR (eye/head tracking); time until first "explore" action | Blascheck 2019; Dragan 2013; Rosen 2019 (completion time); Mercado 2016 / Stowers 2020 (RT) |
| **Accuracy (outcome comprehension)** | Correctly identifying which requested goals will and will not be satisfied, and where | (1) Per-object fulfillment classification against ground truth: hit rate, false-alarm rate, F1. (2) SAGAT/SAFE-AI-style queries after the display: L1 "What will the robot move?", L2 "Why is the cup not placed?", L3 "Where will object X be after execution?". (3) Localization: tap or point at the unfulfilled object in AR (accuracy plus RT). | Confidence per judgment (1–7) | Rosen 2019 (TP/FP/TN/FN); Sukkerd 2020; Das 2021 (F1); Endsley 1995; Sanneman & Shah 2022 |
| **Understanding of cause (explore layer)** | Correctly attributing non-fulfillment to object / action / constraint (e.g., a house rule) | Cause identification among plausible alternatives (1 correct), scored as accuracy or F1. Repair correctness: does the chosen local edit make the replanned outcome satisfy the goal? Plus time-to-repair and number of edits. | Hoffman Explanation Satisfaction Scale; Hoffman Prediction/Counterfactual task ("What change would make X satisfied?") | Das 2021 (FId/SId); Kwon 2018; Lage 2019 (counterfactual simulation); Porfirio 2024 (feasibility score) |
| **Clarity** | The display is perceived as easy to interpret and unambiguous | Agreement between users' interpretation and ground truth on ambiguous items; inter-participant variance of predictions (Dragan's HERB heterogeneity shows why this matters) | Explanation Satisfaction Scale (Hoffman, 5-point, α = 0.86); single-item clarity / "I understood what the robot will achieve"; SUS for overall usability | Hoffman 2018/2023; Walker 2018; Porfirio 2024 |
| **Cognitive effort** | Mental workload required to reach the judgment | Dual-task or secondary-task RT (as in Selkowitz 2017's dual task); pupil diameter if eye-tracking is available (not verified in sources here); number of explore actions needed | NASA-TLX (raw or weighted) (used in Rosen 2019 and Porfirio 2024); SMEQ / Paas single-item mental effort (not verified here) | Rosen 2019; Selkowitz 2017; Stowers 2020; Risko & Gilbert 2016 (offloading rationale) |
| **Calibration (trust and confidence)** | Users accept fulfilled plans and flag or repair problematic ones; confidence tracks correctness | (1) **Signal detection**: d′ and criterion c for accept vs. flag over seeded good and bad plans (over-trust = misses of unfulfilled plans; under-trust = false alarms or unnecessary exploration of fine plans). (2) Confidence–accuracy calibration: Brier score or a confidence-weighted score (Sukkerd's −4..+4; Huang's ±confidence). (3) Behavioral reliance: approve rate when correct vs. incorrect; explore/explanation-request rate on fine plans (Chakraborti: about 1/3 still requested explanations). | Trust scale pre/post (Schaefer TPS-HRI 14-item or Jian et al. 2000, not verified here); Hoffman two-item trust/reliance | Okamura & Yamada 2020 (d′); Huang 2018 (deploy/take-over); Wang 2016 (compliance vs. correctness); Mercado 2016 (seeded 3/8 wrong); Lee & See 2004 |

**Design recommendations derived from the evidence:**
- Seed roughly 30–50% of plans with unfulfilled sub-goals. Mercado used 3/8 = 37.5%; this is a precedent, not a requirement.
- Include preference- or rule-misaligned cases, since accuracy drops there (Sukkerd).
- Measure a baseline prediction before the display (Dragan, Huang 2018 query phase) to control for prior expectations and robot familiarity (Porfirio found familiarity correlated with nearly every measure).
- Compare against a 2D or text plan baseline. AR superiority is not assumed: Rosen found MR better than 2D, but Rosen's ref [25] reports no accuracy gain, and Stowers reports time costs of more information.

---

## Agent summary

**Top 5 closest works (to CoGround's comprehension evaluation):**
1. **Sukkerd2020** gives an objective goal-satisfaction judgment of a pre-execution plan (correctness, confidence, reliable-confidence score; OR about 3.8 with explanation). It is the best template for the accuracy and calibration measures.
2. **Rosen2019** is an in-situ AR preview of a plan with binary judgment, TP/FP rates, time, and NASA-TLX. It is the best template for speed and accuracy in AR, though it judges feasibility, not goal satisfaction.
3. **Porfirio2024 (Polaris)** is a household tidying plan preview before runtime with intermediate states and repair of the goal spec. Its expectation match is subjective only.
4. **Das2021** offers objective cause and solution identification (F1) in a household pick-and-place task, which suits the explore/repair layer.
5. **Mercado2016 / Stowers2020 (SAT)** cover plan acceptance with seeded wrong recommendations, accuracy plus RT plus workload, and contrary time-cost evidence.

**Key gaps:**
- No found study objectively measures glanceability (exposure-threshold or RT) for robot plan or outcome displays.
- No study measured objective goal-satisfaction judgments over spatial Before/After predicted states.
- Calibration (d′) is rarely applied to pre-execution plan approval in HRI.

**Open doubts:**
- Selkowitz2017's SA instrument is unverified.
- Hoffman's full Explanation Satisfaction item list beyond items 1–2 is paraphrased from the text, so check Appendix C before use.
- Rosen IJRR final numbers may differ from the preprint.
- The Chakraborti HRI'19 final N is unverified.
- Risko & Gilbert and Schaefer were verified from secondary sources only.

**Cross-check suggestions:**
- **Stream A agent:** Porfirio2024 (Polaris), Rosen2019, Sukkerd2020.
- **Explainable-planning agent:** Chakraborti2019, and Sanneman & Shah RA-L 2022 (reward explanations with SA-level measures).
- Someone should identify Rosen 2019's ref [25] (an AR intent study with no accuracy gain, possible contrary evidence).
- Someone should check Huber et al. 2021 (HIGHLIGHTS + saliency, mixed results).
