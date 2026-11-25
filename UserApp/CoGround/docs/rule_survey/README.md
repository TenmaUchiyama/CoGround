# 家庭ロボットが守るべきルール — 文献調査（2026-11-22）

家庭ロボットが家の中で守るべきルール（規範・マナー・プライバシー・安全・持ち主・片付けの好みなど）について、調べた論文を集めた。

- 全 130 本の一覧：[included.csv](included.csv)（種類・ルールの領域・年・会場・リンク付き）
- 検索に使ったスクリプトと検索語：[scripts/](scripts/)、[data/](data/)

---

## 1. 結論

### 1.1 論文の種類

| 種類 | 何をしている論文か | 本数 |
|---|---|---|
| **人に聞いた調査** | アンケート・インタビュー・ワークショップで、家庭ロボットにどうふるまってほしいかを集めた | 32 |
| **レビュー・分類・理論** | 規範やプライバシーの分類、ロボットが規範を持つための要件、ルールの書き方 | 21 |
| **データセット・ベンチマーク** | 具体的なルールや危険な場面を大量に集め、LLM や VLM を評価する | 37 |
| **手法** | ルールを学ぶ・守る・ぶつかったときに解決する方法 | 40 |

### 1.2 ルールの領域

| 領域 | 例 | 本数 |
|---|---|---|
| **マナー・社会規範** | 客がいるときに掃除機をかけない、人の前を横切らない、近づく距離・方向 | 41 |
| **プライバシー** | 入浴中は見ない、会話を記録しない・他人に漏らさない、入ってはいけない部屋 | 29 |
| **安全** | 火・刃物・薬・子ども・ペットに関する危険、水を電子機器の上で運ばない | 27 |
| **倫理・価値** | 本人の自律を尊重する、持ち主の命令と他人の利益がぶつかったとき | 27 |
| **片付け・置き場所の好み** | 物をどこにしまうか、人ごとの好み | 13 |
| **持ち主（所有）** | 「私のコップ」、他人の物を勝手に動かさない | 7 |
| **空間・立入** | 立入禁止の場所（バーチャルな境界線）、通路での譲り合い | 4 |
| **衛生** | 汚れた物に触れたあと、そのまま食器に触らない | 1 |

1 本が複数の領域にまたがるので、合計は 130 を超える。

### 1.3 分かったこと

- **「家庭のルールを人に聞いた調査」は、思ったより少ない。** 家庭用ロボットへの期待や受容の調査は多いが、「どんなルールを守るべきか」を正面から聞いた研究は少ない。中心になるのは次の論文。
  - **Li ほか, "Perceptions of Domestic Robots' Normative Behavior Across Cultures," AIES 2019**：家庭ロボットの規範について、中国と米国の人に、規範がぶつかる場面でどの行動を取るべきかを聞いた。対象の規範は、効率、社会のルールに従う、持ち主の命令に従う、人の行動に合わせる、正直さ、持ち主への忠誠。著者は、家庭ロボットの規範の優先順位を文化をまたいで調べた最初の調査だとしている（要旨で確認）。
  - **Koay / Dautenhahn ほかのロボットエチケット研究（HRI 2007、UH Robot House 2013）**：家で一緒に暮らすロボットに、どんな行動を期待するかを調べた。
  - **Pantofaru ほか, "Exploring the role of robots in home organization," HRI 2012**：家の片付けの実態を調べた。誰の物か、誰が片付けるかが絡むことを示した。
  - **"Understanding Social Appropriateness Perceptions in Secondary Users of Domestic Robots," HRI 2026**：持ち主ではない同居人や来客が、何を適切と思うかを調べた。
- **プライバシーは、調査の数が最も多い。** 家族・10 代・高齢者・複数人世帯それぞれで、ロボットに見られたくないもの、話されたくないことを調べている。「Rules for Robots」（2026）は、高齢者と一緒にプライバシーのルールを作った。
- **安全は、2024 年以降にベンチマークが急に増えた。** LLM・VLM を計画に使うロボットが、危険な指示をそのまま実行しないかを測る（SafeAgentBench、IS-Bench、SafetyALFRED、ASIMOV など）。ルールを文章で書いて守らせる「ロボット憲法」の考え方（Generating Robot Constitutions、RoboGuard）もここに入る。
- **持ち主と片付けの好みは、主に手法の研究。** 「私のコップ」を理解する所有の推定（That's Mine!、Whose Is This?、COOL）と、物の置き場所の好みの学習（TidyBot、Housekeep）が中心。
- **規範の理論は、Malle と Scheutz のグループが中心。** ロボットが規範を持つための要件（文脈に依存する、ぶつかる、例外がある、など）を整理している。「The seven troubles with norm-compliant robots」は、規範に従わせることの問題点（規範の偏り、誰の規範か、など）を挙げる。
- **SLEEC ルール（社会・法・倫理・共感・文化）** は、ルールを「When X then Y, unless Z」の形で書く方法として、形式手法の研究で使われている。
- **複数の住人の好みがぶつかる問題は、手法が少しあるだけ。** Multi-user Norm Consensus、Multi-User Personalisation、Modularity as Accommodation（家族で 1 台のロボットを共有する設計）がある。

---

## 2. 調査方法

前回の失敗の種類の調査（[../failure_survey/](../failure_survey/README.md)）と同じ手順で行った。

| 段階 | やったこと | 件数 |
|---|---|---|
| ① 出発点 | 中心的な論文 14 本を選んだ（社会規範のレビュー、所有の規範、規範の要件、ロボット憲法、Housekeep、TidyBot、SafeAgentBench、プライバシーの分類、EgoNormia など。[seed_titles.json](data/seed_titles.json)） | 14 |
| ② 引用をたどる（1 段目） | 14 本の参考文献と被引用を OpenAlex から取得 | 1,968 |
| ③ キーワード検索 | OpenAlex で 30 個の検索語、各上位 200 件（[grid.json](data/grid.json)） | 4,133 |
| ④ arXiv 検索 | arXiv API で 16 + 15 個の検索語（[q_arxiv.json](data/q_arxiv.json)、[q_arxiv2.json](data/q_arxiv2.json)） | 149 + 223 |
| ⑤ 引用をたどる（2 段目） | ①〜④で見つかった中心論文 8 本で②を繰り返した（ロボットエチケット、家の片付け、Safety Chip、命令の拒否、AGENTSAFE など） | 1,455 |
| 重複を除いた合計 | タイトルで重複を除いた | **約 7,000** |
| ⑥ 機械的な絞り込み | タイトル・要旨に「ロボット系の語」「ルール系の語」「家庭系の語」をすべて含むもの。家庭の語を含まない規範研究を拾うため、「norm」「etiquette」「ownership」などの強い語だけの条件も別に使った | 919 + 319 |
| ⑦ タイトルで判定 | 全件のタイトルを読んで判定 | → 約 150 |
| ⑧ 要旨で判定 | 要旨を読んで採否を決めた | **130 本採用** |
| ⑨ Web 検索で確認 | 既知の論文が漏れていないかを確認 | RoboGuard などを確認 |

### 2.1 含めたもの・除いたもの

- **含めた**：家庭（または家庭を含む日常の場）で、ロボットや身体を持つエージェントが守るべきルール・規範・好み・制約を、調べた・分類した・集めた・守らせた研究。
- **除いた**：
  - 受容・外見の好み・使う意図だけの調査（「どんな見た目がよいか」など）。
  - 介護ロボットの倫理の一般論のうち、具体的なルールに触れないもの。代表として Sharkey & Sharkey 2010（Granny and the robots）だけを残した。
  - 社会的ナビゲーション（人混みの中の移動）。家庭以外の場が中心のため。
  - サイバーセキュリティ・データ保護の技術（暗号化・連合学習など）のうち、ロボットのふるまいのルールに関わらないもの。

### 2.2 漏れの確認

- **飽和の確認**：2 段目の引用（⑤）で新しく判定対象になった 108 本のうち、新しく採用したのは 5 本ほどだった。大半は、高齢者の受容や期待の調査で、ルールそのものではなかった。
- **Web 検索**：「家庭ロボットが守るべきルール」で検索すると、最も近いものとして Li ほか 2019 が挙がった。今回の一覧にすでに入っていた。
- **OpenAlex に出てこなかった論文**：RoboGuard（Safety Guardrails for LLM-Enabled Robots、RA-L 2026）は、OpenAlex のタイトル検索では見つからず、Web 検索で確認した。最終的には検索プールに入っていた。

### 2.3 限界

- **データベース**：OpenAlex と arXiv だけ。ACM DL・IEEE Xplore・Scopus は直接検索していない。各検索語は上位 200 件だけを見た。
- **判定者は 1 人**：タイトル・要旨の判定は私 1 人。
- **本文は読んでいない**：今回は全件、要旨までの確認。各論文が挙げているルールの中身（たとえば Li ほか 2019 の規範の優先順位）は、本文で確認する必要がある。
- **言語**：英語だけ。日本語の論文は探していない。
- **年**：2026 年の新しいプレプリントが多い。査読を経ていないものを含む。

---

## 3. 論文の一覧

★ は、「家庭のルールを調べた」という意味で特に中心になる論文。リンクは [included.csv](included.csv) にある。

### 3.1 人に聞いた調査（32 本）

**マナー・社会規範**
- ★ Li ほか, Perceptions of Domestic Robots' Normative Behavior Across Cultures, AIES 2019
- ★ Koay ほか, Robotic etiquette: results from user studies involving a fetch and carry task, HRI 2007
- ★ Exploring Robot Etiquette: Refining a HRI Home Companion Scenario Based on Feedback from Two Artists Who Lived with Robots in the UH Robot House, 2013
- Form, Function and Etiquette – Potential Users' Perspectives on Social Domestic Robots, 2017
- Social Roles and Baseline Proxemic Preferences for a Domestic Service Robot, IJSR 2014
- Dautenhahn ほか, What is a robot companion – friend, assistant or butler?, IROS 2005
- Ray ほか, What do people expect from robots?, IROS 2008
- ★ Understanding Social Appropriateness Perceptions in Secondary Users of Domestic Robots, HRI 2026
- Investigating family perceptions and design preferences for an in-home robot, 2020
- ★ Modularity as Accommodation: How Families Negotiate One Shared Domestic Robot in Co-Design, 2026
- A Robot Jumping the Queue: Expectations About Politeness and Power During Conflicts, CHI 2024
- Step Aside! VR-Based Evaluation of Adaptive Robot Conflict Resolution Strategies for Domestic Service Robots, IJSR 2022
- Examining the Impact of Robot Norm Violations on Participants' Trust, Discomfort, Behaviour and Physiological Responses, THRI 2025
- Instruct or Evaluate: How People Choose to Teach Norms to Social Robots, HRI 2022

**片付け・持ち主**
- ★ Pantofaru ほか, Exploring the role of robots in home organization, HRI 2012
- Robots in the Home: Qualitative and Quantitative Insights into Kitchen Organization, HRI 2015

**自律・価値**
- Preserving Sense of Agency: User Preferences for Robot Autonomy and User Control across Household Tasks, 2025
- Dignity, Autonomy, and Style of Company: Dimensions Older Adults Consider for Robot Companions, 2021
- Older Adults' Task Preferences for Robot Assistance in the Home, 2023
- Preferences and Expectations for Home Robot Tasks: Comparison According to Age and Household Type in Republic of Korea, 2024
- Users' Perspectives on Value Awareness in Social Robots, 2023

**プライバシー**
- ★ Rules for Robots: Co-Designing Privacy-Conscious Social Robots with Older Adults, 2026
- ★ Our business, not the robot's: family conversations about privacy with social robots in the home, 2024
- ★ Snitches Get Unplugged: Adolescents' Privacy Concerns about Robots in the Home are Relationally Situated, HRI 2024
- ★ "It's like a pet...but my pet doesn't collect data about me": Multi-person Households' Privacy Design Preferences for Household Robots, 2026
- "Is it always watching? Is it always listening?" Exploring Contextual Privacy and Security Concerns Toward Domestic Social Robots, 2025
- Surveying Adult Perceptions of Privacy and Attitudes towards Social Robots in the Home, HRI 2024
- "I still need my privacy": comfort and privacy preferences of German-speaking older adults (mobile assistant robots), 2021
- Navigating privacy in smart homes: how robot roles, communication styles, and contextual scenarios shape user perceptions, 2026
- Enhancing Privacy and Trust in Domestic Robots Through Real-Time Feedback and Intervention Interfaces, 2025
- Designing for In-Home Long-Term Family-Robot Interactions: Family Preferences, Connection-Making, and Privacy, 2023
- Responsible domestic robotics: exploring ethical implications of robots in the home, 2019

### 3.2 レビュー・分類・理論（21 本）

**社会規範**
- ★ The Role of Social Norms in Human–Robot Interaction: A Systematic Review, THRI 2025
- Tian & Oviatt, A Taxonomy of Social Errors in Human-Robot Interaction, THRI 2021
- ★ Malle ほか, Requirements for an Artificial Agent with Norm Competence, AIES 2019
- What Properties of Norms can we Implement in Robots?, RO-MAN 2023
- The seven troubles with norm-compliant robots, 2023
- Making Place for Social Norms in the Design of Human-Robot Interaction, 2016
- Norms, Institutions, and Robots, 2018
- To Help or Not to Help?: An Expanded Framework for Deciding Socially Appropriate Robot Assistance, THRI 2026

**プライバシー**
- ★ Rueben ほか, A Taxonomy of Privacy Constructs for Privacy-Sensitive Robotics, 2017
- Themes and Research Directions in Privacy-Sensitive Robotics, 2018
- Privacy-Sensitive Robotics: Perceptions, Measures, and Metrics, HRI 2025
- Privacy at Home: An Inquiry into Sensors and Robots for the Stay at Home Elderly, 2018
- Towards Designing Privacy-Compliant Social Robots for Use in Private Households, RO-MAN 2020
- Position: Robot Privacy as Embodied Boundary Work, 2026
- Design Guidelines for Privacy-Aware Interactions in Home Robots Based on Engagement, 2025
- More work for Roomba? Domestic robots, housework and the production of privacy, 2022
- A Spotlight on Security and Privacy Risks with Future Household Robots, 2009

**安全・倫理・ルールの書き方**
- The Safety of Domestic Robotics: A Survey of Various Safety-Related Publications, 2014
- Sharkey & Sharkey, Granny and the robots: ethical issues in robot care for the elderly, 2010
- ★ Specification and Validation of Normative Rules for Autonomous Agents（SLEEC ルール）, FASE 2023
- Toolkit for specification, validation and verification of SLEEC requirements for autonomous agents, 2024

### 3.3 データセット・ベンチマーク（37 本）

**安全**
- ★ Generating Robot Constitutions & Benchmarks for Semantic Safety（ASIMOV）, 2025
- ★ SafeAgentBench, 2024 / AGENTSAFE, 2025 / IS-Bench, 2025 / EARBench, 2024
- SafetyALFRED, 2026 / HomeSafeBench, 2025 / HomeSafe-Bench, 2026 / Hazards in Daily Life?, NAACL 2025
- SafeRelBench / EgoSafetyBench / CAPSafe / MANIGUARD / ROBOSHACKLES / HoRoTrust / OopsieVerse, 2026
- VestaBench, EMNLP 2025 / Can AI Perceive Physical Danger and Intervene?, 2025
- DESPITE（Using large language models for embodied planning introduces systematic safety risks）, 2026：物理的な危険と規範上の危険の両方を含む

**衛生**
- HygieneRoboBench, 2026

**社会規範**
- ★ NormAct: Benchmarking Embodied Agents' Proactive Compliance with Unspoken Social Norms, 2026
- ★ EgoNormia: Benchmarking Physical-Social Norm Understanding, ACL Findings 2025
- ★ Mind Your Manners!（MANNERS-DB：家庭ロボットの行動の適切さのデータセット）, 2022
- NormBank: A Knowledge Bank of Situational Social Norms, ACL 2023
- Reading Books is Great, But Not if You Are Driving!（文脈で変わる常識的な規範）, 2023
- Where Norms and References Collide: Evaluating LLMs on Normative Reasoning, AAAI 2026

**価値**
- ★ RobotValues: Evaluating Household Robots When Human Values Conflict, 2026
- InterSocialBench, 2026 / SciFi-Benchmark, 2025

**プライバシー**
- EAPrivacy（Measuring Physical-World Privacy Awareness of LLMs）, 2026
- How Far Are VLMs from Privacy Awareness in the Physical World?, 2026
- Benchmarking LLM Privacy Recognition for Social Robot Decision Making, 2025
- A Picture is Worth a Thousand Risks（室内画像からプライバシーの危険を推定）, 2026

**片付け・持ち主**
- ★ Housekeep: Tidying Virtual Households using Commonsense Reasoning, ECCV 2022
- PersONAL（持ち主を含む個人化の課題）, 2025
- Personalized Robotic Object Rearrangement from Scene Context, RO-MAN 2025
- Inferring the Unspoken: Aligning Embodied Agents with Implicit Preferences, EMNLP 2026

### 3.4 手法（40 本）

**持ち主**
- ★ Tan, Brawer & Scassellati, That's Mine! Learning Ownership Relations and Norms for Robots, AAAI 2019
- An Interactive Learning Framework for Item Ownership Relationship in Service Robots, 2023
- ActOwL（Toward ownership understanding of objects）, 2026 / Whose Is This?, 2026 / COOL, 2026

**片付け・置き場所**
- ★ TidyBot, IROS 2023 / Robot, organize my shelves!, ICRA 2015 / Organizing objects by predicting user preferences through collaborative filtering, 2016
- My House, My Rules（NeatNet）, 2021 / LLM-Personalize, 2024 / APRICOT, 2024
- Explaining Why Things Go Where They Go, HRI 2026

**社会規範の学習・推論**
- Learning behavioral norms in uncertain and changing contexts, 2017
- What Am I Allowed to Do Here?: Online Learning of Context-Specific Norms by Pepper, 2020
- A General Methodology for Teaching Norms to Social Robots, RO-MAN 2020
- Explicit representation of social norms for social robots, IROS 2015
- A Computational Framework for Integrating Task Planning and Norm Aware Reasoning, RO-MAN 2018
- GRACE（客がいるときに掃除機をかけるか、などを LLM と人の説明で判断）, ICRA 2025
- Federated Learning of Socially Appropriate Agent Behaviours in Simulated Home Environments, 2024
- Mind the Context: Continual Learning of Socially Appropriate Robot Actions, 2026
- Should I Help?: A Skill-Based Framework, RO-MAN 2024

**規範がぶつかったとき**
- Kasenberg & Scheutz, Norm Conflict Resolution in Stochastic Domains, AAAI 2018 / Inverse Norm Conflict Resolution, AIES 2018 / Inferring and Obeying Norms in Temporal Logic, HRI 2018
- Multi-user Norm Consensus, AAMAS 2024
- Multi-User Personalisation: Resolving Preference Conflicts Using Gradual Argumentation, 2025
- Personalization of Basic and Moral Values Guiding LLM-Controlled Assistant Robots, 2026

**倫理ルール**
- Care Robots Learning Rules of Ethical Behavior Under the Supervision of an Ethical Teacher, 2022
- Implementing Pro-social Rule Bending in an Elder-care Robot Environment, 2023
- Operationalising Normative Rules in Autonomous Robotic Systems Through Context-Oriented Programming（SLEEC）, IJCAI 2026
- Briggs & Scheutz, "Sorry, I Can't Do That": Developing Mechanisms to Appropriately Reject Directives, AAAI 2015

**安全の制約**
- ★ Plug in the Safety Chip: Enforcing Constraints for LLM-driven Robot Agents, ICRA 2024
- ★ RoboGuard（Safety Guardrails for LLM-Enabled Robots）, RA-L 2026：「プライバシーを尊重する」「危険な場所に近づかない」などのルールを環境に結び付けて守らせる
- Semantically Safe Robot Manipulation（水の入ったコップをノート PC の上で運ばない）, RA-L 2025
- Updating Robot Safety Representations Online From Natural Language Feedback, ICRA 2025
- Building Trustworthy Household Robots through Open-World Safety, 2026
- Application of modified Asimov's laws to the agent of home service robot, 2018

**空間・プライバシー**
- Interactive Restriction of a Mobile Robot's Workspace in a Smart Home Environment（バーチャルな境界線）, 2019
- Detection of privacy-sensitive situations for social robots in smart homes, 2016
- Privacy-aware LLM-assisted Task Planning for Home Robots, 2026

---

## 4. CoGround への示唆

- **ルールの「内容」の語彙づくりに使える論文。** CoGround のルールの内容は「ロボットが変えられる状態」から作る方針になっている。具体的なルールの例を多く含むのは、ASIMOV（ロボット憲法）、NormAct、MANNERS-DB、SafeAgentBench、RobotValues。これらに出てくるルールを内容の語彙と照らし合わせると、抜けている語彙が分かる。
- **「対象」と属性の照合に直接関わるのは、持ち主の研究。** 「他人の物は動かさない」のように、対象を持ち主で決めるルールは多い。持ち主は画像から分からない属性なので、住人が登録するという CoGround の方針は、That's Mine! や Whose Is This?（持ち主は見ただけでは分からず、聞く必要がある）と一致する。
- **「条件」の部分は、規範の理論が裏付けになる。** Malle ほかは、規範が文脈に依存し、例外があることを要件に挙げている。SLEEC ルールの「unless」も同じ考え方。
- **家庭のルールを住人に聞いた調査は少ない。** 家庭でどんなルールが実際に必要かを、住人から集めた研究は Li ほか 2019 など少数。CoGround でルールを集める実験をすれば、それ自体が新しいデータになる可能性がある。

## 5. 次にやること

- 中心論文（★）の本文で、挙げているルールの中身を確認する。ACM・Springer の論文は自動で取得できないので、Zotero に入れてもらう必要がある。
- 日本語の論文（家庭用ロボットのルール・マナー）を別に探す。
