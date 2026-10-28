# TypeScript フロントエンド (React / Next.js / Vue / Rails+Hotwire) PRレビュー観点

凡例: 各チェック項目の末尾タグは `[重大度 / 判定に必要な範囲]`。
- 重大度: **must**(バグ・データ不整合・a11y阻害・本番障害に直結)/ **should**(保守性・性能・将来のバグ要因)/ **nit**(スタイル・好み)
- 判定範囲: **diff**=差分だけで判定可 / **repo**=tsconfig・lint設定・周辺コード・バックエンドスキーマ等の確認が必要 / **run**=実機・計測(ブラウザ, Lighthouse, スクリーンリーダー)が必要
- 調査日: 2026-10-28。出典に「(知識ベース, 本調査で未fetch)」とあるものは、URLは一次資料だが本調査中に本文を再取得していないもの。レポート作成時は確度を一段下げて扱うこと。

---

## Q1. 型安全性のレビュー観点と TypeScript 5.x〜6.0〜7.0 の最新動向

### Takeaway
2026年10月時点で TypeScript は **6.0(2026-03-23, JS実装の最終版・ブリッジ)→ 7.0(2026-07-08 GA, Go製ネイティブ移植, 8〜12倍高速)** に移行済みで、`strict: true` がデフォルト化し `baseUrl`/`moduleResolution: node10`/`target: es5` 等が 7.0 で削除された。レビューでは「型の穴(any / as / ! / ts-ignore)を差分で塞ぐ」ことに加え、「外部データは境界で runtime 検証」「tsconfig 変更の妥当性」「7.0 非対応ツール(typescript-eslint・Vue 等は 6.0 API 依存)」の確認が新たに重要。

### Cited Findings

**TypeScript 6.0 / 7.0 の事実関係(古い助言の検出に使う)**
- TS 6.0 は 2026-03-23 リリース。現行 JS コードベース最後のリリースで、Go 製 7.0 へのブリッジ — [Announcing TypeScript 6.0](https://devblogs.microsoft.com/typescript/announcing-typescript-6-0/)
- 6.0 の新デフォルト: `strict: true`、`module: esnext`、`target`=最新ES(es2025)、`noUncheckedSideEffectImports: true`、`rootDir`=tsconfig のあるディレクトリ、`types: []`(グローバル `@types` は明示列挙が必要) — [TS 6.0](https://devblogs.microsoft.com/typescript/announcing-typescript-6-0/)
- 6.0 で非推奨(7.0 で削除): `target: es5`、`downlevelIteration`、`moduleResolution: node/node10`(→ `bundler` か `nodenext`)、`module: amd/umd/systemjs/none`、`baseUrl`(→ `paths` に移す)、`alwaysStrict: false`、`outFile`、`esModuleInterop: false`、import の `asserts`(→ `with`)、namespace 用 `module` キーワード — [TS 6.0](https://devblogs.microsoft.com/typescript/announcing-typescript-6-0/)
- 6.0 の挙動変更: generic call(generic JSX 含む)内の関数式チェックが厳格化し、明示的型引数が必要になる場合あり。`dom.iterable` は `dom` に統合 — [TS 6.0](https://devblogs.microsoft.com/typescript/announcing-typescript-6-0/)
- 6.0 の新機能: `#/` サブパス import(`bundler`/`nodenext`)、`es2025` target/lib、`esnext` に Temporal 型、`Map.getOrInsert`、`RegExp.escape`、7.0 差分診断用の `--stableTypeOrdering` — [TS 6.0](https://devblogs.microsoft.com/typescript/announcing-typescript-6-0/)
- TS 7.0 は 2026-07-08 GA。Go 製ネイティブ移植でフルビルド 8〜12倍高速(例: vscode 125.7s→10.6s)、`--checkers`(既定4)で並列型チェック。パッケージ名は `typescript`、コマンドは `tsc` のまま — [Announcing TypeScript 7.0](https://devblogs.microsoft.com/typescript/?p=5246)
- 7.0 互換性: 6.0 で `stableTypeOrdering` 有効かつ `ignoreDeprecations` なしでクリーンにコンパイルできれば 7.0 でも同じ結果。テンプレートリテラル型が Unicode コードポイントを保持(破壊的変更)、JSDoc ベースの JS 解析が変更 — [TS 7.0](https://devblogs.microsoft.com/typescript/?p=5246)
- 7.0 は **プログラマティック API なし**(7.1 で予定)。typescript-eslint 等は `@typescript/typescript6`(`tsc6`)併用で動かす。**Vue / MDX / Astro / Svelte / Angular テンプレートのワークフローは 6.0 API 依存のまま** — [TS 7.0](https://devblogs.microsoft.com/typescript/?p=5246)
- Next.js 16 の最低 TS バージョンは 5.1 — [Next.js 16](https://nextjs.org/blog/next-16)

**型の穴・アサーション(Google TS Style Guide)**
- `any` は避け、具体型 / `unknown` / インターフェースを使う。やむを得ない場合は lint 抑制+理由コメント — [Google TypeScript Style Guide](https://google.github.io/styleguide/tsguide.html)
- `as` と `!`(非nullアサーション)は unsafe。runtime チェック(`instanceof`、truthiness)を優先し、使うなら安全である理由をコメント。二重アサーションは `any` でなく `unknown` 経由 — [Google TS Style Guide](https://google.github.io/styleguide/tsguide.html)
- オブジェクトリテラルは `as Foo` でなく `: Foo` 注釈(余分・誤字フィールドを検出するため) — [Google TS Style Guide](https://google.github.io/styleguide/tsguide.html)
- `@ts-ignore` / `@ts-expect-error` / `@ts-nocheck` は本番コードで禁止 — [Google TS Style Guide](https://google.github.io/styleguide/tsguide.html)
- `{}` 型を避け `unknown`/`Record<string,T>`/`object` を使う。ラッパー型(`String`, `Number` 等)禁止 — [Google TS Style Guide](https://google.github.io/styleguide/tsguide.html)
- `const enum` 禁止、enum 値の truthiness 判定禁止(明示比較)。`switch` は `default` 必須・非空 case の fallthrough 禁止 — [Google TS Style Guide](https://google.github.io/styleguide/tsguide.html)
- 型専用 import/export は `import type` / `export type`。default export 禁止(named export)、`export let`(可変 export)禁止、namespace 禁止 — [Google TS Style Guide](https://google.github.io/styleguide/tsguide.html)
- 例外は `Error`(サブクラス)のみ throw。空 catch には理由コメント。`Number()`+NaN チェックで変換し単項 `+`/`parseInt` を一般パースに使わない — [Google TS Style Guide](https://google.github.io/styleguide/tsguide.html)
- 型注釈は自明な推論では省略、`new Set<string>()` のように推論が `unknown` になる箇所や複雑な式では明示。戻り値型はレビュアーが要求してよい — [Google TS Style Guide](https://google.github.io/styleguide/tsguide.html)

**typescript-eslint の構成**
- `recommended` / `recommended-type-checked` / `stylistic` は semver 安定。`strict` / `strict-type-checked` は非安定(マイナーでルール変更あり)で、「TypeScript に習熟した開発者が相当数いるチーム向け」 — [typescript-eslint Shared Configs](https://typescript-eslint.io/users/configs/)
- 型情報付き lint は flat config で `parserOptions: { projectService: true }` — [typescript-eslint Shared Configs](https://typescript-eslint.io/users/configs/)
- 主要な型情報ルール(各ルールページ): `no-floating-promises`、`no-misused-promises`、`switch-exhaustiveness-check`、`no-unsafe-assignment/-member-access/-call/-return/-argument`、`no-unnecessary-condition`、`no-non-null-assertion`、`no-explicit-any` — [typescript-eslint Rules](https://typescript-eslint.io/rules/)(知識ベース, 本調査ではどのプリセットに含まれるかまでは未確認)

**チェックリスト(Q1)**
- 新規 `any`(明示・暗黙)や `as any` / `as unknown as T` が入っていないか。入れるなら理由コメントと範囲の最小化 `[must(境界・公開API)/should / diff]` — Google TS Style Guide
- `!` 非nullアサーション、`as` ダウンキャストが「型チェッカを黙らせる」目的で使われていないか(→ 型ガード / 早期 return / `satisfies` へ) `[should / diff]` — Google TS Style Guide
- オブジェクトリテラルに `as Foo` でなく `: Foo` か `satisfies Foo` を使っているか `[should / diff]` — Google TS Style Guide;`satisfies` は TS 4.9 で導入([TS 4.9 release notes](https://www.typescriptlang.org/docs/handbook/release-notes/typescript-4-9.html), 知識ベース・未fetch)
- `@ts-ignore` / `@ts-nocheck` が追加されていないか。どうしても必要なら `@ts-expect-error`+理由(型修正時に検出される) `[must / diff]` — Google TS Style Guide
- `catch (e)` の `e` は `unknown` として扱い、`instanceof Error` 等で絞り込んでいるか(`useUnknownInCatchVariables` は strict に含まれる) `[should / diff]` — [tsconfig: useUnknownInCatchVariables](https://www.typescriptlang.org/tsconfig/#useUnknownInCatchVariables)(知識ベース・未fetch)
- 状態は「boolean フラグの組み合わせ」でなく判別可能ユニオン(`{status:'loading'} | {status:'error', error} | {status:'success', data}`)で表し、`switch` に `never` による網羅チェックまたは `switch-exhaustiveness-check` があるか `[should / diff]` — [TS Handbook: Narrowing (exhaustiveness checking)](https://www.typescriptlang.org/docs/handbook/2/narrowing.html)(知識ベース・未fetch)
- `fetch().json()`・`JSON.parse`・`localStorage`・URL query・`postMessage`・`data-*` 属性・WebSocket 等の外部入力を `as T` で信用していないか。境界で zod / valibot 等で parse しているか `[must / diff]`(推論。下記 Inferences 参照)
- 未 await の Promise(イベントハンドラ内の `async` 関数呼び出し、`onClick={async () => …}` が void を期待する箇所)— `no-floating-promises` / `no-misused-promises` 相当 `[must / diff]` — typescript-eslint rules
- 配列/Record の index アクセス結果を `undefined` 考慮しているか(`noUncheckedIndexedAccess` 有効なら型で強制) `[should / repo]` — [tsconfig: noUncheckedIndexedAccess](https://www.typescriptlang.org/tsconfig/#noUncheckedIndexedAccess)(知識ベース・未fetch)
- `exactOptionalPropertyTypes` 下で `prop?: T` に `undefined` を明示代入していないか(区別が必要な API パッチ等) `[nit/should / repo]` — [tsconfig: exactOptionalPropertyTypes](https://www.typescriptlang.org/tsconfig/#exactOptionalPropertyTypes)(知識ベース・未fetch)
- tsconfig の変更: `strict` の部分的無効化、`skipLibCheck` 追加、`baseUrl`/`node10`/`es5`/`downlevelIteration` の新規追加(=7.0 で削除済み・6.0 で非推奨)がないか。`"types": ["*"]` 復活は非推奨 `[must / diff]` — TS 6.0 / 7.0 announcements
- TS 7 への移行 PR では、`rootDir` 明示・`types` 明示・`@typescript/typescript6` による lint 併用が考慮されているか。Vue(vue-tsc)プロジェクトは 6.0 API 依存のため 7.0 単独化は時期尚早 `[must / repo]` — TS 7.0 announcement
- 型専用 import は `import type`(`verbatimModuleSyntax` 使用時は必須)、esbuild/Vite の isolated トランスパイルと整合しているか `[nit/should / repo]` — Google TS Style Guide; [tsconfig: verbatimModuleSyntax](https://www.typescriptlang.org/tsconfig/#verbatimModuleSyntax)(知識ベース・未fetch)
- `enum` 新規追加より文字列リテラルユニオン/`as const` オブジェクト(Node の type stripping・`erasableSyntaxOnly` と相性)— チーム規約次第 `[nit / repo]` — [TS 5.8: --erasableSyntaxOnly](https://www.typescriptlang.org/docs/handbook/release-notes/typescript-5-8.html)(知識ベース・未fetch)
- バックエンド API 型の手書き重複がないか。OpenAPI/GraphQL codegen の生成物を手編集していないか、スキーマ変更 PR で生成物が再生成されているか `[must / repo]`(推論)

### Inferences
- TS 6.0 以降は `strict` がデフォルトなので、tsconfig に `"strict": false` を**明示的に追加**する差分は強いシグナル(以前は「書いていない」だけで非 strict だった)。レビューでは must 扱いで理由を問うのが妥当。
- 「`baseUrl` を使ってパスエイリアス」「`moduleResolution: node`」「`target: es5`」を勧める記事・テンプレートは 2026 年時点で**古い助言**。Vite/esbuild/Rails(jsbundling)構成では `moduleResolution: bundler` が自然。
- TS の型は runtime に存在しないため、`as T` で受けた API レスポンスはバックエンド変更で静かに壊れる。境界(fetch ラッパー、Server Action の入力、フォーム、`JSON.parse`)で zod/valibot 等により parse し、内部では信頼された型を使う「parse, don't validate」型の設計を推す。Server Actions は公開 HTTP エンドポイントになるので入力検証は must(セキュリティ詳細は他担当)。
- `strict-type-checked` は非安定であることから、採用は「ルール追加で CI が突然赤くなる」ことを許容できるチーム向け。多くのチームでは `recommended-type-checked` + 個別に `switch-exhaustiveness-check`・`no-floating-promises` 等を足す構成が現実的。

### Gaps
- typescript-eslint の各プリセットに含まれる具体的ルール一覧は、configs ページに列挙がなく本調査で確定できなかった(ルールページ個別確認が必要)。
- zod v4 / valibot v1 の最新状況(2026 年)は本調査で一次資料を取得していない。
- TS 7.1(API 復活)のリリース有無は 2026-10-28 時点で未確認(7.0 記事では「3〜4か月ごとのリリース」「7.1 で API」とのみ記載)。
- tsconfig の `noUncheckedIndexedAccess` / `exactOptionalPropertyTypes` は strict に含まれない別フラグという点は知識ベース(公式 tsconfig リファレンス未fetch)。

---

## Q2. React の正しさ(hooks・Effect・keys・stale closure・競合)、React 19 / Compiler、Next.js App Router の境界

### Takeaway
React 19.x + React Compiler 1.0(2025-10-07 安定版)+ Next.js 16(2025-10-21)が現行の前提。レビューの主眼は「Effect を同期以外に使っていないか(You Might Not Need an Effect)」「fetch の競合・クリーンアップ」「Server/Client 境界と serializable props」「Next.js 16 の async API・キャッシュ API 変更」。Compiler 導入後は「手動 memo を新たに足す」差分を疑う一方、既存 memo の一括削除も慎重に。

### Cited Findings

**You Might Not Need an Effect(react.dev)**
- 派生値を state+Effect で同期せず、レンダー中に計算する — [You Might Not Need an Effect](https://react.dev/learn/you-might-not-need-an-effect)
- 重い計算はまず計測し、遅ければ `useMemo`。React Compiler があれば多くのケースで手動 `useMemo` は不要 — 同上
- props 変化で全 state をリセットするなら Effect でなく `key` を付ける。一部の state 調整はレンダー中に prev 値比較、または ID を保持して派生 — 同上
- ユーザー操作起因のロジック(通知、POST 送信)はイベントハンドラへ。「表示されたから」実行するものだけが Effect — 同上
- Effect の連鎖(setState→Effect→setState)は余計な再レンダーと脆さの原因。外部システム同期(依存ドロップダウンのネットワーク取得等)以外は避ける — 同上
- アプリ初期化を `useEffect(..., [])` で行うと開発時に2回走る。モジュールレベルのガードを使う — 同上
- 親への通知(`onChange`)を Effect で呼ばず、同じイベントハンドラで呼ぶ(1回のレンダーにバッチ)。子が fetch して親に渡す逆流は避け、親が取得して props で渡す — 同上
- 外部ストア購読は手動 listener+setState でなく `useSyncExternalStore` — 同上
- Effect 内 fetch はクリーンアップ(`ignore` フラグ)で競合を防ぐ。より良いのはカスタムフック化またはフレームワーク組込みのデータ取得(キャッシュ、SSR、ウォーターフォール対策) — 同上

**React Compiler 1.0**
- 2025-10-07 に 1.0 安定版。ビルド時に components/hooks を自動メモ化。React 17+ 対応 — [React Compiler v1.0](https://react.dev/blog/2025/10/07/react-compiler-1)
- 新規コードは Compiler に任せ、`useMemo`/`useCallback` は「effect の依存に使うメモ化値」など精密な制御が要る場合のみ。既存のメモ化は残すか、慎重にテストしてから削除(削除でコンパイル結果が変わり得る) — 同上
- Compiler 由来の lint ルールは `eslint-plugin-react-hooks` の `recommended` / `recommended-latest` に統合(`set-state-in-render`, `set-state-in-effect`, `refs` 等)。`eslint-plugin-react-compiler` は削除して移行 — 同上
- メモ化の変化で `useEffect` の発火タイミングが変わる可能性があり、テストが薄いならバージョンを exact pin — 同上

**Next.js 16(2025-10-21)**
- Cache Components: `"use cache"` ディレクティブで明示的にキャッシュ。キャッシュは完全 opt-in で、動的コードは既定でリクエスト時実行。`cacheComponents: true` で有効化。`experimental.ppr`・`experimental.dynamicIO` は削除/改名 — [Next.js 16](https://nextjs.org/blog/next-16)
- `middleware.ts` → `proxy.ts`(Node.js ランタイム、関数名 `proxy`)。`middleware.ts` は Edge 用に残るが非推奨 — 同上
- 同期の `params` / `searchParams` / `cookies()` / `headers()` / `draftMode()` アクセスは削除。`await` 必須 — 同上
- `revalidateTag(tag)` 単一引数は非推奨。`revalidateTag(tag, 'max')` 等 cacheLife プロファイル必須。read-your-writes が要る Server Action では `updateTag()`、非キャッシュデータ更新は `refresh()` — 同上
- React Compiler サポートは stable(`reactCompiler: true`)だがデフォルト無効(Babel 依存でビルドが遅くなる) — 同上
- React 19.2: `<ViewTransition>`、`useEffectEvent`、`<Activity>` — 同上 / [React 19.2](https://react.dev/blog/2025/10/01/react-19-2)
- 並列ルートの全スロットに `default.js` 必須。`next lint` 削除(ESLint/Biome を直接実行)。`images.domains` 非推奨→`remotePatterns`。`next/legacy/image` 非推奨 — [Next.js 16](https://nextjs.org/blog/next-16)
- 要件: Node.js 20.9+、TS 5.1+、Chrome/Edge/Firefox 111+、Safari 16.4+ — 同上

**Server / Client 境界(Next.js docs, 2026-10-05 更新)**
- `"use client"` を付けたファイルの import と直接レンダーするコンポーネントは全てクライアントバンドルに入る。インタラクティブな末端コンポーネントにだけ付けてバンドルを削る — [Server and Client Components](https://nextjs.org/docs/app/getting-started/server-and-client-components)
- Server→Client の props は React で serializable でなければならない(関数・クラスインスタンス・Date 以外の複雑オブジェクト等に注意) — 同上
- Server Component を `children`/props として Client Component に渡す(interleaving)。Context は Server Component で使えないので Client の Provider で `children` を包み、Provider はできるだけ深く置く — 同上
- サーバ専用コード(API キー参照)は `import 'server-only'` で誤 import をビルドエラー化。`NEXT_PUBLIC_` 接頭辞のみクライアントに露出 — 同上
- `use` API でサーバからクライアントへデータをストリーム可能 — 同上

**チェックリスト(Q2)**
- Hooks のルール: 条件分岐・ループ・早期 return 後で hook を呼んでいないか、カスタムフックは `use` 接頭辞か `[must / diff]` — [Rules of React](https://react.dev/reference/rules)(知識ベース・未fetch)
- `useEffect` の依存配列から値を抜いて lint を `eslint-disable` していないか(stale closure の典型)。非リアクティブに読みたい値は `useEffectEvent`(19.2+)で切り出す `[must / diff]` — React 19.2, Next.js 16
- 派生値を state にコピーして Effect で同期していないか / props→state のコピー `[should / diff]` — You Might Not Need an Effect
- ユーザー操作起因の副作用(POST、トースト、analytics の「購入」イベント)が Effect に入っていないか `[must(重複送信リスク) / diff]` — 同上
- Effect 内 fetch / subscribe / timer / listener に cleanup があるか(AbortController または ignore フラグ)。StrictMode の二重実行で壊れないか `[must / diff]` — 同上
- Effect チェーン・親通知 Effect・子→親データ逆流がないか `[should / diff]` — 同上
- 外部ストア/ブラウザ API 購読は `useSyncExternalStore` か `[should / diff]` — 同上
- リスト `key` が安定・一意な ID か(index・`Math.random()` 禁止)。並べ替え/削除で state が別要素に移らないか `[must / diff]` — [Rendering Lists](https://react.dev/learn/rendering-lists)(知識ベース・未fetch)
- state リセットに `key` を活用しているか(フォームの切り替え等) `[should / diff]` — You Might Not Need an Effect
- state の直接 mutate(`arr.push` 後 setState)、レンダー中の ref 読み書き・setState がないか(Compiler lint `refs` / `set-state-in-render`) `[must / diff]` — React Compiler 1.0
- React Compiler 有効環境で、新たに `useMemo`/`useCallback`/`React.memo` を「念のため」足していないか(effect 依存の安定化など明確な理由があれば可) `[nit/should / repo]` — React Compiler 1.0
- 逆に既存の memo 一括削除 PR は effect 発火変化のリスクがあり、テスト/動作確認の根拠があるか `[should / repo]` — 同上
- React 19 Actions: フォーム送信は `<form action>`/`useActionState`/`useFormStatus` を使い、pending・エラー・二重送信防止を自前 state で再実装していないか。楽観的更新は `useOptimistic` でロールバック経路があるか `[should / diff]` — [React 19](https://react.dev/blog/2024/12/05/react-19)(知識ベース・未fetch)
- `use(promise)` に渡す Promise をレンダーごとに新規生成していないか(Server Component から渡す / キャッシュする)。Suspense 境界・Error Boundary が対で存在するか `[must / diff]` — [use](https://react.dev/reference/react/use)(知識ベース・未fetch)
- React 19 では `forwardRef` 不要(ref は props)。新規コードで `forwardRef`・`defaultProps`(関数コンポーネント)・`propTypes` を使っていないか `[nit / diff]` — React 19(知識ベース・未fetch)
- `"use client"` が不必要に上位(layout/page 全体)に付いてバンドル肥大していないか `[should / diff]` — Server and Client Components
- Client Component に関数・クラスインスタンス・巨大オブジェクトを props で渡していないか(serializable 制約、ペイロード肥大) `[must / diff]` — 同上
- サーバ専用モジュールに `server-only` があるか。秘密値が `NEXT_PUBLIC_` で露出していないか `[must / diff]` — 同上
- Next.js 16: `params`/`searchParams`/`cookies()`/`headers()` を await しているか、型が `Promise<...>` か `[must / diff]` — Next.js 16
- `revalidateTag` に第2引数があるか、Server Action で書き込み直後の再表示が必要なら `updateTag` を使っているか `[should / diff]` — 同上
- `"use cache"` を付けた関数が cookies/headers/ユーザー固有データに依存していないか(ユーザー間でのキャッシュ漏れ)、タグ・cacheLife 設計が妥当か `[must / repo]` — 同上(推論を含む)
- 新規 `middleware.ts` ではなく `proxy.ts` か。proxy に重いビジネスロジックを入れていないか `[should / diff]` — 同上
- Server Action / Route Handler の入力を zod 等で検証しているか(公開エンドポイント) `[must / diff]`(推論; セキュリティ詳細は他担当)
- `app/` 内の `loading.tsx` / `error.tsx`(Client Component 必須)/ `not-found.tsx` が新ルートに用意されているか `[should / repo]` — [Next.js Error Handling](https://nextjs.org/docs/app/getting-started/error-handling)(知識ベース・未fetch)
- ハイドレーション不一致要因(レンダー中の `Date.now()`、`Math.random()`、`window` 分岐、ロケール依存フォーマット)がないか `[should / diff]`(知識ベース)

### Inferences
- 「`useMemo`/`useCallback` を常に付けよ」「`React.memo` で全部包め」は Compiler 1.0 以降は**古い助言**。ただし「既存 memo を消せ」も公式は推奨していないので、レビューでは新規追加の正当性だけを問うのがバランスが良い。
- Next.js 15 までの「App Router は既定で積極キャッシュ」という前提の記事・コードは、16 の Cache Components(opt-in)では誤り。`fetch` の `cache` オプションや `export const dynamic` に依存する差分は、プロジェクトが `cacheComponents` を有効にしているかで評価が変わる(repo 判定)。
- データ取得は「Effect で fetch」より、Server Components / フレームワークのローダー / TanStack Query・SWR 等のライブラリを優先させるのが react.dev の方針と整合する。Effect 直書き fetch を見たら少なくとも cleanup と loading/error 状態の有無を確認する。

### Gaps
- `eslint-plugin-react-hooks` の Compiler 系ルールの完全な一覧(purity, immutability, preserve-manual-memoization 等)は本調査で未確認。
- Next.js 16.x の最新マイナー(2026-10 時点)や Next.js 17 の有無は未確認。第三者記事で 16.1/16.2 と proxy/Cache Components 関連のセキュリティアドバイザリへの言及あり([LogRocket](https://blog.logrocket.com/next-js-16-whats-new) 等, 二次情報)。
- React 19.x の最新マイナー(19.2 以降)の新機能は未確認。
- Vue 3.5+/Nuxt 固有の観点(`defineProps` 型、`ref` の `.value` 忘れ、`reactive` の分割代入でのリアクティビティ喪失等)は本調査でソース未取得。

---

## Q3. Rails フロントエンド(Hotwire: Stimulus / Turbo、Vite/esbuild/importmap)固有の観点

### Takeaway
Hotwire では「DOM が Turbo により差し替え・キャッシュ復元・morph される」ことが前提。レビューは (1) Stimulus の `connect`/`disconnect` で対称的にセットアップ/クリーンアップしているか、(2) `DOMContentLoaded` 依存や非冪等な DOM 変換がないか、(3) Turbo キャッシュ前の UI リセット・`data-turbo-permanent`/`data-turbo-temporary`、(4) script の配置と `data-turbo-track` が中心。

### Cited Findings
- `connect()` は要素が文書内にあり `data-controller` に識別子があるとき、`disconnect()` は条件を外れたとき呼ばれる。`[name]TargetConnected/Disconnected` は `connect`/`disconnect` の前に発火 — [Stimulus Lifecycle Callbacks](https://stimulus.hotwired.dev/reference/lifecycle-callbacks)
- コールバックは MutationObserver により DOM 変更後のマイクロタスクで非同期に実行。`connect` と `disconnect` は必ず交互 — 同上
- 要素削除、祖先の `innerHTML` 置換、`data-controller` 変更、Turbo のページ遷移による新 `<body>` で disconnect される。再アタッチ時は**同じインスタンスが再利用**され `connect()` が何度も呼ばれ得る — 同上
- `DOMContentLoaded` / `window.onload` / jQuery `ready` は初回ロードのみ。`turbo:load` を使うか、Drive/Frames/Streams すべてに一様に対応できる Stimulus を推奨 — [Turbo Handbook: Building](https://turbo.hotwired.dev/handbook/building)
- `turbo:before-cache` でフォームのリセット、展開 UI の折りたたみ、サードパーティウィジェットの破棄を行う。flash 等は `data-turbo-temporary` でキャッシュ復元時に再表示しない — 同上
- キャッシュ済みページは DOM 変更を保持したまま `turbo:load` が再発火するため、DOM 変換は冪等に(結果の存在チェック) — 同上
- `data-turbo-permanent` 要素は `id` 必須で、ナビゲーション間でデータ・イベントリスナごと保持 — 同上
- アプリのバンドルは `<head>` で読み込む(body 内 script はレンダーごとに評価される)。フィンガープリント付きバンドルに `data-turbo-track="reload"` — 同上
- Page refresh の morph: `<meta name="turbo-refresh-method" content="morph">`、スクロール保持は `turbo-refresh-scroll=preserve`。morph させたくない要素(開いているポップオーバー等)は `data-turbo-permanent`。`<turbo-frame refresh="morph">`。`broadcasts_refreshes` + `turbo_stream_from` で refresh をブロードキャスト — [Turbo Handbook: Page Refreshes](https://turbo.hotwired.dev/handbook/page_refreshes)

**チェックリスト(Q3)**
- Stimulus: `connect()` で追加した `addEventListener`/`setInterval`/`ResizeObserver`/サードパーティ初期化を `disconnect()` で解除しているか(同インスタンスで複数回 connect される) `[must / diff]` — Stimulus Lifecycle
- `connect()` 内処理が再実行に耐えるか(二重初期化・二重 DOM 挿入) `[must / diff]` — Stimulus Lifecycle; Turbo Building
- イベントは可能な限り `data-action` 宣言で結線(自動で着脱される)し、`document`/`window` への手動 listener は `@window`/`@document` 修飾子または disconnect での解除 `[should / diff]` — [Stimulus Actions](https://stimulus.hotwired.dev/reference/actions)(知識ベース・未fetch)
- `DOMContentLoaded` / `window.onload` / jQuery `ready` に新規ロジックを書いていないか(→ Stimulus コントローラ) `[must / diff]` — Turbo Building
- ターゲット・値の参照に `this.xxxTarget` / `static values`(型付き)を使い、`querySelector` でコントローラ外の DOM を掴んでいないか。存在が任意のターゲットは `hasXxxTarget` で確認しているか(なければ例外) `[should / diff]` — [Stimulus Targets](https://stimulus.hotwired.dev/reference/targets)(知識ベース・未fetch)
- TypeScript で書く Stimulus コントローラは `declare readonly xxxTarget: HTMLInputElement` 等で target/value の型を宣言し、`as` キャストを散在させていないか `[nit/should / diff]`(推論)
- コントローラ識別子とファイル名の対応(`hello_controller.ts` → `data-controller="hello"`)、ERB 側の `data-*-target`/`data-action` 名が JS と一致しているか(タイポは静かに無効) `[must / repo]`(推論: ERB と TS の両方を見る必要)
- Turbo キャッシュ: 開いたモーダル・ドロップダウン・入力途中のフォームが Back で復元されてしまわないか(`turbo:before-cache` かコントローラの `disconnect` でリセット) `[should / run]` — Turbo Building
- flash/トーストに `data-turbo-temporary` が付いているか `[nit/should / diff]` — 同上
- morph 有効ページでクライアント側状態(開閉状態・入力中の値・サードパーティが生成した DOM)が refresh で消える/壊れる箇所に `data-turbo-permanent` が付いているか `[should / run]` — Turbo Page Refreshes
- 新規 script を `<body>` に置いていないか、バンドルに `data-turbo-track="reload"` があるか `[should / diff]` — Turbo Building
- フォーム: Turbo Drive のフォーム送信で、バリデーション失敗時にサーバが 4xx(Rails では `status: :unprocessable_entity` / Rack 3.1 以降の `:unprocessable_content`)で render し、成功時は redirect しているか(200 で render すると Turbo は描画しない) `[must / diff(Rails 側コード)]` — [Turbo Handbook: Drive (Redirecting After a Form Submission)](https://turbo.hotwired.dev/handbook/drive#redirecting-after-a-form-submission)(知識ベース・未fetch)
- Turbo Frame の `id` がレスポンス側と一致しているか(不一致は "Content missing")、フレーム外へ遷移すべきリンクに `data-turbo-frame="_top"` があるか `[must / repo]` — [Turbo Handbook: Frames](https://turbo.hotwired.dev/handbook/frames)(知識ベース・未fetch)
- Turbo Stream の target ID が DOM に存在するか、`dom_id` ヘルパで一貫生成しているか `[should / repo]`(知識ベース)
- importmap-rails 構成に `.ts` を置いていないか(importmap はトランスパイルしない。TS を使うなら jsbundling-rails(esbuild/bun)または vite_ruby)。esbuild/Vite は型チェックをしないため CI で `tsc --noEmit` が別途走っているか `[must / repo]` — [importmap-rails README](https://github.com/rails/importmap-rails)(知識ベース・未fetch)/ [esbuild TypeScript caveats](https://esbuild.github.io/content-types/#typescript-caveats)(知識ベース・未fetch)
- esbuild/Vite の isolated トランスパイル前提で `isolatedModules: true`(または `verbatimModuleSyntax`)が有効か、型の re-export が `export type` か `[should / repo]` — 同上(知識ベース)

### Inferences
- Stimulus は「同一インスタンスが何度も connect/disconnect される」ため、React の Effect cleanup と同じ「対称性」レビューが最重要。React の StrictMode 二重実行チェックに相当する観点。
- Turbo 8 の morph はクライアント状態を保持しない可能性があるため(handbook はこの点に明記なし)、morph 導入 PR は run 判定(実機確認)を求めるべき。

### Gaps
- Turbo の morph 時の Stimulus コントローラ挙動(再 connect されるか、属性変更が values に反映されるか)、`turbo:before-morph-element` 等のイベントについて、本調査で一次資料を取得できず。
- Turbo のフォーム送信ステータスコード要件は本調査で再fetchしておらず知識ベース。
- Hotwire 公式に「レビュー観点」の形でまとまった資料は見つからなかった。

---

## Q4. 状態管理・データ取得・エラー/ローディング状態

### Takeaway
「最小の state + 派生はレンダー中に計算」「サーバ状態はキャッシュ層(Server Components / TanStack Query / SWR / フレームワーク)に任せ、グローバルストアに複製しない」「loading / error / empty / success を型で網羅」が軸。

### Cited Findings
- 冗長な state(他の state/props から計算できる値)を持たず、レンダー中に計算する — [You Might Not Need an Effect](https://react.dev/learn/you-might-not-need-an-effect)
- Effect 内データ取得は競合条件に注意し cleanup を書く。より良いのはカスタムフックかフレームワーク組込みデータ取得(キャッシュ・SSR・ネットワークウォーターフォールの扱い) — 同上
- Next.js 16 ではキャッシュは opt-in、書き込み後の即時反映は `updateTag`、非キャッシュ部分の更新は `refresh()` — [Next.js 16](https://nextjs.org/blog/next-16)
- Server Component でデータ取得し、Client へは props か `use` でストリーム — [Server and Client Components](https://nextjs.org/docs/app/getting-started/server-and-client-components)

**チェックリスト(Q4)**
- 同じデータが複数の state/ストアに重複保持されていないか(Single source of truth)。サーバデータを Redux/Zustand 等に手でコピーしていないか `[should / repo]` — You Might Not Need an Effect(推論を含む)
- グローバルストア/Context に入れる必要のない局所状態をグローバル化していないか。Context 値の頻繁な更新で広範囲が再レンダーされないか `[should / repo]`(推論)
- URL に載せるべき状態(フィルタ・ページ・タブ)を URL search params で表現しているか(共有・戻る対応) `[should / diff]`(推論)
- loading / error / empty / success の全状態の UI があるか。error 時に再試行手段があるか。判別可能ユニオンで「loading かつ error」等の不正状態を型で排除しているか `[must(error 未処理) / diff]`(推論; TS narrowing)
- 並列にできる取得が直列ウォーターフォールになっていないか(`await` の連鎖、子コンポーネントでの逐次 fetch) `[should / diff]` — You Might Not Need an Effect(ウォーターフォール言及)
- 検索入力等の連続リクエストで古いレスポンスが新しい結果を上書きしないか(AbortController / ignore / ライブラリのキー管理) `[must / diff]` — 同上
- ミューテーション後のキャッシュ無効化(`updateTag`/`revalidateTag`/`router.refresh`/`queryClient.invalidateQueries` 等)が漏れていないか `[must / repo]` — Next.js 16(+推論)
- 楽観的更新に失敗時ロールバックとエラー通知があるか `[must / diff]` — React 19 `useOptimistic`(知識ベース・未fetch)
- Suspense / Error Boundary の粒度: ページ全体が1つの fallback で固まらないか、エラーが局所に閉じるか `[should / repo]`(推論)
- Promise の reject が握り潰されていないか(空 catch、`console.error` のみでユーザーに伝わらない) `[must / diff]` — Google TS Style Guide(空 catch 規定)

### Inferences
- データ取得ライブラリ(TanStack Query / SWR)の具体的な観点(queryKey に全依存を含める、staleTime 設定、enabled 条件)は一般的に重要だが、本調査では一次資料を取得していない。

### Gaps
- TanStack Query v5 / SWR / Zustand / Redux Toolkit / Pinia の公式ベストプラクティスは本調査範囲外として未取得。

---

## Q5. アクセシビリティ(WCAG 2.2)

### Takeaway
WCAG 2.2 で追加された AA 基準のうち、フロントエンド PR で頻出するのは **2.4.11 Focus Not Obscured(固定ヘッダ/トースト/クッキーバナーがフォーカスを隠す)**、**2.5.7 Dragging Movements(ドラッグ代替)**、**2.5.8 Target Size(24×24 CSS px)**、**3.3.8 Accessible Authentication**。4.1.1 Parsing は削除。従来の基本(セマンティクス・ラベル・キーボード・フォーカス管理・コントラスト・ARIA 誤用)も引き続き最重要。

### Cited Findings
- WCAG 2.2 追加基準: 2.4.11 Focus Not Obscured (Minimum, AA)、2.4.12 (Enhanced, AAA)、2.4.13 Focus Appearance (AAA, 最小サイズと 3:1 コントラスト)、2.5.7 Dragging Movements (AA)、2.5.8 Target Size (Minimum, AA: 24×24 CSS px か間隔等の例外)、3.2.6 Consistent Help (A)、3.3.7 Redundant Entry (A)、3.3.8 Accessible Authentication (Minimum, AA)、3.3.9 (Enhanced, AAA) — [What's New in WCAG 2.2](https://www.w3.org/WAI/standards-guidelines/wcag/new-in-22/)
- 4.1.1 Parsing は obsolete として WCAG 2.2 から削除。その他 2.0/2.1 の基準は実質変更なし — 同上

**チェックリスト(Q5)**
- クリック可能要素は `<button>`/`<a href>` を使い、`<div onClick>` にしていないか(使うなら role・tabIndex・Enter/Space 対応が必要) `[must / diff]` — [WCAG 2.1.1 Keyboard / 4.1.2 Name, Role, Value](https://www.w3.org/WAI/WCAG22/quickref/)(知識ベース・未fetch)
- `<a>` はナビゲーション、`<button>` はアクション。`href="#"` + onClick のボタン代用がないか `[should / diff]`(知識ベース)
- フォーム入力に可視ラベル(`<label htmlFor>`)があり、placeholder だけでラベル代用していないか。エラーメッセージが `aria-describedby` 等で関連付けられ、`aria-invalid` が設定されるか `[must / diff]` — WCAG 1.3.1 / 3.3.1 / 3.3.2(知識ベース・未fetch)
- 画像に適切な `alt`(装飾は `alt=""`)、アイコンのみボタンにアクセシブルネーム(`aria-label` 等) `[must / diff]` — WCAG 1.1.1 / 4.1.2(知識ベース)
- ARIA の誤用: ネイティブ要素で済むのに role を付与、`aria-hidden="true"` をフォーカス可能要素/祖先に付与、存在しない ID への `aria-labelledby`、`role="button"` に keydown なし `[must / diff]` — [Using ARIA (First rule of ARIA)](https://www.w3.org/TR/using-aria/)(知識ベース・未fetch)
- 複合ウィジェット(タブ、メニュー、コンボボックス、ダイアログ)は WAI-ARIA APG のキーボード操作パターンに従うか。可能なら `<dialog>`・Headless UI/Radix/React Aria 等の実績あるプリミティブを使うか `[should / diff]` — [ARIA Authoring Practices Guide](https://www.w3.org/WAI/ARIA/apg/)(知識ベース・未fetch)
- モーダル: 開いたらフォーカス移動、フォーカストラップ、Esc で閉じる、閉じたらトリガーへフォーカス復帰 `[must / diff]` — APG Dialog pattern(知識ベース)
- SPA/Turbo のクライアント遷移・非同期更新でフォーカスとスクリーンリーダー通知(見出しへのフォーカス移動、`aria-live` 領域)が考慮されているか `[should / run]`(知識ベース)
- `outline: none` 等でフォーカスインジケータを消していないか(`:focus-visible` で代替スタイル) `[must / diff(CSS)]` — WCAG 2.4.7 / 2.4.13(2.4.13 は上記出典)
- 固定ヘッダ・スティッキーフッタ・トースト・チャットウィジェットがフォーカス要素を完全に隠さないか(2.4.11, AA; `scroll-padding` 等で対処) `[must / run]` — What's New in WCAG 2.2
- ドラッグ&ドロップ(並べ替え、スライダー、カンバン)に単一ポインタ代替(ボタン、メニュー)があるか(2.5.7, AA) `[must / diff]` — 同上
- ポインタターゲットが 24×24 CSS px 以上、または十分な間隔があるか(2.5.8, AA)。小さなアイコンボタン・密集リンク `[should / diff(CSS) or run]` — 同上
- ログイン/2FA でパスワードマネージャ・ペーストを妨げていないか(`autocomplete` 属性、`onPaste` で preventDefault しない)— 3.3.8 `[must / diff]` — 同上
- 複数ステップフォームで既入力情報を再入力させていないか(3.3.7) `[should / repo]` — 同上
- テキストコントラスト 4.5:1(大文字 3:1)、UI 部品・フォーカス表示 3:1。色だけで状態を伝えていないか `[must / run]` — WCAG 1.4.3 / 1.4.11 / 1.4.1(知識ベース・未fetch)
- 見出しレベルの飛び・ランドマーク(`main`, `nav`)・`lang` 属性 `[should / diff]`(知識ベース)
- アニメーションに `prefers-reduced-motion` 対応 `[should / diff(CSS)]`(知識ベース)
- `eslint-plugin-jsx-a11y`(React)/`eslint-plugin-vuejs-accessibility`(Vue)等の静的チェックを無効化していないか `[should / diff]`(知識ベース)

### Inferences
- 「4.1.1 Parsing(重複 ID・不正なネスト)」を WCAG 違反として指摘するのは 2.2 では**古い**。ただし重複 ID は `aria-labelledby`/`htmlFor`/Turbo Frame の参照を壊すので、機能バグとして指摘する価値は残る。
- 2.5.8 / 1.4.3 / 2.4.11 は CSS とレイアウトに依存し差分だけでは判定困難(run 判定)。PR テンプレートでスクリーンショットや axe 結果の添付を求めると効率的。

### Gaps
- WCAG 3.0 の進捗(2026 年時点)は未確認。
- 日本の JIS X 8341-3 と WCAG 2.2 の対応状況は未確認。

---

## Q6. フロントエンドパフォーマンス(バンドル、再レンダー、Compiler 下のメモ化、画像、Core Web Vitals / INP)

### Takeaway
INP は「Good ≤200ms / Poor >500ms(75パーセンタイル)」。レビューではイベントハンドラ内の重い同期処理・レイアウトスラッシング・巨大 DOM を差分で疑い、`"use client"` の位置や重い依存の import でバンドルを抑える。手動メモ化は Compiler があれば原則不要。

### Cited Findings
- INP 閾値: Good ≤200ms、Needs improvement 200–500ms、Poor >500ms(モバイル/デスクトップ別の 75 パーセンタイル) — [Optimize INP](https://web.dev/articles/optimize-inp)
- INP の3フェーズ: input delay / processing duration / presentation delay — 同上
- 対策: 長いタスクの分割、`setTimeout` 等でメインスレッドへ yield、次フレームに必要な視覚更新だけ先に行い残り(保存等)を後回し(`requestAnimationFrame`+`setTimeout`)、レイアウトスラッシング回避、DOM サイズ削減、`content-visibility`、JS による大量 HTML 描画の制限、Web Worker — 同上
- `"use client"` は末端のインタラクティブコンポーネントにのみ付けてクライアント JS を削減 — [Server and Client Components](https://nextjs.org/docs/app/getting-started/server-and-client-components)
- React Compiler が自動メモ化。手動 `useMemo` は計測して遅い場合のみ(`console.time` で計測)、Compiler 下では多くの場合不要 — [You Might Not Need an Effect](https://react.dev/learn/you-might-not-need-an-effect); [React Compiler v1.0](https://react.dev/blog/2025/10/07/react-compiler-1)
- Next.js 16 の `next/image` 既定変更: `minimumCacheTTL` 4時間、`imageSizes` から 16 除外、`qualities` 既定 `[75]`、ローカル画像のクエリ文字列は `images.localPatterns` 必須 — [Next.js 16](https://nextjs.org/blog/next-16)
- Turbo: アプリバンドルを `<head>` で読み込まないと遷移ごとに再ロード — [Turbo Handbook: Building](https://turbo.hotwired.dev/handbook/building)

**チェックリスト(Q6)**
- 重い依存(日付・グラフ・エディタ・アイコン全量 import、lodash 全体)の新規追加・バレル import でバンドルが増えていないか。動的 import(`next/dynamic`/`React.lazy`/`import()`)で遅延できないか `[should / repo]`(知識ベース; bundle analyzer 等で確認)
- `"use client"` 境界が高すぎないか `[should / diff]` — Server and Client Components
- イベントハンドラ内で重い同期計算・大量 DOM 更新・レイアウト読み書き交互をしていないか(INP) `[should / diff]` — Optimize INP
- 大きなリストは仮想化・ページング、オフスクリーンは `content-visibility` を検討 `[should / diff]` — 同上
- 入力に連動する重い再描画は `useDeferredValue`/`startTransition` で緊急更新と分離しているか `[should / diff]` — [useTransition](https://react.dev/reference/react/useTransition)(知識ベース・未fetch)
- 不要な再レンダー源: 毎レンダー新規オブジェクトを Context value に渡す、巨大 Context、親の頻繁な state 更新。ただし Compiler 有効なら手動 memo 追加より state の配置(下げる/分割)で解決しているか `[should / repo]` — React Compiler 1.0(+推論)
- 画像: `next/image` か `width`/`height`(または `aspect-ratio`)指定で CLS 防止、LCP 画像に `priority`/`fetchpriority="high"`、それ以外は `loading="lazy"`、適切な `sizes` `[should / diff]` — Next.js 16(既定変更)/ web.dev(知識ベース・未fetch)
- Web フォント・サードパーティスクリプトの読み込み戦略(`next/font`, `next/script` の strategy, `defer`) `[should / diff]`(知識ベース)
- ウォーターフォールなデータ取得(Q4参照)とクライアント側フェッチによる LCP 悪化 `[should / diff]`
- 計測根拠: 性能目的の変更に before/after(Lighthouse, React Profiler, Web Vitals)が添付されているか `[nit/should / run]`(推論)

### Inferences
- INP は 2024 年3月に FID を置き換えて Core Web Vitals になった([web.dev blog](https://web.dev/blog/inp-cwv-march-12), 知識ベース・未fetch)。FID ベースの助言は**古い**。
- 「全部 memo で包む」最適化は Compiler 時代には効果が薄く可読性を損なう。性能指摘は「計測で裏付けのあるもの」に絞るのが React 公式の姿勢と整合。

### Gaps
- `scheduler.yield()` のブラウザ対応状況(2026 年)は本調査で未確認(optimize-inp 記事本文には記載なし)。
- LCP/CLS の最新閾値ページは本調査で再fetchしていない(一般に LCP ≤2.5s、CLS ≤0.1 だが未確認)。

---

## Q7. typescript-eslint・React docs・大手企業ガイドが重視する点(保守性含む)

### Takeaway
公式系(typescript-eslint, Google TS Style Guide, react.dev)は共通して「型の逃げ道(any/as/!/ts-ignore)の抑制」「Promise の扱い」「網羅性」「Effect の最小化」を重視。日本企業の公開ガイドは本調査では一次資料に到達できなかった。

### Cited Findings
- typescript-eslint: `recommended` は「ほぼ常にバッドプラクティスかバグ」を検出するドロップイン、`strict` は追加で意見の強いルール(習熟チーム向け・非安定)、`stylistic` はロジックに影響しない書き方の統一 — [typescript-eslint Shared Configs](https://typescript-eslint.io/users/configs/)
- Google TS Style Guide: named export のみ、`import type`、`readonly`、`===`(`== null` は例外)、`for...in` 非推奨、`#private` 不使用(`private` 修飾子)、getter は純粋、decorator 新規定義禁止 — [Google TypeScript Style Guide](https://google.github.io/styleguide/tsguide.html)
- React: 新規コードのメモ化は Compiler に任せる。`eslint-plugin-react-hooks` の recommended に Compiler 系ルール統合 — [React Compiler v1.0](https://react.dev/blog/2025/10/07/react-compiler-1)
- Next.js 16 で `next lint` 削除、ESLint(flat config)または Biome を直接使う — [Next.js 16](https://nextjs.org/blog/next-16)
- 日本語での検索では企業の社内レビューガイドライン本体は見つからず、一般的観点(型・null 処理・再レンダー・遅延読み込み)のまとめ記事や Dify のフロントエンドレビュー用スキル(High/Medium/Low の緊急度分類)が出てきた — [skill-gallery: langgenius frontend code review guide](https://www.skill-gallery.jp/ja/blog/langgenius-frontend-code-review-guide)(二次情報)

**チェックリスト(Q7: 保守性)**
- lint 抑制コメント(`eslint-disable`, 特に `react-hooks/exhaustive-deps`、`@typescript-eslint/no-explicit-any`)の新規追加に理由があるか `[should / diff]` — typescript-eslint / React Compiler 1.0
- コンポーネントの責務過多(データ取得+整形+表示+イベント)、巨大ファイル。ロジックはカスタムフック/純関数に分離し、純関数は UI 非依存か `[should / diff]`(推論)
- props の boolean 乱立(`isPrimary isLarge isDanger`)より variant ユニオン型 `[nit / diff]`(推論)
- 公開コンポーネント/関数の型が過度に広い(`string` で列挙値を受ける)・`React.FC` で children を暗黙許容等 `[nit / diff]`(知識ベース)
- default export を禁止する規約(Google)と Next.js のファイル規約(page/layout は default export 必須)の衝突に注意。規約はチームの lint 設定に従う `[nit / repo]` — Google TS Style Guide(+推論)
- マジックナンバー・文字列、重複コード、既存ユーティリティ/デザインシステムコンポーネントの再発明 `[should / repo]`(推論)
- CSS: グローバル CSS の新規追加による副作用、`!important`、z-index の場当たり値、ハードコード色(デザイントークン不使用)、ダークモード・レスポンシブ崩れ `[should / diff]`(推論)
- 死んだコード・`console.log`・TODO の放置 `[nit / diff]`(推論)

### Inferences
- 重大度の割り当ての目安: 型の逃げ道は「境界・公開 API なら must、内部の局所なら should」。lint 抑制は「理由なしなら should」。スタイル(interface vs type、`T[]` vs `Array<T>`)はツールに任せ nit 以下(人間がレビューで指摘しない)とするのが効率的。
- 差分のみで判定できない観点(tsconfig/lint 設定、バックエンドスキーマ同期、ERB と Stimulus の名前一致、Turbo Frame ID の対応、キャッシュ無効化の漏れ、a11y のコントラスト・フォーカス隠れ)は、AI/自動レビューでは「repo コンテキスト取得」または「人間の実機確認」に回す設計が必要。

### Gaps
- Airbnb JavaScript/React Style Guide は本調査で取得していない(更新頻度が低く、TypeScript・React 19 以降には追随していない可能性が高いが未確認)。
- メルカリ・サイボウズ(Cybozu Frontend Expert Team)・LINE ヤフー・Vercel 等の公開フロントエンドレビュー指針について、本調査では一次資料に到達できなかった(日本語検索で該当なし)。レポートで企業名を挙げる場合は別途確認が必要。
- Vercel の公式「React best practices」系ドキュメントの有無・内容は未確認。
