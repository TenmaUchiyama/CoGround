# 引用をたどる調査（2026-11-23）

規範の表現とルールの検査に関する 7 本を引用している論文を OpenAlex から取り、家庭・HRI・AR に関係するものを題名と要旨で絞った。

- 実行：`node scripts/cites.js`（結果は `data/` に出る。OpenAlex に連絡先は送っていない）
- `data/seeds.json`：種の 7 本と被引用数
- `data/pool_cites.json`：取れた 620 件（引用元と、キーワード検索 6 本の結果）
- `data/search_log.json`：キーワード検索の語と件数
- `data/shortlist.txt`：要旨を読んだ 21 件の OpenAlex ID

結果のまとめは `reports/設計要件と新規性 ルールの照合と修正.md` の 4 節。

限界：題名と要旨だけで絞った。要旨が OpenAlex に無い論文がある。Safety Chip と VeriPlan の引用元（計 220 件）は、キーワードと題名の目視で絞っただけである。TidyBot の引用元は、件数が多く取得に失敗したので入れていない。
