# D. 現行 CoGround ルール設計の内部監査（何が書けて、何が照合でき、何が見えるか）

調査日 2026-11-22。ローカルのコードと文書だけを読んだ（Web なし、テスト実行なし、リポジトリは無変更）。
「事実」はコード・文書の行番号つきで Cited Findings に、「私の判断」は Inferences に分けた。行番号は各ファイルの `cat -n` の番号。
出典の略記（すべてローカルファイル。リンク定義は末尾）: `voc`=norms/vocabulary.py、`model`=norms/model.py、`pred`=norms/predicates.py、`eval`=norms/evaluate.py、`attr`=norms/attributes.py、`plan`=norms/planner.py、`mon`=norms/monitors.py、`rep`=norms/report.py、`task`=norms/task.py、`dep`=norms/depends.py、`guide`=Documents/CoGround_Home_Rules.md（設計ガイド）、`compile`=llm/compile_rule.py。

---

## 1. 実装されているルールモデルは正確には何か（枠・語彙・3 値・どの段階で何を調べるか・アプリに渡る報告）

### Takeaway
ルールは「原文 + 規範・条件（Scope）・対象（Target）・内容（Requirement）」で、内容 7 語・条件 4 語が登録簿にある。ただし表現力を実際に決めているのは登録簿の外にある 3 つの固定構造、すなわち **対象が「属性 = 値」1 個だけ**、**時刻が HH:MM の窓だけ**、**依頼者が人物 ID の一致だけ**、である。計画時に調べているのは「つかむ時点」「置いた時点」「経路の領域進入」の 3 つだけで、速さ・停止の内容は実行時の監視でしか評価されない。

### Cited Findings
**枠**
- ルール 1 件 = `id, author, original_text, norm, scope, target, requirement, reason, exception_of, origin, source, attributes` — [model.py:229-247][model]。`reason` は判定に使わない — [model.py:237][model]。
- 規範は `obligation / prohibition / permission` の 3 つ — [model.py:31][model]。許可は単独では常に `not_applicable` を返し、`exception_of` を持つときだけ元の禁止の適用範囲を狭める — [evaluate.py:81-82, 98-111][eval]、[model.py:249-253][model]。
- 条件 Scope = 時刻の窓 `from/until`（HH:MM、日またぎ可）+ `requester`（人物 ID の一致）+ `when`（状態の条件）— [model.py:101-152][model]。`when` は述語 1 個、AND（`all`）、NOT（`negate`）。OR は無い — [model.py:74-98][model]、[guide:117][guide]。
- 対象 Target = `kind`（object / zone / robot）、`id`（個体）、`where`（属性 = 値を 1 個）、`unknown_as`、`fallback` — [model.py:155-186][model]。`where` の型 `RuleCondition` は「属性 = 値だけ」と明記 — [models.py:236-248][models]。読める属性は `category / group / role` と `attributes` のキーだけ（`region_id` は読めない）— [models.py:135-140][models]。
- 内容 Requirement = `predicate`（語彙の名前）+ `args`。評価区間 W と transition は内容の性質として語彙が持つ — [model.py:198-213][model]、[guide:86][guide]。

**語彙の登録簿（内容 7 語 + 旧名 1）** — [vocabulary.py:68-124][voc]

| 内容 | 読む状態 | 対象の種類 | 調べる時点（checked） | 実行中の応答 |
|---|---|---|---|---|
| contact | contact | object | grasp | （無し） |
| holding | holding | object | grasp | （無し） |
| placed_in(region) | object_region | object | place | （無し） |
| enter_zone | base_pose, zone_shape | zone | motion（外→内の変化） | replan |
| in_zone | base_pose, zone_shape | zone | motion | replan |
| base_stopped | base_speed | robot | motion | hold |
| speed_below(limit) | base_speed | robot | motion | hold |

**条件 4 語（+ 旧名 near_child）** — [vocabulary.py:126-156][voc]: `near_person(kind, distance)`（台車から人まで）、`holding_something`、`base_in_zone(zone)`、`region_full(region)`。人の種類は `child / adult / unknown` の 3 値だけ — [models.py:165][models]。

**ROBOT_STATES** は 5 項目を手で列挙: `base_pose, base_speed, contact, holding, object_region` — [vocabulary.py:36-42][voc]。`coverage()` は「列挙した各状態を `reads` に含む内容が 1 つ以上あるか」を返すだけ — [vocabulary.py:197-199][voc]、テストは 7 語の名前の集合を固定で確認 — [test_vocabulary.py:55-60][tvoc]。

**3 値評価**
- Kleene の and3 / or3 / not3 — [model.py:48-63][model]。
- 適用 `A = S ∧ T ∧ ¬例外`、違反は禁止 `A ∧ φ`、義務 `A ∧ ¬φ`。結果は `violated / undetermined / compliant / not_applicable`、未確定は `missing`（足りない事実）つき — [evaluate.py:3-11, 107-144][eval]。
- 対象条件の属性に値が無い物体は「不明」（`unknown_as="unknown"`）。`unknown_as="false"` なら非該当とみなす — [model.py:183-186][model]。

**どの段階で何を調べるか**
- 計画（依頼の行ごと）: ①収納先 = `placed_in` の義務のうち Scope と対象の両方に合うもの、②つかむ時点の予測で `checked ∋ grasp` の物体ルール、③置いた時点の予測で `checked ∋ place` かつ収納先を決めないルール（「…には置くな」）、④動作計画が返した経路ブロック — [planner.py:3-13, 59-64, 119-154][plan]。
- つかむ時点の予測状態は `contact={obj}, holding={obj}` の 1 サンプルだけ（台車位置・人・領域は入らない）— [evaluate.py:28-30][eval]。
- 経路の計画時判定は **領域進入の禁止だけ**（`is_zone_entry` で絞る）— [monitors.py:97][mon]、呼び出しは [motion.py:474][motion]。`base_stopped / speed_below` を計画時に評価するコードは無い。
- 実行時: `monitored()` = 内容が motion で調べるもの、または条件が台車の位置・速さを読むもの。応答は replan（領域）か hold（それ以外）— [monitors.py:49-76][mon]。
- 設計ガイドは R4 の計画時の判断を「予測できる接近には待機・迂回を入れる」と書いている — [guide:253][guide]。

**アプリに渡る報告**
- Plan の step: `status`（ok / ambiguous / unmatched / infeasible / deferred）、`to`、`rule_id`、`candidate_rule_ids`、`message`、`verdicts`（時刻を落とした判定）— [models.py:346-373][models]。
- 依頼の報告 `build_report`: 行ごとに `exec_state, destination, sentence, reasons（not_applicable は除く）, route, missing, judgments, holds`、全体の `counts / summary / corrections` — [report.py:28-68][rep]。
- `judgments`: 物体 × 「物体が対象で、id か where を持つ」ルールの対象条件の照合結果（true / false / null、属性・期待値・実際の値・出どころ・確信度）— [report.py:75-107][rep]。state には運ぶ物（role = item）全部について入る — [state.py:381-384][state]。
- 語彙 `export()`（phrase, targets, checked, response）も state に入り、Unity は名前を自前で持たない — [vocabulary.py:242-255][voc]。
- Unity 側: `StepDto.Verdicts`、`VerdictDto`、`MissingFactDto` — [CoGroundPlanTypes.cs:58-88][ptypes]。After 表示は deferred / ambiguous / unmatched / infeasible の物体を残して理由ラベルを出す — [CoGroundAfterView.cs:12-26][after]。吹き出しは違反 → 禁止（赤）、未確定 → 判断できない（黄）、どちらも無ければ `step.Message` — [CoGroundRuleTagView.cs:415-446][tag]。実行中の hold と避けている領域は別の状態表示 — [CoGroundHomeStatus.cs:11-14][home]。

### Inferences
- 「4 枠 + 登録簿」という説明は、**内容と条件の述語**については正しいが、表現力の上限の多くは登録簿の外（Target、Scope の時刻と依頼者、人の種類の列挙）にある。「内容を足すのは登録簿 1 件だけ」は真でも、「書けるルールを広げるのは登録簿 1 件だけ」は真ではない。
- 設計ガイド §7 の R4 の計画時の扱い（待機・迂回を入れる）は、読んだコードには対応する実装が無い。文書とコードのずれ。

### Gaps
- `SYSTEM_OVERVIEW.md` と 2 つの README は、ルールモデルについては `planner.py: ルール → Plan` 程度の記述で、枠や範囲の定義は設計ガイドにしか無かった（README 888 行は全文を読んでいない。grep のみ）。
- 知覚パイプラインは VLM の答えを文字列（"unknown" など）で記憶に入れる — [pipeline.py:219-222][pipe]。これが `SceneObject.attributes` の型つきの値（True / False / 無し）にどこで直るかは、読んだ範囲では見つからなかった。文字列 "unknown" のまま届くと `"unknown" == True` は偽で「非該当」になるので、要確認。

---

## 2. 「ロボットが変えられる状態のすべてについて規範を書ける」は成り立つか。範囲の定義として良いか

### Takeaway
主張は「手で列挙した 5 状態について」しか成り立たず、検査（coverage）は列挙に対する同語反復である。実際に内外を分けている基準は「ロボットが変えられるか」ではなく「**シミュレータの状態ベクトルに、真偽を返せる変数があるか**」であり、その結果、速さは入って騒音は出る、接触は入って「丁寧に」は出る、という恣意的に見える境界になっている。

### Cited Findings
- 設計ガイドの主張:「ロボットが変えられる状態のすべてについて、住人が規範を書ける」「網羅しているかは機械的に確かめられる」— [guide:102][guide]。範囲の定義:「ロボットが変えられる状態について、観測できる条件の下で、要求または禁止するルール」— [guide:340][guide]。
- ROBOT_STATES は辞書リテラルで、スキル定義から導出していない — [vocabulary.py:36-42][voc]。`SKILL_CHANGES` も別の手書き表 — [depends.py:26-30][dep]。
- 範囲外として明記されているもの: 測れない様態（静かに・丁寧に）、順序・回数、好み・重み、例からの学習、画像から分からない属性の認識、腕や搬送物の副作用 — [guide:342-349][guide]。
- 「静かに」は `quiet` という内容が無いので未対応を返す。テストで確認 — [test_vocabulary.py:260-276][tvoc]。
- つかむ時点の予測では contact と holding が常に同じ集合になる — [evaluate.py:30][eval]。
- `speed_below` を破りそうなときの応答は減速ではなく停止 — [guide:353][guide]、[vocabulary.py:112-113][voc]。

### Inferences
- **列挙から漏れている「ロボットが変えられる状態」**: 腕・手先の軌道、搬送物の姿勢（傾き）、領域内での置き位置・向き、把持の力、音、カメラの向き・記録の有無、動作する時間帯そのもの。これらは pick / place / navigate が実際に変えるが ROBOT_STATES に無い。したがって「すべて」は列挙に対してのみ真。
- **本当の基準は可観測性**: 速さは `base_speed` という変数があるので入る。騒音は変数が無いので出る。「丁寧に」は加速度や把持力という変数を用意すれば入る。基準が「変えられるか」でなく「シミュレータが数値を持つか」なら、そう書いた方が正直で、境界の説明もつく。
- **contact と holding は、いまのスキルでは独立に変えられない**（pick は必ず両方を真にする）。5 状態のうち実質は 4。「触ってよいが運ぶな（押すのは可）」は語彙上は書けるが、判定結果は contact の禁止と区別できない。
- **内容の語彙は「状態」由来だが、条件の語彙には導出原理が無い**。near_person・holding_something・base_in_zone・region_full は、デモの R4 と「満杯なら赤い箱」から逆算して足したものに見える。外界の状態（人がどの部屋にいるか、物がどこにあるか、曜日）についての条件は無い。
- この基準は**住人が言いたいことの分布**と噛み合っていない。§3 の結果では、書けない理由の大半は内容ではなく、対象・条件・人の状態・履歴にある。範囲を内容の側（ロボットの状態）から定義しても、住人から見た「どんなルールが書けるか」は説明できない。
- 範囲の定義として残すなら、「ロボットの状態」ではなく §9 の案のように、**見えるもの（After で物体に付くか）と、知る必要があるもの（どの事実が要るか）**で切る方が、AR の主張と一致する。

### Gaps
- 「ロボットが変えられる状態」基準の出どころ（どの文献に基づくか）は設計ガイドに書かれていない。IG 2.0 は 4 枠の根拠であって、内容の語彙の根拠ではない — [guide:13-24][guide]。

---

## 3. カバレッジテスト: 具体的な家庭ルール 90 件を現行モデルに入れてみる

### Takeaway
90 件のうち、そのまま書けるのは 33 件、住人の属性登録・領域定義・人数分のルール展開を前提にすれば書けるのが 11 件、登録簿に 1 件足せば書けるのが 7 件、書けないのが 39 件。リポジトリ由来の 23 件を除いた 67 件（文献 + 構成例）では 19 / 10 / 5 / 33 で、**安全（物と場所）と立入は大半が書け、所有と倫理は住人による登録・展開が前提、片付けは 8 件中 3 件、マナーとプライバシーは 8 件中 2 件、衛生は 0 件**。書けない理由は内容の語彙より、人の状態、対象の構造（場所で選ぶ・AND）、2 物体の関係、履歴、様態、尋ねる・発話、センシングに集中する。

### Cited Findings
判定の記号: **A** = そのまま書ける / **A+** = 書けるが、住人の属性登録・領域の事前定義・人数分や領域数分のルール展開が要る / **B** = 登録簿に 1 件足せば書ける（何を足すかを記す）/ **C** = 書けない（理由を記す）。
「見え方」: **物** = After で物体が動く・残る（物体にラベル）/ **経** = 経路だけが変わる（最終状態は同じ）/ **実** = 実行中だけ / **無** = 表示に出ない。
出典: (a) リポジトリのテスト・設計ガイド、(c) AR 文献調査、(b) 調査 README の領域ごとに私が作った構成例（**構成例**と明記。実在の住人の発話ではない）。

**(a) リポジトリ内のルール（23 件）** — 出典: [test_norms.py:20-39][tnorms]、[test_home_rules.py:27-39, 419][thome]、[test_vocabulary.py:187-189, 239, 260-298][tvoc]、[test_rule_registration.py:73, 112-121][treg]、[guide:119-124, 178, 202, 342-349][guide]

| # | ルール | 判定 | 符号化 / 書けない理由 | 見え方 |
|---|---|---|---|---|
| 1 | 割れ物に触るな（R1） | A | 禁止・fragile=true・contact | 物 |
| 2 | 18 時以降この辺りに入るな（R2） | A | 禁止・18:00〜・zone・enter_zone（until 未確定なら登録の途中） | 経 / 道が無ければ物 |
| 3 | 皿は上段（R3a） | A | 義務・category=plate・placed_in | 物 |
| 4 | コップは下段（R3b） | A | 同上 | 物 |
| 5 | 子供の 5 m 以内では止まれ（R4） | A | 義務・near_person(child,5)・robot・base_stopped | 実 |
| 6 | 私が頼んだときは触ってよい（P1） | A | 許可・requester・exception_of | 物 |
| 7 | 文房具は白い箱、満杯なら赤い箱 | A | 義務 ×2・region_full の NOT / 正 | 物 |
| 8 | このペンを赤い箱に入れるな | A | 禁止・id・placed_in | 物 |
| 9 | パパの物に触るな | A+ | owner=papa（visual=false。住人が物体ごとに登録） | 物 |
| 10 | 18 時以降は割れ物に触るな（R1e） | A | 禁止・18:00〜・fragile | 物 |
| 11 | 食器はシンクへ | A | group=dish・placed_in | 物 |
| 12 | それ以外は箱へ | A | fallback | 物 |
| 13 | 全部 box_1 に（依頼の間だけ） | A | origin=task | 物 |
| 14 | 何か持っているときは 0.3 m/s 以下 | A | 義務・holding_something・speed_below（計画時は未確定） | 実 |
| 15 | この領域の中にいるな | A | in_zone | 経 / 物 |
| 16 | ゆっくり動け（上限なし） | C | 引数不足で未対応（数値を言えば A） | — |
| 17 | 静かに運べ | C | 様態。真偽を返す状態が無い | — |
| 18 | 丁寧に扱え | C | 様態 | — |
| 19 | 先に皿を片づけろ | C | 順序（シーケンス編集で代替） | — |
| 20 | 一度に 2 つまで | C | 数量 | — |
| 21 | できれば上段に | C | 好み・重み | — |
| 22 | 雨のときは触るな | B | 条件 raining（外部センサが要る） | 物 |
| 23 | カーペット上では吸引しない | B | 状態 suction + 内容 1 件（スキルが無い） | 実 |

**(c) AR 文献調査に出てくるルール・制約（15 件）** — 出典: MRPilot の 2 場面 [文献調査:18][arrep]、X-OOHRI [文献調査:76-78][arrep]、MARCER [文献調査:9, 98][arrep]、表の実行時の例 [文献調査:59][arrep]、調査 README の手法の例 [README:224, 243-244, 250][survey]

| # | ルール | 判定 | 符号化 / 書けない理由 | 見え方 |
|---|---|---|---|---|
| 24 | PRIVATE と記された部屋に入らない（MRPilot） | A | 禁止・zone・in_zone | 経 / 物 |
| 25 | 同、その場で進入の許可を尋ねる | C | 「尋ねる」は規範 3 種に無い。許可は事前登録の例外だけ | — |
| 26 | Jim は仕事中に邪魔されたくない（MRPilot） | C | 人の状態（仕事中）と「邪魔」の定義が無い。時刻つきの部屋進入禁止で近似すると意味が変わる | — |
| 27 | 高すぎて届かない（X-OOHRI） | C | ルールではなく物理的な実行可能性。モデルの外（status=infeasible で別に扱う） | 物 |
| 28 | 大きすぎて持てない / 向きが悪くつかめない（X-OOHRI） | C | 同上 | 物 |
| 29 | コップがコースターに置かれたらシンクへ運ぶ（MARCER 型の trigger-action。構成例） | C | 他者が起こすイベントが引き金。ルールは作業を生成しない（収納先を決めるだけ） | — |
| 30 | 赤い仮想の柵の中に入らない（Hietanen） | A | in_zone | 経 / 物 |
| 31 | 危険な場所に近づかない（RoboGuard） | A+ | 余白込みで領域を定義すれば in_zone。「d m 以内」を直接書くなら B | 経 |
| 32 | プライバシーを尊重する（RoboGuard） | C | 抽象的。状態に落ちない | — |
| 33 | 水の入ったコップをノート PC の上で運ばない（Semantically Safe） | C | 2 物体の関係 + 搬送物の軌道。副作用は範囲外と明記 | — |
| 34 | 客がいるときは掃除機をかけない（GRACE） | C | スキルが無い + 人の種類（客）が無い | — |
| 35 | バーチャルな境界線の外に出ない | A | in_zone（外側を領域にする） | 経 |
| 36 | 人が近づいたら止まる（安全ゾーン） | A | near_person(any, d)・base_stopped | 実 |
| 37 | 力が上限を超えたら止まる | C | 力の状態が無い（B にするには状態の追加が要る） | — |
| 38 | 持ち主の命令と他人の利益がぶつかったら… | C | ルール間の優先順位が無い | — |

**(b) 構成例（52 件。調査 README の 8 領域 [README:25-32][survey] に沿って私が作った。実在の発話ではない）**

| # | 領域 | ルール（構成例） | 判定 | 符号化 / 書けない理由 | 見え方 |
|---|---|---|---|---|---|
| 39 | マナー | 夜 10 時以降は寝室に入らない | A | 禁止・22:00〜・zone | 経 / 物 |
| 40 | マナー | 夜 10 時以降は 0.2 m/s 以下で動く | A | 義務・時刻・speed_below | 実 |
| 41 | マナー | 人の 1 m 以内に近づかない | B | 内容 keep_distance（base と人の距離。near_person は条件でしか使えない） | 経 |
| 42 | マナー | 客がいるときはリビングに入らない | B | 条件 person_in_zone + 人の種類に guest（列挙の変更も要る） | 経 / 物 |
| 43 | マナー | 食事中はテーブルの物を片づけない | C | 人の状態（食事中）+ 場所で対象を選ぶ | — |
| 44 | マナー | テレビを見ている人の前を横切らない | C | 人の向き・状態。領域で近似すれば A | — |
| 45 | マナー | 人とすれ違うときは道を譲る | C | 相互作用・意図 | — |
| 46 | マナー | 物を取る前に声をかける | C | 発話は状態に無い + 順序 | — |
| 47 | プライバシー | 書斎には入らない | A | zone | 経 / 物 |
| 48 | プライバシー | 書類・郵便物は動かさない | A | 禁止・category・contact | 物 |
| 49 | プライバシー | 書斎の机の上の物には触らない | C | 場所で対象を選べない（Target は属性 = 値だけ）。物体ごとに属性を登録すれば A+ | — |
| 50 | プライバシー | 誰かが浴室にいるときは浴室に入らない | B | 条件 person_in_zone | 経 |
| 51 | プライバシー | 着替え中の部屋に入らない | C | 人の状態 | — |
| 52 | プライバシー | カメラを人に向けない・撮影しない | C | センシングは状態に無い | — |
| 53 | プライバシー | 引き出しを開けない・中を見ない | C | スキルが無い + センシング | — |
| 54 | プライバシー | 見たものを来客に話さない | C | 情報の流れ | — |
| 55 | 安全 | 包丁には触らない | A | category=knife | 物 |
| 56 | 安全 | 薬は戸棚の上段に | A | 義務・category・placed_in | 物 |
| 57 | 安全 | 子供が近くにいるときは刃物を運ばない | A | 禁止・near_person(child)・holding。ただしつかむ時点の予測に人の位置が入らないので計画時は常に未確定 → 保留 | 物（未確定で残る） |
| 58 | 安全 | 熱い飲み物は運ばない | A+ | 属性 hot（画像で分かるか怪しい。住人登録） | 物 |
| 59 | 安全 | コンロの周りに近づかない | A | zone | 経 |
| 60 | 安全 | 階段の近くでは 0.2 m/s 以下 | A | 義務・base_in_zone・speed_below | 実 |
| 61 | 安全 | 重い物は高い棚に置かない | A+ | 禁止・heavy（住人登録）・placed_in を棚の数だけ | 物 |
| 62 | 安全 | 液体入りのコップは傾けない | C | 様態（姿勢）。状態に無い | — |
| 63 | 安全 | ペットが近くにいるときは止まる | B | near_person の kind に pet（人の種類の列挙も変更） | 実 |
| 64 | 安全 | 床に物を置かない | A+ | 床が領域として定義されていれば 禁止・placed_in | 物 |
| 65 | 倫理 | 家族以外の依頼では物を動かさない | A+ | 全物体の contact 禁止 + 家族 1 人ずつの許可（requester は ID の一致だけ） | 物 |
| 66 | 倫理 | 子供に頼まれても薬は動かさない | A+ | 薬の contact 禁止 + 大人 1 人ずつの許可 | 物 |
| 67 | 倫理 | 祖母が自分でやりたいことは手伝わない | C | 人の意図 | — |
| 68 | 倫理 | できない理由を必ず説明する | C | 発話（ただしシステムの固定動作として実現済み） | — |
| 69 | 倫理 | 持ち主の許可なく捨てない | A+ | ごみ箱への placed_in 禁止 + 持ち主ごとの許可（持ち主 = 依頼者という関係は直接書けない） | 物 |
| 70 | 倫理 | 命令がぶつかったら父を優先 | C | 優先順位・メタルール | — |
| 71 | 片付け | 本は本棚に | A | 義務 | 物 |
| 72 | 片付け | 汚れた食器はシンク、きれいな食器は棚 | C | 対象の AND（group=dish ∧ dirty）が書けない。dirty=true だけにすると食器以外も入る | 物 |
| 73 | 片付け | リモコンはテーブルに残す | A | 禁止・category・contact | 物 |
| 74 | 片付け | 私のコップは左、妻のコップは右 | C | 対象の AND（category=cup ∧ owner）。owner だけにすると全持ち物が動く | 物 |
| 75 | 片付け | ラベルを前に向けて置く・大きい順に並べる | C | 領域内の姿勢・並び。placed_in は領域単位 | — |
| 76 | 片付け | 同じ種類はまとめて置く | C | 2 物体の関係 | — |
| 77 | 片付け | 棚には 3 つまで | B | 条件 region_count（region_full は幾何の空きで近似するだけ） | 物 |
| 78 | 片付け | 使いかけのペットボトルは捨てない | A | 属性 trash=false（語彙に既にある） | 物 |
| 79 | 所有 | 各自の物は各自の部屋へ | A+ | 人数分の義務（owner=X → X の部屋） | 物 |
| 80 | 所有 | 他人の物は持ち主に聞いてから動かす | C | 「聞く」が無い。禁止 + 許可で静的に近似 | — |
| 81 | 所有 | 借りた物は元の場所に戻す | C | 履歴（元の場所） | — |
| 82 | 所有 | 子供の作品は捨てない | A+ | 属性（住人登録）+ ごみ箱への placed_in 禁止 | 物 |
| 83 | 所有 | 形見の時計は動かさない | A+ | 個体 id（登録時にシーンに居る必要。id の持続は未確認） | 物 |
| 84 | 立入 | ベランダに出ない | A | zone | 経 / 物 |
| 85 | 立入 | 玄関マットの上で止まらない | A | 禁止・base_in_zone・base_stopped。ただし応答が内容で固定の hold なので、禁止と矛盾する | 実 |
| 86 | 立入 | 狭い廊下で人が近くにいたら止まって待つ | A | 義務・AND(near_person, base_in_zone)・base_stopped | 実 |
| 87 | 立入 | 赤ちゃんが寝ている間は子供部屋に入らない | C | 人の状態。時刻の窓で近似すれば A | — |
| 88 | 衛生 | 床に落ちていた物は食卓に置かない | C | 場所で対象を選ぶ + 履歴 | — |
| 89 | 衛生 | 生ごみを触ったあとは、そのまま食器に触らない | C | 履歴（接触の順序） | — |
| 90 | 衛生 | 汚れた物ときれいな物を同じ箱に入れない | C | 2 物体の関係 | — |

**集計**（表の記号を数えた。A には A+ を含まない）

| 範囲 | 件数 | A | A+ | B | C |
|---|---|---|---|---|---|
| (a) リポジトリ | 23 | 14 | 1 | 2 | 6 |
| (c) 文献 | 15 | 4 | 1 | 0 | 10 |
| (b) 構成例 | 52 | 15 | 9 | 5 | 23 |
| 合計 | 90 | 33 | 11 | 7 | 39 |

リポジトリ以外の 67 件では A 19 / A+ 10 / B 5 / C 33（表の行を機械的に数えた）。

構成例 52 件の領域別（A / A+ / B / C）: マナー 2 / 0 / 2 / 4、プライバシー 2 / 0 / 1 / 5、安全 5 / 3 / 1 / 1、倫理 0 / 3 / 0 / 3、片付け 3 / 0 / 1 / 4、所有 0 / 3 / 0 / 2、立入 3 / 0 / 0 / 1、衛生 0 / 0 / 0 / 3。

**C（39 件）の理由の内訳**（1 件に主な理由を 1 つ）: 人の状態・意図 6（#26, 43, 44, 51, 67, 87）／ 尋ねる・発話・相互作用 5（#25, 45, 46, 68, 80）／ 様態・姿勢・並び 4（#17, 18, 62, 75）／ 対象の構造（場所で選ぶ・AND）4（#49, 72, 74, 88）／ センシング・情報・抽象的 4（#32, 52, 53, 54）／ 2 物体の関係 3（#33, 76, 90）／ 順序・数量・好み 3（#19, 20, 21）／ 履歴 2（#81, 89）／ 優先順位 2（#38, 70）／ スキルや状態が無い 2（#34, 37）／ ルールではない（物理的な実行可能性）2（#27, 28）／ 作業の生成 1（#29）／ 引数不足 1（#16）。

符号化の根拠: 対象が属性 = 値 1 個だけ — [models.py:236-248][models]；場所（region_id）は対象条件で読めない — [models.py:135-140][models]；requester は ID の一致 — [model.py:149-152][model]；人の種類 — [models.py:165][models]；内容に使えるのは CONTENTS だけ（条件の語は内容にできない）— [vocabulary.py:202-206][voc]；個体 id は登録時にシーンに無いと未対応 — [compile_rule.py:257-259][compile]；応答は内容ごとに固定 — [vocabulary.py:105-117][voc]。

### Inferences
- **領域別の入り方**（構成例、私の判断）: 安全（物と場所に関するもの）と立入は大半が A / A+。所有と倫理は A が 0 で、書けるものはすべて住人の登録・人数分の展開が前提（A+）。片付けは 8 件中 A が 3 件にとどまり、対象の AND・領域内の並び・2 物体の関係で落ちる。マナーとプライバシーは 8 件中 2 件（どちらも時刻つき・常時の部屋進入禁止だけ）、衛生は 0 件。調査 README の本数で最大の 3 領域（マナー 41 本、プライバシー 29 本、安全 27 本）のうち 2 つがほぼ範囲外になる。「家庭のルール一般を扱う」とは言えない。
- **B は少ない（7 件）**。「登録簿に 1 件足せば広がる」という拡張性の主張は、このサンプルではあまり効かない。足りないのは語彙ではなく構造（Target の表現力、人の状態、履歴、関係）である。
- **片付けという中心タスクの中でも落ちる**ものがある（#72「汚れた食器はシンク、きれいな食器は棚」、#74「私のコップは左」）。対象条件の AND が無いことは、範囲外と宣言していない欠落で、住人が最初に言いそうな文で当たる。
- **A+ の 11 件は、住人の負担で成立している**。持ち主・重さ・形見は物体ごとに手で登録し、「家族」「各自」は人数分のルールに展開する。「書ける」と「使える」の間に差がある。
- 集計は私 1 人が作った例に対するもので、実在の住人の発話の分布ではない。割合そのものに意味は無く、**書けない理由がどの次元に集中するか**だけを読むべきである。

### Gaps
- 調査 README が挙げる中心論文（ASIMOV、NormAct、MANNERS-DB、SafeAgentBench、RobotValues）の本文中の実ルールは未読（README 自身が「本文は読んでいない」と明記 — [README:88][survey]）。実在のルールでの再テストが要る。
- LLM（`norms.compile`）が A のルールを実際に正しく 4 枠に落とせるかは、テストが FakeLlm を使っているため未検証 — [test_vocabulary.py:255-258][tvoc]。ここでの「書ける」は「表現として存在する」の意味。

---

## 4. 違反はどこに現れるか: 物体単位 / 動作単位 / 見えない（内容 7 語それぞれ）

### Takeaway
After（最終状態）に現れるのは「物が動いたか・残ったか・どこに着いたか」だけなので、物体に付く結果を生むのは contact・holding・placed_in の 3 語と、**迂回路が見つからなかったときの**領域進入だけである。迂回が成功した領域進入、base_stopped、speed_below は最終状態を変えないので、Before/After には原理的に出ない。

### Cited Findings

| 内容 | 規範 | 計画時の結果 | Before/After での見え方 | 根拠 |
|---|---|---|---|---|
| contact | 禁止 | つかむ時点の予測で violated → step が deferred、行は保留 | **物体が元の場所に残り、ラベル「R1 に反するので残す」** | [planner.py:119-125][plan]、[CoGroundRuleTagView.cs:425-430][tag] |
| contact | 禁止（属性が不明） | undetermined → deferred、missing つき | 物体が残り、「足りない情報: fragile」 | [planner.py:126-128][plan]、[CoGroundRuleTagView.cs:433-441][tag] |
| holding | 禁止 | contact と同じ予測状態で評価 | contact と同じ（区別できない） | [evaluate.py:28-30][eval] |
| placed_in | 義務 | 収納先を決める。複数の義務が別の先を指すと ambiguous | 物体が置き先に現れる（元は薄く）。競合なら残って「行き先が決まらない」 | [planner.py:255-313][plan]、[CoGroundAfterView.cs:13-22][after] |
| placed_in | 禁止 | 決まった収納先がその領域なら violated → deferred。別の置き先は探さない | 物体が残り、ラベル | [planner.py:129-142][plan] |
| enter_zone / in_zone | 禁止 | 経路を判定 → 違反なら領域を避けて計画し直す | **迂回成功: 最終状態は同じ。After には何も出ない**（避けた領域は行の route と実行状態表示の keepout に残る） | [motion.py:15-20, 383-405][motion]、[task.py:53-54][task]、[CoGroundHomeStatus.cs:12][home] |
| enter_zone / in_zone | 禁止 | 迂回路なし → route block → 行は保留 | 物体が残り、「…に反しない経路が無い」 | [planner.py:143-154][plan]、[report.py:123-124][rep] |
| base_stopped | 義務 | **計画時は評価しない**（経路の判定は領域進入だけ） | 出ない。実行中に HOLD 表示 | [monitors.py:97][mon]、[CoGroundHomeStatus.cs:11][home] |
| speed_below | 義務 | 同上 | 出ない。実行中に HOLD（減速ではなく停止） | 同上、[guide:353][guide] |

- 条件 `holding_something` を持つ領域ルールは、動作計画が把持状態を渡さないので計画時に未確定になる — [guide:354][guide]、`route_verdicts` の呼び出しに holding 引数が無い — [motion.py:474-475][motion]。未確定は違反と同じ扱いで領域を避ける — [motion.py:383][motion]。
- 条件 `near_person` を持つ物体ルール（#57）は、つかむ時点の予測状態に人も台車位置も無いので未確定になる — [evaluate.py:28-30][eval]、[predicates.py:86-87][pred]。
- step の判定からは時刻が落とされる — [models.py:338-340][models]。

### Inferences
- 7 語を「見えるもの」で分けると 3 群になる。**(i) 物体に付く**: contact、holding、placed_in。**(ii) 床と経路に付く**: enter_zone、in_zone（迂回が成功したとき）。**(iii) 時間の中にしか無い**: base_stopped、speed_below。提案中の「違反する物体は消さずに残してラベル」は (i) と、(ii) の失敗時だけを覆う。
- (ii) で迂回が成功した場合、ルールは確かに計画を変えたのに、Before/After では**ルールが効いたことが見えない**。「計画のどこに効いたかを住人が確認できる」という設計ガイドの問い（[guide:11][guide]）に対して、最終状態の比較だけでは答えられない部分がここにある。
- (iii) は、プレビューの段階では住人に何も見せられない。計画時に評価していないので、「このルールは今回は関係しなかった」のか「実行中に効くはず」なのかも区別して出せない。
- 「物体に付く結果」を生む原因は少なくとも 6 通りある（禁止の違反、属性が不明、行き先の競合、行き先を決めるルールが無い、迂回路なし、物理的に不可）。X-OOHRI が扱うのは最後の 1 つだけ（[文献調査:78][arrep]）なので、規範由来の 5 通りを物体ラベルで区別して見せることは、表示設計の中身として残る。
- After は「いまの時計」での予測である。17:55 に見た After と 18:02 に見た After は違いうるが、step の判定に時刻が残らないので、**いつまで有効なプレビューか**を表示側は知らない。

### Gaps
- Unity の CoGroundPlanView が経路そのもの（台車の軌跡）と避けた領域を Before 側でどう描くかは、ヘッダのコメント（弧とゴースト）しか読んでいない。経路上に「R2 のため迂回」を出す実装があるかは未確認。

---

## 5. 属性はどこから来るか、「不明」はどう表され、対象の照合は定義できているか

### Takeaway
対象は自由文ではなく「個体 id」か「属性 = 値 1 個」で、照合そのものは等値比較として明確に定義されている。曖昧さは照合の手前に寄せられている。すなわち、(1) 自由文 →（属性名, 値）への変換を LLM に任せる段階、(2) 属性名・値の表記ゆれが黙って「非該当」になること、(3) 場所・関係・持ち主と依頼者の対応のように、属性 = 値で書けない対象。

### Cited Findings
- VLM への質問は、ルールの `target.where` が使う属性から作る。`category / group / role` は属性ではないので聞かない — [attributes.py:19, 26-52][attr]。`visual=false` の属性は質問から外す — [attributes.py:55-57][attr]。
- 属性の定義（見分け方・選択肢・visual）は登録時に LLM が返す — [compile_rule.py:48-51, 227-229][compile]。同じ意味の属性に同じ名前を使うことは、プロンプトの指示に依存 — [compile_rule.py:78-79][compile]。
- 複数のルールが同じ属性を使うとき、`visual` は AND で合成（1 つでも false なら聞かない）— [attributes.py:40][attr]。
- 画像から分からない属性は住人が登録する — [guide:71, 348][guide]。経路は `objects.set_attribute`、値は `source="user", confidence=1.0` で、VLM の値を上書きし、次の scene.update のあとも効く — [state.py:455-476][state]。
- `category / group / role` は `set_attribute` で直せない（エラーになる）— [state.py:465-466][state]。
- 属性の訂正はルールバンクのファイルに残さない（「その場の状態なので」）— [rulebank.py:7][bank]。
- 「不明」の表現: 属性に値が無い → 対象の照合が None — [model.py:183-185][model]。VLM は判断できなければ "unknown" と答える指示 — [vlm_analyzer.py:53-56][vlma]。
- 不明のときの計画: 接触ルール → その物体は保留（deferred）、足りない事実つき — [planner.py:126-128, 221-222][plan]。収納先の義務が不明 → 「取り決めが当てはまるか分からない」で保留。ただし**ほかに合った義務が 1 つでもあれば、不明の候補は無視して進む** — [planner.py:296-302][plan]。
- `unknown_as` は登録の口で違う: 片付けルール（rules.set → from_legacy）は `"false"`（値が無ければ非該当）、norms.compile 経由は既定の `"unknown"` — [model.py:262][model]、[compile_rule.py:102-106][compile]。
- 等値比較: `value == self.where.equals` — [model.py:186][model]。
- 非該当の表示 `judgments` は、物体が対象で id か where を持つルールだけ。「全物体」を対象にするルール、領域・ロボットが対象のルールは出ない — [report.py:83][rep]。時刻や依頼者で非適用になった判定は `reasons` から除かれる — [report.py:59][rep]。吹き出しに出る照合の行は既定で 3 行まで — [CoGroundRuleTagView.cs:66][tag]。

### Inferences
- **「割れ物」**: LLM が fragile=true に落とし、VLM が答える。定義できている。誤答は judgments で見える。
- **「パパの物」**: owner=papa（visual=false）に落ちる。照合は定義できているが、値が "papa" か "dad" か "user_01" かは LLM と住人の入力しだいで、不一致は**エラーにならず非該当**になる。持ち主は物体ごとに手入力で、しかもファイルに残らないので、再起動のたびに入れ直す設計になっている（意図かどうかは不明）。
- **「食卓の上の物すべて」**: 対象としては書けない。場所は依頼の `source_region` としてだけ扱える（[task.py:130][task]）。つまり「場所で対象を選ぶ」ことは依頼にはできてルールにはできない。
- **不明の扱いは一様ではない**。同じ「皿は上段」でも、rules.set で入れると材質不明の物は非該当、norms.compile で入れると不明（保留）。住人から見た区別の理由は無い。
- **「非該当も見せる」が守っているのは属性の誤認識だけ**。種類（category）の誤認識は見えても直す経路が無く、時刻・依頼者による非適用は見えない。「VLM の誤りを直せる」という主張は、**属性については成り立ち、種類については成り立っていない**。片付けルールの多くは種類で対象を選ぶ（R3a/b）ので、この穴は小さくない。
- 収納先の決定で「合った義務があれば不明の候補を無視する」のは、不明を安全側に倒すという全体の方針と逆向きで、黙った取りこぼしになりうる（例: 「割れ物は緩衝材の箱へ」が不明、「皿は上段」が該当 → 上段へ運ぶ）。

### Gaps
- VLM の答えの文字列（"true" / "false" / "unknown"）が、照合で使う型つきの値にどこで変換されるかは未確認（§1 の Gaps と同じ）。
- 個体 id（`plate_A` など）がセッションや再検出をまたいで保たれるかは、知覚側（object_store.py、association.py）を読んでいないので未確認。id を対象にしたルール（#83）の持続性はここに依存する。
- 属性の訂正が知覚側の記憶（ObjectMemory）には残るのかどうかも未確認。

---

## 6. 依頼とルール、ルール同士がぶつかったとき。依頼に出てこない物体への義務。部分実行は本当か

### Takeaway
部分実行は実装されている（行ごとに独立に判定し、運べない物は保留、ほかは計画）。ぶつかり方の解決は「禁止が常に勝つ」「依頼の置き先は常設の置き先に勝つが禁止は解かない」「義務同士は解決せず住人に返す」の固定で、優先順位の枠は無い。義務は「常に達成すべき目標」ではなく「動かすならここ」という収納先の指定として働く。

### Cited Findings
- 行ごとに調べ、運べない物があってもほかの物は個別に計画する。保留した物は行に残り未達成として数える — [planner.py:22-30][plan]、テスト [test_task.py:77, 153, 203][ttask]。報告は「N 点中 M 点」— [report.py:41-42][rep]。
- **依頼 vs 禁止**: 依頼の対象に含めたうえで（「片づけるかどうかはルールが決める」— [compile_rule.py:287][compile]）、禁止に反する予測なら触れずに残す — [planner.py:124-125][plan]。依頼の置き先指定は禁止を解かない — [planner.py:20][plan]、[test_task.py:309][ttask]。
- **依頼 vs 常設の義務**: 依頼の間だけのルール（origin = task）が収納先で先に立ち、使わなかった常設ルールは `overridden_rule_ids` と message に残す — [planner.py:275-294, 336-342][plan]。
- **手の指定 2 種**: `plan.place` はルールを確かめずに使う — [planner.py:260-262][plan]。シーケンス編集の指定（`requested_destination`）は収納先のルールと照合し、違えば保留 — [planner.py:316-333][plan]。
- **義務 vs 義務**: 別の収納先を指す義務が複数合うと ambiguous（候補を返す）— [planner.py:308-312][plan]。
- **禁止 vs 禁止 / 禁止 vs 義務**: どれか 1 つでも violated なら保留。優先順位のフィールドは NormRule に無い — [model.py:229-247][model]。
- **許可**: `exception_of` で指した禁止だけを、Scope と対象が合うときに狭める — [evaluate.py:98-111][eval]。
- **依頼に出てこない物体**: 依頼があるあいだは依頼の行だけを計画する — [state.py:664-668][state]。依頼が無いときは、運ぶ物すべてを暗黙の依頼にして、収納先の義務が当てはまる物だけを step にする — [state.py:676-700][state]、[planner.py:53-54, 105-106][plan]。
- 義務 placed_in は置き終わった時点でだけ評価する。動かさなかった物体には評価する時点が無く `not_applicable` — [evaluate.py:94-97][eval]、[guide:243][guide]。
- 収納先を決めるルールが無い物体は、依頼中は status = deferred（「取り決めが無い」）— [planner.py:304-307, 219][plan]。

### Inferences
- 「動かせる物は動かし、残りは残す」は本当に実装されており、AR の Before/After の前提（混在した最終状態）と合っている。これは監査として**支持**できる。
- ただし「禁止が常に勝つ」ことは設計ガイドに規則として書かれておらず、コードの順序から生じている。住人が「この禁止より、今日の私の依頼を優先して」と言う手段は、事前登録の許可（依頼者の一致）しか無い。その場で「今回だけ無視」（X-OOHRI の Ignore、[文献調査:84][arrep]）に当たる操作は、ルールモデルには無い。
- **「義務」の意味が内容によって違う**。placed_in の義務は「もし置くならここ」（条件つき・時点）、base_stopped の義務は「条件が成り立つ間ずっと」（維持）。さらに依頼が無いときだけ、placed_in の義務が実質的に「常設の目標」として働き、物を動かす。同じ「義務」という語で 3 通りの振る舞いがある。「薬は戸棚にしまう」を住人が義務として登録したとき、依頼中は机の上の薬だけ・依頼が無ければ家中の薬、という違いは説明が要る。
- 手の指定の 2 経路（plan.place はルール無視、sequence.add はルール照合）は、住人から見て同じ「ここに置いて」なのに結果が違う。AR で物体をつかんで置き先を直す操作がどちらに繋がるかで、ラベルの出方が変わる。
- deferred という 1 つの status に「禁止に反する」「情報が足りない」「取り決めが無い」「置き先指定がルールと違う」「迂回路が無い」が入っている。表示側は verdicts と message を見て分けているが、「取り決めが無い」は家庭ルールによる保留ではないので、status として分ける方が AR のラベル設計と合う。

### Gaps
- 複数の住人が矛盾するルールを登録した場合（author が違う）の扱いは、コードに特別な処理が見当たらない（author は「私」の参照先としてだけ使う — [model.py:231][model]）。意図的な範囲外かは文書に無い。

---

## 7. 現行の範囲の定義にある曖昧さ・不整合（一覧）

### Takeaway
範囲の定義は 1 文（[guide:340][guide]）と除外表だけで、「何を知る必要があるか」「いつ調べるか」「何が見えるか」の次元では定義されていない。そのため、宣言した範囲内なのに書けないもの、書けるのに見えないもの、口によって意味が変わるものが混ざっている。

### Cited Findings
各項目の根拠は前節までに示した行番号。ここでは対応だけを挙げる。
1. 「ロボットが変えられる状態のすべて」は手書きの 5 項目に対する主張 — [vocabulary.py:36-42, 197-199][voc]。
2. contact と holding は現行スキルで独立に変えられない — [evaluate.py:30][eval]。
3. 条件の語彙に導出原理が無い（4 語）— [vocabulary.py:126-156][voc]。
4. 対象条件は属性 = 値 1 個（AND・NOT・場所・関係なし）で、これは除外表に載っていない — [models.py:236-248][models]、[guide:342-349][guide]。
5. 時刻は HH:MM の窓だけ（曜日・日付・期間なし）— [model.py:104-106, 134-147][model]。除外表に載っていない。
6. 依頼者は ID の一致だけ（「家族」「持ち主本人」などの集合・関係なし）— [model.py:149-152][model]。
7. 人についての事実は「台車からの距離」と 3 種の kind だけ（部屋・活動・向きなし）— [predicates.py:81-95][pred]、[models.py:165][models]。
8. 「義務」が内容によって時点の義務・維持の義務・（依頼が無いとき）常設の目標として働く — [evaluate.py:94-97][eval]、[state.py:676-700][state]。
9. 許可は例外としてしか機能しない — [evaluate.py:81-82][eval]。
10. `unknown_as` が登録の口で違う — [model.py:262][model]。
11. 収納先の決定で、合った義務があると不明の候補を無視する — [planner.py:296-302][plan]。
12. 計画時に評価するのは grasp / place / 領域進入だけ。設計ガイド §7 の R4 の計画時の記述と実装が合わない — [monitors.py:97][mon]、[guide:253][guide]。
13. 実行中の応答が内容ごとに固定で、規範（義務か禁止か）を見ない — [vocabulary.py:105-117][voc]、[monitors.py:64-76][mon]。
14. `speed_below` の応答は停止 — [guide:353][guide]。
15. 「非該当も見せる」は属性照合だけ。種類は直せず、時刻・依頼者の非適用は見えない — [report.py:59, 83][rep]、[state.py:465-466][state]。
16. 属性の訂正（住人が登録する持ち主など）はファイルに残らない — [rulebank.py:7][bank]。
17. 手の置き先指定が 2 経路で、ルールの扱いが違う — [planner.py:15-16][plan]。
18. status = deferred に、ルール由来でない「取り決めが無い」が入る — [planner.py:219, 304-307][plan]。
19. `Step.status` の `unmatched` の説明が、models.py（合うルールが無い）と planner / Unity（収納先の領域がシーンに無い）で違う — [models.py:352][models]、[planner.py:26][plan]、[CoGroundRuleTagView.cs:14][tag]。
20. 設計ガイドの置き場所は `CoGround/Documents/` で、Backend・UserApp のどちらの README からも辿れなかった（grep で該当なし）。コードは「設計ガイド §n」と参照する — [vocabulary.py:1][voc]。

### Inferences
- 4〜7 は「**範囲外と宣言していないのに書けない**」もので、査読者や住人が最初に踏む。除外表（様態・順序・好み・学習・非視覚属性・副作用）は内容の側の限界しか挙げておらず、対象・条件の側の限界が抜けている。
- 12〜14 は「**書けるが、プレビューに出ない／応答が期待と違う**」もの。範囲内と数えると AR の主張と合わなくなる。
- 8〜11、17 は「**同じ文が口や状況で違う意味になる**」もの。範囲の問題というより意味論の不整合。
- 「ルールの種類を数えない」という方針は守られているが、その代わりの次元（何を制約するか／何を知る必要があるか／いつ調べるか／何が見えるか）で範囲を書いた箇所は、設計ガイドに無い。語彙の表（[guide:92-100][guide]）が「状態・時点・応答」までは持っているので、ここに「必要な事実」と「見え方」の列を足せば次元による定義になる。

### Gaps
- 上の不整合のうちどれが意図した単純化で、どれが見落としかは、文書からは判断できない。チームへの確認が要る（特に 10、11、16、17）。

---

## 8. ルールモデルと、計画している AR インタラクション（Before/After・DR・違反物体は残してラベル）は整合しているか

### Takeaway
物体に結果が付くルール（接触・保持・置き先）と、行ごとの部分実行、足りない事実の提示については、バックエンドの出力と AR の設計はよく合っており、Unity 側にも既に実装がある。合っていないのは、経路・速さ・停止のルール（最終状態に出ない）、「違反」という語（実際は予測して避けた）、プレビューの有効時刻、ルールに関係しない物体の扱いの 4 点。

### Cited Findings
- After 表示は既に「動く物は元の位置を薄くして置き先にコピー、たどり着けない物は残して理由ラベル」を実装している — [CoGroundAfterView.cs:12-26][after]。段階表示（①の後、②の後、最終）もある — [CoGroundAfterView.cs:9-11][after]。
- ラベルは違反（赤・ルール原文）、未確定（黄・足りない情報）、その他（message）を分ける。Before では「運ばない」、After では「残す」と言い分ける — [CoGroundRuleTagView.cs:11-18, 415-446][tag]。
- 計画が物体に付ける理由の文は "Left in place without touching it, because it violates …" — [planner.py:125][plan]。判定の basis は predicted — [planner.py:120][plan]。task.py は「触れずに保留した物体は『違反の予測により保留』であり、実行時の違反ではない」と明記 — [task.py:21-22][task]。
- Plan に出てこない物（もう行き先にある、ルールに関係ない）は、After で「そのまま」（ラベルなし）— [CoGroundAfterView.cs:26][after]。依頼が無いとき、収納先の取り決めが当てはまらない物は step にしない — [planner.py:53-54, 105-106][plan]。
- 実行中の停止と避けている領域は、別の状態表示（HOLD マーク、keepout）— [CoGroundHomeStatus.cs:11-14][home]。領域そのものの表示部品もある（CoGroundZone.cs）。
- 文献調査の位置づけ: X-OOHRI は物理的な実行可能性だけを物体に赤とタグで示し、家庭ルール・持ち主・言葉で書いた制約は判定対象に無い — [文献調査:76-78][arrep]。規範違反を物体ごとに AR ラベルで示す研究は見つからなかった — [文献調査:80][arrep]。
- DR の実装方式（ステンシルで背景メッシュを出す）は物体単位のマスク — [DiminishReality/README.md:1-16][drreadme]。

### Inferences
- **合っている点（支持）**: (1) 行ごとの部分実行 → 混在した After。(2) 違反・未確定・競合・物理不可の区別が verdicts と status で届く。(3) 根拠になったルールの原文と id が届く。(4) 足りない事実が届くので「何を教えれば動くか」をラベルに書ける。(5) DR は物体単位で、「残す物は消さない」は自然に実現できる。
- **合っていない点 1: 最終状態に出ないルール**。§4 の (ii)(iii)。提案の主張を「家庭ルールの違反を物体に付けて見せる」と書くなら、R2（迂回成功時）と R4 は主張の外にある。設計ガイドの冒頭シナリオ（[guide:28-34][guide]）は 4 ルール中 2 つ（R2、R4）がこの種類なので、**デモの見せ場と AR の主張がずれている**。
- **合っていない点 2: 「違反」という語**。プレビュー時点では何も違反していない。正確には「動かすと R1 に反するので、動かさない計画にした」。ラベルに「違反」と書くと、ロボットが違反した・しそうだと読まれうる。バックエンドは predicted / observed を分けているので、表示の語を「R1 により残す」に寄せるだけで足りる（Unity の note は既に "Left in place because it violates R1" で、ほぼこの形）。
- **合っていない点 3: 有効時刻**。時刻つきのルールがあると After は「いま実行したら」の予測で、数分後には変わりうる。Before/After を承認の根拠にするなら、「18:00 を過ぎるとこの経路は使えない」のような失効条件を見せる必要がある。step の判定から時刻を落としているので、いまの出力では表示側が知りえない。
- **合っていない点 4: 動かない物の 3 分類**。After で動かない物体には「ルールで残す（ラベルあり）」「依頼の対象外・取り決め無し（ラベルなし）」「認識されていない（何も無い）」がある。「非該当も見せて直せる」を強みにするなら、2 番目と 3 番目が区別できないのは弱い。judgments は運ぶ物すべてに届いている（[state.py:381-382][state]）ので、データは足りている。表示の問題。
- **残す物体が複数の理由を持つ場合**、最初の violated だけがラベルになる（[CoGroundRuleTagView.cs:421][tag]、[planner.py:124][plan]）。1 つ直しても別の理由でまた残る、という体験になりうる。
- 経路・速さのルールを Before/After に入れる方法の候補（私の案）: (a) After に「通った道」と「避けた領域」を床に重ねる（row.route の keepout を使う）。(b) 速さ・停止は「実行中に効くルール」として After の外に一覧で出し、物体ラベルとは別の層にする（build_monitors の結果を使う）。(c) 範囲から外し、実行時の安全層として論文の主張から切り離す。どれを選ぶかが §9 の選択肢に対応する。

### Gaps
- 実機の DR で「元の位置を薄くする」をどう実現するか（シミュレーションでは Renderer を切って薄いコピー — [CoGroundAfterView.cs:14][after]）は、当面シミュレーション前提なので評価していない。
- 住人が Before/After で経路ルールの効果をどの程度知りたいかは、ユーザー調査が無く不明。

---

## 9. もっと輪郭のはっきりした範囲の定義にするための選択肢

### Takeaway
選択肢は 4 つある。私の判断では、論文の主張（物体に付く説明つきの Before/After）と最も整合するのは **案 1（最終状態に効くルールに限定）を核にし、案 3 の一部（対象条件の AND と場所）を足す**形で、経路ルールを見せ場に残したいなら案 2 になる。案 4（文書だけ直す）は最小コストだが、範囲の狭さがそのまま残る。

### Cited Findings
各案の「コード・文書の変更」は、前節までに引用した箇所に対するもの。新しい事実の引用は無い。現状の前提だけ再掲する: 内容 7 語と checked / response — [vocabulary.py:68-124][voc]；除外表 — [guide:342-349][guide]；After の表示対象 — [CoGroundAfterView.cs:12-26][after]；対象条件の型 — [models.py:236-248][models]。

### Inferences
範囲は「種類の数」ではなく、次の 4 つの次元で書く: **何の状態を制約するか／判定に何を知る必要があるか／いつ調べるか／住人に何が見えるか**。

**案 1: 最終状態に効くルールに限定する（「どの物が、最後にどこにあるか」を変えうるルール）**
- 定義: 範囲内 = 計画時（つかむ時点・置いた時点・経路の成立）に判定でき、結果が「物体が動く／残る／着く場所」として After に現れるルール。知る必要があるのは、物体の属性（VLM か住人）、領域、時計、依頼者。
- 残す: contact（holding は統合）、placed_in、領域進入（「道が無ければその物は残る」という物体への結果として）。Scope の時刻・依頼者、region_full。
- 外す（主張から）: base_stopped、speed_below、near_person、holding_something、base_in_zone。コードは実行時の安全層として残してよいが、「住人が書ける家庭ルール」の範囲と coverage の主張からは外す。
- 変更: `ROBOT_STATES` を「プレビューに効く状態」と「実行時だけの状態」に分ける（vocabulary.py）。設計ガイド §4 の主張文と §10 の範囲文を書き換え、冒頭シナリオから R4 を外すか「実行時の安全層」と位置づけ直す。test_vocabulary の coverage テストを更新。Unity は変更なし。
- 得るもの: AR の主張と 1 対 1 に合う。「違反で動かせない物は残す」がすべての範囲内ルールで成り立つ。失うもの: R4 のデモ、「状態すべて」という一般性の主張。

**案 2: 2 層の範囲にし、層ごとに見せ方を決める（結果のルール + 動きのルール）**
- 定義: 語彙の各内容に「どこに付けて見せるか」を持たせる。物体（contact / holding / placed_in）、床・経路（enter_zone / in_zone）、ロボット・時間（base_stopped / speed_below）。範囲内 = 3 つのどれかに付けて、**計画時に**見せられるルール。
- 残す: 7 語すべて。
- 変更: `Entry` に表示の錨（anchor: object / floor / robot）を足し、`export()` で渡す（vocabulary.py）。速さ・停止の計画時の予測を足す（いまは無い。少なくとも「このルールは経路のこの区間で効きうる」を出す）。After に経路と避けた領域を重ね、迂回の理由（ルール id）を付ける（CoGroundAfterView / CoGroundPlanView、行の route を使う）。step の判定に失効時刻を残す（models.py の timeless の見直し）。設計ガイドの語彙表に「見え方」の列を足す。
- 得るもの: 冒頭シナリオ（R1〜R4）をそのまま主張にできる。失うもの: 実装量が最大。動きのルールの AR 表示は、文献調査が示す既存研究（軌跡・ゾーン表示）と重なり、新規性は物体ラベルほど強くない。

**案 3: 内容は絞り、対象と条件の表現力を上げる（「照合」を貢献にするなら、照合する側を強くする）**
- 定義: 範囲内 = 物体・場所・人・時刻についての事実の組み合わせで対象と状況を選び、物の扱い（触る・置く）を決めるルール。
- 残す: contact、placed_in、領域進入。
- 足す: 対象条件の AND と NOT、場所で選ぶ（in(region)）、持ち主と依頼者の対応（owner = requester）、条件に person_in_zone と object_in_region、時刻に曜日。
- 変更: `RuleCondition` と `Target.matches`（models.py、model.py）、`judgments`（複数の属性の照合結果を並べる。report.py）、登録プロンプト（compile_rule.py）、`depends_on`（depends.py）、設計ガイド §4。Unity の judgments 表示（CoGroundNormText）。
- 得るもの: §3 で落ちた #49, 72, 74, 88 と、A+ の人数分展開（#65, 66, 69, 79）が解ける。片付けと所有の中での網羅性が上がる。失うもの: 3 値の照合と「足りない事実」の提示が複雑になる（AND の中の不明をどう見せるか）。

**案 4: コードは変えず、範囲を 3 つの検査で定義し直す（文書だけ）**
- 定義: ルールが範囲内 ⇔ (i) 内容が、シミュレータの状態ベクトル上の述語で、いずれかのスキルがその値を変える。(ii) 対象と条件に要る事実がすべて {時計、依頼者、VLM が答える属性、住人が登録した属性、領域の形、人の位置} から得られる。(iii) つかむ時点・置いた時点・台車が動く間のいずれかで判定できる。
- 変更: 設計ガイド §4 の主張を「列挙した状態について」に弱め、§10 の除外表に、対象・条件の側の限界（人の状態、履歴、2 物体の関係、場所で選ぶ、対象の AND、優先順位、尋ねる、センシング）を例つきで足す。語彙表に「必要な事実」と「見え方（物体／経路／実行時だけ）」の列を足す。§7 の R4 の計画時の記述を実装に合わせる。
- 得るもの: 最小コストで正直になる。失うもの: 範囲の狭さ（調査の主要 3 領域のうち 2 つがほぼ外）と、AR の主張とのずれは残る。

**どの案でも直すべきもの（範囲と無関係の不整合）**: `unknown_as` の口による違い、収納先で不明の候補を無視する挙動、status = deferred から「取り決めが無い」を分ける、種類（category）の訂正経路、属性の訂正の保存、手の置き先指定 2 経路の統一、応答が規範を見ないこと。

### Gaps
- 各案のユーザー価値（住人がどの次元のルールを実際に言うか）は、実在の発話データが無いので判断できない。調査 README も「家庭のルールを住人に聞いた調査は少ない」としている — [README:261][survey]。
- 案 2 の速さ・停止の計画時予測がどこまで可能かは、人の動きの予測に依存し、シミュレーション前提では評価できていない。

---

## 10. これまでのチームの決定のうち、この監査が支持するもの・疑問を付けるもの

### Takeaway
「原文 + 4 枠」「検索より照合」「VLM への質問はルールから」「非該当も見せる」は、方針としては監査でも支持できる。疑問が付くのは「内容の語彙をロボットが変えられる状態から作る」を**範囲の定義として**使うことと、「照合」「非該当の表示」が実装上は属性 = 値 1 個の等値比較に限られていること。

### Cited Findings
- 記録されている決定: 4 枠、「種類が N 個」と言わない、内容の語彙は「ロボットが変えられる状態」から、スキルを鍵にした検索はせず照合、VLM の質問はルールバンクの属性から、非視覚属性は住人が登録、非該当も見せる — [coground-rule-design.md][mem]、[guide:24, 88-102, 190-200, 63-71, 220-230][guide]。
- 以前の新規性調査の結論: ルールを分解する表現は**既出**（AgentSpec、ODRL、ADICO、SLEEC など）、分解の効果は**証拠不足** — [HouseRule_Novelty_Report.md:21-22][novelty]。5 者の議論の結論は「論文の主な枠組みは評価ベンチマーク。物体ごとの未確定の扱いは副次的な主張」— [HouseRule_Novelty_Report.md:27][novelty]。
- 以前の比較表は、CoGround の差分として「時刻・依頼者・状態で効く範囲を変える」「範囲があいまいなルールを住人に確定させる」「訂正と差分」を挙げる — [CoGround_vs_TidyBot_ThatsMine.md:21, 38, 44][vs]。

### Inferences

| 決定 | 監査の結果 | 理由 |
|---|---|---|
| ルール = 原文 + 4 枠（規範・条件・対象・内容） | **支持**（ただし新規性の主張にはしない） | 枠ごとの訂正（属性・Scope・領域・例外）と差分が実装され、AR ラベルの材料（どの枠が効いたか）になっている。分解そのものは既出という以前の結論と整合 |
| 「種類が N 個」と言わない | **支持**。ただし代わりの次元がまだ書かれていない | §7。語彙表に「必要な事実」「見え方」を足せば次元による定義になる |
| 内容の語彙は「ロボットが変えられる状態」から | **語彙の作り方としては可、範囲の定義としては疑問** | §2。列挙は手書きで、実際の境界は可観測性。住人が書けない理由の大半は内容の外（§3） |
| スキルで検索せず、対象と属性を照合 | **支持** | 全件評価で足り、部分実行と judgments の土台になっている。ただし「照合」の実体は属性 = 値 1 個の等値比較で、場所・AND・関係は照合できない（§5）。照合を貢献に据えるなら案 3 が要る |
| VLM への質問はルールが使う属性から。非視覚属性は住人が登録 | **支持、ただし運用の穴あり** | 仕組みは一貫している。穴: 登録した属性が保存されない、属性名・値の表記ゆれが黙って非該当になる、visual の判定を LLM に任せている |
| 非該当も見せて、VLM の誤りをすぐ直せる | **属性については支持、種類・時刻・依頼者については疑問** | §5。種類は直せず、Scope による非適用は見えない。「全物体」対象や領域ルールは judgments に出ない |
| （AR）違反で動かせない物は消さずに残してラベル | **支持、ただし覆えるのは内容 7 語のうち 3 語と、迂回失敗時の領域進入** | §4、§8。冒頭シナリオの R2（迂回成功）と R4 は覆えない |
| 部分実行（運べる物は運ぶ） | **支持** | §6。実装・テストとも揃っている |

- 以前の議論が「主な枠組みは評価ベンチマーク、未確定の扱いは副次的」と結論したのに対し、いまの AR 側の計画は「物体に付く説明つきのプレビュー」を主張にしようとしている。この 2 つは矛盾しないが、**範囲の定義は AR の主張に合わせて引き直す必要がある**（ベンチマークなら「分解が効くルール」、AR なら「物体に結果が付くルール」が自然な範囲）。現行の「ロボットが変えられる状態」はどちらの主張にも直接は対応していない。

### Gaps
- 議論記録（debate/R1〜R2 の各ファイル）は grep で範囲に関する行を拾っただけで、全文は読んでいない。範囲について別の合意があった可能性は残る。
- メモリの記録は 2026-11-19 時点のもので、その後の口頭の合意は確認できない。

[voc]: file:///C:/Users/tenma/CoGround/Backend/grounding_server/coground_server/norms/vocabulary.py
[model]: file:///C:/Users/tenma/CoGround/Backend/grounding_server/coground_server/norms/model.py
[pred]: file:///C:/Users/tenma/CoGround/Backend/grounding_server/coground_server/norms/predicates.py
[eval]: file:///C:/Users/tenma/CoGround/Backend/grounding_server/coground_server/norms/evaluate.py
[attr]: file:///C:/Users/tenma/CoGround/Backend/grounding_server/coground_server/norms/attributes.py
[plan]: file:///C:/Users/tenma/CoGround/Backend/grounding_server/coground_server/norms/planner.py
[mon]: file:///C:/Users/tenma/CoGround/Backend/grounding_server/coground_server/norms/monitors.py
[rep]: file:///C:/Users/tenma/CoGround/Backend/grounding_server/coground_server/norms/report.py
[task]: file:///C:/Users/tenma/CoGround/Backend/grounding_server/coground_server/norms/task.py
[dep]: file:///C:/Users/tenma/CoGround/Backend/grounding_server/coground_server/norms/depends.py
[models]: file:///C:/Users/tenma/CoGround/Backend/grounding_server/coground_server/models.py
[state]: file:///C:/Users/tenma/CoGround/Backend/grounding_server/coground_server/state.py
[motion]: file:///C:/Users/tenma/CoGround/Backend/grounding_server/coground_server/motion.py
[bank]: file:///C:/Users/tenma/CoGround/Backend/grounding_server/coground_server/rulebank.py
[compile]: file:///C:/Users/tenma/CoGround/Backend/grounding_server/coground_server/llm/compile_rule.py
[pipe]: file:///C:/Users/tenma/CoGround/Backend/grounding_server/coground_server/perception/pipeline.py
[vlma]: file:///C:/Users/tenma/CoGround/Backend/grounding_server/coground_server/perception/vlm_analyzer.py
[tvoc]: file:///C:/Users/tenma/CoGround/Backend/grounding_server/tests/test_vocabulary.py
[tnorms]: file:///C:/Users/tenma/CoGround/Backend/grounding_server/tests/test_norms.py
[thome]: file:///C:/Users/tenma/CoGround/Backend/grounding_server/tests/test_home_rules.py
[treg]: file:///C:/Users/tenma/CoGround/Backend/grounding_server/tests/test_rule_registration.py
[ttask]: file:///C:/Users/tenma/CoGround/Backend/grounding_server/tests/test_task.py
[guide]: file:///C:/Users/tenma/CoGround/Documents/CoGround_Home_Rules.md
[survey]: file:///C:/Users/tenma/CoGround/UserApp/CoGround/docs/rule_survey/README.md
[arrep]: file:///C:/Users/tenma/CoGround/UserApp/CoGround/reports/AR計画可視化とエラー表示%20文献調査.md
[novelty]: file:///C:/Users/tenma/CoGround/Backend/ResearchDoc/houserule_review/final/HouseRule_Novelty_Report.md
[vs]: file:///C:/Users/tenma/CoGround/Backend/ResearchDoc/houserule_review/final/CoGround_vs_TidyBot_ThatsMine.md
[mem]: file:///C:/Users/tenma/.claude/projects/C--Users-tenma-CoGround-UserApp-CoGround/memory/coground-rule-design.md
[ptypes]: file:///C:/Users/tenma/CoGround/UserApp/CoGround/Assets/Main/Script/Plan/CoGroundPlanTypes.cs
[after]: file:///C:/Users/tenma/CoGround/UserApp/CoGround/Assets/Main/Script/Plan/CoGroundAfterView.cs
[tag]: file:///C:/Users/tenma/CoGround/UserApp/CoGround/Assets/Main/Script/Rules/CoGroundRuleTagView.cs
[home]: file:///C:/Users/tenma/CoGround/UserApp/CoGround/Assets/Main/Script/Home/CoGroundHomeStatus.cs
[drreadme]: file:///C:/Users/tenma/CoGround/UserApp/CoGround/Assets/Main/Script/DiminishReality/README.md
