You are an independent critical reviewer (a different model family from the other agents). You have NO tools: do not attempt shell, file, or web tools — answer only from your own knowledge in your final message. Be honest about uncertainty: for every paper give title, authors, year, venue as best you recall, and a confidence (high/med/low). Never fabricate; if unsure of a detail, say so. Your list will be verified by other agents against original sources.

Context: the review spec and the shared brief are appended below.

Tasks:
1. For each claim A, B, C, D, list the 5–8 prior works you believe most strongly refute or overlap it (robotics, HRI, AI planning, NLP/LLM agents, normative multi-agent systems, deontic logic, embodied AI benchmarks). Include works under different names (social norms, deontic constraints, safety constraints, LTL specifications, personalized preferences, contextual integrity, instructable agents, interactive task learning, constitution for robots).
2. For claim C specifically: works that decompose rules/norms into target / condition / deontic action (e.g., normative MAS norm representations, ODRL, deontic logic frames, institutional grammar "ADICO"), and any that measured the effect of decomposition on generalization.
3. For claim D: any evaluation that varies house rules while keeping scene and instruction fixed.
4. Name concepts from other fields that are the same idea under another name (e.g., Institutional Grammar ADICO = Attribute, Deontic, aIm, Conditions, Or-else; access-control policies; ABAC attribute-based access control; business rules engines; defeasible deontic logic) and judge whether CoGround's R = (N, S, T, C=(W, φ)) is just an instance.
5. Give your verdict per claim (already done / difference candidate / insufficient evidence) and the single contribution sentence you think is defensible, plus the condition under which it should be retracted.
Output in English, structured markdown.

===== SPEC =====
# 家庭内ルールを用いた物体操作の新規性調査計画

作成日 2026年11月19日。以下は予備調査を踏まえた本調査の実行仕様である。

## 1. 調査で判定すること

想定する場面は、人が家庭固有のルールを一度教え、後から「机の上を片づけて」と依頼する場面である。ロボットは新しく出会った物体について、どのルールがどの行動に適用されるかを判断する。最初の調査ではルールの入力媒体を限定しない。実験用画像に書かれた説明とロボット自身が観測できる情報は区別する。

| 検証する主張 | 直接の反証として探すもの |
|---|---|
| A. 教えられたルールを別の物体に適用する | 新しい個体を認識し、以前のルールで操作・配置を決めた実証 |
| B. 保存したルールと後続指示を照合する | ルールと独立の依頼を受け、関連ルールを選択して対象物の行動を変えた実証 |
| C. ルールを対象・適用条件・規範的な指示に分けることが、未教示の組み合わせでの判断に寄与する | 同等の分解と再利用を示した手法、および分解を使わない条件と比べて効果を測った評価。手法の先取性と効果の実証は個別に判定する |
| D. 家庭固有ルールの違いを反映しながら、包括的な依頼の実行可能部分を完遂する | 同一場面・同一指示で家庭ルールを変え、禁止対象の回避と許容対象の完遂をともに測った比較 |

## 2. 探索の起点

- Tan et al. は所有規範を学ぶBaxterが、片付け時の訂正を別の物体に一般化し、所有規範に反する後続の依頼を拒否する例を示した。実機デモの各シナリオでどの所有情報が初めから与えられたかを区別して読む。[That's Mine! Learning Ownership Relations and Norms for Robots, Video demonstration・図1–2](https://scazlab.yale.edu/sites/default/files/files/Xuan_AAAI19.pdf)
- TidyBotは少数の例から利用者の片付けルールを一般化し、新しい物体に対して収納先に加えて置く・投げ入れるといった操作も選ぶ。固定の片付け課題で獲得した選好を、独立した依頼における禁止・義務の判断と比較する。[TidyBot, §III–IV](https://pixl.cs.princeton.edu/gfx/pubs/Wu_2023_TPR/tidybot_IROS23.pdf)
- Safety Chipは自然言語の制約を時相論理に変換し、計画中の行動を検査する。実機で与えた物体状態、制約の翻訳を検証した人の役割、課題と制約が矛盾する試験を確認する。[Plug in the Safety Chip](https://h2r.cs.brown.edu/wp-content/uploads/yang24.pdf)
- Wu et al. の2026年11月公開のプレプリントは、保存済みの文章ルールから、画像とタスク指示の組に適用可能な安全制約を選び、計画を検査・修正する。一般安全と住人が任意に決めるルールの違い、未見とする単位、規則の明示的な分解の有無を調べる。[A Generalizable Approach to Safety-Aware Robotic Behavior Planning with an Explicit Constraint Space](https://arxiv.org/abs/2611.18026)

## 3. 並列調査の担当

統合役1名と探索役3名で実施する。探索役は独立に検索し、自分の担当分野から本提案を最も強く反証する研究を提出する。

| 担当 | 調査範囲 | 検索式の出発点 |
|---|---|---|
| 1. HRI・規範学習 | 人が教える許可・禁止・所有・家庭固有の方針、教示後の別指示、ロボットによる部分実行や指示の拒否 | robot AND (“norm learning” OR “action permission” OR “instructable agent”) AND (object OR instruction) |
| 2. 知覚・家庭ロボット | 外見、材質、状態からの適用判断、片付け選好、未見個体・カテゴリへの一般化。ラベルを知覚入力とする実装なら環境中の文字・記号の利用も含める | robot AND (tidying OR manipulation) AND (“user preferences” OR “personalized rules” OR “open-vocabulary grounding”) |
| 3. 記号推論・タスク計画 | 変数を持つルールへの物体の割当て、規範・例外・優先度、自然言語制約を用いた行動選択。PDDL、ASP、時相論理、LLM/VLMも対象 | robot AND (“norm-aware planning” OR “instruction grounding” OR “constraint applicability” OR “semantic constraints”) AND (object OR task) |
| 統合役 | 各担当の上位候補を横断比較し、異分野の別名と複数の既存手法の単純な組み合わせでも同じ結果が出る可能性を調べる | 上位論文の引用元・被引用、同著者の後続研究、日本語の「家庭ロボット 規範 教示 物体操作」等 |

年代の下限を設けず、調査日までのHRI、RO-MAN、ICRA、IROS、RSS、CoRL、AAAI、AAMAS、ICAPSなどを対象にする。Google Scholar・OpenAlexで横断検索し、IEEE Xplore、ACM DL、会議録・著者公開版、arXivで原文を確認する。検索日、データベース、検索式、採否理由を記録する。直接の競合には前方・後方引用をたどり、別の担当が最も近い文献を再読する。追加探索で比較表の判定が動かなくなった範囲と、本文未入手などで残った範囲を明記する。

## 4. 全員が提出する比較表

1行を「論文 × 実験条件」とする。各行にURL、根拠となる節・図表、手法への入力、実際に測った出力、今回との一致点と差分を書く。同一論文の別々のデモは、すべてを同時に達成した単一の実証として扱わない。

- **ルールの由来と表現**　住人の明示教示、例からの選好推定、設計者による登録、常識知識。原文のまま保持するか、対象・適用条件・行為と禁止／許可／義務に分けるか。誰が分解するか。
- **新しさの単位**　教示に出ていない個体、教示に出ていないカテゴリ、既知の属性と行為の新しい組み合わせ、未見の家庭・場面を分ける。基盤モデルの事前学習で見たかどうかとは区別する。
- **認識の入力**　物体名・属性の正解を入力したか、画像から推定したか、人の教示で知ったか。不明な属性をどう扱うか。
- **指示との照合**　単発の制約付き指示か、以前のルールを別の依頼で再利用するか。場面全体に関連するルールの検索と、個々の物体・候補行動への適用判定を分ける。
- **判断と証拠**　操作選択、動作の禁止、部分実行、必要時の質問のどれを実証したか。構想、実装、定性デモ、対照付き定量評価を区別する。記述が見つからないセルは「未確認」とする。

## 5. 差分が残った場合の最小比較実験

1. **家庭ルールだけを変える。** 同じ机・同じ物体・同じ「片づけて」で、家庭Aは「星印のカップはそのまま」、家庭Bは「丸印のカップはそのまま」と教える。これは新たに提案するテストで、星・丸は素材や危険性と相関しないようにする。一般常識で正解しやすい「割れ物」条件も別に残す。
2. **新しい組み合わせを試す。** 教示と評価で個体を分ける。対象・条件・行為の各要素は既知でも、その組み合わせを教示していない試行を設ける。条件の該当・非該当の双方を入れる。別カテゴリへの転移を主張するときはカテゴリ単位でも分割する。
3. **分解の効果を切り分ける。** 同じ知覚入力、ルール、候補行動を使い、ルール全文を直接読む方式、関連ルールの原文を検索して読む方式、分解して対象と候補行動に照合する方式を比べる。属性の正解を与える条件と画像認識を含む条件を設け、認識誤りと照合誤りを分ける。
4. **成功条件を先に決める。** 主要指標は「禁止対象に一度も触れず、許可された対象をすべて正しく片づけた試行の割合」。内訳として禁止違反率、許可対象の完遂率、家庭ルールを入れ替えた対で両方正解した割合を報告する。照合を貢献とする場合は、物体・候補行動ごとの適用規則の適合率と再現率も取る。

## 6. 判定と成果物

- 同じ入出力と同じ条件で先行例があれば、その機能の初出という主張を取り下げる。先行手法が同等でも、これまで測られていない誤り・一般化・人の教示負担を測れれば、評価またはHRI上の貢献として別に判定する。
- 差が実装の組み合わせに留まる場合は、最も近い先行方式と上記の分解を外した方式を比較する。未見の組み合わせで効果があれば、効果が出た条件を記した限定的な手法主張を候補にする。差が出なければ分解の有効性は主張しない。
- 最終成果物は、検索記録、出典と節番号付き比較表、最も強い反例3件、主張ごとの「既出／差分候補／証拠不足」、および**論文に書ける貢献文1文と、その文を撤回すべき条件**とする。


===== BRIEF =====
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
