# E. ルールの範囲と、インタラクション設計・研究貢献との関係

調査日：2026-11-22。既存レポート（`reports/AR計画可視化とエラー表示 文献調査.md` 本文）と `docs/rule_survey/README.md` を前提にし、重複する説明は省いた。

確認度の書き方

- **【全文】**：Zotero の全文キャッシュ、または取得した PDF を `pdftotext` で文字にして自分で該当行を読んだもの。
- **【全文W】**：arXiv の HTML 全文を WebFetch（要約モデル）経由で読み、引用文を抜き出させたもの。引用前に原文と突き合わせること。
- **【要旨】**：要旨・著者ページ・検索結果の抜粋まで。
- **【未検証】**：題名と書誌のみ、または調査者の記憶。引用前に原典確認が要る。

「見つからなかった」は Web 検索と手元の全文の範囲での結果で、ACM DL・IEEE Xplore の直接検索はしていない。

ルールは「N 種類」に分けず、次の次元で扱う（本ノートで使う呼び名）。

| 次元 | 値の例 | 根拠にした枠組み |
|---|---|---|
| 判定する時間範囲 | 終了時の状態だけ（at end）／途中の全状態（always）／順序（sometime-before）／期限（within） | PDDL3 の state trajectory constraints |
| 主語（何についてのルールか） | 物体／場所・領域／ロボットの動き方（速さ・音）／人／時刻 | Walker らの VDE 分類、Pascher らの intent 分類 |
| 厳しさ | 必ず守る／できれば守る | PDDL3 strong / soft、VeriPlan のスライダ |
| 誰が登録し、誰が外せるか | 本人／他の住人／管理者 | Zeng & Roesner の role-based / reactive access control |
| 違反が計画に与える形 | 物が動かない／置き場所が変わる／経路が変わる／順序や時刻が変わる／計画全体が立たない | X-OOHRI の Alternative、Reality Promises の rectification、Polaris の黙った除外 |
| 判定の確からしさ | 記号で決まる／属性の推定に依存する（「壊れ物」「父の物」） | X-OOHRI の VLM 誤り、KnowNo |

---

## 1. ルールの次元は、どの表示形式に自然に載るか（Before/After で見せられるもの・見せられないもの）

### Takeaway

Before/After（事後状態）で自然に見せられるのは「判定する時間範囲＝終了時」かつ「違反の形＝物が動かない／置き場所が変わる」ルールだけで、途中の状態に関わるルール（経路・順序・速さ・音・時刻）は事後状態に痕跡を残さない。先行研究は、領域には領域の重畳、経路には軌道の重畳、順序にはステップ列、理由には文章、と主語ごとに別の固定先を使っており、1 つの表示形式で全部を受けた例は見つからなかった。

### Cited Findings

**(a) 「終了時の状態」と「途中の状態」の区別は計画言語に既にある**

- PDDL3 は制約を 2 系統に分ける。原文：「The proposed extended language, PDDL3, allows us to express strong and soft constraints on plan trajectories (that is, constraints over possible actions in the plan and intermediate states reached by the plan), as well as strong and soft problem goals」【全文】 — [Gerevini & Long, ICAPS-06 WS](https://artificial-intelligence.unibs.it/gerevini/papers/WS-PREF-ICAPS06.pdf)
- 同：「State trajectory constraints assert conditions that must be met by the entire sequence of states visited during the execution of a plan.」基本の演算子は「always, sometime, at-most-once, and at end (for goal state conditions)」に within（期限）、sometime-after、sometime-before、always-within を加えたもの【全文】 — [同上](https://artificial-intelligence.unibs.it/gerevini/papers/WS-PREF-ICAPS06.pdf)
- 同：「Strong constraints and goals must be satisfied by any valid plan, while soft constraints and goals express desirable outcomes」【全文】 — [同上](https://artificial-intelligence.unibs.it/gerevini/papers/WS-PREF-ICAPS06.pdf)
- 例として「a fragile block can never have something above it」が trajectory constraint に挙がる【全文】。「壊れ物の上に物を置かない」は、終了時だけでなく途中でも守るべきルールとして書かれている — [同上](https://artificial-intelligence.unibs.it/gerevini/papers/WS-PREF-ICAPS06.pdf)

**(b) 物体に残す＋ラベル（主語＝物体、違反の形＝動かない）**

- X-OOHRI は物体を赤く塗り、説明タグを付ける。「if an object cannot be picked by any of the available robots, its GhostObject appears red and immovable」「Explanation tags complement color coding by labeling constraint causes and can expand into detailed tooltips, with content initialized from common errors and extended as new failure types arise.」【全文】 — [X-OOHRI](https://doi.org/10.1145/3757279.3785569)
- VAM-HRI の分類には物体に付ける表示が 2 つある。Entity Attributes：「whether an entity is heavy, delicate, or dangerous; information known about the entity’s affordances; the current state of an entity (e.g., an entity that is too hot, in a dangerous location, …)」。Command Options：「these VDEs allow a robot to inform users that it is incapable of performing an action … sometimes with an explanation as to why they are not possible.」【全文】 — [Walker ら, THRI 2023](https://arxiv.org/abs/2202.11249)
- 事後状態の予告そのものは Spatial Previews（「show future poses of robots, objects, and other environmental entities」）と Alteration Previews（「give the user a chance to verify if the robot’s plan matches that of the user’s task goal(s) prior to execution and cancel or modify them if needed」）に当たる【全文】。どちらも「動かなかった物」を示す下位分類は持たない — [Walker ら](https://arxiv.org/abs/2202.11249)

**(c) 領域の重畳（主語＝場所）**

- User-defined Spatial Regions：「These regions have many potential uses but are most commonly used to define areas a robot should not enter, in the form of virtual boundaries」【全文】 — [Walker ら](https://arxiv.org/abs/2202.11249)
- Sprute らの virtual borders は「virtual borders that are respected by a robot while performing its tasks」で、非専門家 15 名で評価した【要旨】。学位論文は動機にプライバシーとナビゲーション誤りの回避を挙げる【要旨（検索抜粋）】 — [arXiv 1709.00954](https://arxiv.org/abs/1709.00954)
- RoboVisAR の 6 種の可視化に Safety Zone があり、条件で色を変えられる（既存レポートで【全文】確認済み） — [RoboVisAR](https://kops.uni-konstanz.de/server/api/core/bitstreams/5af29385-e262-4de2-a331-518fc13d06b9/content)
- MARCER と PRogramAR は 3D ゾーンをルールの部品にする。PRogramAR：「users create, move, resize, and delete 3D zones within the real environment to indicate regions relevant to triggers or actions」【全文】 — [PRogramAR](https://doi.org/10.1145/3640008)
- MRPilot の「PRIVATE と記された部屋への進入許可」は、部屋ではなくロボットの空間ラベルで尋ねる（既存レポートで【全文】確認済み） — [MRPilot](https://arxiv.org/abs/2610.07477)

**(d) 経路・軌道の重畳（時間範囲＝途中、主語＝ロボットの通り道）**

- 「Trajectories are the most commonly used VDE」（175 本中）。Spatial Previews、Waypoints、Entity Location がそれに続く【全文】 — [Walker ら](https://arxiv.org/abs/2202.11249)
- Suzuki らのサーベイでは「paths and trajectories」が 154 本【全文】 — [Suzuki ら, CHI 2022](https://doi.org/10.1145/3491102.3517719)
- 経路を全部出すと見づらくなる。Walker ら（2018）：「NavPoints has the potential to display a full flight path of all waypoints, but early pilot tests revealed this led to a distracting case of overdraw. We instead opted to show only a portion of the robot’s path」【全文】 — [Walker ら, HRI 2018](https://doi.org/10.1145/3171221.3171253)
- 同論文の初期案には「dynamic virtual fences that outlined “safe” and “unsafe” areas in the environment」もあった【全文】 — [同上](https://doi.org/10.1145/3171221.3171253)
- Pascher らは 77 本・172 intent を分類し、motion intent が論文の約 69%。位置は on-robot 114、on-human（HMD 等）50、on-world 8。情報は空間に位置合わせしたもの 105、していないもの（記述・記号・信号）67【全文W】 — [Pascher ら, CHI 2023](https://arxiv.org/html/2303.00362v2)
- Safety Chip が扱う制約の例は経路と順序である。「don't go to bedside table before going to bookshelf」「Don't go to kitchen before bathroom」。違反はエラーメッセージとして LLM に返し、危険な行動はマスクする【全文W】 — [Safety Chip](https://ar5iv.labs.arxiv.org/html/2309.09919)

**(e) ステップ列・タイムライン（時間範囲＝順序・期限）**

- VeriPlan のルール翻訳器は 6 つの時間カテゴリに写す。「(1) fixed time blocks, (2) sequential order, (3) concurrent events, (4) conditional constraints, (5) exclusive constraints, and (6) global constraints」。違反は文の一覧で返す【全文】 — [VeriPlan](https://arxiv.org/abs/2502.17898)
- ImageInThat はステップごとの画像列で、変化を強調する。「When an object is moved between consecutive steps, it is visually highlighted while all other objects and fixtures are made less salient.」「hovering over any previous or future step displays the difference through an animation」【全文W】 — [ImageInThat](https://arxiv.org/html/2503.15500)
- MARCER の承認後プレビューは「AR digital twins showing the current, future, and final states of relevant objects, and simulated robot movements」で、終了状態だけでなく途中も動画で見せる【全文】 — [MARCER](https://doi.org/10.1109/HRI61500.2025.10974232)
- RoboVisAR のタイムラインは可視化の有効区間を示すもので、出来事やエラーは載らない（既存レポートで【全文】確認済み） — [RoboVisAR](https://kops.uni-konstanz.de/server/api/core/bitstreams/5af29385-e262-4de2-a331-518fc13d06b9/content)

**(f) 文の一覧（空間に参照先がない、または理由を伝える）**

- MRPilot の結果：「In MRPilot, the same information was conveyed through icons, labels, and lines. These elements could show what happened and where it happened, but not why, and they could also be overlooked.」【全文】 — [MRPilot](https://arxiv.org/abs/2610.07477)
- RoVer は違反を一覧で返し、位置を絞れるものだけ場所を示す。「for the properties that could be pinpointed to a specific area in the interaction—where the violations occurred」【全文】 — [RoVer, UIST 2018](https://par.nsf.gov/servlets/purl/10080246)
- RoboCritics：「outputs a flag, OK, Warning, or Error, with a natural language explanation and hints for addressing the concern.」【全文W】 — [RoboCritics](https://arxiv.org/html/2603.06842v1)

**(g) 利用者への質問（判定が不確か、または権限が要る）**

- KnowNo は候補が複数残ると「asks the human to choose one」。扱う曖昧さは実験で使った種類（属性・数・空間、Winograd、好み、危険）で、網羅的な分類ではない【全文W】 — [KnowNo](https://ar5iv.labs.arxiv.org/html/2307.01928)
- MRPilot の Authorization or Access：「The agent (or a policy layer) stops at an action boundary and the human grants or denies permission for a consequential action … The human decision is binary or scoped; the plan and goal are otherwise unchanged.」【全文】 — [MRPilot 付録 D](https://arxiv.org/abs/2610.07477)

### Inferences

次の表は上の所見からの推論で、対応そのものを検証した研究ではない。

| 表示形式 | 自然に載るルール（次元で書く） | 文献の裏づけ | 載らないもの |
|---|---|---|---|
| 物体を消さずに残す＋ラベル | 時間範囲＝終了時、主語＝物体、違反の形＝動かない（「これは動かさない」「これは○○の物」「これを△△に入れない」） | X-OOHRI の赤＋タグ、Walker の Entity Attributes と Command Options、oversubscription planning（既存レポート） | 物は動くが動かし方が違反するルール。計画側が別の置き場所を選んで回避した場合（何も残らない） |
| 領域の重畳 | 主語＝場所（置いてはいけない面、入ってはいけない部屋）。時間範囲は終了時（置き場所）でも途中（進入）でもよい | Walker の User-defined Spatial Regions、Sprute、RoboVisAR Safety Zone、MARCER / PRogramAR のゾーン | 時刻や人の在不在で有効・無効が変わる領域は、いつの状態かを別に示す必要がある |
| 経路・軌道の重畳 | 時間範囲＝途中、主語＝ロボットの通り道（「寝室を通らない」「人の前を横切らない」） | Walker：最多の VDE、Suzuki：154 本、Safety Chip の制約例 | 速さ・音・力。全経路の表示は過密になる（Walker 2018 の予備試験） |
| ステップ列・タイムラインの印 | 時間範囲＝順序・期限・時刻（「先に手を洗ってから食器」「22 時以降は動かない」） | VeriPlan の 6 カテゴリ、ImageInThat のステップ列、Zhang らの TAP デバッグ（既存レポート） | 空間内の「どこ」 |
| 文の一覧 | 空間に参照先がないルール、理由の説明、厳しさの調整 | MRPilot（可視化は why を示せない）、RoVer、VeriPlan、RoboCritics | 「どの物・どこ」の特定（PRogramAR で 25% が読み解けず、既存レポート） |
| 利用者への質問 | 判定の確からしさが低い（属性推定）、外す権限が本人にない | KnowNo、MRPilot Authorization、Zeng & Roesner の reactive access control（4 節） | 件数が多いと負担。まとめて出す工夫が要る |

- **Before/After の盲点は 2 つある。** 1 つ目は途中の状態に関わるルールで、違反していても事後の光景は整って見える。2 つ目は、計画側がルールを避けて別の置き場所を選んだ場合で、物は消えて別の場所に現れるだけなので、ルールが効いたこと自体が見えない。Reality Promises の rectification と Polaris の「omit that checkpoint」は、まさにこの「黙って変える」側の例である（[Polaris](https://arxiv.org/html/2403.13988v1)【全文W】）。「残す」表示は、計画側が代替案を持たないときにしか発生しない点を、設計の前提として決めておく必要がある。
- 「残っている物」は少なくとも 3 つの原因（ルール違反、物理的に不可能、そもそも計画の対象外）で生じる。残すこと自体は原因を区別しないので、ラベルが原因の区別を担う。
- MARCER が終了状態だけでなく「current, future, and final states」と動きを見せたのは、途中を見せる必要を認めた設計と読める。Before/After を 2 枚の静止状態に限るか、間を動画でつなぐかは、扱うルールの時間範囲で決まる。

### Gaps

- 「事後状態だけを見せると途中の違反を見落とす」ことを直接測った実験は見つからなかった。ImageInThat の本文に、画像では「どうやるか」を表せないという限界の記述はなかった（WebFetch の抽出範囲）。
- 速さ・音・力のようなロボットの動き方のルールを AR でどこに固定するかの定石は見つからなかった。Walker の Internal Readings（車輪速度など）は状態の表示で、違反の表示ではない。
- 主語が「人」のルール（「子どもの近くではゆっくり」）の固定先として、人の周りの領域を使った家庭ロボットの例は今回確認していない（産業の安全領域は Hietanen らが既存レポートにある）。

---

## 2. 「何を」の制約と「どうやって」の制約：利用者はどちらを多く述べるか

### Takeaway

「何を（結果）」と「どうやって（過程）」の区別は、計画言語（PDDL3）、エンドユーザプログラミング（Polaris）、介入の分類（MRPilot）で独立に立てられている。しかし、家庭の片付け・取ってくる作業で利用者がどちらを多く述べるかを直接数えた研究は、今回の検索では見つからなかった。

### Cited Findings

- Polaris は範囲を結果に限ると明言する。「our strict definition of goals as expressing desired state rather than any information about the robot’s actions」「The scope of our work is on the former—what.」【全文W】 — [Polaris, HRI 2024](https://arxiv.org/html/2403.13988v1)
- MRPilot の付録は介入を「何を」と「どうやって」で分ける。Task or Goal Update：「The human changes what the agent is trying to achieve」。Plan Selection or Optimization：「The goal is unchanged; the human shapes the how.」。Contextual or Norm Adjustment：「The human supplies or changes situational context, preferences, constraints, or norms that govern how the agent should act without changing the goal or a specific action」【全文】。つまり MRPilot は規範を「どうやって」の側に置いている — [MRPilot 付録 D](https://arxiv.org/abs/2610.07477)
- TidyBot は結果（どの容器に入れるか）に加えて、動かし方の好みも扱う。「we can also infer generalized rules for how to manipulate objects」。プリミティブは「pick and place and pick and toss」の 2 つ【全文】 — [TidyBot](https://arxiv.org/abs/2305.05658)
- Text2Interaction は言語から「a task plan, motion preferences as Python code, and parameters of a safety controller」を作る。好みを動き方の側で扱う例【要旨】 — [Text2Interaction](https://arxiv.org/abs/2408.06105)
- Safety Chip：「All constraints fall in avoidance and trigger patterns formulated by Menghi et al.」。10 個の安全制約で 2 つの移動操作タスクを実演した【全文W】 — [Safety Chip](https://ar5iv.labs.arxiv.org/html/2309.09919)
- RoVer が検証する社会規範は、すべて過程（順序と同時性）の性質である。Greeting norm、Farewell norm、Speech norm（「The robot should not interrupt the human's …」）、Gaze norm、Noninterruptability norm、および Waiting / Turn-Taking Expectations の表【全文】 — [RoVer](https://par.nsf.gov/servlets/purl/10080246)
- スマートホームの TAP では、Ur らのオンライン調査で望まれた挙動の 78% が単一トリガ・単一アクションで書けた【要旨（Brown 大の報道経由）】 — [Ur ら, CHI 2014](https://doi.org/10.1145/2556288.2557420)
- MARCER は将来課題で「Huang and Cakmak [101], highlight nine trigger-action programming pairs that match a user’s mental model. These pairs, such as While-Do, As-Long-As-Do, and If-When-Then, could extend our set」と書く【全文】。While / As-Long-As は「〜の間は」という過程の条件である — [MARCER](https://doi.org/10.1109/HRI61500.2025.10974232)
- チーム内の文献調査（130 本）の領域別本数は、マナー・社会規範 41、プライバシー 29、安全 27、片付け・置き場所の好み 13、持ち主 7、空間・立入 4。これは論文の本数で、利用者が述べる頻度ではない — `docs/rule_survey/README.md`

### Inferences

- 文献の重心は過程の側にある。マナー（「客がいるときに掃除機をかけない」「人の前を横切らない」）、プライバシー（「入浴中は見ない」）、安全（「水を電子機器の上で運ばない」）の例は、ほとんどが途中の状態か、人や時刻に条件づけられたルールで、終了時の配置だけで判定できるのは「片付け・置き場所の好み」「持ち主」「置いてはいけない場所」に限られる。Before/After に載る範囲は、本数でいえば少数側（13＋7＋4 本の領域）に当たる。
- 一方で、CoGround の作業は navigate / pick / place で、作業の成果は物の配置である。成果に直接かかるルール（どこに置くか、何を動かさないか）が作業と最も強く結びつくのは自然で、TidyBot が置き場所を中心に据えたのと同じ理由になる。
- したがって「利用者は結果のルールを最も気にする」と書くことはできない（根拠がない）。書けるのは「片付け作業では結果のルールが作業の成否を直接決める」までである。

### Gaps

- 住人に家庭ロボットのルールを自由に書かせ、終了時／途中の別で数えた研究は見つからなかった。これは小さな事前調査で埋められる（7 節）。
- Bhattacharjee ら（食事介助での自律度の好み）、Language-to-Rewards、"Is it the what or the how" 型の研究は今回確認していない【未検証】。
- Ur らの 78% は一次資料（論文本文）で確認していない。

---

## 3. 視覚プレビューで確かめられるもの、文章が要るもの

### Takeaway

空間の表示は「何が・どこで」を速く伝えるが「なぜ」は伝えず、見落とされることもある。文章は理由を伝えるが、原因の物や場所を指せないと読み解けない。さらに、現実感の高い AR 表示は AI の提案への過信を増やした実験があり、整った After の光景をそのまま検証手段として信頼することはできない。

### Cited Findings

- MRPilot（20 名、VR、会話型との比較）：可視化は「what happened and where it happened, but not why」。P12 は扉の施錠を「because without that message I would assume that it got to its destination」と述べた。節の見出しは「Visualizing the execution process increases user trust, but reduces the explainability provided through text.」【全文】 — [MRPilot](https://arxiv.org/abs/2610.07477)
- MRPilot の事前調査（12 名）は逆向きの所見を出している。「Text-based status displays did not resolve this」「participants wanted it placed back into the spatial environment: trajectories shown “directly in the scene instead of limiting them to a small panel” (P4), text anchored “directly to the corresponding robot” (P8)」【全文】 — [MRPilot](https://arxiv.org/abs/2610.07477)
- MRPilot の著者の提言：「Future systems should distinguish among observing an action, receiving an explanation for it, and verifying that it satisfies task and safety constraints」「Future work should vary planner accuracy and explanation reliability, then measure error detection, appropriate acceptance or rejection」【全文】 — [MRPilot](https://arxiv.org/abs/2610.07477)
- PRogramAR：ロボット頭上のエラー文を 4 名（25%）が読み解けなかった。P6：「I wanted to know what that error meant about the zone. There was no guidance on the panel」【全文】 — [PRogramAR](https://doi.org/10.1145/3640008)
- X-OOHRI（14 名、探索的）：全員が能力・限界の理解に役立ったと回答。要望に「extend explanation tags beyond text (P4)」があった【全文】 — [X-OOHRI](https://doi.org/10.1145/3757279.3785569)
- AR の埋め込み表示は過信を増やした。「we conducted an empirical study (N = 32) comparing an AR embedded visualization (X-ray) and 2D Minimap」「the embedded visualization led to greater inappropriate reliance on AI, primarily as over-reliance」。理由は「perceptual challenges, visual proximity illusions, and highly realistic visual representations」。提言は「using less embodied, realistic representation for AI suggestions when the risk of over-reliance is high」【全文W】 — [Liu ら, CHI 2026](https://arxiv.org/html/2507.14316v4)
- ImageInThat（10 名）：画像での指示はテキストより速かった（110.8 秒対 363.88 秒）が、誤りは全体として有意差なし【全文W】 — [ImageInThat](https://arxiv.org/html/2503.15500)
- 変化の見落とし：VR と AR の両方で、物の除去・色・大きさの変化の検出を調べた実験があり、「Participants detected changes more quickly and had a higher detection rate with Flickering compared to Head-Turning.」【要旨】。頭を回して見比べる条件のほうが検出が悪い — [Kim, Han, Cho](https://arxiv.org/abs/2308.12476v3)
- RoVer（開発者 9 名、参加者間）：検証の結果を返すと、誤りの解釈がしやすくなった（assisted M = 5.20 対 nonassisted M = 3.81）【全文】 — [RoVer](https://par.nsf.gov/servlets/purl/10080246)
- RoVer の限界：「RoVer analyzes interactions nondeterministically … Consequently, false positives often arise」【全文】。検証器の偽陽性が利用者に見える — [RoVer](https://par.nsf.gov/servlets/purl/10080246)

### Inferences

| 確かめたいこと | 視覚プレビューで足りるか | 根拠 |
|---|---|---|
| どの物がどこへ行くか（配置） | 足りる。ただし見比べ方に依存する | Spatial Previews（Walker）、ImageInThat の速さ、Kim らの見落とし |
| どの物が動かないか | 足りる（残っていること自体が見える）。ただし複数の Before/After を頭を回して見比べると見落としうる | Kim ら |
| なぜ動かないか | 足りない。文章が要る | MRPilot、X-OOHRI のタグ |
| どのルールに当たったか、誰のルールか | 足りない。文章が要る | VeriPlan、RoVer の一覧 |
| 通り道が適切か | 軌道の重畳が要る。事後状態では見えない | Walker、Safety Chip |
| 順序・時刻・速さ・音 | 事後状態では見えない。順序はステップ列、速さ・音は文章 | VeriPlan、PDDL3 |
| ルールが効いて置き場所が変わったこと | 事後状態では区別できない。明示が要る | Polaris の黙った除外、Reality Promises の rectification |

- Before と After を切り替えて見せる方式は、Kim らの Flickering 条件（切り替え）に近く、頭を回して見比べる方式より検出に有利と見込める。ただし Kim らの課題は記憶した光景との比較で、計画検証とは違う。
- Liu らの結果は、きれいな After が「もっともらしい計画」として過信を招くという既存レポートの懸念（He ら）に、AR 固有の実験的な裏づけを足す。残した物のラベルは、整った光景の中に疑うべき箇所を明示する働きを持つので、過信対策として位置づけられる。

### Gaps

- AR の Before/After でルール違反の検出率を測った研究は見つからなかった（既存レポートと同じ結論）。
- 過程のルールを文の一覧で補った場合に、利用者が一覧を読むかどうかの証拠はない。MRPilot は「アイコンや線は見落とされる」と書くが、補助の文章パネルの読まれ方は測っていない。

---

## 4. ルールの次元ごとの解決操作と、誰が外せるか

### Takeaway

解決操作（今回だけ外す、例外を足す、ルールを変える、行き先を変える、属性を直す、他の住人に聞く）は先行研究にそれぞれ先例があるが、「誰のルールを誰が外せるか」を家庭ロボットの計画プレビューで扱った研究は見つからなかった。スマートホームの 1 か月の実地調査は、細かいアクセス制御を用意しても世帯はほとんど使わなかったと報告しており、権限の仕組みを作り込むことは範囲の膨張につながる。

### Cited Findings

- X-OOHRI の解決は 5 つ。システム側が Auto、Alternative、Ignore、利用者側が Virtual、Physical。「the Alternative resolution modifies the instruction by suggesting either a different object of the same class or another target pose」【全文】 — [X-OOHRI](https://doi.org/10.1145/3757279.3785569)
- VeriPlan の厳しさ：「hard constraints must be satisfied for a plan to be valid, and any plan that violates a hard constraint is immediately rejected. Soft constraints, while preferred, are not strictly necessary … the plan with the violated soft constraint will be marked as valid, and the user will be notified of the violation.」利用者は結果を見てからスライダを動かせる【全文】 — [VeriPlan](https://arxiv.org/abs/2502.17898)
- VeriPlan の評価（12 名、機能を外す比較）：スライダを外した条件より全機能のほうが有用と評価された（p = .047）【全文】 — [VeriPlan](https://arxiv.org/abs/2502.17898)
- RoboCritics の重大度は OK / Warning / Error の 3 段階【全文W】 — [RoboCritics](https://arxiv.org/html/2603.06842v1)
- RoboGuard は衝突を自動で解く。「using temporal logic control synthesis, ensuring compliance while minimally violating user preferences」【要旨】 — [RoboGuard](https://arxiv.org/abs/2503.07885)
- Zeng & Roesner の設計原則は 4 つ。「access control flexibility, user agency, respect among users, and transparency of smart home behaviors」【全文】 — [Zeng & Roesner, USENIX Security 2019](https://www.usenix.org/conference/usenixsecurity19/presentation/zeng)
- 同、reactive access control：「If a user attempts to access a capability they do not have permission to use, the app will ask a more privileged user for permission in real-time, by sending a notification to asking them to approve or deny the request」【全文】 — [同上](https://www.usenix.org/conference/usenixsecurity19/presentation/zeng)
- 同、7 世帯・1 か月の結果：「in general, we found that the access controls we implemented did not fit with the participants needs and use cases.」「most of them quickly settled on the least restrictive access control setting」。使い続けたのは同居人世帯 1 つ（各自の寝室の照明）だけで、「none of the roommates ever attempted to violate these access controls」【全文】 — [同上](https://www.usenix.org/conference/usenixsecurity19/presentation/zeng)
- 同：「positive household social norms and relationship dynamics obviated the need for technical access controls」「when we increased complexity, it decreased usability」【全文】 — [同上](https://www.usenix.org/conference/usenixsecurity19/presentation/zeng)
- Geeng & Roesner（CHI 2019）は複数人世帯の緊張を混合手法（n = 18）で調べたとされる【未検証（二次資料の記述のみ）】 — [DOI](https://doi.org/10.1145/3290605.3300498)

### Inferences

| ルールの次元 | 合う解決操作 | 先例 |
|---|---|---|
| 厳しさ＝できれば守る | 今回だけ外す | X-OOHRI の Ignore、VeriPlan のスライダ |
| 厳しさ＝必ず守る | 行き先・対象を変える。外す操作は出さないか、確認を重くする | X-OOHRI の Alternative、VeriPlan の hard |
| 主語＝物体、判定が属性推定に依存 | 属性を直す（「これは父の物ではない」） | X-OOHRI の VLM 誤り、既存レポートの iTeach |
| 主語＝場所 | 領域を動かす・例外の物を足す | PRogramAR のゾーン編集、Sprute |
| 登録者が別の住人 | その住人に聞く（その場で通知して許可・拒否） | Zeng & Roesner の reactive access control、MRPilot の Authorization |
| 時間範囲＝途中（経路・順序） | 経路や順序を選び直す | MRPilot の Plan Selection、Fang らのドラッグ（既存レポート） |

- Zeng & Roesner の結果からは、権限の細かな設定画面より、「誰のルールかをラベルに書く」（transparency）と「必要なときだけ聞く」（reactive）の 2 つで足りる可能性が高い。ただしスマートホームの機器操作での結果で、物の所有に関わるロボットのルールにそのまま当てはまる保証はない。
- 権限は、評価が難しい（1 人の参加者では他の住人の反応を再現できない）ので、最初の論文では「ラベルに登録者を表示する」までに止め、外す権限の仕組みは将来課題とするのが安全である。

### Gaps

- 家庭ロボットで、他人が登録したルールを外すときの受容を調べた研究は今回確認していない。チームの文献調査にある Multi-user Norm Consensus、Multi-User Personalisation は本文未確認。
- Geeng & Roesner の本文は取得できなかった。

---

## 5. 類似研究は、扱うエラー・制約・ルールの範囲をどう決め、どう説明したか

### Takeaway

20 件を見ると、範囲の決め方は 5 通り（ロボットの能力モデルから、先行研究の分類から、利用者の事前調査から、既存データ・ベンチマークから、専門家の知識から）に分かれ、範囲を決めた理由を 1 文で明示している論文は少数である。明示している論文は「ロボットの能力が限られるので」「対象は what に限る」のように、除外した側を短く言い切っている。

### Cited Findings

| # | 研究 | 扱う範囲 | 範囲の決め方 | 説明の文（原文） | 確認度 |
|---|---|---|---|---|---|
| 1 | [MARCER](https://doi.org/10.1109/HRI61500.2025.10974232) (HRI 2025) | トリガ 4 つ（場所、時間、時間つき場所、即時） | 設計者が選択。54 件の注釈例で LLM に教える | 「Currently, MARCER supports four types of triggers」。選んだ理由の文は確認した範囲になし。将来課題で Huang & Cakmak の 9 対に拡張可能と書く | 【全文】 |
| 2 | [PRogramAR](https://doi.org/10.1145/3640008) (THRI 2024) | If-Then と While-Do。トリガは「ゾーンに物がある／ない」、行動は移動のみ | ロボットの能力と先行系（Senft ら）から | 「Due to the limited capabilities of our robot, the only supported action is moving an object from a zone or its current location, to another zone」 | 【全文】 |
| 3 | [X-OOHRI](https://doi.org/10.1145/3757279.3785569) (HRI 2026) | 到達・把持・可搬の 3 判定（決定木） | ロボットと物体の能力モデルから。タグの文面は「よくあるエラー」から始めて拡張 | 「in manipulative tasks, the decision tree evaluates reachability, graspability, and manipulability」「content initialized from common errors and extended as new failure types arise」。好みを扱わない理由の文はなし | 【全文】 |
| 4 | [MRPilot](https://arxiv.org/abs/2610.07477) (2026) | 介入 8 種（情報の確認、計画の選択、許可、目標の更新、失敗前の修正、失敗回復、能力不足の補助、文脈・規範の調整） | 事前調査（12 名）で課題を出し、介入の種類は先行研究から合成 | 「we identified eight intervention types from prior work on human–multi-robot interaction and LLM-based robot planning」。場面は事前に固定：「This design standardized event exposure but did not measure whether participants would detect and initiate these interventions spontaneously」 | 【全文】 |
| 5 | [RoboCritics](https://arxiv.org/html/2603.06842v1) (2026) | 批評器 5 つ（空間使用、衝突、関節速度、手先姿勢、挟み込み） | 専門家の知識を符号化した先行枠組み（Schoen ら 2022）から | 「external, motion-level critics adapted from expert-encoded frames」。限界：「we did not conduct cross-validation of the expert-informed critics with robotic experts.」 | 【全文W】 |
| 6 | [VeriPlan](https://arxiv.org/abs/2502.17898) (CHI 2025) | 時間制約の 6 カテゴリ（LTL の雛形） | 検証器（モデル検査）が受け取れる形から。3 つのシナリオで確認 | 「We present a template-based approach to categorizing temporal constraints for verifying LLM outputs, instantiated and validated within a finite set of scenarios.」 | 【全文】 |
| 7 | [Polaris](https://arxiv.org/html/2403.13988v1) (HRI 2024) | 望む状態（ゴール述語）のみ。行動は書かせない | 先行研究と介護者の場面から。事前調査の記述なし | 「The scope of our work is on the former—what.」矛盾するゴールは「Polaris will omit that checkpoint」 | 【全文W】 |
| 8 | [RoVer](https://par.nsf.gov/servlets/purl/10080246) (UIST 2018) | 挨拶、別れ、発話、視線、割り込みなどの社会規範と課題の性質（LTL） | 社会ロボットの文献から。表現力は LTL で決まる | 「Limitations of the modeling framework also limit the social-norm properties that can be expressed in LTL, specifically the expression of probabilistic properties and properties that reason about the ordering of events among concurrently executing microinteractions.」 | 【全文】 |
| 9 | [Safety Chip](https://ar5iv.labs.arxiv.org/html/2309.09919) (ICRA 2024) | 回避と発火の型の LTL 制約（主に移動の順序と立入） | 既存の仕様パターン（Menghi ら）から | 「All constraints fall in avoidance and trigger patterns formulated by Menghi et al.」「LTL lacks expressivity as compared to natural language.」 | 【全文W】 |
| 10 | [RoboGuard](https://arxiv.org/abs/2503.07885) (RA-L 2026) | 事前に与えた安全ルールを環境に当てはめた時相論理の仕様 | 事前定義のルールを LLM で文脈化 | 「contextualizes pre-defined safety rules by grounding them in the robot's environment」 | 【要旨】 |
| 11 | [TidyBot](https://arxiv.org/abs/2305.05658) (AuRo 2023) | 物の種類→容器、物の種類→動かし方（置く／投げる） | 作業（片付け）の中心課題から。自作ベンチマークで測る | 「A key challenge is determining the proper place to put each object」「we use pick and place and pick and toss as our primitives, as they are well-suited for household cleanup. However, other sets of primitives could also be used.」 | 【全文】 |
| 12 | [ASIMOV](https://arxiv.org/abs/2503.08663) (2025) | 意味的な安全（衝突回避より上の層） | 実データ（病院の傷害報告、実写の場面）から自動生成 | 「generate undesirable situations from real-world visual scenes and human injury reports from hospitals」 | 【要旨】 |
| 13 | [ImageInThat](https://arxiv.org/html/2503.15500) (HRI 2025) | 台所の 4 課題、単一物体の操作 | 現在のロボットの能力から | 「reflecting the current capabilities of robots, which is typically limited to single-object manipulation.」 | 【全文W】 |
| 14 | [GhostObjects](https://arxiv.org/abs/2508.11022) (2025) | 物理的なゴールと空間パラメータの指定 | 操作の型（仮想ツインの直接操作）から | 「users can precisely specify physical goals and spatial parameters」 | 【要旨】 |
| 15 | [Reality Promises](https://doi.org/10.1145/3746059.3747660) (UIST 2025) | 1 物体の移動。実現できない置き場所は黙って補正 | 錯覚の成立条件から | 既存レポートで確認済み（rectification） | 【全文】 |
| 16 | [Sprute ら](https://arxiv.org/abs/1709.00954) (2017–2019) | 立入禁止の領域のみ | 利用者の必要（ロボットの制御を保つ）から | 「virtual borders that are respected by a robot while performing its tasks」 | 【要旨】 |
| 17 | [KnowNo](https://ar5iv.labs.arxiv.org/html/2307.01928) (CoRL 2023) | 指示の曖昧さ（属性・数・空間、Winograd、好み、危険） | 実験設定として選択。網羅性は主張しない | 「We introduce three settings based on different types of ambiguities in the user instruction」 | 【全文W】 |
| 18 | [RoboVisAR](https://kops.uni-konstanz.de/server/api/core/bitstreams/5af29385-e262-4de2-a331-518fc13d06b9/content) (2024) | 可視化 6 種、条件 4 種 | 既存レポートで確認済み。専門家 3 名で評価 | — | 【全文】 |
| 19 | [ORCESTRA](https://arxiv.org/abs/2608.00775) (2026) | 配置・機体適合・認識の確信度・座標・到達と IK・接触の論理積 | ロボットの実行条件から | 既存レポートで確認済み。不合格の理由は利用者に見せない | 【全文】 |
| 20 | [Zeng & Roesner](https://www.usenix.org/conference/usenixsecurity19/presentation/zeng) (USENIX Sec 2019) | 役割・位置・監督・その場の許可の 4 種のアクセス制御 | 先行研究から設計原則を整理し、実地で検証 | 「We systematize from prior work a set of possible design principles … and we develop a prototype based on these principles」→ 実地では「did not fit with the participants needs and use cases」 | 【全文】 |

範囲の決め方ごとの整理（上の表から）

| 決め方 | 例 | 強み | 弱み（著者自身が認めたもの） |
|---|---|---|---|
| ロボットの能力モデルから | X-OOHRI、PRogramAR、ORCESTRA、ImageInThat | 判定が確実で、説明が短い | 好み・規範が落ちる |
| 検証器が受け取れる形から | VeriPlan、RoVer、Safety Chip | 正しさを保証できる | 「LTL lacks expressivity」。偽陽性（RoVer） |
| 先行研究の分類から | MRPilot（介入 8 種）、Zeng & Roesner | 網羅の根拠を示せる | 利用者の必要と合わないことがある（Zeng & Roesner） |
| 利用者の事前調査から | MRPilot（F1〜F4 → 4 段階の表示） | 設計の理由を参加者の言葉で示せる | 調査の対象が設計者の想定に縛られる |
| 実データ・ベンチマークから | ASIMOV、TidyBot | 規模と再現性 | 住人が自分で登録するルールとは出所が違う |
| 専門家の知識から | RoboCritics | 実務の妥当性 | 「did not conduct cross-validation」 |

### Inferences

- 範囲を言い切っている論文（Polaris「what」、PRogramAR「limited capabilities」、ImageInThat「current capabilities」）は、除外の理由を外部の事実（能力、言語の定義）に置いている。CoGround も「事後状態で判定できるルール」という判定基準を外部の枠組み（PDDL3 の at end と trajectory の区別）に結びつければ、同じ型で書ける。
- X-OOHRI は好みや規範を扱わない理由を書いていない。CoGround が「X-OOHRI の型を規範へ広げる」と主張するなら、X-OOHRI が書かなかった境界（どの規範まで、なぜ）を自分で書く必要がある。そこが査読で問われる。
- MRPilot は場面を事前に固定し、その限界を明記した。ルール照合を実装せず場面を作り込む評価は先例として成立するが、「システムが照合した結果を見せる」ことを貢献にするなら、照合が実際に動いていることを示す技術的な確認（少数のルールでよい）が別に要る。

### Gaps

- MARCER がトリガ 4 つを選んだ理由は、grep した範囲では見つからなかった（全文を通読してはいない）。
- RoVer の規範がどの文献から何本選ばれたかの数は確認していない。
- RoboGuard、ASIMOV、GhostObjects、Sprute は要旨までで、範囲を説明する文は本文未確認。

---

## 6. CHI / HRI / UIST 投稿で、最小の範囲と主張の地図

### Takeaway

評価は論文の主張から決まり、対照実験は系のごく一部しか測れないので、主張が広いほど評価との隙間が開く。最も小さく強い組合せは「事後状態で判定できるルールの違反を、消さずに残して示す」に絞り、途中の状態のルールは範囲外と明記したうえで 1 つだけ境界の確認として入れる形である（以下の地図は調査者の推論）。

### Cited Findings

- 評価は主張から決める。「our stance is that the evaluation of a toolkit must stem from the claims of the paper. Evaluation is a means to follow through with the proposed claims of the innovation.」【全文（OCR の空白を補正）】 — [Ledo ら, CHI 2018](https://doi.org/10.1145/3173574.3173610)
- 対照実験の限界：「Controlled experiments measuring usability are limited in scope and evaluate a very small subset of what the toolkit can accomplish, making it difficult to generalize usage results. Furthermore, selected experimental tasks might favour elements that the toolkit can accomplish.」【全文】 — [同上](https://doi.org/10.1145/3173574.3173610)
- 課題と指標：「rigour is only of value if truly representative tasks and appropriate measures are used.」「Publications should clearly articulate why the chosen tasks and measures support the claims made in the paper」【全文（OCR 補正）】 — [同上](https://doi.org/10.1145/3173574.3173610)
- 想定利用者の伸び縮み：「Speculating on the intended audience creates the risk of an elastic user [18], where the definition of the target audience is stretched to accommodate implementation decisions and toolkit design.」【全文】 — [同上](https://doi.org/10.1145/3173574.3173610)
- threshold と ceiling：「The threshold is the user’s ability to get started using the toolkit, while ceiling refers to how much can be achieved using the toolkit」【全文】 — [同上](https://doi.org/10.1145/3173574.3173610)
- Ledo らは、1 つの作業をする系とツールキットを分ける。「Toolkits are typically different from systems that perform one task (e.g. a system, algorithm, or an interaction technique) as they provide generative, open-ended authoring within a solution space.」【全文（OCR 補正）】 — [同上](https://doi.org/10.1145/3173574.3173610)
- Olsen（Ledo ら経由）：「simple metrics can produce simplistic progress that is not necessarily meaningful.」。usability trap の 3 前提は「walk up and use, standardized tasks, and problem scalability」で、系の研究では満たされにくい。fatal flaw fallacy（小さなチームは製品品質にできない）【全文（Ledo ら本文の引用・要約）】 — [Olsen, UIST 2007](https://doi.org/10.1145/1294211.1294256)
- Wobbrock & Kientz（Ledo ら経由）：artifact contribution は「new knowledge is embedded in and manifested by artifacts and the supporting materials that describe them」【全文（Ledo ら本文の引用）】 — [Wobbrock & Kientz, 2016](https://doi.org/10.1145/2907069)
- Greenberg & Buxton：ごく初期の設計段階を従来の使いやすさ評価で検証すべきでなく、他の内省的・批評的な方法を考えるべきだ、という主張【要旨（リポジトリの要約）】 — [Greenberg & Buxton, CHI 2008](https://doi.org/10.1145/1357054.1357074)
- 比較対象がない場合の先例：X-OOHRI「As no comparable systems exist for visually communicating robot limitations via object-oriented interactions, we opted for an exploratory study rather than a controlled experiment.」「all interactions occurred before execution; no physical robots were used」【全文】 — [X-OOHRI](https://doi.org/10.1145/3757279.3785569)
- 仮想ロボットでの評価の妥当性：物理ロボット（MR）とデジタルツイン（VR）の比較で「no significant differences between the PhyR and VirR setting for any of the assessed user perceptions or behavioral intentions」。ただし複数時点で測った変数（信頼など）は「only roughly 58% of analyses meeting our criterion」と混在【全文】 — Mara ら 2026（Zotero: YME6LC6D、URL 未取得）
- MRPilot は VR で再現した家で評価し、物理環境への移行を限界に挙げた【全文】 — [MRPilot](https://arxiv.org/abs/2610.07477)

### Inferences

CoGround は Ledo らの言う「1 つの作業をする系・インタラクション技法」に当たり、ツールキットのような一般性の主張は要らない。主張は表示技法とその効果に置ける。候補 4 つの地図は次のとおり。

| 候補 | 範囲（次元で書く） | 論文の主張 | できる評価（シミュレーション・仮想ロボット前提） | 査読で突かれる点 |
|---|---|---|---|---|
| **A. 事後状態・物体** | 時間範囲＝終了時、主語＝物体（動かさない物、持ち主、物ごとの置き場所） | 計画の違反を「消さずに残す」ことで、事後状態の中に位置づけて示せる | 違反を埋め込んだ計画で、残す＋ラベル／ゴースト重畳のみ／文の一覧（タブレット）を比べ、検出（d′）と受容率を分けて測る。条件が少なく検出力を確保しやすい | 「片付けの好みは TidyBot、物体への表示は X-OOHRI の色替え」。ルール照合が自明。規範研究の重心（マナー・安全）を外している |
| **B. 事後状態・物体＋場所** | A に、主語＝場所の終了時ルール（置いてはいけない面・部屋）を足す | 終了時に判定できるルールは、物体か場所のどちらかに固定して事後状態の中で示せる | A に固定先（物体／領域）の要因を足す。領域の表示は Sprute らの先例と比べられる | 物体と領域の両方に印が付くときの見やすさ。A との差が小さいと「足しただけ」に見える |
| **C. 途中の状態まで全部** | B に、経路・順序・時刻・速さ・音・人の条件を足す | 家庭ルール全般を実行前に検証できる | 表示形式が 4〜5 種に増え、条件の組合せが膨らむ。速さ・音は仮想ロボットでは体感を再現できない | Before/After が主役でなくなり「VeriPlan の一覧を AR に置いただけ」。照合の正しさ（LLM→形式化）の評価を求められる。主張と評価の隙間が最大 |
| **D. B ＋ 境界の確認** | B を範囲とし、途中の状態のルールは範囲外と明記。ただし評価に 1 種類（例：通ってはいけない部屋を通る経路）だけ入れ、事後状態では検出できないことと、軌道重畳を足すと検出できることを示す | 事後状態プレビューが有効な範囲と、その限界を実験で示す | B の比較に「途中の違反」の試行を少数混ぜる。検出率がルールの時間範囲で分かれることを示せば、否定的な結果も貢献になる | 条件が増えて検出力が落ちる。「限界を示しただけで解決していない」。軌道重畳は既存技術 |

- **最小で強いのは B、主張を厚くするなら D。** B は、範囲の線を「物体か場所か」ではなく「終了時に判定できるか」に引くので、PDDL3 の区別に結びつけて 1 文で説明できる。D は、MRPilot の著者が今後の課題に挙げた「エラー検出と適切な受容・拒否の測定」に、ルールの時間範囲という要因を足して答える形になる。
- **範囲の膨張で貢献がぼやける箇所は 3 つ。** (1) 途中の状態のルールを主張に入れると、表示の主役が Before/After から軌道・一覧に移る。(2) 権限（誰が外せるか）を入れると、1 人の参加者では評価できない。(3) ルールの登録（自然言語→形式化）の正しさを主張に入れると、VeriPlan の rule translator や nl2spec と同じ土俵での評価が要る。3 つとも「できるが主張しない」と書くのが安全である。
- A だけでは、チームの文献調査が示す規範の重心（マナー 41、プライバシー 29、安全 27）との距離を説明しにくい。B または D にして、「安全・プライバシーのうち終了時に判定できる部分（薬を子どもの手の届く棚に置かない、私物を共有スペースに出さない）は範囲内」と例で示すと、領域の名前ではなく次元で範囲を説明できる。
- 仮想ロボットでの評価は X-OOHRI と MRPilot に先例があり、Mara らは知覚の指標で物理ロボットとの有意差なしを報告する。ただし信頼の時間変化は一致率が約 58% で、信頼を主要指標にするのは避け、検出と受容率を主要指標にするのが妥当である。

### Gaps

- Olsen 2007 の本文（importance、generality、expressive leverage の定義）は取得できず、Ledo ら経由の記述だけである。Greenberg & Buxton、Wobbrock & Kientz も本文未確認。
- HRI・CHI の査読で「範囲が狭い」ことが不採択理由になった実例の資料は探していない。上の「突かれる点」は調査者の推測である。
- Mara ら 2026 の URL・掲載先は未確認（Zotero にのみ存在）。

---

## 7. ルールの範囲を先に決めるか、インタラクションを先に決めるか

### Takeaway

どちらを先にしても固有の危険がある。表示側から決めると「見せられるものだけを評価する」循環に陥り、ルール側から決めると表示できないルールが大量に残って一覧表示に退化する。先行研究で設計の理由を最もよく説明できているのは、利用者の事前調査で課題を出し、範囲の候補は先行研究から取り、評価で限界を明記した MRPilot の進め方である。決めるべきは、ルールの一覧ではなく「範囲に入るかどうかの判定基準」である。

### Cited Findings

**表示側・能力側から決めた例**

- PRogramAR は能力から範囲が決まり、将来課題に表現力を挙げた。「increased TAP rule expressibility by including more object states such as dirty or clean dishes, social behaviors [48], and trigger-action rules (e.g., As-long-as-Do, If-When-Then [39])」【全文】 — [PRogramAR](https://doi.org/10.1145/3640008)
- X-OOHRI は能力モデルから範囲が決まり、評価は探索的。将来課題は「more complex task sequences and highly abstract instructions」【全文】 — [X-OOHRI](https://doi.org/10.1145/3757279.3785569)
- Ledo ら：実験課題が系のできることに有利に選ばれる危険（6 節の引用）【全文】 — [Ledo ら](https://doi.org/10.1145/3173574.3173610)

**ルール側・先行研究側から決めた例**

- Zeng & Roesner は先行研究から原則と機能を決め、実地で外れた。「we expected that households would use our access controls … However, in general, we found that the access controls we implemented did not fit with the participants needs and use cases.」【全文】 — [Zeng & Roesner](https://www.usenix.org/conference/usenixsecurity19/presentation/zeng)
- VeriPlan は検証器の形から 6 カテゴリを決め、「instantiated and validated within a finite set of scenarios」と範囲を限定して書いた【全文】 — [VeriPlan](https://arxiv.org/abs/2502.17898)
- RoboCritics は専門家の知識から決め、妥当性の確認がないことを限界に書いた【全文W】 — [RoboCritics](https://arxiv.org/html/2603.06842v1)

**事前調査を挟んだ例**

- MRPilot：「To inform our system design, we conducted a formative study guided by the following research question: What challenges do users encounter when directing an LLM-based heterogeneous MRS through natural-language instructions in spatial tasks?」。12 名、VR のシミュレーション。所見 F1〜F4 から 4 段階の表示を導いた。F2：「Direct commitment to an unpreviewed plan makes robot coordination difficult to assess.」F4：「High-level prompting is a poor fit for localized intervention.」【全文】 — [MRPilot](https://arxiv.org/abs/2610.07477)
- MRPilot は介入の種類を事前調査からではなく先行研究から取った（5 節の表）【全文】 — [MRPilot](https://arxiv.org/abs/2610.07477)
- Ur らは、望む挙動をオンライン調査で集めてから、トリガ・アクション形式で書けるかを調べ、次に 226 名で使いやすさを試した【要旨】 — [Ur ら, CHI 2014](https://doi.org/10.1145/2556288.2557420)
- Ledo ら：「Discussing the understanding of the challenges, perhaps informed by earlier studies or experiences with other tools or toolkits, can help address why different decisions were made.」【全文】 — [Ledo ら](https://doi.org/10.1145/3173574.3173610)

### Inferences

| | 表示側から範囲を決める | ルール側から範囲を決める |
|---|---|---|
| 得るもの | 表示と範囲が一致し、主張が鋭い。実装が小さい | 規範研究との接続が説明できる。「何を外したか」を示せる |
| 危険 1 | 評価が循環する（見せられるルールだけで評価し、有効と結論する） | 表示できないルールが多数残り、一覧表示（VeriPlan 型）に退化して新規性が消える |
| 危険 2 | 住人が実際に登録するルールの多くが範囲外で、想定利用者が実装に合わせて伸び縮みする（Ledo らの elastic user） | 文献から決めた範囲が住人の必要と合わない（Zeng & Roesner） |
| 危険 3 | 「残す」表示が発生しない場面（計画側が代替の置き場所を選ぶ）を見落とす | 照合の実装（自然言語→形式）の負担が膨らみ、表示の研究に時間が回らない |
| 危険 4 | 途中の状態の違反がきれいな After に隠れ、過信を招く（Liu ら） | 権限・厳しさ・時刻など次元の組合せが増え、評価条件を絞れない |

- **「範囲を先に固定する」という方針は半分正しい。** 固定すべきなのは個々のルールの一覧ではなく、範囲に入るかどうかの判定基準（例：終了時の状態だけで判定できる。違反が物体か場所に帰着する）である。基準が決まれば、表示形式は 1 節の対応表から選べ、個々のルールは後から足せる（X-OOHRI の「extended as new failure types arise」と同じ扱い）。
- **全体の設計について、文献から言える修正点は 3 つある。**
  1. 「違反した物を残す」は、計画側が代替案を出さない場合の表示である。代替の置き場所に動かした場合（ルールが効いて結果が変わった）の表示を別に決めないと、黙って変える系（Polaris、Reality Promises）と同じ弱点を持つ。
  2. 範囲外のルール（途中の状態）に違反する計画でも After は整って見える。範囲外であることを画面で示す（「経路と順序は確認していません」に当たる表示、または軌道の簡易表示）か、評価で限界として測る（候補 D）かを決める必要がある。
  3. 残す理由が複数ある（ルール違反、物理的に不可能、認識の誤り）ので、ラベルは原因の区別と、判定が属性推定に依存する場合の「属性を直す」出口を持つ必要がある。
- **進め方の提案（推論）。** (1) 判定基準を先に決める（1 日で決められる軽い決定）。(2) 小さな事前調査で、住人に自分の家のルールを自由に書いてもらい、判定基準に入る割合を数える（2 節の空白を埋め、範囲の説明にも使える。シミュレーションの部屋の画像で実施できる）。(3) 表示を設計する。(4) 評価で、範囲内の違反と範囲外の違反を混ぜて検出を測る。(2) を挟むと、MRPilot と同じく「事前調査→設計→限界の明記」の形になり、ルール側・表示側のどちらの循環も避けられる。

### Gaps

- ルールを先に集めた設計と、技術を先に作った設計を直接比べた研究は見つからなかった。上の比較は個別の事例からの推論である。
- Porfirio らの事前調査型の研究（エンドユーザプログラミングの設計要件）は今回確認していない【未検証】。
- 事前調査で「終了時に判定できるルール」の割合が低かった場合の扱い（範囲を広げるか、作業を片付けに限定して説明するか）は、結果を見てから決める必要がある。

---

## Zotero に追加が必要な文献（自動取得できなかったもの）

| 文献 | 用途 | 現状 |
|---|---|---|
| Olsen, "Evaluating User Interface Systems Research," UIST 2007（[DOI](https://doi.org/10.1145/1294211.1294256)） | 系の研究の評価基準（generality、expressive leverage） | 本文取得不可。Ledo ら経由のみ |
| Greenberg & Buxton, "Usability Evaluation Considered Harmful (Some of the Time)," CHI 2008（[DOI](https://doi.org/10.1145/1357054.1357074)） | 初期段階の評価の扱い | 要約のみ |
| Wobbrock & Kientz, "Research Contributions in Human-Computer Interaction," Interactions 2016（[DOI](https://doi.org/10.1145/2907069)） | 貢献の種類 | Ledo ら経由のみ |
| Geeng & Roesner, "Who's In Control?," CHI 2019（[DOI](https://doi.org/10.1145/3290605.3300498)） | 複数人世帯での制御の緊張 | 二次資料のみ |
| Ur ら, "Practical Trigger-Action Programming in the Smart Home," CHI 2014（[DOI](https://doi.org/10.1145/2556288.2557420)） | 望む挙動を先に集めた設計の例、78% の数字 | 報道経由のみ |
| Huang & Cakmak, "Supporting Mental Model Accuracy in Trigger-Action Programming," UbiComp 2015（[DOI](https://doi.org/10.1145/2750858.2805830)） | TAP の 9 対（While / As-Long-As） | MARCER 経由のみ |
| Gleicher ら, "Visual comparison for information visualization," 2011（[DOI](https://doi.org/10.1177/1473871611416549)） | Before/After の比較技法の分類 | 未検証（既存レポートと同じ） |
| Willett ら, "Embedded Data Representations," TVCG 2017（[DOI](https://doi.org/10.1109/TVCG.2016.2598608)）、White & Feiner, "SiteLens," CHI 2009（[DOI](https://doi.org/10.1145/1518701.1518871)） | 物体に固定する表示の理論 | 未検証。今回は読んでいない |
| Sprute ら, "A Study on Different User Interfaces for Teaching Virtual Borders to Mobile Robots," IJSR 2019（[DOI](https://doi.org/10.1007/s12369-018-0506-3)） | 領域ルールの UI 比較 | 検索抜粋のみ |
| RoboGuard、ASIMOV、GhostObjects、Text2Interaction の本文 | 範囲を説明する文の確認 | 要旨のみ |
| Rensink ら 1997 などの change blindness の古典 | 見落としの理論的根拠 | 今回は未確認。AR / VR の実験（Kim ら）は要旨で確認 |
