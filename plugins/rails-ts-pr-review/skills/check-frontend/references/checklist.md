# check-frontend チェックリスト

このファイルは scripts/extract_checklists.py で docs/research/report.md から生成。直接編集しない。

凡例は次のとおり。**既定**は重要度の初期値で、must はマージ前に必須、should は強く推奨（理由があれば見送り可）、nit は任意を表す。検証段階で上げ下げできる。**判定**は、指摘に必要な情報の範囲を表す。diff は差分だけで判断できる、repo は呼び出し元・スキーマ・設定・lint 設定などリポジトリ文脈が必要、PR は PR 説明やチケットが必要、実行は実機・CI 結果・本番統計・外部レジストリが必要、という意味だ。判定が「実行」の項目は静的レビューでは確定できないので、カバレッジ報告で「人間による確認が必要」と明示する。出典が「慣行」の項目は、権威ある単一の一次情報が見つからなかったものだ。

| # | 観点 | 既定 | 判定 | 出典 |
|---|---|---|---|---|
| FE1 | 新しい `any`、`as any`、`as unknown as T` | must（境界・公開 API）／should | diff | [Google TS Style](https://google.github.io/styleguide/tsguide.html) |
| FE2 | `@ts-ignore`/`@ts-nocheck` の追加 | must | diff | 同上 |
| FE3 | 外部入力（`fetch().json()`、`JSON.parse`、`localStorage`、URL クエリ、`postMessage`）を `as T` で信用している。境界で zod などを使って parse しているか | must | diff | 同上（`as` は unsafe）; 境界で parse する設計は推論 |
| FE4 | await されない Promise、void を期待する場所への async 関数（`no-floating-promises`/`no-misused-promises` 相当） | must | diff | [typescript-eslint](https://typescript-eslint.io/rules/) |
| FE5 | tsconfig で `strict: false` を明示的に追加、`skipLibCheck` を追加、`baseUrl`/`node10`/`es5` を新規に指定 | must | diff | [TS 6.0](https://devblogs.microsoft.com/typescript/announcing-typescript-6-0/) |
| FE6 | TS 7 への移行で、typescript-eslint や Vue が依存する 6.0 API への手当て（`@typescript/typescript6` の併用）があるか | must | repo | [TS 7.0](https://devblogs.microsoft.com/typescript/?p=5246) |
| FE7 | `!` や `as` で型チェッカーを黙らせていないか。オブジェクトリテラルには `as Foo` ではなく `: Foo` または `satisfies` を使う。`catch (e)` の `e` を `unknown` として絞り込んでいるか | should | diff | [Google TS Style](https://google.github.io/styleguide/tsguide.html) |
| FE8 | 状態を boolean の組み合わせではなく判別可能ユニオンで表し、網羅性チェックをしているか | should | diff | [TS Handbook Narrowing](https://www.typescriptlang.org/docs/handbook/2/narrowing.html) |
| FE9 | Hooks のルール（条件分岐の中、早期 return の後で呼んでいないか） | must | diff | [Rules of React](https://react.dev/reference/rules) |
| FE10 | `exhaustive-deps` を `eslint-disable` で抜いていないか（stale closure）。非リアクティブな値は `useEffectEvent` で扱う | must | diff | [React 19.2](https://react.dev/blog/2025/10/01/react-19-2) |
| FE11 | ユーザー操作に起因する副作用（POST、購入イベント）を Effect に入れていないか | must | diff | [You Might Not Need an Effect](https://react.dev/learn/you-might-not-need-an-effect) |
| FE12 | Effect 内の fetch、購読、タイマー、listener に cleanup（AbortController、ignore フラグ）があるか。検索入力などで古いレスポンスが新しい結果を上書きしないか | must | diff | 同上 |
| FE13 | リストの `key` が安定した一意の ID か（index や `Math.random()` を使わない） | must | diff | [Rendering Lists](https://react.dev/learn/rendering-lists) |
| FE14 | state を直接 mutate していないか。レンダー中に ref を読み書きしたり setState したりしていないか | must | diff | [React Compiler 1.0](https://react.dev/blog/2025/10/07/react-compiler-1) |
| FE15 | `use(promise)` に渡す Promise をレンダーごとに生成していないか。Suspense と Error Boundary が対になっているか。楽観的更新にロールバック経路があるか | must | diff | [use](https://react.dev/reference/react/use) |
| FE16 | Client Component にシリアライズできない props を渡していないか。サーバー専用モジュールに `server-only` があるか | must | diff | [Server and Client Components](https://nextjs.org/docs/app/getting-started/server-and-client-components) |
| FE17 | Next.js 16：`params`/`searchParams`/`cookies()`/`headers()` を await しているか | must | diff | [Next.js 16](https://nextjs.org/blog/next-16) |
| FE18 | `"use cache"` を付けた関数が、cookie やユーザー固有データに依存していないか（ユーザー間でキャッシュが漏れる） | must | repo | 同上（一部推論） |
| FE19 | ミューテーション後のキャッシュ無効化（`updateTag`、`revalidateTag(tag, profile)`、`invalidateQueries`）が漏れていないか | must | repo | 同上 |
| FE20 | loading/error/empty/success の全状態に UI があるか。エラーを握り潰していないか | must | diff | [Google TS Style](https://google.github.io/styleguide/tsguide.html)（空 catch） |
| FE21 | 派生値を state にコピーして Effect で同期していないか。Effect の連鎖や、子から親へのデータの逆流がないか | should | diff | [You Might Not Need an Effect](https://react.dev/learn/you-might-not-need-an-effect) |
| FE22 | `"use client"` を上位に付けすぎていないか。新しい `middleware.ts` ではなく `proxy.ts` か。新しいルートに `loading`/`error` があるか | should | diff | [Next.js 16](https://nextjs.org/blog/next-16) |
| FE23 | React Compiler が有効な環境で「念のため」の memo を足していないか。逆に、既存 memo の一括削除に動作確認の根拠があるか | nit／should | repo | [React Compiler 1.0](https://react.dev/blog/2025/10/07/react-compiler-1) |
| FE24 | Stimulus：`connect()` で追加した listener、タイマー、Observer、サードパーティの初期化を `disconnect()` で解除しているか。`connect()` が再実行されても壊れないか | must | diff | [Stimulus Lifecycle](https://stimulus.hotwired.dev/reference/lifecycle-callbacks) |
| FE25 | `DOMContentLoaded`/`window.onload`/jQuery の `ready` に新しいロジックを書いていないか（Turbo 環境では初回ロードでしか発火しない） | must | diff | [Turbo Building](https://turbo.hotwired.dev/handbook/building) |
| FE26 | ERB 側の `data-controller`/`data-*-target`/`data-action` の名前が TS 側と一致しているか。Turbo Frame の `id` がレスポンスと一致しているか | must | repo | 推論（ERB と TS の両方を参照する必要がある） |
| FE27 | Turbo のフォーム送信で、失敗時は 422 で render、成功時は redirect しているか | must | diff | [Turbo Drive](https://turbo.hotwired.dev/handbook/drive#redirecting-after-a-form-submission) |
| FE28 | importmap 構成に `.ts` を置いていないか。esbuild/Vite 構成で CI が `tsc --noEmit` を実行しているか | must | repo | [importmap-rails](https://github.com/rails/importmap-rails); [esbuild](https://esbuild.github.io/content-types/#typescript-caveats) |
| FE29 | Turbo のキャッシュ（`turbo:before-cache` でのリセット、`data-turbo-temporary`）、morph 時の `data-turbo-permanent`、`<head>` での script 読み込みと `data-turbo-track` | should | 実行 | [Turbo Building](https://turbo.hotwired.dev/handbook/building); [Page Refreshes](https://turbo.hotwired.dev/handbook/page_refreshes) |
| FE30 | クリック可能な `<div>`、ラベルの欠落（placeholder で代用）、`alt` やアクセシブルネームの欠落、ARIA の誤用、`outline: none` | must | diff | [WCAG 2.2 quickref](https://www.w3.org/WAI/WCAG22/quickref/); [Using ARIA](https://www.w3.org/TR/using-aria/) |
| FE31 | モーダル：開いたときのフォーカス移動、フォーカストラップ、Esc で閉じる、閉じたあとのフォーカス復帰 | must | diff | [ARIA APG](https://www.w3.org/WAI/ARIA/apg/) |
| FE32 | WCAG 2.2：ドラッグ操作に代替手段があるか（2.5.7）、ログインでペーストを妨げていないか（3.3.8）、ターゲットサイズ 24px（2.5.8）、固定ヘッダーなどがフォーカスを隠さないか（2.4.11） | must（2.5.7、3.3.8）／should | diff／実行 | [What's New in WCAG 2.2](https://www.w3.org/WAI/standards-guidelines/wcag/new-in-22/) |
| FE33 | コントラスト（4.5:1）、色だけで状態を伝えていないか | must | 実行 | [WCAG 2.2 quickref](https://www.w3.org/WAI/WCAG22/quickref/) |
| FE34 | **性能（必ず探す）**：イベントハンドラ内の重い同期処理、レイアウトスラッシング、巨大な DOM や仮想化されていない長いリスト（INP は 200ms 以下が Good） | should | diff | [Optimize INP](https://web.dev/articles/optimize-inp) |
| FE35 | **性能（必ず探す）**：重い依存の新規追加や全量 import、動的 import の余地、直列のデータ取得（ウォーターフォール）、画像の寸法・優先度・遅延読み込み | should | diff+repo | 同上; [Next.js 16](https://nextjs.org/blog/next-16) |
| FE36 | 理由のない lint 抑制コメント、既存のデザインシステムやユーティリティの再発明、`!important` やハードコードした色 | should | diff | [typescript-eslint](https://typescript-eslint.io/users/configs/); 一部推論 |
