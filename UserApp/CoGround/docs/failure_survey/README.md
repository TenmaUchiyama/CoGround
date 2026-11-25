# ロボットの失敗の種類 — 体系的な文献調査（2026-11-21）

ロボットがタスクに失敗する原因には、どんな種類があるか。先行研究の分類を、再現できる手順で集め直した。

- 採用した論文の一覧：[included.csv](included.csv)（98 本。分類・確認の程度・どの経路で見つかったか付き）
- 検索に使ったスクリプトと検索語：[scripts/](scripts/)、[data/](data/)

---

## 1. 結論：失敗の種類（統合分類）

前回の 8 種類に、今回の調査で **I（期待のずれ）** を加えて 9 種類にした。

| # | 種類 | 例 | 代表的な論文（✓＝分類を提案している論文） | 採用数 |
|---|---|---|---|---|
| A | **ロボットの身体的制約** | 腕が届かない、重くて持てない、体が大きくて通れない、そのスキルがない | ✓Kwon 2018、✓Brandao 2021、✓Robot Arms Too Short? 2025、LLM3 2024、ホームロボットの段差・通路幅 2026 | 16 |
| B | **外部環境の問題** | 物が邪魔で経路がない、遮蔽、照明・反射、床の摩擦、人混み、物の想定外のふるまい | ✓External faults 2019、✓環境ベースの失敗説明 ICRA 2024、✓Honig 2024（Incompatibility）、✓Khalastchi & Kalech 2018（exogenous events）、✓環境の複雑さと失敗要因 2026 | 25 |
| C | **知覚・グラウンディングの誤り** | 違う物を選ぶ、存在しない物を前提にする、指示と意味がずれた動作 | ✓AHA、✓RoboFAC、✓EAI、I-FailSense 2026 | 18 |
| D | **計画の誤り** | 手順の抜け・順序違い、前提条件の見落とし、最終状態が目的と違う | ✓EAI、✓REFLECT、✓FailRecOnt、CAPE 2024、PerceptTwin 2026 | 24 |
| E | **実行・制御の誤り** | 掴み損ね、滑り落ち、位置のずれ、接触の力加減の失敗 | ✓AHA、✓RoboFAC、✓Sentinel 2024、✓VLA の接触失敗 2026 | 26 |
| F | **機器の故障**（ハード・ソフト） | センサ・モータ・電源・通信の故障、ソフトのバグ | ✓Carlson & Murphy 2004/2005、✓Steinbauer 2013、✓Khalastchi & Kalech 2018、✓Honig 2018 | 29 |
| G | **人間側の誤り・指示の問題** | あいまいな指示、実行できない指示、人の言い間違い・勘違い | ✓CLARA 2023、✓HRI の人間のエラー 2025、KnowNo 2023、Honig 2018 | 23 |
| H | **規範・安全の違反**（できたが、してはいけなかった） | 危険な操作、社会的に不適切なふるまい、ルール違反 | ✓Tian & Oviatt 2021、✓Giuliani 2015、✓SafeMind 2025、SafeAgentBench 2024 | 30 |
| I | **期待のずれ**（ロボットは設計通り動いたが、人の想定と違った） | 「できると思っていたのにできない」「そういう意味ではなかった」 | ✓Tolmeijer 2020（Expectation failures）、✓メンタルモデルのずれ 16 種類 2026 | 2 |

採用数は、その種類を扱う論文の数。1 本の論文が複数の種類にまたがるので、合計は 98 を超える。

### 今回の調査で分かったこと

- **B（外部環境）には、確立した概念がある。** 「内部の部品は正常なのに、環境とのやりとりで失敗する」ことを **external fault（外部故障）** と呼ぶ研究の流れがある。Steinbauer 2013 と Bonn-Rhein-Sieg 大学の研究が中心で、サービスロボットの実演から 4 種類の外部故障を挙げている。外乱、不完全な知覚、計画オペレータの不備、行動の連鎖の 4 つ（要旨で確認）。
- **B は、分類の定番論文の中にも項目として入っていた（本文で確認）。** Honig 2024 は「Incompatibility（稼働環境やほかのエージェントと合わない）」を失敗の種類の 1 つにしている。例は、階段で動けない、特定の床で使えない、ペットを怖がらせる。Khalastchi & Kalech 2018 は、interaction related fault の原因として、外部の出来事（exogenous events）を挙げている。
- **A と B は、動作計画の説明研究で切り分けられている。** 同じ「計画が見つからない」でも、原因の説明の仕方が 2 つある。「どの物をどこへ動かせば解けるか」が環境ベースの説明（ICRA 2024）。「腕があと何 cm 長ければ解けるか」がロボットの設計ベースの説明（RO-MAN 2025）。
- **I（期待のずれ）は、ほかの分類では抜けやすい。** Tolmeijer 2020 は失敗を Design / System / Expectation / User の 4 種類に分ける。その中の Expectation failure は、ロボットは正しく動いたのに人の期待と違ったという失敗。
- **分野ごとの偏りは前回の見立て通りだった。** マニピュレーション系（AHA、RoboFAC など）は C・D・E が細かい。HRI 系（Honig、Tian & Oviatt）は F・G・H が中心。A・B・H をまとめて扱う分類は、今回も見つからなかった。

---

## 2. 調査方法

### 2.1 何を探したか

- **問い**：ロボットのタスク失敗について、原因や種類の分類を提案している研究、または使っている研究。
- **含める**：
  - 物理ロボット、またはシミュレーション上の身体を持つエージェントが対象であること。
  - 失敗・故障・誤り・実行不能・安全違反を、2 種類以上に分けて扱っていること。
  - 査読論文か arXiv。年は問わない。
- **除く**：
  - 失敗の検出だけで、種類を分けない手法（成功／失敗の 2 値など）。
  - 部品単位の故障診断の信号処理（ベアリングや減速機の振動分類など）。ただし故障の種類をまとめたレビューは含める。
  - 手術ロボット、自動運転、ロボットを使わない LLM エージェント。
  - 接客の失敗が顧客心理に与える影響だけを調べたマーケティング研究。

### 2.2 手順

| 段階 | やったこと | 件数 |
|---|---|---|
| ① 出発点 | 分類を提案している代表論文 12 本を選んだ（[seed_titles.json](data/seed_titles.json)） | 12 |
| ② 引用をたどる（1 段目） | 12 本の参考文献と被引用を、OpenAlex からすべて取得 | 2,476 |
| ③ キーワード検索 | OpenAlex で 30 個の検索語、各 200 件（[grid.json](data/grid.json)） | 4,274 |
| ④ arXiv 検索 | 新しいプレプリントを拾うため、arXiv API で 12 + 8 個の検索語 | 502 + 395 |
| ⑤ 引用をたどる（2 段目） | ①〜④で新しく見つかった中心論文 10 本で、②を繰り返した | 1,347 |
| 重複を除いた合計 | タイトルで重複を除いた | **約 7,700** |
| ⑥ 機械的な絞り込み | タイトル・要旨に「ロボット系の語」と「失敗系の語」を含むもの | 約 2,100 |
| ⑦ タイトルで判定 | 私が全件のタイトルを読んで判定 | → 約 165 |
| ⑧ 要旨で判定 | 要旨を読み、2.1 の基準で採否を決めた | **98 本採用**（分類を提案 44、使用 54） |
| ⑨ 本文で確認 | 中心論文の分類名を本文で確認 | 一部のみ（2.4 参照） |

採用した 98 本のうち、各経路で見つかった本数は次の通り（重なりあり）。キーワード 76、被引用 52、arXiv 36、参考文献 25、手作業で追加 3。

### 2.3 漏れがないかの確認

**飽和の確認。** 引用の 2 段目（⑤）で新しく 891 本が見つかった。そのうち基準に合ったのは 5 本ほどで、新しい分類の軸は「外部故障」の系統だけだった。arXiv の追加検索でも、新しく 283 本のうち採用は 3 本だった。新しい分類は出てきにくくなっている。

**既知の論文との照合。** 前回の調査や以前の文献レビューで知っていた関連論文 25 本が、検索結果に入っていたかを調べた。

- 入っていた：20 本（80%）。
- 入っていなかった：5 本。
  - DESPITE 2026、Defining Boundaries 2024、LAP 2024、Model Reconciliation 2026：LLM の実行可能性に関する新しい arXiv 論文。OpenAlex への登録が遅れやすい。このうち 3 本は手作業で一覧に加えた。
  - Brooks の博士論文（ロボットの失敗の分類）：学位論文は OpenAlex に入りにくい。

**絞り込みの漏れ。** 最初の機械的な絞り込みが厳しすぎて、"To Err Is Robot" や KnowNo のような関連論文を落としていた。条件を緩めて、追加の 747 本もタイトルで判定し直した。

### 2.4 限界

- **データベース**：OpenAlex と arXiv だけを使った。Scopus、IEEE Xplore、ACM DL は直接検索していない。キーワード検索は各語の上位 200 件だけを見た。
- **判定者が 1 人**：タイトル・要旨の判定は私 1 人で行った。2 人目による確認はしていない。
- **本文を確認できたのは一部だけ**：
  - 本文で分類名を確認できたのは次の 6 本。AHA、RoboFAC（v3）、Tian & Oviatt、Tolmeijer、Khalastchi & Kalech、Honig 2024。後ろの 4 本は Zotero の全文キャッシュで確認した。
  - REFLECT、CLARA、Honig 2018 は一部を確認した。
  - Bonn-Rhein-Sieg の external faults の博士論文は、リポジトリがボット確認で止まり、要旨までの確認になる。
  - 一覧の `verification` 列に、論文ごとの確認の程度を書いた。
- **言語**：英語の検索語だけで探した。韓国語の論文が 1 本見つかったが、日本語の論文は探していない。

---

## 3. 種類ごとの主な論文

全 98 本は [included.csv](included.csv) にある。ここでは、分類を提案している論文を中心に挙げる。

### A. ロボットの身体的制約
- **Kwon, Huang & Dragan, "Expressing Robot Incapability," HRI 2018**：重すぎて持てないなどの能力の限界を、動きで伝える。[DOI](https://doi.org/10.1145/3171221.3171276)
- **Brandao ほか, "Towards providing explanations for robot motion planning," ICRA 2021**：動作計画の失敗の説明を、コスト・制約・パラメータ・ロボットの設計・環境に分ける。[DOI](https://doi.org/10.1109/icra48506.2021.9562003)
- **"Robot Arms Too Short? Explaining Motion Planning Failures using Design Optimization," RO-MAN 2025**：「腕のリンクが足りない」のように、ロボットの設計を最小限変える形で失敗を説明する。[DOI](https://doi.org/10.1109/ro-man63969.2025.11217709)
- **"Basic Research on Movement Failure Condition for Home Service Robots," ICAROB 2026**：14 台のロボットで、段差・通路幅・家具下の隙間を試した。体の大きさが移動を最も制限した（A と B の境目）。[DOI](https://doi.org/10.5954/icarob.2026.os7-9)

### B. 外部環境の問題
- **Steinbauer, "A Survey about Faults of Robots Used in RoboCup," 2013**：ハードとソフトの故障だけでは、自律ロボットの不具合を説明しきれないと示した。[DOI](https://doi.org/10.1007/978-3-642-39250-4_31)
- **"Improving the Reliability of Service Robots in the Presence of External Faults," 2019**（博士論文）：環境とのやりとりで起きる外部故障を 4 種類に分ける（外乱、不完全な知覚、計画オペレータの不備、行動の連鎖）。[OpenAlex](https://openalex.org/W2944976407)
- **"Using naive physics for unknown external faults in robotics," 2011**：物の物理的性質から、予期しない外部故障の原因を推論する。
- **"Generating Environment-based Explanations of Motion Planner Failure," ICRA 2024**：失敗の原因になった環境中の物と、それをどこへ動かせば解けるかを示す。[DOI](https://doi.org/10.1109/icra57147.2024.10611577)
- **"Classification of Exogenous Anomalies and Self-Diagnosis in Autonomous Robots," 2019**：外からの妨げ（exogenous anomaly）を分類し、対処法を学ぶ。[DOI](https://doi.org/10.1109/chilecon47746.2019.8987980)
- **"An Exploratory Study of Environmental Complexity Profiles and Failure Factors in Service Robot Field Demonstrations," 2026**：9 件の実証実験から、環境の複雑さを物理・社会・システムの 3 面で評価した。環境が複雑になるほど、主な失敗要因がハードの故障から知覚・通信の限界へ移る。[DOI](https://doi.org/10.5762/kais.2026.27.10.795)
- **"From Hardware to Autonomy," Machines 2026**：過酷な環境のストレス要因を 5 種類に分け、ハードの劣化からミッションの失敗までの伝わり方を整理した。[DOI](https://doi.org/10.3390/machines14111274)
- **"What Matters for Designing Reliable Systems," ERAS 2026**：自律型水中ロボット Sentry の約 450 回の運用から、失敗の原因・条件・影響の分類を作った。[DOI](https://doi.org/10.1109/eras69098.2026.11564256)
- **Murphy & Hershberger, "Classifying and recovering from sensing failures," AAAI 1996**：知覚の失敗の原因に、センサの故障・ソフトの誤り・環境の変化・誤った期待を挙げる。

### C・D・E. 知覚・計画・実行の誤り（主にマニピュレーション）
- **AHA, ICLR 2025**：7 種類（本文で確認）。[arXiv](https://arxiv.org/abs/2410.00371)
- **RoboFAC, 2025**：3 層・6 種類（v3 の本文で確認）。[arXiv](https://arxiv.org/abs/2505.12224)
- **REFLECT, CoRL 2023**：execution failure と planning failure に分ける。[arXiv](https://arxiv.org/abs/2306.15724)
- **Embodied Agent Interface, NeurIPS 2024**：hallucination、affordance、手順の抜け・余分・順序違い。[DOI](https://doi.org/10.52202/079017-3188)
- **Sentinel, 2024**：erratic failure（動作が不安定になる）と task progression failure（安定しているが課題が進まない）に分ける。[arXiv](https://arxiv.org/abs/2410.04640)
- **"What Can One Sentence Fix?," 2026**：VLA の失敗を 4 種類に分ける。一文の指示で直せるのは execution misalignment だけだった。[arXiv](https://doi.org/10.48550/arxiv.2608.29967)
- **"Demystifying When and Why VLAs Fail in Contact-Rich Tasks," 2026**：precision failure と force failure に分ける。[arXiv](https://arxiv.org/abs/2608.01402)
- **LabRobFail, 2026**：化学実験室で、5 カテゴリ・11 種類の失敗。[arXiv](https://doi.org/10.48550/arxiv.2607.23704)
- **"Unsupervised Discovery of Failure Taxonomies from Deployment Logs," 2025**：失敗の種類を、ログから自動で見つける。[arXiv](https://arxiv.org/abs/2506.06570)

### F. 機器の故障
- **Carlson & Murphy, T-RO 2005 / Carlson, Murphy & Nelson, ICRA 2004**：physical（effector、sensor、control、power、communications）と human に分ける。15 台のデータでは control system の故障が最も多かった（32%）。[DOI](https://doi.org/10.1109/robot.2004.1302508)
- **Khalastchi & Kalech, "On Fault Detection and Diagnosis in Robotic Systems," ACM CSUR 2018**：ロボットの故障検出・診断のサーベイ。[DOI](https://doi.org/10.1145/3146389)（本文で確認）
  - 故障を **hardware / software / interaction related** の 3 つに分ける（Fig. 1）。
  - hardware は低レベルの知覚と動作の部品の故障。software は誤ったアルゴリズムか、正しいアルゴリズムの誤った実装で、知覚・意思決定・行動の実行に影響する。
  - interaction related は、ロボット内部の故障か **外部の出来事（exogenous events）** から生じる。B の根拠になる。
  - 締め切りに間に合わないなどの timing の故障は、3 つのどの層でも起こりうる。
- **"Results of the Survey: Failures in Robotics and Intelligent Systems," 2017**：研究者へのアンケート。ハードの問題が最も多い原因だった（要約からの読み取りで、数字は未確認）。[arXiv](https://arxiv.org/abs/1708.07379)

### G. 人間側の誤り・指示の問題
- **CLARA, RA-L 2023**：指示を certain / ambiguous / infeasible に分ける。
- **KnowNo, CoRL 2023**：LLM の計画が不確かなとき、人に聞く。
- **"The role of human error in human robot interaction," 2025**：製造現場の HRI で、人間のエラーの分類を整理した。[DOI](https://doi.org/10.1016/j.procs.2025.01.295)
- **"Classification of Causes of Errors in the Human-Robot System," 2018**：人とロボットのシステムでのエラーの原因を 5 グループに分ける。[DOI](https://doi.org/10.24218/jrmer.2018.26)

### H. 規範・安全の違反
- **Giuliani ほか, Frontiers 2015**：エラーの場面を social norm violation と technical failure の 2 種類に分ける。[DOI](https://doi.org/10.3389/fpsyg.2015.00931)
- **Tian & Oviatt, ACM THRI 2021**：social error を 5 カテゴリ・30 種類に分ける。各カテゴリは、短い対話で起きるものと長期の関係で起きるものに分かれている。[DOI](https://doi.org/10.1145/3439720)（本文で確認）
  - E1 共感・感情の反応の破綻（感情の認識ミス、不適切な感情表現など）
  - E2 社会的スキルの不足（社会的な文脈の認識ミス、**社会規範の違反または過剰な遵守**、決まった手順に従わないなど）
  - E3 ユーザーの誤解（ユーザーの知識や**意図の推定ミス**、共同注意への応答ミスなど）
  - E4 コミュニケーション機能の不足（無関係な返答、話者交替のずれ、関与を保てないなど）
  - E5 協働・向社会性の破綻（**プライバシーの侵害**、相手の評判を傷つける、公平さを保てないなど）
- **SafeMind, 2025**：危険が生じる段階（タスクの理解・環境の知覚・高レベルの計画・低レベルの動作）と、制約の種類（事実・因果・時間）を分ける。[arXiv](https://doi.org/10.48550/arxiv.2509.25885)
- **SafeAgentBench 2024、AGENTSAFE 2025、IS-Bench 2025、SafetyALFRED 2026**：家庭内の危険な作業のベンチマーク。
- **"The Role of Social Norms in HRI: A Systematic Review," 2025**：69 本のレビュー。[DOI](https://doi.org/10.1145/3722120)

### I. 期待のずれ
- **Tolmeijer ほか, "Taxonomy of Trust-Relevant Failures and Mitigation Strategies," HRI 2020**：[DOI](https://doi.org/10.1145/3319502.3374793)（本文で確認）
  - まず「誰の行動が信頼を損ねたか」（システムかユーザーか）で分け、次に失敗を 4 種類に分ける（Table 1）。

    | 種類 | 設計通りに動いたか | 振り返って、その動きでよかったか | 例 |
    |---|---|---|---|
    | **Design** | はい | いいえ | 命令が直感的でなく、機能が使われない |
    | **System**（hardware / software） | いいえ | — | 理由なく部屋の真ん中で止まる、スキャナの故障 |
    | **Expectation**（commission / omission） | はい | はい | 充電のために対話の途中で動き出す（commission）、ユーザーが期待した動作をしない（omission） |
    | **User**（intentional / unintentional） | ユーザーの行動 | — | ロボットへのいたずら（intentional）、**ロボットの通り道に立つ**（unintentional） |

  - 失敗は連鎖する。たとえば Design failure（動作を説明しない設計）が Expectation failure を生む。Expectation failure は unintentional な User failure にもつながる。
  - 対処法も種類ごとに整理している。説明、謝罪、修理、代替案の提示、ユーザーの訓練など。
- **"A Taxonomy of Mental Model Mismatches for HRI," ACM THRI 2026**：人の頭の中のロボット像と、実際のロボットとのずれを、Sense–Plan–Act に沿って 16 種類に分ける（sensing 7、planning 5、acting 4）。[DOI](https://doi.org/10.1145/3846186)

### 横断的な分類・サーベイ
- **Honig & Oron-Gilad, Frontiers 2018**：technical failure と interaction failure に分ける（本文で確認）。
- **Honig ほか, IJSR 2024（2022 年オンライン公開）**：家庭用ロボットの Amazon レビュー 10,072 件から、繰り返し現れる 119 の失敗を見つけた。これを 12 種類にまとめ、3 カテゴリ（Technical / Interaction / Service）とあわせて分類した（本文で確認）。種類とカテゴリは別の軸で、同じ種類が複数のカテゴリにまたがる。
  - 12 種類：
    - Task completion（作業を終えられない、引っかかる）
    - Robustness & resilience（壊れる、動かなくなる、性能が不安定）
    - User effort（手間がかかる、見張りが必要）
    - **Incompatibility（稼働環境やほかのエージェントと合わない。階段で動けない、特定の床で使えない、ペットを怖がらせる、警報を鳴らす）**
    - Design（欲しい機能がない、ゴミ箱が小さい）
    - Task completion method（作業は終えるが、動き方がおかしい・遅い）
    - Market value（価格に見合わない）
    - **Safety（壁にぶつかる、物を巻き込む、階段から落ちる、人や動物を怖がらせる）**
    - Charging & battery（充電・電池）
    - User confusion（表示がわかりにくく、ユーザーが誤解する）
    - Service quality（サポート、プライバシー）
    - Connection issues & updates（接続・更新）
  - Technical が最も多く、失敗を書いたレビューの 74% に含まれていた（Interaction 49%、Service 37%）。星の評価を最も下げたのは Robustness & resilience だった。
  - **Incompatibility は B（外部環境）の、Safety は H（安全）の、実データでの根拠になる。**
- **"Safe Embodied AI for Long-horizon Tasks," 2026**：grounding → planning → policy → execution の層をまたいで、誤りが積み重なることを整理した。

---

## 4. CoGround への示唆

- **ユーザーが挙げた 2 つは、どちらも先行研究に足場がある。** 「物理的制約」は A で、「腕が短い」説明（RO-MAN 2025）が最も近い。「外部環境」は B で、external fault の概念と環境ベースの説明（ICRA 2024）が使える。
- **A と B は、「何を変えれば成功するか」で区別できる。** ロボットを変えるなら A（届かない、持てない）。環境を変えるなら B（物をどかす、置き場所を変える）。2 つの説明研究は、この区別をそのまま方法にしている。CoGround の AR プレビューで、「その場で直せる失敗」として見せ方を分ける根拠になる。
- **家庭のルールは H に入る。** 「実行できるか」と「してよいか」を別の軸で扱う研究（DESPITE、SafeMind）がある。
- **I（期待のずれ）は、事前のプレビューで減らせる種類の失敗。** Tolmeijer の Expectation failure は「ロボットは正しいが、人が想定と違うと感じる」もの。CoGround が見せる After の状態は、このずれを実行前に表に出す仕組みと説明できる。

## 5. 未確認・次にやること

- external faults の博士論文（4 種類の外部故障）は、まだ要旨しか確認していない。B の中心になる論文なので、Zotero に入れて本文を確認したい。
- REFLECT / RoboFail の 8 種類は図にしかなく、まだ読めていない。
- 2 人目による判定や、Scopus での追加検索はしていない。論文に書くなら、この 2 点を限界として明記する必要がある。
