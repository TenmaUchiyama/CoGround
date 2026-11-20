# I1 — Integrator-1 cross-read of the closest papers

Role: the spec rule that "a different agent re-reads the closest papers" (HouseRule_Research.md §3). I re-read every paper below **in the original**, downloaded the PDFs and ran `pdftotext`, and did not rely on S1/S2/S3/C1. Date: 2026-11-19.
Legend: **[本文確認]** = I read the passage in the original full text. **[要旨のみ]** = abstract or listing only. **未確認 (unverified)** = not found in the original.

---

## 1. Search / reading log

| # | Date | Source | Query / action | Result |
|---|---|---|---|---|
| 1 | 2026-11-19 | Author PDF scazlab.yale.edu/…/Xuan_AAAI19.pdf (= arXiv 1812.02576v1) and arXiv 1812.02576v2 | Full text read; diffed v1 against v2 | v1 lists "Zong Xuan Tan", v2 lists "Zhi-Xuan Tan"; otherwise the text is the same except for layout |
| 2 | 2026-11-19 | ojs.aaai.org/index.php/AAAI/article/view/4808 (via web search) + OpenAlex W2964255654 | Bibliographic check | AAAI-19, Proc. AAAI 33(01):8058–8065. Authors: **Zhi-Xuan Tan, Jake Brawer, Brian Scassellati** |
| 3 | 2026-11-19 | bit.ly/2z8obET (`curl -I`) | Tried to resolve the demo video | Redirects to Google Photos (photos.app.goo.gl/XMovjoBMpTJJLsnFA). Cannot be played from this environment, so the video stays **未確認** |
| 4 | 2026-11-19 | Science News article (sciencenews.org/?p=224668), secondary source | Description of the demo | Used only to corroborate the scenario-1 initial conditions (see §2 note T1). Not used as primary evidence |
| 5 | 2026-11-19 | IROS PDF pixl.cs.princeton.edu/…/tidybot_IROS23.pdf + arXiv 2305.05658v2 (= AuRo version) | Full text read: §III–IV (IROS), §3–4.6 (v2) | OpenAlex W4388720459: Autonomous Robots 47(8):1087–1102, 2023, DOI 10.1007/s10514-023-10139-z |
| 6 | 2026-11-19 | arXiv 2611.18026v2 PDF (16 Nov 2026) | Full text read, including references | No appendix. Rule texts are never shown |
| 7 | 2026-11-19 | arXiv 2503.07885 PDF (RA-L preprint, "accepted February 2026") | Full text read, including App. A–D | — |
| 8 | 2026-11-19 | OpenAlex `filter=cites:W2964255654` (Tan) | Forward citations | 18 citing works. None adds resident-taught prohibitions/obligations to a tidying robot task in 2024–26 (see §5) |
| 9 | 2026-11-19 | OpenAlex `filter=cites:W4388720459` (TidyBot), pages 1–3 (489 records with abstracts) | Keyword screen in Python (prohibit, forbid, don't, norm, rule, constraint, safety, permission, personal…), restricted to 2024–26, then read ~20 abstracts | Candidates in §5 |
| 10 | 2026-11-19 | Semantic Scholar API (Tan, TidyBot citations) | — | HTTP 429 (rate-limited). Not used |
| 11 | 2026-11-19 | WebSearch (extended) | robot tidying user-taught prohibitions "do not touch" household rules LLM same scene different users 2025 2026 | Found FLEX (arXiv 2610.28893, CoRL 2026) and APOLLO (arXiv 2606.17309) |
| 12 | 2026-11-19 | arXiv 2606.17309 PDF | What "abstention" means in APOLLO | Read the relevant parts (§I, §IV) |
| 13 | 2026-11-19 | arXiv abs 2610.28893 + MIT News 2026-11-09 | FLEX | [要旨のみ] + news |
| 14 | 2026-11-19 | WebSearch | "That's Mine" … 2025 OR 2026 follow-up tidying LLM | No LLM-era follow-up found |

---

## 2. Verified comparison-table rows

Columns follow 00_brief.md.

### 2.1 Tan, Brawer, Scassellati, "That's Mine! Learning Ownership Relations and Norms for Robots", AAAI 2019 — verified TRUE

**Author-list conflict resolved:** the authors are **Zhi-Xuan Tan** (printed "Zong Xuan Tan" in arXiv v1 / author PDF), **Jake Brawer**, and **Brian Scassellati**, all at Yale; Tan also has an A*STAR affiliation. This is confirmed by the PDF header (v1 and v2), AAAI OJS 4808, and OpenAlex. **S1 is correct. Codex ("Xuan Tan, Fanjun Li, Brian Scassellati") is wrong:** Fanjun Li is not an author.

Facts that hold across all Tan scenarios:
- The paper **never describes how speech or language is understood** (no ASR, no parser, no template). Whether understanding is template-based is therefore **未確認**. Only the utterances are quoted ("No Baxter, that's mine!").
- The paper **never describes the object perception pipeline on Baxter** (no camera, detector, or marker is mentioned). What it does give is the feature set used to predict ownership: "an object's 3D position, color, and the most recent time each agent interacted with that object" (§Predicting ownership relations). The rule vocabulary is designer-defined: `ownedBy`, `isColored`, `inArea` ("relations readily perceived by robotic hardware", §Ownership norms). Whether these feature values come from vision or are given as ground truth is **未確認**.
- Only prohibitions are modelled: "we focused on rules that forbid specific actions under certain conditions. Actions not explicitly forbidden were assumed to be allowed" (§Ownership norms). There are **no obligations**.
- Execution uses a threshold: a rule evaluates to a probability, and the robot avoids the action "if 0.75 is above a user-specified threshold for rule obedience, but will go ahead otherwise." There is **no undetermined/hold state**.

| Paper (URL) | Condition/demo | Evidence location | Rule origin | Rule representation | Novelty unit | Perception input | Instruction matching | Decision & evidence | Match A–D | Differences |
|---|---|---|---|---|---|---|---|---|---|---|
| Tan et al. AAAI 2019 [本文確認] https://ojs.aaai.org/index.php/AAAI/article/view/4808 | **Real S1**: told to "clear the workspace", Baxter tries to throw away a red object and is reprimanded "No Baxter, that's mine!" | §Video demonstration ¶2; Fig. 1 top | Resident explicit, given **during execution** as a verbal reprimand | The single reprimand is "simultaneously interpreted as direct instruction of a norm, an object-specific permission, as well as an ownership claim". The system splits it into a predicate norm (`forbid trash if ownedBy any`), `forbid(trash,O)`, and `ownedBy(O,Xuan)`. The NL→logic method is **未確認** | Untaught instances: the "other red objects" | Ownership of the other red objects is **predicted** by KLR on position, colour, and last-interaction time. The paper does not say whether any ownership was known before the reprimand. A secondary source (Science News) says none was given and that the robot inferred the red blocks were Tan's because he had interacted only with them (see T1). Object sensing: **未確認** | The same broad request continues after the correction. It is not a later, independent request | **Partial execution**: "completing its task while avoiding touching any of the other red objects, which it correctly predicts to belong to the user". Qualitative demo only (video unwatchable) | A ○ (instances). D △: avoids forbidden objects and completes the rest of a broad request, but in one household with no rule swap | Rule is taught mid-task, not beforehand. Generalisation runs through an ownership attribute predicted from interaction history, not through a perceived physical attribute. No hold on unknowns. No obligations |
| same | **Real S2**: follows S1 chronologically. A new user (Jake) commands "throw away object 2" | §Video demonstration ¶3; Fig. 1 bottom | Resident explicit (from S1) | Owner-specific norm plus ownership graph | New requester, new single-object command | Ownership of object 2 is a **belief carried over from S1**. It is updated when Jake "claims exclusive ownership" | **A stored rule is reused for a later, independent request** (single object named) | **Refuses and apologises**. After the ownership claim, the same command is executed. Qualitative | B ○ (qualitative). D-like micro-contrast: same scene, same command, different normative facts → different action, on one object | The change is to a **fact** (ownership), not to the household rule set. No broad request. No rule retrieval step: all rules are evaluated |
| same | **Real S3**: norm induction from examples | §Video demonstration ¶4; Fig. 2 caption | Inferred from examples (object-specific permissions) | Induced `forbid pickUp if ownedBy any` (sequential rule learning; Alg. 1–4) | Untaught instance (object 4) | The system "is **initially aware of the ownership status** of the blocks" (GT-like ownership) | Later single-object pickUp request | **Refusal** ("denies the request in accordance with the learned norm"). Qualitative | A ○, C △ (structured rule; no effect measurement) | Ownership is given, not perceived. Single object |
| same | **Sim: norm learning** (20 blocks, 3 agents, colour as a distractor) | §Norm learning; Table 1 | Inferred from permissions generated by 3 designer rules (incl. `forbid collect if isColored red`) | Predicate Horn clauses | Untaught instances | Ownership known (noiseless) or 40–80% certain (noisy). Symbolic | — (rule accuracy only) | Controlled quantitative: acc/F1 from 0.995/0.995 (noiseless, all permissions) down to 0.761/0.519 (noisy, 0.25). Baseline 0.583/0.000 | A ○ (sim) | Note T2: the text says "100%, 75%, or 25%" but Table 1 columns are 1.00/0.50/0.25 |
| same | **Sim: task-based** collectAll / trashAll, "except where doing so would violate a set of norms it had to learn" | §Task-based evaluation; Table 3 | Online correction with true permissions. True owners are given "if ownership was relevant" | same | — | Symbolic | **Broad request** with norm exceptions, but norms are learned online during the same task | Quantitative: mistakes 6.30 / 6.32 vs baseline 8.75 / 15. Rule accuracy 0.975 / 0.877 | D △: avoidance and action errors are counted together, not separately | No prior teaching followed by a later request. No household swap. Errors are not split into forbidden-touch vs permitted-missed |

**T1 (S1 open question, partly resolved).** The video cannot be played. The paper does not state the initial ownership information for S1. It says only that the reprimand doubles as an ownership claim, and that the other red objects are "correctly predict[ed]" via perceptual heuristics. Science News (secondary) says no ownership facts were given in advance and that the inference came from Tan having interacted only with the red blocks. That matches the paper's KLR features (last-interaction time). **Conclusion:** in S1 the norm is taught by the reprimand, and ownership of the other objects is inferred from interaction-history features. In S3 ownership is given. Language handling and object sensing remain **未確認** in every scenario.

### 2.2 TidyBot — Wu, Antonova, Kan, Lepert, Zeng, Song, Bohg, Rusinkiewicz, Funkhouser; IROS 2023 and Autonomous Robots 47(8) 2023 — verified TRUE

| Paper (URL) | Condition/demo | Evidence location | Rule origin | Rule representation | Novelty unit | Perception input | Instruction matching | Decision & evidence | Match A–D | Differences |
|---|---|---|---|---|---|---|---|---|---|---|
| TidyBot [本文確認] https://arxiv.org/abs/2305.05658 (v2 = AuRo) / IROS PDF | **Text benchmark**: 96 scenarios (4 room types × 24); 2–5 receptacles; 4–10 seen and an equal number of unseen placements; 672 + 672 placements; **1,076 unique objects** | IROS §IV-A–C, Tab. I–III; v2 §4.1–4.3, Tab. 1–4 | Inferred from examples, written as text by the authors per scenario ("we created a benchmark dataset") | LLM summary in free text (e.g., "Put light-colored clothes in the drawer and dark-colored clothes in the closet"). No deontic type, no target/condition split | **Unseen objects** ("distinct from the seen examples") in the same scenario. **There is no instance-vs-category split**: an unseen object may be a new category or a new instance of a seen category. v2 Tab. 1 tags scenarios by sorting criterion: Category 86/96, Attribute 27/96, Function 24/96, Subcategory 31/96, Multiple 17/96 | GT object names as text | Rules given once; the only task is put-away; no rule selection | Placement accuracy (unseen): 91.2% vs examples-only 78.5%, CLIP-embedding 83.7%, WordNet 67.5%; commonsense 45.6%; human summary 97.5% (v2 Tab. 2, 4) | A ○ (placement); C △ (summarisation vs raw examples measures abstraction, not deontic decomposition) | Preferences only: no prohibition, permission, or exception; no partial execution |
| same | **Same objects × different preferences?** (claim D) | IROS §IV-A; v2 §4.1 | — | — | — | — | — | **Not reported.** No condition holds the object set and instruction fixed while changing the preference set. 1,076 unique objects over 1,344 placements suggests little reuse; the scenario files were not checked | D ✗ | The commonsense ablation shows only that personal rules differ from commonsense, not a paired swap |
| same | **Primitive selection** (pick&place vs pick&toss) | IROS §III-B; v2 §3.2 | Inferred from examples | Separate LLM summary ("pick and place shirts, pick and toss socks") | Unseen objects | Text in the prompt | — | **No benchmark accuracy for primitive choice** (confirmed absent). On the robot it is reported jointly with the receptacle (below) | A ○ (choice of manipulation method) | A choice between two methods, not a ban on contact |
| same | **Real robot**: 8 scenarios, "each with its own set of 10 objects", 2–5 receptacles, 4–10 seen examples, 3 runs each (240 object attempts); 70 unique unseen test objects, 11 receptacles | IROS §IV-D, Fig. 3; v2 §4.5, Fig. 4–6, Tab. 7 | Text examples for "a particular user", given before cleanup | Summary → **category list** extracted by the LLM and used as CLIP labels | Unseen real objects | **Estimated from images**: two overhead cameras + ViLD localise objects (92.5%); a base camera + CLIP classify over the summarised categories (95.5%; vs 70.7% with scenario object names, 52.3% with all names). Receptacle locations **hard-coded**; robot pose from ArUco. CLIP "will always output a prediction", so there is **no unknown/hold**. Failure modes: background objects; "white socks" matching anything white | One cleanup request per scenario. Rules are applied **per category, not per instance** | 85.0% put away correctly. Given the predicted category, the LLM chose the right receptacle **and** primitive for 100% of localised objects; execution 96.2%. Quantitative, but no robot baseline | A ○ with real perception | Each scenario uses a different object set, so no rule swap on the same scene. Forced classification. No prohibition |

### 2.3 Wu, Liu, Liang, Chen, Ma, Deng, Li, Li, Zhang, "A Generalizable Approach to Safety-Aware Robotic Behavior Planning with an Explicit Constraint Space", arXiv 2611.18026v2 (16 Nov 2026) — verified TRUE

| Paper (URL) | Condition/demo | Evidence location | Rule origin | Rule representation | Novelty unit | Perception input | Instruction matching | Decision & evidence | Match A–D | Differences |
|---|---|---|---|---|---|---|---|---|---|---|
| Wu et al. [本文確認] https://arxiv.org/abs/2611.18026 | **Constraint applicability**: trained on 50 scenes with C1, tested on 50 new scenes with C2; 3 task configurations each (single / double / multi), giving 150 held-out queries; 93 candidate rules | §III-B, §IV-A, Table I | **Not stated.** "Constraint Space consisting of textual safety rules"; labels are "manually annotated". No text mentions a user, resident, household rule, or preference (grep confirmed). Examples are general hazards (liquid near electronics, sharp objects near humans) | **Raw text** embedded by a frozen BGE-M3; a dual-tower MLP produces a query-conditioned hyperplane. No target/condition/deontic fields; rule texts never listed | "evaluation task instructions and scene descriptions are unseen during training, although C2 may contain rules also present in C1". This is an unseen scene and task, **not** an unseen rule, category, or household | Image → VLM caption D_t = V(I_t) used for the query; the planner also gets the image. No GT attributes; unknown attributes are not discussed | Stored rules × later (task, image). **Unit of selection = whole query Q_t = T_t ⊕ D_t (scene + task level)**. Each rule gets a binary applicable decision per query, **not per object or per candidate action** | Recall 37.48 / Prec 40.23 / F1 0.388 / EMR 2.67% vs BGE-M3 top-n_t 24.32 / 26.11 / 0.252 / 0.00% | B ○ (scene-level retrieval for a later request); C ✗ | General safety, not resident-arbitrary. No per-object applicability |
| same | **Safety Inspector** (LoRA, 3 Qwen VLMs) on 30 unseen scenes / 390 samples | §III-C, §IV-B, Table II | — | Inspector checks the **whole primitive plan** and reconstructs the full applicable set Ĝ_t | Unseen scenes | Image | Per plan | IDA 90.0–97.7%, CEM 35.3–67.1%, REC 97.8–98.1% | — | Plan-level PASS/FAIL. After 3 failures, `call_human_help()`. **No partial execution** ("Only plans receiving PASS are executed") |
| same | **Sequential test-time adaptation** over 50 scenes in 5 stages | §IV-C, Table III, §V | Validated Inspector feedback adds rules (ΔC_t) | — | — | — | — | Recall 0 → 20.5–46.2%; HVPR 20–50%, non-monotonic | — | The paper says the components are **not isolated** ("rather than isolating the stage-wise contribution", §IV-C/§V) |
| same | **Real robot**: two tasks (ball → brush pot near a bottle; tape → shelf near scissors) | §IV-D, Fig. 2 | — | — | — | Grounding DINO + SAM2 + CoPa (§III-E). Platform not named ("a physical robotic platform") | Single instruction | Qualitative "direct plan vs safety-aware plan". The safety-aware plan **inserts** extra Grasp/Put actions before the task | — | Adds actions rather than skipping forbidden objects |
| same | **Ablations?** | whole paper | — | — | — | — | — | Only the selection-method comparison against BGE-M3 top-n (Table I) and the qualitative direct-vs-safety-aware plan (Fig. 2). **No ablation** of planner with vs without selected constraints, full rule text vs selected, or structured vs raw rules | C-effect ✗ | — |

### 2.4 Ravichandran, Robey, Kumar, Pappas, Hassani, "Safety Guardrails for LLM-Enabled Robots" (RoboGuard), arXiv 2503.07885 (RA-L preprint, accepted Feb 2026) — verified TRUE

| Paper (URL) | Condition/demo | Evidence location | Rule origin | Rule representation | Novelty unit | Perception input | Instruction matching | Decision & evidence | Match A–D | Differences |
|---|---|---|---|---|---|---|---|---|---|---|
| RoboGuard [本文確認] https://arxiv.org/abs/2503.07885 | **Sim**: 7 harmful behaviours × 10 rephrasings × 3 randomised environments (small indoor, large indoor, outdoor); 3 rules ("respect privacy", "not physically harm anyone", "avoid potentially hazardous areas"); 10 safe tasks | §III-A/B, §IV, Table I (the text calls it "Table IV"), Fig. 2–3 | **Designer**, configured offline ("safety rules that are defined by a system designer during an offline configuration process"). §III-A also calls them "user-defined rules", so the wording is inconsistent, but in practice they are designer rules | Root-of-trust GPT-4o with CoT turns each NL rule into **per-entity LTL** over contextual propositions AP(M,F), e.g. `G(!goto(ground_21))`, `G(!inspect(knife_1))`, `G(goto(doorway_1) -> F(!goto(doorway_1)))` (App. D-A, Listing 5). The JSON lists (constraint, reasoning) per rule. The LLM does the decomposition | **Per-object grounding: yes.** Each perceived entity (person_1, knife_1, …) gets its own constraint. Maps are randomised by adding and removing regions/objects | Semantic graph (objects and regions). In simulation the graph comes from real robot maps with randomised elements (App. C-C); real robot below | Fixed rules × independent (possibly adversarial) prompts; grounded per entity in the world model | ASR with RoboGuard 0.2–5.2% (e.g. RoboPAIR 92.3% → 2.3%); safe tasks 100% → 100% | A ○ (lifted rule → instances); B ○ (rules vs later prompts) | **Action space has no manipulation**: goto, map_region, inspect, answer, clarify, replan (Listing 3). Rules are general safety |
| same | **Ablation: reasoning** | §IV-B, Table II, Fig. 3 | — | — | — | — | — | ASR 4.3% (full) → 12.8% (no CoT) → 25.7% (no CoT + temp 0.5); temperature alone has no effect | C-effect △: structured CoT grounding beats direct LTL, but this is not a deontic-decomposition ablation | — |
| same | **Ablation: rule set** (App. D-B) | App. D-B, Table A.II | Designer swaps rule sets: disaster response ("do not obstruct first responders", "avoid hazardous areas") vs construction ("respect privacy", "do not harm others") | same | **Different rule sets, but also different environments** (large indoor vs outdoor) and different tasks | Sim | — | Disaster: RoboPAIR 97.5% → 2.5%, safe tasks 100%. "Only allowing for one unsafe behavior" | D △: a rule-set swap, but not on the same scene or instruction, and only ASR / safe-task success are measured | Not a household swap; no per-object completion metric |
| same | **Real robot** Clearpath Jackal, 35 harmful + 10 safe | §IV-D, Table IV, Fig. 4, App. C-B | same 3 rules | same | Online world model grows; e.g. a person discovered mid-task produces `!goto(person)` | **Estimated**: ZED 2 RGB-D + Ouster LiDAR, SPINE mapping, GroundingDINO object nodes, GroundGrid regions | Per prompt | RoboPAIR ASR 100% → 0%; safe tasks 100% | A ○ (online grounding to newly perceived entities) | Navigation only |
| same | **Partial execution?** | §III-B Alg. 1, Thm III.2 | — | — | — | — | — | **Design claim only**: "maximally follows the LLM-generated plan … comply with the proposed plan if possible". Alg. 1 returns either φ_proposed (if accepted) or φ_safe. **No metric for retained or completed permitted sub-goals.** Listing 5 ends "Plan is unsafe." | D: not measured | `clarify()` exists in the planner API only for vague instructions; it is not a guard-level "undetermined" state |

---

## 3. Agreements / disagreements with the searchers and Codex (cell level)

### Tan 2019
| Item | S1 | Codex C1 | I1 (verified) |
|---|---|---|---|
| Authors | Tan, Brawer, Scassellati ✔ | "Xuan Tan, Fanjun Li, Brian Scassellati" ✘ | Zhi-Xuan Tan (v1: Zong Xuan Tan), Jake Brawer, Brian Scassellati |
| S1 ownership at start | "not given (obtained from the reprimand)" | "verify" | Paper is silent. The reprimand is the claim; other objects are predicted by KLR from position, colour, and last interaction. A secondary source says nothing was given in advance. **Agree with S1, with the caveat that this is not stated explicitly in the paper** |
| S3 ownership | given ✔ | — | "initially aware of the ownership status" ✔ |
| Language understanding | 未確認 ✔ | — | 未確認: no parsing or ASR described; video unplayable |
| Object perception | "perceptual heuristics (KLR)" ✔ | — | KLR is **ownership** prediction. Object sensing is **未確認** (no sensor described). S1's cell mixes the two |
| Table 1 condition | "100/50/25%" | — | Table says 1.00/0.50/0.25, but the text says "100%, 75%, or 25%". The inconsistency is in the paper; S1 followed the table |
| Codex "command-refusal demo reuses a stored norm on a later request" | — | ✔ | ✔ (S2). Note that the S2 norm is owner-specific, and the contrast is a change of ownership **fact**, not of rule |
| Codex "generalization of taught ownership norms across objects" | — | ✔ | ✔ S1 (via predicted ownership) and S3 (via given ownership) |

### TidyBot
| Item | S2 | Codex | I1 |
|---|---|---|---|
| Bibliography | IROS 2023 / AuRo 47(8) ✔ | IROS 2023, 9 authors ✔ | ✔ (AuRo 47(8):1087–1102) |
| Instance vs category | "no unseen-category split reported" ✔ | "inspect" | ✔. Unseen = distinct objects. v2 Tab. 1 also gives sorting criteria (Attribute in 27/96 scenarios), which S2 omitted. The robot applies rules per **category** (CLIP), never per instance |
| Same scene × different users (D) | "scenarios do not pair identical object sets" ✔ | "highest-priority D check" | ✔ Not reported. Real scenarios each have "its own set of 10 objects" |
| Real-robot perception | ViLD + CLIP, 95.5% vs 52.3% ✔ | — | ✔. Add: receptacle locations hard-coded, ArUco pose, forced classification |
| Primitive accuracy | not on benchmark; 100% on robot ✔ | — | ✔ |
| Numbers 91.2 / 78.5 / 83.7 / 45.6 / 85.0 / 92.5 / 95.5 / 96.2 | ✔ | — | ✔ all match |

### Wu 2611.18026
| Item | S3 | Codex | I1 |
|---|---|---|---|
| Rule source | not stated; manually annotated labels ✔ | from brief, low confidence | ✔ No user/household wording anywhere; examples are general hazards |
| Representation | raw text, BGE-M3, no fields ✔ | — | ✔ |
| Unit of selection | scene-level (Q_t), not per object or action ✔ | "check" | ✔ Additionally, the Inspector judges the whole plan |
| "Unseen" | unseen scenes and task instructions; C2 may overlap C1 ✔ | — | ✔ |
| Ablation | "No ablation without the Constraint Space, no raw-text comparison" ✔ | — | ✔. Only Table I (vs semantic top-n) and qualitative Fig. 2. §IV-C/§V admit the components are not isolated |
| Partial execution | (not stated) | — | **None**: only PASS plans run; otherwise `call_human_help()` |
| Robot platform | not given ✔ | — | ✔ |

### RoboGuard
| Item | S3 | I1 |
|---|---|---|
| Rule origin | Designer ✔ | ✔. The text says both "system designer" and "user-defined"; operationally designer |
| Per-entity LTL | ✔ (App. D-A) | ✔ Listing 5 |
| Perception | SPINE, GroundingDINO, GroundGrid ✔ | ✔ (App. C-B) |
| Numbers (92.3→2.3, 100→0, 4.3→12.8, 100% safe) | ✔ | ✔ |
| "mostly navigation/inspect" | understated | **Only** navigation, inspect, answer, clarify: no manipulation primitive at all (Listing 3) |
| "D partial (maximal plan retention)" | overstated | Retention is a design claim (Alg. 1 / Thm III.2), **not measured** |
| Missed by S3 | — | **App. D-B rule-set ablation**: designer swaps rule sets per deployment. This is the closest thing to "swap rules" in my set, but environment and tasks change with the rules |
| Venue | "RA-L 2026 per preprint label" | ✔ The PDF header reads "IEEE RA-L preprint version. Accepted February 2026"; the IEEE Xplore entry was not checked |

---

## 4. Forward-citation check (2024–2026): resident-taught prohibitions/obligations added to tidying, or rule swap on the same scene

**Tan 2019 (OpenAlex, 18 citing works).** Robot-relevant 2024–26 citers:
- ActOwL / "Toward ownership understanding of objects…" (2026)
- "Whose Is This?: Context-Aware Object Ownership Inference with Uncertainty-Guided Questioning" (2026)
- EgoAsk (2026; teaching personalised object knowledge through smart glasses)
- "Who Owns That? Evaluating Ownership Intuitions in LLMs" (2026)
- Oldenburg & Tan (2024, multi-agent rule induction)

Per their titles and abstracts, all of these concern ownership **inference** or teaching. **None adds resident-taught prohibitions or obligations to a tidying task, and none swaps rules on the same scene.** [要旨のみ]

**TidyBot (OpenAlex, 489 citing works screened by keyword).** The closest 2024–26 works, all [要旨のみ] unless noted:
- **APOLLO** (Collin & Ayub, RO-MAN 2026, arXiv 2606.17309; body partly read): personalised rearrangement with an explicit **abstention** outcome ("when objects should not be placed at all"). APOR has 10 organisational profiles × 3 users and measures abstention separately (pa_abs). Preferences are **inferred from demonstrations** per user-environment pair. The data are synthetic and LLM-generated, with no robot. Abstention means "irrelevant to the user's organisation", **not a taught prohibition**. This is relevant to D's "measure leave-alone separately", but it is not resident-taught and is not a same-scene swap.
- **LIBERO-PeRM** (arXiv 2610.22372): separates task completion from preference satisfaction, uses paired demonstrations with and without preferences, and tests conflicts. The preferences are motion, skill, and profile choices in simulation, not prohibitions over objects.
- **CarryOn** (2026): persistent user and scene preferences plus a contact-hazard shield (violation rate 52.6% → 6.1%). The safety side is generic hazard, not resident rules.
- **Coloring Between the Lines** (2025): personalisation inside the null space of safety CSP constraints; learns parameterised constraints online (feeding domain).
- **APRICOT** (2024): preference learning plus geometric feasibility for fridge arrangement.
- **In-situ Value-aligned HRI with Physical Constraints / ICLHF** (2025): preferences from instructions and feedback, balanced against physical constraints, on a household benchmark.
- **Multi-User Personalisation (MUP-QBAF)** (2025): positive and negative preferences of two users resolved by argumentation, in a frailty-assessment case study.
- **COMMET** (2025): human-induced conflicts, with user preferences summarised by GPT-4o.
- **AlignBot**, **PAHF** (2026), **MEMENTO** (2025), and **Inferring the Unspoken / PBP** (2026): preference memory and retrieval for later instructions. These bear on claim B (retrieval of stored user knowledge for a new instruction), but they concern preferences, not deontic rules.

**Outside the citation chains (web search):** **FLEX** (Lee, Dennler, Sucholutsky, Bobu; CoRL 2026, arXiv 2610.28893) [要旨のみ + MIT News]. A one-sentence prohibition such as "Don't spill on the laptop" is generalised by an LLM to a category (all electronics, fragile, flammable) and used as trajectory-avoidance features. This is the closest **2026** precedent for claim A with **resident-stated prohibitions generalised to untaught objects through an attribute** (fragile). It concerns trajectories rather than which objects to tidy, and per the news it applies within the same scene. The news story says simulation only, while arXiv mentions a real-world study (未確認). Reuse for a later independent request is 未確認. **Recommend that S2/S3 or the final round read the FLEX body.**

**Result:** no 2024–26 work was found that (a) has a resident teach prohibitions or obligations and then applies them to a later broad tidying request per object, or (b) swaps household rules on the same scene and instruction while scoring both forbidden-object avoidance and permitted-object completion. Coverage limits: Semantic Scholar was rate-limited; TidyBot citers were screened by keyword in the abstract (or title where no abstract exists); Google Scholar "cited by" was not directly accessible.

---

## 5. Implications for claims A–D (from the cross-read only)

- **A — 既出.** Tan S1 and S3 (instances via ownership), TidyBot (unseen real objects via CLIP categories, including the Attribute sorting criterion), RoboGuard (per-entity grounding from perception), and FLEX 2026 (stated prohibition → attribute category, abstract-level). What remains for CoGround is narrower: a resident-stated **prohibition or obligation** applied to unseen instances in **object manipulation** through a **perceived physical attribute**, with an explicit undetermined/hold state. Every paper here either forces a decision (TidyBot CLIP, Tan threshold) or works at scene level (Wu).
- **B — 既出 at scene level and in qualitative single-object form.** Tan S2 (stored norm → a later different-user command → refusal), Wu (stored rule library → later (task, image), scene-level, quantitative), and RoboGuard (fixed rules → independent prompts, per entity, navigation only). CoGround's per-object × per-candidate-action applicability under a broad request is **not** shown by Wu (scene-level) or Tan (single object). This is a 差分候補 with a small margin.
- **C — method 既出; effect 証拠不足.** Structured rules exist in Tan (Horn clauses) and RoboGuard (per-entity LTL). The nearest effect evidence is RoboGuard's CoT ablation (12.8% vs 4.3%) and TidyBot's summarisation vs examples-only (91.2% vs 78.5%). Neither is a deontic-decomposition ablation on held-out combinations. Wu runs no such ablation.
- **D — 差分候補 (evaluation design).** Nothing verified holds the scene and instruction fixed while swapping household rules and scoring both outcomes. Near-misses:
  - Tan S1 (partial completion while avoiding owned objects, one household)
  - Tan S2 (same command, different ownership fact, one object)
  - RoboGuard App. D-B (rule-set swap, but with different environments and tasks, ASR only)
  - TidyBot (different object sets per scenario)
  - APOLLO (abstention measured per profile, inferred and synthetic)

---

## 6. Still unverified

- Tan: video content (Google Photos link not playable here); the language-understanding method; the object-sensing method on Baxter; the exact initial ownership state in S1 (secondary source only).
- TidyBot: whether any benchmark scenarios reuse identical object lists under different preferences (I did not inspect the dataset files; the paper reports no such pairing).
- Wu: actual rule texts and their authorship (absent from v2 and there is no appendix); the v1 content was not compared.
- RoboGuard: the RA-L publication record on IEEE Xplore.
- FLEX: body not read (abstract + news only; the news and arXiv disagree on whether there is a real-world study).
- Citing works in §4 other than APOLLO: abstract level only.
