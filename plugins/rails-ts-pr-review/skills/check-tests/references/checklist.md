# check-tests チェックリスト

このファイルは scripts/extract_checklists.py で docs/research/report.md から生成。直接編集しない。

凡例は次のとおり。**既定**は重要度の初期値で、must はマージ前に必須、should は強く推奨（理由があれば見送り可）、nit は任意を表す。検証段階で上げ下げできる。**判定**は、指摘に必要な情報の範囲を表す。diff は差分だけで判断できる、repo は呼び出し元・スキーマ・設定・lint 設定などリポジトリ文脈が必要、PR は PR 説明やチケットが必要、実行は実機・CI 結果・本番統計・外部レジストリが必要、という意味だ。判定が「実行」の項目は静的レビューでは確定できないので、カバレッジ報告で「人間による確認が必要」と明示する。出典が「慣行」の項目は、権威ある単一の一次情報が見つからなかったものだ。

| # | 観点 | 既定 | 判定 | 出典 |
|---|---|---|---|---|
| TE1 | 本体で変わった振る舞い（新しい分岐、エラー経路、バグ修正）それぞれにテストがあるか。バグ修正なら、修正前のコードで落ちる回帰テストがあるか | must | diff（本体と照合） | [SWE Book ch.12](https://abseil.io/resources/swe-book/html/ch12.html) |
| TE2 | 空振りテスト：assertion がない、`waitFor` のコールバックが空、存在確認に `query*` を使っている、`await` が漏れている、`skip`/`xit` のまま | must | diff | [Kent C. Dodds](https://kentcdodds.com/blog/common-mistakes-with-react-testing-library); [Playwright BP](https://playwright.dev/docs/best-practices) |
| TE3 | `.only`/`fit`/`focus: true` や、`binding.pry`/`debugger`/`console.log`/`save_and_open_page` の残存 | must | diff | 慣行 |
| TE4 | 外部 HTTP への実通信（WebMock/VCR、MSW、`page.route` でスタブする）。VCR カセットに秘密情報が入っていないか | must | diff | [Betterspecs](https://www.betterspecs.org/) |
| TE5 | 時刻依存（`travel_to`/`useFakeTimers` で固定する）、固定 sleep（`sleep`、`waitForTimeout`、`cy.wait(ms)`）、テスト間の順序依存や状態共有 | must | diff | [Fowler: Non-Determinism](https://martinfowler.com/articles/nonDeterminism.html); [Playwright BP](https://playwright.dev/docs/best-practices) |
| TE6 | flaky なテストを retry や skip で黙らせていないか（隔離するなら issue と理由を残す） | must | diff | [Fowler](https://martinfowler.com/articles/nonDeterminism.html) |
| TE7 | 異常系・境界値（nil、空、上限、権限外、not found、外部 API のエラー） | should | diff | [Betterspecs](https://www.betterspecs.org/) |
| TE8 | 実装詳細をテストしていないか（private メソッド、内部 state、呼び出し回数だけの検証）。モックしすぎていないか（`allow_any_instance_of`、広範な `jest.mock`） | should | diff | [SWE Book ch.12](https://abseil.io/resources/swe-book/html/ch12.html); [Testing Library](https://testing-library.com/docs/guiding-principles) |
| TE9 | テスト内にロジック（if、ループ、期待値の計算）がないか。DRY より DAMP を優先しているか。`let!`/`before` を使いすぎていないか | should | diff | [SWE Book ch.12](https://abseil.io/resources/swe-book/html/ch12.html); [Betterspecs](https://www.betterspecs.org/) |
| TE10 | FactoryBot の肥大化や連鎖 create、乱数や Faker への依存 | should | diff+repo | [Betterspecs](https://www.betterspecs.org/) |
| TE11 | Testing Library のクエリ優先順位（`getByRole` が最優先）と `user-event`、E2E のロケーターが role ベースか | should | diff | [Kent C. Dodds](https://kentcdodds.com/blog/common-mistakes-with-react-testing-library); [Playwright BP](https://playwright.dev/docs/best-practices) |
| TE12 | スナップショットの乱用や、意図の分からない一括更新（`-u` で更新した差分） | should | diff | [Jest Snapshot BP](https://jestjs.io/docs/snapshot-testing#best-practices) |
| TE13 | 統合点（コントローラ→DB、API クライアントと UI の間）をモックだけで済ませていないか。遅いテストを追加していないか | should | repo／実行 | [Kent C. Dodds: Write tests](https://kentcdodds.com/blog/write-tests); [Betterspecs](https://www.betterspecs.org/) |
| TE14 | テスト名が振る舞いと期待結果を表しているか。失敗時に原因が分かる matcher を使っているか | nit | diff | [Betterspecs](https://www.betterspecs.org/); [SWE Book ch.12](https://abseil.io/resources/swe-book/html/ch12.html) |
