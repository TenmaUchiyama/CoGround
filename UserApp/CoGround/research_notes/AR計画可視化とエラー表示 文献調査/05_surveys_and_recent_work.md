# 05 サーベイ・タクソノミーと 2024–2026 年の最新研究（AR/MR によるロボットの意図・計画・状態の伝達）

調査日: 2026-11-22。位置づけ対象: 自然言語指示 → 家庭内片付けタスクの計画 → AR で事後環境をプレビュー（Before/After）→ エラー・ルール違反のある物体/ステップをマーキングするシステム。

**調査方法と検証レベル（読み手への注意）**

- 前方引用は Semantic Scholar Graph API（`/paper/{id}/citations`）で取得した。取得日時点の件数: Suzuki 2022 = 310 件（うち 2024 年以降 247）、Walker 2023 = 159（128）、Pascher 2023 = 104（87）、PRogramAR = 30、MARCER = 16、RoboVisAR = 12、ImageInThat = 7、X-OOHRI = 4。重複除去後 446 件の題目を全件見て、言語指示・計画プレビュー・エラー可視化・家庭タスク・信頼評価に関わるものを抜粋した。
- OpenAlex API は共有 IP の無料枠が枯渇して使えず（HTTP 429）、arXiv API も 429 だった。したがって「引用グラフ外」の新着は Web 検索でしか補えていない（Gaps 参照）。
- 検証ラベル: **[S2+abs]** = Semantic Scholar で書誌とアブストラクトを確認。**[S2]** = 書誌のみ確認（アブストラクト未取得。内容は題目からの推定）。**[全文]** = arXiv/ar5iv/出版社ページの本文を取得して確認。**[記憶]** = 自分の記憶に基づく記述で今回未検証。
- **[既]** = 既存レビュー `master_db_raw.csv`（約 110 本）に収録済み。**[新]** = 未収録。
- S2 の著者名はイニシャル化・ハイフン化されることがある（例: "Y. Sugiura"）。本ノートでは一部のイニシャルを記憶に基づいてフルネームに展開し、ハイフンを除いた（例: "D. Tsetserukou" → "Dzmitry Tsetserukou"）。展開した名は未検証なので、引用時は DOI 先で正式表記を確認のこと。
- KQ4 に書いた所属（京大 神田研、阪大、東大 鳴海研、立命館 谷口研、中部大・慶應 など）は著者名からの記憶に基づく推定で、今回は確認していない。
- 2026 年後半の arXiv 番号（26xx.xxxxx）や DOI は S2 API の返り値をそのまま記載した。個別ページの閲覧までは行っていない。

---

## KQ1. サーベイ／タクソノミー各論と、「計画プレビュー」「エラー表示」を分類するのに有用な設計次元

### Takeaway

AR×ロボットの中核 3 サーベイ（Suzuki 2022 / Walker 2023 / Pascher 2023）は、それぞれ「何を・どこに・何のために」を別の切り口で体系化しており、本システムの 2 機能は Walker の **Task Comprehension VDE（Spatial Previews / Alteration Previews / Task Status）**、Suzuki の **Plan and Activity 情報 × Virtual Replica and Ghost Effects**、Pascher の **Motion intent の World Actions / State intent × On-World または Head-Attached** に写像できる。一方で、どのタクソノミーにも「計画の妥当性（エラー・ルール違反）を事前にマークする」専用カテゴリは無く、失敗伝達は Honig & Oron-Gilad の RF-HIP モデルなど非 AR の文献側にある。

### Cited Findings

#### A-1. AR/VR×ロボットのサーベイ・タクソノミー

- **Suzuki, Karim, Xia, Hedayati, Marquardt. "Augmented Reality and Robotics: A Survey and Taxonomy for AR-enhanced Human-Robot Interaction and Robotic Interfaces." CHI 2022.** [既][全文] 460 本を調査し 8 次元で整理。(1) Approaches to augmenting reality: ハードウェア配置 On-Body / On-Environment / On-Robot、拡張対象 Augment Robots / Augment Surroundings。(2) ロボット特性: Form Factor、Relationship（1:1, 1:m, n:1, n:m）、Scale、Proximity（co-located〜remote）。(3) Purposes and benefits: Facilitate Programming / Support Real-time Control and Navigation / Improve Safety / Communicate Intent / Increase the Expressiveness。(4) 提示情報: Robot's Internal Information / External Information about the Environment / **Plan and Activity** / Supplemental Content。(5) 視覚デザイン: UIs and Widgets（Menus, Information Panels, **Labels and Annotations**, Controls and Handles, Monitors and Displays）、Spatial References and Visualizations（Points and Locations, Paths and Trajectories, Areas and Boundaries, Other）、Embedded Visual Effects（Anthropomorphic, **Virtual Replica and Ghost Effects**, Texture Mapping）。(6) インタラクション: 対話性 4 段階（No Interaction〜Explicit and Direct Physical Manipulation）とモダリティ 7 種（Tangible, Touch, Pointer and Controller, Spatial Gesture, Gaze, Voice, Proximity）。(7) 応用領域。(8) 評価: Demonstration / Technical / User Evaluation。— [arXiv 2203.03254](https://arxiv.org/abs/2203.03254)、[ar5iv 本文](https://ar5iv.labs.arxiv.org/html/2203.03254)、[DOI](https://doi.org/10.1145/3491102.3517719)
- **Walker, Phung, Chakraborti, Williams, Szafir. "Virtual, Augmented, and Mixed Reality for Human-Robot Interaction: A Survey and Virtual Design Element Taxonomy." ACM THRI 2023.** [既][全文] 30 年分 175 本（99 の会議・誌）を調査し、Virtual Design Element（VDE）を 4 大分類。(1) Virtual Entities: Robots（Visualization Robots, Simulated Robots, Robot Digital Twins）、Control Objects（Panels & Buttons, Controllers）、Environmental（Simulated Agents/Objects/Environments, **Object Digital Twins**, Environment Digital Twins）。(2) Virtual Alterations: Superficial（Cosmetic, Special Effect）、Morphological（Body Extensions, **Body Diminishments**, Form Transformations）。(3) Robot Status Visualizations: Internal（Internal Reading, Internal Readiness）、External（Robot Pose, Robot Location）。(4) Robot Comprehension Visualizations: Environment（センサ視野・センサ値・空間領域 7 種）、Entity（**Entity Labels, Entity Attributes**, Entity Locations, Entity Appearances）、Task（Headings, Waypoints, Callouts, **Spatial Previews**, Trajectories, **Alteration Previews**, Command Options, **Task Status**, Task Instructions）。Spatial Previews は環境に固定した可視化でロボット・物体など実体の将来姿勢を示すもの、Alteration Previews はロボットが物体に加える恒久的変更を事前に示し実行前に検証させるもの。— [arXiv 2202.11249](https://arxiv.org/abs/2202.11249)、[ar5iv 本文](https://ar5iv.labs.arxiv.org/html/2202.11249)、[DOI](https://doi.org/10.1145/3597623)
- **Pascher, Gruenefeld, Schneegass, Gerken. "How to Communicate Robot Motion Intent: A Scoping Review." CHI 2023.** [新][全文] 最終コーパス 77 本。意図伝達モデルの 3 次元: **Intent type**（Motion: Robot Self-Actions / World Actions、Attention: Robot-Focused / World-Focused、State: Robot Self-Perception / Robot World Perception、Instruction: Robot-Centered / World-Centered）、**Intent information**（Spatial: Local, Directional, Description, Symbol, Signal、Temporal: Discrete / Continuous）、**Intent location**（On-Robot: Robot-Only / Robot-Attached、On-World、On-Human: Head-Attached / Hand-Held）。加えてロボット種別（Robotic Arm, Humanoid, Mobile Robot）、人の役割（Collaborator, Observer, Coworker, Bystander）、目的（supporting collaboration / oversight / coexistence）。— [arXiv 2303.00362](https://arxiv.org/abs/2303.00362)、[ar5iv 本文](https://ar5iv.labs.arxiv.org/html/2303.00362)、[DOI](https://doi.org/10.1145/3544548.3580857)
- **Williams, Szafir, Chakraborti. "The Reality-Virtuality Interaction Cube: A Framework for Conceptualizing Mixed-Reality Interaction Design Elements for HRI." HRI 2019（LBR, pp. 520–521）.** [新][S2] 書誌を確認。3 軸の内容（現実–仮想連続体に加えてロボットの表現力と制御の柔軟性を軸にとる、という理解）は [記憶] で未検証。— [DOI](https://doi.org/10.1109/HRI.2019.8673071)
- **Makhataeva, Varol. "Augmented Reality for Robotics: A Review." Robotics 9(2):21, 2020.** [新][S2] 書誌を確認。MDPI が自動取得を拒否（403）したため分類軸は未検証。医療ロボット・動作計画と制御・HRI・群ロボットという応用領域別の構成という理解は [記憶]。— [DOI](https://doi.org/10.3390/robotics9020021)
- **Bassyouni, Elhajj. "Augmented Reality Meets Artificial Intelligence in Robotics: A Systematic Review." Frontiers in Robotics and AI 8, 2021.** [新][全文] 2010–2020 年の 29 本。分類は「AR supports AI」（18 本）/「AI supports AR」（11 本）と、応用別の Learning（12）/ Planning（8、タスク・経路・把持計画）/ Perception（9）。HMD が最多（48%）、空間投影が最少（3%）。AR の主用途はロボットの意図と学習結果をユーザに見せること、と結論。— [Frontiers 本文](https://www.frontiersin.org/articles/10.3389/frobt.2021.724798/full)
- **Dianatfar, Latokartano, Lanz. "Review on existing VR/AR solutions in human–robot collaboration." Procedia CIRP 97:407–411, 2021.** [新][S2] 産業 HRC 向けの短いレビュー。分類軸の詳細は未確認。— [DOI](https://doi.org/10.1016/j.procir.2020.05.259)
- **Tsamis, Chantziaras, Giakoumis, Kostavelis, Kargakos, Tsakiris, Tzovaras. "Intuitive and Safe Interaction in Multi-User Human Robot Collaboration Environments through Augmented Reality Displays." RO-MAN 2021, pp. 520–526.** [新][S2] 依頼文では「サーベイ」候補に挙がっていたが、題目上はシステム論文でありサーベイではない。— [DOI](https://doi.org/10.1109/RO-MAN50785.2021.9515474)
- **Costa, Petry, Moreira. "Augmented Reality for Human–Robot Collaboration and Cooperation in Industrial Applications: A Systematic Literature Review." Sensors 22(7):2725, 2022.** [新][S2] 追加で見つけた産業 HRC の系統的レビュー。— [DOI](https://doi.org/10.3390/s22072725)
- **Chang, Hayes. "A Survey of Augmented Reality for Human–Robot Collaboration." Machines 12(8):540, 2024.** [新][S2] 追加で見つけた 2024 年のサーベイ。MDPI が 403 のため分類軸は未確認。— [DOI](https://doi.org/10.3390/machines12080540)
- **Wang, Shen, Lee. "A Systematic Review of XR-Enabled Remote Human-Robot Interaction Systems." ACM Computing Surveys（arXiv 2024）.** [新][S2+abs] PRISMA に従い 2013 年 1 月〜2023 年 12 月の 2,561 本から 100 本を採択。遠隔 HRI における XR の利用法とインタラクション設計を整理し、ユーザ中心設計の不足を指摘。— [arXiv 2403.11384](https://arxiv.org/abs/2403.11384)、[DOI](https://doi.org/10.1145/3730574)
- **Burden, Liu, Vermeulen. "Designing Effective AR Interfaces for Human-Robot Interaction: A Scoping Review and Practical Guidelines for Robot Pick-and-Place Tasks." OzCHI 2024.** [新][S2+abs] 産業用 pick-and-place の教示に絞った AR インタフェースのスコーピングレビューと設計指針。— [DOI](https://doi.org/10.1145/3726986.3727041)
- **Habibian, Alvarez-Valdivia, Blumenschein, Losey. "A survey of communicating robot learning during human-robot interaction." IJRR 2024.** [新][S2+abs] ロボットの学習状態を人に返す視覚・触覚・聴覚インタフェースを横断し、学習と伝達を一緒に設計すると教示の質・信頼・相互適応が向上すると整理。— [DOI](https://doi.org/10.1177/02783649241281369)
- **Grubert, Dudley, Ofek, Kristensson. "Extended Reality as a Mediation Layer for Situated Human Control in Human-Robot Teaming." arXiv 2026.** [新][S2+abs] サーベイではなく視点論文だが設計次元を提案。XR を「意図・計画動作・到達可能性・状態の伝達」に加えて「人がロボット行動を理解し、形作り、承認し、中断する」ための媒介層と位置づけ、4 つの媒介機能と 6 つの設計次元（joint action possibilities / socio-physical constraints / **uncertainty and plan validity** / multimodal control and correction / roles, handover, and accountability / **anticipatory recovery**）を導出。— [arXiv 2607.25047](https://arxiv.org/abs/2607.25047)
- **Spagnuolo, Hagman, Lagerstedt, Rueben, Thellman. "Making Robot Ecologies Visible: Toward a Taxonomy for Gibsonian Human–Robot Interface Design." HRI Companion 2026.** [新][S2+abs] ロボットが何を知覚し何に作用できるか（Umwelt）を、記号的手がかりではなく生態学的な特定化で示すインタフェースの分類を提案。— [DOI](https://doi.org/10.1145/3776734.3794418)
- **van Deurzen, Rovelo Ruiz, Luyten. "A Visual Design Space for One-Dimensional Intelligible Human-Robot Interaction Visualizations." HRI 2024 Companion.** [新][S2+abs] ロボットの目標と行動を理解可能にする可視化を、限られた表示資源（1 次元のピクセル列）でどう設計するかのデザイン空間。— [DOI](https://doi.org/10.1145/3610978.3640557)

#### A-2. 説明可能ロボティクス・失敗伝達のサーベイ

- **Anjomshoae, Najjar, Calvaresi, Främling. "Explainable Agents and Robots: Results from a Systematic Literature Review." AAMAS 2019, pp. 1078–1088.** [新][S2] 書誌を確認。説明の提示モダリティ別の集計を含むという理解は [記憶]。— [Semantic Scholar 経由の DOI](https://doi.org/10.65109/kczb5817)（この DOI は S2 の返り値。AAMAS 公式の識別子かは未確認）
- **Sakai, Nagai. "Explainable autonomous robots: a survey and perspective." Advanced Robotics 36(5–6):219–238, 2022.** [新][全文（アブストラクト）] 日本（阪大）発。機械学習における説明可能性の諸義を整理し、「説明とは何か」から explainable autonomous robots を定義して関連研究をレビュー。4 要件（解釈可能な意思決定空間・ユーザモデル推定・重要情報の同定・説明生成）という理解は [記憶] で、アブストラクトからは確認できなかった。— [arXiv 2105.02658](https://arxiv.org/abs/2105.02658)、[DOI](https://doi.org/10.1080/01691864.2022.2029720)
- **Wachowiak, Çeliktutan, Coles, Canal. "A Survey of Evaluation Methods and Metrics for Explanations in Human–Robot Interaction (HRI)." 2023.** [新][S2] 題目・著者・年のみ確認。S2 に掲載誌・DOI・arXiv 番号の記録が無く、**掲載先と URL は unverified**（ICRA 2023 のワークショップ論文という理解は [記憶]）。
- **Honig, Oron-Gilad. "Understanding and Resolving Failures in Human-Robot Interaction: Literature Review and Model Development." Frontiers in Psychology 9:861, 2018.** [新][全文] 52 本をレビュー。失敗を Technical failures（ハードウェア、ソフトウェア = design / communication / processing）と Interaction failures（環境・他エージェント・人との相互作用の不確実性、社会規範違反、人的エラー）に分類し、機能的深刻度・社会的深刻度・関連性・頻度・条件・症状で特徴づける。RF-HIP モデルは (1) Communicating failures、(2) Perceiving and comprehending failures（注意の切替と維持・理解と記憶・信念と態度）、(3) Solving failures（動機・意思決定・行動）の 3 段。目に見える症状のない失敗（データ欠落など）は意図的に伝える必要があり、単純な信号は「問題がある」ことは示せても原因は説明できない、と指摘。— [Frontiers 本文](https://www.frontiersin.org/articles/10.3389/fpsyg.2018.00861/full)
- **Cameron, Castle-Green, Chughtai, Dowthwaite, Kucukyilmaz, Maior, Ngo, Schneiders ほか. "A Taxonomy of Domestic Robot Failure Outcomes: Understanding the impact of failure on trustworthiness of domestic robots." TAS 2024.** [新][S2] 家庭用ロボットの「失敗の結果」の分類。本システムの「家庭タスクでのエラー種別」の語彙に使える可能性。内容は検索結果の要約レベル。— [DOI](https://doi.org/10.1145/3686038.3686050)
- **Hwang, Lee, Porfirio, Hiatt, Mutlu. "Formal methods in robot end user development: progress, gaps, and opportunities." Foundations and Trends in Robotics 2026.** [新][S2+abs] エンドユーザ開発における形式手法（correct-by-construction 合成、自動修復など）のレビュー。「ルール違反の検出と提示」の技術側の整理に使える。— [DOI](https://doi.org/10.1108/ftrob-05-2025-0083)

#### A-3. LLM×HRI、LLM×XR、Diminished Reality のサーベイ

- **Zhang, Chen, Li, Peng, Mao. "Large language models for human-robot interaction: A review." Biomimetic Intelligence and Robotics 2023.** [新][S2] — [DOI](https://doi.org/10.1016/j.birob.2023.100131)
- **Kim, Lee, Mutlu. "Understanding Large-Language Model (LLM)-powered Human-Robot Interaction." HRI 2024, pp. 371–380.** [新][S2] サーベイではなく実験研究。— [arXiv 2401.03217](https://arxiv.org/abs/2401.03217)、[DOI](https://doi.org/10.1145/3610977.3634966)
- **Wang, Xu, Nikolova, Wang, Wang, Wang, Tong. "How Do We Research Human-Robot Interaction in the Age of Large Language Models? A Systematic Review." CHI 2026.** [新][S2+abs] PRISMA に従い 86 本を採択。LLM 駆動 HRI の研究は探索的で、実験設定・研究方法・評価指標がばらばらであると指摘。MARCER、Suzuki 2022、Pascher 2023、ImageInThat を引用。— [arXiv 2602.15063](https://arxiv.org/abs/2602.15063)、[DOI](https://doi.org/10.1145/3772318.3790920)
- **Tang, Situ, Cui, Wu, Huang. "LLM Integration in Extended Reality: A Comprehensive Review of Current Trends, Challenges, and Future Perspectives." CHI 2025.** [新][S2] 書誌のみ確認。— [DOI](https://doi.org/10.1145/3706598.3714224)
- **Wang, Zhao, Mao, Yang. "Survey of Large Language Models in Extended Reality: Technical Paradigms and Application Frontiers." arXiv 2025.** [新][S2] 検索結果の要約では、interactive agent control・XR development toolkits・generative scene synthesis などの技術パラダイムで分類。— [arXiv 2508.03014](https://arxiv.org/abs/2508.03014)
- **Ning, Zhuo, Wang, Sio, Lee. "When Generative Artificial Intelligence Meets Extended Reality: A Systematic Review." IJHCI 2025.** [新][S2] 2023–2025 年の生成 AI×XR を対象。— [arXiv 2511.03282](https://arxiv.org/abs/2511.03282)、[DOI](https://doi.org/10.1080/10447318.2025.2565392)
- **Bozkir ほか. "Embedding Large Language Models into Extended Reality."（arXiv 2402.03907, 2024）** [新] サーベイではなく主張論文（検索結果による）。— [arXiv 2402.03907](https://doi.org/10.48550/ARXIV.2402.03907)
- **De La Torre, Fang, Huang, Banburski-Fahey, Amores Fernandez, Lanier. "LLMR: Real-time Prompting of Interactive Worlds using Large Language Models." CHI 2024.** [新][S2] 依頼文の「LLMR」はサーベイではなくシステム論文。— [arXiv 2309.12276](https://arxiv.org/abs/2309.12276)、[DOI](https://doi.org/10.1145/3613904.3642579)
- **Fang, Xu, Zhang, Wang, Zheng. "Towards large language model for cognitive industrial mixed reality: A survey." Advanced Engineering Informatics 2026.** [新][S2] MARCER を引用する産業 MR×LLM サーベイ。— [DOI](https://doi.org/10.1016/j.aei.2025.104276)
- **"Intelligent human-centric manufacturing in industry 5.0: A review of large language model enabled extended reality systems." Journal of Industrial Information Integration 2026.** [新][S2] 著者名は S2 上でイニシャルのみ（要確認）。MARCER を引用。— [DOI](https://doi.org/10.1016/j.jii.2026.101229)
- **Mori, Ikeda, Saito. "A survey of diminished reality: Techniques for visually concealing, eliminating, and seeing through real objects." IPSJ Transactions on Computer Vision and Applications 9:17, 2017.** [新][S2] 日本発。実物体を視覚的に除去・隠蔽・透視する DR 研究をレビューし技術マップを提示（検索結果による）。— [DOI](https://doi.org/10.1186/s41074-017-0028-1)
- **Cheng, Yin, Yan, Gugenheimer, Lindlbauer. "Towards Understanding Diminished Reality." CHI 2022.** [新][S2] サーベイではなく実証研究。参加者は不透明度を下げる除去を好み、輪郭表示など「消した物の文脈を保つ仕組み」を評価した（検索結果による）。— [DOI](https://doi.org/10.1145/3491102.3517452)
- **Eskandari, Motamedi. "Observation-based diminished reality: a systematic literature review." Virtual Reality 29:7, 2025.** [新][S2] 2000–2024 年の 1,284 本から 67 本を分析した観測ベース DR の系統的レビュー（検索結果による）。— [DOI](https://doi.org/10.1007/s10055-024-01074-0)

### Inferences

「計画プレビュー」「エラー表示」の分類に使う設計次元として、以下の 7 軸を抽出することを提案する（各軸の出典は上記）。

| 軸 | 選択肢の例 | 由来 | 本システムの位置 |
|---|---|---|---|
| 1. 何を見せるか（内容） | 軌道・経路／将来の物体姿勢（Spatial Preview）／物体の恒久的変化（Alteration Preview）／タスク進行（Task Status）／内部状態／不確実性・計画妥当性 | Walker の Task VDE、Suzuki の Plan and Activity、Grubert の uncertainty and plan validity | 物体の事後配置（Spatial Preview）＋計画妥当性 |
| 2. 何で表すか（視覚形式） | ゴースト/レプリカ、ラベル・注釈、パネル、領域・境界、色・不透明度 | Suzuki の design components、Walker の Object Digital Twins / Entity Labels | 物体ゴースト＋物体付きラベル |
| 3. どこに固定するか | On-World（物体・環境）、On-Robot、On-Human（Head-Attached / Hand-Held）、画面内パネル | Pascher の intent location、Suzuki の hardware placement | On-World（物体アンカー）を HMD で |
| 4. いつ見せるか | 実行前（feedforward）／実行中／失敗後（再生・診断） | Pascher の temporal、Honig の RF-HIP の段階 | 実行前が主、違反は実行前に前倒し |
| 5. 何のために | 意図伝達／安全／プログラミング支援／監督（oversight）／承認と修正 | Suzuki の purposes、Pascher の goals、Grubert の authorize / interrupt | 監督・承認・修正 |
| 6. 対話性 | 出力のみ／間接操作／直接操作（修正可能か） | Suzuki の interactivity | 要設計（プレビューを直接直せるか） |
| 7. エラーの性質 | technical / interaction、深刻度、可視的症状の有無、原因説明の有無 | Honig & Oron-Gilad、Cameron 2024 | 「まだ起きていない計画上の違反」= 症状なしの失敗 |

- 既存タクソノミーでは、Before/After の「After 状態そのもの」を表す最も近いカテゴリは Walker の Spatial Previews と Object Digital Twins の組合せであり、Alteration Previews は物体への恒久的変更（加工など）を指すため、片付け後の配置にそのまま当てはまるかは定義の読み方次第である。
- Walker の Virtual Alterations にある Body Diminishments はロボット身体の縮減であり、「環境中の物体を消して After を見せる」という DR 的操作は Walker にも Suzuki にも明示的なカテゴリが無い。DR サーベイ（Mori 2017、Eskandari 2025）と Cheng 2022 の知見（文脈保持の手がかり）を別途持ち込む必要がある。
- 計画エラーの事前マーキングは、Honig の枠組みでは「目に見える症状のない失敗を意図的に伝える」場合に相当し、Grubert 2026 が挙げる "uncertainty and plan validity" と "anticipatory recovery" が最も直接的な設計次元名である。

### Gaps

- Makhataeva & Varol 2020、Chang & Hayes 2024、Dianatfar 2021、Reality-Virtuality Interaction Cube、Tang 2025（CHI）、Anjomshoae 2019 は本文を取得できず、分類軸の詳細は未検証。
- Wachowiak らのサーベイは掲載先と URL を確認できなかった。
- 「LLM ロボットの失敗説明・回復」に特化した 2024–2026 年のサーベイは見つからなかった（検索 1 回の範囲）。
- ロボット文脈に特化した Diminished Reality のサーベイは見つからなかった。

---

## KQ2. 2024–2026 年の関連論文リスト（前方引用ベース、新規優先）

### Takeaway

「MR/AR × LLM/VLM × 実行前プレビューと確認」を備えたシステムは 2024 年以降に複数現れているが（ORCESTRA、Fang ら 2024、MRPilot、MARCER、X-OOHRI）、対象はアーム・協働ロボット・マルチロボットが中心で、**家庭内片付けの事後状態を AR で Before/After 提示し、かつ違反箇所を物体単位でマークする**ものは今回の探索範囲では見当たらなかった。エラー系の AR 研究は「起きた後の診断・遠隔解消」が主で、「実行前の計画エラーのマーキング」は X-OOHRI と ORCESTRA の validation が最も近い。

### Cited Findings

以下、★は本システムの位置づけに特に重要なもの。全て前方引用リスト（S2 API）または Web 検索で実在を確認した。

#### B-1. AR/MR × LLM/VLM × ロボット

1. ★ **"ORCESTRA: VLM-driven Visual Robot programming in Mixed Reality."** Ivan Snegirev, Elizaveta Semenyakina, Mikhail Konenkov, Artem Lykov, Miguel Altamirano Cabrera, Dzmitry Tsetserukou. arXiv 2026. [新][S2+abs] パススルー MR でロボットのデジタルツインを実表面に置き、ウェイポイント教示または音声/テキスト指示を VLM が構造化計画に変換。両モードが metric grounding・**embodiment-aware validation・preview・confirmation**・デジタルツイン実行のバックエンドを共有する。言語駆動プログラミングの「実機投入前の安全層としての MR 検証」を主張しており、本システムと構造が最も近い新規論文の一つ。Suzuki 2022 を引用。— [arXiv 2608.00775](https://arxiv.org/abs/2608.00775)
2. ★ **"Enabling Waypoint Generation for Collaborative Robots using LLMs and Mixed Reality."** Cathy Mengying Fang, Krzysztof Zielinski, Pattie Maes, Joseph Paradiso, Bruce Blumberg, Mikkel Baun Kjærgaard. arXiv 2024. [新][S2+abs] 自然言語 → LLM がワークスペース理解とウェイポイント生成 → **AR で計画結果を視覚フィードバック**。実機の単純な pick-and-place で実証。「言語 → 計画 → AR プレビュー」の早期例。— [arXiv 2403.09308](https://arxiv.org/abs/2403.09308)
3. **"SiSCo: Signal Synthesis for Effective Human-Robot Communication Via Large Language Models."** Shubham D. Sonawani, Fabian Weigend, Heni Ben Amor. IROS 2024. [新][S2+abs] LLM と MR を組み合わせ、協働用の視覚的手がかりをその場で生成。自然言語信号のベースライン比でタスク完了時間 約 73% 減、成功率 18% 増、NASA-TLX 46% 減と報告。「何をどう表示するか」を LLM に合成させる方向。— [arXiv 2409.13927](https://arxiv.org/abs/2409.13927)
4. **"Teaching the Teacher: Live Foundation Model and Augmented Reality Feedback for Human-to-Robot Skill Transfer."** N. Moorman, Matthew B. Luebbers, ほか. HRI 2026. [新][S2+abs] LfD で、基盤モデルの文章フィードバック（タスク分解の助言）と AR の視覚フィードバック（デモの性能・汎化の即時評価）を併用。言語と AR の役割分担の例。— [DOI](https://doi.org/10.1145/3757279.3788667)
5. **"fARfetch: Enabling Collocated AR-HRC in Large Visually Diverse Environments with VLM-Driven AR Content Adaptation."** Christian Fronk, Han-Ting Ye, David Hunt, Miroslav Pajic, Maria Gorlatova. RO-MAN 2026. [新][S2+abs] 屋外の広い環境で、共有セマンティック地図によるランドマーク可視化と VLM による AR コンテンツ適応を行う AR-HRC。表示の可読性を VLM で保つ発想。— [arXiv 2606.25162](https://arxiv.org/abs/2606.25162)
6. **"Gesture First, LLM-Assisted Voice Complement: Exploring Multimodal Robot 'Puppeteer' Teleoperation Via Virtual Counterpart in Augmented Reality."** Yuchong Zhang, Bastian Orthmann, Shichen Ji, Michael C. Welle, Jonne van Haastregt, Danica Kragic. arXiv 2025. [新][S2+abs] Meta Quest 3 上で仮想ロボットを操って実機を動かす。N=42 の被験者内比較で、ジェスチャのみが時間制約下ではより確実・効率的、音声+ジェスチャは柔軟だが遅延と認識誤りで負荷が増えうる。「モダリティ追加が常に得ではない」という注意喚起。— [arXiv 2506.13189](https://arxiv.org/abs/2506.13189)
7. **"LLM-Based Waypoint Authoring via Augmented Reality for Human–Robot Interaction."** M. Hashemi, Kasra Mojallal, Saeed Mozaffari, S. Alirezaee. Applied Sciences 2026. [新][S2+abs] HoloLens 2 + UR10 の AR ウェイポイント決定に音声を追加。安全に関わる動詞はオンデバイスのキーワード認識と **2 段階確認ゲート**、それ以外を LLM が解釈する 2 層設計。確認ゲートの設計例。— [DOI](https://doi.org/10.3390/app16209974)
8. **"An AR-assisted Human-Robot Interaction System for Improving LLM-based Robot Control."** Ziyue Zhao, Shanhe Lou, Runjia Tan, Chen Lv. IEEE CIS-RAM 2024. [新][S2] アブストラクト未取得。題目から、LLM ベースのロボット制御を AR で補助するシステム。— [DOI](https://doi.org/10.1109/CIS-RAM61939.2024.10673005)
9. **"InteractGuide: LLM-Enhanced Multimodal Reasoning for User-Centric Interaction Recommendations in AR-HRI Authoring."** Yunqiang Pei ほか. ACM Multimedia 2025. [新][S2+abs] AR-HRI のオーサリングで、ユーザの暗黙の好みと身体的負担の衝突を LLM が推論して操作方法を推薦。— [DOI](https://doi.org/10.1145/3746027.3754542)
10. **"Historical visual question answering with large language model for Augmented Reality-assisted Human–Robot Collaboration."** Jianhao Lv, Jiahui Si, Ding Gao, Jinsong Bao. Journal of Manufacturing Systems 2025. [新][S2] アブストラクト未取得。— [DOI](https://doi.org/10.1016/j.jmsy.2025.10.005)
11. **"Trustworthy Collaborative Agents for Industrial IoT: A Multimodal Mixed Reality Framework for Human-Centric Precision Assembly."** Meipeng Huang ほか. IEEE Internet of Things Journal 2026. [新][S2+abs] 精密組立向けの軽量 MR 協働エージェント（HC-CoAgent）。— [DOI](https://doi.org/10.1109/JIOT.2026.3722235)
12. ★ **"EgoAsk: Egocentric Teaching of Personalized Object Knowledge for Household Robots."** Yuanda Hu, Wenbin Zuo, Yiting Shen, Tianle Chen, Hector Fabio Calero Tobar, Yate Ge, Xiaohua Sun, Weiwei Guo. arXiv 2026. [新][S2+abs] スマートグラスでユーザの一人称視点をロボットと共有し、個人化された物体知識の欠落を見つけて日常活動の中で質問する。被験者内 N=18。**家庭用ロボット × ウェアラブル × 物体知識**という点で片付けタスクの前提（「どこに何を置くか」の個人ルール）に直結。— [arXiv 2609.16766](https://arxiv.org/abs/2609.16766)
13. **"Beyond Static Instruction: A Multi-agent AI Framework for Adaptive Augmented Reality Robot Training."** Nicolas Leins, Jana Gonnermann-Müller, Malte Teichmann, Sebastian Pokutta. HRI Companion 2026. [新][S2+abs] AR ロボット訓練アプリを 36 名で評価し、マルチエージェント AI による適応化を提案。— [arXiv 2603.00016](https://arxiv.org/abs/2603.00016)
14. **"Gaze-supported Large Language Model Framework for Bi-directional Human-Robot Interaction."** Jens V. Rüppel, Andrey Rudenko, Tim Schreiter, Martin Magnusson, Achim Lilienthal. RO-MAN 2025. [新][S2+abs] 視線と音声を入力とする LLM ベースの双方向支援。AR 表示を使うかはアブストラクトからは未確認。— [arXiv 2507.15729](https://arxiv.org/abs/2507.15729)
15. **"Tell-XR: Conversational End-User Development of XR Automations."** A. Carcangiu, Marco Manca, Jacopo Mereu, Carmen Santoro, Ludovica Simeoli, Lucio Davide Spano. INTERACT 2025. [新][S2+abs] ロボットではなく XR オートメーション（ECA ルール）の対話的作成だが、「会話で定義 → 確認 → 修正」の段階設計が参考になる。続編 **"End-user automation authoring in VR and AR through conversations: patterns, errors and user recovery strategies"**（Behaviour & Information Technology 2026、[DOI](https://doi.org/10.1080/0144929x.2026.2714168)、[S2] アブストラクト未取得）は、題目上エラーとユーザの回復戦略を扱う。— [arXiv 2504.09104](https://arxiv.org/abs/2504.09104)
16. **"Reframing Human-Robot Interaction Through Extended Reality: Unlocking Safer, Smarter, and More Empathic Interactions with Virtual Robots and Foundation Models."** Yuchong Zhang, Yong Ma, Danica Kragic. Empathic Computing（arXiv 2025）. [新][S2+abs] 基盤モデルで動く XR 内仮想ロボットを論じる視点論文。— [arXiv 2512.02569](https://arxiv.org/abs/2512.02569)

#### B-2. 計画・意図の事前可視化、監督、オーサリング

17. ★ **"HRI Grounding: Evidence That Operators Authorize and Correct AI Multi-Robot Plans Through a Generated Supervisory Interface."** Pattaraorn Yu, Ishaan Nair, Youngbin Song, G. Soh. IEEE RA-L 2026. [新][S2+abs] AR ではないが、「AI 生成計画を人が実行前に承認・修正できるか」を直接測った研究。計画を 1 ステップ 1 コントロールで自動描画。100 件の生成計画の約 5 分の 1 に意味的欠陥。16 名の操作者が正しい計画と欠陥計画を高感度・低誤警報で弁別（**d′ = 2.90**）、無監督なら失敗した 96 ミッション中 85 を回復。MARCER を引用。評価設計の手本（KQ3 参照）。— [DOI](https://doi.org/10.1109/LRA.2026.3730218)
18. ★ **"Supporting Long-Horizon Tasks in Human-Robot Collaboration by Aligning Intentions via Augmented Reality."** Chenyang Ma, Yue Yang, Bryce Ikeda, Daniel Szafir. HRI 2025. [新][S2+abs] 長期タスクでのサブタスク目標の曖昧さ（intention misalignment）に対し、AR を双方向チャネルとして使い、ロボットが曖昧なサブタスクの意図を提示しユーザのフィードバックで適応。3 物体の pick-and-place で検証。「目標物体と目標姿勢の事前すり合わせ」は After 状態の合意に相当。— [DOI](https://doi.org/10.1109/HRI61500.2025.10973947)
19. **"PRogramAR: Augmented Reality End-User Robot Programming."** Bryce Ikeda, Daniel Szafir. ACM THRI 2024. [新][S2] MARCER の前身にあたる AR エンドユーザプログラミング。— [DOI](https://doi.org/10.1145/3640008)
20. **"RoboVisAR: Immersive Authoring of Condition-based AR Robot Visualisations."** Rasmus Lunding, Mille Skovhus Lunding, Tiare M. Feuchtner, Marianne Graves Petersen, Kaj Grønbæk, Ryo Suzuki. HRI 2024. [新][S2] 条件に応じて出し分ける AR ロボット可視化を没入環境でオーサリング。「どの条件でどの可視化を出すか」という本システムのルール設計に対応。— [DOI](https://doi.org/10.1145/3610977.3634972)
21. **"ARTHUR: authoring human–robot collaboration processes with augmented reality using hybrid user interfaces."** Rasmus Lunding, Sebastian Hubenschmid, Tiare M. Feuchtner, Kaj Grønbæk. Virtual Reality 2025. [新][S2+abs] デスクトップ/タッチで作り HMD で試すハイブリッド型オーサリング。ロボット・タスク・システム状態を伝える 20 種のマルチモーダルフィードバックを提供。— [arXiv 2501.02304](https://arxiv.org/abs/2501.02304)
22. **"REACTR: A Responsive Environment for Authoring Code and Testing Robots."** Bryce Ikeda, Daniel Szafir. RO-MAN 2026. [新][S2+abs] コード変更と挙動の可視化を常時同期させるライブプログラミング環境。— [DOI](https://doi.org/10.1109/RO-MAN72286.2026.11714554)
23. **"ERUPT: An Open Toolkit for Interfacing with Robot Motion Planners in Extended Reality."** Isaac Ngui, Courtney McBeth, ほか. arXiv 2025. [新][S2+abs] XR 内で環境を組み替えながら動作計画を対話的に行うオープンソース基盤。— [arXiv 2510.02464](https://arxiv.org/abs/2510.02464)
24. **"ROS2MR: Connecting ROS 2 Motion Planning to Mixed-Reality Trajectory Visualization."** Santiago Berrezueta-Guzman, Habiba-Loai Khalil, A. Koshelev, Stefan Wagner. arXiv 2026. [新][S2+abs] MoveIt を含む ROS 2 の関節軌道を MR 再生用フォーマットに変換。本プロジェクト（MoveIt 軌道プレビュー）と実装面で近い。— [arXiv 2611.11830](https://arxiv.org/abs/2611.11830)
25. **"ReachVox: Clutter-Free Reachability Visualization for Robot Motion Planning in Virtual Reality."** Steffen Hauck, Diar Abdlkarim, John Dudley, Per Ola Kristensson, Eyal Ofek, Jens Grubert. ISMAR 2025. [新][S2+abs] 対象物近傍の到達可能性を最小限に符号化する可視化。「できる/できない」を煩雑にならずに示す例。— [arXiv 2508.11426](https://arxiv.org/abs/2508.11426)
26. **"RCLL-AR: Augmented Reality Support for Understanding Autonomous Processes in the RoboCup Logistics League."** Jan-Heliodor Tscherko, Peter Kohout, Philipp Fleck, Matteo Tschesche, Alexander Ferrein, Gerald Steinbauer-Wagner, Alexander Plopski. ISMAR 2025. [新][S2+abs] 自律ロボット群の進行状況と今後の動きを観客に AR で提示。専門家インタビュー・初心者調査・HMD 調査を実施し、複雑な自律システムでの AR の課題も報告。— [DOI](https://doi.org/10.1109/ISMAR67309.2025.00045)
27. **"Evaluating Digital Twin Visualisations for Safety and Trust in Robot-Assisted Dressing."** Y. Cogurcu ほか. ACM THRI 2026. [新][S2+abs] 着衣支援で Bounding Boxes と Trajectory Visualisation を比較（被験者内 N=36）。BB は知覚安全・信頼を有意に向上、軌道表示は使用性と予測可能性を向上。— [DOI](https://doi.org/10.1145/3805805)
28. **"Delegate the Details: Flexible Assembly Constraint Authoring for Collaborative XR."** Ben Yang, Xichen He, Charlie Zou, Jen-Shuo Liu, Barbara Tversky, Steven K. Feiner. ISMAR 2026. [新][S2+abs] 全部品の 6DoF 姿勢を指定させず、制約の指定権限に幅を持たせる XR オーサリング。片付けの「置き場所の許容範囲」を指定する発想に近い。— [DOI](https://doi.org/10.1109/ISMAR70079.2026.00083)
29. **"From Planning to Verification: Designing Interactions for Multi-Drone Search and Rescue Operations in Mixed Reality."** Lorélia Latarche, Christophe Jouffrais, Jérémie Garcia. NordiCHI 2026. [新][S2+abs] 計画・監督・手動操縦の遷移を research-through-design で検討。— [DOI](https://doi.org/10.1145/3829807.3829828)
30. **"Visualizing Motion Intent in Heterogeneous Multi-Robot Environments."** Malte Riechmann-Thom, Jan Rexilius. ISMAR-Adjunct 2025. [新][S2+abs] 地上・飛行ロボットが混在する場での動作意図の AR 可視化枠組み。— [DOI](https://doi.org/10.1109/ISMAR-Adjunct68609.2025.00145)
31. **"Mirror Skin: In Situ Visualization of Robot Touch Intent on Robot Skin."** David Wagmann, Matti Krüger, Chao Wang, Michael Gienger, Jürgen Steimle. UIST 2025. [新][S2+abs] 接触意図（誰が・どこに・いつ）をロボット表面に表示。On-Robot アンカーの例。— [arXiv 2512.11472](https://arxiv.org/abs/2512.11472)
32. **"Designing Intent Communication for Agent-Human Collaboration."** Yi Li, Francesco Chiossi, ほか. MUM 2025. [新][S2+abs] 「何を伝えるか」のモデルが「どう・いつ伝えるか」の系統的選択に結びついていない、という問題提起。— [arXiv 2510.20409](https://arxiv.org/abs/2510.20409)
33. **"ARTOO-DARTU: Studying AR-HRC With AR Obstruction Mitigation During a Warehouse Task."** Christian Fronk, Han-Ting Ye, Zhehan Qu, Maria Gorlatova. arXiv 2026. [新][S2+abs] AR の状況内分析表示が実世界を遮る問題に対し遮蔽検出・緩和を導入。N=34 で、緩和が有効なときのみ全体効率 46% 向上。**AR オーバーレイが実物を隠す副作用**は Before/After 表示でも避けられない論点。— [arXiv 2606.25202](https://arxiv.org/abs/2606.25202)
34. **"Context-Aware Augmented Reality for Human-Robot Collaboration."** Shakiba Davari, Akhil Ajikumar, Mohsen Moghaddam. ISMAR-Adjunct 2025. [新][S2+abs] 文脈適応型 AR による双方向の意図伝達。— [DOI](https://doi.org/10.1109/ISMAR-Adjunct68609.2025.00087)
35. **"HORUS: A Mixed Reality Interface for Managing Teams of Mobile Robots."** Omotoye Shamsudeen Adekoya, Antonio Sgorbissa, Carmine Recchiuto. UR 2026. [新][S2+abs] 複数移動ロボットの状態監視・センサ可視化・タスク割当の MR インタフェース。— [arXiv 2506.02622](https://arxiv.org/abs/2506.02622)
36. **"A digital twin-enabled environment for end-user development of robot tasks."** Luigi Gargioni, Daniela Fogli, Elena Margherita Nava. Intelligent Service Robotics 2026. [新][S2] アブストラクト未取得。MARCER を引用。— [DOI](https://doi.org/10.1007/s11370-026-00758-7)
37. **"Bootstrapping Human-Like Planning via LLMs."** David Porfirio, Vincent Hsiao, Morgan Fine-Morris, Leslie N. Smith, Laura M. Hiatt. RO-MAN 2025. [新][S2+abs] AR ではない。ドラッグ&ドロップと自然言語プログラミングの統合を LLM で検討。MARCER と ImageInThat を引用。— [arXiv 2506.22604](https://arxiv.org/abs/2506.22604)
38. **"Reality Promises: Virtual-Physical Decoupling Illusions in Mixed Reality via Invisible Mobile Robots."** UIST 2025. [新][S2] 著者・アブストラクトは今回未出力（題目と DOI のみ確認）。題目上、MR 内でロボットを不可視化する（DR 的）手法。MARCER・Suzuki・Walker・PRogramAR を引用。— [DOI](https://doi.org/10.1145/3746059.3747660)

#### B-3. エラー・失敗・能力限界・不確実性の可視化

39. ★ **"Mixed Reality Outperforms Virtual Reality for Remote Error Resolution in Pick-and-Place Tasks."** Advay Kumar, Stephanie Simangunsong, Pamela Carreno-Medrano, Akansel Cosgun. HRI 2025. [新][S2+abs] ロボットがエラーを検出して停止した後、遠隔操作者が解消する場面で MR / VR / カメラ映像を比較（N=21、線形混合モデル）。MR が解消時間・SUS・NASA-TLX の全てで優位。— [arXiv 2502.06141](https://arxiv.org/abs/2502.06141)
40. ★ **"Replayable Augmented Reality Visualization for Robot Fault Diagnosis: A Comparative Study."** Lachlan James Richards, Yew Siang Ku, Alexander Calvert, Joshua Migdal, Gabriel Hebert, Elizabeth Croft, Akansel Cosgun. International Journal of Social Robotics 2025. [新][S2+abs] 故障直前 15 秒のセンサデータ再生を AR とタブレットで比較（N=24、8 つの故障シナリオ）。**同一情報ならタブレットが AR より好まれた**（視野の狭さ・ぼやけが理由）。AR の優位性を前提にできないという反例。— [DOI](https://doi.org/10.1007/s12369-025-01219-4)
41. **"Indicating Robot Vision Capabilities with Augmented Reality."** Hong Wang, Ridhima Phatak, James Ocampo, Zhao Han. International Journal of Social Robotics（arXiv 2025）. [新][S2+abs] ロボットの視野限界を示す 4 種の AR インジケータを N=41 で比較。ロボット頭部側（egocentric）とタスク空間側（allocentric）のアンカーを比べ、評価は正確さ・確信度・効率・負荷。**アンカー位置の比較実験**として参考になる。— [arXiv 2511.03550](https://arxiv.org/abs/2511.03550)
42. **"Interaction-aware augmented reality interface for assisting erring social robots."** Kyohei Hosoda, Dražen Brščić, Takayuki Kanda. Journal on Multimodal User Interfaces 2025. [新][S2+abs] 接客ロボットの誤りを店員が AR HMD で監督・介入。AR オブジェクトの位置を動かして店員の頭の動きを自然に見せる視線誘導を提案。日本拠点（KQ4 参照）。— [DOI](https://doi.org/10.1007/s12193-025-00453-4)
43. **"Robot-Assisted Decision-Making: Unveiling the Role of Uncertainty Visualisation and Embodiment."** Sarah Schömbs, Saumya Pareek, Jorge Goncalves, Wafa Johal. CHI 2024. [新][S2+abs] ロボットの不確実性の可視化（グラフ表示 vs 身体動作）と確信度（低・高・100%）が人の意思決定と透明性知覚に与える影響。— [DOI](https://doi.org/10.1145/3613904.3642911)
44. **"Uncertain Pointer: Situated Feedforward Visualizations for Ambiguity-Aware AR Target Selection."** Ching-Yi Tsai, Nicole Tacconi, Andrew D. Wilson, Parastoo Abtahi. CHI 2026. [新][S2+abs] ロボット論文ではないが、確定前に複数候補を注釈する feedforward 可視化（色などの識別子で曖昧さ解消、不透明度などで不確実性を表現）を 25 種のポインタ空間として体系化。X-OOHRI と ImageInThat を引用。物体単位マーキングの視覚語彙として直接使える。— [arXiv 2602.13433](https://arxiv.org/abs/2602.13433)
45. **"Multimodal Coherent Explanation Generation of Robot Failures."** Pradip Pramanick, Silvia Rossi. IROS 2024. [新][S2] AR ではない。失敗説明をモダリティ間で整合させる生成。— [arXiv 2410.00659](https://arxiv.org/abs/2410.00659)
46. **"Visual Explanation With Action Query Transformer in Deep Reinforcement Learning and Visual Feedback via Augmented Reality."** Hidenori Itaya, Wantao Yin, Tsubasa Hirakawa, Takayoshi Yamashita, Hironobu Fujiyoshi, Komei Sugiura. IEEE Access 2025. [新][S2+abs] 深層強化学習エージェントの行動根拠の視覚的説明を AR でフィードバック。日本拠点（KQ4 参照）。— [DOI](https://doi.org/10.1109/ACCESS.2025.3554493)
47. **"Enhancing Privacy and Trust in Domestic Robots Through Real-Time Feedback and Intervention Interfaces."** Jiayang Xu, Marius Hoggenmueller, Xinyan Yu. OzCHI 2025. [新][S2+abs] 家庭用ロボットのデータ取扱いをリアルタイムに可視化し介入できるようにして、プライバシー知覚・信頼・UX への影響を調査。AR 使用の有無はアブストラクトからは未確認。— [DOI](https://doi.org/10.1145/3764687.3764705)
48. **"Prompting an Embodied AI Agent: How Embodiment and Multimodal Signaling Affects Prompting Behaviour."** Tianyi Zhang, Colin Au Yeung, Emily Aurelia, Yuki Onishi, Neil Chulpongsatorn, Jiannan Li, Anthony Tang. CHI 2025. [新][S2+abs] VR 内の身体化エージェントが、言及中の物体をハイライトするなどのマルチモーダル信号で会話のグラウンディングを支える。指示途中の物体ハイライトの例。— [DOI](https://doi.org/10.1145/3706598.3713110)

#### B-4. 既存レビューに収録済みの中核論文（前方引用で再確認したもの）

- **MARCER**（Ikeda, Gramopadhye, Nekervis, Szafir, HRI 2025）[既] — [DOI](https://doi.org/10.1109/HRI61500.2025.10974232)
- **Explainable OOHRI / X-OOHRI**（Wang, Kari, Abtahi, HRI 2026）[既]。S2 上の被引用は 4 件のみ（Body Sublimation〔UIST 2026、[DOI](https://doi.org/10.1145/3830398.3830583)〕、MRPilot、Qu ら、Uncertain Pointer）。— [arXiv 2601.14587](https://arxiv.org/abs/2601.14587)
- **SHRIMP**（UIST 2026）[既] — [arXiv 2608.08884](https://arxiv.org/abs/2608.08884)
- **RoboCritics**（HRI 2026）[既] — [arXiv 2603.06842](https://arxiv.org/abs/2603.06842)
- **MRPilot**（arXiv 2026）[既]。計画と実行状態を「構造化されたコミットメント」として状況内ビューと俯瞰ビューで同期表示し、Forming / Reviewing / Following ほかの段階で監督と介入を支える。— [arXiv 2610.07477](https://arxiv.org/abs/2610.07477)
- **GhostObjects**（UIST 2025 Adjunct）[既] — [arXiv 2508.11022](https://arxiv.org/abs/2508.11022)
- **ImageInThat**（HRI 2025）[既] — [arXiv 2503.15500](https://arxiv.org/abs/2503.15500)
- **Better Situational Awareness in AR-HRC?**（Qu ら、arXiv 2026）[既] — [arXiv 2609.01461](https://arxiv.org/abs/2609.01461)

### Inferences

- MARCER の被引用 16 件のうち、言語指示・計画確認に関わるのは HRI Grounding、SHRIMP、RoboCritics、X-OOHRI、GhostObjects、Bootstrapping、Teaching the Teacher、Delegate the Details と、産業 MR×LLM のサーベイ 2 本、形式手法レビュー 1 本であり、**家庭内片付けを対象とするものは無い**。
- 「実行前に確認させる」設計は 2024 年以降の共通項になりつつある（ORCESTRA の preview/confirmation、Hashemi らの 2 段階確認ゲート、MRPilot の Reviewing 段階、HRI Grounding のステップごとの承認）。差別化点は確認の「単位」と「形式」であり、既存は軌道・ウェイポイント・ステップ列が中心で、**環境の事後状態（物体配置）そのものを単位とする確認**は Ma ら 2025（目標姿勢のすり合わせ）と GhostObjects / ImageInThat（入力側）に限られる。
- AR の優位は自明ではない。Richards ら 2025（タブレットが好まれた）、Leins ら 2026（AR は負荷・使用性を有意に改善せず、空間能力の低い人を補償する効果のみ示唆）、Zhang ら 2025（音声追加で負荷増）、ARTOO-DARTU（遮蔽緩和が無いと効果が出ない）は、本システムの評価で非 AR ベースライン（タブレット/2D）を置くべき根拠になる。

### Gaps

- OpenAlex と arXiv API が使えず、引用グラフに入っていない新着プレプリント（MARCER/Suzuki 等を引用しないもの）は網羅できていない。特に CoRL / ICRA / RA-L 側の「VLM による再配置目標画像生成 + 人への提示」系は今回ほぼ拾えていない。
- VAM-HRI 2024/2025 ワークショップの採択論文一覧は公式ページを取得できなかった（第三者ページのみヒット）。
- 上記のうち [S2] ラベルの論文（8, 10, 19, 20, 36, 38, 45 ほか）はアブストラクト未読で、関連性は題目からの推定。
- ImageInThat の被引用 7 件・RoboVisAR の 12 件は全件確認したが、PRogramAR 30 件のうち産業プログラミング系は関連が薄いため説明を省いた。

---

## KQ3. 計画プレビュー／意図可視化が信頼・負荷・エラー検出・過信に与える影響と、使われた評価指標

### Takeaway

「ユーザはプレビューから計画の誤りを見抜けるか」を信号検出理論で直接測った研究が 2026 年に現れた（HRI Grounding: d′ = 2.90、失敗ミッション 96 中 85 を回復）が、これは非 AR のステップ列 UI であり、**AR の空間プレビューで計画エラー検出率を測った研究は今回見つからなかった**。隣接する LLM エージェント研究は「もっともらしい計画は誤りがあっても受け入れられやすい」「説明は評価精度を上げるが信頼はあまり動かさない」と報告しており、プレビューが過信を生む危険を評価設計に織り込む必要がある。

### Cited Findings

- **エラー弁別を直接測る設計（非 AR）**: HRI Grounding は 16 名の操作者に正しい計画と意味的欠陥のある計画を提示し、感度 d′ = 2.90・低誤警報、失敗するはずだった 96 ミッション中 85 の回復、完了時間・操作回数・エラー・作業負荷の低下を報告。— [DOI](https://doi.org/10.1109/LRA.2026.3730218)
- **もっともらしい計画への過信（非ロボット）**: He, Demartini, Gadiraju "Plan-Then-Execute: An Empirical Study of User Trust and Team Performance When Using LLM Agents As A Daily Assistant"（CHI 2025、N=248、リスクの異なる 6 タスク）は、LLM エージェントは高品質な計画と実行時の適切な関与があれば有効だが、もっともらしく見える計画のエージェントを誤って信頼しやすい「諸刃の剣」と結論。— [arXiv 2502.01390](https://arxiv.org/abs/2502.01390)、[DOI](https://doi.org/10.1145/3706598.3713218)
- **説明・修正と信頼の乖離（非 AR）**: Chen, Yang, Boggess, Heo, Feng, Topcu "Evaluating Human Trust in LLM-Based Planners: A Preliminary Study"（arXiv 2025）は PDDL ドメインで LLM プランナと古典プランナを比較。指標は主観的信頼質問紙と客観的な評価精度（計画の正誤判定）。正しさが信頼と成績の主因、LLM の説明は評価精度を上げるが信頼への効果は限定的、計画の refinement は評価精度をあまり上げずに信頼を上げうる。— [arXiv 2502.20284](https://arxiv.org/abs/2502.20284)
- **軌道表示と安全領域表示の信頼への効果**: Cogurcu ら（THRI 2026、被験者内 N=36、6 条件）は検証済みのインタラクション品質質問紙と使用性質問紙を使用。Bounding Boxes が知覚安全・不快感・信頼を有意に改善（各 p < 0.001）、Trajectory Visualisation が使用性（p = 0.007）と確信・予測可能性を改善。— [DOI](https://doi.org/10.1145/3805805)
- **エラー解消の媒体比較**: Kumar ら（HRI 2025、N=21）は解消時間・SUS・NASA-TLX を線形混合モデルで分析し、MR が VR とカメラ映像に優ると報告。— [arXiv 2502.06141](https://arxiv.org/abs/2502.06141)
- **故障診断での AR の不利**: Richards ら（IJSR 2025、N=24、8 シナリオ）では同一情報のタブレットが AR より有効・使いやすいと評価された。— [DOI](https://doi.org/10.1007/s12369-025-01219-4)
- **AR と空間能力・認知負荷**: Leins ら "Robot Programming with Augmented Reality: The Role of Spatial Ability"（arXiv 2026、被験者間 N=71、UR5e）は Mental Rotation Test・主観的認知負荷・使用性を測定。AR は全体では負荷・使用性を有意に改善しなかったが、対照群でのみ空間能力が使用性と外在的負荷を予測し、AR が低空間能力者の不利を補償する可能性を示した。— [arXiv 2602.03544](https://arxiv.org/abs/2602.03544)
- **状況認識（SA）の多層評価**: Qu ら（arXiv 2026、被験者間 N=30）は AR とモバイル UI を同等情報で比較し、ロボットと環境の両方について複数レベルの SA を評価。AR の空間可視化が視覚的注意を変え、競合する SA 需要を生みうると問題提起。[既] — [arXiv 2609.01461](https://arxiv.org/abs/2609.01461)
- **遮蔽の副作用と効率**: ARTOO-DARTU（N=34）は遮蔽緩和ありのときのみ効率 46% 向上、実世界の視認を要するサブタスクで 61% 高速化。— [arXiv 2606.25202](https://arxiv.org/abs/2606.25202)
- **LLM 生成の視覚信号と負荷**: SiSCo は完了時間・成功率・NASA-TLX 下位尺度・未知物体への信号の主観評価を使用。— [arXiv 2409.13927](https://arxiv.org/abs/2409.13927)
- **メンタルモデルの正確さ**: Wang ら（IJSR、N=41）は視野インジケータを正確さ・確信度・タスク効率・負荷で評価。— [arXiv 2511.03550](https://arxiv.org/abs/2511.03550)
- **信頼違反を使った AR シミュレーションの妥当性**: Guerra, Söhngen, Prilla "Investigating the Validity of Augmented Reality Simulations for Human-Robot Interaction through Trust"（2026、被験者間 N=40）は、AR 上の仮想ロボットと実機の受け渡しで 2 種の信頼違反（落とす・渡しにくい位置）を与え、ベイズ解析で条件差の明確な証拠なし・一部は実質的等価と報告。**実機なしの AR シミュレーションで信頼を測ることの妥当性**を支える初期証拠。S2 の会議名表記は "Message Understanding Conference" だが、DOI 接頭辞と著者から Mensch und Computer 2026 と推定（会議名は unverified）。— [DOI](https://doi.org/10.1145/3820253.3820273)
- **不確実性表示と意思決定**: Schömbs ら（CHI 2024）は不確実性可視化のモダリティと確信度が、意思決定に至る過程と透明性知覚を有意に変えると報告。— [DOI](https://doi.org/10.1145/3613904.3642911)
- **サーベイが挙げる評価の現状**: Suzuki 2022 は評価を Demonstration / Technical / User Evaluation（NASA-TLX、ラボ実験、インタビュー、質問紙、観察、専門家インタビュー）に分類。— [ar5iv 本文](https://ar5iv.labs.arxiv.org/html/2203.03254)。Wang ら CHI 2026 は LLM 駆動 HRI の評価指標が研究ごとにばらばらだと指摘。— [arXiv 2602.15063](https://arxiv.org/abs/2602.15063)

### Inferences

後続のユーザスタディ設計に向けた指標の候補（上記研究で実際に使われたもの）:

| 測りたいこと | 指標 | 使用例 |
|---|---|---|
| 計画エラーの検出能力 | 欠陥計画を混ぜた承認/却下課題での hit / false alarm、d′、回復できたミッション数 | HRI Grounding |
| 計画の正誤判定の精度 | 評価精度（客観）と主観的信頼の両方を取り、乖離を見る | Chen ら 2025 |
| 過信・適切な依存 | 欠陥計画の受容率、計画品質×関与段階の交互作用 | He ら 2025 |
| 作業負荷 | NASA-TLX（全体または下位尺度）、外在的認知負荷 | Kumar、SiSCo、Leins |
| 使用性 | SUS | Kumar |
| 信頼・知覚安全 | 検証済み質問紙、信頼違反の操作 | Cogurcu、Guerra |
| 状況認識 | ロボット/環境別・複数レベルの SA | Qu ら |
| メンタルモデル | 正確さ＋確信度 | Wang ら（視野インジケータ） |
| 個人差の統制 | Mental Rotation Test | Leins |
| 副作用 | 実世界視認が必要なサブタスクの時間（遮蔽の影響） | ARTOO-DARTU |

- 本システムの評価では、(a) 欠陥を意図的に埋め込んだ計画を一定割合で混ぜ、(b) AR Before/After・AR+違反マーキング・非 AR（テキスト列/タブレット）を比較し、(c) d′ と受容率で「検出」と「過信」を分けて測る、という設計が先行研究と直接比較可能になる。HRI Grounding の「約 5 分の 1 に欠陥」という比率は欠陥混入率の参考値になる。
- 既存レビューに収録済みの信頼較正・SAT・SAGAT 系の文献（Lee & See 2004、Chen 2014/2018、Endsley 1995 など）と組み合わせれば、指標の理論的根拠は足りる。
- Guerra ら 2026 と、実機を当面使わないという本プロジェクトの前提は整合する（AR/シミュレーションでの信頼計測に初期的な妥当性の証拠がある）。ただし対象は受け渡し課題であり、計画プレビューの文脈への一般化は未検証。

### Gaps

- AR の空間プレビュー（ゴースト配置）でユーザが計画エラーを検出できる率を測った研究は見つからなかった。X-OOHRI・MARCER・MRPilot の評価が何を測ったかは既存レビュー側の記録を参照のこと（今回は再読していない）。
- プレビューが「過信」を増やすかを AR×ロボットで直接検証した研究は見つからなかった。He ら・Chen らは非 AR・非ロボット（または PDDL 計画）である。
- He ら 2025 の信頼較正・認知負荷の具体的尺度、Chen ら 2025 の参加者数は取得したページからは確認できなかった。

---

## KQ4. 日本語または日本拠点の関連研究

### Takeaway

家庭用ロボットへのエンドユーザ指示インタフェースは、JST ERATO 五十嵐デザインインタフェースプロジェクト（五十嵐・稲見・坂本・杉浦ら）が 2009–2011 年に CHI で集中的に発表しており、依頼文に挙がった 4 件は全て実在を確認できた（「Fukui」に該当する論文は特定できなかった）。2024–2026 年の日本拠点の関連研究は、失敗する接客ロボットの AR 監督（京大 神田研）、強化学習の説明の AR 提示（中部大・慶應）、影投影による動作予告、XR モダリティ比較（立命館 谷口研）が見つかったが、**LLM 計画 + AR プレビューを家庭タスクで扱う日本発の研究は見つからなかった**。

### Cited Findings

#### 2009–2011 年: ERATO 五十嵐プロジェクトの家庭用ロボット指示インタフェース（全て [新]）

- **Sugiura, Sakamoto, Withana, Inami, Igarashi. "Cooking with robots: designing a household system working in open environments." CHI 2010.** [S2] 実在確認。— [DOI](https://doi.org/10.1145/1753326.1753693)
- **Sakamoto, Honda, Inami, Igarashi. "Sketch and run: a stroke-based interface for home robots." CHI 2009.** [S2] 実在確認。— [DOI](https://doi.org/10.1145/1518701.1518733)
- **Zhao, Nakamura, Ishii, Igarashi. "Magic cards: a paper tag interface for implicit robot control." CHI 2009.** [S2] 実在確認。— [DOI](https://doi.org/10.1145/1518701.1518730)
- **Hashimoto, Ishida, Inami, Igarashi. "TouchMe: An Augmented Reality Based Remote Robot Manipulation." 2011.** [S2] 題目・著者・年を確認。S2 に掲載会議と DOI の記録が無く、**会議名（ICAT 2011 という理解は [記憶]）と URL は unverified**。
- **Liu, Sakamoto, Inami, Igarashi. "Roboshop: multi-layered sketching interface for robot housework assignment and management." CHI 2011.** [S2] 追加で確認。題目上、家事の割当と管理をスケッチで行う。本システムの「家事タスクの指示と管理」に最も近い古典。— [DOI](https://doi.org/10.1145/1978942.1979035)
- **Ishii, Zhao, Inami, Igarashi, Imai. "Designing Laser Gesture Interface for Robot Control." INTERACT 2009, pp. 479–492.** [S2] 追加で確認。— [DOI](https://doi.org/10.1007/978-3-642-03658-3_52)
- **Sugiura, Igarashi, Takahashi, Gowon, Fernando, Sugimoto, Inami. "Graphical instruction for a garment folding robot." SIGGRAPH 2009 Emerging Technologies.** [S2] 追加で確認。依頼文の「Sugimoto」はこの共著者（杉本）に対応する可能性がある。— [DOI](https://doi.org/10.1145/1597956.1597968)
- JST ERATO 五十嵐プロジェクトのページに、ハンドヘルド AR 機器で家庭用ロボットに連続タスクを教える研究の紹介がある（検索結果による。ページ本文は未読）。— [JST ERATO プロジェクトページ](https://www.jst.go.jp/erato/igarashi/projects/SequentialTask/index.html)

#### 近未来可視化（九州大 倉爪研）

- **Previewed Reality**（Horikawa, Egashira, Nakashima, Kawamura, Kurazume, IROS 2017）[既]。ロボットの計画動作と物理シミュレータの予測結果を AR と HMD で実風景に重ね、数秒先を確認させる。日本語の ROBOMEC 講演（2017、2019、2020）が研究室サイトに公開されている（検索結果による。PDF 本文は未読）。— [ROBOMEC 2017 PDF](https://robotics.ait.kyushu-u.ac.jp/kurazume/papers/ROBOMEC17-1.pdf)、[ROBOMEC 2019 PDF](https://robotics.ait.kyushu-u.ac.jp/irvs/wp/wp-content/uploads/2020/02/ROBOMEC19-2.pdf)、[ROBOMECH 2020 PDF](https://robotics.ait.kyushu-u.ac.jp/kurazume/papers/ROBOMECH20-6.pdf)

#### 2024–2026 年の日本拠点の研究（全て [新]）

- **Hosoda, Brščić, Kanda. "Interaction-aware augmented reality interface for assisting erring social robots." JMUI 2025.** [S2+abs] 誤りを起こす接客ロボットを人間の店員が AR HMD で監督。販売場面のユーザ調査で顧客の主観的体験と使用性が向上。— [DOI](https://doi.org/10.1007/s12193-025-00453-4)
- **Itaya, Yin, Hirakawa, Yamashita, Fujiyoshi, Sugiura. "Visual Explanation With Action Query Transformer in Deep Reinforcement Learning and Visual Feedback via Augmented Reality." IEEE Access 2025.** [S2+abs] 行動根拠の視覚的説明を AR で提示。— [DOI](https://doi.org/10.1109/ACCESS.2025.3554493)
- **Miyasaka, Matsumoto. "Motion preview of a humanoid robot by shadow projection." Artificial Life and Robotics 2026.** [S2] アブストラクト未取得。題目上、影の投影でヒューマノイドの動作を予告。Pascher 2023 を引用。— [DOI](https://doi.org/10.1007/s10015-026-01143-4)
- **Tornberg, Torck, El Hafi, Taniguchi. "Evaluating the Impact of Adaptive Extended Reality on Human-Robot Interaction Across the Reality-Virtuality Continuum." arXiv 2026.** [S2+abs] サイバネティック・アバターの文脈で、XR モダリティ（AR / AV / VR）を固定せずタスク成果への影響を検証。— [arXiv 2609.31138](https://arxiv.org/abs/2609.31138)
- **"Does Robot Clothing Really Help? User Preferences and Effects in Simulated Domestic Scenarios." JACIII 2025.** [S2] 題目と DOI のみ確認（著者未出力）。家庭場面のシミュレーション研究で Suzuki 2022 を引用。本システムとの関連は薄い。— [DOI](https://doi.org/10.20965/jaciii.2025.p1530)
- **Ohta, Ban, Nii, Gourmelen, Narumi, Sousa ほか. "Body Sublimation: Designing State-Changing Extended Hand for Embodied Out-of-Reach Interaction." UIST 2026.** [S2+abs] XR の知覚的柔軟性とロボットの物理能力を統合する拡張手の概念。X-OOHRI を引用。計画可視化ではないが日本（東大 鳴海研）関係の XR×ロボット研究。— [DOI](https://doi.org/10.1145/3830398.3830583)
- 日本人研究者による基盤文献として、Suzuki ら 2022（鈴木遼）[既]、Sakai & Nagai 2022（阪大）、Mori, Ikeda, Saito 2017（DR サーベイ）が KQ1 に挙げたとおり存在する。Mori らには 2011 年の日本語 DR サーベイ（日本バーチャルリアリティ学会論文誌）もある（検索結果による。本文未読）。— [TVRSJ 2011 PDF](https://www.rm2c.ise.ritsumei.ac.jp/papers/2011/TVRSJ_MR5_mori.pdf)

### Inferences

- 2009–2011 年の ERATO 系研究は「家庭で非専門家がロボットに家事を指示する」という問題設定を、スケッチ・カード・レーザ・AR タッチといった 2D/タンジブル入力で解いており、本システムはその問題設定を「自然言語 + LLM 計画 + HMD での事後状態プレビュー」に置き換えたものとして系譜づけられる。特に Roboshop（家事の割当と管理）と Cooking with robots（開環境の家庭システム）が直接の先行にあたる可能性が高いが、いずれも本文未読のため、プレビュー機能の有無は確認が必要。
- Previewed Reality は「数秒先の動作」の提示であり、本システムの「タスク完了後の環境状態」の提示とは時間スケールが異なる。この差は位置づけ上の明確な区別点になる。

### Gaps

- 依頼文の「Fukui」に該当する論文は特定できなかった（検索語に手がかりが無く、未調査）。
- 日本語文献（日本ロボット学会誌、日本 VR 学会論文誌、インタラクション、ROBOMECH）の 2024–2025 年分は、日本語検索 1 回では該当する論文が出なかった。J-STAGE を「近未来可視化」「拡張現実 ロボット 意図提示」などで直接検索する必要がある。
- ERATO 系 7 件はいずれも書誌確認のみで、本文・アブストラクトは読んでいない。
- 稲見研・五十嵐研の 2024 年以降の関連研究、および LLM 計画 + AR を扱う国内研究は今回の探索では見つからなかった（存在しないことの確認ではない）。
