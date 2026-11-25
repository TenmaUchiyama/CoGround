# 手順（シーケンス）の可視化と、エラーの位置づけ（どのステップ／どの場所か）

調査日：2026-11-22。担当範囲は「ロボットのタスク過程を列として見せる表現」と「その列の中、または実空間の中のどこにエラーがあるかを示す方法」。失敗の種類の分類は `docs/failure_survey/README.md`（A〜I の 9 種類）に既にあるので、ここでは繰り返さない。

**確認の程度の書き方**

- 【本文】：論文の本文（PDF または HTML）を今回読んで確認した。
- 【要旨】：要旨か著者ページ、検索結果の抜粋までの確認。
- 【未検証】：書誌や内容の一部が、今回の調査では確かめられていない（私の記憶による）。引用する前に原典を確認すること。

各論文の注記は、次の 4 点をこの順に書く。①列の表現、②エラーの見せ方、③空間に固定か・時間（ステップ）に固定か、④実行前（予測）か・事後か。

---

## 1. RoboVisAR は、列（タイムライン）と条件をどう表現しているか。関連する著者グループの研究は何か

### Takeaway

RoboVisAR は「ロボットのプログラムを一度実行して記録 → その記録のタイムライン上で可視化を設計 → 再生して確認」という 3 段階で、可視化を「いつ出すか」を条件（ロボットの状態・近接・箱領域・力/トルク）で決める。エラーや失敗を示す専用の仕組みはなく、後継の ARTHUR にも失敗処理の記述はない。つまり「タイムライン＋条件で出し分ける」土台はあるが、「列のどこが危ないかを示す」部分は空いている。

### Cited Findings

**1) RoboVisAR: Immersive Authoring of Condition-based AR Robot Visualisations** — Rasmus Skovhus Lunding, Mille Skovhus Lunding, Tiare Feuchtner, Marianne Graves Petersen, Kaj Grønbæk, Ryo Suzuki。HRI '24（Boulder）、pp. 462–471、DOI 10.1145/3610977.3634972。【要旨＋検索抜粋。本文 PDF は 10MB 超で取得できなかった】

- 著者は上の 6 名。依頼文にあった「Hubenschmid」は RoboVisAR の著者ではなく、後継の ARTHUR の著者である — [Semantic Scholar API](https://api.semanticscholar.org/graph/v1/paper/DOI:10.1145/3610977.3634972?fields=title,authors)、[KOPS 書誌](https://kops.uni-konstanz.de/entities/publication/d6fcf256-3ce1-4e49-99a2-82bde60fc239)
- 流れは 3 段階。(1) Record：ロボットの動作例を記録する。(2) Design：タイムラインに基づく可視化を作り、見た目を変える。(3) Play：元のロボット、または別のロボットで可視化を試す — [KOPS 全文（検索抜粋）](https://kops.uni-konstanz.de/server/api/core/bitstreams/5af29385-e262-4de2-a331-518fc13d06b9/content)
- タイムラインは Pronto と Rapido に着想を得ている。タイムラインは「どの可視化が追加されているか」と「それがいつ有効か」を示す — [同上](https://kops.uni-konstanz.de/server/api/core/bitstreams/5af29385-e262-4de2-a331-518fc13d06b9/content)
- 再生ボタンを押すと、ロボットの位置を映す仮想ロボットの上で、作った可視化を下見できる — [同上](https://kops.uni-konstanz.de/server/api/core/bitstreams/5af29385-e262-4de2-a331-518fc13d06b9/content)
- 可視化は 6 種類（Path、Point of Interest、Safety Zone、Robot State、Message、Force/Torque）。表示条件は 4 種類（Robot State、Proximity、Box、Force/Torque）— [著者ページ](https://ryosuzuki.org/robovisar/)
- 目的は「必要なときだけ出して、文脈に応じて切り替え、視覚的な混雑を避ける」こと。専門家 3 名の評価で、10 分以内に可視化を作れた — [著者ページ](https://ryosuzuki.org/robovisar/)
- 後継論文による要約：RoboVisAR は「作る前にロボットプログラムを実行して記録を作る、タイムライン方式」。AR の内容はこの記録をもとに設計し、そのあと本番の実行に使う。操作と表示はすべて AR ヘッドセットで行う — [ARTHUR, arXiv 2501.02304](https://arxiv.org/html/2501.02304v1)
- 後継論文が挙げる RoboVisAR の限界は 3 つ。(1) ロボットの可視化だけで、組立手順などの外部の内容を出せない。(2) 実行中にユーザーの入力を受けない（情報はロボット → 人の一方向）。(3) 空中での操作は難しく、特に 2D の UI の編集がつらい — [ARTHUR](https://arxiv.org/html/2501.02304v1)
- ①記録した実行のタイムライン。②エラー表示はない（Safety Zone と Message が最も近い部品）。③可視化は空間に置き、有効な区間をタイムラインに示すので、両方。④記録は事前に作るが、条件は実行時に評価される。

**2) ARTHUR: Authoring Human-Robot Collaboration Processes with Augmented Reality using Hybrid User Interfaces** — Rasmus Lunding, Sebastian Hubenschmid, Tiare Feuchtner, Kaj Grønbæk。arXiv 2501.02304（2025-01）。Virtual Reality 誌 2025 に掲載（DOI 10.1007/s10055-025-01149-6、誌名は検索結果による）。【本文（arXiv HTML の先頭 10 万字）】

- 部品は 3 種類。feedback 20 種（ロボット・作業・システムの状態を伝える）、action 10 種（ユーザーがロボットやシステムを操作する）、condition 18 種（feedback をいつ出すか、action をいつ起こすかを決める）— [arXiv](https://arxiv.org/html/2501.02304v1)
- 作業の順序は、PLM から書き出した組立データ（Bill of Process と Bill of Materials）から取り込む。タイムライン編集画面や順序編集画面の記述はない — [arXiv](https://arxiv.org/html/2501.02304v1)
- 条件の例：開始ボタンは、有効化ボタンと同時に押したとき（AND 条件）だけ、ロボットの確認動作を起こす — [arXiv](https://arxiv.org/html/2501.02304v1)
- エラーや失敗の処理は書かれていない。警告に近いものは例として出るだけ（動き出すときの警告音、立入禁止ゾーン、材料切れを知らせる「ロボット支援」条件）— [arXiv](https://arxiv.org/html/2501.02304v1)
- ①取り込んだ工程表＋条件。②なし（警告音、ゾーン）。③空間。④実行中。

**3) GhostAR: A Time-space Editor for Embodied Authoring of Human-Robot Collaborative Task with Augmented Reality** — Cao, Wang, Qian, Rao, Wadhawan, Huo, Ramani。UIST 2019、DOI 10.1145/3332165.3347902。【要旨】

- 人の動きを「ゴースト」として記録し、それを相手役にしてロボットの動きを実演で作る。時間と空間の両方で行動を編集する — [Purdue PDF](https://engineering.purdue.edu/cdesign/wp/wp-content/uploads/2020/04/GhostAR.pdf)、[検索結果の DOI](https://doi.org/10.1145/3332165.3347902)
- ①時間‐空間エディタ（記録した人とロボットの動きの列）。②エラー表示の記述は確認できなかった。③両方。④実行前（作成時）。

**4) PRogramAR: Augmented Reality End-User Robot Programming** — Bryce Ikeda, Daniel Szafir。ACM THRI 2024（DOI 10.1145/3640008 は検索結果の Crossref リンクによる。【未検証】）。【要旨】

- AR とトリガー・アクション（TAP）を組み合わせる。ロボットの予定の動作をシミュレーションし、TAP ルールが実行できるかをその場で評価して、エンドユーザーのデバッグを助ける。18〜83 歳の 17 名で検証 — [NSF PAR](https://par.nsf.gov/servlets/purl/10510874)
- ①TAP ルール（「もし〜なら〜」）。②実行可能性の即時評価（色やアイコンの詳細は未確認）。③AR 上の領域・物に結びつく（詳細は未確認）。④実行前。

**5) Rapido: Prototyping Interactive AR Experiences through Programming by Demonstration** — Leiva ほか、UIST 2021。**6) Pronto: Rapid Augmented Reality Video Prototyping Using Sketches and Enaction** — Leiva ほか、CHI 2020。【未検証：書誌は記憶による】

- RoboVisAR のタイムラインの着想元。ARTHUR は Rapido を「記録にもとづくタイムライン方式」の出典として引いている — [ARTHUR](https://arxiv.org/html/2501.02304v1)、[Rapido の図（ResearchGate）](https://www.researchgate.net/figure/The-Rapido-system-A-The-mobile-AR-interface-B-The-overview-interface-composed-of-a_fig2_355268579)
- どちらもロボットではなく AR 体験の試作ツール。エラー表示はない。

**7) V.Ra: An In-Situ Visual Authoring System for Robot-IoT Task Planning with Augmented Reality** — Cao ほか、2019。【未検証：会議名は確認していない】

- ARTHUR が関連ツールとして引く。AR 上でロボットと IoT のタスクの列を、その場で作る — [ARTHUR](https://arxiv.org/html/2501.02304v1)

### Inferences

- RoboVisAR の「条件」は、そのままエラー表示の発火条件に読み替えられる。Proximity は「人が近い」、Box は「この領域に入った」、Force/Torque は「力が大きすぎる」。ただし論文は、これを「エラー」としては位置づけていない。
- RoboVisAR と ARTHUR は、どちらも「一度記録した実行」か「取り込んだ工程表」が前提。LLM がその場で作る計画のように、事前の記録がない列には、この方式はそのままでは使えない。
- タイムラインが示すのは「可視化が有効な区間」であって、「タスクのステップ」ではない。ステップ単位でエラーを付けるには、タイムラインをステップで区切る層が要る。

### Gaps

- RoboVisAR のタイムラインの細部（つまみで時刻を動かせるか、条件がタイムライン上にどう描かれるか、記録するデータの項目）は確認できなかった。KOPS の PDF が 10MB を超え、ACM DL は 403 で取得できなかったため。ここに書いた内容は、要旨・検索抜粋・後継論文の記述による。
- 依頼文にあった「Proposing a hybrid authoring …」という題の論文は、今回の検索では見つからなかった。ARTHUR の前段のワークショップ論文の可能性があるが、未確認。
- GhostAR、PRogramAR、V.Ra、Rapido、Pronto のエラー表示の有無は、本文で確認していない。

---

## 2. ロボットプログラムのデバッグと、失敗の可視化をしている研究はどれか（AR デバッグ、再生、PbD でのエラーの位置づけ、形式検証による指摘）

### Takeaway

デバッグ系の AR 研究は「ロボットの内部状態をその場に重ねる」ことが中心で、エラーを明示的に印で示すものは少ない。エラーを「列のどこか」に結びつけているのは、むしろ画面ベースの研究である。RoVer は違反をどのグループが起こしたかまで絞り込み、Polaris は実行前に計画を見せ、RoboCritics は OK / Warning / Error を文章で出す。ただしどれも、実空間の物や場所には固定していない。

### Cited Findings

**AR／MR によるデバッグ**

**8) Advancing the Design of Visual Debugging Tools for Roboticists** — Bryce Ikeda, Daniel Szafir。HRI 2022、pp. 195–204。【本文】

- RViz、2D の GUI、AR ヘッドセットの 3 つを、ロボット研究者 24 名（2 大学）で質的に比べた。課題は TurtleBot に QR コードを見つけさせて近づける、という知覚＋移動のプログラム作り — [NSF PAR PDF](https://par.nsf.gov/servlets/purl/10354657)
- 設計指針は 3 つ。(1) データを正しく符号化した直感的な可視化で、理解を助ける。(2) 視覚的な混雑を減らす。(3) ばらばらのデータを 1 つにまとめて、認知負荷を下げる。例として、可視化を「関係するタスクごと」にまとめて切り替える、文脈に応じたデバッグツールを挙げる — [同上](https://par.nsf.gov/servlets/purl/10354657)
- 「過去と未来の状態を知りたい」が主題の 1 つ。24 名中 8 名（33%）が、実行前に全経由点をたどる様子を見る機能と、過去の動作を見直す機能を求めた。rosbag で再生はできるが、rqt を使っていたのは 3 名（12.5%）だけだった — [同上](https://par.nsf.gov/servlets/purl/10354657)
- ロボットのような分散システムでは、同じプログラムでも通信の遅れなどで結果が変わるので、ブレークポイント型のデバッグは使いにくい、と述べる — [同上](https://par.nsf.gov/servlets/purl/10354657)
- ①列の表現はない（その時点の状態の重ね描き）。②エラーの印はなく、利用者が状態から読み取る。③空間。④実行中。事前の下見と事後の再生は「要望」として出ている。

**9) An Augmented Reality Debugging System for Mobile Robot Software Engineers** — Toby Collett, Bruce A. MacDonald。Journal of Software Engineering for Robotics 1, 18–32, 2010。【書誌は Ikeda & Szafir の参考文献で確認。内容は要旨】

- ARDev。上から見た固定カメラの映像に、2D の AR 注釈でロボットのデータを重ねる。Ikeda & Szafir はこの研究を再現し、対象を 5 名から 24 名に増やした — [Ikeda & Szafir](https://par.nsf.gov/servlets/purl/10354657)、[JOSER 掲載版](https://aisberg.unibg.it/bitstream/10446/86156/1/7-143-1-PB.pdf)
- 依頼文の「Millard, Collett & MacDonald」は 2 つの別の研究である。Millard は次の ARDebug の著者。
- ①なし。②なし（センサ値と実世界のずれを目で見つける）。③空間。④実行中。

**10) ARDebug: An Augmented Reality Tool for Analysing and Debugging Swarm Robotic Systems** — Millard, Redpath, Jewers, Arndt, Joyce, Hilder, McDaid, Halliday。Frontiers in Robotics and AI 5:87, 2018。【書誌は Ikeda & Szafir の参考文献で確認。内容は要旨】

- 群ロボットの内部状態を、AR の図で見せる。オープンソースで、モジュール式 — [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC7805932/)
- ①なし。②なし。③空間（各ロボットの上）。④実行中。

**11) SENSAR: A Visual Tool for Intelligent Robots for Collaborative Human-Robot Interaction** — Andre Cleaver, Faizan Muhammad, Amel Hassan, Elaine Short, Jivko Sinapov。2020。【書誌は Ikeda & Szafir の参考文献で確認。内容は未確認】

- ロボットのセンサと認識のデータを AR で人に見せるツール — [Ikeda & Szafir の参考文献 [39]](https://par.nsf.gov/servlets/purl/10354657)

**12) ARviz – An Augmented Reality-enabled Visualization Platform for ROS Applications** — Hoang ほか（Monash 大）。arXiv 2110.15521。IEEE Robotics & Automation Magazine の XR 特集号に採録。【要旨】

- RViz に着想を得て、標準の ROS メッセージを AR で表示する。音声・ジェスチャ・視線の入力と、プラグインによる拡張がある — [arXiv](https://arxiv.org/abs/2110.15521)
- ①なし。②なし。③空間。④実行中。
- iviz（KIT-ISAS）は GitHub の存在だけ確認した。論文の書誌は確認できていない — [AR-RViz README](https://github.com/kodie-artner/AR-RViz)

**再生・事後の見直し**

**13) Mixed-Reality Robot Behavior Replay: A System Implementation** — Zhao Han, Tom Williams, Holly A. Yanco。AAAI Fall Symposium (AI-HRI) 2022、arXiv 2210.00075。【本文】

- 行動を Behavior Tree で分け、各サブツリーの単位でセンサデータと関節指令を MongoDB に記録する。あとで、その単位ごとに再生できる。対象は腕の操作、移動、プロジェクタによる AR、音声 — [NSF PAR PDF](https://par.nsf.gov/servlets/purl/10403587)、[ar5iv](https://ar5iv.labs.arxiv.org/html/2210.00075)
- 失敗の見せ方：腕の動きを物理的に再現しながら、緑の投影で「掴もうとした物」を示す。白の投影は正しく認識した物。これで「破れた木片を部品と誤認した」という知覚の失敗が分かる。移動では、黄色の球が床の障害物、紫の矢印が過去の迂回路 — [同上](https://ar5iv.labs.arxiv.org/html/2210.00075)
- 問題意識：過去に置いてあった物は、もう動かされたり無くなったりしているので、言葉だけでは指しにくい。ロボット自身が失敗に気づいていないこともある — [NSF PAR PDF](https://par.nsf.gov/servlets/purl/10403587)
- 別論文の評価（N=665）の要約：物理的な再現＋AR 投影＋音声の組み合わせが、最もよく伝わった。迂回の理由は、AR 投影だけでも 60% が推測できた — [ar5iv](https://ar5iv.labs.arxiv.org/html/2210.00075)
- ①Behavior Tree のサブツリー（行動の単位）。②色つきの投影。「失敗」専用の色はなく、正しい認識（白）と実際に選んだ物（緑）の食い違いで分かる。③空間が主で、時間は行動の単位。④事後。

**14) AR インタフェースとセンサデータ再生を、ロボットの故障診断で比べた研究**（題名は未確認）— International Journal of Social Robotics 2025（誌名は検索結果による）、DOI 10.1007/s12369-025-01219-4。【要旨の抜粋のみ】

- AR インタフェースと、センサデータの再生（故障の直前 15 秒をループ）を、よくあるロボットの故障の診断で比べた。「AR は実時間の可視化が中心で、失敗の再生や故障場面の再構成はあまり調べられていない」と述べる — [Springer](https://link.springer.com/article/10.1007/s12369-025-01219-4)
- ①故障前 15 秒の区間。②③④の詳細は未確認（事後であることは確か）。

**15) KITE: Keyframe-Indexed Tokenized Evidence for VLM-Based Robot Failure Analysis** — Mehdi Hosseinzadeh, King Hang Wong, Feras Dayoub。arXiv 2604.07034、ICRA 2026 採録。【要旨】

- 長い実行動画から、動きの目立つキーフレームを少数選ぶ。各キーフレームに、物の検出結果と、上から見た配置図（相対位置、軸、時刻、検出の確信度）を付ける。これを VLM に渡して、失敗の検出・特定・位置づけ・説明・修正をさせる — [arXiv](https://arxiv.org/abs/2604.07034)
- 人に見せる UI ではないが、「キーフレーム＋配置図＋時刻」は、失敗を時間と空間の両方に固定する表現として参考になる。④事後。

**Behavior Tree を使った説明**

**16) Building the Foundation of Robot Explanation Generation Using Behavior Trees** — Zhao Han ほか。ACM THRI 10(3), 2021。【書誌は LeMasurier 2024 の参考文献で確認】

- 自由な形の Behavior Tree を枠にはめて、ロボットの説明を作る。「どの行動に失敗したか」は言えるが、「なぜ失敗したか」を言う情報は足りなかった、と後続研究が述べている — [LeMasurier ほか 2024](https://faculty.cs.byu.edu/~crandall/papers/LeMasurier_etal_HRI2024.pdf)

**17) ABOD3-AR**（Rotsidis, Theodorou ほか）【未検証：正式な題名と会議名は確認していない】

- スマホのカメラで、追跡したロボットの上に、行動計画（Instinct プラン）の木の表示を重ねる — [IUI 2019 ワークショップ論文](https://ceur-ws.org/Vol-2327/IUI19WS-IUIATEC-3.pdf)
- ①木構造の計画。②今実行中のノードを強調する（エラー表示の有無は未確認）。③ロボットに固定。④実行中。

**形式検証・エンドユーザープログラミングでの指摘**

**18) Authoring and Verifying Human-Robot Interactions (RoVer)** — David Porfirio, Allison Sauppé, Aws Albarghouthi, Bilge Mutlu。UIST 2018、pp. 75–86、DOI 10.1145/3242587.3242634、Best Paper。【本文】

- 対話を状態遷移系として作る。部品は「マイクロインタラクション」（Greeter、Handoff、Farewell など）。モデル検査器が裏で動き、社会規範の違反を見つけて知らせる — [NSF PAR PDF](https://par.nsf.gov/servlets/purl/10080246)
- 見せ方：違反した性質を、設計中に実時間で、平易な英語の文の一覧として出す。例は「この対話は別れの挨拶で終わっていない」。画面には専用の feedback 欄がある — [同上](https://par.nsf.gov/servlets/purl/10080246)
- 位置づけ：性質によっては、違反の原因を特定のグループまで絞って示せる。絞り込めない性質もある — [同上](https://par.nsf.gov/servlets/purl/10080246)
- 視線の衝突は別扱いで、どちらの動作を優先するかを設計者に尋ねる — [同上](https://par.nsf.gov/servlets/purl/10080246)
- 評価（開発者 9 名）：形式検証があると、規範違反を見つけて文脈づける力が上がった — [同上](https://par.nsf.gov/servlets/purl/10080246)
- ①状態遷移図。②文の一覧＋一部はグループの強調。③時間（図の中のグループ）。空間への固定はない。④実行前（設計時）。

**19) Figaro: A Tabletop Authoring Environment for Human-Robot Interaction** — Porfirio, Stegner, Cakmak, Sauppé, Albarghouthi, Mutlu。CHI 2021。【本文】

- 机の上に環境の間取り図を投影し、人とロボットの人形を動かしながら話して、場面（scene）を実演する。場面をまとめて、プログラムを合成する — [NSF PAR PDF](https://par.nsf.gov/servlets/purl/10210854)
- フィードバック：人形の移動の軌跡を投影して、正しく追跡できていることを示す。認識できなかった発話や食い違う情報は、場面のあとにタブレットで尋ねる（Resolve モード）— [同上](https://par.nsf.gov/servlets/purl/10210854)
- 限界：ある参加者は、互いに矛盾する場面を実演した。評価時点の Figaro は、この矛盾を扱えなかった — [同上](https://par.nsf.gov/servlets/purl/10210854)
- ①場面の集まり（絵コンテに近い）。②タブレットでの質問。机上にエラーの印は出ない。③あいまいさの解消は場面の単位。④実行前。

**20) Sketching Robot Programs On the Fly (Tabula)** — Porfirio, Stegner, Cakmak, Sauppé, Albarghouthi, Mutlu。HRI 2023、pp. 584–593、arXiv 2302.03088。【本文】

- 音声で課題の核を言い、環境の 2D 地図の上に線を描いて、流れを指定する。描いた線を領域の列に直し、A* で行動の列を作る — [ar5iv](https://ar5iv.arxiv.org/html/2302.03088)
- 著者自身が「エンドユーザーへのフィードバックが足りない」と書いている。引き金があいまいな分岐などの誤りを示して直させることは、今後の課題。エンドユーザー向けソフトウェア工学の fault localization を、その方向として挙げる — [同上](https://ar5iv.arxiv.org/html/2302.03088)
- ①地図上のスケッチ＋有限オートマトン。②なし（今後の課題）。③④該当なし。

**21) Goal-Oriented End-User Programming of Robots (Polaris)** — David Porfirio, Mark Roberts, Laura M. Hiatt。HRI 2024、arXiv 2403.13988。【本文】

- ユーザーは「ゴールのオートマトン」を作る。青い節がチェックポイントで、中にゴールを入れる。そこから分岐つきの計画を実時間でコンパイルする — [arXiv](https://arxiv.org/html/2403.13988v1)
- Plan Visualizer は、意味ラベルつきの地図の上に、計画を 1 分岐ずつ左から右へ見せる。行動をクリックすると、その結果の世界の状態が出る。実行の前に、プランナの出力を人に見せるのが狙い — [同上](https://arxiv.org/html/2403.13988v1)
- 問題の扱い：ゴールが衝突すると（片腕で 2 つ持つなど）、そのチェックポイントと先の部分木を、黙ってコンパイルから外す。警告の色やアイコンは書かれていない。矛盾の自動検出と先回りのフィードバックは今後の課題 — [同上](https://arxiv.org/html/2403.13988v1)
- ①ゴールの木＋行動の列（地図に重ねる）。②明示的な印はない。計画から消えることで分かる。③計画は地図に重なるので、空間と時間の両方の土台はある。④実行前。

**22) Designing User-Centric Programming Aids for Kinesthetic Teaching of Collaborative Robots (Demoshop)** — Gopika Ajaykumar, Maia Stiber, Chien-Ming Huang。Elsevier 誌に投稿された版（掲載誌は Robotics and Autonomous Systems 2021 と記憶するが【未検証】）。【本文の一部】

- 手で教えた連続の軌道を、編集できる経由点に区切る（continuous path discretization）。状態の理解を助ける「mental scaffolds」と、コード補完に近い「just-in-time assistance」を備える — [著者 PDF](https://gopikaajaykumar.github.io/ajaykumar2021designing.pdf)
- 実機がすぐ動くボタンは、色と文字の警告表示で区別する。実行の前に、必ず動きの下見を見せて確認させる — [同上](https://gopikaajaykumar.github.io/ajaykumar2021designing.pdf)
- ①経由点の列。②危険な操作ボタンへの警告表示。③時間（経由点）。④実行前。

**23) RoboCritics: Enabling Reliable End-to-End LLM Robot Programming through Expert-Informed Critics** — Wisconsin 大（Kim ほか。著者全員の名前は【未検証】）。HRI '26、arXiv 2603.06842。【本文】

- 専門家が書いた「批評器（critic）」が、動作レベルの実行記録を調べる。見るのは関節速度の超過、衝突、危険な手先の姿勢 — [arXiv](https://arxiv.org/html/2603.06842v1)
- 画面は 3 つ。左が LLM とのチャットとコード。中央が批評器の一覧。右が 3D シミュレーション（再生できる）。違反は端末の欄に、OK / Warning / Error の 3 段階と、自然言語の説明とヒントで出る — [同上](https://arxiv.org/html/2603.06842v1)
- Fix ボタンを押すと、批評器の指摘が構造化されて LLM に送られ、修正版が作られる — [同上](https://arxiv.org/html/2603.06842v1)
- 3D 画面の中の印や、タイムライン上の印は書かれていない。批評器は各時刻のデータを見ているが、それをどう見せるかは述べていない — [同上](https://arxiv.org/html/2603.06842v1)
- 評価（18 名、UR3e）：批評器なしの LLM 画面より、安全違反が減り、実行の質が上がった — [プロジェクトページ](https://wisc-hci.github.io/RoboCritics)
- ①コード＋3D 再生。②3 段階の重大度＋文章。③固定なし（一覧のみ）。④シミュレーション実行のあと、実機の前。

### Inferences

- 「AR デバッグ」と「エラーを列に結びつける」は、別々の系統で発達している。前者（8〜12）は空間に強く、時間に弱い。後者（18、21、23）は時間（設計図の中の位置）に結びつけるが、実空間には出さない。両方を満たす例は、事後の再生（13）だけだった。
- 重大度を段階で示す例は RoboCritics（OK / Warning / Error）と VeriPlan（厳しさのスライダ、4 章）がある。RoVer は違反の一覧だけで、段階はない。
- Polaris の「衝突するゴールを黙って外す」は、反面教師として使える。計画から消えるだけでは、ユーザーは理由に気づけない。著者自身が先回りのフィードバックを課題に挙げている。
- Ikeda & Szafir の「事前に経由点をたどって見たい」「過去を見直したい」という要望（33%）は、時間軸を持つ AR 表示の必要性の、実証的な根拠になる。

### Gaps

- 「Behavior Tree を AR でデバッグする」ことを主題にした査読論文は、今回は見つからなかった。近いのは ABOD3-AR（計画の木をロボットに重ねる）と、Han ほかの BT 単位の再生。
- 「ロボットのタイムトラベル・デバッグ」を UI として扱う学術論文も見つからなかった。出てきたのは道具だけ（rosbag / rqt、Foxglove の比較モード、PyRoboReplay）— [Foxglove ブログ](https://foxglove.dev/blog/compare-robot-recordings-across-runs)、[PyRoboReplay](https://pypi.org/project/pyroboreplay/)
- ShARe という名前のツールは確認できなかった。
- Demoshop の just-in-time assistance の中身（どんな問題を、どう印で示すか）は、本文を読み切れていない。

---

## 3. 専門家でないユーザーに、ロボットの失敗や予測される失敗を、その場（空間）で伝える研究はどれか

### Takeaway

失敗の説明の研究（Das、LeMasurier、Diehl、REFLECT、AHA）は、ほぼすべて言葉による説明で、実空間に固定していない。逆に、AR／VR で物や場所に印を付ける研究（X-OOHRI、Wozniak、安全ゾーン）は、「タスクの何番目のステップか」を扱わない。「先に言うほうが良い」こと（LeMasurier）と、「物に直接付けると限界の理解が進む」こと（X-OOHRI）は、それぞれ別の研究で示されている。

### Cited Findings

**言葉による失敗の説明（空間に固定しない）**

**24) Explainable AI for Robot Failures: Generating Explanations that Improve User Assistance in Fault Recovery** — Devleena Das, Siddhartha Banerjee, Sonia Chernova。HRI '21、arXiv 2101.01625。【要旨】

- 専門家でない人が失敗の原因と直し方を見つけるには、「失敗の文脈」と「直前の行動の履歴」を含む説明が最も効いた。エンコーダ・デコーダで自動生成した説明は、見たことのないオフィス環境でも、手書きの説明と同じくらい効いた — [arXiv](https://arxiv.org/abs/2101.01625)
- ①行動の履歴（文の中）。②文章。③固定なし。④事後。

**25) Reactive or Proactive? How Robots Should Explain Failures** — Gregory LeMasurier, Alvika Gautam, Zhao Han, Jacob W. Crandall, Holly A. Yanco。HRI '24、pp. 413–422、DOI 10.1145/3610977.3634963。【本文】

- Reactive：Behavior Tree だけ。行動ノードが失敗してから説明する。Proactive：BT に「Assumption Checker」ノードを足す。システムと環境についての前提が破れたら、失敗しそうな行動を実行する前に、理由つきで説明する — [著者 PDF](https://faculty.cs.byu.edu/~crandall/papers/LeMasurier_etal_HRI2024.pdf)
- 説明は定型文。「課題を完了できませんでした。[失敗した行動] ができなかったので、[失敗したサブゴール] ができませんでした。[前提の説明] なので、[サブゴール] はできません」— [同上](https://faculty.cs.byu.edu/~crandall/papers/LeMasurier_etal_HRI2024.pdf)
- 結果（Prolific、N=224）：Proactive のほうが、知的に見え、信頼され、説明が分かりやすく、タイミングも良いと評価された。参加者は早い説明を好んだ — [同上](https://faculty.cs.byu.edu/~crandall/papers/LeMasurier_etal_HRI2024.pdf)
- ①Behavior Tree（サブゴール → 行動 → 前提）。②文章（サブゴール名と行動名を埋め込む）。③BT のノード、つまり時間。空間への固定はない。④両方を比べ、実行前のほうが良かった。

**26) Why Did I Fail? A Causal-Based Method to Find Explanations for Robot Failures** — Maximilian Diehl, Karinne Ramirez-Amaro。IEEE RA-L 7(4), 8925–8932, 2022、arXiv 2204.04483。【要旨】

- シミュレーションの実行から、因果ベイジアンネットを学ぶ。失敗した状態と、「成功したはずの最も近い状態」を比べて、対比的な説明を作る。積み木と球落としで、sim-to-real の精度は 70% と 72%。後続研究は、失敗の予測と予防に広げた — [arXiv](https://arxiv.org/abs/2204.04483)
- ①単一の行動。②対比の文章（「X が大きすぎた」）。③固定なし。④事後（後続は事前）。

**27) REFLECT: Summarizing Robot Experiences for Failure Explanation and Correction** — Liu ほか。CoRL 2023、arXiv 2306.15724。【書誌は既存の失敗サーベイによる】

- マルチセンサのデータと LLM で、失敗の説明と修正計画を作る — [arXiv](https://arxiv.org/abs/2306.15724)、[Diehl ほか 2026 による言及](https://arxiv.org/html/2603.11290v1)
- ①経験の階層的な要約（キーフレームと字幕）。②文章。③失敗した時刻の特定はする。空間はしない。④事後。（①〜③の細部は【未検証】）

**28) AHA: A Vision-Language-Model for Detecting and Reasoning over Failures in Robotic Manipulation** — ICLR 2025、arXiv 2410.00371。【書誌は既存の失敗サーベイによる】

- 失敗の検出と理由づけを、自然言語で出す VLM — [arXiv](https://arxiv.org/abs/2410.00371)。人向けの可視化はない。

**29) Generating Environment-based Explanations of Motion Planner Failure** — ICRA 2024、DOI 10.1109/icra57147.2024.10611577。【書誌と内容は既存の失敗サーベイによる】

- 動作計画が失敗した原因の物と、それをどこへ動かせば解けるかを示す — [DOI](https://doi.org/10.1109/icra57147.2024.10611577)
- ②原因の物を名指しする（空間への固定の候補）。④計画時。

**AR／VR で、物や場所に結びつけて伝える**

**30) Explainable OOHRI: Communicating Robot Capabilities and Limitations as Augmented Reality Affordances (X-OOHRI)** — Lauren W. Wang, Mohamed Kari, Parastoo Abtahi。HRI 2026 採録、arXiv 2601.14587。【要旨】

- ロボットに「できること／できないこと」を、AR のアフォーダンスとして物に付ける。部品は、視覚的な手がかり、放射状メニュー、色分け、説明タグ。VLM が物の性質とロボットの限界をオブジェクト指向の構造に入れ、説明をその場で作る。ユーザーは、実物に重ねた「仮想の双子」を直接動かす — [arXiv](https://arxiv.org/abs/2601.14587)
- 評価：参加者は物を起点に指示を出し、ロボットの限界について正確なメンタルモデルを作り、ロボットと一緒に問題を解決した — [arXiv](https://arxiv.org/abs/2601.14587)
- ①列は扱わない（物ごとの操作）。②色分け＋説明タグ。③空間（物）。④実行前と読めるが、要旨に明記はない。

**31) What You See Is (Not) What You Get: A VR Framework for Correcting Robot Errors** — Maciej K. Wozniak, Rebecca Stower, Patric Jensfelt, Andre Pereira。HRI '23 Companion、arXiv 2301.04919。【要旨】

- 既存の VR／AR ツールは、ロボットが正しく動く前提で作られている、と指摘する。ロボットが実物を検出しそこねたことを VR で見つけ、仮想の場面で直し、提案された物の軌道を調整してから、実機で実行する — [arXiv](https://arxiv.org/abs/2301.04919)
- ①列ではなく、物ごとの軌道。②ロボットの認識の結果と実物を並べ、足りない物で分かる。③空間。④実行前。

**32) Explainable Human-Robot Training and Cooperation with Augmented Reality** — Chao Wang, Anna Belardinelli, Stephan Hasler, Theodoros Stouraitis, Daniel Tanneberg, Michael Gienger。CHI EA 2023（DOI 10.1145/3544549.3583889）、arXiv 2302.01039。【要旨】

- 新しい課題の解き方の計画を、AR で人に見せて確認してもらう。ほかに、実演で教える場面と、支援中の意図の表示を扱う — [arXiv](https://arxiv.org/abs/2302.01039)
- ①AR 上の計画。②未確認。③空間。④実行前。

**33) Immersive Explainability: Visualizing Robot Navigation Decisions through XAI Semantic Scene Projections in Virtual Reality** — Jorge de Heuvel, Sebastian Müller, Marlene Wessels, Aftab Akhtar, Christian Bauckhage, Maren Bennewitz。arXiv 2504.00682。【要旨】

- 強化学習で動く移動ロボットについて、判断への寄与度（attribution）を、場面の物の強調として VR に投影する。24 名の評価で、専門家でない人の客観的な理解が有意に上がった。LiDAR の表示を足すと、予測しやすさの評価がさらに上がった — [arXiv](https://arxiv.org/abs/2504.00682)
- ①なし。②物の強調。③空間（物）。④実行中。失敗ではなく「判断の理由」だが、物に重要度を塗る方法として参考になる。

**34) Correct Robots Before They Make Mistakes: Proactive Human-in-the-Loop Intervention via Preference Learning (PHIL)** — Xinkai Jiang ほか 10 名（Lioutikov 研）。arXiv 2611.05667（2026-11）。【要旨】

- 学習済みの方策が予測した「これからの動き」を、XR で作業空間に下見として出す。操作者は、望ましくない行動が起きる前に介入する。4 つの実機課題で、平均の成功率が HG-DAgger より上がった（Diffusion Policy で 44.0% → 70.3%、X-VLA で 57.8% → 76.9%）— [arXiv](https://arxiv.org/abs/2611.05667)
- ①近い未来の軌道。②エラーの印はなく、人が下見から判断する。③空間。④実行前（数秒先）。

**35) AR-based Interaction for Safe Human-Robot Collaborative Manufacturing** — Antti Hietanen, Jyrki Latokartano, Roel Pieters, Minna Lanz, Joni-Kristian Kämäräinen。arXiv 1909.02933（掲載誌は Robotics and Computer-Integrated Manufacturing 2020 と記憶するが【未検証】）。【本文】

- 深度センサで作業空間を 3 つに分ける（人・ロボット・危険）。危険ゾーンは、HoloLens では半透明の赤い「仮想の柵」。人の領域で変化した場所は、強調表示する。危険ゾーンに何かが入ると、ロボットはすぐに止まる — [ar5iv](https://ar5iv.labs.arxiv.org/html/1909.02933)
- 画面には GO / STOP / CONFIRM / ENABLE のボタンと、ロボットの状態と指示を出す、画像＋文字の状態表示がある — [同上](https://ar5iv.labs.arxiv.org/html/1909.02933)
- 結果：やりとりのないベースラインより、作業時間が 21〜24%、ロボットの待ち時間が 57〜64% 減った — [arXiv](https://arxiv.org/pdf/1909.02933)
- ①なし。②赤い柵＋変化した領域の強調＋ロボットの停止。③空間。④実行中（予防）。

**36) HoloLens 2 による安全ゾーンの可視化**（Cogurcu ほか、Leeds 大学／White Rose。題名は【未検証】）

- ロボットアームのまわりの安全ゾーンを、いくつかの描き方で出す。ユーザーがゾーンに入ると警告する。色は赤。「多くの国で警告の合図だから」という理由。どの描き方が最良かは、利用者での試験が要る、と述べている — [White Rose PDF](https://eprints.whiterose.ac.uk/174782/1/Edited___UK_RAS_conference_latex_template_10_17_19_Yunus_Cogurcu.pdf)、[続報](https://eprints.whiterose.ac.uk/198148/1/computers-12-00075.pdf)

**37) Communicating Robot Arm Motion Intent Through Mixed Reality Head-Mounted Displays** — Rosen ほか。ISRR 2017、arXiv 1708.03655。【要旨】

- 計画した腕の動きを、HMD で実空間に重ねる。32 名が「この動作計画は衝突するか」を判定する課題で、HMD、2D 画面、可視化なしの 3 条件を比べた — [ar5iv](https://ar5iv.labs.arxiv.org/html/1708.03655)
- ①腕の軌道（残像の列）。②衝突の印はなく、人が軌道を見て判定する。③空間。④実行前。

**38) Communicating Robot Motion Intent with Augmented Reality** — Walker, Hedayati, Lee, Szafir。HRI '18。【要旨】

- 飛行ロボットの動きの意図を AR で示す設計を、いくつか比べた。複数の設計が、ベースラインより課題の効率を有意に上げた — [著者 PDF（ResearchGate）](https://researchgate.net/profile/Hooman-Hedayati/publication/323595221_Communicating_Robot_Motion_Intent_with_Augmented_Reality/links/5abbed870f7e9bfc04559830/Communicating-Robot-Motion-Intent-with-Augmented-Reality.pdf)
- ①経由点の列（NavPoints など）。②なし。③空間（経由点に時刻の情報を添える）。④実行前。

**題名だけ確認した関連研究**（内容は【未検証】）

- **39) Mixed Reality Outperforms Virtual Reality for Remote Error Resolution in Pick-and-Place Tasks** — [arXiv 2502.06141](https://arxiv.org/html/2502.06141v1)
- **40) GhostObjects: Instructing Robots by Manipulating Spatially Aligned Virtual Twins in Augmented Reality** — [arXiv 2508.11022](https://arxiv.org/html/2508.11022v1)。X-OOHRI の前段にあたる「仮想の双子」。
- Politecnico di Torino の 2018 年の論文は、AR で産業用ロボットの故障を実時間に表示する — [PDF](https://iris.polito.it/retrieve/handle/11583/2711096/379424)。依頼文の「De Pace」の研究の可能性があるが、著者は確認していない。

### Inferences

- 「いつ伝えるか」は、先回りのほうが評価が高い（LeMasurier）。「どこに付けるか」は、物に直接付けると限界の理解が進む（X-OOHRI）。この 2 つを同じシステムで組み合わせて評価した研究は、今回は見つからなかった。
- 説明文に入れると効く情報は、「文脈」と「直前の行動の履歴」（Das）と、「失敗するサブゴールと、その原因になる前提」（LeMasurier）。AR のラベルに書く短文の型として、「[前提] なので、[ステップ] ができません」が使える。
- 色の使い方は、研究どうしでそろっていない。安全ゾーンは赤（Hietanen、Cogurcu）。Han ほかの再生は、緑が「選んだ物」、白が「正しく認識した物」で、色がそのままエラーを意味しない。
- Wozniak ほかの「既存のツールはロボットが正しい前提で作られている」という指摘は、今回集めた AR 意図表示の研究（37、38）にも当てはまる。軌道は見せるが、どこが危ないかは人に判定させている。

### Gaps

- Honig & Oron-Gilad の失敗の分類は、既存の失敗サーベイで扱い済みなので、ここでは調べ直していない。
- 到達できる範囲（reachability）と、不確かさを AR で示す研究は、今回の検索では具体的な論文を確認できなかった。ERUPT（[arXiv 2510.02464](https://arxiv.org/pdf/2510.02464)、XR から動作計画器を使う公開ツールキット）は題名だけ確認した。
- REFLECT と AHA の、人向けの見せ方（図の中で失敗の時刻をどう示すか）は、本文で確認していない。
- X-OOHRI の色分けの中身（何色が何を意味するか）と、実行の前に出るかどうかは、本文の確認が要る。

---

## 4. LLM のタスクプランナで、ステップごとの不確かさや、失敗しそうなステップをユーザーに見せる研究はどれか

### Takeaway

KnowNo、Introspective Planning、CLARA は、不確かなときに「質問する」ことで伝える。どのステップが怪しいかを、計画の列の上で示す UI は作っていない。計画と制約の食い違いを画面に出すのは VeriPlan と U-Define で、マインドマップ型の配置と「破られたルールの一覧」を使う。LLM の計画を AR で下見させる研究はあるが、エラーの印は付けず、承認するか却下するかを人に任せている。

### Cited Findings

**41) Robots That Ask For Help: Uncertainty Alignment for Large Language Model Planners (KnowNo)** — Ren ほか。CoRL 2023。【内容は検索結果の要約による。arXiv 番号 2307.01928 は記憶によるので【未検証】】

- LLM が出した次のステップの候補に、conformal prediction をかける。予測集合に候補が 2 つ以上残ったら、実行せずにユーザーに尋ねる。目標の成功率を保証しつつ、尋ねる回数を減らす — [Introspective Planning 論文内の説明](https://arxiv.org/html/2402.06529v2)、[arXiv（番号は未検証）](https://arxiv.org/abs/2307.01928)
- ①次の 1 ステップの選択肢。②選択肢つきの質問。③時間（今のステップ）。空間はなし。④実行前（各ステップの直前）。

**42) Introspective Planning: Aligning Robots' Uncertainty with Inherent Task Ambiguity** — Liang, Zhang, Fisac。arXiv 2402.06529（NeurIPS 2024 と記憶するが【未検証】）。【要旨】

- LLM のプランナは、指示とずれた計画や危険な計画を、自信を持って実行してしまうことがある。微調整なしで、モデルに自分の不確かさを考えさせる。あいまいなときは、ユーザーに確認を取る。成功率と安全性の両方が上がった — [arXiv](https://arxiv.org/html/2402.06529v2)
- ①②③④は KnowNo と同じ型（質問で伝える）。

**43) CLARA: Classifying and Disambiguating User Commands for Reliable Interactive Robotic Agents** — RA-L。【書誌は既存の失敗サーベイによる。arXiv 番号 2306.10284 は記憶によるので【未検証】】

- 指示を certain / ambiguous / infeasible に分ける — [既存サーベイ `docs/failure_survey/README.md` の G の項](https://arxiv.org/abs/2306.10284)
- ①指示の全体（ステップ単位ではない）。②3 つの分類＋質問。③固定なし。④実行前。

**44) VeriPlan: Integrating Formal Verification and LLMs into End-User Planning** — Christine Lee, David Porfirio, Xinyu Jessica Wang, Kevin Zhao, Bilge Mutlu。CHI '25、arXiv 2502.17898。【本文（先頭 10 万字）】

- LLM のプランナに、3 つの機能を足す。ルール翻訳器（依頼文から制約を取り出す）、柔軟さのスライダ、モデル検査器（PRISM）— [arXiv](https://arxiv.org/html/2502.17898v1)
- 画面は「マインドマップ型」。ルール、入力、出力、衝突を、つながったブロックとして置く。モデル検査器の結果は、「破られたルールの一覧」か、計画が妥当だという確認。検査器は、計画の各状態について、ルール違反を調べる — [同上](https://arxiv.org/html/2502.17898v1)
- スライダは、ルールごとの厳しさを割合で決める。高いと絶対の制約になり、違反する計画は却下される。低いと、違反してもよいがユーザーに知らせる — [同上](https://arxiv.org/html/2502.17898v1)
- 参加者の声：この配置で「計画が何か、衝突がどこで起きたか、なぜ起きたか」が見やすくなった。評価は 12 名 — [同上](https://arxiv.org/html/2502.17898v1)
- ロボットではなく、一般の計画作り（予定など）が対象。
- ①ブロックの図。②破られたルールの一覧＋衝突のブロック。③図の中の位置。違反がどの時点かを示すかは、未確認。④実行前。

**45) U-Define: Designing User Workflows for Hard and Soft Constraints in LLM-Based Planning** — Christine P Lee, Xinyu Jessica Wang, Aws Albarghouthi, David Porfirio, Bilge Mutlu。arXiv 2605.02765（2026-05）。【要旨】

- ユーザーが、自然言語で書いた制約に、hard か soft かを付ける。hard は形式的なモデル検査で、soft は LLM による判定で確かめる。結果を見て、制約を直せる — [arXiv](https://arxiv.org/abs/2605.02765)
- ①②の UI の細部は未確認。④実行前。

**46) Enabling Waypoint Generation for Collaborative Robots using LLMs and Mixed Reality** — arXiv 2403.09308。【要旨の抜粋。著者は未確認】

- LLM が作った経由点を、AR ヘッドセットで実環境に重ねて下見する。承認した計画だけを、ロボットが実行する — [arXiv](https://arxiv.org/pdf/2403.09308)
- ①経由点の列。②なし（承認か却下か）。③空間。④実行前。

**47) A Human-in-the-loop Approach to Robot Action Replanning through LLM Common-Sense Reasoning** — arXiv 2507.20870。【要旨の抜粋。著者は未確認】

- ユーザーが、ロボットの計画を自然言語で見直して直す。対話的な修正と、幻覚の訂正が、頑健さを上げた。AR は使わない — [arXiv](https://arxiv.org/abs/2507.20870)

（再掲）**23) RoboCritics** と **32) Wang ほか 2023** も、LLM の計画やプログラムを、実行の前に人に見せる例。前者は OK / Warning / Error の文章、後者は AR 上の計画の確認。

### Inferences

- LLM プランナの不確かさの研究は、「聞くか、聞かないか」を決める仕組みが中心で、その不確かさを計画の列の上に描く UI は手薄。KnowNo の予測集合の大きさは、そのまま「このステップは候補が 2 つある」という印に使えるが、そう見せた研究は今回見つからなかった。
- 「hard は却下、soft は知らせるだけ」という VeriPlan／U-Define の区別は、エラーの重大度を 2 段階にする設計の先例になる。RoboCritics の Warning / Error と同じ型である。
- 形式検証を使う研究（RoVer、VeriPlan、U-Define）は、どれも Mutlu 研と Porfirio の系統。「違反したルールの名前を、平易な文で出す」ところは共通している。違反した時点を列の上で指す機能は、どれも明確には書いていない。

### Gaps

- 「計画の各ステップに、確信度を色で付ける UI」を主題にした論文は、今回の検索では確認できなかった。
- VeriPlan が、違反の反例（どの状態で破れたか）をユーザーに見せているかは、本文の残り 4.5 万字を読んでいないので未確認。
- 2403.09308 と 2507.20870 の著者と掲載先は、確認していない。

---

## 5. HCI 一般で、「列＋エラーの印」の類例は何か（TAP のデバッガ、プロセスマイニング、AR 組立ガイド）

### Takeaway

ロボット以外では、「タイムラインの上で、おかしかった時刻を印す」（スマートホームの TAP デバッグ）、「工程図の各活動を、逸脱の度合いで塗る」（プロセスマイニング）、「実物の部品に、今の位置と目標の位置の枠を出す」（AR 組立）という 3 つの型が確立している。どれも、列か空間のどちらか一方への固定で、両方を同時に扱う例は見つからなかった。

### Cited Findings

**トリガー・アクション（TAP）のデバッグ**

**48) Helping Users Debug Trigger-Action Programs** — Lefan Zhang, Cyrus Zhou, Michael L. Littman, Blase Ur, Shan Lu。Proc. ACM IMWUT 6(4), Article 196, 2022、DOI 10.1145/3569506。【本文】

- デバッグを 4 段階に分ける。(I) おかしな挙動に気づく。(II) 原因のルールを突き止める（fault localization）。(III) 修正案を出す。(IV) 修正を練る — [NSF PAR PDF](https://par.nsf.gov/servlets/purl/10387467)
- History Visualization：自動化の出来事とその文脈を、タイムラインで見直す。ユーザーは、タイムラインをクリックして、「ここがおかしい」（間違った自動化、または欠けている自動化）と印を付ける — [同上](https://par.nsf.gov/servlets/purl/10387467)
- Trace Analysis：履歴から、間違っていそうな、または欠けていそうな自動化を、自動で見つける。人がよく手で操作しているなら、自動化が欠けている。人がよく元に戻しているなら、自動化が間違っている — [同上](https://par.nsf.gov/servlets/purl/10387467)
- Patch Behavior Visualization：「この修正を当てていたら、履歴はどう変わっていたか」を見せる — [同上](https://par.nsf.gov/servlets/purl/10387467)
- 評価：遠隔の 30 名が、3D のスマートホームのシミュレータで、合計 84 時間デバッグした。履歴からおかしな時刻を探す作業が、最も時間がかかった。そこで、その時刻を自動で推定する流れも用意した — [同上](https://par.nsf.gov/servlets/purl/10387467)
- ①出来事のタイムライン。②ユーザーが付ける印＋自動で見つけた候補。③時間。④事後。修正の下見は「もしも」の再生。

**49) AutoTap: Synthesizing and Repairing Trigger-Action Programs Using LTL Properties** — Zhang ほか。ICSE 2019。【要旨】

- 初心者が、望む性質（LTL）を書く。そこから、ルールを合成したり直したりする。利用者の評価では、ルールを直接書くより、性質で書くほうが、誤りが有意に少なかった — [GitHub README](https://github.com/zlfben/autotap/blob/master/README.md)、[著者 PDF](https://homes.cs.washington.edu/~jessejm/data/ZhangICSE2019.pdf)
- ①ルールの集合。②違反は見せずに、自動で直す。④実行前。

**50) Trace2TAP: Synthesizing Trigger-Action Programs from Traces of Behavior** — Zhang ほか。IMWUT 2020（DOI 10.1145/3411838 は検索結果の Crossref リンクによる。【未検証】）。【要旨】

- 時刻つきのセンサ値と手動操作のログ（trace）から、ルールを合成する。実地の評価で、参加者は上位に並んだルールをよく選んだ — [Crossref](https://api.crossref.org/works/10.1145%2F3411838)
- 後続の論文は、これを「合成した新しいルールが起こす自動化の出来事を、タイムラインで見せた」先行例として引いている — [Zhang ほか 2022](https://par.nsf.gov/servlets/purl/10387467)

**51) How Users Interpret Bugs in Trigger-Action Programming** — Brackenbury ほか。CHI 2019。【要旨。著者と会議は記憶によるので【未検証】】

- TAP のバグを 10 種類に分ける。バグがあると、参加者が結果を予測するのは有意に難しくなった — [要旨（SciSpace）](https://scispace.com/papers/how-users-interpret-bugs-in-trigger-action-programming-3weyccz6mk)

**52) EUDebug**（Corno, De Russis, Monge Roffarello。CHI 2019。正式な題名は【未検証】）

- トリガー・アクションのルールを作っている最中に、問題を見つけて理解するのを助ける。参加者は、既存の環境では見つけにくい問題の発見に役立つ、と評価した — [Politecnico di Torino リポジトリ](https://iris.polito.it/retrieve/handle/11583/2724318/231604)
- ①ルールの集合。②作成時の問題の指摘（ループ、矛盾など。細部は未確認）。④実行前。

**53) Whyline（Ko & Myers、2004）と、問いかけ型デバッグ** 【未検証：書誌は記憶による】

- TAP のデバッグ研究（Manca ほか 2019）が、Interrogative Debugging を下敷きにしている — [Manca ほか（CNR リポジトリ）](https://openportal.isti.cnr.it/data/2019/404663/2019_404663.postprint.pdf)。Ikeda & Szafir も、Ko & Myers の "Debugging reinvented"（ICSE 2008）を引いている — [Ikeda & Szafir の参考文献 [27]](https://par.nsf.gov/servlets/purl/10354657)
- 「なぜ起きたか／なぜ起きなかったか」を、ユーザーが尋ねる型。スマートホームで「なぜ〜しなかったのか」を扱う CHI 論文は、今回は特定できなかった。

**54) End-User Software Engineering** — Margaret Burnett, Curtis Cook, Gregg Rothermel。Communications of the ACM 47(9), 2004。【書誌は Tabula の参考文献で確認】

- エンドユーザーに、fault localization などの標準的な手法を届ける研究の流れ。Tabula は、ロボットの EUP にこれを取り入れることを課題に挙げる — [Tabula（ar5iv）](https://ar5iv.arxiv.org/html/2302.03088)

**プロセスマイニング（適合性検査）**

**55) Process Mining Meets Visual Analytics: The Case of Conformance Checking** — Rehse, Pufahl ほか。arXiv 2209.09712。【要旨】

- プロセスマイニングのツールが、適合性検査の結果をどう見せているかを調べた。結論は、「適合性検査の結果の可視化は、研究ではあまり扱われてこなかった」— [arXiv](https://arxiv.org/abs/2209.09712)

**56) CC Viz（ICPM 2025 のデモ）と、時間つきの逸脱の可視化**【要旨。著者は未確認】

- BPMN の図を描き、各活動を適合の度合いで塗る。薄い色は適合、濃い色は違反。度合いは、「その活動が飛ばされた、または余分に入った実行の割合」— [CEUR Vol-4088](https://ceur-ws.org/Vol-4088/paper_241.pdf)
- 既存のツールは、逸脱を集計して工程図に重ねられる。しかし、時間の情報を組み込んだものはない、という指摘 — [CEUR Vol-3628](https://ceur-ws.org/Vol-3628/paper1.pdf)
- ①工程図（BPMN）。②色の濃さ。③列（活動）。④事後（多くの実行の集計）。

**57) A Task Taxonomy for Conformance Checking** — arXiv 2507.11976。【要旨】

- 適合性検査の可視化を評価するための、課題の分類を出す。可視化の開発は、これまでツールの業者に任されてきた、と述べる — [arXiv](https://arxiv.org/html/2507.11976v1)

**AR の組立・保守ガイド**

**58) Augmented Assembly: Object Recognition and Hand Tracking for Adaptive Assembly Instructions in Augmented Reality** — Alexander Htet Kyaw, Haotian Ma, Sasa Zivkovic, Jenny Sabin。arXiv 2601.11535（TEI '26 に投稿）。【要旨】

- HoloLens 2 で、物体認識と手の追跡を使い、手順を 1 つずつ出す。手の追跡で、正しい部品を持っているかを調べる。AR の枠（bounding box）で、各部品の今の位置と目標の位置を示す。順序を強制せず、組立の誤りの候補を強調して、逸脱をやり直しの機会として扱う — [arXiv](https://arxiv.org/abs/2601.11535)
- ①手順の列。②部品の枠の強調。③空間（部品）＋今のステップ。④実行中。

**59) Error Management for Augmented Reality Assembly Instructions** — IEEE の会議論文（著者と会議名は【未検証】）。【要旨の抜粋】

- 手順を短いステップに分ける。組立の状態を実時間で認識する物体検出器を、対照学習で学習する。AR アプリが誤りを警告し、直すための視覚的な助けを出す — [IEEE Xplore](https://ieeexplore.ieee.org/document/10765434)
- ①短いステップの列。②警告＋直し方の図示。③空間＋ステップ。④実行中（誤りの直後）。

**60) デジタルツインの重ね描きの比べ方（VINCI 2025）**【要旨の抜粋。題名と著者は未確認】

- 先行研究のまとめ：検査では、輪郭線（outline）が全体として最もよい。向きを間違えた部品を見つけるには、半透明の描画のほうが効く — [Hasselt 大リポジトリ](https://documentserver.uhasselt.be/bitstream/1942/48158/1/vinci_2025_paper.pdf)

### Inferences

- TAP のデバッグの 4 段階（気づく → 突き止める → 直す案 → 練る）は、ロボットの計画の下見にもそのまま当てはまる。Zhang ほかで最も時間がかかったのは、「おかしな時刻を探す」段階だった。列の上にエラーの位置をあらかじめ示せば、この段階を短くできる見込みがある。
- 「修正を当てたらどうなっていたか」の再生（Patch Behavior Visualization）は、ロボットの計画でも使える型。物の置き場所を変えたら、どのステップのエラーが消えるかを見せる、という形になる。
- プロセスマイニングの「色の濃さ＝逸脱の頻度」は、1 回の計画には直接は使えない。ただし、不確かさ（どのくらい失敗しそうか）を濃さで表す設計には流用できる。
- AR 組立ガイドは、「実物に付く枠」と「今のステップ」の両方を持つ。これが、今回見つけた中で、空間と列を同時に扱う最も近い類例。ただし誤りを起こすのは人で、ロボットではない。

### Gaps

- スマートホームでの「なぜ〜しなかったのか（why not）」の説明を扱う CHI 論文は、特定できなかった。
- ワークフローの来歴（provenance）の可視化で、エラーを注記する研究は調べられていない。
- AR 組立の誤り検出の古典（検索結果は Khuong ほかの積み木の研究を挙げた）は、書誌を確認していない。
- 51〜53 の書誌は、記憶によるところが大きい。引用する前に確認が要る。

---

## 6. 統合：パイプラインの各段階で、エラー表示をどこに付けられるか（カタログ）

### Takeaway

8 段階のどこにも、先行例は少なくとも 1 つある。ただし先行例は、「物や場所に付ける型」（知覚、動作計画、実行）と、「列のステップに付ける型」（計画、ルール検査）に分かれていて、同じエラーを両方に結びつけて見せるものは、事後の再生（Han ほか）と AR 組立ガイドだけだった。事前に、列と空間の両方へ結びつける表示は、今回の調査の範囲では空いている。

### Cited Findings

下の表は、1〜5 章で出典を示した事実だけを並べ直したもの。「先行例」の番号は、本文の論文番号。

| 段階 | 起きるエラー（既存サーベイの記号） | 付けられる場所 | 先行例と、その見せ方 | 固定 | 時点 |
|---|---|---|---|---|---|
| ① 指示（自然言語） | あいまい・実行不能（G） | 指示文そのもの。指示の中の語 | CLARA（43）：certain / ambiguous / infeasible の分類。KnowNo（41）：選択肢つきの質問 | なし（文） | 事前 |
| ② 言語理解・グラウンディング | 違う物を指す（C） | 語と物の対応。候補の物それぞれ | X-OOHRI（30）：物に色分けと説明タグ。KnowNo（41）：候補が複数残ったら尋ねる | 空間（物） | 事前 |
| ③ 知覚・物体認識 | 見落とし、誤認（C） | 認識した物の上。見落とした実物の場所 | Wozniak ほか（31）：VR で認識の結果と実物を比べ、足りない物を直す。Han ほか（13）：白＝正しく認識、緑＝実際に選んだ物。Immersive Explainability（33）：物の強調。KITE（15）：検出の確信度つきの配置図 | 空間（物） | 事前／事後 |
| ④ タスク計画（行動の列） | 手順の抜け・順序違い・前提の見落とし（D） | 列のステップ。ステップが対象にする物 | Polaris（21）：地図に重ねた計画を 1 分岐ずつ見せる（印はない）。LeMasurier（25）：BT のサブゴール＋行動＋前提を文にする。Wang ほか（32）：AR で計画を確認させる | 時間（ステップ）。Polaris は地図にも重なる | 事前 |
| ⑤ ルール・制約の検査 | 規範・安全の違反（H） | 違反したルールの名前。違反を起こすステップやグループ | RoVer（18）：平易な文の一覧＋一部はグループまで絞る。VeriPlan（44）：破られたルールの一覧＋衝突のブロック＋厳しさのスライダ。U-Define（45）：hard / soft。RoboCritics（23）：OK / Warning / Error | 時間（図の中の位置）。空間はなし | 事前 |
| ⑥ 動作計画 | 届かない、経路がない、衝突（A・B） | 軌道の上の点。邪魔な物。届かない目標の位置 | Rosen ほか（37）：軌道を重ね、衝突するかは人が判定。環境ベースの説明（29）：原因の物と、動かす先。RoboCritics（23）：関節速度・衝突・手先の姿勢を文で。PHIL（34）：数秒先の動きの下見 | 空間（軌道・物） | 事前 |
| ⑦ 実行 | 掴み損ね、滑り、力の超過、人の接近（E・H） | ロボットの手先。安全ゾーン。今のステップ | Hietanen ほか（35）：赤い仮想の柵＋変化した領域の強調＋停止。Cogurcu ほか（36）：赤いゾーン＋侵入の警告。RoboVisAR（1）：Proximity / Box / Force-Torque の条件で、可視化を出し分ける。AR 組立（58、59）：部品の枠＋警告 | 空間。今のステップにも付けられる | 実行中 |
| ⑧ 結果の検証 | 最終状態が目的と違う（D・I） | 終わったあとの物の場所。失敗した時刻 | Han ほか（13）：BT の単位で再生し、投影で物を示す。Zhang ほか（48）：タイムラインに、おかしな時刻を印す。REFLECT（27）・KITE（15）：失敗の時刻の特定とキーフレーム。Das（24）：文脈＋行動の履歴の文 | 時間が主。Han ほかは空間も | 事後 |

**見せ方の部品（先行例に出てきたもの）**

- **色**：赤い領域・柵（35、36）。色の濃さで度合い（56）。色分け（30）。白と緑で「正しく認識した物」と「選んだ物」（13）。
- **形**：軌道・経由点（37、38、46）。枠（58）。輪郭線と半透明（60）。球と矢印（13）。
- **文**：違反したルールを平易な文で（18、44）。「[前提] なので [サブゴール] ができません」の定型文（25）。3 段階の重大度つきの説明とヒント（23）。説明タグ（30）。
- **問いかけ**：選択肢つきの質問（41、42）。優先順位を尋ねる（18 の視線の衝突）。場面のあとの確認（19）。
- **操作**：ワンクリックの修正（23）。厳しさのスライダ（44）。「修正したらどうなっていたか」の再生（48）。仮想の双子を動かして直す（30、31）。

### Inferences

- 表の「固定」の列を見ると、①④⑤は時間（列や文）に、②③⑥⑦は空間に寄っている。エラーが起きる段階によって、自然な固定先が変わる。計画やルールのエラー（④⑤）を空間に出すには、「そのステップが対象にする物や場所」へ写す一手間が要る。先行例でこれに最も近いのは、Polaris の「地図に重ねた計画」と、X-OOHRI の「物に付けた説明タグ」。
- 逆に、知覚や動作計画のエラー（③⑥）を列に出すには、「その物を使うのは何番目のステップか」をたどる必要がある。これを UI として示した先行例は、今回は見つからなかった。
- 重大度の段階づけは、3 つの研究で独立に現れている（RoboCritics の Warning / Error、VeriPlan の厳しさ、U-Define の hard / soft）。「止めるエラー」と「知らせるだけの注意」を分けるのは、複数の研究が支持する設計と言える。
- 事前に出すほうが良い、という結果は LeMasurier（説明のタイミング）にある。ただしこれは言葉での説明についての結果で、AR の印についての同じ比べ方は、まだない。
- RoboVisAR の条件の仕組み（1 章）は、⑦の実行中の出し分けにそのまま使える。④〜⑥の事前のエラーには、「記録した実行」の代わりに「シミュレーションした実行」をタイムラインに置けば、同じ枠組みに載る。Ikeda & Szafir の参加者の 33% が求めた「事前に経由点をたどって見る」機能と、方向が合う。

### Gaps

- 「1 つのエラーを、列のステップと実空間の物の両方に、事前に結びつけて見せる」システムは、今回の調査では見つからなかった。ただし、見つからなかったことは、存在しないことの証明ではない。調べたのは Web 検索と、取得できた本文だけで、ACM DL と IEEE Xplore は直接検索していない。
- 複数のエラーが同じ物や同じステップに重なるときの見せ方（優先順位、まとめ方）を扱う研究は、確認できなかった。Ikeda & Szafir の「混雑を減らす」「タスクごとにまとめる」という指針が、いちばん近い。
- 色の意味づけ（赤＝危険、など）を、ロボットのエラー表示で比べた評価は、確認できなかった。Cogurcu ほかは、「どの描き方が最良かは、利用者での試験が要る」と書いている。
- 表の中で【未検証】の印がある論文（17、22 の掲載誌、36、39、40、41 と 43 の arXiv 番号、46、47、49〜53、56、59、60）は、書誌か内容の一部を確かめていない。引用する前に、原典の確認が要る。
