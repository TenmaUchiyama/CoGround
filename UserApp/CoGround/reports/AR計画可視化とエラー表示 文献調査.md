# AR 計画可視化は「違反を物に残す」表示を欠く

言語指示から作った計画を AR で実行前に見せる研究は 2024 年以降に十数件まで増えたが、**計画上のエラーを「どのステップ」と「どの物体」の両方に事前に結びつけて見せるものは、今回の調査範囲では見つからなかった**。最も近いのは X-OOHRI（HRI 2026）で、実行できない操作を赤色と説明タグで物体に付け、解決策をメニューで選ばせるが、判定するのは到達・把持・可搬といった物理的な実行可能性だけで、家庭ルールや規範は扱わない。Before/After については重要な修正がある。調査の途中では語の検索だけで「Reality Promises の DR はロボットを消す用途のみ」と判断していたが、手元の全文では **Reality Promises の removal decoupling mode は実物体も元位置から視覚的に消し、仮想コピーを目標位置へ動かす**と書かれている。つまり「実物を消して仮想コピーをゴールに置き、ロボットが後から運ぶ」という表示技術そのものは既にあり、新規性は技術ではなく用途に置く必要がある。空いているのは、(a) 言語指示からプランナが決めた事後状態を、(b) 実行前の検証と承認のために、(c) 計画全体について一度に見せ、(d) 違反で動かせない物体だけを現場に残して理由と解決策を付ける、という組合せである。RoboVisAR のタイムラインは「記録した実行の上で、可視化が有効な区間を示す」もので、エラー表示の仕組みは持たない（本文で確認済み）。評価面では、同じ情報ならタブレットが AR より好まれた故障診断の研究があり、AR の優位は前提にできない。

本レポートの確認度の書き方は次のとおりである。**【全文】**は手元の全文（Zotero キャッシュ）と今回突き合わせた記述、**【本文】**は調査ノートが論文本文を読んで確認した記述、**【要旨】**は要旨・著者ページ・検索抜粋までの確認、**【未検証】**は題名のみ、または調査者の記憶による記述で、引用前に原典確認が要る。「見つからなかった」と書いた箇所はすべて、Web 検索・Crossref・arXiv API・Semantic Scholar の範囲での結果であり、ACM DL と IEEE Xplore の直接検索、Google Scholar の網羅検索はしていない。OpenAlex は無料枠切れで使えなかった。存在しないことの証明ではない。

## 言語から AR プレビューまで通す系は 2024 年以降の十数件に限られる

「言語（LLM）→ 計画 → AR で実行前に提示 → 編集・承認」を一通り備える系のうち、**ルール（条件＋行動）を言語で作って AR で見せるのは MARCER だけ**で、他はウェイポイント、軌道、仮想ロボット、マルチロボット計画と、見せる対象の抽象度が違う。MARCER は LLM（GPT-4o）がユーザーの発話と環境の文脈から Trigger-Action 型の Python 関数を生成し、平易な文章の説明を返し、関係する物体と面をオレンジのワイヤーフレームで強調する。承認後は、デジタルツインで物体の「現在・将来・最終の状態」とロボットの動きをプレビューする【全文】（[MARCER](https://doi.org/10.1109/HRI61500.2025.10974232)）。15 名の評価で SUS は 70.83、全試行のうち LLM の無効な計画から回復できなかったのは 2 件（4.44%）だった。ただし著者自身が **「システムの失敗を効果的に伝えられなかった。将来のシステムは能力だけでなく、特定の行動がなぜ失敗するかも伝えるべきだ」**と書いている【全文】。実際、ロボットの能力を超える指示を出した 2 名と、届かない位置に物を置いた 2 名は、計画が立たない理由が分からないまま時間切れになった【全文】。MARCER の最終状態プレビューは仮想物体を足す表示で、実物を消す記述は全文に確認できなかった。

MARCER に近い順に並べると、Fang らの LLM＋MR ウェイポイント生成（LLM が作った経由点と軌道を AR に重ね、ドラッグで直し、承認した計画だけ実行）【要旨】（[arXiv 2403.09308](https://arxiv.org/abs/2403.09308)）、AURaPath（HoloLens 2 と UR10、「run」「confirm」を 2 段階の確認ゲートで扱う）【要旨】（[MDPI](https://www.mdpi.com/2076-3417/16/20/9974)）、ORCESTRA（VLM が指示を構造化計画に変え、検証を通った計画だけを編集可能なプレビューとして MR に出し、利用者が確認してから実行する。**検証に落ちた計画はプレビューされず、落ちた理由を利用者に見せる記述はない**）【全文】（[arXiv 2608.00775](https://arxiv.org/abs/2608.00775)）、MRPilot（LLM のマルチロボット計画を状況内ビューと俯瞰ビューで同期表示し、選択・修正・介入。詳細は後述）【全文】（[arXiv 2610.07477](https://arxiv.org/abs/2610.07477)）、AR Puppeteer 系（仮想ロボットが先に動き、確認してから実機が動く）【要旨】（[arXiv 2502.09142](https://arxiv.org/abs/2502.09142)）が続く。Puppeteer の続報は 42 名の比較で、音声を足すと柔軟になるが遅延と認識誤りで負荷が増えうると報告しており、言語入力の誤解釈を AR 側でどう見せるかが未解決であることの実証になる【要旨】（[arXiv 2506.13189](https://arxiv.org/abs/2506.13189)）。ORCESTRA の全文で確認できた細部は次のとおりである。対象はデジタルツインだけで、実機もグリッパもなく、課題は「グリッパを牛乳瓶へ、次にハンマーへ動かす」といった経由点の移動である。検証条件は、ロボットが配置済みか、計画の種類が機体に合うか、参照物体の認識の確信度がしきい値以上か、座標が有限か、到達と逆運動学（移動台車は経路と障害物）が成り立つか、接触が許可されていないか、の論理積である。VLM の応答には診断情報 D が含まれるが、それを画面にどう出すかは書かれていない。手動教示では到達範囲外の目標を拒否し、到達範囲を半透明で表示する。評価は 5 名・20 試行の予備的なもので、成功は単純な形状と日用品が 5/5、工具が 4/5、大きな箱が 1/5 だった。著者は「失敗はすべてプレビュー段階で捕捉された」と述べるが、利用者がどう気づいたかの測定はない【全文】。つまり ORCESTRA は「検証してから見せる」構成の最も近い例だが、不合格の計画を黙って落とす側にあり、物体ごとのエラー表示は持たない。

マルチロボット版の MRPilot（Yang ら、arXiv 2610.07477）も全文で確認した。**家庭のタスクを扱い、計画の単位に理由を持たせ、失敗をロボットの位置に示す**点で、ORCESTRA より提案に近い。確認できた内容は次のとおりで、すべて【全文】である（6.1・6.2 節の統計値は読んでいない）。

- **計画の表現**：計画を「commitment」という 8 項目の組（id、robot、action、referent、place、receiver、waits、rationale）の集まりで持つ。waits は先に終わるべき手順、rationale はその手順を作った理由（例：「アームはキッチンに入れないので配送ロボットが運ぶ」）である。実行状態は pending / started / completed / failed / stop の 5 つ。
- **4 段階の表示**：Forming は指示のあいまいな対象を枠で囲んで選ばせる。Reviewing は LLM が出した 2 つの計画案を、ミニマップ（依存関係と実行順を番号と色で）と MR ビュー（経路の線）で見せて選ばせる。Following は進み具合のバーと現在の動作を出し、視野の外で対応が要るときは画面の端に緑の矢印を出す。Repairing はロボットを選んで局所的に直すか、全体を再計画する。
- **失敗の見せ方**：一定時間内に更新がないと failed になり、問題を特定のロボットに結びつけ、そのロボットの空間ラベルで入力を求める。印が付くのはロボットで、原因の物体やタスク後の配置ではない。
- **規範に関わる場面が 2 つある**：「この客室は PRIVATE と記されています。ドローンの進入を許可しますか」（権限・アクセス。システム側から空間ラベルで尋ねる）と、「Jim は仕事中に邪魔されたくない」（文脈・規範の調整。利用者側が言い出す）。ただし 9 個の介入場面は全参加者に同じものを出すため事前に決めてあり、システムがルールを照合して違反を見つけた結果ではない。権限・アクセスの場面だけは、会話型の比較条件と所要時間が同程度だった。
- **評価**：VR で再現した 2 階建ての家で、着席した 20 名が、同じ LLM プランナを使う会話型インタフェースと比べた（参加者内計画）。要旨によれば、負荷が下がり、状況認識・透明性・信頼・制御感が上がった。
- **著者が認める弱点**：可視化は「何が、どこで起きたか」は示せたが「なぜか」は示せず、アイコンや線は見落とされることもあった。原因と必要な対応を文章で示す会話型のほうが、説明としては優れていた。参加者は、扉が施錠されていたことをメッセージがなければ分からなかったと述べている。
- **測っていないこと**：介入の機会を事前に決めたので、利用者が予期しない問題に自分で気づけるかは測っていない。著者は今後の課題として、プランナの正確さを変えてエラー検出や適切な受容・拒否を測ることを挙げる。

提案との差は 3 つある。失敗や確認の印はロボットに付き、原因の物体には付かない。規範の場面は実行中に 1 件ずつ尋ねる形で、計画全体の事後状態の中で「動かせない物」を残して示す形ではない。理由（rationale）はデータとして持つが、空間の表示には出ておらず、参加者は「なぜ」が分からなかった。最後の点は、**ラベルに理由を書いて原因の物体に貼る**という提案の必要性を直接裏づける。

長期タスクでサブタスクの目標物体と目標姿勢を AR で事前にすり合わせる Ma らの研究は、After 状態の合意に最も近い【要旨】（[Ma ら HRI 2025](https://doi.org/10.1109/HRI61500.2025.10973947)）。

PRogramAR は言語を使わない直接の前身で、AR 上で If-Then と While-Do のルールを作る。**Rule Evaluator が各ルールの条件を世界の状態に照らして常時評価し、真で実行待ちのトリガーとアクションを緑、偽で実行されないルールを赤に塗る**【全文】（[PRogramAR](https://doi.org/10.1145/3640008)）。色は色覚に配慮したパレットから選んでいる。この赤はエラーではなく「今は発火しない」の意味である点に注意が要る。動作計画が立たないときは、ロボットの頭上に「Error: Zone too far or pick/place position too close to other boxes」という文を出すが、**4 名（25%）がこのメッセージの意味を読み解けずに最終課題でつまずいた**【全文】。著者は「非専門家をエラーの原因へ自然に導くフィードバックの統合」を今後の課題に挙げる。ロボットの頭上という固定先と、原因を一文にまとめた文面の両方が、原因の物体やゾーンを指せていなかった例として読める。

言語を主入力にしない近縁には、GhostObjects（実物に位置合わせした仮想ツインを動かしてゴールを指定）【要旨】（[arXiv 2508.11022](https://arxiv.org/abs/2508.11022)）、Wang らの X-HRTraining（新しい課題の計画を AR で人に確認させる）【要旨】（[arXiv 2302.01039](https://arxiv.org/abs/2302.01039)）、SiSCo（LLM がロボットから人への視覚信号を合成。完了時間約 73% 減）【要旨】（[arXiv 2409.13927](https://arxiv.org/abs/2409.13927)）がある。AR を使わない側では、検証器や批評器が見つけた問題を計画に結びつけて返す設計が先に進んでいる。RoboCritics は関節速度の超過・衝突・危険な手先姿勢を OK / Warning / Error の 3 段階と文章で返し、Fix ボタンで LLM に修正させる【本文】（[arXiv 2603.06842](https://arxiv.org/html/2603.06842v1)）。VeriPlan はルール翻訳器、厳しさのスライダ、モデル検査器を LLM プランナに足し、破られたルールの一覧を返す【本文】（[arXiv 2502.17898](https://arxiv.org/html/2502.17898v1)）。ImageInThat は 2D 画像上で望む状態を作って指示にし、10 名の実験でテキストより速かった（平均 110.8 秒対 363.88 秒）【要旨】（[arXiv 2503.15500](https://arxiv.org/abs/2503.15500)）。これらのエラー提示を実空間へ写す部分が、AR 側の空白である。論文の全リストは末尾の付録 A〜C にまとめた。

## RoboVisAR のタイムラインは可視化の出し分けで、エラーの印は持たない

RoboVisAR は Record（ロボットの動作例を記録）、Design（記録のタイムライン上で可視化を作る）、Play（元のロボットか別のロボットで試す）の 3 段階で動く【全文】（[KOPS 全文](https://kops.uni-konstanz.de/server/api/core/bitstreams/5af29385-e262-4de2-a331-518fc13d06b9/content)）。タイムラインは Pronto と Rapido に着想を得ており、「どの可視化が追加されているか」と「それがいつ有効か」を示す。可視化は Path、Point of Interest、Safety Zone、Robot State、Message、Force/Torque の 6 種類、表示条件は Robot State、Proximity、Box、Force/Torque の 4 種類で、専門家 3 名が 10 分以内に可視化を作れた【全文】（[著者ページ](https://ryosuzuki.org/robovisar/)）。その後、本文（Zotero の全文）で細部を確認した。以下はすべて【全文】である。

- **記録する項目**：ロボットからは状態、関節角、手先位置（TCP）、力・トルク、経路。HMD からは利用者の手と頭の位置。記録は複数作れ、著者は例として「通常の実行」と「エラーの場合（error-case）」を挙げるが、Design で使えるのは一度に 1 本だけである。
- **タイムラインの操作**：スライダで記録の任意の時刻へ移動でき、再生ボタンを押すと、記録時の姿勢を再現する仮想ロボットの上で可視化を確かめられる。可視化を追加するときは、スライダで選んだ時刻のデータを使って全種類の見本がその場に出る。
- **タイムラインに描かれるもの**：追加した可視化の一覧と、それぞれが有効な区間だけである。条件そのものや、記録データ中の出来事（ロボットの状態変化など）は描かれない。参加者 P1 と P2 は、出来事をタイムラインに出す拡張を求めた。
- **条件の働き**：表示・非表示を切り替えるほか、有効なときに可視化の属性を変えられる（例：Safety Zone をロボット動作中は赤、それ以外は緑にする）。条件は反転できるが、AND / OR での組合せはできない（P1 と P3 が指摘）。
- **Play では時刻に依存しない**：条件は文脈に対して定義され、特定のプログラムに結びつかないので、可視化の挙動は「タイムラインではなく出来事（データの変化）」で決まる。タイムラインは設計時の確認用で、実行時の仕組みではない。
- **Message 可視化**は「step back」「help」「wait」の 3 種類の定型パネルで、エラーや失敗の理由を書くものではない。
- 評価は AR の専門家 3 名で、4 つの可視化を作る課題の平均は 9 分 30 秒だった。P2 はタイムラインを「動画編集ソフトに似ている」と述べた。

「エラーの場合」の記録を作れるという一文が、RoboVisAR がエラーに触れる唯一の箇所で、エラーを検出したり印を付けたりする仕組みは本文にもない。

後継の ARTHUR は RoboVisAR を「作る前にロボットプログラムを実行して記録を作る、タイムライン方式」と要約し、限界を 3 つ挙げる。ロボットの可視化だけで外部の内容を出せないこと、実行中にユーザー入力を受けず情報がロボットから人への一方向であること、空中での 2D UI 編集がつらいことである【本文】（[ARTHUR](https://arxiv.org/html/2501.02304v1)）。ARTHUR 自身は feedback 20 種、action 10 種、condition 18 種を持つが、エラーや失敗の処理は書かれておらず、警告音や立入禁止ゾーンが例に出るだけである【本文】。ここから 3 つのことが言える。RoboVisAR の条件（近接、箱領域、力）はそのままエラー表示の発火条件に読み替えられるが、論文はそう位置づけていない。記録済みの実行か取り込んだ工程表が前提なので、LLM がその場で作る計画には、記録の代わりにシミュレーションした実行をタイムラインに置く必要がある。タイムラインが示すのは可視化の有効区間であってタスクのステップではないので、ステップ単位でエラーを付けるには区切りの層が要る。

エラーを「列のどこか」に結びつける研究と、「空間のどこか」に結びつける研究は別々に発達している。AR デバッグ系は空間に強く時間に弱い。Ikeda と Szafir はロボット研究者 24 名で RViz・2D GUI・AR を比べ、**8 名（33%）が「実行前に全経由点をたどって見る機能」と「過去の動作を見直す機能」を求めた**と報告する【本文】（[Ikeda & Szafir HRI 2022](https://par.nsf.gov/servlets/purl/10354657)）。画面ベースの系は時間に結びつけるが実空間に出さない。RoVer は社会規範の違反を平易な文の一覧で返し、性質によっては原因のグループまで絞る【本文】（[RoVer](https://par.nsf.gov/servlets/purl/10080246)）。Polaris は計画を地図に重ねて 1 分岐ずつ見せるが、衝突するゴールは黙ってコンパイルから外し、警告は出さない【本文】（[Polaris](https://arxiv.org/html/2403.13988v1)）。これは反面教師で、消えるだけでは利用者は理由に気づけない。両方を満たす例は事後の再生に限られ、Han らは Behavior Tree のサブツリー単位で記録を再生し、緑の投影で「掴もうとした物」、白で「正しく認識した物」を示して知覚の失敗を分からせる【本文】（[Han ら](https://ar5iv.labs.arxiv.org/html/2210.00075)）。ロボット以外では、スマートホームの TAP デバッグがタイムライン上に「ここがおかしい」と印を付け、修正を当てた場合の履歴を再生する。30 名の評価で最も時間がかかったのは、おかしな時刻を探す段階だった【本文】（[Zhang ら IMWUT 2022](https://par.nsf.gov/servlets/purl/10387467)）。AR 組立ガイドは部品の現在位置と目標位置の枠に今のステップを組み合わせるが、誤るのは人でロボットではない【要旨】（[Augmented Assembly](https://arxiv.org/abs/2601.11535)）。

依頼された 8 段階にエラー表示を置ける場所を整理すると、次の表になる。段階ごとに自然な固定先が違い、指示・計画・ルール照合は列や文に、理解・認識・動作計画・実行は空間に寄る。

| 段階 | 起きるエラー | 置ける場所 | 先行例と見せ方（確認度） | 固定先 | 時点 |
|---|---|---|---|---|---|
| 言語指示 | 曖昧、実行不能 | 指示文、文中の語 | CLARA：certain / ambiguous / infeasible の 3 分類【未検証】。KnowNo：候補が複数残れば選択肢つきで尋ねる【要旨】。Raman ら：原因になったユーザー自身の文にさかのぼる【未検証】 | 文 | 事前 |
| 理解（グラウンディング） | 違う物・場所を指す | 語と物の対応、候補の物 | MARCER：関係する物体と面をオレンジで強調し、ルールの説明文を返して承認を待つ【全文】。Rosen ら・Sibirtseva ら：候補を MR で示して問い返す【未検証】 | 空間（物） | 事前 |
| 認識 | 見落とし、誤認 | 認識した物の上、見落とした実物の位置 | Wozniak ら：VR で認識結果と実物を比べて直す【要旨】。iTeach：検出結果を重ね、視線と音声で失敗例に注釈【要旨】。Han ら：白と緑の投影【本文】 | 空間（物） | 事前／事後 |
| 計画 | 手順の抜け、順序違い、前提の見落とし | 列のステップ、ステップの対象物 | Polaris：地図に重ねた計画、印なし【本文】。LeMasurier ら：「[前提] なので [サブゴール] ができません」の定型文【本文】。HRI Grounding：1 ステップ 1 コントロールで承認【要旨】 | 時間（ステップ） | 事前 |
| ルール照合 | 規範・安全・好みの違反 | 違反したルール名、違反を起こすステップ、対象物 | RoVer：文の一覧【本文】。VeriPlan：破られたルールの一覧と厳しさのスライダ【本文】。U-Define：hard / soft【要旨】。PRogramAR：ルールの真偽を緑と赤で表示（エラーではなく発火状態）【全文】 | 時間（図の中）。**物への固定は見つからず** | 事前 |
| 動作計画 | 届かない、経路なし、衝突 | 軌道上の点、邪魔な物、届かない目標位置 | X-OOHRI：到達・把持・可搬を決定木で判定し、物体を赤く塗り「Too high to reach」などのタグを付ける【全文】。PRogramAR：ロボット頭上にエラー文、25% が読み解けず【全文】。Rosen ら：軌道を重ね、衝突は人が判定【要旨】。RoboCritics：3 段階の文【本文】 | 空間（物・軌道） | 事前 |
| 実行 | 掴み損ね、力の超過、人の接近 | 手先、安全ゾーン、今のステップ | Hietanen ら：赤い仮想の柵と停止【本文】。RoboVisAR：Proximity / Box / Force-Torque の条件で出し分け【全文】。X-OOHRI：実行失敗時にエラーを記録し、赤色とエラーメッセージを物体に付けて後で見直せる【全文】 | 空間 | 実行中 |
| 結果確認 | 最終状態が目的と違う | 完了後の物の位置、失敗した時刻 | Han ら：BT 単位の再生と投影【本文】。Zhang ら：タイムラインに印【本文】。Richards ら：故障前 15 秒の再生、タブレットが AR より好まれた【要旨】 | 時間が主 | 事後 |

表から読み取れる設計上の含意は 3 つある。計画やルールのエラーを空間に出すには「そのステップが対象にする物や場所」へ写す一手間が要り、この写像を事前に行う UI は今回見つからなかった。重大度を段階に分ける設計は RoboCritics（Warning / Error）、VeriPlan（厳しさ）、U-Define（hard / soft）で独立に現れており、「止めるエラー」と「知らせるだけの注意」を分けることには複数の裏づけがある。伝える時点は先回りが良く、LeMasurier らは 224 名の実験で、前提が破れた時点で実行前に説明するほうが、知的に見え、信頼され、タイミングも良いと評価されたと報告する【本文】（[LeMasurier ら HRI 2024](https://faculty.cs.byu.edu/~crandall/papers/LeMasurier_etal_HRI2024.pdf)）。ただしこれは言葉での説明の結果で、AR の印について同じ比較をした研究は見つかっていない。色の意味づけも研究間でそろっておらず、安全ゾーンは赤、Han らの緑は「選んだ物」、PRogramAR の赤は「発火しないルール」である。

## 実物を消して仮想コピーを動かす表示は既にあり、新規性は検証用途にある

調査途中の判断を一つ修正する。Reality Promises の全文では、デカップリングに 2 つのモードがある。**removal mode は「ロボットを隠すのと同じ object removal 技術で、まず実物体を視界から隠し、その位置に仮想物体を置く」**。仮想物体が動き出すと元の場所は空に見える。augmented mode は透明な仮想クローンを実物に重ね、操作が始まると不透明になり、実物は見えたまま残る【全文】（[Reality Promises](https://doi.org/10.1145/3746059.3747660)）。Seamless MagicMove ではピンチした瞬間に実物が隠れ、reveal lens で見ると「実物は小さな視覚パッチの裏に隠れているだけ」で、ロボットが実物を取り上げた時点でパッチを外す【全文】。したがって「DR はロボットを消す用途のみ」は正確ではなく、**操作対象の実物体も消している**。なお本文は物体については "object removal" と書き、"diminished reality" の語は関連研究の説明で使っている。もう一方の確認事項、X-OOHRI の全文に "diminish" が 0 件という点はそのまま維持でき、X-OOHRI は実物を消さない。むしろ X-OOHRI の参加者 P6 は「動かした実物をグレーアウトしてほしい」と要望しており、P11 と P13 は GhostObject を輪郭やハイライトで見分けやすくするよう求めた【全文】（[X-OOHRI](https://doi.org/10.1145/3757279.3785569)）。実物とゴーストが二重に見える問題が利用者から指摘された、という裏づけになる。

この修正を踏まえても、提案には差が残る。Reality Promises の目的は錯覚で、検証ではない。ユーザーが仮想物体を放した瞬間に約束が成立してロボットが動き出し、承認の段階はない。ゴールはユーザーの手か、プログラムされた仮想キャラクターが決め、言語指示からプランナが決めるのではない。実現できない置き場所は「rectification」で最も近い有効な姿勢へ黙って補正し、理由は示さない【全文】。扱うのは 1 物体ずつの移動で、複数物体の計画全体の事後状態ではなく、「食洗機に入れる」のような複雑な操作は将来課題である【全文】。ユーザー評価も行っておらず、不可視ロボットの受容は「ユーザースタディに基づく将来研究」とされる【全文】。同じ著者らの Scene Responsiveness は、事前スキャンした部屋のデジタルツインで実物を消して仮想コピーを動かすが、ロボットはいない【未検証】（[Scene Responsiveness](https://doi.org/10.1145/3586183.3606825)）。一般 MR では SceneCtrl が実物の削除・移動・複製を、Remixed Reality が空間と時間の操作を既に実現している【未検証】（[SceneCtrl](https://doi.org/10.1145/3126594.3126601)、[Remixed Reality](https://doi.org/10.1145/3173574.3173703)）。インテリアや景観では、既存の家具や建物を消して新しいものを置く Before/After が確立している【未検証】（[Siltanen](https://doi.org/10.1007/s00371-015-1174-z)、[Kido ら](https://doi.org/10.1016/j.envsoft.2020.104759)）。DecluttAR は机上の散らかりを HMD で減光・除去する【未検証】（[DecluttAR](https://doi.org/10.1145/3582700.3582718)）。

ロボットの未来を AR で見せる主流は、ゴーストロボット、軌跡、ゴースト物体を足す表示である。仮想コピーをゴールへ動かして実物が後追いする系譜は exTouch、TouchMe、Frank ら、GhostObjects、X-OOHRI と続くが、いずれもゴールを指定する入力手段で、プランナが決めた結果を人が検証する出力としての全景表示ではない（[exTouch](https://doi.org/10.1145/2460625.2460661)、[Frank ら](https://doi.org/10.3389/frobt.2017.00020)）【未検証】。VAM-HRI サーベイは「実物体の位置に仮想物体を重ねて実行前にプレビューする」類型（Spatial Previews、Alteration Previews）を定義するが、実物を消す操作のカテゴリは持たず、Body Diminishments はロボット身体の縮減を指す【本文】（[Walker ら](https://arxiv.org/abs/2202.11249)）。ロボティクスでの DR は、ロボット自身を透明にして遮蔽を解く用途がほとんどで、Taylor らは労力低減の見込みと、効率・選好での欠点を報告した【要旨】（[Taylor ら IROS 2020](https://doi.org/10.1109/iros45743.2020.9341536)）。AR を使わない側では、DALL-E-Bot、Dream2Real、SG-Bot、StructDiffusion がゴール状態を画像や 3D として生成するが、評価するのは VLM やロボット内部で、人には見せない【未検証】（[Dream2Real](https://doi.org/10.1109/icra57147.2024.10611220)）。人がゴール状態を作って確かめる代表は ImageInThat で、2D である。

以上から、新規性は次のように書くのが安全である。今回の調査範囲では、**言語指示から得た計画の完了後状態を、実物の除去と仮想コピーの配置で実行前に提示し、人の検証・承認の手段として評価した研究は見つからなかった**。表示技術としての先行は Reality Promises の removal mode と Scene Responsiveness にあり、差は目的（錯覚ではなく検証）、ゴールの出所（ユーザーの手ではなくプランナ）、単位（1 物体ではなく計画全体）、時点（実行と同時ではなく承認前）、評価（エラー検出や過信を測る）にある。設計上の注意は DR 研究から引ける。Cheng らは、不透明度を下げる除去が好まれ、輪郭など「消した物の文脈を保つ仕組み」が評価され、移動の少ないタスクなら文脈理解の低下が許容されたと報告する【要旨】（[Cheng ら CHI 2022](https://doi.org/10.1145/3491102.3517452)）。InvisibleRobot は完全に消すモードと輪郭を残すモードを用意した【要旨】（[InvisibleRobot](https://doi.org/10.1109/ismar-adjunct.2019.00-55)）。Reality Promises 自身も、近くでロボットが動く間はユーザーが着席している前提を置く【全文】。After 表示中に消した実物の輪郭を残すこと、プレビュー中の歩行を想定するなら衝突対策を入れることが妥当である。比較技法としては、Gleicher らの並置・重畳・明示的符号化の 3 分類が使え、提案は置換型のトグル、従来のゴーストは重畳、移動矢印は明示的符号化に当たる【未検証】（[Gleicher ら](https://doi.org/10.1177/1473871611416549)）。AR でロボット計画の Before/After 比較技法を系統的に比べた研究は見つからなかった。未確認として残るのは、Wiley の書籍章 "Human–Robot Interaction through Diminished Reality"（[DOI](https://doi.org/10.1002/9781394470143.ch21)）の中身と、ISMAR・IEEE VR のポスター類である。

## 違反で動かせない物体を残す表示は X-OOHRI の型を規範へ広げる位置にある

X-OOHRI は「できない理由を物体に付けて示し、解決策を選ばせる」直接の先行例である。全文で確認できた仕組みは次のとおりである。VLM（GPT-5.1）が物体とロボットをクラスのインスタンスとして符号化し、**実行可能性は決定木 f : RA × OA × S → e で判定する**。操作タスクでは到達可能性（遮蔽、ナビゲーション、関節限界）、把持可能性（大きさ・向きとグリッパの開き）、可搬性（重さと可搬重量）を調べる【全文】。伝える経路は 5 つで、白い円のシグニファイア、ラジアルメニュー（今はできない操作はグレーアウト、そもそも無い操作は非表示）、**赤色による「できる／できない」の二値表示**、原因を示す説明タグ（短いラベルで、詳しいツールチップに展開できる。文面は「よくあるエラー」から初期化し、新しい失敗型で拡張する）、解決のプレビューアニメーションである【全文】。解決は混合主導で、システム側は Auto（他の物を動かして可能にする）、Alternative（同じクラスの別の物体か別の目標姿勢を提案）、Ignore（制約を無視して試させる）、ユーザー側は Virtual（準備の操作を足す）と Physical（AR の外で手伝う）の 5 つがある【全文】。機材は Quest 3 と Stretch 3 で、技術実証は実機で行ったが、**14 名のユーザー評価は実行前の操作だけを対象にし、物理ロボットは使わず、比較条件のない探索的な研究**である。SUS は 79.3 だった【全文】。

X-OOHRI が扱わないものを正確に書く。決定木が見るのはロボットの能力、物体の操作可能性、世界の状態で、例は高さ、把持できない向き、大きさ、遮蔽、届かない棒である。**家庭ルール、社会規範、持ち主の区別、ユーザーが言葉で書いた制約は判定対象に入っていない**【全文】。本文で preference に触れるのは、導入部の「個人化された指示」という動機と、将来課題の「実現可能な軌道に操作を制約すればユーザーの好みが分かるかもしれない」という一文までである。色は赤一色の二値で重大度の段階はない。表示が出るのは、ユーザーが 1 物体（または投げ縄で選んだ数個）を操作している最中で、プランナが作った計画全体の事後状態の中に「動かせなかった物体」を残す表示ではない。著者は条件トリガー（MARCER、RoboVisAR）やタイムライン編集（GhostAR）との統合を今後の方向として挙げている【全文】。一方で X-OOHRI を「物理的な制約しか扱えない劣った系」と書くのも不正確で、色＋タグ＋解決メニュー＋プレビューして確定、という構成はルール違反にもそのまま転用できる型であり、提案はこの型の適用範囲を広げるものと位置づけるのが妥当である。

家庭ルールや規範の違反を物体ごとに AR ラベルで示す研究は、今回の検索では見つからなかった。規範に最も近づいているのはマルチロボット版 MRPilot で、「PRIVATE と記された部屋への進入許可」をロボットの空間ラベルで尋ね、「邪魔されたくない」という住人の希望による計画変更も扱う【全文】（[arXiv 2610.07477](https://arxiv.org/abs/2610.07477)）。ただし、これらは実験のために事前に決めた場面で、実行中に 1 件ずつ出る。ルールとの照合結果を計画プレビューの中で物体ごとに示すものではない。LLM ロボットの制約遵守の研究は、違反を人に見せずに自動で回避する設計が主流である。Safety Chip は自然言語の制約を時相論理に変えて違反行動を刈り取り、理由の言語化は主に LLM に返す【未検証】（[Safety Chip](https://doi.org/10.1109/icra57147.2024.10611447)）。RoboGuard は計画と仕様の衝突を制御合成で自動解決する【未検証】（[RoboGuard](https://doi.org/10.1109/lra.2026.3667488)）。CAPE は前提条件エラーを LLM に返して修正行動を出させ、人には聞かない【未検証】（[CAPE](https://doi.org/10.1109/icra57147.2024.10611376)）。Reality Promises の rectification も同じく黙って直す側である【全文】。提案はこれらと逆の立場をとり、違反した物体を見える形で残して住人に返す。「動かせる物は動かし、動かせない物は残す」は、全ゴールは満たせない oversubscription planning と同じ構造で、物体 1 個の移動をソフトゴール 1 個と見れば、Eifler らの「p を満たすと q を諦めることになる」という説明がそのまま物体単位の説明になる【未検証】（[Eifler ら AAAI 2020](https://doi.org/10.1609/aaai.v34i06.6534)）。ただし XAIP の説明を AR で空間に固定した研究は確認できなかった。

ラベルの中身は、文献から 4 つの要素に整理できる。どのルールに当たったか（Raman らは達成不能の原因をユーザー自身の文にさかのぼって返す【未検証】、[RSS 2013](https://doi.org/10.15607/rss.2013.ix.023)）、何と両立しないか（Eifler ら）、何を変えれば動かせるか（制約の緩和と excuse【未検証】、[Eifler ら IJCAI 2022](https://doi.org/10.24963/ijcai.2022/641)、[Göbelbecker ら](https://doi.org/10.1609/icaps.v20i1.13421)）、ユーザーが知らない前提だけを伝える（モデル調停【未検証】、[Chakraborti ら](https://doi.org/10.24963/ijcai.2017/23)）である。文型は LeMasurier らの「[前提] なので [ステップ] ができません」が短文の型として使える。ラベルの種類は、CLARA の 3 分類に沿って、ルール違反、物理的に不可能、認識や指示が曖昧、の 3 つに分けられる。PRogramAR の失敗は、原因を 2 つ並べた一文をロボットの頭上に出したことにあり、原因の物体やゾーンのそばに、原因を 1 つに絞って出すべきだという教訓になる。配置は view management の研究が指針になり、違反した実物を隠さない、複数のラベルを重ねない、引出線でつなぐ、視点が動いてもラベルを跳ねさせない、の 4 点である【未検証】（[Azuma & Furmanski](https://doi.org/10.1109/ismar.2003.1240689)、[Hedgehog labeling](https://doi.org/10.1109/vr.2014.6802046)）。フォームの研究は、エラーを入力途中に即座に出すより区切りでまとめて出すほうがよいとしており、プレビューの時点で違反をまとめて見せる設計と整合するが、AR にそのまま当てはまるとは限らない【未検証】（[Bargas-Avila ら](https://doi.org/10.1016/j.intcom.2007.01.003)）。

解決のインタラクションは、文献上 5 つに整理できる。人に聞く（KnowNo）、代案を出す（X-OOHRI の Auto と Alternative）、ルールを緩めるか上書きする（VeriPlan のスライダ、U-Define の hard / soft、X-OOHRI の Ignore）、計画を直接編集する（仮想ツインの操作、Fang らのドラッグ）、認識を直す（iTeach、Wozniak ら）である。認識の修正は「違反と判定されたが実は誤認識だった」場合の出口として必要になる。X-OOHRI は VLM の誤りとして、見えない属性の誤推定（不透明なボトルの重さ、偽物の本）と、遮蔽や視野による空間的誤りを挙げている【全文】。スマートホームの TAP 研究は、ルールの衝突を作成画面の該当ルールのそばに出す（EUDebug は 15 名の探索的調査【要旨】、[EUDebug](https://doi.org/10.1145/3290605.3300618)）。提案はそれを該当する実物のそばに出す。ルールを作る側（ARC-LfD、Virtual Borders、MARCER）と、制約に当たったことを伝える側（X-OOHRI）を一つの流れにつないだ研究は見つからなかった。解決の結果を次回以降のルールとして残す流れには DROC の先例がある【未検証】（[DROC](https://doi.org/10.1109/icra57147.2024.10610455)）。スマートホームのルール衝突を AR でその場に示す査読論文、AR で建築法規違反を現場に重ねる査読論文も、今回は見つからなかった。

## Conclusion

三つの案は別々の新規性ではなく、一つの主張にまとめられる。既存の系は、計画エラーを列（文、ステップ、ルール一覧）に付けるか、物体（赤色、タグ）に付けるかのどちらかで、後者は物理的な実行可能性に限られていた。Before/After 表示は、この二つをつなぐ場になる。事後状態の中で「動いた物」は計画が通ったステップ、「現場に残った物」は通らなかったステップを表すので、残った実物に付けたラベルは、空間への固定と列への固定を同時に果たす。消さないこと自体がエラーの印になる、という点が、赤く塗るだけの X-OOHRI とも、黙って補正する Reality Promises や自動回避するガードレール系とも違う。

評価は、この主張を過信の危険と対にして組む必要がある。HRI Grounding は非 AR のステップ列 UI で、16 名が欠陥のある計画を d′ = 2.90 で見分け、失敗するはずの 96 ミッション中 85 を回復したと報告する【要旨】（[HRI Grounding](https://doi.org/10.1109/LRA.2026.3730218)）。一方、LLM エージェントの研究は、もっともらしい計画が誤って信頼されやすいと結論する【要旨】（[He ら CHI 2025](https://arxiv.org/abs/2502.01390)）。きれいに片付いた After の光景は、まさにもっともらしい計画である。AR の空間プレビューで計画エラーの検出率を測った研究は見つかっていないので、欠陥を埋め込んだ計画を混ぜ、DR つき Before/After、違反ラベルつき、ゴースト重畳のみ、非 AR（タブレットかテキスト列）を比べ、検出（d′）と受容率を分けて測る設計が、先行研究と直接比べられる最初の結果になる。同じ情報ならタブレットが AR より好まれた例（[Richards ら](https://doi.org/10.1007/s12369-025-01219-4)）がある以上、非 AR のベースラインは省けない。X-OOHRI の評価が物理ロボットなしで行われ、AR 上の仮想ロボットと実機で信頼の差に明確な証拠がなかったという報告（[Guerra ら](https://doi.org/10.1145/3820253.3820273)【要旨、会議名は未検証】）もあるので、シミュレーション前提の計画でも評価は成立する。MRPilot の著者も、可視化が透明に感じられることと、利用者が誤りを見抜けることは別だとして、エラー検出と適切な受容・拒否の測定を今後の課題に挙げており、この評価設計はその空白に答える形になる。MARCER と PRogramAR を引用する後続論文は付録 H にまとめた（Semantic Scholar で 43 件）。家庭ルールの違反表示を扱うものはその中になかった。RoboVisAR、ORCESTRA、MRPilot の本文は確認済みである。

---

## 付録 A：言語指示 × AR/MR/VR の計画提示（MARCER の類似研究）

| 題名 | 著者・会場・年 | 要点 | 確認度 | URL |
|---|---|---|---|---|
| MARCER: Multimodal Augmented Reality for Composing and Executing Robot Tasks | Ikeda, Gramopadhye, Nekervis, Szafir. HRI 2025 | LLM が TAP ルールを生成、AR でゾーン指定・強調・最終状態プレビュー。失敗の伝達は不十分と著者が明記 | 全文 | [DOI](https://doi.org/10.1109/HRI61500.2025.10974232) |
| Enabling Waypoint Generation for Collaborative Robots using LLMs and Mixed Reality | Fang, Zieliński, Maes, Paradiso, Blumberg, Kjærgaard. ICRA 2024 WS | LLM の経由点を AR に重ね、編集・承認 | 要旨 | [arXiv](https://arxiv.org/abs/2403.09308) |
| LLM-Based Waypoint Authoring via Augmented Reality for Human–Robot Interaction（AURaPath） | Hashemi, Mojallal, Mozaffari, Alirezaee. Applied Sciences 2026 | HoloLens 2 + UR10、2 段階確認ゲート | 要旨 | [MDPI](https://www.mdpi.com/2076-3417/16/20/9974) |
| ORCESTRA: VLM-driven Visual Robot programming in Mixed Reality | Snegirev, Semenyakina, Konenkov, Lykov, Altamirano Cabrera, Tsetserukou. arXiv 2026 | 検証を通った計画だけを MR でプレビューし確認後に実行。不合格の理由表示なし。デジタルツインのみ、5 名・20 試行 | 全文 | [arXiv](https://arxiv.org/abs/2608.00775) |
| MRPilot: Supervising and Intervening LLM-Based Multi-Robot Teams through Mixed Reality | Yang, Qian, Zhan, Tran, Liu, Jin. arXiv 2026 | 家庭タスク。計画を理由つきの commitment で持ち、4 段階（Forming / Reviewing / Following / Repairing）で表示。失敗はロボットの空間ラベルに出る。「何が・どこで」は示せたが「なぜ」は示せなかった。VR、20 名 | 全文 | [arXiv](https://arxiv.org/abs/2610.07477) |
| MRPilot: A Mixed-Reality System for Responsive Navigation of General Procedural Tasks（上と同名の別論文） | Yang, Zhou, Xu, Fu, Huang. ISMAR 2025 | ロボットは登場しない。LLM が手順を構造化し、実物に仮想の目印を固定して、人の作業の進み具合を検出し手順を自動で進める。LLM が出した手順のうち明らかな誤りは利用者に見せる前に除く | 全文（冒頭と該当箇所） | [DOI](https://doi.org/10.1109/ISMAR67309.2025.00031) |
| LLM-Driven Augmented Reality Puppeteer: Controller-Free Voice-Commanded Robot Teleoperation | Zhang, Orthmann, Welle, Van Haastregt, Kragic. HCII 2025 | 仮想ロボットが先に動く確認型 | 要旨 | [arXiv](https://arxiv.org/abs/2502.09142) |
| Gesture First, LLM-Assisted Voice Complement: Exploring Multimodal Robot 'Puppeteer' Teleoperation Via Virtual Counterpart in Augmented Reality | Zhang, Orthmann, Ji, Welle, Van Haastregt, Kragic. arXiv 2025 | N=42、音声追加で遅延と誤認識 | 要旨 | [arXiv](https://arxiv.org/abs/2506.13189) |
| Multimodal Grounding for Embodied AI via Augmented Reality Headsets for Natural Language Driven Task Planning | Wanna, Parra, Valner, Kruusamäe, Pryor. arXiv 2023 | LLM × AR ヘッドセットの最初期。表示内容は不明 | 要旨 | [arXiv](https://arxiv.org/abs/2304.13676) |
| An AR-assisted Human-Robot Interaction System for Improving LLM-based Robot Control | Zhao, Lou, Tan, Lv. IEEE CIS-RAM 2024 | 題名のみ | 未検証 | [DOI](https://doi.org/10.1109/CIS-RAM61939.2024.10673005) |
| An augmented reality-enhanced large language model-based interactive system for human-robot collaboration | Xu, Zhou, Zhou, Zheng. RCIM | 題名のみ | 未検証 | [DOI](https://doi.org/10.1016/j.rcim.2026.103396) |
| Robi Butler: Multimodal Remote Interaction with a Household Robot Assistant | Xiao, Janaka, Hu, Gupta, Li, Yu ほか. ICRA 2025 | MR 越しに言語＋指差しで家庭ロボットへ指示 | 未検証 | [arXiv](https://arxiv.org/abs/2409.20548) |
| Supporting Long-Horizon Tasks in Human-Robot Collaboration by Aligning Intentions via Augmented Reality | Ma, Yang, Ikeda, Szafir. HRI 2025 | サブタスクの目標物体・姿勢を AR ですり合わせ | 要旨 | [DOI](https://doi.org/10.1109/HRI61500.2025.10973947) |
| SiSCo: Signal Synthesis for Effective Human-Robot Communication Via Large Language Models | Sonawani, Weigend, Ben Amor. IROS 2024 | LLM が視覚信号を合成（ロボット→人） | 要旨 | [arXiv](https://arxiv.org/abs/2409.13927) |
| Teaching the Teacher: Live Foundation Model and Augmented Reality Feedback for Human-to-Robot Skill Transfer | Moorman, Luebbers ほか. HRI 2026 | 基盤モデルの文章＋AR の視覚フィードバック | 要旨 | [DOI](https://doi.org/10.1145/3757279.3788667) |
| fARfetch: Enabling Collocated AR-HRC in Large Visually Diverse Environments with VLM-Driven AR Content Adaptation | Fronk, Ye, Hunt, Pajic, Gorlatova. RO-MAN 2026 | VLM で AR 表示を適応 | 要旨 | [arXiv](https://arxiv.org/abs/2606.25162) |
| EgoAsk: Egocentric Teaching of Personalized Object Knowledge for Household Robots | Hu, Zuo, Shen, Chen, Calero Tobar, Ge, Sun, Guo. arXiv 2026 | スマートグラスで個人化された物体知識を質問、N=18 | 要旨 | [arXiv](https://arxiv.org/abs/2609.16766) |
| InteractGuide: LLM-Enhanced Multimodal Reasoning for User-Centric Interaction Recommendations in AR-HRI Authoring | Pei ほか. ACM MM 2025 | LLM が操作方法を推薦 | 要旨 | [DOI](https://doi.org/10.1145/3746027.3754542) |
| Historical visual question answering with large language model for Augmented Reality-assisted Human–Robot Collaboration | Lv, Si, Gao, Bao. J. Manufacturing Systems 2025 | 題名のみ | 未検証 | [DOI](https://doi.org/10.1016/j.jmsy.2025.10.005) |
| Trustworthy Collaborative Agents for Industrial IoT: A Multimodal Mixed Reality Framework for Human-Centric Precision Assembly | Huang ほか. IEEE IoT-J 2026 | 精密組立向け MR 協働エージェント | 要旨 | [DOI](https://doi.org/10.1109/JIOT.2026.3722235) |
| Beyond Static Instruction: A Multi-agent AI Framework for Adaptive Augmented Reality Robot Training | Leins, Gonnermann-Müller, Teichmann, Pokutta. HRI Companion 2026 | AR ロボット訓練、36 名 | 要旨 | [arXiv](https://arxiv.org/abs/2603.00016) |
| Gaze-supported Large Language Model Framework for Bi-directional Human-Robot Interaction | Rüppel, Rudenko, Schreiter, Magnusson, Lilienthal. RO-MAN 2025 | 視線＋音声、AR 表示の有無は未確認 | 要旨 | [arXiv](https://arxiv.org/abs/2507.15729) |
| Tell-XR: Conversational End-User Development of XR Automations | Carcangiu, Manca, Mereu, Santoro, Simeoli, Spano. INTERACT 2025 | ロボットではないが、会話で定義→確認→修正 | 要旨 | [arXiv](https://arxiv.org/abs/2504.09104) |
| End-user automation authoring in VR and AR through conversations: patterns, errors and user recovery strategies | 同グループ. Behaviour & Information Technology 2026 | 題名のみ | 未検証 | [DOI](https://doi.org/10.1080/0144929x.2026.2714168) |
| Reframing Human-Robot Interaction Through Extended Reality | Zhang, Ma, Kragic. Empathic Computing | 視点論文 | 要旨 | [arXiv](https://arxiv.org/abs/2512.02569) |
| Integrating Large Language Models with Multimodal Virtual Reality Interfaces to Support Collaborative Human-Robot Construction Work | Park, Menassa, Kamat. arXiv 2024 | VR。Approval ボタンで承認 | 要旨 | [arXiv](https://arxiv.org/abs/2404.03498) |
| Prompting an Embodied AI Agent: How Embodiment and Multimodal Signaling Affects Prompting Behaviour | Zhang, Au Yeung, Aurelia, Onishi, Chulpongsatorn, Li, Tang. CHI 2025 | VR 内エージェントが言及中の物体をハイライト | 要旨 | [DOI](https://doi.org/10.1145/3706598.3713110) |
| LaMI: Large Language Models for Multi-Modal Human-Robot Interaction | Wang, Hasler, Tanneberg, Ocker, Joublin, Ceravola ほか. CHI EA 2024 | LLM 駆動 HRI（AR ではない） | 未検証 | [arXiv](https://arxiv.org/abs/2401.15174) |
| Explainable Human-Robot Training and Cooperation with Augmented Reality | Wang, Belardinelli, Hasler, Stouraitis, Tanneberg, Gienger. CHI EA 2023 | 計画を AR で人に確認させる | 要旨 | [arXiv](https://arxiv.org/abs/2302.01039) |
| Increasing Robot Autonomy via Motion Planning and an Augmented Reality Interface | Hernández, Sobti, Sciola, Moll, Kavraki. RA-L 2020 | 高レベル要求→計画を AR で確認 | 未検証 | [DOI](https://doi.org/10.1109/LRA.2020.2967280) |
| Comparison of Multimodal Heading and Pointing Gestures for Co-Located Mixed Reality Human-Robot Interaction | Krupke, Steinicke, Lubos, Jonetzko, Görner, Zhang. IROS 2018 | 音声＋指差し、仮想ロボットでプレビュー | 未検証 | [DOI](https://doi.org/10.1109/IROS.2018.8594043) |
| Mixed Reality as a Bidirectional Communication Interface for Human-Robot Interaction | Rosen, Whitney, Fishman, Ullman, Tellex. IROS 2020 | 参照の曖昧さを MR で問い返す | 未検証 | [DOI](https://doi.org/10.1109/IROS45743.2020.9340822) |
| A Comparison of Visualisation Methods for Disambiguating Verbal Requests in Human-Robot Interaction | Sibirtseva, Kontogiorgos, Nykvist, Karaoguz, Leite, Gustafson, Kragic. RO-MAN 2018 | 候補の提示を HMD・投影・画面で比較 | 未検証 | [DOI](https://doi.org/10.1109/roman.2018.8525554) |
| An Augmented Reality Motion Planning Interface for Robotics | Hutton, Sohre, Davis, Guy, Suma Rosenberg. IEEE VR 2019 | 題名のみ | 未検証 | [DOI](https://doi.org/10.1109/VR.2019.8798010) |

AR を使わない言語駆動の計画提示・検証（比較対象）：

| 題名 | 著者・会場・年 | 要点 | 確認度 | URL |
|---|---|---|---|---|
| RoboCritics: Enabling Reliable End-to-End LLM Robot Programming through Expert-Informed Critics | Wisconsin 大（著者全員は未検証）. HRI 2026 | OK / Warning / Error と Fix ボタン、18 名 | 本文 | [arXiv](https://arxiv.org/html/2603.06842v1) |
| VeriPlan: Integrating Formal Verification and LLMs into End-User Planning | Lee, Porfirio, Wang, Zhao, Mutlu. CHI 2025 | ルール翻訳器・スライダ・モデル検査器、12 名 | 本文 | [arXiv](https://arxiv.org/html/2502.17898v1) |
| U-Define: Designing User Workflows for Hard and Soft Constraints in LLM-Based Planning | Lee, Wang, Albarghouthi, Porfirio, Mutlu. arXiv 2026 | hard は形式検査、soft は LLM 判定 | 要旨 | [arXiv](https://arxiv.org/abs/2605.02765) |
| ImageInThat: Manipulating Images to Convey User Instructions to Robots | Mahadevan, Lewis, Li, Mutlu, Tang, Grossman. HRI 2025 | 2D 画像でゴール状態を作る、10 名 | 要旨 | [arXiv](https://arxiv.org/abs/2503.15500) |
| HRI Grounding: Evidence That Operators Authorize and Correct AI Multi-Robot Plans Through a Generated Supervisory Interface | Yu, Nair, Song, Soh. RA-L 2026 | d′ = 2.90、96 中 85 を回復 | 要旨 | [DOI](https://doi.org/10.1109/LRA.2026.3730218) |
| Goal-Oriented End-User Programming of Robots（Polaris） | Porfirio, Roberts, Hiatt. HRI 2024 | 地図に重ねた計画。衝突ゴールは黙って除外 | 本文 | [arXiv](https://arxiv.org/html/2403.13988v1) |
| Sketching Robot Programs On the Fly（Tabula） | Porfirio, Stegner, Cakmak, Sauppé, Albarghouthi, Mutlu. HRI 2023 | 音声＋地図スケッチ。フィードバック不足を著者が明記 | 本文 | [ar5iv](https://ar5iv.arxiv.org/html/2302.03088) |
| Understanding On-the-Fly End-User Robot Programming | Stegner, Hwang, Porfirio, Mutlu. DIS 2024 | Tabula の続報 | 未検証 | [DOI](https://doi.org/10.1145/3643834.3660721) |
| Alchemist: LLM-Aided End-User Development of Robot Applications | Karli, Chen, Antony, Huang. HRI 2024 | LLM がコード生成、画面とシミュレーションで確認 | 未検証 | [DOI](https://doi.org/10.1145/3610977.3634969) |
| Cocobo: Exploring Large Language Models as the Engine for End-User Robot Programming | Ge, Dai, Shan, Li, Hu, Sun. VL/HCC 2024 | 自然言語とフローチャートの往復 | 未検証 | [arXiv](https://arxiv.org/abs/2407.20712) |
| Vocal Sandbox: Continual Learning and Adaptation for Situated Human-Robot Collaboration | Grannen, Karamcheti, Mirchandani, Liang, Sadigh. CoRL 2024 | 画面 GUI に計画・解釈を表示 | 未検証 | [arXiv](https://arxiv.org/abs/2411.02599) |
| CoFrame: A System for Training Novice Cobot Programmers | Schoen, White, Henrichs, Siebert-Evenstone, Shaffer, Mutlu. HRI 2022 | 3D シミュレーション上で問題点を返す | 未検証 | [DOI](https://doi.org/10.1109/HRI53351.2022.9889345) |
| VoicePilot: Harnessing LLMs as Speech Interfaces for Physically Assistive Robots | Padmanabha, Yuan, Gupta, Karachiwalla, Majidi, Admoni ほか. UIST 2024 | 視覚プレビューなしの対照例 | 未検証 | [arXiv](https://arxiv.org/abs/2404.04066) |
| Understanding Large-Language Model (LLM)-powered Human-Robot Interaction | Kim, Lee, Mutlu. HRI 2024 | 背景文献 | 未検証 | [arXiv](https://arxiv.org/abs/2401.03217) |
| Text2Motion: From Natural Language Instructions to Feasible Plans | Lin, Agia, Migimatsu, Pavone, Bohg. Autonomous Robots 2023 | 幾何的実行可能性を検証した計画 | 未検証 | [arXiv](https://arxiv.org/abs/2303.12153) |
| LATTE: LAnguage Trajectory TransformEr | Bucker, Figueredo, Haddadin, Kapoor, Ma, Vemprala ほか. arXiv 2022 | 言語で軌道を修正 | 未検証 | [arXiv](https://arxiv.org/abs/2208.02918) |
| Code3 | Huang, Cakmak. HRI 2017 | 移動マニピュレータ向け EUP | 未検証 | [DOI](https://doi.org/10.1145/2909824.3020215) |
| A Human-in-the-loop Approach to Robot Action Replanning through LLM Common-Sense Reasoning | 著者未確認. arXiv 2025 | 自然言語で計画を見直す | 要旨 | [arXiv](https://arxiv.org/abs/2507.20870) |
| Bootstrapping Human-Like Planning via LLMs | Porfirio, Hsiao, Fine-Morris, Smith, Hiatt. RO-MAN 2025 | ドラッグ&ドロップと自然言語の統合 | 要旨 | [arXiv](https://arxiv.org/abs/2506.22604) |
| A digital twin-enabled environment for end-user development of robot tasks | Gargioni, Fogli, Nava. Intelligent Service Robotics 2026 | 題名のみ | 未検証 | [DOI](https://doi.org/10.1007/s11370-026-00758-7) |
| SHRIMP | UIST 2026 | 計画の反復改良 | 未検証 | [arXiv](https://arxiv.org/abs/2608.08884) |

## 付録 B：AR エンドユーザロボットプログラミングと意図・状態の可視化（PRogramAR・RoboVisAR の類似研究）

| 題名 | 著者・会場・年 | 要点 | 確認度 | URL |
|---|---|---|---|---|
| PRogramAR: Augmented Reality End-User Robot Programming | Ikeda, Szafir. THRI 2024 | AR × TAP。ルールの真偽を緑／赤、計画不能はロボット頭上にエラー文 | 全文 | [DOI](https://doi.org/10.1145/3640008) |
| RoboVisAR: Immersive Authoring of Condition-based AR Robot Visualisations | R. S. Lunding, M. S. Lunding, Feuchtner, Petersen, Grønbæk, Suzuki. HRI 2024 | 記録→タイムラインで設計→再生。6 可視化・4 条件。タイムラインは可視化の有効区間のみ表示、エラーの仕組みなし | 全文 | [DOI](https://doi.org/10.1145/3610977.3634972) |
| ARTHUR: Authoring Human-Robot Collaboration Processes with Augmented Reality using Hybrid User Interfaces | Lunding, Hubenschmid, Feuchtner, Grønbæk. Virtual Reality 2025 | feedback 20・action 10・condition 18。失敗処理の記述なし | 本文 | [arXiv](https://arxiv.org/html/2501.02304v1) |
| GhostAR: A Time-space Editor for Embodied Authoring of Human-Robot Collaborative Task with Augmented Reality | Cao, Wang, Qian, Rao, Wadhawan, Huo, Ramani. UIST 2019 | 人のゴーストを相手に時空間編集 | 要旨 | [DOI](https://doi.org/10.1145/3332165.3347902) |
| V.Ra: An In-Situ Visual Authoring System for Robot-IoT Task Planning with Augmented Reality | Cao, Xu, Li, Zhong, Huo, Ramani. DIS 2019 | 手持ち AR で経路と IoT タスク列 | 未検証 | [DOI](https://doi.org/10.1145/3322276.3322278) |
| Situated Live Programming for Human-Robot Collaboration | Senft, Hagenow, Radwin, Zinn, Gleicher, Mutlu. UIST 2021 | カメラ映像上の TAP。ルール優先度の衝突を利用者に直させる（PRogramAR 全文の記述） | 未検証 | [DOI](https://doi.org/10.1145/3472749.3474773) |
| Trigger-Action Programming for Personalising Humanoid Robot Behaviour | Leonardi, Manca, Paternò, Santoro. CHI 2019 | ロボット向け TAP の基礎（非 AR） | 未検証 | [DOI](https://doi.org/10.1145/3290605.3300675) |
| Robot Programming Through Augmented Trajectories in Augmented Reality | Quintero, Li, Pan, Chan, Van der Loos, Croft. IROS 2018 | 軌道の作成・プレビュー・編集 | 未検証 | [DOI](https://doi.org/10.1109/iros.2018.8593700) |
| End-User Robot Programming Using Mixed Reality | Gadre, Rosen, Chien, Phillips, Tellex, Konidaris. ICRA 2019 | ウェイポイントとゴーストアーム | 未検証 | [DOI](https://doi.org/10.1109/icra.2019.8793988) |
| Interactive Robot Programing Using Mixed Reality | Ostanin, Klimchik. IFAC-PapersOnLine 2018 | ホログラムでシミュレーション後に実行 | 未検証 | [DOI](https://doi.org/10.1016/j.ifacol.2018.11.517) |
| Human-robot interaction for robotic manipulator programming in Mixed Reality | Ostanin, Mikhel, Evlampiev, Skvortsova, Klimchik. ICRA 2020 | 上の発展 | 未検証 | [DOI](https://doi.org/10.1109/ICRA40945.2020.9196965) |
| Spatial programming for industrial robots based on gestures and Augmented Reality | Lambrecht, Krüger. IROS 2012 | ジェスチャ＋手持ち AR | 未検証 | [DOI](https://doi.org/10.1109/IROS.2012.6385900) |
| Augmented reality-assisted robot programming system for industrial applications | Ong, Yew, Thanigaivel, Nee. RCIM 2020 | ポインタ＋AR で経路、仮想ロボットで検証 | 未検証 | [DOI](https://doi.org/10.1016/j.rcim.2019.101820) |
| An Augmented Reality Interface for Human-Robot Interaction in Unconstrained Environments | Chacko, Kapila. IROS 2019 | スマホ AR でピック&プレース位置を指定 | 未検証 | [DOI](https://doi.org/10.1109/IROS40897.2019.8967973) |
| Toward Programming a Collaborative Robot by Interacting with Its Digital Twin in a Mixed Reality Environment | Rivera-Pinto, Kildal, Lazkano. IJHCI 2023 | デジタルツインを手で動かす | 未検証 | [DOI](https://doi.org/10.1080/10447318.2023.2221599) |
| Online and Offline Robot Programming via Augmented Reality Workspaces | Thoo, Maceiras, Abbet, Racca, Girgin, Calinon. arXiv 2021 | 仮想ワークスペースでの教示 | 未検証 | [arXiv](https://arxiv.org/abs/2107.01884) |
| Kinetic AR: A Framework for Robotic Motion Systems in Spatial Computing | Fuste, Reynolds, Hobin, Heun. CHI EA 2020 | 手持ち AR で動作経路 | 未検証 | [DOI](https://doi.org/10.1145/3334480.3382814) |
| Enabling Human Robot Interaction in flexible robotic assembly lines: an Augmented Reality based software suite | Kousi, Stoubos, Gkournelos, Michalos, Makris. Procedia CIRP 2019 | 軌道・安全領域の表示と修正 | 未検証 | [DOI](https://doi.org/10.1016/j.procir.2019.04.328) |
| MRREP: Mixed Reality-Based Hand-Drawn Reference Path Editing Interface for Mobile Robot Navigation | Taki, Kobayashi, Uranishi. RO-MAN 2026 | 題名のみ | 未検証 | [DOI](https://doi.org/10.1109/RO-MAN72286.2026.11714993) |
| MRHaD: Mixed Reality-based Hand-Drawn Map Editing Interface for Mobile Robot Navigation | Taki, Kobayashi, Iglesius, Chiba, Shirai, Uranishi. RO-MAN 2025 | 題名のみ | 未検証 | [DOI](https://doi.org/10.1109/RO-MAN63969.2025.11217635) |
| Intuitive Robot Path Planning through Augmented Reality | Matour, Winkler. MMAR 2023 | 題名のみ | 未検証 | [DOI](https://doi.org/10.1109/MMAR58394.2023.10242522) |
| Augmented Reality for 6-DoF Motion Recording, Preview, and Execution to Enable Intuitive Surgical Robot Control | Karnam, Żelechowski, Cattin ほか. 2022 | 題名のみ | 未検証 | [DOI](https://doi.org/10.1515/cdbme-2022-1058) |
| Spatially Situated End-User Robot Programming in Augmented Reality | Kapinus, Beran, Materna, Bambusek. RO-MAN 2019 | 3D 空間にアクションポイントとフロー | 未検証 | [DOI](https://doi.org/10.1109/RO-MAN46459.2019.8956336) |
| Augmented reality spatial programming paradigm applied to end-user robot programming | Kapinus, Beran, Materna, Bambušek. RCIM 2024 | 上のジャーナル版 | 未検証 | [DOI](https://doi.org/10.1016/j.rcim.2024.102770) |
| ARCOR2: Framework for Collaborative End-User Management of Industrial Robotic Workplaces using Augmented Reality | Kapinus, Materna, Bambušek, Beran, Smrž. arXiv 2023 | 基盤フレームワーク | 未検証 | [arXiv](https://arxiv.org/abs/2306.08464) |
| Interactive Spatial Augmented Reality in Collaborative Robot Programming: User Experience Evaluation | Materna, Kapinus, Beran, Smrz, Zemcik. RO-MAN 2018 | 投影 AR＋タッチ | 未検証 | [DOI](https://doi.org/10.1109/ROMAN.2018.8525662) |
| Combining Interactive Spatial Augmented Reality with Head-Mounted Display for End-User Collaborative Robot Programming | Bambušek ほか. RO-MAN 2019 | 投影＋HMD | 未検証 | [DOI](https://doi.org/10.1109/RO-MAN46459.2019.8956315) |
| PATI: a projection-based augmented table-top interface for robot programming | Gao, Huang. IUI 2019 | 卓上投影＋タッチ | 未検証 | [DOI](https://doi.org/10.1145/3301275.3302326) |
| Simplifying Robot Programming Using Augmented Reality and End-User Development | Yigitbas, Jovanovikj, Engels. INTERACT 2021 | 手持ち AR＋ブロック型 | 未検証 | [DOI](https://doi.org/10.1007/978-3-030-85623-6_36) |
| ARC-LfD: Using Augmented Reality for Interactive Long-Term Robot Skill Maintenance via Constrained Learning from Demonstration | Luebbers, Brooks, Mueller, Szafir, Hayes. ICRA 2021 | キーフレームと制約を AR で可視化・編集 | 未検証 | [DOI](https://doi.org/10.1109/ICRA48506.2021.9561844) |
| RAMPA: Robotic Augmented Reality for Machine Programming by DemonstrAtion | Dogangun, Bahar, Yildirim, Temir, Ugur, Dogan. RA-L 2025 | AR 上の PbD | 未検証 | [arXiv](https://arxiv.org/abs/2410.13412) |
| REACTR: A Responsive Environment for Authoring Code and Testing Robots | Ikeda, Szafir. RO-MAN 2026 | コードと挙動の可視化を同期 | 要旨 | [DOI](https://doi.org/10.1109/RO-MAN72286.2026.11714554) |
| Delegate the Details: Flexible Assembly Constraint Authoring for Collaborative XR | Yang, He, Zou, Liu, Tversky, Feiner. ISMAR 2026 | 制約の指定に幅を持たせる | 要旨 | [DOI](https://doi.org/10.1109/ISMAR70079.2026.00083) |
| ERUPT: An Open Toolkit for Interfacing with Robot Motion Planners in Extended Reality | Ngui, McBeth ほか. arXiv 2025 | XR から動作計画器を使う | 要旨 | [arXiv](https://arxiv.org/abs/2510.02464) |
| ROS2MR: Connecting ROS 2 Motion Planning to Mixed-Reality Trajectory Visualization | Berrezueta-Guzman, Khalil, Koshelev, Wagner. arXiv 2026 | MoveIt 軌道を MR 再生用に変換 | 要旨 | [arXiv](https://arxiv.org/abs/2611.11830) |
| Communicating Robot Motion Intent with Augmented Reality | Walker, Hedayati, Lee, Szafir. HRI 2018 | 飛行ロボットの経路を AR で予告 | 要旨 | [DOI](https://doi.org/10.1145/3171221.3171253) |
| Communicating and controlling robot arm motion intent through mixed-reality head-mounted displays | Rosen, Whitney, Phillips, Chien, Tompkin, Konidaris, Tellex. IJRR 2019 | 軌道を重ね、衝突は人が判定。32 名 | 要旨 | [DOI](https://doi.org/10.1177/0278364919842925) |
| Robot Teleoperation with Augmented Reality Virtual Surrogates | Walker, Hedayati, Szafir. HRI 2019 | 仮想サロゲートを操作し実機が後追い | 未検証 | [DOI](https://doi.org/10.1109/hri.2019.8673306) |
| Mind the ARm: realtime visualization of robot motion intent in head-mounted augmented reality | Gruenefeld, Prädel, Illing, Stratmann, Drolshagen, Pfingsthorn. MuC 2020 | 経路・プレビュー・ボリュームを比較 | 未検証 | [DOI](https://doi.org/10.1145/3404983.3405509) |
| Projection-Aware Task Planning and Execution for Human-in-the-Loop Operation of Robots in a Mixed-Reality Workspace | Chakraborti, Sreedharan, Kulkarni, Kambhampati. IROS 2018 | 意図の投影を計画に組み込む | 未検証 | [DOI](https://doi.org/10.1109/iros.2018.8593830) |
| Projecting robot intentions into human environments | Andersen, Madsen, Moeslund, Ben Amor. RO-MAN 2016 | プロジェクタで意図を投影 | 未検証 | [DOI](https://doi.org/10.1109/roman.2016.7745145) |
| Interactive Robot Knowledge Patching Using Augmented Reality | Liu, Zhang, Si, Xie, Zhu, Zhu. ICRA 2018 | タスク知識を可視化し修正 | 未検証 | [DOI](https://doi.org/10.1109/icra.2018.8462837) |
| Transparent Robot Behavior Using Augmented Reality in Close Human-Robot Interaction | Bolano, Juelg, Roennau, Dillmann. RO-MAN 2019 | 計画動作と衝突予測を AR で | 未検証 | [DOI](https://doi.org/10.1109/ro-man46459.2019.8956296) |
| AR-supported Human-Robot Collaboration: Facilitating Workspace Awareness and Parallelized Assembly Tasks | Lunding, Lystbæk, Feuchtner, Grønbæk. ISMAR 2023 | 作業領域・次動作を AR 提示 | 未検証 | [DOI](https://doi.org/10.1109/ISMAR59233.2023.00123) |
| Investigating AR Assistance for Human-Robot Collaboration in Mould Assembly "in the Wild" | Lunding, Feuchtner, Grønbæk. HRI 2025 | 現場評価 | 未検証 | [DOI](https://doi.org/10.1109/HRI61500.2025.10973920) |
| RCLL-AR: Augmented Reality Support for Understanding Autonomous Processes in the RoboCup Logistics League | Tscherko, Kohout, Fleck, Tschesche, Ferrein, Steinbauer-Wagner, Plopski. ISMAR 2025 | 自律ロボット群の進行と今後の動き | 要旨 | [DOI](https://doi.org/10.1109/ISMAR67309.2025.00045) |
| Communicating via Augmented Reality for Human-Robot Teaming in Field Environments | Reardon, Lee, Rogers, Fink. SSRR 2019 | 屋外で計画・探索情報を共有 | 未検証 | [DOI](https://doi.org/10.1109/SSRR.2019.8848971) |
| Learning Visualization Policies of Augmented Reality for Human-Robot Collaboration | 著者未検証. arXiv 2022 | 可視化方策の学習 | 未検証 | [arXiv](https://arxiv.org/abs/2211.07028) |
| Making robots understandable: Augmented reality for enhancing situational awareness in human–robot co-located environments | Chacko, Kapila. Empathic Computing 2026 | 題名のみ | 未検証 | [DOI](https://doi.org/10.70401/ec.2026.0016) |
| Task-Based Analysis of Augmented Reality in Collaborative Robotic Programming for Manufacturing Assembly | Kamran, Shrestha, Nguyen. HRI 2026 Companion | 題名のみ | 未検証 | [DOI](https://doi.org/10.1145/3776734.3794344) |
| Evaluating Digital Twin Visualisations for Safety and Trust in Robot-Assisted Dressing | Cogurcu ほか. THRI 2026 | BB と軌道表示を比較、N=36 | 要旨 | [DOI](https://doi.org/10.1145/3805805) |
| From Planning to Verification: Designing Interactions for Multi-Drone Search and Rescue Operations in Mixed Reality | Latarche, Jouffrais, Garcia. NordiCHI 2026 | 計画・監督・操縦の遷移 | 要旨 | [DOI](https://doi.org/10.1145/3829807.3829828) |
| Visualizing Motion Intent in Heterogeneous Multi-Robot Environments | Riechmann-Thom, Rexilius. ISMAR-Adjunct 2025 | 混在環境での意図可視化 | 要旨 | [DOI](https://doi.org/10.1109/ISMAR-Adjunct68609.2025.00145) |
| Mirror Skin: In Situ Visualization of Robot Touch Intent on Robot Skin | Wagmann, Krüger, Wang, Gienger, Steimle. UIST 2025 | 接触意図をロボット表面に | 要旨 | [arXiv](https://arxiv.org/abs/2512.11472) |
| Designing Intent Communication for Agent-Human Collaboration | Li, Chiossi ほか. MUM 2025 | 「何を」と「どう・いつ」の接続 | 要旨 | [arXiv](https://arxiv.org/abs/2510.20409) |
| ARTOO-DARTU: Studying AR-HRC With AR Obstruction Mitigation During a Warehouse Task | Fronk, Ye, Qu, Gorlatova. arXiv 2026 | AR が実物を隠す副作用、N=34 | 要旨 | [arXiv](https://arxiv.org/abs/2606.25202) |
| Context-Aware Augmented Reality for Human-Robot Collaboration | Davari, Ajikumar, Moghaddam. ISMAR-Adjunct 2025 | 文脈適応型 AR | 要旨 | [DOI](https://doi.org/10.1109/ISMAR-Adjunct68609.2025.00087) |
| HORUS: A Mixed Reality Interface for Managing Teams of Mobile Robots | Adekoya, Sgorbissa, Recchiuto. UR 2026 | 複数移動ロボットの MR 管理 | 要旨 | [arXiv](https://arxiv.org/abs/2506.02622) |
| Better Situational Awareness in AR-HRC? | Qu ら. arXiv 2026 | AR とモバイル UI を同等情報で比較、N=30 | 要旨 | [arXiv](https://arxiv.org/abs/2609.01461) |
| Previewed Reality（ROBOMEC 講演） | Horikawa, Egashira, Nakashima, Kawamura, Kurazume. IROS 2017 ほか | 数秒先の動作を AR で重ねる | 未検証 | [PDF](https://robotics.ait.kyushu-u.ac.jp/kurazume/papers/ROBOMEC17-1.pdf) |
| Motion preview of a humanoid robot by shadow projection | Miyasaka, Matsumoto. Artificial Life and Robotics 2026 | 題名のみ | 未検証 | [DOI](https://doi.org/10.1007/s10015-026-01143-4) |
| Evaluating the Impact of Adaptive Extended Reality on Human-Robot Interaction Across the Reality-Virtuality Continuum | Tornberg, Torck, El Hafi, Taniguchi. arXiv 2026 | XR モダリティを固定せず比較 | 要旨 | [arXiv](https://arxiv.org/abs/2609.31138) |
| Roboshop: multi-layered sketching interface for robot housework assignment and management | Liu, Sakamoto, Inami, Igarashi. CHI 2011 | 家事の割当と管理（書誌のみ） | 未検証 | [DOI](https://doi.org/10.1145/1978942.1979035) |
| Cooking with robots: designing a household system working in open environments | Sugiura, Sakamoto, Withana, Inami, Igarashi. CHI 2010 | 書誌のみ | 未検証 | [DOI](https://doi.org/10.1145/1753326.1753693) |
| Magic cards: a paper tag interface for implicit robot control | Zhao, Nakamura, Ishii, Igarashi. CHI 2009 | 書誌のみ | 未検証 | [DOI](https://doi.org/10.1145/1518701.1518730) |
| Graphical instruction for a garment folding robot | Sugiura, Igarashi, Takahashi, Gowon, Fernando, Sugimoto, Inami. SIGGRAPH 2009 ET | 書誌のみ | 未検証 | [DOI](https://doi.org/10.1145/1597956.1597968) |

## 付録 C：シーケンス可視化・デバッグ・失敗の説明（論点 1）

| 題名 | 著者・会場・年 | 要点 | 確認度 | URL |
|---|---|---|---|---|
| Advancing the Design of Visual Debugging Tools for Roboticists | Ikeda, Szafir. HRI 2022 | RViz・2D・AR を 24 名で比較。33% が事前の下見と過去の見直しを要望 | 本文 | [PDF](https://par.nsf.gov/servlets/purl/10354657) |
| An Augmented Reality Debugging System for Mobile Robot Software Engineers | Collett, MacDonald. JOSER 2010 | 固定カメラ映像に 2D 注釈 | 要旨 | [PDF](https://aisberg.unibg.it/bitstream/10446/86156/1/7-143-1-PB.pdf) |
| ARDebug: An Augmented Reality Tool for Analysing and Debugging Swarm Robotic Systems | Millard ほか. Frontiers in Robotics and AI 2018 | 群ロボットの内部状態 | 要旨 | [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC7805932/) |
| ARviz – An Augmented Reality-enabled Visualization Platform for ROS Applications | Hoang ほか. arXiv 2021 | ROS メッセージを AR 表示 | 要旨 | [arXiv](https://arxiv.org/abs/2110.15521) |
| Mixed-Reality Robot Behavior Replay: A System Implementation | Han, Williams, Yanco. AAAI FSS 2022 | BT 単位の再生と投影 | 本文 | [ar5iv](https://ar5iv.labs.arxiv.org/html/2210.00075) |
| Replayable Augmented Reality Visualization for Robot Fault Diagnosis: A Comparative Study | Richards, Ku, Calvert, Migdal, Hebert, Croft, Cosgun. IJSR 2025 | 故障前 15 秒の再生。タブレットが AR より好まれた、N=24 | 要旨 | [DOI](https://doi.org/10.1007/s12369-025-01219-4) |
| KITE: Keyframe-Indexed Tokenized Evidence for VLM-Based Robot Failure Analysis | Hosseinzadeh, Wong, Dayoub. ICRA 2026 | キーフレーム＋配置図＋時刻 | 要旨 | [arXiv](https://arxiv.org/abs/2604.07034) |
| ABOD3-AR（正式題名未確認） | Rotsidis, Theodorou ほか | 行動計画の木をロボットに重ねる | 未検証 | [CEUR](https://ceur-ws.org/Vol-2327/IUI19WS-IUIATEC-3.pdf) |
| Authoring and Verifying Human-Robot Interactions（RoVer） | Porfirio, Sauppé, Albarghouthi, Mutlu. UIST 2018 | モデル検査、違反を文の一覧で | 本文 | [PDF](https://par.nsf.gov/servlets/purl/10080246) |
| Figaro: A Tabletop Authoring Environment for Human-Robot Interaction | Porfirio, Stegner, Cakmak, Sauppé, Albarghouthi, Mutlu. CHI 2021 | 机上投影と人形。矛盾は扱えず | 本文 | [PDF](https://par.nsf.gov/servlets/purl/10210854) |
| Designing User-Centric Programming Aids for Kinesthetic Teaching of Collaborative Robots（Demoshop） | Ajaykumar, Stiber, Huang. 掲載誌は未検証 | 経由点の列、危険操作に警告表示 | 本文の一部 | [PDF](https://gopikaajaykumar.github.io/ajaykumar2021designing.pdf) |
| Reactive or Proactive? How Robots Should Explain Failures | LeMasurier, Gautam, Han, Crandall, Yanco. HRI 2024 | 先回りの説明が高評価、N=224 | 本文 | [PDF](https://faculty.cs.byu.edu/~crandall/papers/LeMasurier_etal_HRI2024.pdf) |
| Explainable AI for Robot Failures: Generating Explanations that Improve User Assistance in Fault Recovery | Das, Banerjee, Chernova. HRI 2021 | 文脈＋行動履歴の説明が効く | 要旨 | [arXiv](https://arxiv.org/abs/2101.01625) |
| Why Did I Fail? A Causal-Based Method to Find Explanations for Robot Failures | Diehl, Ramirez-Amaro. RA-L 2022 | 対比的説明 | 要旨 | [arXiv](https://arxiv.org/abs/2204.04483) |
| REFLECT: Summarizing Robot Experiences for Failure Explanation and Correction | Liu, Bahety, Song. CoRL 2023 | 階層的要約と LLM による説明 | 未検証 | [arXiv](https://arxiv.org/abs/2306.15724) |
| AHA: A Vision-Language-Model for Detecting and Reasoning over Failures in Robotic Manipulation | ICLR 2025 | 失敗の検出と理由づけ | 未検証 | [arXiv](https://arxiv.org/abs/2410.00371) |
| Generating Environment-based Explanations of Motion Planner Failure | ICRA 2024 | 原因の物と動かす先 | 未検証 | [DOI](https://doi.org/10.1109/icra57147.2024.10611577) |
| Multimodal Coherent Explanation Generation of Robot Failures | Pramanick, Rossi. IROS 2024 | モダリティ間で整合した説明 | 未検証 | [arXiv](https://arxiv.org/abs/2410.00659) |
| Immersive Explainability: Visualizing Robot Navigation Decisions through XAI Semantic Scene Projections in Virtual Reality | de Heuvel, Müller, Wessels, Akhtar, Bauckhage, Bennewitz. arXiv 2025 | 寄与度を物の強調として VR に、24 名 | 要旨 | [arXiv](https://arxiv.org/abs/2504.00682) |
| Correct Robots Before They Make Mistakes（PHIL） | Jiang ほか. arXiv 2026 | 方策の数秒先を XR で下見し介入 | 要旨 | [arXiv](https://arxiv.org/abs/2611.05667) |
| AR-based Interaction for Safe Human-Robot Collaborative Manufacturing | Hietanen, Latokartano, Pieters, Lanz, Kämäräinen. arXiv 2019 | 赤い仮想の柵、作業時間 21〜24% 減 | 本文 | [ar5iv](https://ar5iv.labs.arxiv.org/html/1909.02933) |
| HoloLens 2 による安全ゾーン可視化（題名未確認） | Cogurcu ほか | 赤いゾーンと侵入警告 | 未検証 | [PDF](https://eprints.whiterose.ac.uk/174782/1/Edited___UK_RAS_conference_latex_template_10_17_19_Yunus_Cogurcu.pdf) |
| Mixed Reality Outperforms Virtual Reality for Remote Error Resolution in Pick-and-Place Tasks | Kumar, Simangunsong, Carreno-Medrano, Cosgun. HRI 2025 | 停止後の遠隔解消で MR が優位、N=21 | 要旨 | [arXiv](https://arxiv.org/abs/2502.06141) |
| Interaction-aware augmented reality interface for assisting erring social robots | Hosoda, Brščić, Kanda. JMUI 2025 | 誤る接客ロボットを AR HMD で監督 | 要旨 | [DOI](https://doi.org/10.1007/s12193-025-00453-4) |
| Visual Explanation With Action Query Transformer in Deep Reinforcement Learning and Visual Feedback via Augmented Reality | Itaya, Yin, Hirakawa, Yamashita, Fujiyoshi, Sugiura. IEEE Access 2025 | 行動根拠を AR で | 要旨 | [DOI](https://doi.org/10.1109/ACCESS.2025.3554493) |
| Robots That Ask For Help（KnowNo） | Ren, Dixit, Bodrova, Singh, Tu, Brown, Xu ほか. CoRL 2023 | 候補が複数残れば尋ねる | 要旨 | [arXiv](https://arxiv.org/abs/2307.01928) |
| Introspective Planning: Aligning Robots' Uncertainty with Inherent Task Ambiguity | Liang, Zhang, Fisac. arXiv 2024 | 不確かなときに確認 | 要旨 | [arXiv](https://arxiv.org/html/2402.06529v2) |
| CLARA: Classifying and Disambiguating User Commands for Reliable Interactive Robotic Agents | Park, Lim, Lee, Park, Chang, Yu, Choi. RA-L 2024 | certain / ambiguous / infeasible | 未検証 | [DOI](https://doi.org/10.1109/lra.2023.3338514) |
| Robot-Assisted Decision-Making: Unveiling the Role of Uncertainty Visualisation and Embodiment | Schömbs, Pareek, Goncalves, Johal. CHI 2024 | 不確実性の可視化と意思決定 | 要旨 | [DOI](https://doi.org/10.1145/3613904.3642911) |
| Uncertain Pointer: Situated Feedforward Visualizations for Ambiguity-Aware AR Target Selection | Tsai, Tacconi, Wilson, Abtahi. CHI 2026 | 候補の注釈と不確実性の視覚語彙 | 要旨 | [arXiv](https://arxiv.org/abs/2602.13433) |
| Helping Users Debug Trigger-Action Programs | Zhang, Zhou, Littman, Ur, Lu. IMWUT 2022 | タイムラインに印、修正の「もしも」再生、30 名 | 本文 | [PDF](https://par.nsf.gov/servlets/purl/10387467) |
| AutoTap: Synthesizing and Repairing Trigger-Action Programs Using LTL Properties | Zhang, He, Martinez, Brackenbury, Lu, Ur. ICSE 2019 | 性質から自動修復 | 要旨 | [DOI](https://doi.org/10.1109/icse.2019.00043) |
| Trace2TAP: Synthesizing Trigger-Action Programs from Traces of Behavior | Zhang ほか. IMWUT 2020 | 履歴からルール合成 | 未検証 | [Crossref](https://api.crossref.org/works/10.1145%2F3411838) |
| How Users Interpret Bugs in Trigger-Action Programming | Brackenbury, Deora, Ritchey, Vallee, He, Wang, Littman ほか. CHI 2019 | TAP のバグの分類 | 未検証 | [DOI](https://doi.org/10.1145/3290605.3300782) |
| Empowering End Users in Debugging Trigger-Action Rules（EUDebug） | Corno, De Russis, Monge Roffarello. CHI 2019 | 作成中に問題を警告、15 名 | 要旨 | [DOI](https://doi.org/10.1145/3290605.3300618) |
| Supporting end-user debugging of trigger-action rules for IoT applications | Manca, Paternò, Santoro, Corcella. IJHCS 2019 | なぜ／なぜ〜しないのデバッグ | 要旨 | [DOI](https://doi.org/10.1016/j.ijhcs.2018.11.005) |
| Process Mining Meets Visual Analytics: The Case of Conformance Checking | Rehse, Pufahl ほか. arXiv 2022 | 適合性検査の可視化は手薄 | 要旨 | [arXiv](https://arxiv.org/abs/2209.09712) |
| CC Viz（ICPM 2025 デモ） | 著者未確認 | 工程図を逸脱の度合いで塗る | 要旨 | [CEUR](https://ceur-ws.org/Vol-4088/paper_241.pdf) |
| A Task Taxonomy for Conformance Checking | arXiv 2025 | 可視化評価の課題分類 | 要旨 | [arXiv](https://arxiv.org/html/2507.11976v1) |
| Augmented Assembly: Object Recognition and Hand Tracking for Adaptive Assembly Instructions in Augmented Reality | Kyaw, Ma, Zivkovic, Sabin. arXiv 2026 | 部品の現在・目標位置の枠＋手順 | 要旨 | [arXiv](https://arxiv.org/abs/2601.11535) |
| Error Management for Augmented Reality Assembly Instructions | 著者未検証. IEEE | 誤りの警告と直し方の図示 | 未検証 | [IEEE Xplore](https://ieeexplore.ieee.org/document/10765434) |
| デジタルツイン重ね描きの比較（VINCI 2025、題名未確認） | 著者未確認 | 検査は輪郭線、向きの誤りは半透明が効く | 未検証 | [PDF](https://documentserver.uhasselt.be/bitstream/1942/48158/1/vinci_2025_paper.pdf) |

## 付録 D：Before/After・Diminished Reality・ゴール状態の提示（論点 2）

| 題名 | 著者・会場・年 | 要点 | 確認度 | URL |
|---|---|---|---|---|
| Reality Promises: Virtual-Physical Decoupling Illusions in Mixed Reality via Invisible Mobile Robots | Kari, Abtahi. UIST 2025 | ロボットを消す。**removal mode では実物体も消し仮想コピーを動かす**。目的は錯覚、ユーザー評価なし | 全文 | [DOI](https://doi.org/10.1145/3746059.3747660) |
| Explainable OOHRI: Communicating Robot Capabilities and Limitations as Augmented Reality Affordances | Wang, Kari, Abtahi. HRI 2026 | 仮想ツインの直接操作。実物は消さない（"diminish" 0 件）。P6 が実物のグレーアウトを要望 | 全文 | [DOI](https://doi.org/10.1145/3757279.3785569) |
| GhostObjects: Instructing Robots by Manipulating Spatially Aligned Virtual Twins in Augmented Reality | Wang, Abtahi. UIST Adjunct 2025 | 仮想ツインでゴール指定 | 要旨 | [arXiv](https://arxiv.org/abs/2508.11022) |
| Scene Responsiveness for Visuotactile Illusions in Mixed Reality | Kari, Schütte, Sodhi. UIST 2023 | 実物を消して仮想コピーを動かす、ロボットなし | 未検証 | [DOI](https://doi.org/10.1145/3586183.3606825) |
| TransforMR: Pose-Aware Object Substitution for Composing Alternate Mixed Realities | Kari ほか. ISMAR 2021 | 実世界の人・車を仮想に置換 | 未検証 | [DOI](https://doi.org/10.1109/ismar52148.2021.00021) |
| SceneCtrl: Mixed Reality Enhancement via Efficient Scene Editing | Yue, Yang, Ren, Wang. UIST 2017 | 実物の削除・移動・複製 | 未検証 | [DOI](https://doi.org/10.1145/3126594.3126601) |
| Remixed Reality: Manipulating Space and Time in Augmented Reality | Lindlbauer, Wilson. CHI 2018 | 空間・時間の操作 | 未検証 | [DOI](https://doi.org/10.1145/3173574.3173703) |
| Annexing Reality | Hettiarachchi, Wigdor. CHI 2016 | 実物に仮想物体を重ねる | 未検証 | [DOI](https://doi.org/10.1145/2858036.2858134) |
| Causality-preserving Asynchronous Reality | Fender, Holz. CHI 2022 | 過去の出来事を後から再生 | 未検証 | [DOI](https://doi.org/10.1145/3491102.3501836) |
| Diminished Reality for Close Quarters Robotic Telemanipulation | Taylor, Matsumoto, Carter, Plopski, Admoni. IROS 2020 | ロボットを透明化。効率・選好に欠点 | 要旨 | [DOI](https://doi.org/10.1109/iros45743.2020.9341536) |
| InvisibleRobot: Facilitating Robot Manipulation Through Diminished Reality | Plopski, Taylor, Carter, Admoni. ISMAR-Adjunct 2019 | 完全除去と輪郭残しの 2 モード | 要旨 | [DOI](https://doi.org/10.1109/ismar-adjunct.2019.00-55) |
| Time Follower's Vision: a teleoperation interface with past images | Sugimoto, Kagotani, Nii, Shiroma, Matsuno, Inami. IEEE CG&A 2005 | 過去画像＋現在のロボット CG | 未検証 | [DOI](https://doi.org/10.1109/mcg.2005.23) |
| Towards Understanding Diminished Reality | Cheng, Yin, Yan, Gugenheimer, Lindlbauer. CHI 2022 | 輪郭など文脈保持の仕組みが好まれる | 要旨 | [DOI](https://doi.org/10.1145/3491102.3517452) |
| A survey of diminished reality | Mori, Ikeda, Saito. IPSJ CVA 2017 | DR の技術整理 | 未検証 | [DOI](https://doi.org/10.1186/s41074-017-0028-1) |
| Observation-based diminished reality: a systematic literature review | Eskandari, Motamedi. Virtual Reality 2025 | 67 本を分析 | 未検証 | [DOI](https://doi.org/10.1007/s10055-024-01074-0) |
| CIRO: The Effects of Visually Diminished Real Objects on Human Perception in Handheld Augmented Reality | Kim, Kim, Lee, Kim, Hwang. Electronics 2021 | 書誌のみ | 未検証 | [DOI](https://doi.org/10.3390/electronics10080900) |
| Diminished reality for augmented reality interior design | Siltanen. The Visual Computer | 家具を消して新しい家具を置く | 未検証 | [DOI](https://doi.org/10.1007/s00371-015-1174-z) |
| Diminished reality system with real-time object detection using deep learning for onsite landscape simulation during redevelopment | Kido, Fukuda, Yabuki. 2020 | 既存建物を消して新建物を重ねる | 未検証 | [DOI](https://doi.org/10.1016/j.envsoft.2020.104759) |
| Diminished reality using semantic segmentation and generative adversarial network for landscape assessment | Kikuchi, Fukuda, Yabuki. JCDE 2022 | 書誌のみ | 未検証 | [DOI](https://doi.org/10.1093/jcde/qwac067) |
| DecluttAR: An Interactive Visual Clutter Dimming System to Help Focus on Work | Yokoro, Perusquia-Hernandez, Isoyama, Uchiyama, Kiyokawa. AHs 2023 | 机上の散らかりを減光・除去 | 未検証 | [DOI](https://doi.org/10.1145/3582700.3582718) |
| Diminished Reality Based on Image Inpainting Considering Background Geometry | Kawai, Sato, Yokoya. TVCG 2016 | 視点追従のインペインティング | 未検証 | [DOI](https://doi.org/10.1109/tvcg.2015.2462368) |
| InpaintFusion: Incremental RGB-D Inpainting for 3D Scenes | Mori, Erat, Broll, Saito, Schmalstieg, Kalkofen. TVCG 2020 | 多視点で一貫した DR | 未検証 | [DOI](https://doi.org/10.1109/tvcg.2020.3003768) |
| Good Keyframes to Inpaint | Mori, Schmalstieg, Kalkofen. TVCG 2023 | キーフレーム選択 | 未検証 | [DOI](https://doi.org/10.1109/tvcg.2022.3176958) |
| Advanced self-contained object removal for realizing real-time Diminished Reality in unconstrained environments | Herling, Broll. ISMAR 2010 | リアルタイム DR の古典 | 未検証 | [DOI](https://doi.org/10.1109/ismar.2010.5643572) |
| The Dark Side of Perceptual Manipulations in Virtual Reality | Tseng ほか. CHI 2022 | 知覚操作の危害 | 未検証 | [DOI](https://doi.org/10.1145/3491102.3517728) |
| Ad-Blocked Reality | Katins ほか. CHI 2025 | 書誌のみ | 未検証 | [DOI](https://doi.org/10.1145/3706598.3713230) |
| The Mixed Reality Concerns (MRC) Questionnaire | Katins ほか. CHI 2024 | 書誌のみ | 未検証 | [DOI](https://doi.org/10.1145/3613904.3642631) |
| Human–Robot Interaction through Diminished Reality（書籍章） | 著者未検証. Wiley 2026 | 中身未読 | 未検証 | [DOI](https://doi.org/10.1002/9781394470143.ch21) |
| US 9514573 "Diminished reality"（特許） | — | 部屋をステージングして再配置後を見せる（人向け） | 未検証 | [USPTO](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/9514573) |
| exTouch | Kasahara, Niiyama, Heun, Ishii. TEI 2013 | 仮想グラフィックをドラッグ→実体が追従 | 未検証 | [DOI](https://doi.org/10.1145/2460625.2460661) |
| TouchMe: An Augmented Reality Based Remote Robot Manipulation | Hashimoto, Ishida, Inami, Igarashi. ICAT 2011（確認できたのは日本語版 Robomec 2012） | CG ゴーストを操作→実機が動く | 未検証 | [DOI](https://doi.org/10.1299/jsmermd.2012._2p1-m04_1) |
| Mobile Mixed-Reality Interfaces That Enhance Human–Robot Interaction in Shared Spaces | Frank, Moorhead, Kapila. Frontiers 2017 | 実物の仮想コピーをドラッグ | 未検証 | [DOI](https://doi.org/10.3389/frobt.2017.00020) |
| Realizing mixed-reality environments with tablets for intuitive human-robot collaboration for object manipulation tasks | Frank, Moorhead, Kapila. RO-MAN 2016 | 上の前身 | 未検証 | [DOI](https://doi.org/10.1109/roman.2016.7745146) |
| Designing Laser Gesture Interface for Robot Control | Ishii, Zhao, Inami, Igarashi, Imai. INTERACT 2009 | レーザで物体と置き場所を指示 | 未検証 | [DOI](https://doi.org/10.1007/978-3-642-03658-3_52) |
| Sketch and Run: a stroke-based interface for home robots | Sakamoto, Honda, Inami, Igarashi. CHI 2009 | 俯瞰映像にストローク | 未検証 | [DOI](https://doi.org/10.1145/1518701.1518733) |
| Optimal Assistance for Object-Rearrangement Tasks in Augmented Reality | Newman ほか. arXiv 2020 | 人が行う再配置を AR で支援 | 要旨 | [arXiv](https://arxiv.org/abs/2010.07358) |
| Visual comparison for information visualization | Gleicher ほか. 2011 | 並置・重畳・明示的符号化 | 未検証 | [DOI](https://doi.org/10.1177/1473871611416549) |
| Considerations for Visualizing Comparison | Gleicher. TVCG 2018 | 比較設計の枠組み | 未検証 | [DOI](https://doi.org/10.1109/tvcg.2017.2744199) |
| Comparative Layouts Revisited | L'Yi, Jo, Seo. TVCG 2021 | 比較レイアウトの指針 | 未検証 | [DOI](https://doi.org/10.1109/tvcg.2020.3030419) |
| Interactive 4D overview and detail visualization in augmented reality | Zollmann ほか. ISMAR 2012 | 建設現場の時間変化を AR で | 未検証 | [DOI](https://doi.org/10.1109/ismar.2012.6402554) |
| Visualization Techniques in Augmented Reality: A Taxonomy, Methods and Patterns | Zollmann ほか. TVCG 2021 | X-ray・ゴースト・DR の分類 | 未検証 | [DOI](https://doi.org/10.1109/tvcg.2020.2986247) |
| Design Patterns for Situated Visualization in Augmented Reality | Lee, Sedlmair, Schmalstieg（未照合）. 2023 | 状況内可視化のパターン | 未検証 | [arXiv](https://arxiv.org/abs/2307.09157) |
| Who Put That There? Temporal Navigation of Spatial Recordings by Direct Manipulation | Lilija, Pohl, Hornbæk. CHI 2020 | 物体を動かして時間をスクラブ | 未検証 | [DOI](https://doi.org/10.1145/3313831.3376604) |
| In-situ or side-by-side? A user study on augmented reality maintenance instructions in blind areas | 著者未検証. Computers in Industry 2022 | その場重畳と 3D 並置は 2D 図面より良い | 要旨 | [ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S0166361522001919) |
| DALL-E-Bot | Kapelyukh, Vosylius, Johns. RA-L 2023 | 拡散モデルでゴール画像（内部用） | 未検証 | [DOI](https://doi.org/10.1109/lra.2023.3272516) |
| StructDiffusion | Liu, Du, Hermans, Chernova, Paxton. RSS 2023 | 目標配置を拡散モデルで生成 | 未検証 | [DOI](https://doi.org/10.15607/rss.2023.xix.031) |
| StructFormer | Liu, Paxton, Hermans, Fox. ICRA 2022 | 言語から目標配置 | 未検証 | [DOI](https://doi.org/10.1109/icra46639.2022.9811931) |
| Dream2Real | Kapelyukh, Ren, Alzugaray, Johns. ICRA 2024 | 候補ゴール状態を描画し VLM が評価 | 未検証 | [DOI](https://doi.org/10.1109/icra57147.2024.10611220) |
| SG-Bot | Zhai ほか. ICRA 2024 | シーングラフからゴールを想像 | 未検証 | [DOI](https://doi.org/10.1109/icra57147.2024.10610792) |
| SuSIE | Black ほか. ICLR 2024 | サブゴール画像を生成 | 未検証 | [arXiv](https://arxiv.org/abs/2310.10639) |
| UniPi | Du ほか. NeurIPS 2023 | 未来の実行映像を生成 | 未検証 | [DOI](https://doi.org/10.52202/075280-0403) |
| Housekeep | Kant ほか. ECCV 2022 | 常識的な片付け先の推論 | 未検証 | [DOI](https://doi.org/10.1007/978-3-031-19842-7_21) |
| TidyBot | Wu ほか. Autonomous Robots 2023 | 少数例から片付けルールを要約 | 未検証 | [DOI](https://doi.org/10.1007/s10514-023-10139-z) |
| TIDEE | Sarch ほか. ECCV 2022 | 場違いな物体の検出と片付け | 未検証 | [DOI](https://doi.org/10.1007/978-3-031-19842-7_28) |
| Robot, organize my shelves! | Abdo, Stachniss, Spinello, Burgard. ICRA 2015 | 整理の好みを予測 | 未検証 | [DOI](https://doi.org/10.1109/icra.2015.7139396) |
| My House, My Rules | Kapelyukh, Johns. CoRL 2021 | 片付けの好みを GNN で学習 | 未検証 | [arXiv](https://arxiv.org/abs/2111.03112) |

## 付録 E：実行不能・ルール違反の提示、説明可能な計画、ラベル設計（論点 3）

| 題名 | 著者・会場・年 | 要点 | 確認度 | URL |
|---|---|---|---|---|
| Explainable OOHRI（再掲） | Wang, Kari, Abtahi. HRI 2026 | 決定木で物理的実行可能性を判定。赤の二値＋説明タグ＋Auto / Alternative / Ignore / Virtual / Physical。14 名、物理ロボットなしの探索的評価 | 全文 | [DOI](https://doi.org/10.1145/3757279.3785569) |
| Head-Mounted Augmented Reality for Explainable Robotic Wheelchair Assistance | Zolotas, Elsdon, Demiris. IROS 2018 | 介入の理由を障害物の強調で | 未検証 | [DOI](https://doi.org/10.1109/iros.2018.8594002) |
| Towards Explainable Shared Control using Augmented Reality | Zolotas, Demiris. IROS 2019 | 同上 | 未検証 | [DOI](https://doi.org/10.1109/iros40897.2019.8968117) |
| Descriptive and Prescriptive Visual Guidance to Improve Shared Situational Awareness in Human-Robot Teaming | Tabrez, Luebbers, Hayes. AAMAS 2022 | 状態の見立てと推奨行動 | 未検証 | [DOI](https://doi.org/10.65109/ware7854) |
| Augmented Reality-Based Explainable AI Strategies for Establishing Appropriate Reliance and Trust in Human-Robot Teaming | Luebbers, Tabrez, Hayes. VAM-HRI 2022（会場未確認） | 反実仮想説明と正当化 | 未検証 | [PDF](https://m-luebbers.github.io/pdfs/vamhri22.pdf) |
| Virtual Borders: Accurate Definition of a Mobile Robot's Workspace Using Augmented Reality | Sprute, Tönnies, König. IROS 2018 | 住人が AR で立入禁止の境界を描く | 未検証 | [DOI](https://doi.org/10.1109/iros.2018.8593615) |
| A Study on Different User Interfaces for Teaching Virtual Borders to Mobile Robots | 同著者. IJSR | 同上 | 未検証 | [DOI](https://doi.org/10.1007/s12369-018-0506-3) |
| Interactive Policy Shaping for Human-Robot Collaboration with Transparent Matrix Overlays | Brawer ほか. HRI 2023 | 方策を物体上に重ねて修正 | 未検証 | [DOI](https://doi.org/10.1145/3568162.3576983) |
| What You See Is (Not) What You Get: A VR Framework for Correcting Robot Errors | Wozniak, Stower, Jensfelt, Pereira. HRI 2023 Companion | 認識の見落としを VR で直す | 要旨 | [arXiv](https://arxiv.org/abs/2301.04919) |
| Happily Error After | 同著者. RO-MAN 2023 | VR と 2D で認識誤りを直す、56 人 | 要旨 | [arXiv](https://arxiv.org/html/2306.14589v1) |
| iTeach: Interactive Teaching for Robot Perception using Mixed Reality | P, Salvato, Bomnale, Wang, Xiang. arXiv 2024 | 検出結果を重ね、失敗例に注釈 | 要旨 | [arXiv](https://arxiv.org/abs/2410.09072) |
| Robot Object Referencing through Legible Situated Projections | Weng ほか. ICRA 2019 | 紛れない位置に光を当てる | 未検証 | [DOI](https://doi.org/10.1109/icra.2019.8793638) |
| Mixed Reality Deictic Gesture for Multi-Modal Robot Communication | Williams ほか. HRI 2019 | MR の矢印で対象を指す | 未検証 | [DOI](https://doi.org/10.1109/hri.2019.8673275) |
| Shared Affordance-awareness via Augmented Reality for Proactive Assistance in Human-robot Collaboration | Moore, Zolotas, Padir. arXiv 2023 | アフォーダンス領域の外で助けを求める | 要旨 | [arXiv](https://arxiv.org/abs/2312.13410) |
| Using Mobile AR for Rapid Feasibility Analysis for Deployment of Robots | Zielinski, Tadeja, Blumberg, Kjærgaard. RA-L | 設置前に到達可否を調べる、22 人 | 要旨 | [arXiv](https://arxiv.org/abs/2503.14725) |
| ReachVox: Clutter-Free Reachability Visualization for Robot Motion Planning in Virtual Reality | Hauck, Abdlkarim, Dudley, Kristensson, Ofek, Grubert. ISMAR 2025 | 到達可能性を最小限に符号化 | 要旨 | [arXiv](https://arxiv.org/abs/2508.11426) |
| Indicating Robot Vision Capabilities with Augmented Reality | Wang, Phatak, Ocampo, Han. IJSR | 視野限界のインジケータ、N=41 | 要旨 | [arXiv](https://arxiv.org/abs/2511.03550) |
| Expressing Robot Incapability | Kwon, Huang, Dragan. HRI 2018 | 「何が・なぜできないか」を動きで | 未検証 | [DOI](https://doi.org/10.1145/3171221.3171276) |
| Why Can't You Do That HAL? Explaining Unsolvability of Planning Tasks | Sreedharan, Srivastava, Smith, Kambhampati. IJCAI 2019 | 到達できないサブゴールを特定 | 未検証 | [DOI](https://doi.org/10.24963/ijcai.2019/197) |
| A New Approach to Plan-Space Explanation | Eifler, Cashmore, Hoffmann, Magazzeni, Steinmetz. AAAI 2020 | 両立しないゴールの最小集合 | 未検証 | [DOI](https://doi.org/10.1609/aaai.v34i06.6534) |
| Plan-Space Explanation via Plan-Property Dependencies | Eifler, Steinmetz, Torralba, Hoffmann. IJCAI 2020 | 時相論理へ拡張 | 未検証 | [DOI](https://doi.org/10.24963/ijcai.2020/566) |
| Explaining Soft-Goal Conflicts through Constraint Relaxations | Eifler, Frank, Hoffmann. IJCAI 2022 | どの制約を緩めれば衝突が消えるか | 未検証 | [DOI](https://doi.org/10.24963/ijcai.2022/641) |
| Iterative Planning with Plan-Space Explanations: A Tool and User Study | Eifler, Hoffmann. XAIP 2020 | 説明つきの反復計画ツール | 要旨 | [arXiv](https://arxiv.org/abs/2011.09705) |
| Plan Explanations as Model Reconciliation | Chakraborti, Sreedharan, Zhang, Kambhampati. IJCAI 2017 | モデルの差を埋める最小の情報 | 未検証 | [DOI](https://doi.org/10.24963/ijcai.2017/23) |
| Explaining Impossible High-Level Robot Behaviors | Raman, Kress-Gazit. T-RO 2013 | 実現不能な仕様の原因を特定 | 未検証 | [DOI](https://doi.org/10.1109/tro.2012.2214558) |
| Sorry Dave, I'm Afraid I Can't Do That | Raman ほか. RSS 2013 | 原因になったユーザー自身の文にさかのぼる | 未検証 | [DOI](https://doi.org/10.15607/rss.2013.ix.023) |
| Coming Up With Good Excuses | Göbelbecker ほか. ICAPS 2010 | 初期状態のどこが違えば解けたか | 未検証 | [DOI](https://doi.org/10.1609/icaps.v20i1.13421) |
| Contrastive Explanations of Plans through Model Restrictions | Krarup ほか. JAIR 2021 | 「なぜ A でなく B か」 | 未検証 | [DOI](https://doi.org/10.1613/jair.1.12813) |
| The minimum constraint removal problem with three robotics applications | Hauser. IJRR 2014 | 取り除けば解ける制約の最小集合 | 未検証 | [DOI](https://doi.org/10.1177/0278364913507795) |
| The Emerging Landscape of Explainable Automated Planning & Decision Making | Chakraborti, Sreedharan, Kambhampati. IJCAI 2020 | XAIP の総説 | 未検証 | [DOI](https://doi.org/10.24963/ijcai.2020/669) |
| Why and why not explanations improve the intelligibility of context-aware intelligent systems | Lim, Dey, Avrahami. CHI 2009 | なぜ／なぜしないの説明 | 未検証 | [DOI](https://doi.org/10.1145/1518701.1519023) |
| Why and How Robots Should Say 'No' | Briggs, Williams, Jackson, Scheutz. IJSR | 断る理由と断り方 | 未検証 | [DOI](https://doi.org/10.1007/s12369-021-00780-y) |
| Plug in the Safety Chip | Yang, Raman, Shah, Tellex. ICRA 2024 | 制約を時相論理にして違反行動を刈り取る | 未検証 | [DOI](https://doi.org/10.1109/icra57147.2024.10611447) |
| Safety Guardrails for LLM-Enabled Robots（RoboGuard） | Ravichandran ほか. RA-L 2026 | 衝突を自動解決 | 未検証 | [DOI](https://doi.org/10.1109/lra.2026.3667488) |
| Generating Robot Constitutions & Benchmarks for Semantic Safety（ASIMOV） | Sermanet ほか. arXiv 2025 | 憲法による可否判定 | 未検証 | [arXiv](https://arxiv.org/abs/2503.08663) |
| AutoRT | Ahn ほか. arXiv 2024 | 憲法的ルールで課題を選別 | 未検証 | [arXiv](https://arxiv.org/abs/2401.12963) |
| CAPE: Corrective Actions from Precondition Errors using Large Language Models | Raman ほか. ICRA 2024 | 前提条件エラーを LLM に返して修復 | 未検証 | [DOI](https://doi.org/10.1109/icra57147.2024.10611376) |
| Text2Interaction | Thumm, Agia, Pavone, Althoff. CoRL 2024 | 好みを計画・動作・安全パラメータに変換 | 要旨 | [arXiv](https://arxiv.org/abs/2408.06105) |
| DROC | Zha ほか. ICRA 2024 | 言葉の訂正を知識として蓄える | 未検証 | [DOI](https://doi.org/10.1109/icra57147.2024.10610455) |
| SayCan | Ahn ほか. CoRL 2022 | 実行可能性で LLM の提案を重み付け | 未検証 | [arXiv](https://arxiv.org/abs/2204.01691) |
| Inner Monologue | Huang ほか. arXiv 2022 | 成功判定と人の返答を LLM に戻す | 未検証 | [arXiv](https://arxiv.org/abs/2207.05608) |
| DoReMi | Guo, Wang, Zha, Chen. IROS 2024 | 制約を生成し VLM で違反を監視 | 未検証 | [DOI](https://doi.org/10.1109/iros58592.2024.10802284) |
| Asking for Help Using Inverse Semantics | Tellex, Knepper, Li, Rus, Roy. RSS 2014 | 誤解されにくい依頼文 | 未検証 | [DOI](https://doi.org/10.15607/rss.2014.x.024) |
| Recovering from failure by asking for help | Knepper ほか. Autonomous Robots 2015 | 同上 | 未検証 | [DOI](https://doi.org/10.1007/s10514-015-9460-1) |
| Interactive Visual Grounding of Referring Expressions for Human-Robot Interaction | Shridhar, Hsu. RSS 2018 | 候補を質問で絞る | 未検証 | [DOI](https://doi.org/10.15607/rss.2018.xiv.028) |
| REX: Designing User-centered Repair and Explanations to Address Robot Failures | Lee, Praveena, Mutlu. DIS 2024 | 書誌のみ | 未検証 | [DOI](https://doi.org/10.1145/3643834.3661559) |
| Enhancing Privacy and Trust in Domestic Robots Through Real-Time Feedback and Intervention Interfaces | Xu, Hoggenmueller, Yu. OzCHI 2025 | 家庭ロボットのデータ取扱いを可視化し介入 | 要旨 | [DOI](https://doi.org/10.1145/3764687.3764705) |
| Evaluating label placement for augmented reality view management | Azuma, Furmanski. ISMAR 2003 | 重なりと読み取り時間 | 未検証 | [DOI](https://doi.org/10.1109/ismar.2003.1240689) |
| Image-driven view management for augmented reality browsers | Grasset ほか. ISMAR 2012 | 実物を隠さない位置にラベル | 未検証 | [DOI](https://doi.org/10.1109/ismar.2012.6402555) |
| Hedgehog labeling | Tatzgern, Kalkofen, Grasset, Schmalstieg. IEEE VR 2014 | 3D 空間でラベル配置 | 未検証 | [DOI](https://doi.org/10.1109/vr.2014.6802046) |
| Temporal Coherence Strategies for Augmented Reality Labeling | Madsen ほか. TVCG 2016 | ラベルの時間的一貫性 | 未検証 | [DOI](https://doi.org/10.1109/tvcg.2016.2518318) |
| Embedded Data Representations | Willett, Jansen, Dragicevic. TVCG 2017 | situated と embedded の区別 | 未検証 | [DOI](https://doi.org/10.1109/TVCG.2016.2598608) |
| Usable error message presentation in the World Wide Web: Do not show errors right away | Bargas-Avila ほか. 2007 | エラーは区切りでまとめて | 未検証 | [DOI](https://doi.org/10.1016/j.intcom.2007.01.003) |
| Designing usable web forms | Seckler ほか. CHI 2014 | フォーム設計指針の実証 | 未検証 | [DOI](https://doi.org/10.1145/2556288.2557265) |
| Compiler Error Messages Considered Unhelpful | Becker ほか. ITiCSE-WGR 2019 | エラー文面の指針の総説 | 未検証 | [DOI](https://doi.org/10.1145/3344429.3372508) |
| A framework for proactive construction defect management using BIM, augmented reality and ontology-based data collection template | Park, Lee, Kwon, Wang. 2013 | BIM＋AR の欠陥管理 | 未検証 | [DOI](https://doi.org/10.1016/j.autcon.2012.09.010) |
| A defect management system for reinforced concrete work utilizing BIM, image-matching and augmented reality | Kwon, Park, Lim. 2014 | 設計モデルを重ねてずれを見つける | 未検証 | [DOI](https://doi.org/10.1016/j.autcon.2014.05.005) |
| Reality Editor: Programming Smarter Objects | Heun, Hobin, Maes. UbiComp 2013 Adjunct | AR で実物の上に機能を表示 | 未検証 | [DOI](https://doi.org/10.1145/2494091.2494185) |

## 付録 F：サーベイ・タクソノミーと評価の参照研究

| 題名 | 著者・会場・年 | 要点 | 確認度 | URL |
|---|---|---|---|---|
| Augmented Reality and Robotics: A Survey and Taxonomy for AR-enhanced Human-Robot Interaction and Robotic Interfaces | Suzuki, Karim, Xia, Hedayati, Marquardt. CHI 2022 | 460 本、8 次元 | 本文 | [arXiv](https://arxiv.org/abs/2203.03254) |
| Virtual, Augmented, and Mixed Reality for Human-Robot Interaction: A Survey and Virtual Design Element Taxonomy | Walker, Phung, Chakraborti, Williams, Szafir. THRI 2023 | 175 本、VDE。Spatial / Alteration Previews | 本文 | [arXiv](https://arxiv.org/abs/2202.11249) |
| How to Communicate Robot Motion Intent: A Scoping Review | Pascher, Gruenefeld, Schneegass, Gerken. CHI 2023 | 77 本、意図の種類・情報・位置 | 本文 | [arXiv](https://arxiv.org/abs/2303.00362) |
| The Reality-Virtuality Interaction Cube | Williams, Szafir, Chakraborti. HRI 2019 LBR | 書誌のみ | 未検証 | [DOI](https://doi.org/10.1109/HRI.2019.8673071) |
| Augmented Reality for Robotics: A Review | Makhataeva, Varol. Robotics 2020 | 書誌のみ | 未検証 | [DOI](https://doi.org/10.3390/robotics9020021) |
| Augmented Reality Meets Artificial Intelligence in Robotics: A Systematic Review | Bassyouni, Elhajj. Frontiers 2021 | 29 本 | 本文 | [Frontiers](https://www.frontiersin.org/articles/10.3389/frobt.2021.724798/full) |
| Review on existing VR/AR solutions in human–robot collaboration | Dianatfar, Latokartano, Lanz. Procedia CIRP 2021 | 書誌のみ | 未検証 | [DOI](https://doi.org/10.1016/j.procir.2020.05.259) |
| Augmented Reality for Human–Robot Collaboration and Cooperation in Industrial Applications: A Systematic Literature Review | Costa, Petry, Moreira. Sensors 2022 | 書誌のみ | 未検証 | [DOI](https://doi.org/10.3390/s22072725) |
| A Survey of Augmented Reality for Human–Robot Collaboration | Chang, Hayes. Machines 2024 | 書誌のみ | 未検証 | [DOI](https://doi.org/10.3390/machines12080540) |
| A Systematic Review of XR-Enabled Remote Human-Robot Interaction Systems | Wang, Shen, Lee. ACM CSUR | 100 本 | 要旨 | [arXiv](https://arxiv.org/abs/2403.11384) |
| Designing Effective AR Interfaces for Human-Robot Interaction: A Scoping Review and Practical Guidelines for Robot Pick-and-Place Tasks | Burden, Liu, Vermeulen. OzCHI 2024 | pick-and-place 教示の設計指針 | 要旨 | [DOI](https://doi.org/10.1145/3726986.3727041) |
| A survey of communicating robot learning during human-robot interaction | Habibian ほか. IJRR 2024 | 学習状態を人に返す | 要旨 | [DOI](https://doi.org/10.1177/02783649241281369) |
| Extended Reality as a Mediation Layer for Situated Human Control in Human-Robot Teaming | Grubert, Dudley, Ofek, Kristensson. arXiv 2026 | 設計次元に uncertainty and plan validity、anticipatory recovery | 要旨 | [arXiv](https://arxiv.org/abs/2607.25047) |
| Making Robot Ecologies Visible | Spagnuolo ほか. HRI Companion 2026 | 生態学的インタフェースの分類 | 要旨 | [DOI](https://doi.org/10.1145/3776734.3794418) |
| A Visual Design Space for One-Dimensional Intelligible Human-Robot Interaction Visualizations | van Deurzen, Rovelo Ruiz, Luyten. HRI 2024 Companion | 限られた表示資源での設計空間 | 要旨 | [DOI](https://doi.org/10.1145/3610978.3640557) |
| A Survey on End-User Robot Programming | Ajaykumar, Steele, Huang. ACM CSUR 2021 | AR は遮蔽・奥行き、音声は誤認識の問題 | 未検証 | [arXiv](https://arxiv.org/abs/2105.01757) |
| Explainable Agents and Robots: Results from a Systematic Literature Review | Anjomshoae ほか. AAMAS 2019 | 書誌のみ | 未検証 | [DOI](https://doi.org/10.65109/kczb5817) |
| Explainable autonomous robots: a survey and perspective | Sakai, Nagai. Advanced Robotics 2022 | 説明可能な自律ロボットの定義 | 要旨 | [arXiv](https://arxiv.org/abs/2105.02658) |
| Understanding and Resolving Failures in Human-Robot Interaction | Honig, Oron-Gilad. Frontiers in Psychology 2018 | 52 本、RF-HIP モデル。症状のない失敗は意図的に伝える必要 | 本文 | [Frontiers](https://www.frontiersin.org/articles/10.3389/fpsyg.2018.00861/full) |
| A Taxonomy of Domestic Robot Failure Outcomes | Cameron ほか. TAS 2024 | 家庭ロボットの失敗結果の分類 | 未検証 | [DOI](https://doi.org/10.1145/3686038.3686050) |
| Formal methods in robot end user development | Hwang, Lee, Porfirio, Hiatt, Mutlu. 2026 | 形式手法のレビュー | 要旨 | [DOI](https://doi.org/10.1108/ftrob-05-2025-0083) |
| How Do We Research Human-Robot Interaction in the Age of Large Language Models? A Systematic Review | Wang ほか. CHI 2026 | 86 本、評価指標がばらばら | 要旨 | [arXiv](https://arxiv.org/abs/2602.15063) |
| Large language models for human-robot interaction: A review | Zhang ほか. 2023 | 書誌のみ | 未検証 | [DOI](https://doi.org/10.1016/j.birob.2023.100131) |
| LLM Integration in Extended Reality | Tang ほか. CHI 2025 | 書誌のみ | 未検証 | [DOI](https://doi.org/10.1145/3706598.3714224) |
| Survey of Large Language Models in Extended Reality | Wang, Zhao, Mao, Yang. arXiv 2025 | 技術パラダイム別 | 未検証 | [arXiv](https://arxiv.org/abs/2508.03014) |
| When Generative Artificial Intelligence Meets Extended Reality | Ning ほか. IJHCI 2025 | 生成 AI × XR | 未検証 | [arXiv](https://arxiv.org/abs/2511.03282) |
| LLMR: Real-time Prompting of Interactive Worlds using Large Language Models | De La Torre ほか. CHI 2024 | システム論文 | 未検証 | [arXiv](https://arxiv.org/abs/2309.12276) |
| Towards large language model for cognitive industrial mixed reality: A survey | Fang ほか. 2026 | 産業 MR × LLM | 未検証 | [DOI](https://doi.org/10.1016/j.aei.2025.104276) |
| Intelligent human-centric manufacturing in industry 5.0 | 著者要確認. 2026 | 同上 | 未検証 | [DOI](https://doi.org/10.1016/j.jii.2026.101229) |
| Plan-Then-Execute: An Empirical Study of User Trust and Team Performance When Using LLM Agents As A Daily Assistant | He, Demartini, Gadiraju. CHI 2025 | もっともらしい計画への過信、N=248 | 要旨 | [arXiv](https://arxiv.org/abs/2502.01390) |
| Evaluating Human Trust in LLM-Based Planners: A Preliminary Study | Chen ほか. arXiv 2025 | 説明は評価精度を上げるが信頼への効果は限定的 | 要旨 | [arXiv](https://arxiv.org/abs/2502.20284) |
| Robot Programming with Augmented Reality: The Role of Spatial Ability | Leins ほか. arXiv 2026 | AR は全体では負荷・使用性を改善せず、N=71 | 要旨 | [arXiv](https://arxiv.org/abs/2602.03544) |
| Investigating the Validity of Augmented Reality Simulations for Human-Robot Interaction through Trust | Guerra, Söhngen, Prilla. 2026（会議名未検証） | AR 上の仮想ロボットと実機で信頼に明確な差なし、N=40 | 要旨 | [DOI](https://doi.org/10.1145/3820253.3820273) |
| Body Sublimation | Ohta ほか. UIST 2026 | XR とロボットを統合する拡張手 | 要旨 | [DOI](https://doi.org/10.1145/3830398.3830583) |

## 付録 G：見つからなかったものと検索範囲の限界

次の項目は、今回の検索では該当する研究を確認できなかった。いずれも Web 検索数回、Crossref、arXiv API（途中で制限）、Semantic Scholar（429 多発）の範囲での結果で、ACM DL・IEEE Xplore の直接検索、Google Scholar の網羅検索、J-STAGE の直接検索はしていない。存在しないことを意味しない。

| 見つからなかったもの | 補足 |
|---|---|
| 1 つのエラーを列のステップと実空間の物の両方に、事前に結びつけて見せるシステム | 事後なら Han ら、人の誤りなら AR 組立ガイドが近い |
| 家庭ルール・規範の違反を物体ごとに AR ラベルで示す研究 | 物理的制約なら X-OOHRI |
| 言語指示から得た計画の完了後状態を、実物の除去＋仮想コピーで実行前に見せ、人の検証手段として評価した研究 | 表示技術は Reality Promises の removal mode と Scene Responsiveness にある |
| AR の空間プレビューで計画エラーの検出率を測った研究 | 非 AR では HRI Grounding |
| プレビューが過信を増やすかを AR × ロボットで検証した研究 | 非 AR・非ロボットでは He ら、Chen ら |
| 計画の各ステップに確信度を色で付ける UI を主題にした論文 | KnowNo の予測集合は転用できる |
| AR でロボット計画の Before/After 比較技法を系統的に比べた研究 | Gleicher らの 3 分類が枠組みになる |
| XAIP の説明を AR で空間に固定した研究 | — |
| スマートホームのルール衝突を AR でその場に可視化する査読論文、AR で建築法規違反を現場に重ねる査読論文 | 特許文書のみヒット |
| Behavior Tree を AR でデバッグする査読論文、ロボットのタイムトラベル・デバッグを UI として扱う学術論文 | 道具（rosbag、Foxglove）は存在 |
| DR で隠した実物体に利用者がぶつかったことを実測した研究 | — |
| LLM 計画＋AR プレビューを家庭タスクで扱う日本発の研究 | J-STAGE 未検索 |
| MARCER（被引用 16）と PRogramAR（被引用 30）を引用する後続論文の一覧 | その後 Semantic Scholar で全件取得し、付録 H に掲載。Google Scholar との突き合わせは未実施 |

原典で未確認のまま残した主な点は、AURaPath のエラー表示の有無、VeriPlan が違反の反例（どの状態で破れたか）を利用者に見せるか、Cheng らの参加者数とデバイス、Taylor らの数値、ERATO 系 7 件の本文である。

## 付録 H：MARCER と PRogramAR を引用する後続論文（Semantic Scholar、2026-11-22 取得）

Semantic Scholar の引用 API で取得できた全件である。MARCER は 16 件、PRogramAR は 30 件で、重複を除くと 43 件になる（PRogramAR 側には MARCER 自身と、無関係な分野の論文 1 件を含む）。Google Scholar では件数がこれより多い可能性があり、網羅の保証はない。「近さ」は提案（言語指示 → 計画の AR プレビュー → エラー・違反の表示）との関係で、◎ は直接関係する、○ は周辺、− は関係が薄い。要点は Semantic Scholar に載っている要旨の冒頭に基づく（確認度【要旨】）。要旨がないものは題名だけで判断しており【未検証】である。「新規」は本レポートの付録 A〜G に載っていなかった論文である。

なお、提案に最も近い MRPilot（arXiv 2610.07477）と ORCESTRA（arXiv 2608.00775）は、全文を確認した範囲では MARCER も PRogramAR も引用していない。

### 両方を引用する論文（3 件）

| 題名 | 著者・会場・年 | 要点 | 近さ | URL |
|---|---|---|---|---|
| Reality Promises: Virtual-Physical Decoupling Illusions in Mixed Reality via Invisible Mobile Robots | Kari, Abtahi. UIST 2025 | 実物を隠して仮想コピーを動かし、見えないロボットが後から運ぶ（本文 3 節で詳述）【全文】 | ◎ | [DOI](https://doi.org/10.1145/3746059.3747660) |
| Robot Programming with Augmented Reality: The Role of Spatial Ability | Leins, Fischer, Teichmann, Gonnermann-Müller ほか. arXiv 2026 | 71 名の参加者間実験。AR とティーチペンダントで UR5e のプログラミングを学ばせ、空間認識能力との関係を調べる | ○ | [arXiv](https://arxiv.org/abs/2602.03544) |
| Delegate the Details: Flexible Assembly Constraint Authoring for Collaborative XR | Yang, He, Zou, Liu ほか. ISMAR 2026 | 組立の制約を XR で指定する。部品ごとに姿勢を決めるか、人やエージェントに任せるかを選べる | ○ | [DOI](https://doi.org/10.1109/ISMAR70079.2026.00083) |

### MARCER だけを引用する論文（13 件）

| 題名 | 著者・会場・年 | 要点 | 近さ | URL |
|---|---|---|---|---|
| Explainable OOHRI: Communicating Robot Capabilities and Limitations as Augmented Reality Affordances | Wang, Kari, Abtahi. HRI 2026 | できない操作を赤色と説明タグで物体に示す（本文 4 節で詳述）【全文】 | ◎ | [DOI](https://doi.org/10.1145/3757279.3785569) |
| GhostObjects: Instructing Robots by Manipulating Spatially Aligned Virtual Twins in Augmented Reality | Wang, Abtahi. UIST Adjunct 2025 | 実物に位置合わせした等身大の仮想ツインを AR で動かして指示する | ◎ | [arXiv](https://arxiv.org/abs/2508.11022) |
| RoboCritics: Enabling Reliable End-to-End LLM Robot Programming through Expert-Informed Critics | Kim, White, He, Sala ほか. HRI 2026 | LLM が生成したロボットプログラムを批評器が検査し、問題を返す（非 AR）【本文】 | ◎ | [arXiv](https://arxiv.org/abs/2603.06842) |
| SHRIMP: Iterative Refinement of Robot Task Plans | Schroder, Hwang, Kim, Cheng ほか. UIST 2026 | 自然言語から作ったロボットのタスク計画を反復して直す | ◎ | [arXiv](https://arxiv.org/abs/2608.08884) |
| HRI Grounding: Evidence That Operators Authorize and Correct AI Multi-Robot Plans Through a Generated Supervisory Interface | Yu, Nair, Song, Soh. RA-L 2026 | AI が作ったマルチロボット計画を、非専門家が各ステップを見て承認・修正する（非 AR） | ◎ | [DOI](https://doi.org/10.1109/LRA.2026.3730218) |
| Bootstrapping Human-Like Planning via LLMs | Porfirio, Hsiao, Fine-Morris, Smith ほか. RO-MAN 2025 | ドラッグ&ドロップと自然言語という 2 つのエンドユーザプログラミング手法を組み合わせる | ○ | [arXiv](https://arxiv.org/abs/2506.22604) |
| Teaching the Teacher: Live Foundation Model and Augmented Reality Feedback for Human-to-Robot Skill Transfer | Moorman, Luebbers, Zhang, Lau ほか. HRI 2026 | 実演による教示で、非専門家がよい実演を与えられるよう支援する | ○ | [DOI](https://doi.org/10.1145/3757279.3788667) |
| Formal methods in robot end user development: progress, gaps, and opportunities | Hwang, Lee, Porfirio, Hiatt ほか. Foundations and Trends in Robotics 2026 | エンドユーザによるロボット開発での形式手法のサーベイ | ○ | [DOI](https://doi.org/10.1108/ftrob-05-2025-0083) |
| How Do We Research Human-Robot Interaction in the Age of Large Language Models? A Systematic Review | Wang, Xu, Nikolova, Wang ほか. CHI 2026 | LLM を使う HRI 研究の体系的レビュー | ○ | [arXiv](https://arxiv.org/abs/2602.15063) |
| A digital twin-enabled environment for end-user development of robot tasks | Gargioni, Fogli, Nava. Intelligent Service Robotics 2026 | 題名のみ【未検証】 | ○ | [DOI](https://doi.org/10.1007/s11370-026-00758-7) |
| Towards large language model for cognitive industrial mixed reality: A survey | Fang, Xu, Zhang, Wang ほか. Advanced Engineering Informatics 2026 | 題名のみ【未検証】 | ○ | [DOI](https://doi.org/10.1016/j.aei.2025.104276) |
| Intelligent human-centric manufacturing in industry 5.0: A review of large language model enabled extended reality systems | C. P., R. R., Samuel, Karthika ほか. J. Industrial Information Integration 2026 | 題名のみ【未検証】 | ○ | [DOI](https://doi.org/10.1016/j.jii.2026.101229) |
| Vision-Language-Action Models: Concepts, Progress, Applications and Challenges（新規） | Sapkota, Cao, Roumeliotis, Karkee. arXiv 2025 | VLA モデルの総説。題名のみ【未検証】 | − | [arXiv](https://arxiv.org/abs/2505.04769) |

### PRogramAR だけを引用する論文（27 件）

| 題名 | 著者・会場・年 | 要点 | 近さ | URL |
|---|---|---|---|---|
| MARCER: Multimodal Augmented Reality for Composing and Executing Robot Tasks | Ikeda, Gramopadhye, Nekervis, Szafir. HRI 2025 | 本文 1 節で詳述【全文】 | ◎ | [DOI](https://doi.org/10.1109/HRI61500.2025.10974232) |
| LLM-Based Waypoint Authoring via Augmented Reality for Human–Robot Interaction（AURaPath） | Hashemi, Mojallal, Mozaffari, Alirezaee. Applied Sciences 2026 | HoloLens 2 と UR10 の経由点指定に音声を足す。安全に関わる動詞は端末内のキーワード認識で扱う 2 層構成 | ◎ | [DOI](https://doi.org/10.3390/app16209974) |
| ImageInThat: Manipulating Images to Convey User Instructions to Robots | Mahadevan, Lewis, Li, Mutlu ほか. HRI 2025 | 画像を操作してロボットへの指示を伝える（非 AR） | ◎ | [arXiv](https://arxiv.org/abs/2503.15500) |
| ARTHUR: authoring human–robot collaboration processes with augmented reality using hybrid user interfaces | Lunding, Hubenschmid, Feuchtner, Grønbæk. Virtual Reality 2025 | RoboVisAR の後継（本文 2 節）【本文】 | ◎ | [arXiv](https://arxiv.org/abs/2501.02304) |
| Tell-XR: Conversational End-User Development of XR Automations | Carcangiu, Manca, Mereu, Santoro ほか. INTERACT 2025 | LLM エージェントが、XR の自動化を Event-Condition-Action ルールとして会話で定義させる（ロボットではない） | ◎ | [arXiv](https://arxiv.org/abs/2504.09104) |
| End-user automation authoring in VR and AR through conversations: patterns, errors and user recovery strategies | Carcangiu, Manca, Mereu, Santoro ほか. Behaviour & Information Technology 2026 | 題名から、会話でのルール作成における誤りと利用者の回復方略を扱う【未検証】 | ◎ | [DOI](https://doi.org/10.1080/0144929x.2026.2714168) |
| REACTR: A Responsive Environment for Authoring Code and Testing Robots | Ikeda, Szafir. RO-MAN 2026 | 可視化を直接操作してプログラムの挙動を変え、すぐに結果を見るライブプログラミング環境 | ○ | [DOI](https://doi.org/10.1109/RO-MAN72286.2026.11714554) |
| Exploring Co-located Collaborative Visual Programming of Industrial Robotic Workplaces in Handheld AR（新規） | Materna, Kapinus, Bambušek, Beran ほか. CHI 2026 | 複数の利用者が同じ場所で、手持ち AR を使ってロボット作業場をプログラムする | ○ | [DOI](https://doi.org/10.1145/3772318.3791440) |
| ARTOO-DARTU: Studying AR-HRC With AR Obstruction Mitigation During a Warehouse Task | Fronk, Ye, Qu, Gorlatova. 2026 | AR の表示が実世界の重要な要素を隠す問題と、その緩和 | ○ | [arXiv](https://arxiv.org/abs/2606.25202) |
| Low-Code Mixed Reality Programming Framework for Collaborative Robots: From Operator Intent to Executable Trajectories（新規） | Wang, Li, Yu, Pan ほか. Robotics 2025 | MR と実演による教示で協働ロボットをプログラムする | ○ | [DOI](https://doi.org/10.3390/robotics15010009) |
| An augmented reality-based wearable system for handheld-free and intuitive robot programming（新規） | Kim, Lee, Bae. J. Intelligent Manufacturing 2025 | 産業用ロボットを手ぶらでプログラムする AR ウェアラブル | ○ | [DOI](https://doi.org/10.1007/s10845-025-02581-w) |
| Codeless, Inclusive, and End-to-End Robotized Manipulations by Leveraging Extended Reality and Digital Twin Technologies（新規） | Hübel, Kaigom. HSI 2024 | XR とデジタルツインでコードを書かずにロボット操作を指定する | ○ | [DOI](https://doi.org/10.1109/HSI61632.2024.10613560) |
| Improving Interaction Comfort in Authoring Task in AR-HRI through Dynamic Dual-Layer Interaction Adjustment（新規） | Pei, Zhang, Yang, Tao ほか. ACM MM 2024 | AR-HRI の作成作業で、身体的に楽な操作方法を場面に応じて選ぶ | ○ | [DOI](https://doi.org/10.1145/3664647.3681364) |
| Beyond Static Instruction: A Multi-agent AI Framework for Adaptive Augmented Reality Robot Training | Leins, Gonnermann-Müller, Teichmann, Pokutta. HRI Companion 2026 | 産業用ロボット訓練の AR アプリと、学習者に合わせる枠組み | ○ | [arXiv](https://arxiv.org/abs/2603.00016) |
| Empowering Non-Expert Users in Fashion Remanufacturing: Enhancing Human-Multi-Robot Interaction through Real-Time Visualization（新規） | Gollob, Bastan, Braumann, Luible-Baer. CHI EA 2025 | 非専門家が可視化つきの手動誘導で複数ロボットのタスクを定義する | ○ | [DOI](https://doi.org/10.1145/3706599.3716232) |
| Enabling End Users to Program Robots Using Reinforcement Learning（新規） | Ayalew, Wang, Littman, Ur ほか. HRI 2025 | 非技術者が強化学習の報酬を指定してロボットをプログラムする 2 つの手法（非 AR） | ○ | [DOI](https://doi.org/10.1109/HRI61500.2025.10974035) |
| Robo-Blocks: Generative Scaffolding in End-User Design and Programming of Social Robots（新規） | Sato, Kim, White, Maneesh ほか. DIS 2026 | ソーシャルロボットのプログラミングで、LLM への頼りすぎを避ける足場かけ（非 AR） | ○ | [arXiv](https://arxiv.org/abs/2605.28154) |
| Rapid Conversational Authoring of Interactive Human-Robot Activities（新規） | Cao, Tchamdja, Huang. AAAI Symposium Series 2026 | ソーシャルロボットの振る舞いを会話で作る（非 AR） | ○ | [DOI](https://doi.org/10.1609/aaaiss.v10i1.43501) |
| Collaborative Robot Teleoperation in Mixed Reality Environment for Inspection Tasks（新規） | Rivera, Aceta, Kildal, Fernández ほか. PRESENCE 2024 | 協働ロボットの遠隔操作を MR で支援する | ○ | [DOI](https://doi.org/10.1162/PRES_a_00439) |
| MAGIC: Mixed Reality-Enhanced Active Constraint Generation and Impedance Control for Human–Robot Co-Manipulation（新規） | Wang, Xiao, Lin, Chen ほか. IEEE T-ASE 2026 | MR で制約を作り、インピーダンス制御で共同操作する | − | [DOI](https://doi.org/10.1109/TASE.2026.3683134) |
| From BIM to Executable Spatial Media: Action Skill Graphs for Zero-Code Assembly with Cable-Driven Parallel Robots（新規） | Wang, Jiang, Búš. ACM MM 2026 | BIM と MR の重ね合わせから実行可能なグラフを作り、ケーブル駆動ロボットを動かす | − | [DOI](https://doi.org/10.1145/3767308.3832550) |
| Evaluating Task Optimization and Reinforcement Learning Models in Robotic Task Parameterization（新規） | Delledonne, Villagrossi, Beschi, Rastegarpanah. IEEE Access 2024 | 産業用ロボットのタスクパラメータ最適化 | − | [DOI](https://doi.org/10.1109/ACCESS.2024.3504354) |
| Intuitive, Low-Cost Cobot Control System for Novice Operators, Using Visual Markers and a Portable Localisation Scanner（新規） | George, Cheng, Pang. Machines 2026 | 視覚マーカーを使う初心者向けの協働ロボット操作 | − | [DOI](https://doi.org/10.3390/machines14020201) |
| MKT-GMM: A Motion Knowledge Transferring Framework for Robot Trajectory Adaptation to Variable Via-Points（新規） | Ye, Wu, Luo, Li ほか. Biomimetics 2026 | 実演から学んだ軌道を経由点の変化に適応させる | − | [DOI](https://doi.org/10.3390/biomimetics11050351) |
| Augmented reality and robotics in education: A systematic literature review（新規） | Pasalidou, Lytridis, Tsinakos, Fachantidis. Comput. Hum. Behav. Artif. Humans 2025 | 教育分野の AR とロボットのレビュー。題名のみ【未検証】 | − | [DOI](https://doi.org/10.1016/j.chbah.2025.100157) |
| Immersive Technologies (AR/VR) for Computer Science and Computational Thinking Education: A Systematic Literature Review of Trends and Gaps（新規） | Jang, Jeon, Jung. IEEE Access 2026 | 計算機科学教育での AR/VR のレビュー | − | [DOI](https://doi.org/10.1109/ACCESS.2026.3680395) |
| Impact of Augmented Reality on Actual Purchase Behavior: The Role of Customer Brand Engagement and Purchase Intention（新規） | Akram, Nasir, Asghar, Majid. J. Global Social Transformation 2026 | 消費者行動の研究で、ロボットとは無関係 | − | [DOI](https://doi.org/10.71317/jgst.2.9(s2).2026.653) |

### 一覧から分かること

- **家庭の片付けや、家庭ルール・規範の違反表示を主題にした後続論文は、この 43 件の中にはない。** 産業用の協働ロボットのプログラミングが多数を占める。
- **MARCER の後続は 2 方向に分かれている。** 物体を直接操作する AR（GhostObjects、X-OOHRI、Reality Promises。いずれも Abtahi のグループ）と、LLM が作った計画やプログラムを検査して直す非 AR の系（RoboCritics、SHRIMP、HRI Grounding、Bootstrapping）である。この一覧の中に、両者をつなぐ後続は見当たらない。
- **MARCER が自ら課題に挙げた「失敗の伝達」に AR で取り組んだ後続は、この一覧では X-OOHRI だけ**で、対象は物理的な実行可能性に限られる。
- **会話でルールを作るときの誤りと回復**を扱う Carcangiu らの 2026 年の論文は、題名からはルール作成段階のエラーに最も近い。内容は未確認なので、原典を読む優先度が高い。
