# 自然言語によるロボット指示 × AR/MR での計画・プログラム・ルール可視化(プレビュー/確認/編集)文献調査

> 調査日: 2026-11-22。凡例:
> - **【新規】** = 既存レビュー `master_db_raw.csv` に無い / **【既出】** = 既存レビューに有り
> - **書誌◎** = 本調査中に Crossref / arXiv API / Semantic Scholar で題名・著者・会議・年を照合済み。**書誌△** = 一部のみ照合(該当箇所に「未検証」と明記)
> - **内容S** = 本調査中に検索スニペット/アブストラクトで内容を確認。**内容M** = 調査者の既有知識に基づく記述で、本調査中に本文は開いていない(レポート執筆時に原典で要再確認)
> - (a) 入力 (b) AR に何を出すか (c) いつ出すか (d) 編集・承認 (e) エラー/実行不能/不確実性の表示
> - 調査上の制約: OpenAlex は無料枠切れ、Semantic Scholar は 429 多発で、MARCER / PRogramAR の被引用リスト(forward citation)は取得できなかった(Gaps 参照)。

---

## Key Question 1: LLM/自然言語のタスク指示と、ロボット計画の AR/MR 可視化を組み合わせた論文はどれか(2022–2026)

### Takeaway
「言語(LLM)→ 計画 → AR で実行前プレビュー → ユーザが編集/承認」を一通り備えるのは、MARCER(HRI 2025)、Fang らの LLM+MR ウェイポイント生成(ICRA 2024 WS)、AURaPath(Applied Sciences 2026)、MRPilot(arXiv 2026)、KTH の AR Puppeteer 系(2025)など少数で、いずれも 2024 年以降。**エラー・実行不能・不確実性を AR 上に明示するものは X-OOHRI(HRI 2026)以外ほぼ見当たらず**、ここが明確な空白。

### Cited Findings

#### クラスタ A: LLM/言語 → AR で計画プレビュー・編集・承認(MARCER に最も近い)

- **A1. MARCER: Multimodal Augmented Reality for Composing and Executing Robot Tasks** — Bryce Ikeda, Maitrey Gramopadhye, LillyAnn Nekervis, Daniel Szafir. HRI 2025. 【既出】書誌◎ 内容S。(a) 自然言語(音声)+ AR 上の直接操作のマルチモーダル。(b) LLM がユーザの言語記述と環境コンテキストを Trigger-Action 形式の「Action Plan」に変換し、AR で提示。(c) 実行前(プレビュー)。(d) AR 上で編集・プレビュー可能。(e) エラー/不確実性表示の有無は本調査では未確認。Crossref 上の被引用数 13。なお依頼文中の題名「…Composing and Executing Rules using Natural Language」は誤りで、正式題名は上記。 — [Crossref DOI 10.1109/HRI61500.2025.10974232](https://doi.org/10.1109/HRI61500.2025.10974232); [著者ページ](https://maitreygram.github.io/publications/marcer); [UNC 学部研究アブストラクト](https://our.unc.edu/abstract/nekervis-marcer-a-multimodal-augmented-reality-system-for-composing-and-executing-robot-action-plans)
- **A2. Enabling Waypoint Generation for Collaborative Robots using LLMs and Mixed Reality** — Cathy Mengying Fang, Krzysztof Zieliński, Pattie Maes, Joe Paradiso, Bruce Blumberg, Mikkel Baun Kjærgaard. ICRA 2024 Workshop VLMNM(arXiv 2403.09308)。【新規】書誌◎ 内容S。(a) 音声またはテキスト。(b) LLM(LLMR フレームワーク上)が生成したウェイポイントと軌道を AR ヘッドセットで実環境に重畳。(c) 実行前プレビュー。(d) ウェイポイントをドラッグして直接編集でき、満足したら承認 → Unity からロボットへ送信。(e) エラー表示は確認できず。 — [arXiv:2403.09308](https://arxiv.org/abs/2403.09308)
- **A3. LLM-Based Waypoint Authoring via Augmented Reality for Human–Robot Interaction(システム名 AURaPath)** — Mohammad Hashemi, Kasra Mojallal, Saeed Mozaffari, Shahpour Alirezaee. Applied Sciences 16(20):9974, 2026. 【新規】書誌◎ 内容S。(a) 自然言語 + HoloLens 2 上の手操作。(b) UR10 のデジタルツイン周りに 6-DoF エンドエフェクタ・ウェイポイントを配置/編集。(c) デジタルツインでのプレビュー段階を挟んでから実機へストリーム。(d) 編集可。LLM は実行前に自分の解釈を確認し、「run」「confirm」を安全上重要なコマンドとして扱う。(e) 解釈確認(言語)以外のエラー可視化は未確認。 — [MDPI](https://www.mdpi.com/2076-3417/16/20/9974)
- **A4. MRPilot: Supervising and Intervening LLM-Based Multi-Robot Teams through Mixed Reality** — Xiaoran Yang, Xun Qian, Yang Zhan, Nathan Tran, Ziyi Liu, Qiao Jin. arXiv 2610.07477, 2026(プレプリント)。【既出】書誌◎ 内容S。(a) 言語プロンプト + MR 操作。(b) LLM 生成のマルチロボット計画を 2 種のビューで提示。(c) 実行前プレビュー + 実行中の監督・介入。(d) プレビューした計画から選択・修正可能(ベースラインは「プロンプトを書き直して全体やり直し」で不評)。(e) 未確認。 — [arXiv:2610.07477](https://arxiv.org/abs/2610.07477)
- **A5. LLM-Driven Augmented Reality Puppeteer: Controller-Free Voice-Commanded Robot Teleoperation** — Yuchong Zhang, Bastian Orthmann, Michael C. Welle, Jonne Van Haastregt, Danica Kragic. HCI International 2025(arXiv 2502.09142)。【新規】書誌◎ 内容S。(a) LLM 経由の音声コマンド。(b) 実ロボットに重ねた仮想カウンターパート(ゴーストロボット)。(c) 仮想ロボットが先に動き、物理ロボットが動く前にユーザが視覚確認。(d) 確認(承認)型。(e) 初版では体系的なユーザ評価なしと著者自身が記載。 — [arXiv:2502.09142](https://arxiv.org/abs/2502.09142)
- **A6. Gesture First, LLM-Assisted Voice Complement: Exploring Multimodal Robot 'Puppeteer' Teleoperation Via Virtual Counterpart in Augmented Reality**(v2 題名は "Multimodal 'Puppeteer': Exploring Robot Teleoperation Via Virtual Counterpart with LLM-Driven Voice and Gesture Interaction in Augmented Reality")— Yuchong Zhang, Bastian Orthmann, Shichen Ji, Michael Welle, Jonne Van Haastregt, Danica Kragic. arXiv 2506.13189, 2025(査読中と記載)。【新規】書誌◎ 内容S。(a) Meta Quest 3 上の手ジェスチャ + LLM 音声。(b) 仮想カウンターパートロボット。(c)(d) A5 と同様。(e) 42 名のピック&プレース実験で、ジェスチャのみ(GO)の方が信頼性・効率が高く、音声+ジェスチャ(VG)は柔軟だが遅延と認識誤りを持ち込む、という結果。言語入力の誤認識が AR 側で十分に扱われていないことを示す実証。 — [arXiv:2506.13189](https://arxiv.org/abs/2506.13189)
- **A7. Multimodal Grounding for Embodied AI via Augmented Reality Headsets for Natural Language Driven Task Planning** — Selma Wanna, Fabian Parra, Robert Valner, Karl Kruusamäe, Mitch Pryor. arXiv 2304.13676, 2023. 【新規】書誌◎ 内容S(アブストラクトのみ)。(a) 自然言語駆動のタスク計画。(b)「AR ヘッドセットが EAI エージェントと人間オペレータ間の情報交換を仲介する」とあるが、何を表示するかはアブストラクトからは不明。(c)(d) 未確認。(e) プロンプト頑健性と「潜在的な落とし穴」の分析を含む(AR 上のエラー表示かは不明)。LLM×AR ヘッドセットの最初期(2023 年 4 月)の例。 — [arXiv:2304.13676](https://arxiv.org/abs/2304.13676)
- **A8. An AR-assisted Human-Robot Interaction System for Improving LLM-based Robot Control** — Ziyue Zhao, Shanhe Lou, Runjia Tan, Chen Lv. IEEE CIS-RAM 2024. 【新規】書誌◎(DOI は接頭部 10.1109/cis-ram61939 までしか取得できず未完全)内容**未検証**(題名から LLM ロボット制御を AR で補助する系と判断。詳細は要原典確認)。 — [Crossref 検索](https://api.crossref.org/works?rows=1&query.bibliographic=An+AR-assisted+Human-Robot+Interaction+System+for+Improving+LLM-based+Robot+Control)
- **A9. An augmented reality-enhanced large language model-based interactive system for human-robot collaboration** — Hao Xu, Linzhen Zhou, Xuanchen Zhou, Pai Zheng. Robotics and Computer-Integrated Manufacturing(Crossref の発行年は 2027 表記、SSRN 版 2026)。【新規】書誌◎ 内容**未検証**(題名のみ)。 — [DOI 10.1016/j.rcim.2026.103396](https://doi.org/10.1016/j.rcim.2026.103396)
- **A10. Robi Butler: Multimodal Remote Interaction with a Household Robot Assistant** — Anxing Xiao, Nuwan Janaka, Tianrun Hu, Anshul Gupta, Kaixin Li, Cunjun Yu ほか 1 名. ICRA 2025(arXiv 2409.20548)。【新規】書誌◎ 内容M。(a) 遠隔ユーザが MR ヘッドセット越しに言語 + 指差しジェスチャで家庭用ロボットへ指示(LLM/VLM が解釈)。(b)(c)(d)(e) 計画プレビューや承認ステップの有無は未確認。「言語+ポインティングの MR 指示」の代表例。 — [arXiv:2409.20548](https://arxiv.org/abs/2409.20548)

- **A11. ORCESTRA: VLM-driven Visual Robot programming in Mixed Reality** — Ivan Snegirev, Elizaveta Semenyakina, Mikhail Konenkov ほか. arXiv 2608.00775, 2026(プレプリント)。【新規】書誌△(Semantic Scholar の検索結果 1 件のみで確認、著者全員・会議は未検証)内容**未検証**(題名から、VLM 駆動の MR ビジュアルロボットプログラミング。MARCER に近い可能性が高く、優先して原典確認すべき)。 — [arXiv:2608.00775](https://arxiv.org/abs/2608.00775)

#### クラスタ B: 言語を主入力としないが、AR でゴール/能力/信号を扱う 2023–2026 の近縁(LLM/VLM 利用を含む)

- **B1. Explainable OOHRI: Communicating Robot Capabilities and Limitations as Augmented Reality Affordances** — Lauren W. Wang, Mohamed Kari, Parastoo Abtahi. HRI 2026(arXiv 2601.14587)。【既出】書誌◎ 内容S(題名・既存レビュー)。(a) AR 上のオブジェクト指向操作。(b) ロボットの「できること/できないこと」を AR アフォーダンスとして提示。(e) **実行不能・制約を AR で説明する数少ない例**。RoboVisAR を引用。 — [arXiv:2601.14587](https://arxiv.org/abs/2601.14587)
- **B2. GhostObjects: Instructing Robots by Manipulating Spatially Aligned Virtual Twins in Augmented Reality** — Lauren W. Wang, Parastoo Abtahi. UIST Adjunct 2025(arXiv 2508.11022)。【既出】書誌◎ 内容S。(a) 実物に位置合わせした仮想ツイン(ゴーストオブジェクト)を AR で動かしてゴールを指定。(b) ゴースト物体=目標配置。(c) 実行前。(d) 配置し直しで編集。RoboVisAR を引用。 — [arXiv:2508.11022](https://arxiv.org/abs/2508.11022)
- **B3. SiSCo: Signal Synthesis for Effective Human-Robot Communication Via Large Language Models** — Shubham Sonawani, Fabian Weigend, Heni Ben Amor. IROS 2024(arXiv 2409.13927)。【新規】書誌◎ 内容M。LLM がロボット→人の視覚信号を合成する(方向が逆: 人の指示の可視化ではなく、ロボットの意図/要求の可視化)。表示媒体の詳細(投影/モニタ)は要原典確認。RoboVisAR を引用。 — [arXiv:2409.13927](https://arxiv.org/abs/2409.13927)
- **B4. Prompting an Embodied AI Agent: How Embodiment and Multimodal Signaling Affects Prompting Behaviour** — Tianyi Zhang, Colin Au Yeung, Emily Aurelia, Yuki Onishi, Neil Chulpongsatorn, Jiannan Li ほか 1 名. CHI 2025. 【新規】書誌◎ 内容**未検証**(RoboVisAR を引用している CHI 論文。身体性のある AI エージェントへのプロンプト行動の研究)。 — [DOI 10.1145/3706598.3713110](https://doi.org/10.1145/3706598.3713110)
- **B5. Integrating Large Language Models with Multimodal Virtual Reality Interfaces to Support Collaborative Human-Robot Construction Work** — Somin Park, Carol C. Menassa, Vineet R. Kamat. arXiv 2404.03498, 2024. 【新規】書誌◎ 内容S。AR ではなく **VR**。LLM チャット + VR。ユーザがチャット UI の「Approval」ボタンを押すとロボットが作業開始する承認ゲートを持つ。 — [arXiv:2404.03498](https://arxiv.org/abs/2404.03498)
- **B6. Explainable Human-Robot Training and Cooperation with Augmented Reality** — Chao Wang, Anna Belardinelli, Stephan Hasler ほか. CHI EA 2023. 【既出】(詳細は既存レビュー参照)。同グループの **LaMI: Large Language Models for Multi-Modal Human-Robot Interaction**(Chao Wang, Stephan Hasler, Daniel Tanneberg, Felix Ocker, Frank Joublin, Antonello Ceravola ほか 2 名, CHI EA 2024)は LLM 駆動のマルチモーダル HRI(AR ではない)。【新規】書誌◎ — [DOI 10.1145/3613905.3651029](https://doi.org/10.1145/3613905.3651029); [arXiv:2401.15174](https://arxiv.org/abs/2401.15174)

#### クラスタ C: LLM 以前の「音声/言語 + AR プレビュー + 承認」(直接の先祖)

- **C1. Increasing Robot Autonomy via Motion Planning and an Augmented Reality Interface** — Juan David Hernández, Shlok Sobti, Anthony Sciola, Mark Moll, Lydia E. Kavraki. IEEE RA-L 5(2), 2020. 【新規】書誌◎ 内容M。(a) HoloLens 上で高レベル要求(音声・視線等)を指定。(b) モーションプランナが出した計画を AR で提示。(c) 実行前。(d) ユーザが確認してから実行、再計画可。(e) 要原典確認。 — [DOI 10.1109/LRA.2020.2967280](https://doi.org/10.1109/LRA.2020.2967280)
- **C2. Comparison of Multimodal Heading and Pointing Gestures for Co-Located Mixed Reality Human-Robot Interaction** — Dennis Krupke, Frank Steinicke, Paul Lubos, Yannick Jonetzko, Michael Görner, Jianwei Zhang. IROS 2018. 【新規】書誌◎ 内容M。(a) 頭部方向/指差し + 音声コマンドでピック&プレース対象を指定。(b) 仮想ロボットによる動作プレビュー。(c) 実行前。(d) 音声で確認して実行。 — [DOI 10.1109/IROS.2018.8594043](https://doi.org/10.1109/IROS.2018.8594043)
- **C3. Mixed Reality as a Bidirectional Communication Interface for Human-Robot Interaction** — Eric Rosen, David Whitney, Michael Fishman, Daniel Ullman, Stefanie Tellex. IROS 2020. 【新規】書誌◎ 内容M。(a) 言語 + ジェスチャによる物体参照。(b) ロボットが曖昧さ解消のため MR で対象候補を可視化して問い返す。(e) **参照の不確実性を MR で人に返す**双方向型。 — [DOI 10.1109/IROS45743.2020.9340822](https://doi.org/10.1109/IROS45743.2020.9340822)
- **C4. A Comparison of Visualisation Methods for Disambiguating Verbal Requests in Human-Robot Interaction** — E. Sibirtseva ほか. RO-MAN 2018. 【既出】言語要求の曖昧さ解消を AR(HMD/投影)とモニタで比較(詳細は既存レビュー参照)。
- **C5. An Augmented Reality Motion Planning Interface for Robotics** — Courtney Hutton, Nicholas Sohre, Bobby Davis, Stephen Guy, Evan Suma Rosenberg. IEEE VR 2019. 【新規】書誌◎ 内容**未検証**(題名のみ。AR での動作計画インタフェース)。 — [DOI 10.1109/VR.2019.8798010](https://doi.org/10.1109/VR.2019.8798010)

### Inferences
- MARCER に最も近い順(言語→AR プレビュー→編集→承認の充足度で判断): **A2 Fang ら ≈ A3 AURaPath > A4 MRPilot > A5/A6 Puppeteer > A7 Wanna ら**。ただし A2/A3 は「ウェイポイント/軌道」レベル、MARCER は「Trigger-Action ルール」レベル、MRPilot は「マルチロボットのタスク計画」レベルで、可視化対象の抽象度が違う。「ルール(条件+行動)を言語で作り AR で見せる」のは実質 MARCER のみ。
- 表示タイミングはほぼ全て「実行前プレビュー」。実行中/実行後の差分提示は MRPilot(監督・介入)程度。
- A6 の結果(音声は遅延と認識誤りを持ち込む)は、「言語入力の誤解釈を AR 側でどう見せるか」が未解決であることの実証的根拠として使える。
- LLM の誤解釈・実行不能・不確実性を AR で可視化する設計は、X-OOHRI(能力/限界)と C3/C4(参照曖昧性、LLM 以前)に限られる。CoGround の「エラー表示」はこの空白を狙える。

### Gaps
- 依頼文にあった「Gong "LLM + AR"」「Chat-with-robot AR」「HoloLens + ChatGPT robot」に該当する特定論文は同定できなかった(検索でヒットせず)。存在を否定するものではない。
- A7, A8, A9, A10, B3, B4, C5 は表示内容・承認フローの詳細を本文で確認していない。
- VAM-HRI ワークショップ 2024–2026 の LLM×AR 論文は検索で見つけられなかった(ワークショップ論文は索引されにくい)。
- 検索結果に arXiv 2609.31138「Evaluating the Impact of Adaptive Extended Reality on Human-Robot Interaction Across the Reality-Virtuality Continuum」と、arXiv 2507.01206(NASA SUITS 向け LLM 駆動 AR システムの報告)が現れたが、前者は arXiv API で照合できず**未検証**、後者は題名・著者未確認。

---

## Key Question 2: AR エンドユーザロボットプログラミングにはどんなシステムがあるか(trigger-action / PbD / ウェイポイント / ブロック型)

### Takeaway
AR ロボットプログラミングは (i) ウェイポイント/軌道オーサリング、(ii) Trigger-Action・条件ベース、(iii) 空間的ビジュアルプログラミング(ブロック/フロー)、(iv) AR 支援 PbD、(v) 動作意図の提示、に大別でき、PRogramAR は (ii) の代表。どれも入力は手操作・GUI が中心で、言語入力は MARCER 以降。実行不能の提示は「到達不能ウェイポイントの色変化」「仮想ロボットでのシミュレーション」程度にとどまる。

### Cited Findings

#### クラスタ D: Trigger-Action / 条件ベースの AR オーサリング(PRogramAR に最も近い)

- **D1. PRogramAR: Augmented Reality End-User Robot Programming** — Bryce Ikeda, Daniel Szafir. ACM THRI 13(1), Article 15, 2024. 【新規】書誌◎ 内容S。(a) AR 上の手操作(言語なし)。(b) Trigger-Action プログラミングを AR の視覚フィードバックと組み合わせる(トリガ領域・アクション)。(c) 作成時(実行前)。(d) AR 上で編集。18〜83 歳の 17 名が協働タスク用にロボットをプログラム。Crossref 被引用 25。 — [DOI 10.1145/3640008](https://doi.org/10.1145/3640008); [NSF PAR 公開版](https://par.nsf.gov/biblio/10510874)
- **D2. RoboVisAR: Immersive Authoring of Condition-based AR Robot Visualisations** — Rasmus S. Lunding, (Lystbæk), Feuchtner, (Pfeuffer), Grønbæk ら(DBLP キー LundingLFPG024。**著者全員の正確な綴りは未検証**)。HRI 2024. 【新規】書誌◎ 内容M。(a) HMD 上の没入オーサリング(コード不要)。(b) ロボットプログラムそのものではなく、「どの条件のときにどの AR 可視化(経路・領域等)を出すか」を、記録したロボット動作のタイムライン上で作る。(c) 実行中に条件成立で表示。(d) 可視化ルールを編集。(e) 状態に応じた表示切替が主眼。 — [DOI 10.1145/3610977.3634972](https://doi.org/10.1145/3610977.3634972)
- **D3. ARTHUR: Authoring Human-Robot Collaboration Processes with Augmented Reality using Hybrid User Interfaces** — Rasmus Lunding, Sebastian Hubenschmid, Tiare Feuchtner, Kaj Grønbæk. Virtual Reality 29, 2025(arXiv 2501.02304)。【新規】書誌◎ 内容M。AR HMD と別デバイスを組み合わせたハイブリッド UI で、人ロボット協働プロセス(アクション・条件・フィードバック)を現場でオーサリング。RoboVisAR の後継。 — [arXiv:2501.02304](https://arxiv.org/abs/2501.02304)
- **D4. Situated Live Programming for Human-Robot Collaboration** — Emmanuel Senft, Michael Hagenow, Robert Radwin, Michael Zinn, Michael Gleicher, Bilge Mutlu. UIST 2021. 【新規】書誌◎ 内容M。(a) タブレット上のカメラ映像への注釈。(b) 実シーン映像に重ねた高レベルアクションと Trigger-Action プログラム。(c)(d) その場で作成・即実行・修正。PRogramAR が引用。 — [DOI 10.1145/3472749.3474773](https://doi.org/10.1145/3472749.3474773)
- **D5. Trigger-Action Programming for Personalising Humanoid Robot Behaviour** — Nicola Leonardi, Marco Manca, Fabio Paternò, Carmen Santoro. CHI 2019. 【新規】書誌◎ 内容M。AR ではない(Web の TAP エディタ)。ロボット向け Trigger-Action の基礎。PRogramAR が引用。 — [DOI 10.1145/3290605.3300675](https://doi.org/10.1145/3290605.3300675)
- **D6. V.Ra: An In-Situ Visual Authoring System for Robot-IoT Task Planning with Augmented Reality** — Yuanzhi Cao, Zhuangying Xu, Fan Li, Wentao Zhong, Ke Huo, Karthik Ramani. DIS 2019(CHI EA 2019 版もあり)。【新規】書誌◎ 内容M。(a) 手持ち AR デバイスで空間を歩いて指定。(b) 移動ロボットの経路と IoT 機器との相互作用タスク列(条件・タイマ等のロジック含む)。(c) 実行前。(d) 編集可。RoboVisAR が引用。 — [DOI 10.1145/3322276.3322278](https://doi.org/10.1145/3322276.3322278)
- **D7. GhostAR: A Time-space Editor for Embodied Authoring of Human-Robot Collaborative Task with Augmented Reality** — Yuanzhi Cao ほか. UIST 2019. 【既出】人の動作を記録したゴーストに対してロボット協働動作を時空間編集。PRogramAR・RoboVisAR の双方が引用。 — [DOI 10.1145/3332165.3347902](https://doi.org/10.1145/3332165.3347902)

#### クラスタ E: ウェイポイント/軌道オーサリングと仮想ロボットプレビュー

- **E1. Robot Programming Through Augmented Trajectories in Augmented Reality** — C. P. Quintero ほか. IROS 2018. 【既出】HoloLens で軌道を作成・プレビュー・修正(詳細は既存レビュー)。
- **E2. End-User Robot Programming Using Mixed Reality** — S. Y. Gadre, E. Rosen, G. Chien, E. Phillips, S. Tellex, G. Konidaris. ICRA 2019. 【既出】MR でウェイポイントを置き、仮想アームで動作をプレビューしてから実行。
- **E3. Interactive Robot Programing Using Mixed Reality** — M. Ostanin, A. Klimchik. IFAC-PapersOnLine, 2018. 【新規】書誌◎ 内容M。HoloLens で点・幾何経路を指定し、ホログラムのロボットでシミュレーション後に実行。 — [DOI 10.1016/j.ifacol.2018.11.517](https://doi.org/10.1016/j.ifacol.2018.11.517)
- **E4. Human-robot interaction for robotic manipulator programming in Mixed Reality** — Mikhail Ostanin, Stanislav Mikhel, Alexey Evlampiev, Valeria Skvortsova, Alexandr Klimchik. ICRA 2020. 【新規】書誌◎ 内容M。E3 の発展(複数ロボット・経路タイプ・ホログラムでの事前確認)。 — [DOI 10.1109/ICRA40945.2020.9196965](https://doi.org/10.1109/ICRA40945.2020.9196965)
- **E5. Spatial programming for industrial robots based on gestures and Augmented Reality** — Jens Lambrecht, Jörg Krüger. IROS 2012. 【新規】書誌◎ 内容M。ジェスチャ + 手持ち AR でポーズ・軌道を定義し、仮想ロボットでプログラムをシミュレーション。PRogramAR が引用。 — [DOI 10.1109/IROS.2012.6385900](https://doi.org/10.1109/IROS.2012.6385900)
- **E6. Augmented reality-assisted robot programming system for industrial applications** — S. K. Ong, A. W. W. Yew, N. K. Thanigaivel, A. Y. C. Nee. Robotics and Computer-Integrated Manufacturing, 2020. 【新規】書誌◎ 内容M。手持ちポインタ + AR で経路定義、仮想ロボットで検証。PRogramAR が引用。 — [DOI 10.1016/j.rcim.2019.101820](https://doi.org/10.1016/j.rcim.2019.101820)
- **E7. An Augmented Reality Interface for Human-Robot Interaction in Unconstrained Environments** — Sonia Mary Chacko, Vikram Kapila. IROS 2019. 【新規】書誌◎ 内容M。スマホ AR で仮想マーカを置いてピック&プレース位置を指定。PRogramAR・RoboVisAR の双方が引用。 — [DOI 10.1109/IROS40897.2019.8967973](https://doi.org/10.1109/IROS40897.2019.8967973)
- **E8. Toward Programming a Collaborative Robot by Interacting with Its Digital Twin in a Mixed Reality Environment** — Andoni Rivera-Pinto, Johan Kildal, Elena Lazkano. International Journal of Human–Computer Interaction, 2023. 【新規】書誌◎ 内容M。MR 上のデジタルツインを手で動かしてプログラム。 — [DOI 10.1080/10447318.2023.2221599](https://doi.org/10.1080/10447318.2023.2221599)
- **E9. Online and Offline Robot Programming via Augmented Reality Workspaces** — Yong Joon Thoo, Jérémy Maceiras, Philip Abbet, Mattia Racca, Hakan Girgin, Sylvain Calinon. arXiv 2107.01884, 2021(IEEE RAM 投稿と記載、掲載は未検証)。【新規】書誌◎ 内容M。仮想ロボット・仮想ワークスペースを使ったオンライン/オフライン教示。 — [arXiv:2107.01884](https://arxiv.org/abs/2107.01884)
- **E10. Kinetic AR: A Framework for Robotic Motion Systems in Spatial Computing** — Anna Fuste, Ben Reynolds, James Hobin, Valentin Heun. CHI EA 2020. 【新規】書誌◎ 内容M。手持ち AR でロボットの動作経路をオーサリング。RoboVisAR が引用。 — [DOI 10.1145/3334480.3382814](https://doi.org/10.1145/3334480.3382814)
- **E11. Enabling Human Robot Interaction in flexible robotic assembly lines: an Augmented Reality based software suite** — Niki Kousi, Christos Stoubos, Christos Gkournelos, George Michalos, Sotiris Makris. Procedia CIRP, 2019. 【新規】書誌◎ 内容M。HMD で移動ロボットの軌道・安全領域を表示し、作業者がナビゲーション指示・修正。 — [DOI 10.1016/j.procir.2019.04.328](https://doi.org/10.1016/j.procir.2019.04.328)
- **E12. MRREP: Mixed Reality-Based Hand-Drawn Reference Path Editing Interface for Mobile Robot Navigation** — Takumi Taki, Masato Kobayashi, Yuki Uranishi. RO-MAN 2026. 【新規】書誌◎ 内容**未検証**(題名: MR 上の手描きで移動ロボットの参照経路を編集)。前作 **MRHaD: Mixed Reality-based Hand-Drawn Map Editing Interface for Mobile Robot Navigation**(Taki, Kobayashi, Iglesius, Chiba, Shirai, Uranishi, RO-MAN 2025)。 — [DOI 10.1109/RO-MAN72286.2026.11714993](https://doi.org/10.1109/RO-MAN72286.2026.11714993); [DOI 10.1109/RO-MAN63969.2025.11217635](https://doi.org/10.1109/RO-MAN63969.2025.11217635)

- **E13. Intuitive Robot Path Planning through Augmented Reality** — M. Matour, Alexander W. Winkler. MMAR 2023. 【新規】書誌△(Semantic Scholar 検索結果のみ)内容**未検証**。 — [DOI 10.1109/MMAR58394.2023.10242522](https://doi.org/10.1109/MMAR58394.2023.10242522)
- **E14. Augmented Reality for 6-DoF Motion Recording, Preview, and Execution to Enable Intuitive Surgical Robot Control** — Murali K. Karnam, Marek Żelechowski, P. Cattin ほか. Current Directions in Biomedical Engineering, 2022. 【新規】書誌△(同上)内容**未検証**(題名どおり、AR での動作記録→プレビュー→実行)。 — [DOI 10.1515/cdbme-2022-1058](https://doi.org/10.1515/cdbme-2022-1058)

#### クラスタ F: 空間的ビジュアルプログラミング(ブロック/フロー/投影)

- **F1. Spatially Situated End-User Robot Programming in Augmented Reality** — Michal Kapinus, Vitezslav Beran, Zdenek Materna, Daniel Bambusek. RO-MAN 2019. 【新規】書誌◎ 内容M。タブレット AR で、3D 空間に配置したアクションポイントとプログラムフローを可視化・編集。 — [DOI 10.1109/RO-MAN46459.2019.8956336](https://doi.org/10.1109/RO-MAN46459.2019.8956336)
- **F2. Augmented reality spatial programming paradigm applied to end-user robot programming** — Michal Kapinus, Vítězslav Beran, Zdeněk Materna, Daniel Bambušek. Robotics and Computer-Integrated Manufacturing, 2024. 【新規】書誌◎ 内容M。F1 のジャーナル発展版。 — [DOI 10.1016/j.rcim.2024.102770](https://doi.org/10.1016/j.rcim.2024.102770)
- **F3. ARCOR2: Framework for Collaborative End-User Management of Industrial Robotic Workplaces using Augmented Reality** — Michal Kapinus, Zdeněk Materna, Daniel Bambušek, Vítězslav Beran, Pavel Smrž. arXiv 2306.08464, 2023(Journal of Intelligent and Robotic Systems 投稿と記載)。【新規】書誌◎ 内容M。F1/F2 の基盤フレームワーク。 — [arXiv:2306.08464](https://arxiv.org/abs/2306.08464)
- **F4. Interactive Spatial Augmented Reality in Collaborative Robot Programming: User Experience Evaluation** — Zdenek Materna, Michal Kapinus, Vitezslav Beran, Pavel Smrz, Pavel Zemcik. RO-MAN 2018. 【新規】書誌◎ 内容M。作業台への投影 AR + タッチで命令パラメータを設定。PRogramAR が引用。 — [DOI 10.1109/ROMAN.2018.8525662](https://doi.org/10.1109/ROMAN.2018.8525662)
- **F5. Combining Interactive Spatial Augmented Reality with Head-Mounted Display for End-User Collaborative Robot Programming** — D. Bambušek ほか. RO-MAN 2019. 【既出】PRogramAR が引用。 — [DOI 10.1109/RO-MAN46459.2019.8956315](https://doi.org/10.1109/RO-MAN46459.2019.8956315)
- **F6. PATI: a projection-based augmented table-top interface for robot programming** — Yuxiang Gao, Chien-Ming Huang. IUI 2019. 【新規】書誌◎ 内容M。卓上投影 + タッチジェスチャで、領域図形を使ったピック&プレースを指定。PRogramAR が引用。 — [DOI 10.1145/3301275.3302326](https://doi.org/10.1145/3301275.3302326)
- **F7. Simplifying Robot Programming Using Augmented Reality and End-User Development** — Enes Yigitbas, Ivan Jovanovikj, Gregor Engels. INTERACT 2021(LNCS)。【新規】書誌◎ 内容M。手持ち AR + ブロック型プログラミング、AR 内でのシミュレーション実行。 — [DOI 10.1007/978-3-030-85623-6_36](https://doi.org/10.1007/978-3-030-85623-6_36)
- **F8. Augmented reality for industrial robot programmers: Workload analysis…** — Stadler ほか 2016. 【既出】。

#### クラスタ G: AR 支援の実演教示(PbD/LfD)

- **G1. ARC-LfD: Using Augmented Reality for Interactive Long-Term Robot Skill Maintenance via Constrained Learning from Demonstration** — Matthew B. Luebbers, Connor Brooks, Carl L. Mueller, Daniel Szafir, Bradley Hayes. ICRA 2021. 【新規】書誌◎ 内容M。学習済みスキルのキーフレームと制約を AR で可視化し、ユーザが制約を編集してスキルを保守。PRogramAR が引用。 — [DOI 10.1109/ICRA48506.2021.9561844](https://doi.org/10.1109/ICRA48506.2021.9561844)
- **G2. RAMPA: Robotic Augmented Reality for Machine Programming by DemonstrAtion** — Fatih Dogangun, Serdar Bahar, Yigit Yildirim, Bora Toprak Temir, Emre Ugur, Mustafa Doga Dogan. IEEE RA-L 2025(arXiv 2410.13412)。【新規】書誌◎ 内容M。AR ヘッドセット上で実演の記録・軌道の可視化・学習結果のプレビューを現場で行う PbD。 — [arXiv:2410.13412](https://arxiv.org/abs/2410.13412)
- **G3. Augmented Reality interface to verify Robot Learning** — M. Diehl ほか. RO-MAN 2020. 【既出】学習結果を AR で検証。

#### クラスタ H: 動作意図・状態・デバッグの AR 可視化(計画を「見せる」側の基礎)

- **H1. Communicating Robot Motion Intent with Augmented Reality** — Walker, Hedayati, Lee, Szafir. HRI 2018. 【既出】 — [DOI 10.1145/3171221.3171253](https://doi.org/10.1145/3171221.3171253)
- **H2. Communicating and controlling robot arm motion intent through mixed-reality head-mounted displays** — Rosen ほか. IJRR 2019. 【既出】 — [DOI 10.1177/0278364919842925](https://doi.org/10.1177/0278364919842925); [arXiv:1708.03655](https://arxiv.org/abs/1708.03655)
- **H3. Advancing the Design of Visual Debugging Tools for Roboticists** — Bryce Ikeda, Daniel Szafir. HRI 2022. 【新規】書誌◎ 内容M。ロボットのデバッグ向け可視化(AR を含む)の設計研究。RoboVisAR が引用。 — [DOI 10.1109/HRI53351.2022.9889392](https://doi.org/10.1109/HRI53351.2022.9889392)
- **H4. AR-supported Human-Robot Collaboration: Facilitating Workspace Awareness and Parallelized Assembly Tasks** — Rasmus S. Lunding, Mathias N. Lystbæk, Tiare Feuchtner, Kaj Grønbæk. ISMAR 2023. 【新規】書誌◎ 内容M。協働組立でロボットの作業領域・次動作を AR 提示。 — [DOI 10.1109/ISMAR59233.2023.00123](https://doi.org/10.1109/ISMAR59233.2023.00123)
- **H5. Investigating AR Assistance for Human-Robot Collaboration in Mould Assembly "in the Wild"** — Rasmus Skovhus Lunding, Tiare Feuchtner, Kaj Grønbæk. HRI 2025. 【新規】書誌◎ 内容**未検証**(現場での AR 支援評価)。 — [DOI 10.1109/HRI61500.2025.10973920](https://doi.org/10.1109/HRI61500.2025.10973920)
- **H6. RCLL-AR: Augmented Reality Support for Understanding Autonomous Processes in the RoboCup Logistics League** — Jan-Heliodor Tscherko, Peter Kohout, Philipp Fleck, Matteo Tschesche, Alexander Ferrein, Gerald Steinbauer-Wagner ほか 1 名. ISMAR 2025. 【新規】書誌◎ 内容**未検証**(自律プロセス理解のための AR)。 — [DOI 10.1109/ISMAR67309.2025.00045](https://doi.org/10.1109/ISMAR67309.2025.00045)
- **H7. Indicating Robot Vision Capabilities with Augmented Reality** — Hong Wang, Ridhima Phatak, James Ocampo, Zhao Han. International Journal of Social Robotics, 2026(arXiv 2511.03550)。【新規】書誌◎ 内容M(題名)。(e) ロボットの視覚能力(見える範囲)を AR で示す=能力・限界の可視化。 — [arXiv:2511.03550](https://arxiv.org/abs/2511.03550)
- **H8. Communicating via Augmented Reality for Human-Robot Teaming in Field Environments** — Christopher Reardon, Kevin Lee, John G. Rogers, Jonathan Fink. SSRR 2019. 【新規】書誌◎ 内容M。屋外チーミングでロボットの計画・探索情報を AR 共有。 — [DOI 10.1109/SSRR.2019.8848971](https://doi.org/10.1109/SSRR.2019.8848971)
- **H9. Learning Visualization Policies of Augmented Reality for Human-Robot Collaboration** — (Chandan, Zhang ら。著者は**未検証**)CoRL 2022 と記憶、arXiv 2211.07028。【新規】書誌△。同グループの **ARROCH**(ICRA 2021)は【既出】。 — [arXiv:2211.07028](https://arxiv.org/abs/2211.07028)
- **H10. Projection-Aware Task Planning and Execution for Human-in-the-Loop Operation of Robots in a Mixed-Reality Workspace** — Chakraborti ほか. IROS 2018. 【既出】 — [著者 PDF](https://yochan-lab.github.io/papers/files/papers/projection-aware.pdf)
- **H11. Making robots understandable: Augmented reality for enhancing situational awareness in human–robot co-located environments** — Sonia Chacko, Vikram Kapila. Empathic Computing, 2026. 【新規】書誌◎ 内容**未検証**。 — [DOI 10.70401/ec.2026.0016](https://doi.org/10.70401/ec.2026.0016)
- **H12. Task-Based Analysis of Augmented Reality in Collaborative Robotic Programming for Manufacturing Assembly** — Medhavi Kamran, Snehesh Shrestha, Vinh Nguyen. HRI 2026 Companion. 【新規】書誌◎ 内容**未検証**。 — [DOI 10.1145/3776734.3794344](https://doi.org/10.1145/3776734.3794344)
- サーベイ: **Suzuki ら CHI 2022**、**Walker ら THRI 2023**(arXiv 2202.11249)はともに【既出】。エンドユーザロボットプログラミング全般は **A Survey on End-User Robot Programming**(Ajaykumar, Steele, Huang, ACM CSUR 2021)が PRogramAR の参照文献にあり、AR インタフェースは視点の遮蔽・奥行き知覚の問題を、音声プログラミングは騒音下の誤認識を抱えると指摘。 — [arXiv:2202.11249](https://arxiv.org/abs/2202.11249); [DOI 10.1145/3466819](https://doi.org/10.1145/3466819); [arXiv:2105.01757](https://arxiv.org/abs/2105.01757)

### Inferences
- PRogramAR に最も近いのは D4(Situated Live Programming、TAP を現場映像上で作る)、D6(V.Ra、空間的タスク+ロジック)、D7(GhostAR)、F1/F2(空間的ビジュアルプログラミング)。RoboVisAR(D2)は「ロボットプログラム」ではなく「可視化を出す条件」を作る点で別物だが、「条件 → AR 表示」のルール化という意味で CoGround のエラー表示ルール設計の直接の参考になる。
- 実行不能の扱いは、このクラスタでは「仮想ロボットで事前シミュレーションして人が目で気づく」が主流で、システム側が「なぜ不能か」を AR で説明する設計は少ない(各論文の (e) は本文未確認が多く、断定はできない)。

### Gaps
- 内容M/未検証と記した項目の (a)–(e) は原典での再確認が必要。特に (e) エラー表示の有無は、ほとんどの論文で本調査では確かめていない。
- Suzuki 研究室(Ryo Suzuki)の、言語×AR×ロボット計画に直接該当する論文は同定できなかった(B4 が同グループの可能性があるが著者末尾 1 名を未確認)。
- Suzuki 2022 / Walker 2023 サーベイの分類表を直接マイニングする作業は行っていない。

---

## Key Question 3: MARCER / PRogramAR / RoboVisAR が近縁として引用した論文と、それらを引用した後続論文

### Takeaway
PRogramAR の参照文献 85 件と RoboVisAR の 56 件は Crossref から取得でき、GhostAR と Chacko & Kapila(IROS 2019)を両者が共通に引用している。後続は RoboVisAR の被引用 12 件のみ取得でき、X-OOHRI・GhostObjects・ARTHUR・SiSCo が特に近い。MARCER の参照文献と、MARCER・PRogramAR の被引用リストは取得できなかった。

### Cited Findings
- PRogramAR(DOI 10.1145/3640008)は Crossref 上で参照文献 85 件・被引用 25 件。参照文献には、Ajaykumar ら「A survey on end-user robot programming」、Bambušek ら RO-MAN 2019(10.1109/RO-MAN46459.2019.8956315)、Chacko & Kapila IROS 2019(10.1109/IROS40897.2019.8967973)、GhostAR(10.1145/3332165.3347902)、Gadre ら ICRA 2019、Gao & Huang IUI 2019(PATI)、Kapinus ら RO-MAN 2019、Lambrecht & Krüger IROS 2012(10.1109/IROS.2012.6385900)、Leonardi ら CHI 2019(10.1145/3290605.3300675)、ARC-LfD(10.1109/ICRA48506.2021.9561844)、Materna ら RO-MAN 2018(10.1109/ROMAN.2018.8525662)、Ong ら RCIM 2020(10.1016/j.rcim.2019.101820)、Senft ら UIST 2021(10.1145/3472749.3474773)、Walker ら HRI 2018(10.1145/3171221.3171253)、Suzuki ら CHI 2022、Walker らサーベイ、Trace2TAP(10.1145/3411838)が含まれる。 — [Crossref API: 10.1145/3640008](https://api.crossref.org/works/10.1145/3640008)
- PRogramAR は LLM 計画研究として Gramopadhye & Szafir「Generating executable action plans with environmentally-aware language models」(IROS 2023, arXiv 2210.04964)と Huang, Wenlong ら(ICML 2022)を既に引用しており、MARCER(言語化)への布石が見える。 — [Crossref API: 10.1145/3640008](https://api.crossref.org/works/10.1145/3640008)
- RoboVisAR(DOI 10.1145/3610977.3634972)は Crossref 上で参照文献 56 件・被引用 9 件(Semantic Scholar では 12 件)。参照文献に V.Ra(10.1145/3322276.3322278)、GhostAR(10.1145/3332165.3347902)、Chacko & Kapila IROS 2019、Kinetic AR(10.1145/3334480.3382814)、Ikeda & Szafir HRI 2022(10.1109/hri53351.2022.9889392)、Lunding ら ISMAR 2023(10.1109/ISMAR59233.2023.00123)、Rosen ら IJRR(10.1177/0278364919842925)を含む。 — [Crossref API: 10.1145/3610977.3634972](https://api.crossref.org/works/10.1145/3610977.3634972)
- RoboVisAR を引用する論文(Semantic Scholar、12 件): Explainable OOHRI(HRI 2026)、GhostObjects(UIST Adjunct 2025)、ARTHUR(Virtual Reality 2025)、SiSCo(IROS 2024)、Indicating Robot Vision Capabilities with AR(IJSR)、RCLL-AR(ISMAR 2025)、ReachVox: Clutter-Free Reachability Visualization for Robot Motion Planning in Virtual Reality(Hauck, Abdlkarim, Dudley ら, ISMAR 2025, arXiv 2508.11426)、Prompting an Embodied AI Agent(CHI 2025)、Lunding ら HRI 2025、"That's Iconic! Designing Augmented Reality Iconic Gestures…"(Zhu ら, IROS 2025)、Yu & Venture(RO-MAN 2026)、Rodrigues ら(Computers & Graphics 2026、オーサリングツールの系統的レビュー)。 — [Semantic Scholar: RoboVisAR](https://api.semanticscholar.org/graph/v1/paper/DOI:10.1145/3610977.3634972/citations?fields=title,year,venue)
- MARCER(DOI 10.1109/HRI61500.2025.10974232)は Crossref 上で被引用 13 件だが、参照文献リストは Crossref に登録されていない(0 件)。 — [Crossref API: MARCER](https://api.crossref.org/works/10.1109/hri61500.2025.10974232)

### Inferences
- GhostAR と Chacko & Kapila(スマホ AR のピック&プレース指定)は PRogramAR・RoboVisAR の共通祖先で、「AR 空間オーサリング」系の必須引用とみなせる。
- RoboVisAR の後続のうち、X-OOHRI(能力・限界の AR アフォーダンス)、ReachVox(到達可能性の可視化、VR)、Wang ら(視覚能力の AR 提示)は「ロボットの限界/実行不能を空間的に見せる」方向で、CoGround のエラー表示に最も関係する。

### Gaps
- MARCER の参照文献リストは取得できなかった(Crossref 未登録、arXiv 版も API で見つからず。依頼文に書かれがちな arXiv 番号は**未検証**)。
- MARCER(被引用 13)と PRogramAR(被引用 25)を引用する後続論文の題名一覧は取得できなかった(Semantic Scholar が空応答/429、OpenAlex は無料枠切れ)。Google Scholar か API キー付き OpenAlex での再取得が必要。
- PRogramAR 参照文献のうち DOI のみで題名が返らなかった約 40 件は個別に解決していない。

---

## Key Question 4: AR を使わない言語駆動システムで、実行前に計画をユーザへ見せて検証させるもの

### Takeaway
画面 GUI・シミュレーション・画像・フローチャートで LLM の計画を提示して確認/修正させる系は HRI/CHI/UIST に多数あり(Alchemist、Cocobo、ImageInThat、VeriPlan、RoboCritics、SHRIMP、Vocal Sandbox など)、形式検証や「批評器」によるエラー提示はむしろ非 AR 側の方が進んでいる。AR 側はこれらのエラー提示を空間に持ち込めていない。

### Cited Findings
- **Alchemist: LLM-Aided End-User Development of Robot Applications** — Ulas Berk Karli, Juo-Tung Chen, Victor Nikhil Antony, Chien-Ming Huang. HRI 2024. 【新規】書誌◎ 内容M。自然言語 → LLM がロボットコード生成、画面 UI とシミュレーション表示で確認・反復。 — [DOI 10.1145/3610977.3634969](https://doi.org/10.1145/3610977.3634969)
- **Cocobo: Exploring Large Language Models as the Engine for End-User Robot Programming** — Yate Ge, Yi Dai, Run Shan, Kechun Li, Yuanda Hu, Xiaohua Sun. IEEE VL/HCC 2024(arXiv 2407.20712)。【新規】書誌◎ 内容M。自然言語とフローチャートを行き来して LLM 生成プログラムを確認・編集。 — [arXiv:2407.20712](https://arxiv.org/abs/2407.20712)
- **Vocal Sandbox: Continual Learning and Adaptation for Situated Human-Robot Collaboration** — Jennifer Grannen, Siddharth Karamcheti, Suvir Mirchandani, Percy Liang, Dorsa Sadigh. CoRL 2024(arXiv 2411.02599)。【新規】書誌◎ 内容M。音声指示に対し、画面 GUI に計画・解釈を表示してユーザが確認、教示で拡張。 — [arXiv:2411.02599](https://arxiv.org/abs/2411.02599)
- **Sketching Robot Programs On the Fly**(Tabula)— David Porfirio, Laura Stegner, Maya Cakmak, Allison Sauppé, Aws Albarghouthi, Bilge Mutlu. HRI 2023. 【新規】書誌◎ 内容M。音声 + 地図上スケッチ → プログラム合成、タブレットで確認。続報 **Understanding On-the-Fly End-User Robot Programming**(Stegner, Hwang, Porfirio, Mutlu, DIS 2024)。 — [DOI 10.1145/3568162.3576991](https://doi.org/10.1145/3568162.3576991); [DOI 10.1145/3643834.3660721](https://doi.org/10.1145/3643834.3660721)
- **CoFrame: A System for Training Novice Cobot Programmers** — Andrew Schoen, Nathan White, Curt Henrichs, Amanda Siebert-Evenstone, David Shaffer, Bilge Mutlu. HRI 2022(THRI 版 2026: White, Schoen, Sullivan, Mutlu)。【新規】書誌◎ 内容M。言語入力ではないが、3D シミュレーション上で専門家の観点に基づく問題点(エラー・改善点)をプログラムにフィードバック表示する代表例。 — [DOI 10.1109/HRI53351.2022.9889345](https://doi.org/10.1109/HRI53351.2022.9889345); [DOI 10.1145/3860630](https://doi.org/10.1145/3860630)
- **VoicePilot: Harnessing LLMs as Speech Interfaces for Physically Assistive Robots** — Akhil Padmanabha, Jessie Yuan, Janavi Gupta, Zulekha Karachiwalla, Carmel Majidi, Henny Admoni ほか 1 名. UIST 2024(arXiv 2404.04066)。【新規】書誌◎ 内容M。LLM 音声 IF(食事支援)。確認・中断などの設計指針。視覚的計画プレビューは無い側の対照例。 — [arXiv:2404.04066](https://arxiv.org/abs/2404.04066)
- **Understanding Large-Language Model (LLM)-powered Human-Robot Interaction** — Callie Y. Kim, Christine P. Lee, Bilge Mutlu. HRI 2024(arXiv 2401.03217)。【新規】書誌◎。LLM 搭載ロボットとの対話のユーザ研究(計画 UI ではなく背景文献)。 — [arXiv:2401.03217](https://arxiv.org/abs/2401.03217)
- **Text2Motion: From Natural Language Instructions to Feasible Plans** — Kevin Lin, Christopher Agia, Toki Migimatsu, Marco Pavone, Jeannette Bohg. Autonomous Robots 2023(arXiv 2303.12153)。【新規】書誌◎ 内容M。言語 → 幾何的実行可能性を検証した計画(ユーザ向け UI ではなく、実行可能性チェック側の代表)。 — [arXiv:2303.12153](https://arxiv.org/abs/2303.12153)
- **LATTE: LAnguage Trajectory TransformEr** — Arthur Bucker, Luis Figueredo, Sami Haddadin, Ashish Kapoor, Shuang Ma, Sai Vemprala ほか 1 名. arXiv 2208.02918, 2022. 【新規】書誌◎ 内容M。言語で既存軌道を修正(軌道レベルの言語編集)。 — [arXiv:2208.02918](https://arxiv.org/abs/2208.02918)
- **Code3**(Justin Huang, Maya Cakmak, HRI 2017)【新規】書誌◎ 内容M。移動マニピュレータ向けのエンドユーザプログラミング一式(非 AR)。 — [DOI 10.1145/2909824.3020215](https://doi.org/10.1145/2909824.3020215)
- 既存レビューに収録済みで本観点に該当するもの(詳細は `master_db_raw.csv` 参照): **TidyBot**(arXiv 2305.05658、ID は調査者の記憶で未検証)、**ImageInThat**(HRI 2025、画像操作で指示・結果画像で確認)、**GenComUI**(CHI 2025、生成的視覚補助)、**VeriPlan**(CHI 2025、形式検証 + LLM)、**RoboCritics**(HRI 2026、専門家知識に基づく批評器)、**SHRIMP**(2026、計画の反復改良)、**PerceptTwin**(2026、シーン再構成上での計画検証)、**Polaris**(HRI 2024、ゴール指向 EUP)、**KnowNo**(CoRL 2023、不確実なとき人に尋ねる)、**Interactive Task Planning with Language Models**、**Prospection**(2019、言語から将来予測で解釈可能な計画)、**DALL-E-Bot**、**iRoPro**。 — [既存レビュー内の Polaris arXiv:2403.13988](https://arxiv.org/abs/2403.13988)
- VR での例: Park ら(B5、承認ボタン)。 — [arXiv:2404.03498](https://arxiv.org/abs/2404.03498)

### Inferences
- 非 AR 側では「検証器/批評器が見つけた問題を計画に紐づけて提示する」(VeriPlan、RoboCritics、CoFrame)設計が既にあり、これを AR の空間表示(ウェイポイント・ゾーン・ゴースト上)に写像することが CoGround の新規性になり得る。AR 側でそれに相当するのは X-OOHRI のみ。
- 「言語 → 画像/シミュレーションで結果を見せる」(ImageInThat、PerceptTwin、Alchemist)は AR プレビューの画面版と見なせ、比較対象(ベースライン)候補。

### Gaps
- 依頼文の「SayCan の確認付き派生」「LLM plan verification UI」に該当する特定論文は、既存レビュー収録分以外には同定していない。SayCan(arXiv 2204.01691)、Inner Monologue(arXiv 2207.05608)、Yell At Your Robot(arXiv 2403.12910)、ChatGPT for Robotics(arXiv 2306.17582)は関連が深いが、本調査では arXiv API で照合できず、ID は調査者の記憶によるため**未検証**。
- 内容M の項目は UI の詳細(何を・いつ・どう編集)を原典で再確認していない。
