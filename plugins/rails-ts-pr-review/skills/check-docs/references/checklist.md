# check-docs チェックリスト

このファイルは scripts/extract_checklists.py で docs/research/report.md から生成。直接編集しない。

凡例は次のとおり。**既定**は重要度の初期値で、must はマージ前に必須、should は強く推奨（理由があれば見送り可）、nit は任意を表す。検証段階で上げ下げできる。**判定**は、指摘に必要な情報の範囲を表す。diff は差分だけで判断できる、repo は呼び出し元・スキーマ・設定・lint 設定などリポジトリ文脈が必要、PR は PR 説明やチケットが必要、実行は実機・CI 結果・本番統計・外部レジストリが必要、という意味だ。判定が「実行」の項目は静的レビューでは確定できないので、カバレッジ報告で「人間による確認が必要」と明示する。出典が「慣行」の項目は、権威ある単一の一次情報が見つからなかったものだ。

| # | 観点 | 既定 | 判定 | 出典 |
|---|---|---|---|---|
| DOC1 | 記述がコードと一致しているか（コマンド、ENV 名、設定キー、API の例、既定値）。コードを変えた PR で関連ドキュメントの更新が漏れていないか | must | repo | [Google looking-for](https://google.github.io/eng-practices/review/reviewer/looking-for.html) |
| DOC2 | セットアップ・実行手順が現状で動くか（Ruby/Node のバージョン、`bin/setup`、パッケージマネージャー） | must | repo／実行 | 同上 |
| DOC3 | API ドキュメント（OpenAPI、rswag）が実装と一致し、破壊的変更とエラーレスポンスを明記しているか | must（公開 API） | repo | 慣行 |
| DOC4 | CHANGELOG に破壊的変更と移行手順を書いているか（Added/Changed/Removed/Fixed/Security） | should | diff | [Keep a Changelog](https://keepachangelog.com/) |
| DOC5 | ADR の形式（Context/Decision/Status/Consequences）と中身（選択肢の網羅性、判断基準、帰結の客観性）。既存の ADR を書き換えず、新しい ADR で置き換えているか | should | diff | [adr.github.io](https://adr.github.io/); [Zimmermann](https://www.ozimmer.ch/practices/2023/04/05/ADRReview.html) |
| DOC6 | 文書タイプが混ざっていないか。手順を番号付きにし、コマンドはコピペで動く形にしているか | should | diff | [Diátaxis](https://diataxis.fr/compass/); [Google style](https://developers.google.com/style/highlights) |
| DOC7 | リンク切れ、アンカー切れ | should | diff+実行 | [lychee](https://github.com/lycheeverse/lychee) |
| DOC8 | コードコメントが「なぜ」を説明しているか。TODO に issue へのリンクがあるか | should | diff | [SWE Book ch.10](https://abseil.io/resources/swe-book/html/ch10.html) |
| DOC9 | 日本語の文体（です・ます／である の混在、一文 100 字以内、表記の統一）、リンクテキスト、見出しの階層 | nit | diff | [textlint preset](https://github.com/textlint-ja/textlint-rule-preset-ja-technical-writing); [Google style](https://developers.google.com/style/highlights) |
