# check-general チェックリスト

このファイルは scripts/extract_checklists.py で docs/research/report.md から生成。直接編集しない。

凡例は次のとおり。**既定**は重要度の初期値で、must はマージ前に必須、should は強く推奨（理由があれば見送り可）、nit は任意を表す。検証段階で上げ下げできる。**判定**は、指摘に必要な情報の範囲を表す。diff は差分だけで判断できる、repo は呼び出し元・スキーマ・設定・lint 設定などリポジトリ文脈が必要、PR は PR 説明やチケットが必要、実行は実機・CI 結果・本番統計・外部レジストリが必要、という意味だ。判定が「実行」の項目は静的レビューでは確定できないので、カバレッジ報告で「人間による確認が必要」と明示する。出典が「慣行」の項目は、権威ある単一の一次情報が見つからなかったものだ。

| # | 観点 | 既定 | 判定 | 出典 |
|---|---|---|---|---|
| GC1 | ロジックの誤り（条件の反転、off-by-one、早期 return の漏れ、変数の取り違え、単位の取り違え） | must | diff | [SmartSHARK](https://arxiv.org/pdf/2205.09428); [MCR-Bench](https://arxiv.org/pdf/2608.27442) |
| GC2 | エッジケース（空、nil/undefined、境界値、重複、大量データ、同時操作） | must | diff+PR | [Google looking-for](https://google.github.io/eng-practices/review/reviewer/looking-for.html) |
| GC3 | 呼び出し元との契約（引数、戻り値、例外、型）を壊していないか。シグネチャを変えたら全呼び出し元を確認したか | must | repo | [MCR-Bench](https://arxiv.org/pdf/2608.27442); [CR-Bench](https://arxiv.org/html/2603.11078v1) |
| GC4 | チェックの欠落（nil ガード、入力検証、状態遷移の前提条件） | must | diff+repo | [MCR-Bench](https://arxiv.org/pdf/2608.27442) |
| GC5 | 例外の握り潰し、fail-open（例外時に処理を続行・許可）、空の `rescue`/`catch` | must | diff | [OWASP Top 10:2025 A10](https://top10.owasp.org/2025); [Google TS Style](https://google.github.io/styleguide/tsguide.html) |
| GC6 | 互換性：公開 API や JSON の形、enum、イベント・キューのペイロードを破壊的に変更していないか。古いクライアントや稼働中のジョブで動くか | must | repo | [Kodus](https://kodus.io/en/code-review-checklist/) |
| GC7 | revert 時にデータ不整合が残らないか（書き込み形式やデータ変換の変更） | must（不可逆な場合）／should | repo | [Rollback checklist](https://smithery.ai/skills/thoreinstein/rollback); [Google Small CLs](https://google.github.io/eng-practices/review/developer/small-cls.html) |
| GC8 | 並行性・冪等性（競合状態、二重実行、Webhook の再送、フォームの二重送信） | must | diff+repo | [Google looking-for](https://google.github.io/eng-practices/review/reviewer/looking-for.html) |
| GC9 | 設計：変更がこの層・このコードベースに属するか、既存の責務分割と整合するか | should（設計が破綻していれば must） | repo | [Google looking-for](https://google.github.io/eng-practices/review/reviewer/looking-for.html) |
| GC10 | 複雑さ・過剰設計（今必要のない汎用化や設定項目） | should | diff | 同上 |
| GC11 | 既存のユーティリティやヘルパーで代替できる重複実装 | should | repo | 同上 |
| GC12 | feature flag の既定が安全側（OFF）か、ON/OFF 両方の経路にテストがあるか、オーナーと削除計画があるか。flag 削除 PR で死んだ分岐を残していないか | should | diff+PR | [Feature Dev Checklist](https://app.manifest.ly/public/checklists/3b7ca63632345cb2c6425338389d188e?modal=true); [GitLab](https://gitlab.com/gitlab-org/gitlab/-/issues/591312) |
| GC13 | 理解しにくい箇所を、PR 上の説明ではなくコードやコメントで明確にしているか。コメントは「なぜ」を説明しているか | should／nit | diff | [Google comments](https://google.github.io/eng-practices/review/reviewer/comments.html) |
| GC14 | 命名が意図を表しているか | nit | diff | [Google looking-for](https://google.github.io/eng-practices/review/reviewer/looking-for.html) |
| GC15 | 障害調査に必要なログ・メトリクスがあるか | should | diff | 慣行（筆者推論） |
