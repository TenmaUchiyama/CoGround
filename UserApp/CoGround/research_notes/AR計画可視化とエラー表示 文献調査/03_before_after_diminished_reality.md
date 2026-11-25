# Before/After 提示と Diminished Reality（ロボットのタスク完了後環境を AR で事前提示する設計の先行研究）

> 調査メモの読み方
> - **書誌の検証**: 特記がない限り、タイトル・著者・会議/誌名・年・DOI は Crossref API で照合済み（2026-11-22）。Crossref で取れなかったものは「書誌未検証」と明記。
> - **内容の検証レベル**: 【抄録確認】= 今回の調査で抄録・公式ページ・検索スニペットを確認。【既有知識】= 調査者（LLM）の既有知識に基づく要約で、今回原文を再読できていない（ACM DL / PDF 抽出不可のため）。数値や細部を報告書に使う前に原文確認を推奨。
> - OpenAlex はレート制限で使えず、PDF テキスト抽出ツールも環境に無かったため、本文レベルの精読はできていない。

---

## 新規性の問い: 「DR + 仮想オブジェクト重畳で **ロボットタスクの完了後状態** をプレビューする」先行研究はあるか

### Takeaway
今回の調査範囲では、**「実物体を DR で現在位置から消し、ゴール位置に 3D 仮想コピーを重ねて、ロボット実行前に Before/After を人が確認する」ことを主題にした論文は見つからなかった**。最も近いのは (a) Reality Promises（UIST 2025：DR で *ロボット* を消し、仮想操作に物理が後追いする）、(b) X-OOHRI（HRI 2026：実物体の virtual twin を AR で直接操作してロボットに指示）、(c) Scene Responsiveness（UIST 2023：実物体を DR で消して仮想コピーを動かす、ロボット無し）、(d) ImageInThat（HRI 2025：2D 画像上でゴール状態を編集・確認）で、いずれも「DR による After 提示を人の検証手段として評価」はしていない。

### Cited Findings
- 試した検索クエリ（WebSearch、いずれも該当する統合システムは出ず）:
  1. `diminished reality augmented reality preview robot task goal state object rearrangement "diminished reality" robot plan visualization`
  2. `"diminished reality" robot "virtual twin" OR "ghost" OR "preview" manipulation mixed reality user moves virtual copy real object erased robot executes`
  3. `Kari Abtahi "Reality Promises" invisible mobile robots diminished reality ...`
  4. Crossref 書誌検索: `Diminished reality for hiding robot human-robot collaboration` / `Erasing the robot diminished reality telepresence robot body` / `Diminished reality teleoperation robot arm see-through` / `Preview robot plan digital twin mixed reality before execution approve` / `Outcome preview robot action augmented reality what-if digital twin human approval` / `Tidying up rooms augmented reality robot user preference specification`
  → 1 の検索結果要約は「DR・ロボットのゴール状態プレビュー・再配置を 1 システムに統合したものは出てこなかった」、2 も「ロボット実行中/前に実物体を消すシステムは見つからない」。
- VAM-HRI サーベイ（Walker et al., THRI 2023）は「実カップの位置に仮想カップを重ね、ユーザがロボット実行前に実物体への動作をプレビューする」類型を記述しているが、実物体を消す（DR）ことは記述していない（検索スニペットによる）— [Walker et al. 2023](https://doi.org/10.1145/3597623) / [arXiv 2202.11249](https://arxiv.org/abs/2202.11249)
- Reality Promises: MR ヘッドセット装着ユーザが物体を仮想的に選んで置くと、**ユーザから不可視化された移動ロボット**が実物体をその場所へ運ぶ。3D Gaussian Splatting で部屋のデジタルコピーを作り、パススルー映像からロボットを消したり仮想キャラクタ（蜂）を足したりする。機材は Stretch 3 と Meta Quest 3（検索結果による）。— [Princeton CS ニュース](https://www.cs.princeton.edu/node/6711) / [DOI](https://doi.org/10.1145/3746059.3747660) / [著者 PDF](https://hci.princeton.edu/wp-content/uploads/sites/459/2025/08/kari2025-reality-promises.pdf)
- X-OOHRI（Explainable OOHRI）: 抄録は「シミュレーション環境と空間整合した **virtual twins の直接操作**」「signifier・ラジアルメニュー・色分け・説明タグでロボットの可能/不可能を提示」と述べるが、**抄録には DR・インペインティング・実物体の隠蔽への言及はない**。— [arXiv 2601.14587](https://arxiv.org/abs/2601.14587)
- 特許レベルでは「現在の部屋の映像を空の部屋などの状態に“ステージング”し、その上に仮想要素を重ねて再配置後を見せる」DR 特許がある（人間向け、ロボット計画ではない。検索結果による要約で、特許本文は未精読）— [US 9514573 "Diminished reality"](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/9514573)
- Wiley の書籍 *Human–Robot Interaction through Extended Reality*（2026）に "Human–Robot Interaction through Diminished Reality" という章がある（著者名は Crossref に無く未検証、内容未読）。DR×HRI の整理が存在することを示すので要確認。— [DOI 10.1002/9781394470143.ch21](https://doi.org/10.1002/9781394470143.ch21)

### Inferences
- 既存の DR×ロボット研究はほぼ全て「**ロボット自身を消す**」（遮蔽解消 or イリュージョン）であり、「**操作対象物を消して未来状態を見せる**」方向は空いている可能性が高い。
- Reality Promises / Scene Responsiveness / X-OOHRI が同一グループ（Kari, Abtahi）から出ており、X-OOHRI 本文で DR を使っている可能性は残る（抄録だけでは否定できない）。**新規性主張の前に X-OOHRI と Reality Promises の本文・関連研究節の確認が必須**。
- 差別化軸の候補: (1) DR の目的が「イリュージョン」でなく「計画の検証（Before/After 比較）」、(2) 計画由来（ロボット/プランナが決めたゴール）であってユーザが置いたゴールではない、(3) Before/After 切替の比較技法と安全性（消した実物体への衝突）を評価対象にする。

### Gaps
- X-OOHRI 本文（パススルー上で実物体を消しているか）、Reality Promises 本文の評価結果・安全性議論は未確認（PDF テキスト抽出不可）。
- Wiley 書籍章の中身、Google Scholar での網羅検索（"diminished reality" AND robot AND (goal OR preview)）は未実施。ISMAR 2025/2026・IEEE VR 2026 のポスター類は未走査。

---

## KQ1. ロボットのゴール状態 / 未来状態 / 結果プレビュー（AR/MR）

### Takeaway
AR でのロボット未来提示は「ゴーストロボット（virtual surrogate）・軌跡・ゴースト物体」の**加算的重畳**が主流で、実物体は元の位置に見えたまま仮想コピーが目的地に半透明で出る。プレビュー→承認→実行の流れは確立しているが、実物体と仮想コピーが二重に見える問題を DR で解いた例は見当たらない。

### Cited Findings（論文リスト）
1. **Robot Teleoperation with Augmented Reality Virtual Surrogates** — Michael E. Walker, Hooman Hedayati, Daniel Szafir. HRI 2019. [DOI](https://doi.org/10.1109/hri.2019.8673306)
   ドローン遠隔操作で、実機の代わりに AR 上の仮想サロゲート（ゴースト機体）を操作し、実機が後追いする（time-shifted preview）。HMD（HoloLens、光学シースルー）。ユーザスタディで直接操作より効率・主観評価が改善と報告。【既有知識】
2. **Communicating Robot Motion Intent with Augmented Reality** — Michael Walker, Hooman Hedayati, Jennifer Lee, Daniel Szafir. HRI 2018. [DOI](https://doi.org/10.1145/3171221.3171253)
   飛行ロボットの将来経路を NavPoints / Arrow / Gaze / Utilities の AR デザインで提示。HoloLens。意図提示で協働効率と主観評価が向上。【既有知識】
3. **Communicating and controlling robot arm motion intent through mixed-reality head-mounted displays** — Eric Rosen, David Whitney, Elizabeth Phillips, Gary Chien, James Tompkin, George Konidaris, Stefanie Tellex. IJRR 2019. [DOI](https://doi.org/10.1177/0278364919842925)
   アームの計画軌道をゴーストアーム列として HoloLens に重畳。2D ディスプレイや可視化なしより衝突判定の正確さ・速さが向上。【既有知識】
4. **Mixed Reality as a Bidirectional Communication Interface for Human-Robot Interaction** — Eric Rosen, David Whitney, Michael Fishman, Daniel Ullman, Stefanie Tellex. IROS 2020. [DOI](https://doi.org/10.1109/iros45743.2020.9340822)
   MR HMD でロボットが参照物体を可視化して曖昧性を解消する双方向インタフェース（pick 対象の確認）。【既有知識】
5. **End-User Robot Programming Using Mixed Reality** — Samir Yitzhak Gadre, Eric Rosen, Gary Chien, Elizabeth Phillips, Stefanie Tellex, George Konidaris. ICRA 2019. [DOI](https://doi.org/10.1109/icra.2019.8793988)
   HoloLens 上でウェイポイントを置き、ゴーストアームで動作をプレビューしてから実行。2D モニタ UI と比較。【既有知識】
6. **Robot Programming Through Augmented Trajectories in Augmented Reality** — Camilo Perez Quintero, Sarah Li, Matthew KXJ Pan, Wesley P. Chan, H.F. Machiel Van der Loos, Elizabeth Croft. IROS 2018. [DOI](https://doi.org/10.1109/iros.2018.8593700)
   AR HMD で軌道を作成・プレビュー・編集してから実行。【既有知識】
7. **GhostAR: A Time-space Editor for Embodied Authoring of Human-Robot Collaborative Task with Augmented Reality** — Yuanzhi Cao, Tianyi Wang, Xun Qian, Pawan S. Rao, Manav Wadhawan, Ke Huo, Karthik Ramani. UIST 2019. [DOI](https://doi.org/10.1145/3332165.3347902)
   人の動作を記録した「ゴースト」を時空間参照として AR に再生し、ロボットの協調動作をオーサリング、AR 内でシミュレーション確認。HMD。【既有知識】
8. **V.Ra: An In-Situ Visual Authoring System for Robot-IoT Task Planning with Augmented Reality** — Yuanzhi Cao, Zhuangying Xu, Fan Li, Wentao Zhong, Ke Huo, Karthik Ramani. DIS 2019. [DOI](https://doi.org/10.1145/3322276.3322278)
   ハンドヘルド AR で移動ロボットの経路・IoT 連携タスクをその場で描き、端末をロボットに載せて実行。【既有知識】
9. **Kinetic AR: A Framework for Robotic Motion Systems in Spatial Computing** — Anna Fuste, Ben Reynolds, James Hobin, Valentin Heun. CHI EA 2020. [DOI](https://doi.org/10.1145/3334480.3382814)
   モバイル AR 上でロボットの経路・動作を空間的に編集・可視化するフレームワーク（Reality Editor 系）。【既有知識】
10. **exTouch: spatially-aware embodied manipulation of actuated objects mediated by augmented reality** — Shunichi Kasahara, Ryuma Niiyama, Valentin Heun, Hiroshi Ishii. TEI 2013. [DOI](https://doi.org/10.1145/2460625.2460661)
    タブレット画面上で実物体（駆動体）に重なる仮想グラフィックをドラッグすると、実物体がその位置へ追従。**「仮想コピーをゴールへ動かす→実体が後追い」の原型**。【既有知識】
11. **TouchMe: An Augmented Reality Based Remote Robot Manipulation** — Sunao Hashimoto, Akihiko Ishida, Masahiko Inami, Takeo Igarashi. ICAT 2011（英語版の書誌は未検証）。Crossref で確認できたのは日本語版 Robomec 2012: [DOI](https://doi.org/10.1299/jsmermd.2012._2p1-m04_1)
    三人称カメラ映像上でロボットの CG ゴーストをタッチ操作し、指を離すと実機がゴースト姿勢へ動く。スクリーン（タッチパネル）。【既有知識】
12. **Mobile Mixed-Reality Interfaces That Enhance Human–Robot Interaction in Shared Spaces** — Jared A. Frank, Matthew Moorhead, Vikram Kapila. Frontiers in Robotics and AI 2017. [DOI](https://doi.org/10.3389/frobt.2017.00020)（OA）
    タブレット AR 上で**実物体の仮想コピーをドラッグしてゴール位置を指定**し、ロボットが pick-and-place。ハンドヘルド（ビデオシースルー）。【既有知識】
13. **Realizing mixed-reality environments with tablets for intuitive human-robot collaboration for object manipulation tasks** — Jared A. Frank, Matthew Moorhead, Vikram Kapila. RO-MAN 2016. [DOI](https://doi.org/10.1109/roman.2016.7745146)
    上記の前身。タブレット MR で物体操作タスクを指示。【既有知識】
14. **Designing Laser Gesture Interface for Robot Control** — Kentaro Ishii, Shengdong Zhao, Masahiko Inami, Takeo Igarashi, Michita Imai. INTERACT 2009 (LNCS). [DOI](https://doi.org/10.1007/978-3-642-03658-3_52)
    レーザポインタで物体と置き場所を指示し、プロジェクタ等でフィードバック。家庭内 pick-and-place のゴール指定の古典。【既有知識】
15. **Sketch and Run: a stroke-based interface for home robots** — Daisuke Sakamoto, Koichiro Honda, Masahiko Inami, Takeo Igarashi. CHI 2009. [DOI](https://doi.org/10.1145/1518701.1518733)
    天井カメラ俯瞰映像（スクリーン）にストロークを描き掃除ロボットの経路・領域を指定。非 AR ベースライン。【既有知識】
16. **ARC-LfD: Using Augmented Reality for Interactive Long-Term Robot Skill Maintenance via Constrained Learning from Demonstration** — Matthew B. Luebbers, Connor Brooks, Carl L. Mueller, Daniel Szafir, Bradley Hayes. ICRA 2021. [DOI](https://doi.org/10.1109/icra48506.2021.9561844)
    学習済みスキルのキーフレーム・制約を AR HMD で可視化し、その場で編集・再計画結果を確認。【既有知識】
17. **Projection-Aware Task Planning and Execution for Human-in-the-Loop Operation of Robots in a Mixed-Reality Workspace** — Tathagata Chakraborti, Sarath Sreedharan, Anagha Kulkarni, Subbarao Kambhampati. IROS 2018. [DOI](https://doi.org/10.1109/iros.2018.8593830)
    HoloLens でロボットの意図（これから使う物体など）を投影し、「投影行為」自体をプランニングに組み込む。タスク計画レベルの意図提示。【既有知識】
18. **Projecting robot intentions into human environments** — Rasmus S. Andersen, Ole Madsen, Thomas B. Moeslund, Heni Ben Amor. RO-MAN 2016. [DOI](https://doi.org/10.1109/roman.2016.7745145)
    プロジェクタで作業対象物上にロボットの意図・将来動作を投影（ヘッドセット不要）。【既有知識】
19. **Mind the ARm: realtime visualization of robot motion intent in head-mounted augmented reality** — Uwe Gruenefeld, Lars Prädel, Jannike Illing, Tim Stratmann, Sandra Drolshagen, Max Pfingsthorn. Mensch und Computer 2020. [DOI](https://doi.org/10.1145/3404983.3405509)
    アームの動作意図を HMD で経路・プレビュー・ボリュームとして可視化し比較。【既有知識】
20. **Comparison of Multimodal Heading and Pointing Gestures for Co-Located Mixed Reality Human-Robot Interaction** — Dennis Krupke, Frank Steinicke, Paul Lubos, Yannick Jonetzko, Michael Gorner, Jianwei Zhang. IROS 2018. [DOI](https://doi.org/10.1109/iros.2018.8594043)
    HoloLens で pick-and-place 対象を選び、仮想ロボットの動作プレビューを見てから実行。【既有知識】
21. **Interactive Robot Knowledge Patching Using Augmented Reality** — Hangxin Liu, Yaofang Zhang, Wenwen Si, Xu Xie, Yixin Zhu, Song-Chun Zhu. ICRA 2018. [DOI](https://doi.org/10.1109/icra.2018.8462837)
    ロボットの内部状態・タスク知識（And-Or グラフ）を HoloLens で可視化し、人がその場で修正。【既有知識】
22. **PRogramAR: Augmented Reality End-User Robot Programming** — Bryce Ikeda, Daniel Szafir. ACM THRI 2024. [DOI](https://doi.org/10.1145/3640008)
    AR HMD でのエンドユーザ向けロボットプログラミング（トリガ・領域・動作をその場で指定）。【既有知識】
23. **Spatially Situated End-User Robot Programming in Augmented Reality** — Michal Kapinus, Vitezslav Beran, Zdenek Materna, Daniel Bambusek. RO-MAN 2019. [DOI](https://doi.org/10.1109/ro-man46459.2019.8956336)
    タブレット AR でプログラム要素を作業空間に配置する。【既有知識】
24. **RoboVisAR: Immersive Authoring of Condition-based AR Robot Visualisations** — Rasmus Skovhus Lunding, Mille Skovhus Lunding, Tiare Feuchtner, Marianne Graves Petersen, Kaj Grønbæk, Ryo Suzuki. HRI 2024. [DOI](https://doi.org/10.1145/3610977.3634972)
    ロボット状態に応じた AR 可視化（軌跡・プレビュー等）をその場でオーサリング。【既有知識】
25. **Explainable OOHRI: Communicating Robot Capabilities and Limitations as Augmented Reality Affordances (X-OOHRI)** — Lauren W. Wang, Mohamed Kari, Parastoo Abtahi. HRI 2026. [DOI](https://doi.org/10.1145/3757279.3785569) / [arXiv 2601.14587](https://arxiv.org/abs/2601.14587) / [project](https://xoohri.github.io)
    実物体に整合した **virtual twin を直接操作**してロボットに指示し、VLM が物体属性とロボット制約をオブジェクト指向構造にして、できない理由を色分け・説明タグで提示。実ロボットで単体 pick-and-place、複数物体、ブラインド操作等をデモ。ユーザスタディで、参加者はオブジェクト指向コマンドを出し、ロボットの限界について正確なメンタルモデルを形成し、混合主導で解決したと報告。**抄録に DR の記述なし**（依頼文の「X = XR」は誤りで "Explainable" の X）。【抄録確認】
26. **Reality Promises: Virtual-Physical Decoupling Illusions in Mixed Reality via Invisible Mobile Robots** — Mohamed Kari, Parastoo Abtahi. UIST 2025. [DOI](https://doi.org/10.1145/3746059.3747660)
    ユーザが仮想的に物体を置く→不可視化（DR）されたロボットが実物体を運ぶ→仮想と物理が再結合。3DGS ベースのロボット認識ラスタライズでパススルーからロボットを消す。Quest 3（ビデオシースルー）+ Stretch 3。公式ニュースでは部屋と全物体の事前スキャンが面倒という制約が挙げられている。ユーザ評価の結果は未確認。— [Princeton](https://www.cs.princeton.edu/node/6711)【抄録確認】
27. **Augmented Reality and Robotics: A Survey and Taxonomy for AR-enhanced Human-Robot Interaction and Robotic Interfaces** — Ryo Suzuki, Adnan Karim, Tian Xia, Hooman Hedayati, Nicolai Marquardt. CHI 2022. [DOI](https://doi.org/10.1145/3491102.3517719)
    460 本規模の AR×ロボット論文の分類（設計空間）。プレビュー/シミュレーション類型の位置づけに使える。【既有知識】
28. **Virtual, Augmented, and Mixed Reality for Human-Robot Interaction: A Survey and Virtual Design Element Taxonomy** — Michael Walker, Thao Phung, Tathagata Chakraborti, Tom Williams, Daniel Szafir. ACM THRI 2023. [DOI](https://doi.org/10.1145/3597623)
    仮想デザイン要素の分類。「実物体位置に仮想物体を重ねて実行前プレビュー」を含む。【抄録確認（検索スニペット）】
29. **Optimal Assistance for Object-Rearrangement Tasks in Augmented Reality** — Benjamin Newman ほか（共著者未検証）. arXiv 2020. [arXiv 2010.07358](https://arxiv.org/abs/2010.07358)
    *人間*が行う物体再配置を、身体化エージェントの最適方策（容量付き配送計画問題）として解き、AR HUD で提案を出す。ロボット向けではないが「再配置×AR 支援」の近接研究。【抄録確認（検索スニペット）】
30. **Mixed Reality Outperforms Virtual Reality for Remote Error Resolution in Pick-and-Place Tasks** — Advay Kumar, Stephanie Simangunsong, Pamela Carreno-Medrano, Akansel Cosgun. HRI 2025. [DOI](https://doi.org/10.1109/hri61500.2025.10974002)
    タイトルの通り pick-and-place の遠隔エラー解決で MR と VR を比較（内容未読、タイトルのみ確認）。

### Inferences
- 「仮想コピーをゴールへ」は exTouch / TouchMe / Frank et al. / X-OOHRI と系譜があるが、いずれも**入力（ゴール指定）手段**であり、**出力（プランナが決めた結果の提示と検証）**としての全景 After 表示は薄い。
- 加算重畳のみだと、同一物体が「実物（現在位置）」と「ゴースト（ゴール位置）」で二重に見える。物体数が多い片付けタスクでは After の全体像が把握しづらい、というのが DR 併用の動機づけになり得る（この点を直接検証した論文は未発見）。

### Gaps
- 依頼文にあった "Pick-by-AR"、"Blanco-Mulero の AR ゴール指定"、"AR object rearrangement goal specification" は該当論文を確認できなかった（存在しない/名称違いの可能性。リストから除外）。
- "Holo-Dex: Teaching Dexterity with Immersive Mixed Reality"（Arunachalam, Güzey, Chintala, Pinto, ICRA 2023, [DOI](https://doi.org/10.1109/icra48891.2023.10160547)）は実在するが、VR ヘッドセットでの遠隔デモ収集であり、ゴール状態プレビューとは無関係（リスト対象外）。
- 各論文のユーザスタディ数値は今回再確認できていない。

---

## KQ2. Diminished Reality（HRI/ロボティクスでの利用、および DR + 物体移動の MR 研究、知覚・倫理・安全上の問題）

### Takeaway
ロボティクスでの DR は「**ロボット自体を透明化して遮蔽を解く**」用途がほぼ全てで、効果は限定的（労力は減るが効率・選好は悪化し得る）。一般 MR では「実物体を消して仮想コピーを動かす」技術（SceneCtrl、Remixed Reality、Scene Responsiveness）が既にあり、DR 研究は「消した物体の文脈を保つ手がかり（輪郭など）」の必要性を繰り返し指摘している。

### Cited Findings（論文リスト）
31. **Diminished Reality for Close Quarters Robotic Telemanipulation** — Ada V. Taylor, Ayaka Matsumoto, Elizabeth J. Carter, Alexander Plopski, Henny Admoni. IROS 2020. [DOI](https://doi.org/10.1109/iros45743.2020.9341536) / [CMU RI](https://ri.cmu.edu/?p=126733)
    光学シースルー HMD で「ロボットが透明」に見える DR 錯視を作り、ロボット背後の遮蔽領域を見せる。遮蔽あり/なしターゲットの遠隔操作タスクでユーザスタディ。**ユーザの労力低減の見込みはあるが、タスク効率とユーザ選好では欠点があり、DR インタフェース体験の摩擦点を複数特定**。【抄録確認】
32. **InvisibleRobot: Facilitating Robot Manipulation Through Diminished Reality** — Alexander Plopski, Ada Virginia Taylor, Elizabeth Jeanne Carter, Henny Admoni. ISMAR-Adjunct 2019. [DOI](https://doi.org/10.1109/ismar-adjunct.2019.00-55) / [PDF](https://harplab.github.io/assets/pubs/ada_ismar_2019.pdf)
    ロボット本体を完全に消す表示と、**内部だけ消して輪郭を残す**表示の 2 モード。予備的ユーザスタディで遮蔽条件下の通常操作と比較。完全 DR では関節の微妙な特徴しか残らず使いにくくなり得ると記述。【抄録確認（検索スニペット）】
33. **Time Follower's Vision: a teleoperation interface with past images** — M. Sugimoto, G. Kagotani, H. Nii, N. Shiroma, F. Matsuno, M. Inami. IEEE CG&A 2005. [DOI](https://doi.org/10.1109/mcg.2005.23)
    過去のカメラ画像に現在のロボット CG を重ね、三人称視点を合成する遠隔操作 UI。過去映像+現在モデルの時間合成という点で Before/After 表現の先例。【既有知識】
34. **A survey of diminished reality: Techniques for visually concealing, eliminating, and seeing through real objects** — Shohei Mori, Sei Ikeda, Hideo Saito. IPSJ Trans. CVA 2017. [DOI](https://doi.org/10.1186/s41074-017-0028-1)（OA）
    DR を diminish / see-through / replace / inpaint に整理し、背景取得法（事前観測・多視点・インペインティング）と評価の課題を概観。【既有知識】
35. **Towards Understanding Diminished Reality** — Yi Fei Cheng, Hang Yin, Yukang Yan, Jan Gugenheimer, David Lindlbauer. CHI 2022. [DOI](https://doi.org/10.1145/3491102.3517452) / [CMU HCII](https://www.hcii.cmu.edu/project/towards-understanding-diminished-reality)
    研究 1: 4 シナリオで DR と他の mediated reality 効果（色・サイズ変更）を比較。研究 2: 動画視聴と組立の 2 タスクを DR 環境で実施し、参加者が消す対象と強度を選択。**不透明度を下げる除去が好まれ、輪郭表示など「消した物の文脈理解を保つ仕組み」が評価された。移動の少ないタスクでは文脈理解の低下を許容**。デバイス・参加者数は今回未確認。【抄録確認】
36. **CIRO: The Effects of Visually Diminished Real Objects on Human Perception in Handheld Augmented Reality** — Hanseob Kim, Taehyung Kim, Myungho Lee, Gerard Jounghyun Kim, Jae-In Hwang. Electronics 2021. [DOI](https://doi.org/10.3390/electronics10080900)（OA）
    ハンドヘルド AR で、仮想物体と意味的に不整合な実物体（Contextually Inconsistent Real Objects）を消す/半透明にすることが知覚（プレゼンス等）に与える影響を調べた研究（結果の詳細は未読）。【タイトル・書誌のみ確認】
37. **Diminished reality for augmented reality interior design** — Sanni Siltanen. The Visual Computer（オンライン 2015、巻号は 2017）. [DOI](https://doi.org/10.1007/s00371-015-1174-z)
    既存家具を画像上で消して新しい仮想家具を置くインテリア AR。**「実物を消して仮想物を置く」Before/After 用途の代表例**。モバイル/静止画ベース。【既有知識】
38. **SceneCtrl: Mixed Reality Enhancement via Efficient Scene Editing** — Ya-Ting Yue, Yong-Liang Yang, Gang Ren, Wenping Wang. UIST 2017. [DOI](https://doi.org/10.1145/3126594.3126601)
    HoloLens 等で実シーンの物体を選択して**削除・移動・複製**（元位置は背景補完）できる MR シーン編集。【既有知識】
39. **Remixed Reality: Manipulating Space and Time in Augmented Reality** — David Lindlbauer, Andy D. Wilson. CHI 2018. [DOI](https://doi.org/10.1145/3173574.3173703)
    複数深度カメラのライブ 3D 再構成を VR HMD で見せ、実環境の**空間的変更（物体の消去・移動・複製）、外観変更、時間操作（録画再生・一時停止）、視点変更**を可能にする。ビデオシースルー的 MR。【既有知識】
40. **Annexing Reality: Enabling Opportunistic Use of Everyday Objects as Tangible Proxies in Augmented Reality** — Anuruddha Hettiarachchi, Daniel Wigdor. CHI 2016. [DOI](https://doi.org/10.1145/2858036.2858134)
    実物体に形状の近い仮想物体を重ねて触覚プロキシにする（置換型 mediated reality）。【既有知識】
41. **TransforMR: Pose-Aware Object Substitution for Composing Alternate Mixed Realities** — Mohamed Kari, Tobias Grosse-Puppendahl, Luis Falconeri Coelho, Andreas Rene Fender, David Bethge, Reinhard Schütte, Christian Holz. ISMAR 2021. [DOI](https://doi.org/10.1109/ismar52148.2021.00021)
    ビデオパススルー（モバイル）で実世界の人・車をインペインティングで消し、姿勢を保った仮想キャラクタに置換。【既有知識】
42. **Scene Responsiveness for Visuotactile Illusions in Mixed Reality** — Mohamed Kari, Reinhard Schütte, Raj Sodhi. UIST 2023. [DOI](https://doi.org/10.1145/3586183.3606825)
    事前スキャンした部屋のデジタルツインを使い、パススルー MR で**実物体を消して仮想コピーを動かす**（仮想キャラが実物体を動かしたように見せ、ユーザを誘導して触覚と再整合させる）。Quest 系 VST。ロボット無し。【既有知識】
43. **Diminished Reality Based on Image Inpainting Considering Background Geometry** — Norihiko Kawai, Tomokazu Sato, Naokazu Yokoya. IEEE TVCG 2016. [DOI](https://doi.org/10.1109/tvcg.2015.2462368)
    背景を局所平面で近似し、インペインティング結果を視点移動に追従させる DR。【既有知識】
44. **InpaintFusion: Incremental RGB-D Inpainting for 3D Scenes** — Shohei Mori, Okan Erat, Wolfgang Broll, Hideo Saito, Dieter Schmalstieg, Denis Kalkofen. IEEE TVCG 2020. [DOI](https://doi.org/10.1109/tvcg.2020.3003768)
    色+深度を同時にインペイントし、多視点で一貫した 3D の DR を実現。【既有知識】
45. **Good Keyframes to Inpaint** — Shohei Mori, Dieter Schmalstieg, Denis Kalkofen. IEEE TVCG 2023. [DOI](https://doi.org/10.1109/tvcg.2022.3176958)
    3D DR 用にインペイントすべきキーフレームの選択法。【既有知識】
46. **Advanced self-contained object removal for realizing real-time Diminished Reality in unconstrained environments** — Jan Herling, Wolfgang Broll. ISMAR 2010. [DOI](https://doi.org/10.1109/ismar.2010.5643572)
    事前情報なしのリアルタイム映像インペインティング DR の古典。【既有知識】
47. **Diminished reality system with real-time object detection using deep learning for onsite landscape simulation during redevelopment** — Daiki Kido, Tomohiro Fukuda, Nobuyoshi Yabuki. Environmental Modelling & Software 2020. [DOI](https://doi.org/10.1016/j.envsoft.2020.104759)
    再開発の景観検討で、既存建物を DR で消し新建物を重ねて「解体後/建設後」を現地で見せる。物体検出で前景（人・車）のオクルージョンも処理。**都市スケールの Before/After × DR の代表**。【既有知識】
48. **Diminished reality using semantic segmentation and generative adversarial network for landscape assessment: evaluation of image inpainting according to colour vision** — Takuya Kikuchi, Tomohiro Fukuda, Nobuyoshi Yabuki. J. Computational Design and Engineering 2022. [DOI](https://doi.org/10.1093/jcde/qwac067)
    セグメンテーション+GAN インペインティングで建物を仮想解体する DR。【タイトル・書誌確認】
49. **DecluttAR: An Interactive Visual Clutter Dimming System to Help Focus on Work** — Kaito Yokoro, Monica Perusquia-Hernandez, Naoya Isoyama, Hideaki Uchiyama, Kiyoshi Kiyokawa. Augmented Humans 2023. [DOI](https://doi.org/10.1145/3582700.3582718)
    机上の散らかった物を HMD 上で減光/除去して集中を支援。**「片付いた後の見た目」を DR で作る**点で主題に近い（ロボット無し）。【既有知識】
50. **The Dark Side of Perceptual Manipulations in Virtual Reality** — Wen-Jie Tseng, Elise Bonnail, Mark McGill, Mohamed Khamis, Eric Lecolinet, Samuel Huron, Jan Gugenheimer. CHI 2022. [DOI](https://doi.org/10.1145/3491102.3517728)
    知覚操作（リダイレクション等）が身体的危害に悪用され得ることを論じる。DR で実物体を隠す際の安全・倫理議論の参照点。【既有知識】
51. **Ad-Blocked Reality: Evaluating User Perceptions of Content Blocking Concepts Using Extended Reality** — Christopher Katins, Jannis Strecker, Jan Hinrichs, Pascal Knierim, Bastian Pfleging, Thomas Kosch. CHI 2025. [DOI](https://doi.org/10.1145/3706598.3713230)
    現実世界のコンテンツ（広告等）を XR で遮断・除去する概念へのユーザ受容を評価。【タイトル・書誌確認】
52. **Assessing User Apprehensions About Mixed Reality Artifacts and Applications: The Mixed Reality Concerns (MRC) Questionnaire** — Christopher Katins, Paweł W. Woźniak, Aodi Chen, Ihsan Tumay, Luu Viet Trinh Le, John Uschold, Thomas Kosch. CHI 2024. [DOI](https://doi.org/10.1145/3613904.3642631)
    MR に対する懸念（安全・プライバシー・信頼等）を測る質問紙。DR プレビューの評価指標候補。【タイトル・書誌確認】

### Inferences
- InvisibleRobot / Taylor et al. の知見（完全に消すと手がかりを失う、輪郭を残すモードが必要、効率と選好が下がり得る）と Cheng et al. の知見（輪郭など文脈保持の仕組みが好まれる、移動が少ないタスクなら許容）は一致しており、**After 表示中も「消した実物体の輪郭/ゴースト」を残す**設計が妥当と推測される。
- 片付けプレビューはユーザが静止して眺める時間が主なので Cheng et al. の「less mobile なら許容」に当てはまるが、プレビュー中に歩き回る場合は消した物体への衝突リスクが残る。
- Scene Responsiveness / Reality Promises は部屋と物体の事前スキャン（デジタルツイン/3DGS）を前提にしており、「物体単位の 3D モデルがあれば DR と仮想コピー再配置は Quest 3 クラスで実現可能」という技術的裏付けになる。

### Gaps
- 「DR で隠した実物体にユーザがぶつかった」ことを実測した研究は今回特定できず。Cheng et al. の本文（安全・倫理の議論、参加者数、デバイス）は PDF 抽出不可で未確認。
- Taylor et al. の具体的数値（N、条件別成績）未確認。
- "RealityEdit"、"Scene editing in MR"（依頼文の例）は該当論文を確認できず除外。

---

## KQ3. Before/After 比較技法（AR/MR/可視化）

### Takeaway
比較可視化の標準理論は Gleicher らの 3 分類（**並置 juxtaposition / 重畳 superposition / 明示的符号化 explicit encoding**）で、AR の Before/After は「その場重畳（ゴースト/onion-skin）」「時間スクラブ」「トグル」に対応づけられる。AR でロボット計画の Before/After 比較技法を系統的に比較した研究は今回見つからなかった。

### Cited Findings（論文リスト）
53. **Visual comparison for information visualization** — Michael Gleicher, Danielle Albers, Rick Walker, Ilir Jusufi, Charles D. Hansen, Jonathan C. Roberts. Information Visualization 2011. [DOI](https://doi.org/10.1177/1473871611416549)
    比較可視化を juxtaposition / superposition / explicit encoding（差分の明示）の 3 基本設計とその組合せで分類。【既有知識】
54. **Considerations for Visualizing Comparison** — Michael Gleicher. IEEE TVCG 2018. [DOI](https://doi.org/10.1109/tvcg.2017.2744199)
    比較タスクの要素（対象・行為・スケーラビリティ）から設計を導く枠組み。【既有知識】
55. **Comparative Layouts Revisited: Design Space, Guidelines, and Future Directions** — Sehi L'Yi, Jaemin Jo, Jinwook Seo. IEEE TVCG 2021. [DOI](https://doi.org/10.1109/tvcg.2020.3030419)
    比較レイアウト（並置・重畳・アニメーション遷移等）の実証研究をサーベイし指針を整理。【既有知識】
56. **Interactive 4D overview and detail visualization in augmented reality** — Stefanie Zollmann, Denis Kalkofen, Christof Hoppe, Stefan Kluckner, Horst Bischof, Gerhard Reitmayr. ISMAR 2012. [DOI](https://doi.org/10.1109/ismar.2012.6402554)
    建設現場の時系列 3D 再構成（4D データ）を AR でその場に重ね、概観→詳細と時間方向の比較を行う。**現地 AR での時間的変化の比較可視化の代表**。【既有知識】
57. **Visualization Techniques in Augmented Reality: A Taxonomy, Methods and Patterns** — Stefanie Zollmann, Tobias Langlotz, Raphael Grasset, Wei Hong Lo, Shohei Mori, Holger Regenbrecht. IEEE TVCG 2021. [DOI](https://doi.org/10.1109/tvcg.2020.2986247)
    AR 可視化技法（X-ray、ゴースト、フィルタリング、DR 等）の分類とパターン。【既有知識】
58. **Design Patterns for Situated Visualization in Augmented Reality** — Benjamin Lee, Michael Sedlmair, Dieter Schmalstieg（著者は既有知識、Crossref 未照合）. IEEE TVCG / VIS 2023. [arXiv 2307.09157](https://arxiv.org/abs/2307.09157)
    状況内可視化のデザインパターン（ゴースト、グリフ、ミラー等）を整理。【書誌一部未検証】
59. **Who Put That There? Temporal Navigation of Spatial Recordings by Direct Manipulation** — Klemen Lilija, Henning Pohl, Kasper Hornbæk. CHI 2020. [DOI](https://doi.org/10.1145/3313831.3376604)
    空間記録（3D 録画）の中の**物体を掴んでその軌跡に沿って動かすと時間がスクラブされる**直接操作型の時間ナビゲーション。「この物はどこから来た/どこへ行く」の探索に直結。VR。【既有知識】
60. **Causality-preserving Asynchronous Reality** — Andreas Rene Fender, Christian Holz. CHI 2022. [DOI](https://doi.org/10.1145/3491102.3501836)
    MR で過去の出来事を因果関係を保って後から再生する。現在の環境と過去イベントの混在提示。【既有知識】
61. **Remixed Reality**（上掲 #39）— 時間操作（過去の再生・現在との重畳）を含むため Before/After 技法の実装例でもある。[DOI](https://doi.org/10.1145/3173574.3173703)
62. **In-situ or side-by-side? A user study on augmented reality maintenance instructions in blind areas** — 著者未検証. Computers in Industry 2022（年・誌名は ScienceDirect URL からの推定）. [ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S0166361522001919)
    見えない箇所の保守指示で、その場重畳 AR・3D 並置・2D 図面を比較。**その場重畳と 3D 並置は 2D 図面より良く、alpha blending は成績を損なわず、作業時間には有意差なし**（検索スニペットによる）。【抄録確認（検索スニペット）、書誌未検証】

### Inferences
- 提案（DR + ゴール位置の仮想コピー）は Gleicher 分類では「その場での**置換型トグル**（時間的並置 = blink/toggle）」に当たり、従来のゴースト重畳は「superposition」、移動矢印や差分ハイライトは「explicit encoding」に当たる。比較条件を設計するならこの 3 類型を条件に取るのが自然。
- トグル（Before⇄After の切替）は change blindness を招きやすいので、移動矢印・アニメーション遷移（物体が現在位置からゴールへ滑る）・変化物体のハイライトなど explicit encoding との併用が望ましいと考えられる（直接の実証は未発見）。

### Gaps
- 「AR でのリフォーム/建設 Before-After」「AR 内スライダー/ワイプ比較」のユーザスタディ論文は今回特定できなかった（検索 `augmented reality in-situ "before and after" comparison ... slider toggle user study` は該当なし）。
- "Timeline in AR"、"Past scene overlay in AR"（依頼文の例）は特定の論文に結び付けられず除外。
- change blindness と AR トグル比較の関係を直接扱った論文は未調査。

---

## KQ4. AR を使わないゴール状態プレビュー（生成ゴール画像・想像シーン・VR）と人による検証

### Takeaway
再配置ロボット研究では「ゴール状態を画像/3D として生成（想像）」する手法が多数あるが、ほとんどは**ロボット内部の目標表現**であり人には見せない。人がゴール状態を見て編集・確認することを中心に据えたのは ImageInThat（HRI 2025）が代表で、テキスト指示より大幅に速く、好まれた。

### Cited Findings（論文リスト）
63. **ImageInThat: Manipulating Images to Convey User Instructions to Robots** — Karthik Mahadevan, Blaine Lewis, Jiannan Li, Bilge Mutlu, Anthony Tang, Tovi Grossman. HRI 2025（Best Paper と Rice lab ページに記載）. [DOI](https://doi.org/10.1109/hri61500.2025.10974179) / [arXiv 2503.15500](https://arxiv.org/abs/2503.15500)
    ユーザが 2D 画像上で物体を直接操作して**望む状態の画像列**を作り、それをロボットへの指示にする（スクリーン UI）。参加者 10 名の被験者内実験（画像 vs テキスト、台所タスク 4 種: パントリー収納・果物仕分け・炒め物・皿洗い）で、**平均 110.8 秒 vs 363.88 秒（t(37) = -8.96, p < 0.001）**、ロボットが理解できるという確信も高く、画像方式が好まれた。**人がゴール状態を作成・検証する**代表例。【抄録確認（検索結果）】
64. **DALL-E-Bot: Introducing Web-Scale Diffusion Models to Robotics** — Ivan Kapelyukh, Vitalis Vosylius, Edward Johns. IEEE RA-L 2023. [DOI](https://doi.org/10.1109/lra.2023.3272516)
    現在のシーンの物体記述から拡散モデルで「人間らしく整った配置」のゴール画像を生成し、物体を対応づけて再配置。ゴール画像はロボット内部用で、ユーザスタディは結果の配置の好ましさ評価。【既有知識】
65. **StructDiffusion: Language-Guided Creation of Physically-Valid Structures using Unseen Objects** — Weiyu Liu, Yilun Du, Tucker Hermans, Sonia Chernova, Chris Paxton. RSS 2023. [DOI](https://doi.org/10.15607/rss.2023.xix.031)
    言語指示から物体点群の目標配置（3D 構造）を拡散モデルで生成し、物理的妥当性を識別器で選別。人の確認は介在しない。【既有知識】
66. **StructFormer: Learning Spatial Structure for Language-Guided Semantic Rearrangement of Novel Objects** — Weiyu Liu, Chris Paxton, Tucker Hermans, Dieter Fox. ICRA 2022. [DOI](https://doi.org/10.1109/icra46639.2022.9811931)
    言語から複数物体の目標配置を Transformer で予測。【既有知識】
67. **Dream2Real: Zero-Shot 3D Object Rearrangement with Vision-Language Models** — Ivan Kapelyukh, Yifei Ren, Ignacio Alzugaray, Edward Johns. ICRA 2024. [DOI](https://doi.org/10.1109/icra57147.2024.10611220)
    シーンの NeRF 表現を作り、物体を仮想的に動かした**候補ゴール状態をレンダリング**して VLM で評価し最良配置を選ぶ。「3D で After を想像して描画する」点は提案に近いが、評価者は VLM で人ではない。【既有知識】
68. **SG-Bot: Object Rearrangement via Coarse-to-Fine Robotic Imagination on Scene Graphs** — Guangyao Zhai, Xiaoni Cai, Dianye Huang, Yan Di, Fabian Manhardt, Federico Tombari, Nassir Navab, Benjamin Busam. ICRA 2024. [DOI](https://doi.org/10.1109/icra57147.2024.10610792)
    ゴールをシーングラフで与え、そこからゴールシーンを「想像」生成して再配置。シーングラフ差分でのゴール指定の例。【既有知識】
69. **Zero-Shot Robotic Manipulation with Pretrained Image-Editing Diffusion Models (SuSIE)** — Kevin Black ほか. ICLR 2024（書誌は Crossref 未収録のため既有知識、arXiv 2310.10639 と記憶、**未検証**）. [arXiv](https://arxiv.org/abs/2310.10639)
    画像編集拡散モデルでサブゴール画像を生成し、低レベル方策がそれを達成。サブゴール画像は内部表現。【既有知識・書誌未検証】
70. **Learning Universal Policies via Text-Guided Video Generation (UniPi)** — Yilun Du, Sherry Yang, Bo Dai, Hanjun Dai, Ofir Nachum, Josh Tenenbaum, Dale Schuurmans, Pieter Abbeel. NeurIPS 2023. [DOI](https://doi.org/10.52202/075280-0403)
    テキストから未来の実行映像を生成し、それを計画として行動を逆算。原理的には人が見られる「未来プレビュー映像」だが、人による検証は扱わない。【既有知識】
71. **Housekeep: Tidying Virtual Households Using Commonsense Reasoning** — Yash Kant, Arun Ramachandran, Sriram Yenamandra, Igor Gilitschenski, Dhruv Batra, Andrew Szot, Harsh Agrawal. ECCV 2022. [DOI](https://doi.org/10.1007/978-3-031-19842-7_21)
    明示的ゴール無しで、人間の常識的配置嗜好データ（クラウドソーシング）と LLM により「どこに片付けるか」を推論するベンチマーク。ゴール提示 UI は無い。【既有知識】
72. **TidyBot: Personalized Robot Assistance with Large Language Models** — Jimmy Wu, Rika Antonova, Adam Kan, Marion Lepert, Andy Zeng, Shuran Song, Jeannette Bohg, Szymon Rusinkiewicz. Autonomous Robots 2023 / IROS 2023. [DOI](https://doi.org/10.1007/s10514-023-10139-z)
    少数の配置例から LLM がユーザ固有の片付けルールを要約し、未知物体の置き場所を決定。**実行前にユーザへ計画を見せて確認する仕組みは主題ではない**。【既有知識】
73. **TIDEE: Tidying Up Novel Rooms Using Visuo-Semantic Commonsense Priors** — Gabriel Sarch, Zhaoyuan Fang, Adam W. Harley, Paul Schydlo, Michael J. Tarr, Saurabh Gupta, Katerina Fragkiadaki. ECCV 2022. [DOI](https://doi.org/10.1007/978-3-031-19842-7_28)
    場違いな物体を検出し、常識的事前知識で置き場所を推論して片付ける。【既有知識】
74. **Robot, organize my shelves! Tidying up objects by predicting user preferences** — Nichola Abdo, Cyrill Stachniss, Luciano Spinello, Wolfram Burgard. ICRA 2015. [DOI](https://doi.org/10.1109/icra.2015.7139396)
    協調フィルタリングでユーザの整理嗜好を予測。ゴール嗜好の個人差が大きいこと（＝事前確認の必要性）の根拠として使える。【既有知識】
75. **My House, My Rules: Learning Tidying Preferences with Graph Neural Networks** — Ivan Kapelyukh, Edward Johns. CoRL 2021（Crossref 未収録、**書誌は既有知識**、arXiv 2111.03112 と記憶・未検証）. [arXiv](https://arxiv.org/abs/2111.03112)
    GNN でユーザ別の片付け嗜好を学習し配置を生成。【既有知識・書誌未検証】
76. **Sketching Robot Programs On the Fly** — David Porfirio, Laura Stegner, Maya Cakmak, Allison Sauppé, Aws Albarghouthi, Bilge Mutlu. HRI 2023. [DOI](https://doi.org/10.1145/3568162.3576991)
    タブレット上の環境図にスケッチしてロボットプログラムを指定（非 AR の 2D ゴール/経路指定）。【既有知識】

### Inferences
- 「生成/想像されたゴール状態」は技術的には既にロボット側にある（DALL-E-Bot、Dream2Real、SG-Bot、StructDiffusion）。**それを人に見せて検証させる出力チャネル**が未開拓で、ImageInThat が 2D で、提案はそれを 3D・その場（AR+DR）に拡張する位置づけにできる。
- Dream2Real の「シーンを 3D 表現にして物体を仮想的に動かしレンダリング」は、DR + 仮想コピーによる After 表示と技術的に同型（表示先がVLMかユーザかの違い）。
- 片付け嗜好は個人差が大きい（Abdo et al., Kapelyukh & Johns, TidyBot の前提）ため、実行前のゴール確認には実用上の動機がある。

### Gaps
- VR でロボットの結果（完了後の部屋）をプレビューして承認するユーザスタディは今回特定できず。
- "ConceptGraphs ベースのゴール指定" を UI として評価した論文は確認できず除外。
- ImageInThat のエラー数（H2）の結果は検索スニペットに無く未確認。
- 「生成ゴール画像を人が承認する」構成の他の例（LLM プランナの計画を画像で確認させる等）は未走査。
