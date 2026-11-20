# S1 — HRI・規範学習 (Searcher 1) 調査結果

担当: 人が教える許可・禁止・所有・家庭固有の方針、教示後の別指示での再利用、規範による部分実行・拒否。
調査日: 2026-11-19。仕様: ../../HouseRule_Research.md、共通ブリーフ: ../00_brief.md。

検証状態の凡例: **[本文確認]** = PDF本文を取得してテキストで該当箇所を読んだ / **[要旨のみ]** = abs・要旨・書誌のみ / **[未確認]** = 二次情報のみ。

---

## 1. 検索ログ

| # | 日付 | DB | 検索式 / 操作 | 採否と理由 |
|---|---|---|---|---|
| 1 | 2026-11-19 | 著者PDF (scazlab.yale.edu) | Tan et al. AAAI19 PDF を取得し全文読解 | 採用。起点文献。動画 (https://bit.ly/2z8obET) は視聴できず、本文中の動画説明と図1–2キャプションで判断 |
| 2 | 2026-11-19 | Web search | robot ownership norms learning Scassellati follow-up 2021–2023 | 新しい追試論文はなし。報道記事のみなので除外 |
| 3 | 2026-11-19 | OpenAlex | `filter=cites:W2964255654` (Tan の被引用) | 18件。ロボット関連の候補: Ayub&Wagner 2020、ActOwL 2025/26、COIN 2026、EgoAsk 2026、Oldenburg&Tan 2024。他はサーベイ・MAS・政治規範なので除外 |
| 4 | 2026-11-19 | Semantic Scholar API | `paper/arXiv:1812.02576/citations` | 16件。OpenAlex とほぼ重なる。追加は "Learning Ownership based on Theory of Mind" (2023) だが原文が見つからず未確認 |
| 5 | 2026-11-19 | OpenAlex | `cites:W3084730698` (Ayub&Wagner の被引用) | 継続学習の論文ばかりで、規範をロボット操作に適用するものはない。除外 |
| 6 | 2026-11-19 | Web search | "What Am I Allowed to Do Here" Pepper | 採用。本文確認の結果、行為は会話・移動で物体操作ではないため関連は低い |
| 7 | 2026-11-19 | Web search | Briggs Scheutz "Sorry, I can't do that" felicity conditions | 採用 (拒否機構の起点)。本文確認 |
| 8 | 2026-11-19 | Web search | robot learns prohibitions from NL instruction norm one-shot DIARC Scheutz | Scheutz, Thielstrom & Abrams 2022 (IJHCI) と Kasenberg et al. 2019 を採用。本文確認 |
| 9 | 2026-11-19 | Web search | LLM household robot "house rules" user-specified constraints manipulation | TidyBot・LLM-Personalize・Safety Chip はほかの担当 (S2/S3) が扱うので、ここでは評価しない |
| 10 | 2026-11-19 | Web search (extended) | personalized safety rules household robot LLM "don't touch" | RoboGuard・Safety Chip・2606.05952 は S3 に回す。自分の担当では採用しない |
| 11 | 2026-11-19 | Web search (extended) | household robot social norms LLM refuse partial 2024–2026 | ROBOTVALUES (2606.03312)、Empathic Ethical Disobedience (2512.18474)、Refuses in Chat (2610.14043)、GRACE を確認。教示ルールの再利用を含まないため、参照のみ |
| 12 | 2026-11-19 | Web search | contextual integrity privacy norms home robot | 2507.16124 (LLMのプライバシー認識ベンチ) と NeurIPS 2025 ポジション論文。操作の実行や教示ルールの再利用は含まないので参照のみ |
| 13 | 2026-11-19 | Web search | Kasenberg Roque Thielstrom Scheutz Engaging in Dialogue | 採用。本文確認 |
| 14 | 2026-11-19 | Web search (extended) | robot remembers user-taught rules applies to later instructions LLM memory | 直接該当なし。DROC は既知の文献として別途確認 |
| 15 | 2026-11-19 | arXiv | 2311.10678 (DROC) PDF を取得し全文読解 | 採用。主張Bへの強い反例 |
| 16 | 2026-11-19 | Web search | "action permissions" OR "permission learning" robot | Tan と Ayub に戻るだけで、新規文献なし |
| 17 | 2026-11-19 | Web search | Rosie interactive task learning Mohan Laird Lindes | タスクと概念の学習で、許可・禁止ルールは扱わない。別名「instructable agent」として記録し除外 |
| 18 | 2026-11-19 | Web search (extended) | LLM robot learns social norms household norm learning 2024–2026 | Malle et al. RO-MAN 2020 (方法論、本文確認)、NormGym 2611.08613 (要旨のみ) |
| 19 | 2026-11-19 | Web search (extended) | embodied agent benchmark household-specific rules personalized norms | NormAct 2606.27826 と VestaBench (EMNLP 2025 industry) は要旨のみ。PersONAL・PersonalHomeBench は S2 に回す |
| 20 | 2026-11-19 | Web search | Brawer Scassellati Interactive Policy Shaping | 採用 (Tan の同ラボの後続、言語指示から禁止・許可ルールを作る)。本文確認 |
| 21 | 2026-11-19 | arXiv abs | 2605.28087 (COIN)、2609.16766 (EgoAsk)、2509.12754 (ActOwL) | いずれも所有推定・知識教示まで。操作の拒否や部分実行は要旨に記載なし。参照のみ |
| 22 | 2026-11-19 | OpenAlex | robot norm learning object instruction ほか | 新規の該当なし (一部クエリは API エラー) |

---

## 2. 比較表 (1行 = 論文 × 実験条件)

| Paper (URL) | Condition/demo | Evidence location | Rule origin | Rule representation | Novelty unit | Perception input | Instruction matching | Decision & evidence | Match A–D | Differences |
|---|---|---|---|---|---|---|---|---|---|---|
| Tan, Brawer, Scassellati, "That's Mine!" AAAI 2019 [本文確認] https://scazlab.yale.edu/sites/default/files/files/Xuan_AAAI19.pdf | **実機シナリオ1**: 「作業台を片づけて」の実行中に赤い物体を捨てようとして "No Baxter, that's mine!" と叱責される | §Video demonstration、Fig.1上 | 住人が明示 (叱責) | 叱責を3つに分けて解釈する: 規範 (forbid trash if ownedBy …)、物体固有の許可 (forbid(trash,O))、所有の主張。分けるのはシステム。自然言語の解析方式は未確認 | 未教示の個体。ほかの赤い物体の所有者を知覚ヒューリスティック (KLR、特徴は位置・色・最終接触時刻) で予測する | 叱責された物体の所有情報は初めは**与えられていない** (叱責で得る)。ほかの物体の所有は推定 | 同じ依頼の**実行中**に教えられ、同じ依頼にすぐ適用される。後続の別依頼ではない | 部分実行: 残りを片づけ、所有物と予測した赤い物体には触れない。定性デモのみ (動画は未視聴、本文の説明だけで判断) | A ○ (新しい個体)、D △ (包括的な依頼の部分完遂。ただし単一の家庭) | ルールは事前教示ではなく実行中の訂正。家庭ルールの入れ替え比較はない。義務を扱わない |
| 同上 | **実機シナリオ2**: シナリオ1の後、別ユーザが物体2を捨てるよう命令する | §Video demonstration、Fig.1下 | 住人の明示 (シナリオ1の教示) | 所有者ごとの規範 + 所有グラフ | 新しい依頼者・新しい依頼 | 物体2の所有はシナリオ1の結果として**信念がある**。新ユーザが排他的所有を主張すると更新される | **以前のルールを別の依頼で再利用する**。対象は単一の物体指定 | 拒否して謝罪する。所有の主張後は実行する。定性デモのみ | B ○ (定性)、D △ (所有状態を変えると同じ依頼で行動が変わる) | 依頼は単一物体を指定し、包括的な依頼ではない。関連ルールの検索という仕組みはなく、全規則を評価する |
| 同上 | **実機シナリオ3**: ブロックの所有状態を**初めから知っている** (与えられている)。物体2の pickUp 禁止 (Xuan所有)、さらに2例、物体3 (所有者なし) の許可 → 規範を帰納 | §Video demonstration、Fig.2 | 例からの帰納 (物体固有の許可) | 帰納された規範 `forbid pickUp if ownedBy any`。帰納するのはシステム (逐次ルール学習) | 未教示の個体 (物体4) | 所有は**最初から与えられている** | 後続の pickUp 依頼に適用。単一の物体 | 拒否 ("denies the request")。定性デモのみ | A ○、C △ (分解表現はあるが効果は測っていない) | 所有の正解ありの条件。家庭ごとの比較はない |
| 同上 | **シミュレーション 規範学習**: 20ブロック・3エージェント。許可を 100/50/25% 与え、所有の雑音あり/なし | Table 1 | 例から帰納 (真のルール3本を設計者が設定) | 述語ルール (ownedBy, isColored, inArea …、語彙は設計者が用意) | 未教示の個体 (残りの物体) | 所有は既知または40–80%の確信度。色は撹乱変数 | ― (ルール精度の評価) | 対照付き定量: accuracy 0.995→0.761、F1 0.995→0.519、ベースライン 0.583/0.000 | A ○ (定量、シミュレーション) | 家庭ルールの比較なし。分解の有無を比べるアブレーションなし |
| 同上 | **シミュレーション 課題ベース評価**: collectAll / trashAll。誤るたびに真の許可で訂正する | Table 3 | オンライン訂正 | 同上 | 同上 | 所有ルールが関係するときだけ真の所有者を与える | 包括的な依頼 (全部集める/捨てる、規範違反は除く)。規範は事前に知らずオンラインで学ぶ | 定量: ミス数 6.30 / 6.32 (ベースライン 8.75 / 15)。ルール精度 0.975 / 0.877 | D △ (包括的な依頼で回避と完遂を同時に測っている。ただし家庭ルールの入れ替えや対での正解率はない) | 事前教示 → 後続依頼という構成ではない。確率が閾値を超えるかで実行するので、不明時の保留はない |
| Zha et al., DROC "Distilling and Retrieving Generalizable Knowledge for Robot Manipulation via Language Corrections" arXiv 2311.10678 (v2 2024-03) [本文確認、採録会議は本文中に記載なし=未確認] https://arxiv.org/abs/2311.10678 | **計画レベル**: 訓練タスクで受けた言語訂正を知識として蒸留し、別のテストタスクで検索する (例: "Put scissors in drawer" で "User wants stationery in white drawer" → テスト "Clean the table") | §IV、Table I、Table II、Fig.4 | 住人の明示 (実行中の訂正。著者3名がオラクル利用者) | LLMが自然言語の知識文に蒸留する (例 "Robot only has one hand"、"White shelf is full")。対象・条件・規範への分解はしない | 新しいタスク・新しい物体 (テキストと視覚の類似で検索) | 実機 (Franka)。物体状態の与え方は本文で一部のみ確認 | **以前の知識を別の依頼で再利用**し、関連知識を検索する (タスク意味と視覚特徴) | 定量 (小規模、各3試行): テスト時の訂正回数 Pref 0.5 vs 1、Feasibility 0.67 vs 1.33 ほか (Ours vs Ours–R) | B ○ (定量)、A ○ | 中身は選好・実行可能性であり禁止・許可の規範ではない。拒否や部分実行はない。家庭の比較はない |
| 同上 | **スキルレベル**: 同じタスクを3回繰り返し、物体の個体や位置を変える | §IV、Fig.3 | 訂正 | スキルパラメータ | 新しい個体 | 実機 | 同じタスクの反復 | 定量 (訂正回数の減少) | A △ | 規範ではない |
| Scheutz, Thielstrom, Abrams, "Transparency through Explanations and Justifications in Human-Robot Task-Based Communications", IJHCI 38(18–20), 2022 [本文確認] https://doi.org/10.1080/10447318.2022.2091086 | **マグ拒否デモ**: "Give me the mug, Andy." → "I should not give you the mug because it belongs to Ravenna, and I need Ravenna's permission." | §4.1、Fig.2 (動画 PermissionFailure.mp4、未視聴) | 設計者が知識ベースに登録 (belongsTo(mug,ravenna) と、許可なく他人の物を使うのは不適切という原理) | 論理規則 (前件=条件、後件=:isProper(did(A,use(X)))、give の前提条件として照合)。拒否理由は前件から生成 | 単一の物体 | 所有の事実は知識ベースで与えられている | 単発の依頼を規範的前提条件で検査する | 拒否と理由説明。定性デモのみ | B △ (登録済みの規範を後続依頼に適用)、C △ (条件と行為を分けている) | 住人による教示ではない。包括的な依頼でも部分実行でもない |
| 同上 | **安全デモ**: 「ナイフを放して」→ 人が前にいるので拒否 | §4.4、Fig.5 | 設計者 (一般安全規範) | 論理規則 | ― | 状態は既知 | 単発 | 拒否・定性 | ― | 常識的な安全規範で、家庭固有ではない |
| Briggs & Scheutz, "Sorry, I Can't Do That", AAAI Fall Symp. AI-HRI 2015 [本文確認] https://cdn.aaai.org/ocs/11709/11709-51307-1-PB.pdf | Nao が felicity 条件 (知識・能力・目標の優先度とタイミング・社会的役割と義務・規範的許容性) で命令を拒否する | §Felicity conditions、§Example interaction | 設計者 | 信念の推論規則 (DIARC) | ― | 既知 | 単発 | 拒否・説明・人の追加情報による撤回。定性 (proof-of-concept と明記) | 拒否の先行例 | 物体操作や家庭ルールは扱わない |
| Kasenberg, Roque, Thielstrom, Scheutz, "Engaging in Dialogue about an Agent's Norms and Behaviors", NL4XAI 2019 [本文確認] https://arxiv.org/abs/1911.00229 | ユーザが自然言語で規範を追加・削除し (仮定的な追加も可)、計画エージェントが説明する。買い物ドメイン | §2、Fig.1 | ユーザの明示 (自然言語) | 時相論理 VEL (G/F + 述語の連言、変数の量化)。CCG で解析する | 物体変数の量化により、未列挙の物体にも適用される | シミュレーション (記号状態) | 規範集合を変えると計画が変わる | 規範違反を最小化する計画と説明。定性 | B △、C △ (分解表現)、D △ (規範を変えて同じ課題) | ロボットの実機や知覚はない。家庭ではない。定量評価はない |
| Brawer et al., "Interactive Policy Shaping for HRC with Transparent Matrix Overlays", HRI 2023 [本文確認] https://scazlab.yale.edu/sites/default/files/files/HRI_2023___Chefbot.pdf | 言語指示 (テンプレート) から prohibit / permit / transfer の if-then オーバーレイを作り、学習済み方策に重ねる。料理の共同作業 | §3、§4、Fig.5、Table 6 (付録) | ユーザの明示 (テンプレート化した音声) | 記号の if-then 規則 (条件 ⇒ ¬行為)。禁止・許可の種別あり。Prolog | 新しい食事の選好 (シミュレーションで50種) | 状態は Boolean ベクトル (既知) | 進行中の協調で付けたり外したりする | シミュレーションは定量 (方策適応)、実機は定性の proof-of-concept | C △ (分解と禁止/許可の種別)、B △ | 物体の属性に基づく家庭ルールではない。部分完遂の評価はない |
| Ayub & Wagner, "What am I allowed to do here?", ICSR 2020 [本文確認] https://arxiv.org/abs/2009.05105 | Pepper が場所ごとに最大3問の yes/no 質問で、行為 (talkLoudly 等6種) の許可を学ぶ | §3.3、§4.2、Table 1–2 | 人への質問 (実験者がキーボードで回答) | 文脈ごとの Dempster-Shafer 規範 (文脈・行為・義務/禁止/許可) | 未見の場所 (シーン認識) | 画像からシーンを推定 (VGG16) | ― (規範を使った推論は今後の課題と明記) | 学習結果の表のみ | 低 | 物体操作も後続指示もない |
| Malle, Rosen, Chi, Berg, Haas, "A General Methodology for Teaching Norms to Social Robots", RO-MAN 2020 [本文確認] https://cs.brown.edu/people/er35/publications/roman2020.pdf | 規範の収集実験 (文脈ごとの処方・禁止、N=80) と Norm-Learning Game の構想 | §IV–V、Fig.1–2 | 人から収集 | 文脈 → 処方/禁止 | ― | ― | ― | 構想と人の実験 | 低 (構想) | ロボット実装の評価はない |
| GRACE (Doğan et al.) arXiv 2409.16879 [本文冒頭のみ確認] | 家庭内の行為の社会的適切さを、LLM と人の説明で予測する (MannersDB) | §III–V、Table I–III | 常識 (LLM) + 人の説明 | スコア | データセット上の場面 | 画像の要約 | ― | 定量 (RMSE 等) | 低 | 教示ルールの再利用も操作もない |
| NormAct arXiv 2606.27826 [要旨のみ] | 550場面。暗黙の社会規範 (所有・プライバシーを含む) に従いながら目標を達成するか | 要旨 | 常識 (暗黙) | ― | 未確認 | 未確認 | 単発の目標 | 目標達成率と規範遵守率を分けて測る (67.3% vs 26.4%、二次情報) | D △ (2指標を分ける設計は近い) | 規範は教示されず暗黙。家庭固有ではない |
| ActOwL arXiv 2509.12754 / Artificial Life and Robotics 2025 [要旨のみ] / COIN arXiv 2605.28087 [要旨のみ] | 質問による所有推定 | 要旨 | 人への質問 + LLM | 所有の確率・集合 | 新しい物体 | シミュレーション・実機 (ActOwL) | ― | 所有推定の精度のみ (要旨の範囲) | 低 | 規範による行為の判定は要旨に記載なし |

---

## 3. 主張ごとの判定 (担当分野から)

- **A. 教えられたルールを別の物体に適用する → 既出**
  - 決め手は Tan et al. 2019。シナリオ1 (叱責 → ほかの赤い物体にも知覚ヒューリスティックで適用) とシナリオ3 (帰納した規範で未教示の物体4を拒否) が実機の定性デモ、Table 1 がシミュレーションの定量評価。DROC (新しい個体・タスクへの知識再利用) も該当する。
  - CoGround に残る差は、属性述語 (fragile 等) を知覚から得ることと、不明な属性を undetermined として保留すること。Tan は所有確率を閾値と比べて実行するため、保留という扱いがない。

- **B. 保存したルールと後続の独立した指示を照合する → 既出 (定性・小規模の定量)**
  - Tan シナリオ2: 片づけ中に教わった所有規範を、別のユーザによる別の依頼に再利用して拒否した。
  - DROC Table II: 訓練タスクの訂正を別のテストタスクで検索して再利用し、訂正回数が減った。
  - Kasenberg 2019: 自然言語で追加した規範が後の計画を変える。
  - 残る差は2点。(i) **禁止・義務の規範**を (DROC は選好・実行可能性を扱う) (ii) **包括的な依頼の中で、物体ごと・行為ごとに**適用判定する組み合わせ。これを先行研究と同じ入出力で示した例は、自分の担当範囲では見つからなかった。差分は小さい。

- **C. 分解 (対象・適用条件・規範) が未教示の組み合わせでの判断に寄与する**
  - **手法の先取性 → 既出。** Tan の forbid(Φ,O) :- 条件述語、Scheutz 2022 の規範規則 (前件と行為の前提条件)、Kasenberg の VEL、Brawer 2023 の prohibit / permit オーバーレイ、Ayub/Sarathy の (文脈, 義務演算子, 行為)。どれも同等の構造化表現を持つ。LLM で自然言語から (N, S, T, C) へ「コンパイル」する点は実装上の差に留まる。
  - **効果の実証 → 証拠不足 (差分候補)。** 分解しない方式 (原文を直接読む、原文を検索して読む) と比べた対照評価は、担当範囲で見つからなかった。

- **D. 家庭固有ルールの違いを反映して、包括的な依頼の実行可能部分を完遂する → 差分候補 (評価設計として)**
  - Tan の Table 3 (collectAll/trashAll) は、包括的な依頼で回避と実行の誤りを同時に数えている。シナリオ1は部分完遂の定性デモ。
  - ただし、**同じ場面・同じ指示で家庭ルールだけを入れ替えた対の比較**や、禁止違反率と許可対象の完遂率を分けた報告は見つからなかった。NormAct は2指標を分けるが、規範は暗黙の常識であり教示されたものではない。
  - したがって「機能の初出」は主張できない。対照評価の設計として差分候補になる。

---

## 4. 最も強い反例3件

1. **Tan, Brawer, Scassellati, AAAI 2019 "That's Mine!"**
   - 片づけという包括的な依頼の中で、人の叱責を規範・物体固有の許可・所有に分けて取り込む。それを未教示の個体に適用して部分実行し (シナリオ1)、後から来た別ユーザの別依頼を拒否する (シナリオ2)。
   - A・B・D の定性版と、C の「分解表現」を一つの論文で示している。シミュレーションでは定量評価もある。
   - 欠けている点: シナリオごとに条件が違う (シナリオ3は所有が既知、シナリオ1は叱責で獲得、シミュレーションは正解の所有を与える)。単一の実証として扱ってはいけない。義務は扱わない。家庭ルールを入れ替えた対の比較はない。分解のアブレーションもない。
2. **Zha et al. DROC (arXiv 2311.10678)**
   - 実機で、利用者の言語訂正を知識ベースに蒸留し、**別のタスク** ("Clean the table" など) で意味と視覚の類似から検索して再利用する。対照 (Ours–R) と比べた定量評価があり、主張Bの「関連ルールを選択して後続依頼の行動を変える」に最も近い。
   - 欠けている点: 対象は選好と実行可能性であり、禁止・許可の規範や拒否・部分実行は扱わない。試行は少ない (各3試行)。分解しない自由文の知識を使う。
3. **Scheutz, Thielstrom, Abrams, IJHCI 2022 (+ Briggs & Scheutz 2015)**
   - 所有規範 (belongsTo + 許可原理) を物体操作の命令の前提条件として照合し、拒否と理由説明をする実機デモがある。
   - 条件と行為を分けた論理規範で、後から来た命令を検査する機構を先に示している。
   - 欠けている点: 規範は設計者が登録したもので、住人の教示ではない。単発の命令で、部分実行はない。評価は定性デモのみ。

次点: Brawer et al. HRI 2023 (音声から prohibit / permit の if-then ルールを作り方策に重ねる。Tan と同じラボ)、Kasenberg et al. 2019 (自然言語で規範を追加・削除し、時相論理で計画)。

---

## 5. 他の担当に再読してほしい文献

- **Tan et al. 2019** (統合役へ): 動画 https://bit.ly/2z8obET を視聴し、シナリオ1で叱責前に「作業台を片づけて」の対象物と所有情報がどう与えられたか、自然言語理解がテンプレートかどうかを確認してほしい。
- **DROC** (S2・S3 へ): 採録会議 (ICRA 2024 かどうか未確認)、Table II の各タスクの物体状態の入力方法、知識に禁止型 ("don't …") の訂正が含まれるか。
- **Brawer et al. HRI 2023** (S3 へ): prohibit / permit オーバーレイは、規範・例外・優先度を持つ記号的制約であり、Safety Chip などとの関係を確認してほしい。
- **NormAct 2606.27826、VestaBench (EMNLP 2025 industry)** (S2・S3・統合役へ): 目標達成と規範遵守を分けて測る評価設計が主張Dの評価に近い。規範が明示的に与えられる条件があるか、本文を確認してほしい。
- **Kasenberg & Scheutz 系 (inverse norm conflict resolution AIES 2018、norm conflict resolution AAAI 2018)** (S3 へ): 時相論理の規範とその優先度。本文は未確認。
- **Oldenburg & Tan, AAMAS 2024 (arXiv 2402.13399)**: ベイズ的なルール帰納による規範の学習。マルチエージェントのため担当外で、要旨も未確認。

---

## 6. 未確認のまま残ったもの

- Tan et al. の動画の内容 (シナリオ1の初期条件や自然言語解析の方式)。本文の文章とキャプションだけで判断した。
- Scheutz 2022 と Briggs 2015 のデモ動画は未視聴。
- DROC の採録会議名、知識に禁止型の訂正が入るかどうか。
- Sarathy, Scheutz & Malle 2017 (CogInfoCom)、Malle & Scheutz の規範ネットワークの章、Kasenberg & Scheutz 2018 (2本)、Jackson & Williams の noncompliance 研究、Mohan & Laird 2014、Kirk & Laird のゲームルール学習は書誌確認のみで本文は未読。Rosie はタスクと概念の学習であり、許可・禁止ルールの例は見つからなかった。
- "Learning Ownership based on Theory of Mind" (2023、Semantic Scholar の被引用リストにある) は原文を特定できなかった。
- NormAct、ActOwL、COIN、EgoAsk、ROBOTVALUES、2507.16124 は要旨か二次情報のみ。ActOwL の著者名は未確認。
- 2024〜2026年の LLM 系で「住人が教えた禁止・許可を保存し、後続の包括的な依頼に物体ごとに適用して部分実行する」HRI 研究は、担当範囲の検索では見つからなかった。ただし探しきったとは言えない。Google Scholar の被引用は直接は使えず、OpenAlex と Semantic Scholar で代用した。
