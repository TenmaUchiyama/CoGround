# 04 「依頼の一部はできない」をロボット・プランナがどう伝え、どう解決させるか（物体ごと・その場での表示）

調査日：2026-11-22。対象設計：AR の事後環境プレビューで、動かせる物体はゴール位置に表示し、家庭ルールに違反して計画に入れられない物体は実位置に残して違反理由のラベルを付け、ユーザーがその場で解決する。

**確認の程度（全体に共通）**
- 書誌（題名・著者・会場・年・DOI）は、特記のない限り Crossref API または arXiv API で今回照合した。照合できなかった項目は「書誌未確認」と書いた。
- 内容の要約は、X-OOHRI・MARCER・Text2Interaction・Wang ほか 2023・Moore ほか 2023・Zielinski ほか 2025・iTeach・Wozniak ほか 2023・Eifler & Hoffmann 2020 は今回取得した要旨・プロジェクトページに基づく。**それ以外は本文・要旨を今回取得しておらず、既知の内容の要約である**。細部が怪しい箇所は「未確認」と明記した。引用前に本文確認が必要。
- 既存の `docs/rule_survey/`（130 本、ルールの「中身」の調査）と重なる論文（Safety Chip、RoboGuard、ASIMOV、TidyBot、Briggs & Scheutz 2015、Sprute 2019）は、ここでは「違反をどう伝え・解決するか」の観点だけ書いた。
- OpenAlex は無料枠が尽きて使えず、arXiv API も途中で制限された。ACM DL・IEEE Xplore は直接検索していない。

---

## KQ1. AR/XR でロボットの能力・不可能・認識結果を物体に付けて示す研究

### Takeaway
「できない理由を物体に付けた AR タグで示し、解決策を選ばせる」研究は X-OOHRI（HRI 2026）がほぼ唯一の直接の先行例で、扱うのはロボットの物理的な限界（届かない・隠れている等）である。家庭ルール・規範の違反を物体ごとに AR ラベルで示す研究は、今回の検索では見つからなかった。周辺には、意図・軌道の予告、制約の可視化と編集、認識結果の可視化と修正、到達可能性の可視化がある。

### Cited Findings

**直接の先行例**

1. **Explainable OOHRI: Communicating Robot Capabilities and Limitations as Augmented Reality Affordances** — Lauren W. Wang, Mohamed Kari, Parastoo Abtahi. HRI 2026. DOI 10.1145/3757279.3785569 / arXiv 2601.14587.
   - 扱う「できない」：ロボットの限界（robot limits）。プロジェクトページの例は「届かない（blinds の棒が out of reach）」「隠れた籠（occluded basket）」。家庭ルール・社会規範・ユーザーの好みへの言及は、要旨・プロジェクトページにはない。— [arXiv 要旨](https://arxiv.org/abs/2601.14587)、[プロジェクトページ](https://xoohri.github.io)
   - 検出：VLM で物体の性質とロボットの限界をオブジェクト指向の構造に符号化し、アクションモジュールが実行可能性を検証する。— [プロジェクトページ](https://xoohri.github.io)。依頼文にある「開発者が書いた決定木で物理的な実行可能性を判定」は、今回取得できた要旨・プロジェクトページからは**確認できなかった**（本文未取得）。
   - 伝え方：視覚的シグニファイア、ラジアルメニュー、色分け、explanation tag。物体の仮想ツインを直接操作する。物体単位で空間に固定されている。— [arXiv 要旨](https://arxiv.org/abs/2601.14587)
   - 解決：限界が生じると色分けとタグを更新し、任意の解決策（例：Auto＝籠を引き出して入れて戻す）を提示。ユーザーがプレビューして確定すると ROS2 に送る。ユーザー調査で「ロボットの限界の正確なメンタルモデル」「mixed-initiative な解決」を報告。— [プロジェクトページ](https://xoohri.github.io)
   - 参加者数 14、ロボットは Stretch 3 という記述は二次要約サイトのみで見た（**未確認**）。色の意味・タグの文面・タグの位置は取得できた範囲では不明。

**AR でロボットの計画・意図・内部状態を示す（不可能そのものは扱わない）**

2. **Projection-Aware Task Planning and Execution for Human-in-the-Loop Operation of Robots in a Mixed-Reality Workspace** — Chakraborti, Sreedharan, Kulkarni, Kambhampati. IROS 2018. [DOI 10.1109/IROS.2018.8593830](https://doi.org/10.1109/iros.2018.8593830)。HoloLens でロボットの意図（これから使う物体への注釈など）を環境に投影し、投影できること自体を計画に組み込む。不可能の説明ではなく意図の曖昧さの低減が目的。物体単位・空間固定。解決操作の詳細は未確認。
3. **Communicating Robot Motion Intent with Augmented Reality** — Walker, Hedayati, Lee, Szafir. HRI 2018. [DOI 10.1145/3171221.3171253](https://doi.org/10.1145/3171221.3171253)。ドローンの移動意図を AR の経路点・矢印などで予告する設計を比較。不可能は扱わない。
4. **Communicating and controlling robot arm motion intent through mixed-reality head-mounted displays** — Rosen, Whitney, Phillips, Chien, Tompkin, Konidaris, Tellex. IJRR 2019. [DOI 10.1177/0278364919842925](https://doi.org/10.1177/0278364919842925)。腕の計画軌道を MR HMD で実空間に重ね、衝突するかどうかをユーザーが実行前に判断する。物理的な失敗（衝突）の事前発見を人に任せる形。
5. **Transparent Robot Behavior Using Augmented Reality in Close Human-Robot Interaction** — Bolano, Juelg, Roennau, Dillmann. RO-MAN 2019. [DOI 10.1109/RO-MAN46459.2019.8956296](https://doi.org/10.1109/ro-man46459.2019.8956296)。計画した動作と、ロボットが認識した作業空間の占有・衝突予測を AR で示す（細部は未確認）。
6. **Explainable Human-Robot Training and Cooperation with Augmented Reality** — Chao Wang, Belardinelli, Hasler, Stouraitis, Tanneberg, Gienger. arXiv 2302.01039（2023、CHI EA 2023 と思われるが会場は未確認）。[arXiv](https://arxiv.org/abs/2302.01039)。AR の設計要素で、(1) 教示時にロボットが何を理解したか、(2) 新しい課題の計画を実行前に人が検証、(3) 支援中の意図、を示す 3 例。計画の事前検証という点で対象設計に近い。
7. **Head-Mounted Augmented Reality for Explainable Robotic Wheelchair Assistance** — Zolotas, Elsdon, Demiris. IROS 2018. [DOI 10.1109/IROS.2018.8594002](https://doi.org/10.1109/iros.2018.8594002)。および **Towards Explainable Shared Control using Augmented Reality** — Zolotas, Demiris. IROS 2019. [DOI 10.1109/IROS40897.2019.8968117](https://doi.org/10.1109/iros40897.2019.8968117)。車椅子の共有制御が「なぜ操作に介入したか」を、障害物の強調や予測経路の AR 表示で説明する。安全制約による介入を、原因の物体に固定した表示で説明する例。
8. **Descriptive and Prescriptive Visual Guidance to Improve Shared Situational Awareness in Human-Robot Teaming** — Tabrez, Luebbers, Hayes. AAMAS 2022. [DOI 10.65109/ware7854](https://doi.org/10.65109/ware7854)（Crossref 登録の DOI）。AR で「状態の見立てを示す（descriptive）」と「推奨行動を示す（prescriptive）」を比較。規範ではなく不確実性下の助言。
9. **Augmented Reality-Based Explainable AI Strategies for Establishing Appropriate Reliance and Trust in Human-Robot Teaming** — Luebbers, Tabrez, Hayes. 著者サイトのファイル名から VAM-HRI 2022 ワークショップと推定（会場は**未確認**）。[著者 PDF](https://m-luebbers.github.io/pdfs/vamhri22.pdf)。上記 2 種の誘導に加え、視覚的な反実仮想説明、ロボットによる正当化（justification）を提案する。
10. **RoboVisAR: Immersive Authoring of Condition-based AR Robot Visualisations** — R. S. Lunding, M. S. Lunding, Feuchtner, Petersen, Grønbæk, Suzuki. HRI 2024. [DOI 10.1145/3610977.3634972](https://doi.org/10.1145/3610977.3634972)。ロボットのデータを条件付きで AR 表示する可視化を、その場で作る道具。「条件を満たしたときだけ表示する」という考え方が、違反時だけラベルを出す設計に対応する。

**制約・ルールを AR で見せて編集する**

11. **ARC-LfD: Using Augmented Reality for Interactive Long-Term Robot Skill Maintenance via Constrained Learning from Demonstration** — Luebbers, Brooks, Mueller, Szafir, Hayes. ICRA 2021. [DOI 10.1109/ICRA48506.2021.9561844](https://doi.org/10.1109/icra48506.2021.9561844)。教示で学んだ技能のキーフレームと制約を AR で実空間に示し、ユーザーがその場で制約を追加・修正して技能を保守する。制約を空間に固定して可視化・編集する代表例。
12. **MARCER: Multimodal Augmented Reality for Composing and Executing Robot Tasks** — Ikeda, Gramopadhye, Nekervis, Szafir. HRI 2025. [DOI 10.1109/HRI61500.2025.10974232](https://doi.org/10.1109/hri61500.2025.10974232)。LLM が自然言語と環境の文脈からトリガー・アクション型の Action Plan を作り、AR でパラメータ設定・検証・実時間プレビューを行う。— [著者ページ](https://maitreygram.github.io/publications/marcer)。同グループのポスターは仮想の制約設定、デジタルツインでのプレビュー、Zone Trigger を挙げる。— [UNC ポスター要旨](https://our.unc.edu/abstract/nekervis-marcer-a-multimodal-augmented-reality-system-for-composing-and-executing-robot-action-plans)。**ルール同士の衝突をどう扱うかは、取得できた範囲では確認できなかった**。
13. **PRogramAR: Augmented Reality End-User Robot Programming** — Ikeda, Szafir. THRI 2024. [DOI 10.1145/3640008](https://doi.org/10.1145/3640008)。AR でのトリガー・アクション型ロボットプログラミング。実行可能性のフィードバックの有無は未確認。
14. **Virtual Borders: Accurate Definition of a Mobile Robot's Workspace Using Augmented Reality** — Sprute, Tönnies, König. IROS 2018. [DOI 10.1109/IROS.2018.8593615](https://doi.org/10.1109/iros.2018.8593615)。および **A Study on Different User Interfaces for Teaching Virtual Borders to Mobile Robots** — 同著者. IJSR（オンライン 2018）. [DOI 10.1007/s12369-018-0506-3](https://doi.org/10.1007/s12369-018-0506-3)。住人が AR で立入禁止の境界を描く。ユーザーが空間的なルールを作る側の研究で、違反の提示は主題でない。
15. **Interactive Policy Shaping for Human-Robot Collaboration with Transparent Matrix Overlays** — Brawer, Ghose, Candon, Qin, Roncone, Vázquez, Scassellati. HRI 2023. [DOI 10.1145/3568162.3576983](https://doi.org/10.1145/3568162.3576983)。ロボットの方策（どの物体をどう扱うか）を AR の重ね表示で物体上に見せ、ユーザーが直接修正する（細部は未確認）。

**ロボットの認識結果を見せて直させる**

16. **What You See Is (not) What You Get: A VR Framework for Correcting Robot Errors** — Wozniak, Stower, Jensfelt, Pereira. HRI 2023 Companion. [DOI 10.1145/3568294.3580081](https://doi.org/10.1145/3568294.3580081)。ロボットが実物体を検出し損ねたことを VR 内で見つけ、その場で直し、物体の軌道案も修正する。— [arXiv 2301.04919](https://arxiv.org/pdf/2301.04919)
17. **Happily Error After: Framework Development and User Study for Correcting Robot Perception Errors in Virtual Reality** — 同著者. RO-MAN 2023. [DOI 10.1109/RO-MAN57019.2023.10309446](https://doi.org/10.1109/ro-man57019.2023.10309446)。56 人が VR と 2D 画面の両方で認識誤りを直す比較。— [arXiv 2306.14589](https://arxiv.org/html/2306.14589v1)
18. **iTeach: Interactive Teaching for Robot Perception using Mixed Reality** — Jishnu Jaykumar P, Salvato, Bomnale, Wang, Xiang. arXiv 2410.09072（会場不明）。[arXiv](https://arxiv.org/abs/2410.09072)。HoloLens 2 で物体検出・セグメンテーションの結果を重ねて見せ、視線と音声で失敗例に注釈し、モデルを継続的に改善する。VLM の誤認識を物体上で見せて直させる設計に最も近い。
19. **A Comparison of Visualisation Methods for Disambiguating Verbal Requests in Human-Robot Interaction** — Sibirtseva, Kontogiorgos, Nykvist, Karaoguz, Leite, Gustafson, Kragic. RO-MAN 2018. [DOI 10.1109/ROMAN.2018.8525554](https://doi.org/10.1109/roman.2018.8525554)。口頭の物体指示が曖昧なとき、ロボットの候補を HMD の AR・プロジェクタ・画面のどれで示すのがよいかを比較（結果の細部は未確認）。
20. **Robot Object Referencing through Legible Situated Projections** — Weng, Perlmutter, Nikolaidis, Srinivasa, Cakmak. ICRA 2019. [DOI 10.1109/ICRA.2019.8793638](https://doi.org/10.1109/icra.2019.8793638)。ロボットが物体を指すとき、プロジェクタで他の物体と紛れない位置に光を当てる。「どの物体の話か」を曖昧にしない配置の研究。
21. **Mixed Reality Deictic Gesture for Multi-Modal Robot Communication** — Williams, Bussing, Cabrol, Boyle, Tran. HRI 2019. [DOI 10.1109/HRI.2019.8673275](https://doi.org/10.1109/hri.2019.8673275)。ロボットが言葉と併せて MR の矢印などで対象物を指す。

**到達可能性・アフォーダンスの可視化**

22. **Shared Affordance-awareness via Augmented Reality for Proactive Assistance in Human-robot Collaboration** — Moore, Zolotas, Padir. arXiv 2312.13410（2023、work-in-progress）。[arXiv](https://arxiv.org/abs/2312.13410)。人とロボットそれぞれのアフォーダンス領域をモデル化し、行動がその領域の外にあるときに AR で助けを求める。家庭の掃除課題で議論。ユーザー調査は要旨にない。
23. **Using Mobile AR for Rapid Feasibility Analysis for Deployment of Robots: A Usability Study with Non-Expert Users** — Zielinski, Tadeja, Blumberg, Kjærgaard. IEEE RA-L 採択（arXiv 2503.14725）。[arXiv](https://arxiv.org/abs/2503.14725)。非専門家がモバイル AR で、ロボットアームが目標に届くかを設置前に調べる。22 人、10 分以内に完了。

**総説**

24. **Augmented Reality and Robotics: A Survey and Taxonomy for AR-enhanced Human-Robot Interaction and Robotic Interfaces** — Suzuki, Karim, Xia, Hedayati, Marquardt. CHI 2022. [DOI 10.1145/3491102.3517719](https://doi.org/10.1145/3491102.3517719)。AR×ロボットの設計空間の分類。
25. **Virtual, Augmented, and Mixed Reality for Human-robot Interaction: A Survey and Virtual Design Element Taxonomy** — Walker, Phung, Chakraborti, Williams, Szafir. THRI 2023. [DOI 10.1145/3597623](https://doi.org/10.1145/3597623)。仮想設計要素の分類（ロボットの状態の可視化、ロボットの理解の可視化などの区分があるはずだが、区分名は未確認）。

**AR でない「できない」の表現**

26. **Expressing Robot Incapability** — Kwon, Huang, Dragan. HRI 2018. [DOI 10.1145/3171221.3171276](https://doi.org/10.1145/3171221.3171276)。ロボットが「何をしようとして、なぜできないか」を動きで表す（持ち上げようとして上がらない、など）。AR ではないが、「何ができないか」と「なぜか」の両方を伝えるという要件を示した。

### Inferences
- X-OOHRI との違いは明確に書ける：(a) X-OOHRI の制約はロボットの物理的限界で、家庭ルール・規範・持ち主などユーザー由来の制約は（確認できた範囲で）対象外、(b) ユーザーが 1 物体ずつ命令する場面での表示であり、計画全体の事後状態プレビューの中に「動かせなかった物体」を残す表示ではない。ただし (b) は本文未確認なので断定は避ける。
- 「色分け＋物体に付けたタグ＋解決策の選択＋プレビューして確定」という X-OOHRI の構成は、ルール違反の表示にそのまま転用できる型。
- 認識結果の修正（iTeach、Wozniak ほか）は、「違反と判定されたが実は誤認識」という場合の解決手段（物体のラベル・属性を直す）の根拠になる。
- ARC-LfD・Virtual Borders・MARCER は「ユーザーが制約を作る」側、X-OOHRI は「制約に当たったことを伝える」側。両方を 1 つの流れにつないだ研究は見つからなかった。

### Gaps
- X-OOHRI の本文（決定木の有無、色の意味、タグの文面と位置、参加者数、ロボット・HMD の機種、将来課題に規範が挙がっているか）を取得できなかった（arXiv HTML は 404、PDF は容量超過）。Zotero 経由で要確認。
- 「家庭ルール違反を物体ごとに AR ラベルで示す」研究は見つからなかった。ただし検索は Web 検索数回と既知論文の照合だけで、ACM DL・IEEE Xplore の網羅検索はしていない。「ない」とは言えず「見つからなかった」に留まる。
- 把持可能性（graspability）を物体ごとに AR で示す査読論文は特定できなかった。VR の ReachVox（arXiv 2508.11426）は検索結果に出たが、書誌・内容とも未確認。
- SENSAR（Cleaver, Muhammad, Hassan, Short, Sinapov）は arXiv に存在することだけ確認。題名・年・内容は未確認のため一覧から外した。

---

## KQ2. 説明可能な計画（XAIP）：解けない・一部しか満たせない計画の説明

### Takeaway
XAIP には、「なぜこのゴールは達成できないか」を (a) 両立しないゴールの最小集合、(b) 満たせないサブゴール、(c) 何を変えれば解けるか（excuse／制約の緩和）、(d) ユーザー自身の指示文のどの部分が原因か、の形で答える手法が揃っている。伝え方はほぼすべて文章か Web UI で、物体に固定した表示はない。

### Cited Findings

27. **Why Can't You Do That HAL? Explaining Unsolvability of Planning Tasks** — Sreedharan, Srivastava, Smith, Kambhampati. IJCAI 2019. [DOI 10.24963/ijcai.2019/197](https://doi.org/10.24963/ijcai.2019/197)。解けない計画問題について、抽象化したモデルの中で「到達できないサブゴール（ランドマーク）」を特定し、ユーザーの理解水準に合わせて示す。伝え方は記号的な説明。
28. **A New Approach to Plan-Space Explanation: Analyzing Plan-Property Dependencies in Oversubscription Planning** — Eifler, Cashmore, Hoffmann, Magazzeni, Steinmetz. AAAI 2020. [DOI 10.1609/aaai.v34i06.6534](https://doi.org/10.1609/aaai.v34i06.6534)。全ゴールは満たせない（oversubscription）状況で、「なぜ性質 p を満たさないのか」に「p を満たすと q を諦めることになるから」と答える。両立しないゴールの最小集合を計算する。
29. **Plan-Space Explanation via Plan-Property Dependencies: Faster Algorithms & More Powerful Properties** — Eifler, Steinmetz, Torralba, Hoffmann. IJCAI 2020. [DOI 10.24963/ijcai.2020/566](https://doi.org/10.24963/ijcai.2020/566)。上記を時相論理で書いた性質に拡張し高速化。
30. **Explaining Soft-Goal Conflicts through Constraint Relaxations** — Eifler, Frank, Hoffmann. IJCAI 2022. [DOI 10.24963/ijcai.2022/641](https://doi.org/10.24963/ijcai.2022/641)。ソフトゴールの衝突を「どの制約をどれだけ緩めれば衝突が消えるか」で説明する。「ルールを上書きすれば動かせる」という解決策の提示に対応する。
31. **Iterative Planning with Plan-Space Explanations: A Tool and User Study** — Eifler, Hoffmann. XAIP 2020 ワークショップ（ICAPS 2020）。[arXiv 2011.09705](https://arxiv.org/abs/2011.09705)。「提案された計画はなぜ p を満たさないのか」に答える説明を組み込んだ、人が計画を繰り返し直す Web ツールとユーザー調査。
32. **Plan Explanations as Model Reconciliation: Moving Beyond Explanation as Soliloquy** — Chakraborti, Sreedharan, Zhang, Kambhampati. IJCAI 2017. [DOI 10.24963/ijcai.2017/23](https://doi.org/10.24963/ijcai.2017/23)。説明を「人が持つモデルとロボットのモデルの差を埋める最小の情報」と定式化。ユーザーが知らないルール・状態だけを伝えればよい、という考え方。
33. **Explaining Impossible High-Level Robot Behaviors** — Raman, Kress-Gazit. IEEE T-RO 2013. [DOI 10.1109/TRO.2012.2214558](https://doi.org/10.1109/tro.2012.2214558)。時相論理で書いた高水準の仕様が実現不能なとき、原因（仕様内の矛盾か、環境の振る舞いのせいか）を特定してユーザーに返す。
34. **Sorry Dave, I'm Afraid I Can't Do That: Explaining Unachievable Robot Tasks Using Natural Language** — Raman, Lignos, Finucane, Lee, Marcus, Kress-Gazit. RSS 2013. [DOI 10.15607/RSS.2013.IX.023](https://doi.org/10.15607/rss.2013.ix.023)。自然言語の指示を論理式に変換し、達成不能なとき、原因になった**ユーザー自身の文**にさかのぼって自然言語で説明する。違反ラベルに「どのルール文に当たったか」を出す設計の先行例。
35. **Coming Up With Good Excuses: What to do When no Plan Can be Found** — Göbelbecker, Keller, Eyerich, Brenner, Nebel. ICAPS 2010. [DOI 10.1609/icaps.v20i1.13421](https://doi.org/10.1609/icaps.v20i1.13421)。計画が見つからないとき、「初期状態のどこが違えば解けたか」（excuse）を求める。反実仮想型の説明。
36. **Contrastive Explanations of Plans through Model Restrictions** — Krarup, Krivic, Magazzeni, Long, Cashmore, Smith. JAIR 2021. [DOI 10.1613/jair.1.12813](https://doi.org/10.1613/jair.1.12813)。「なぜ A でなく B をしないのか」という質問を制約としてモデルに加え、その下での計画と元の計画を比べて答える。
37. **The minimum constraint removal problem with three robotics applications** — Hauser. IJRR 2014（オンライン 2013）. [DOI 10.1177/0278364913507795](https://doi.org/10.1177/0278364913507795)。動作計画が不可能なとき、取り除けば解ける制約（障害物）の最小集合を求める。「何が邪魔か」を物体単位で答える幾何側の定式化。
38. **The Emerging Landscape of Explainable Automated Planning & Decision Making** — Chakraborti, Sreedharan, Kambhampati. IJCAI 2020（サーベイ）. [DOI 10.24963/ijcai.2020/669](https://doi.org/10.24963/ijcai.2020/669)。XAIP の総説。
39. **Why and why not explanations improve the intelligibility of context-aware intelligent systems** — Lim, Dey, Avrahami. CHI 2009. [DOI 10.1145/1518701.1519023](https://doi.org/10.1145/1518701.1519023)。ルールで動くシステムについて、「なぜ」「なぜしなかったか」の説明が理解と信頼を高めることを示した HCI の基礎研究。
40. **Why and How Robots Should Say 'No'** — Briggs, Williams, Jackson, Scheutz. IJSR（オンライン 2021）. [DOI 10.1007/s12369-021-00780-y](https://doi.org/10.1007/s12369-021-00780-y)。ロボットが指示を断る理由の種類と、断り方の言語的な設計。Briggs & Scheutz 2015（"Sorry, I Can't Do That"、rule_survey に収録済み）の発展。伝え方は発話。

### Inferences
- 対象設計のラベルに載せる情報は、XAIP の 4 つの型から選べる：どのルールに当たったか（34）、何と両立しないか（28）、何を変えれば動かせるか（30、35）、ユーザーが知らない前提は何か（32）。
- 「動かせる物体は動かし、動かせない物体は残す」は、oversubscription planning の「ゴールの部分集合を満たす」と同じ構造。物体 1 個の移動をソフトゴール 1 個とみれば、Eifler らの説明がそのまま物体単位の説明になる。
- XAIP は説明の中身を作る研究で、どこにどう表示するかは扱わない。AR で物体に固定する部分は対象設計の独自部分になりうる。

### Gaps
- XAIP の説明を AR で空間に固定して表示した研究は確認できなかった（Chakraborti 2018 は意図の投影で、解けない理由の説明ではない）。
- "Explainable Planning"（Fox, Long, Magazzeni、arXiv 1709.10256 と記憶）は arXiv に著者名で存在することのみ確認。ID は未確認。
- 各手法のユーザー調査の結果（説明で理解が上がったか）は今回確認していない。

---

## KQ3. ロボットと規範・家庭ルール・ユーザーが書いた制約：違反の検出と提示

### Takeaway
LLM ロボットの制約遵守の研究は、違反の検出（時相論理での検証、LLM による判定）と自動修復（違反行動の刈り取り、再計画）が中心で、違反を住人にどう見せ、住人がどう解決するかは主題になっていない。ルール違反を作成画面上で設計者に返す例は、HRI では Porfirio ほか（UIST 2018）がある。

### Cited Findings

41. **Plug in the Safety Chip: Enforcing Constraints for LLM-driven Robot Agents** — Yang, Raman, Shah, Tellex. ICRA 2024. [DOI 10.1109/ICRA57147.2024.10611447](https://doi.org/10.1109/icra57147.2024.10611447)。自然言語の安全制約を時相論理に変換し、LLM エージェントの行動を検証して違反行動を刈り取る。違反の理由を言葉にして LLM に返し再計画させる（「違反の推論と説明」は要旨の記憶による、未確認）。説明の受け手は主に LLM で、住人向けの表示ではない。
42. **Safety Guardrails for LLM-Enabled Robots**（RoboGuard）— Ravichandran, Robey, Kumar, Pappas, Hassani. IEEE RA-L 2026. [DOI 10.1109/LRA.2026.3667488](https://doi.org/10.1109/lra.2026.3667488)。あらかじめ与えた安全ルールを LLM が現場の文脈に結び付けて時相論理の仕様にし、制御合成で計画と仕様の衝突を解く（手法の細部は記憶による、未確認）。衝突は自動で解決され、人への提示は主題でない。
43. **Generating Robot Constitutions & Benchmarks for Semantic Safety**（ASIMOV）— Sermanet, Majumdar, Irpan, Kalashnikov, Sindhwani. arXiv 2503.08663（2025）. [arXiv](https://arxiv.org/abs/2503.08663)。文章で書いた「ロボット憲法」で行動の可否を判定させるベンチマーク。出力は可否判定で、人への伝え方は扱わない。
44. **AutoRT: Embodied Foundation Models for Large Scale Orchestration of Robotic Agents** — Ahn ほか. arXiv 2401.12963（2024、ICRA 2024 VLMNM Workshop）. [arXiv](https://arxiv.org/abs/2401.12963)。プロンプトに書いた憲法的なルールで、LLM が提案した課題を拒否・選別する（細部は未確認）。拒否は裏側で行われる。
45. **CAPE: Corrective Actions from Precondition Errors using Large Language Models** — Raman, Cohen, Idrees, Rosen, Mooney, Tellex, Paulius. ICRA 2024. [DOI 10.1109/ICRA57147.2024.10611376](https://doi.org/10.1109/icra57147.2024.10611376)。行動の前提条件が満たされないとき、そのエラーを LLM に返して修正行動を出させる。物理的・手続き的な不可能を自動で修復する。人には聞かない。
46. **Text2Interaction: Establishing Safe and Preferable Human-Robot Interaction** — Thumm, Agia, Pavone, Althoff. CoRL 2024. [arXiv 2408.06105](https://arxiv.org/abs/2408.06105)。LLM がユーザーの好みを、タスク計画・動作の好み（Python コード）・安全制御器のパラメータに変換する。課題達成と満足の確率の積を最大化。83% の利用者が好みが計画に反映されたと回答（要旨）。好みを満たせない場合の提示は要旨にない。
47. **TidyBot: Personalized Robot Assistance with Large Language Models** — Wu ほか. IROS 2023 / Autonomous Robots 2023. [DOI 10.1109/IROS55552.2023.10341577](https://doi.org/10.1109/iros55552.2023.10341577)。少数の例から置き場所の好みを LLM が一般則に要約する。ルールに合わない物体をどう示すかは扱わない。
48. **Distilling and Retrieving Generalizable Knowledge for Robot Manipulation via Language Corrections**（DROC）— Zha, Cui, Lin, Kwon, Gonzalez Arenas, Zeng, Xia ほか. ICRA 2024. [DOI 10.1109/ICRA57147.2024.10610455](https://doi.org/10.1109/icra57147.2024.10610455)。実行中の言葉での訂正を、次回以降に使える知識として蓄える。解決の結果をルールとして残す流れの例。
49. **Authoring and Verifying Human-Robot Interactions**（RoVer）— Porfirio, Sauppé, Albarghouthi, Mutlu. UIST 2018. [DOI 10.1145/3242587.3242634](https://doi.org/10.1145/3242587.3242634)。対話の設計を、社会規範を表す論理式に照らしてモデル検査し、違反を作成画面上で設計者に返す。規範違反を検証して、作っている対象の該当箇所に表示する、HRI での先行例。
50. **CLARA: Classifying and Disambiguating User Commands for Reliable Interactive Robotic Agents** — Park, Lim, Lee, Park, Chang, Yu, Choi. IEEE RA-L 2024. [DOI 10.1109/LRA.2023.3338514](https://doi.org/10.1109/lra.2023.3338514)。ユーザーの指示を「明確」「曖昧」「実行不可能」に分類し、曖昧なら質問する。「できない」と「分からない」を分けて扱う例。
51. **Do As I Can, Not As I Say: Grounding Language in Robotic Affordances**（SayCan）— Ahn ほか. CoRL 2022 と記憶（arXiv 2204.01691 と記憶、**今回は書誌未確認**）. [arXiv](https://arxiv.org/abs/2204.01691)。LLM の提案を、その場で実行できるかの価値関数で重み付けする。実行可能性を計画に織り込むが、できないことを人に伝えはしない。

（重なり）rule_survey 収録の "Explaining Why Things Go Where They Go"（HRI 2026）は置き場所の理由の説明を扱うので、ラベル文面の参考になる可能性がある。今回は内容未確認。

### Inferences
- この系統は「違反を人に見せずに自動で回避する」設計が主流。対象設計の「違反した物体を見える形で残し、住人に解決を委ねる」は、これらと逆の立場をとる。家庭ルールは例外や文脈依存が多い（rule_survey の Malle ほかの整理）ので、自動で黙って落とすより住人に返すほうが妥当、という論拠は立てられる。
- Safety Chip の「違反理由の言語化」は、受け手を LLM から住人に替えれば、ラベル文面の生成に使える。
- CLARA の 3 分類は、ラベルの種類を分ける根拠になる（ルール違反／物理的に不可能／認識・指示が曖昧）。

### Gaps
- NormBank、SafeAgentBench、Housekeep は rule_survey に収録済みで、いずれもデータ・評価であり提示は扱わないため、ここでは再掲していない。
- ProgPrompt、Promptable Behaviors（Hwang ほか、CVPR 2024 と記憶）は、違反の提示・解決に関係が薄いと判断して外した。Promptable Behaviors は arXiv に著者名で存在することのみ確認。
- 「家庭ルールの衝突（ルール同士、ルールと指示）を住人にどう見せるか」を扱ったロボット研究は見つからなかった。rule_survey の Multi-user Norm Consensus などは解決アルゴリズムで、提示は不明。
- MARCER のルール衝突処理は確認できなかった（KQ1 参照）。

---

## KQ4. 混合主導の解決と部分実行：できる分はやり、残りを報告・質問する

### Takeaway
「不確かなときだけ人に聞く」「失敗の原因を説明して助けを求める」研究は多いが、伝え方は発話・文章が中心。質問や報告を対象物体に空間的に結び付ける研究は、参照の曖昧さの解消（KQ1 の 19〜21）に限られる。計画段階で「この物体だけは入れられなかった」と残す部分計画の提示は、X-OOHRI 以外に見つからなかった。

### Cited Findings

52. **Robots That Ask For Help: Uncertainty Alignment for Large Language Model Planners**（KnowNo）— Ren, Dixit, Bodrova, Singh, Tu, Brown, Xu ほか. CoRL 2023. [arXiv 2307.01928](https://arxiv.org/abs/2307.01928)。LLM プランナの次の行動の候補を conformal prediction で絞り、候補が 1 つに決まらないときだけ人に聞く。扱うのは曖昧さ。選択肢を文章で示す。
53. **Inner Monologue: Embodied Reasoning through Planning with Language Models** — Huang, Xia, Xiao, Chan, Liang, Florence, Zeng ほか. arXiv 2207.05608（CoRL 2022 と記憶）. [arXiv](https://arxiv.org/abs/2207.05608)。成功判定・場面記述・人の返答を言葉で LLM に戻し、再計画する。人への質問も言葉。
54. **REFLECT: Summarizing Robot Experiences for Failure Explanation and Correction** — Liu, Bahety, Song. CoRL 2023. [arXiv 2306.15724](https://arxiv.org/abs/2306.15724)。多感覚の記録を階層的に要約し、LLM が失敗の原因を説明して修正計画を作る。事後の説明で、文章。
55. **DoReMi: Grounding Language Model by Detecting and Recovering from Plan-Execution Misalignment** — Guo, Wang, Zha, Chen. IROS 2024. [DOI 10.1109/IROS58592.2024.10802284](https://doi.org/10.1109/iros58592.2024.10802284)。LLM が実行中に守るべき制約を生成し、VLM で違反を監視して即座に回復する。制約の検出は自動で、人には返さない。
56. **Asking for Help Using Inverse Semantics** — Tellex, Knepper, Li, Rus, Roy. RSS 2014. [DOI 10.15607/RSS.2014.X.024](https://doi.org/10.15607/rss.2014.x.024)。および **Recovering from failure by asking for help** — Knepper, Tellex, Li, Roy, Rus. Autonomous Robots 2015. [DOI 10.1007/s10514-015-9460-1](https://doi.org/10.1007/s10514-015-9460-1)。組立中に失敗したロボットが、人に誤解されにくい依頼文（どの部品をどうしてほしいか）を生成する。物理的な失敗、発話、対象物を言葉で特定。
57. **Interactive Visual Grounding of Referring Expressions for Human-Robot Interaction** — Shridhar, Hsu. RSS 2018. [DOI 10.15607/RSS.2018.XIV.028](https://doi.org/10.15607/rss.2018.xiv.028)。指示された物体が曖昧なとき、候補について質問して絞る。
58. **Explainable AI for Robot Failures: Generating Explanations that Improve User Assistance in Fault Recovery** — Das, Banerjee, Chernova. HRI 2021. [DOI 10.1145/3434073.3444657](https://doi.org/10.1145/3434073.3444657)。失敗時に、原因と直前の文脈を含む説明を出すと、非専門家が原因と対処を見つけやすくなる（結果の細部は未確認）。「何が」「なぜ」を含む説明が復旧を助ける根拠。
59. **Why Did I Fail? A Causal-Based Method to Find Explanations for Robot Failures** — Diehl, Ramirez-Amaro. IEEE RA-L 2022. [DOI 10.1109/LRA.2022.3188889](https://doi.org/10.1109/lra.2022.3188889)。因果モデルを使い、失敗した状態と、成功したはずの最も近い状態を比べて対比的に説明する。
60. **Understanding and Resolving Failures in Human-Robot Interaction: Literature Review and Model Development** — Honig, Oron-Gilad. Frontiers in Psychology 2018. [DOI 10.3389/fpsyg.2018.00861](https://doi.org/10.3389/fpsyg.2018.00861)。HRI の失敗の総説。人が失敗に気づき、理解し、対処するまでの段階モデルを提案。
61. **REX: Designing User-centered Repair and Explanations to Address Robot Failures** — Lee, Praveena, Mutlu. DIS 2024. [DOI 10.1145/3643834.3661559](https://doi.org/10.1145/3643834.3661559)。題名と書誌のみ確認。失敗時の修復と説明の設計を扱うとみられるが、**内容は未確認**。

### Inferences
- 解決操作の候補は文献上 5 つに整理できる：(1) 人に聞く（52、57）、(2) 代案を出す（X-OOHRI の Auto、45）、(3) ルール・制約を緩める（30）、(4) 計画を直接編集する（X-OOHRI の仮想ツイン操作、12、31）、(5) 認識を直す（16〜18）。対象設計のラベルから出すメニューは、この 5 つから選べる。
- 既存研究の質問・報告は「実行中または実行後」に「言葉で」出る。対象設計は「実行前のプレビュー」で「物体の位置に」出すので、時点と媒体の両方が異なる。

### Gaps
- 「できる分だけ実行して残りを報告する」ことを主題にした家庭ロボット研究を、題名で特定できなかった。部分実行の報告のしかたの比較研究も見つからなかった。
- AR で対象物体を指しながら助けを求める研究（"asking for help with AR pointing"）は、依頼文にあった形では特定できなかった。近いのは 20、21。

---

## KQ5. HCI の類例：項目ごとのその場のエラー表示と、AR ラベルの設計指針

### Takeaway
AR ラベルの配置は view management の研究が直接の設計指針になる（物体を隠さない、ラベル同士を重ねない、引出線、視点が動いてもラベルを跳ねさせない）。「エラーは該当項目のそばに出す」は Web フォームの研究が経験的な根拠になる。建設の AR 欠陥管理は「問題のある実物の位置に印を付ける」類例。AR でのルール衝突の可視化（スマートホーム）と、AR での建築法規違反の可視化は、査読論文としては見つからなかった。

### Cited Findings

**AR ラベルの配置（view management）**

62. **View management for virtual and augmented reality** — Bell, Feiner, Höllerer. UIST 2001. [DOI 10.1145/502348.502363](https://doi.org/10.1145/502348.502363)（DOI は記憶による、Crossref 照合では出なかった）。注釈が重要な物体や互いを隠さないよう、画面上の空き領域を求めてラベルの位置・大きさを決める。view management という問題設定の出発点。
63. **Evaluating label placement for augmented reality view management** — Azuma, Furmanski. ISMAR 2003. [DOI 10.1109/ISMAR.2003.1240689](https://doi.org/10.1109/ismar.2003.1240689)。ラベル配置アルゴリズムを比較し、重なりと読み取り時間の関係をユーザー評価で調べた。
64. **Image-driven view management for augmented reality browsers** — Grasset, Langlotz, Kalkofen, Tatzgern, Schmalstieg. ISMAR 2012. [DOI 10.1109/ISMAR.2012.6402555](https://doi.org/10.1109/ismar.2012.6402555)。カメラ画像の顕著性とエッジを使い、重要な実物を隠さない場所にラベルと引出線を置く。
65. **Hedgehog labeling: View management techniques for external labels in 3D space** — Tatzgern, Kalkofen, Grasset, Schmalstieg. IEEE VR 2014. [DOI 10.1109/VR.2014.6802046](https://doi.org/10.1109/vr.2014.6802046)。ラベルを画面上でなく 3D 空間で配置し、視点が動いてもラベルが飛び回らないようにする。
66. **Temporal Coherence Strategies for Augmented Reality Labeling** — Madsen, Tatzgern, Madsen, Schmalstieg, Kalkofen. IEEE TVCG 2016. [DOI 10.1109/TVCG.2016.2518318](https://doi.org/10.1109/tvcg.2016.2518318)。ラベルの時間的な一貫性の戦略をユーザー評価で比較（3D 空間に置き更新を離散的にする方式が良いという結果だったと記憶、未確認）。
67. **Embedded Data Representations** — Willett, Jansen, Dragicevic. IEEE TVCG 2017. DOI 10.1109/TVCG.2016.2598608（記憶による、**書誌未確認**）. [DOI](https://doi.org/10.1109/TVCG.2016.2598608)。データを、それが指す実物の近くに置く「situated」と、実物に重ねる「embedded」を区別する枠組み。物体に付けた違反ラベルの位置づけを述べる語彙になる。

**項目ごとのエラー表示（フォーム、コンパイラ）**

68. **Usable error message presentation in the World Wide Web: Do not show errors right away** — Bargas-Avila, Oberholzer, Schmutz, de Vito, Opwis. Interacting with Computers 2007. [DOI 10.1016/j.intcom.2007.01.003](https://doi.org/10.1016/j.intcom.2007.01.003)。フォームのエラーをいつ出すかの実験。入力の途中で即座に出すより、入力を終えた後にまとめて出すほうがよいという結果（題名のとおり）。
69. **Designing usable web forms: empirical evaluation of web form improvement guidelines** — Seckler, Heinz, Bargas-Avila, Opwis, Tuch. CHI 2014. [DOI 10.1145/2556288.2557265](https://doi.org/10.1145/2556288.2557265)。フォーム設計の指針群（エラーメッセージの位置や書き方を含む）を適用すると、使いやすさが上がることを実験で示した（どの指針が効いたかは未確認）。
70. **Compiler Error Messages Considered Unhelpful: The Landscape of Text-Based Programming Error Message Research** — Becker, Denny, Pettit, Bouchard, Bouvier, Harrington, Kamil ほか. ITiCSE-WGR 2019. [DOI 10.1145/3344429.3372508](https://doi.org/10.1145/3344429.3372508)。プログラミングのエラーメッセージ研究の総説。エラーの文面の指針（原因の箇所を示す、平易な言葉、直し方を示す等）をまとめている（指針の細目は未確認）。

**建設：実物の位置に欠陥・ずれを示す**

71. **A framework for proactive construction defect management using BIM, augmented reality and ontology-based data collection template** — Park, Lee, Kwon, Wang. Automation in Construction 2013. [DOI 10.1016/j.autcon.2012.09.010](https://doi.org/10.1016/j.autcon.2012.09.010)。BIM と AR で、現場の欠陥を事前に防ぐ管理の枠組み。
72. **A defect management system for reinforced concrete work utilizing BIM, image-matching and augmented reality** — Kwon, Park, Lim. Automation in Construction 2014. [DOI 10.1016/j.autcon.2014.05.005](https://doi.org/10.1016/j.autcon.2014.05.005)。現場で設計モデルを AR で重ね、施工のずれ・欠陥を見つける。
73. 没入型 AR で、天井裏の設備が BIM からずれている箇所を参加者に見つけさせる研究（Buildings 2021, 11(2), 77）。— [MDPI](https://www.mdpi.com/2075-5309/11/2/77)。題名・著者は**未確認**。
74. 現場の BIM-AR 欠陥管理は、紙での検査より使いやすさ・作業負荷・所要時間・欠陥の発見で優れたと報告（Buildings 2022, 12, 140）。— [MDPI PDF](https://mdpi-res.com/d_attachment/buildings/buildings-12-00140/article_deploy/buildings-12-00140-v3.pdf)。題名・著者は**未確認**。

**スマートホームのルール：衝突の検出とデバッグ（AR ではない）、AR でのルール作成**

75. **Empowering End Users in Debugging Trigger-Action Rules**（EUDebug）— Corno, De Russis, Monge Roffarello. CHI 2019. [DOI 10.1145/3290605.3300618](https://doi.org/10.1145/3290605.3300618)。ルール作成中に、ルール同士の問題（ループ、矛盾、重複）を検出して作成画面で警告し、段階実行で確かめさせる。15 人の探索的調査で、問題の発見と理解に役立ったと報告。— [CORE](https://core.ac.uk/works/70472523)
76. **Supporting end-user debugging of trigger-action rules for IoT applications** — Manca, Paternò, Santoro, Corcella. IJHCS 2019. [DOI 10.1016/j.ijhcs.2018.11.005](https://doi.org/10.1016/j.ijhcs.2018.11.005)。「なぜ／なぜ〜しない」に答える形式のデバッグと、ルールの衝突の検出・解決支援。— [CNR 版](https://openportal.isti.cnr.it/data/2019/404663/2019_404663.postprint.pdf)
77. **How Users Interpret Bugs in Trigger-Action Programming** — Brackenbury, Deora, Ritchey, Vallee, He, Wang, Littman ほか. CHI 2019. [DOI 10.1145/3290605.3300782](https://doi.org/10.1145/3290605.3300782)。トリガー・アクション型プログラムのバグの種類を整理し、利用者がそれをどう読み違えるかを調べた。
78. **AutoTap: Synthesizing and Repairing Trigger-Action Programs Using LTL Properties** — Zhang, He, Martinez, Brackenbury, Lu, Ur. ICSE 2019. [DOI 10.1109/ICSE.2019.00043](https://doi.org/10.1109/icse.2019.00043)。「〜は決して起きてはならない」のような性質を利用者が指定し、違反するルールを自動で修復する。
79. **Reality Editor: Programming Smarter Objects** — Heun, Hobin, Maes. UbiComp 2013 Adjunct. [DOI 10.1145/2494091.2494185](https://doi.org/10.1145/2494091.2494185)。AR で実物の上に機能を表示し、物どうしを線でつないで連携を作る。ルールを実物に結び付けて見せる出発点。衝突の表示は扱わない。
80. スマートフォンの AR で家庭の自動化ルールを作るツールと、家庭での初回ユーザーテスト（Ariano, Manca, Paternò, Santoro）。— [CNR 版 PDF](https://iris.cnr.it/retrieve/eda19a9e-5442-4067-9e67-1f5750e93a93/prod_462129-doc_180394.pdf)。題名・会場・年は**未確認**。
81. モバイル AR で自動化の作成・制御を推薦とシミュレーションで支援し、AR での説明の枠組みを検討する短報（Mattioli, Paternò）。— [CEUR-WS Vol-3408](https://ceur-ws.org/Vol-3408/short-s4-07.pdf)。題名は**未確認**。

### Inferences
- ラベル配置の要件：(a) 違反した実物を隠さない（62、64）、(b) 複数の違反ラベルが重ならない（63）、(c) ラベルと物体を引出線でつなぐ（64、65）、(d) 頭を動かしてもラベルが跳ねない（65、66）。違反物体が同じ棚に複数あるときに特に効く。
- 68 は「エラーは作業の区切りでまとめて出す」ことを支持する。対象設計が「計画を作り終えたプレビューの時点で、違反をまとめて見せる」ことと整合する。ただしフォーム入力の実験であり、AR にそのまま当てはまるとは限らない。
- 75〜78 は、ルール違反・衝突を「作成画面の該当ルールのそば」に出す。対象設計は「該当する実物のそば」に出す。67 の語彙でいえば、前者はルール側に置き、後者は対象物側に置く。
- エラー文面は、70 と 58 から「どの物体が」「どのルールに」「どうすれば解決できるか」の 3 点を含めるのが妥当と推測できる。

### Gaps
- AR で建築法規・基準への違反を現場に重ねて示す査読論文は、今回見つからなかった（検索に出たのは特許文書のみ）。BIM の干渉チェック（clash detection）の表示方法についての HCI 的な評価も確認していない。
- スマートホームのルール衝突を AR でその場に可視化する査読論文は見つからなかった。Ivy（Ens ほか、GI 2017、空間に置く視覚プログラミング）は Crossref で照合できず、一覧から外した。
- リンタの波線・インライン診断の効果を測った研究は、70 の総説以外に特定していない。
- AR ラベルの読みやすさ（背景との対比、文字の描き方）、色だけに頼らない符号化（色覚多様性）についての文献は今回調べていない。
- 「ゴースト（ゴール位置の半透明表示）と、実位置に残した物体を同時に見せたときの見分けやすさ」を直接評価した研究は確認していない（他の担当範囲の可能性）。
