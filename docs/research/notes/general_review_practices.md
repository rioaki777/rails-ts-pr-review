# 汎用コードレビュー観点（言語非依存）: エンジニアリングガイドと実証研究から

調査日: 2026-10-28。凡例: **Sev** = 既定の重要度（must = マージ前に対応必須、should = 強く推奨／理由があれば見送り可、nit = 軽微・任意）。**Scope** = Diff = diff だけで判断可能、Repo = 周辺ファイル・呼び出し元・設定・履歴など広いコンテキストが必要、PR = PR 説明・Issue・チケットが必要。
Sev と Scope の割り当ては、引用元の内容をもとにした筆者の判断である（例外は明記）。Google eng-practices は数年前からある文書だが現在も公開・維持されており、権威ある基準として扱える。2023 年以降に改訂されたかは確認できなかった（Gaps 参照）。

## Q1. 主要なエンジニアリングガイドが定義するレビュー観点

### Takeaway
業界の標準的な基準は Google Engineering Practices の「What to look for」。観点は、設計・機能・複雑さ（過剰設計を含む）・テスト・命名・コメント・スタイル・一貫性・ドキュメント・全行レビュー・コンテキスト・良い点。最優先は「設計」で、合否の基準は「システム全体のコード健全性を下げないこと」。スタイルの好みでブロックしてはならず、そうした指摘は「Nit:」とする。

### Cited Findings
- 観点の一覧: Design / Functionality / Complexity / Tests / Naming / Comments / Style / Consistency / Documentation / Every Line / Context / Good Things — [Google eng-practices: What to look for](https://google.github.io/eng-practices/review/reviewer/looking-for.html)
- 「レビューで最も重要なのは CL 全体の設計」。各部分がうまく噛み合っているか、この変更がこのコードベース（またはライブラリ）に入るべきものかを確認する — [同上](https://google.github.io/eng-practices/review/reviewer/looking-for.html)
- Functionality: 作者の意図どおりに動くか。エッジケース、並行性、エンドユーザーと将来の開発者のニーズも考慮する — [同上](https://google.github.io/eng-practices/review/reviewer/looking-for.html)
- Complexity: 行・関数・クラスの各レベルで確認する。「複雑すぎる」とは通常「読み手がすぐに理解できない」ことを指す。過剰設計には特に注意し、推測に基づく将来のためではなく、今ある問題を解くべきである — [同上](https://google.github.io/eng-practices/review/reviewer/looking-for.html)
- Tests: 必要に応じて unit / integration / e2e テストを求める。「コードが壊れたときにテストは本当に失敗するか」を確認する — [同上](https://google.github.io/eng-practices/review/reviewer/looking-for.html)
- Comments は「何をしているか」ではなく、主に「なぜそのコードが存在するか」を説明すべきである — [同上](https://google.github.io/eng-practices/review/reviewer/looking-for.html)
- Style: 「個人的なスタイルの好みだけを理由に CL をブロックしない」。任意の指摘には「Nit:」を付ける。大規模なスタイル修正は別 CL に分ける — [同上](https://google.github.io/eng-practices/review/reviewer/looking-for.html)
- Consistency: スタイルガイドが要件として定める事項については、スタイルガイドが絶対的な権威である。推奨にとどまる事項は判断に委ね、局所的な不一致が混乱を招かない限りスタイルガイドを優先する — [同上](https://google.github.io/eng-practices/review/reviewer/looking-for.html)
- Documentation: ビルド・テスト・操作・リリースの方法が変わる場合は、関連ドキュメントが更新されているか確認する — [同上](https://google.github.io/eng-practices/review/reviewer/looking-for.html)
- Every line: 割り当てられたコードは全行を見る。生成コードやデータファイルは流し読みでよいが、人が書いたコードはすべて理解する — [同上](https://google.github.io/eng-practices/review/reviewer/looking-for.html)
- Context: diff だけでなく、ファイル全体やシステム全体を見る。「システムのコード健全性を下げる CL を受け入れない」 — [同上](https://google.github.io/eng-practices/review/reviewer/looking-for.html)
- Good things: 良い実践や改善は認めて伝える。メンタリングとしての効果がある — [同上](https://google.github.io/eng-practices/review/reviewer/looking-for.html)
- 同ページ末尾のまとめチェックリスト: 設計は妥当か／ユーザーに役立つ機能か／UI 変更は妥当か／並行処理は安全か／複雑さは必要最小限か／推測で入れた機能はないか／適切に設計された unit テストがあるか／名前は明確か／コメントは有用で「なぜ」を説明しているか／ドキュメントは適切か／スタイルガイドに従っているか — [同上](https://google.github.io/eng-practices/review/reviewer/looking-for.html)
- Google でレビューが導入された主目的は、バグ発見よりも可読性と保守性だった。後から加わった利点として、スタイルと設計の一貫性、十分なテストの担保、単独の開発者が無審査で任意のコードを入れられないことによるセキュリティ向上が挙げられている。レビューに期待されるテーマは education / maintaining norms / gatekeeping / accident prevention の 4 つ — [Sadowski et al., "Modern Code Review: A Case Study at Google", ICSE-SEIP 2018](https://sback.it/publications/icse2018seip.pdf)

### Inferences
- 汎用レビュー観点の基本構成は、Google の 12 観点に、デプロイ安全性・互換性・可観測性などの横断観点（Q5）を加えたものにするのが妥当。Google の一覧には、並行性以外の運用・デプロイ観点が明示されていない。
- AI レビュアーの場合、「Every line」は全行を読むことを指すが、コメントは重要度の高いものに絞るべきである（Q2 の CodeRabbit 研究を参照）。

### Gaps
- Google eng-practices が 2023 年以降に改訂されたかは確認できなかった。GitHub のコミット履歴を見ていない。

## Q2. 実証研究: レビューで実際に見つかるもの、見逃されるもの

### Takeaway
現代的なコードレビューで見つかる指摘の大半は、機能バグではなく保守性（evolvability）に関するものである。最大の作業は変更内容の「理解」であり、変更が小さいほど速く、質の高いレビューになる。レビューで見逃されやすいのは意味的・ロジック的なバグ。AI レビュアーのコメントは約 6 割が却下されている。主な理由は誤検知、冗長な指摘、スコープ外の指摘、プロジェクトの意図とのずれ。

### Cited Findings
- Microsoft（Bacchelli & Bird, ICSE 2013）: 欠陥発見は依然として主な動機だが、レビューは期待されるほど欠陥に関するものではなかった。知識移転、チームの状況把握、代替案の創出が重要な成果として挙がっている。コードと変更の「理解」がレビューの鍵だが、ツールはほとんど支援していない。データは管理者 165 名と開発者 873 名へのサーベイ、17 名へのインタビュー、CodeFlow コメント 570 件の分析 — [Microsoft Research](https://microsoft.com/en-us/research/?p=164195); [ICSE 2013 page](https://2013.icse-conferences.org/content/expectations-outcomes-and-challenges-modern-code-review.html)
- Google（2014-2016 年の約 900 万 change を分析）: 変更行数の中央値は 24 行。約 90% の変更は 10 ファイル未満で、10% 超は 1 行だけの変更。レビュアー数の中央値は 1 で、80% 超の変更は修正の往復が 1 回以内。レビュー全体のレイテンシの中央値は 4 時間未満。開発者がレビューに使う時間は週平均 3.2 時間（中央値 2.6 時間） — [Sadowski et al. 2018](https://sback.it/publications/icse2018seip.pdf)
- 変更あたりのコメント数は変更行数とともに増え、約 1250 行で平均 12.5 件のピークに達する。これより大きい変更は自動生成コードや大量削除であることが多く、コメント数は減る。先行研究では、変更が大きいほど有用なコメントが減り、レイテンシが伸びる — [Sadowski et al. 2018](https://sback.it/publications/icse2018seip.pdf)
- 入社 1 年以内の開発者の変更には、平均で 2 倍超のコメントが付く。質問形式のコメントは作者から「有用でない」と見なされやすいという先行研究がある — [Sadowski et al. 2018](https://sback.it/publications/icse2018seip.pdf)
- Mäntylä & Lassenius（IEEE TSE 2009, "What Types of Defects Are Really Discovered in Code Reviews?"）: レビューで見つかる欠陥の約 75% は evolvability（保守性）に関するもので、機能欠陥は少数派。数値は二次情報で 75% / 77% / 60-75% と揺れており、原典の数字は未確認 — [Wikipedia: Code review](https://www.Wikipedia.com/wiki/Code_review); [arXiv 2411.11401（77%/23% と引用）](https://arxiv.org/pdf/2411.11401)
- レビューで見逃されたバグ（SmartSHARK, MSR 2022）: 意味的バグが約 51% で最多。次いでビルドや静的解析チェック関連 — [arXiv 2205.09428](https://arxiv.org/pdf/2205.09428)
- Empirical Software Engineering 2023 の研究は、レビューで見つかった欠陥 1,323 件を分析し、原理的には最大 76% を静的解析ツールで検出できる可能性があると推定した（検索結果の要約による。原典は未読） — [検索結果: Static analysis vs review defects](https://repository.tudelft.nl/file/File_9eb1b79b-a0f2-4631-9e2c-d71d4081a138)
- セキュリティ（OpenSSL / PHP のレビューコメント 135,560 件, EMSE 2024 / ICSE 2025 journal-first）: レビュアーは 40 の脆弱性カテゴリのうち 35 でセキュリティ懸念を指摘していた。ただし、解決策をめぐる意見の相違から、認識されただけで修正されなかった指摘もかなりの割合あった — [ICSE 2025 JF](https://conf.researchr.org/details/icse-2025/icse-2025-journal-first-papers/13/Toward-Effective-Secure-Code-Reviews-An-Empirical-Study-of-Security-Related-Coding-W)
- MCR-Bench（arXiv 2026 プレプリント）: レビュー欠陥を functional / evolvability / test / security に分類している。functional ではロジック欠陥が最多で、次いでインターフェース問題、チェックの欠落・不足。evolvability は可読性・構造・保守性が中心 — [arXiv 2608.27442](https://arxiv.org/pdf/2608.27442)
- AI レビュー（CodeRabbit, arXiv 2026。239 リポジトリ・10,191 PR・31,073 コメントを分析）: 受け入れ 36.4%、議論発生 7.3%、却下 56.3%。却下の主な理由は誤検知、冗長な指摘、スコープ外の指摘、開発者の意図やコーディング慣習とのずれ。agentic レビューは functional 寄りだが、functional 指摘のほうが無効になりやすい — [arXiv 2607.03316](https://arxiv.org/abs/2607.03316)
- LLM レビュー（Atlassian との共同研究, 2025 プレプリント）: readability・bug・maintainability のコメントは、design のコメントより解決されやすい（アグリゲータ経由の要約。原典は未確認） — [themoonlight summary](https://www.themoonlight.io/en/review/rethinking-code-review-workflows-with-llm-assistance-an-empirical-study)
- AI レビューの産業事例（Beko, 2025 年の修士論文）: 238 名に導入し、AI コメントの 73.8% に開発者が反応した。一方で PR のクローズ時間は伸び、誤った提案も報告された — [Bilkent repository](https://repository.bilkent.edu.tr/items/8e7ac28e-5120-4c6e-84e3-e7d288c336f0)
- MSR 2025: 曖昧で実行に移せない人間のレビューコメントは「ノイズ」として学習データを劣化させる — [MSR 2025](https://2025.msrconf.org/details/msr-2025-technical-papers/41/Too-Noisy-To-Learn-Enhancing-Data-Quality-for-Code-Review-Comment-Generation)

### Inferences
- AI レビュースキルで最もリスクが大きいのは「見逃し」より「ノイズ（誤検知・冗長・スコープ外）」である。指摘は具体的な根拠（該当行・再現条件）がある場合に限り、確信が持てないものは question として出す設計がよい。
- lint や型チェックで検出できる問題（静的解析で最大 76% という推定がある）は、ツールに任せるか重要度を下げる。そのうえで、人間も見逃しやすい意味的・ロジック的バグ（SmartSHARK で約 51%）、インターフェースの不整合、チェックの欠落に注力すべきである。
- evolvability 指摘は件数こそ多いが、多くは should / nit 相当である。must は機能・セキュリティ・データ破損に限定するのが妥当。

### Gaps
- Bacchelli & Bird のコメント分類の内訳（欠陥コメントの比率など）は一次 PDF で確認できず、記載していない。
- Mäntylä & Lassenius の正確な比率は原典未確認。
- Microsoft の Bosu et al.「Characteristics of Useful Code Reviews」（MSR 2015）は検索結果に出てきたが、未読のため記載していない。
- 2024-2026 年の ICSE / FSE / MSR 本会議で、人間のレビューの欠陥分類を扱った論文は網羅できていない。

## Q3. PR の意図と実際の diff の照合（説明の質・スコープ・サイズ）

### Takeaway
PR は「1 つの自己完結した変更」であるべきで、説明には「何を・なぜ」と既知の欠点を書く。リファクタリングと機能追加・バグ修正は分けるべきである。目安として 100 行程度は妥当、1000 行は通常大きすぎる。レビュー速度は約 500 LOC/時、1 回あたり 200-400 行が上限とされる（2006 年の Cisco 研究。古いデータである点に注意）。

### Cited Findings
- 小さい CL とは「1 つの自己完結した変更」である。関連テストを含み、マージ後もシステムが動き続けること。「100 行は通常妥当、1000 行は通常大きすぎる」。ファイル数も重要で、大きすぎる CL はレビュアーが即却下してよい — [Google: Small CLs](https://google.github.io/eng-practices/review/developer/small-cls.html)
- リファクタリングは機能変更・バグ修正とは別の CL にする。ローカル変数のリネーム程度なら同じ CL でよい。ロジック変更にはテストを同じ CL に含める — [同上](https://google.github.io/eng-practices/review/developer/small-cls.html)
- 小さい CL の利点: レビューが速く丁寧になる、バグが入りにくい、却下されたときの無駄が少ない、マージやロールバックが容易 — [同上](https://google.github.io/eng-practices/review/developer/small-cls.html)
- 大きくてもよい例外: ファイル全体の削除や、信頼できる自動リファクタリングツールの出力 — [同上](https://google.github.io/eng-practices/review/developer/small-cls.html)
- CL の説明は恒久的な記録である。1 行目は具体的な命令形の要約にし、本文には解決する問題、その手法を選んだ理由、既知の欠点、背景（バグ番号・ベンチマーク・設計書）を書く。外部リンクだけに頼らない。「Fix bug」「Phase 1」は悪い例 — [Google: CL descriptions](https://google.github.io/eng-practices/review/developer/cl-descriptions.html)
- レビュー中に CL が変わることがあるので、submit 前に説明が実装と一致しているか見直す — [同上](https://google.github.io/eng-practices/review/developer/cl-descriptions.html)
- SmartBear / Cisco（2006）: 1 回のレビューは 200-400 行未満、60-90 分で 70-90% の欠陥を発見できる。500 LOC/時を超えると欠陥発見密度が大きく下がる。ただし、特定のチーム・コードベースのデータである点に注意 — [SmartBear best practices](https://smartbear.com/learn/code-review/best-practices-for-peer-code-review/); [AgileConnection summary](https://agileconnection.com/article/largest-case-study-code-reviews-ever)
- AI レビューの有用性は PR 説明の質と設計上のコンテキストに依存し、問題記述がないと LLM の正誤判定の精度が下がる（WirelessCar 事例、論文。二次要約経由） — [検索結果要約: Bilkent / 関連研究](https://repository.bilkent.edu.tr/items/8e7ac28e-5120-4c6e-84e3-e7d288c336f0)

### Inferences
- AI レビュースキルでは、最初に「PR 説明と diff の整合チェック」を行うべきである。確認項目は、説明にない変更、説明にあるのに実装されていない項目、無関係なリファクタリングや整形の混入、テストの欠如。
- PR 説明が空または不十分なときは、スキル側で should 指摘として説明の補足を求める。そのうえで、意図が推測に依存する指摘は question にする。

### Gaps
- 行数閾値と欠陥流出率の関係について、2023 年以降の大規模な実証データは見つからなかった。

## Q4. 指摘の分類とコミュニケーション（重要度ラベル・言い回し）

### Takeaway
Conventional Comments の書式「`<label> [decorations]: <subject>`」が事実上の標準である。label は praise / nitpick / suggestion / issue / todo / question / thought / chore / note、decoration は blocking / non-blocking / if-minor。Google は Nit / Optional（Consider） / FYI を用いる。日本の現場では must / imo / nits の 3 段階がよく使われる。トーンについては、人ではなくコードに言及し、理由を説明すること。

### Cited Findings
- Conventional Comments の書式: `<label> [decorations]: <subject>` + `[discussion]`。label: praise（誠実なものに限り、毎レビュー最低 1 件）、nitpick（好みの問題で non-blocking）、suggestion（何を・なぜ）、issue（具体的な問題。suggestion と対で書く。確信がなければ question）、todo（小さいが必要な変更）、question、thought（non-blocking）、chore（受け入れ前に必要なプロセス作業。手順へのリンクを付ける）、note（常に non-blocking）。拡張ラベルとして typo / polish / quibble がある — [conventionalcomments.org](https://conventionalcomments.org/)
- Decorations: `(blocking)` / `(non-blocking)` / `(if-minor)`。`(security)` や `(test)` のような独自の decoration も可だが、少数で明確なものにとどめる。統一された構造は機械的にパースしやすい — [同上](https://conventionalcomments.org/)
- Google の重要度ラベル: Nit（直すべきだが影響は小さい）、Optional / Consider（任意）、FYI（今回の CL では対応不要）。ラベルを付けないと、作者は全コメントを必須と受け取りがちになる — [Google: How to write code review comments](https://google.github.io/eng-practices/review/reviewer/comments.html)
- トーン: 開発者ではなくコードについてコメントする。悪い例は「なぜ **あなたは** ここでスレッドを使ったのか」。変更を求める理由を説明する。修正の責任は作者にあるが、具体的な提案やコードを示すことも有用。良い点は理由付きで褒める — [同上](https://google.github.io/eng-practices/review/reviewer/comments.html)
- 理解できないコードについて説明を求めたら、レビューツール上で説明してもらうのではなく、コードの明確化（必要ならコメントの追加）を求める。「レビューツール上だけの説明は将来の読み手の役に立たない」 — [同上](https://google.github.io/eng-practices/review/reviewer/comments.html)
- 日本の慣習: [must] は必須、[imo] は意見・好み、[nits] は些細な指摘（インデントや誤字など）。ラベルの使い方が人によってばらつき、質問の多用で着地点が分かりにくくなったため、ラベルの意味をドキュメント化したチーム事例がある — [zenn.dev 記事](https://zenn.dev/awsmgs/articles/b4f6bcf1cfd3aa); [speakerdeck: レビューのやり方を整理した話](https://speakerdeck.com/ken7253/rebiyunoyarifang-wo-tiyotuto-zheng-li-sitahua)
- nit は理由を示さずに見送ってよい（take it or leave it）という運用例がある — [Graphite: What are nits](https://graphite.com/blog/what-are-nits)

### Inferences（スキル用の推奨分類）
- 重要度は 3 段階にする。**must**（blocking: バグ、データ破損・損失、セキュリティ、互換性破壊、テスト欠如による回帰リスク）、**should**（non-blocking だが強く推奨: 設計・保守性・可観測性）、**nit**（好み・軽微な点、見送り可）。これに Conventional Comments の label（issue / suggestion / question / nitpick / praise）を組み合わせる。例: `issue (blocking): ...`、`suggestion (non-blocking): ...`、`question: ...`、`nitpick: ...`。
- 確信度が低い指摘は issue ではなく question として出す（Conventional Comments の指針どおり）。AI の誤検知による却下を減らす効果も期待できる。
- 各指摘には「何が問題か」「なぜ問題か（影響）」「具体的な修正案」を含める。主語は「このコード」にし、作者を主語にしない。

### Gaps
- must / imo / nits の公式な出典（特定企業のガイドライン）は特定できなかった。Mercari・Cookpad・SmartHR の公式ブログに当たる時間がなかった。

## Q5. 横断的関心事（ファイル種別に依存しない観点）

### Takeaway
Google のガイドが明示している横断観点は並行性・UI・ドキュメント程度で、デプロイ安全性（後方互換、ロールバック、マイグレーション、feature flag）、可観測性、i18n は権威ある単一の情報源では体系化されていない。見つかったのはコミュニティのチェックリストや GitLab の運用ドキュメントで、内容はおおむね一致している。DB マイグレーション、API 契約、feature flag に最も注意を払い、チェックリストはリスクに応じて適用する、というものである。

### Cited Findings
- 並行処理: 「並行処理は安全か」が Google のまとめチェックリストに含まれる。デッドロックや競合状態にも言及がある — [Google: What to look for](https://google.github.io/eng-practices/review/reviewer/looking-for.html)
- 小さい CL はロールバックしやすい（ロールバック容易性はサイズ方針の根拠の一つ） — [Google: Small CLs](https://google.github.io/eng-practices/review/developer/small-cls.html)
- 互換性チェックの質問例: 公開 API や他サービスとの契約を壊さないか、古いクライアントは動くか、マイグレーションは段階的デプロイに耐えるか、flag・バージョン・フォールバックは必要か。フィールド・enum・ペイロードの小さな変更は、diff 上では気付きにくい形で他サービスを壊しうる（コミュニティ記事） — [Kodus: Code Review Checklist](https://kodus.io/en/code-review-checklist/)
- ロールバックのリスク分類: コードのみの変更、追加的な API 変更、flag 付きの機能は安全。破壊的マイグレーションやデータ変換は最も危険。新しいカラムは nullable にし、破壊的変更はそれに依存するコードと同じリリースに含めない。flag にはオーナーと廃止日を設け、本番の既定は off にする（コミュニティ / ツール系の情報源で、権威性は低い） — [Rollback checklist](https://smithery.ai/skills/thoreinstein/rollback); [Feature Development Checklist](https://app.manifest.ly/public/checklists/3b7ca63632345cb2c6425338389d188e?modal=true)
- GitLab の運用例: 互換性 flag は非本番環境から段階的に有効化し、本番ではパーセンテージでロールアウトしながらエラー率を監視する。マイグレーションは up / down の両方を本番 DB のクローンで実行し、結果を MR に記載する — [GitLab issue](https://gitlab.com/gitlab-org/gitlab/-/issues/591312)（検索結果の要約経由。本文は未読）
- 互換性の範囲は、コードだけでなく永続化データ、モバイルクライアント、公開 API / SDK、バックグラウンドジョブ、キュー、feature flag、ロールバック手順にまで及ぶ（コミュニティ製 skill） — [legacy support adjudication skill](https://skills.cat/skills/pratyush1712/legacy-support-adjudication-skill)

### Inferences
- 下のチェックリストの横断観点（エラー処理、ログ・可観測性、互換性、flag、ロールアウト、並行性、i18n、性能）は、上記の情報源と一般的な実務知識をもとに、筆者が統合したものである。権威ある単一の出典があるわけではない。
- Rails / TS の場合、マイグレーションと API スキーマ（JSON の形、GraphQL / OpenAPI）の互換性は Repo コンテキストが必要な must 候補として扱うのが妥当。

### Gaps
- Stripe・Shopify・Netflix・Dropbox などのレビュー文化に関する一次ブログは、時間の都合で取得していない。
- i18n・ログ・可観測性をレビュー観点として実証的に扱った研究は見つからなかった。
- Atlassian のレビューチェックリストは未取得。

---

## 統合チェックリスト（スキル用ドラフト）

| # | 観点 | チェック項目（日本語） | Sev 既定 | Scope | 出典 |
|---|---|---|---|---|---|
| A1 | PR 意図 | PR 説明に「何を・なぜ」と背景（Issue・チケット）が書かれているか。「Fix bug」のような曖昧な説明ではないか | should | PR | [Google CL desc](https://google.github.io/eng-practices/review/developer/cl-descriptions.html) |
| A2 | PR 意図 | 説明と diff が一致しているか（説明にない変更や、未実装の約束がないか）。説明は最新か | should（乖離が大きければ must） | PR+Diff | [同上](https://google.github.io/eng-practices/review/developer/cl-descriptions.html) |
| A3 | スコープ | 無関係なリファクタリング、整形、依存更新が混入していないか。混入していれば別 PR を提案する | should | Diff | [Google Small CLs](https://google.github.io/eng-practices/review/developer/small-cls.html) |
| A4 | サイズ | 自己完結した 1 変更か。約 1000 行超、または多数ファイルにまたがる場合は分割を提案する（生成コード・削除は除く） | should | Diff | [同上](https://google.github.io/eng-practices/review/developer/small-cls.html); [SmartBear](https://smartbear.com/learn/code-review/best-practices-for-peer-code-review/) |
| B1 | 設計 | 変更がこのコードベース・層に属するか。既存のアーキテクチャや責務分割と整合しているか | must（設計破綻）／should | Repo | [Google looking-for](https://google.github.io/eng-practices/review/reviewer/looking-for.html) |
| B2 | 機能 | 意図どおりに動くか。エッジケース（空・null・境界値・重複・大量データ）の扱いは適切か | must | Diff+PR | 同上 |
| B3 | 機能 | ロジックの誤り（条件の反転、off-by-one、早期 return 漏れ、誤った変数）がないか。レビューで最も見逃されやすい | must | Diff | [SmartSHARK](https://arxiv.org/pdf/2205.09428); [MCR-Bench](https://arxiv.org/pdf/2608.27442) |
| B4 | 機能 | インターフェースの不整合（呼び出し元との引数・戻り値・型の契約）がないか | must | Repo | [MCR-Bench](https://arxiv.org/pdf/2608.27442) |
| B5 | 機能 | 入力検証、権限チェック、nil チェックなどの「チェックの欠落」がないか | must | Diff+Repo | 同上 |
| C1 | 複雑さ | 読み手がすぐ理解できるか。関数やクラスが過度に長い・深いネストになっていないか | should | Diff | [Google looking-for](https://google.github.io/eng-practices/review/reviewer/looking-for.html) |
| C2 | 過剰設計 | 今必要ない汎用化、抽象化、設定項目を追加していないか（YAGNI） | should | Diff | 同上 |
| C3 | 重複 | 既存ユーティリティやヘルパーで代替できる重複実装がないか | should | Repo | 同上（Context） |
| D1 | テスト | ロジック変更に対応するテストが同じ PR にあるか | must（回帰リスクが高い場合）／should | Diff | [Google Small CLs](https://google.github.io/eng-practices/review/developer/small-cls.html) |
| D2 | テスト | テストはコードが壊れたときに本当に失敗するか（アサーションが空でないか、モックし過ぎていないか） | should | Diff | [Google looking-for](https://google.github.io/eng-practices/review/reviewer/looking-for.html) |
| D3 | テスト | 異常系・境界値のテストがあるか。テスト自体が読みやすく保守しやすいか | should | Diff | 同上 |
| E1 | 命名 | 名前が意図を表しているか。冗長すぎず短すぎないか | nit／should | Diff | 同上 |
| E2 | コメント | コメントが「なぜ」を説明しているか。古いコメントや誤ったコメント、不要なコメントアウトコードがないか | nit／should | Diff | 同上 |
| E3 | 説明要求 | レビュアーが理解できなかった箇所は、PR 上の説明ではなくコードやコメントで明確にするよう求める | should | Diff | [Google comments](https://google.github.io/eng-practices/review/reviewer/comments.html) |
| F1 | スタイル | スタイルガイドの必須事項に違反していないか。好みだけの指摘は Nit にし、ブロックしない。linter で検出できるものは lint に任せる | nit | Diff | [Google looking-for](https://google.github.io/eng-practices/review/reviewer/looking-for.html); [静的解析 76% 推定](https://repository.tudelft.nl/file/File_9eb1b79b-a0f2-4631-9e2c-d71d4081a138) |
| F2 | 一貫性 | 周辺コードや既存パターン（命名、エラー処理、ディレクトリ構成）と一貫しているか | should | Repo | 同上 |
| G1 | ドキュメント | ビルド・セットアップ・API・運用手順が変わる場合、README や API ドキュメント、CHANGELOG が更新されているか | should | Diff+Repo | 同上 |
| H1 | セキュリティ | 認証・認可、入力のサニタイズ、秘密情報のハードコードや出力、インジェクションの問題がないか | must | Diff+Repo | [ICSE 2025 secure review](https://conf.researchr.org/details/icse-2025/icse-2025-journal-first-papers/13/Toward-Effective-Secure-Code-Reviews-An-Empirical-Study-of-Security-Related-Coding-W) |
| I1 | エラー処理 | 例外やエラーを握りつぶしていないか。ユーザーへのエラー表示と内部ログを適切に分離しているか。リトライやタイムアウトは妥当か | must（握りつぶし）／should | Diff | 筆者推論（業界一般。単一の権威ある出典なし） |
| I2 | 可観測性 | 障害調査に必要なログ・メトリクス・トレースがあるか。PII や秘密情報をログに出していないか | should（PII 出力は must） | Diff | 筆者推論 |
| J1 | 互換性 | 公開 API、JSON の形、enum、イベントやキューのペイロードを破壊的に変更していないか。古いクライアントや稼働中のジョブとの互換性は保たれているか | must | Repo | [Kodus](https://kodus.io/en/code-review-checklist/); [legacy skill](https://skills.cat/skills/pratyush1712/legacy-support-adjudication-skill) |
| J2 | マイグレーション | DB マイグレーションは段階的デプロイに耐えるか（追加は nullable、破壊的変更は依存コードと別リリース）。ロールバック可能か。大規模テーブルでロックしないか | must | Diff+Repo | [Rollback checklist](https://smithery.ai/skills/thoreinstein/rollback); [GitLab](https://gitlab.com/gitlab-org/gitlab/-/issues/591312) |
| J3 | ロールアウト | リスクの高い変更は feature flag などで段階的にリリースでき、即座に無効化できるか。flag にオーナーと削除計画があるか | should | Diff+PR | [Feature Dev Checklist](https://app.manifest.ly/public/checklists/3b7ca63632345cb2c6425338389d188e?modal=true); [GitLab](https://gitlab.com/gitlab-org/gitlab/-/issues/591312) |
| J4 | ロールバック | このPRを revert した場合に、データ不整合が残らないか（データ変換と書き込み形式の変更が要注意） | must（不可逆な場合）／should | Repo | [Rollback checklist](https://smithery.ai/skills/thoreinstein/rollback); [Google Small CLs](https://google.github.io/eng-practices/review/developer/small-cls.html) |
| K1 | 並行性 | 競合状態、二重実行、デッドロックがないか。冪等性は保たれているか（ジョブ、Webhook、二重送信） | must | Diff+Repo | [Google looking-for](https://google.github.io/eng-practices/review/reviewer/looking-for.html) |
| L1 | 性能 | N+1、ループ内の I/O、無制限のクエリ・ページングがないか。不要な再計算や再レンダリングがないか | should（ホットパスなら must） | Diff+Repo | 筆者推論 |
| M1 | i18n | ユーザー向け文字列のハードコードがないか。日付・時刻・タイムゾーン・数値・通貨の扱いは適切か | should | Diff | 筆者推論 |
| N1 | UI/UX | UI 変更がユーザーにとって妥当か（可能ならスクリーンショットで確認）。アクセシビリティに配慮しているか | should | PR+Diff | [Google looking-for](https://google.github.io/eng-practices/review/reviewer/looking-for.html) |
| O1 | 良い点 | 良い設計や改善があれば、理由付きで praise する（誠実なものに限る） | — | Diff | [Conventional Comments](https://conventionalcomments.org/); [Google comments](https://google.github.io/eng-practices/review/reviewer/comments.html) |

### コメント書式（推奨）
- `issue (blocking): <要旨>` + 影響 + 修正案（Sev = must）
- `suggestion (non-blocking): <要旨>` + 理由（Sev = should）
- `nitpick: <要旨>`（Sev = nit。見送り可）
- `question: <確認事項>`（確信度が低い懸念はすべてこちらにする）
- `praise: <良い点と理由>`
- 主語はコードにし、「なぜ」を必ず書く。lint で検出できる指摘や好みの指摘は最小限にする。AI レビュアーの却下理由の上位は、誤検知・冗長・スコープ外・意図とのずれ（[arXiv 2607.03316](https://arxiv.org/abs/2607.03316)）。
