# PRレビュー観点（Rails + TypeScript）: (A) テスト / (B) ドキュメント / (C) 設定・CI・依存関係

調査日: 2026-10-28。凡例:
- 重大度: **must**（マージ前に必ず直す）/ **should**（原則直す。理由があれば見送り可）/ **nit**（任意）。重大度は出典の推奨の強さとリスクから調査者が付けた「既定値」。出典自体が重大度を定めているのは Kent C. Dodds の記事だけ。
- 判定: **差分** = diff だけで判断できる / **文脈** = リポジトリ全体・CI結果・外部情報の確認が必要。
- 出典の確認状況: 「[取得済]」は本セッションで WebFetch して内容を確認した出典。「[既知]」は調査者の既存知識に基づく正規URLで、本セッションでは再取得していない（Gaps に列挙。レポート執筆時に要注意）。

---

## (A) テスト（RSpec/Minitest・FactoryBot・Capybara、Jest/Vitest・Testing Library・Playwright/Cypress）

### Takeaway
テストPRのレビューでは主に次の4点を見る。(1) 変更した振る舞いが public API／ユーザーに見える挙動の水準で検証されているか、(2) 異常系・境界値まで網羅しているか、(3) 実装詳細やモックへの過度な依存がないか、(4) 非決定性（時間・乱数・順序・sleep・外部ネットワーク）を持ち込んでいないか。Google SWE Book、Betterspecs、Testing Library、Playwright の推奨はこの4点で一致する。

### Cited Findings

#### 一次情報の要点
- Google「Software Engineering at Google」12章（Unit Testing）の要点 [取得済] — [SWE Book ch.12](https://abseil.io/resources/swe-book/html/ch12.html)
  - 理想のテストは変更されない（"the ideal test is unchanging"）。テストを変えるべきなのは要件が変わったときだけで、リファクタリングでは変えない。
  - public API 経由でテストする。
  - interaction ではなく state を検証する。モックフレームワークへの過度な依存は壊れやすさの原因になる。
  - テストはメソッド単位ではなく振る舞い単位で書く（given/when/then）。テスト名には操作と期待結果を書く。
  - テスト内にロジックを書かない（"stick to straight-line code over clever logic"）。
  - 失敗メッセージには期待値・実際の値・関連パラメータを含める。
  - DRY より DAMP を優先する。
  - 共通の setup はテストの completeness を損なうことがある。
- Betterspecs の要点 [取得済] — [betterspecs.org](https://www.betterspecs.org/)
  - `describe '.class_method'` / `'#instance_method'` の記法を使う。context は when/with/without で始める。説明文は40文字以内にする。
  - 単体スペックでは1例1振る舞い（"each test should make only one assertion"）。
  - 正常系だけでなく、不正値・境界・not found・権限外などもテストする（"Test all possible cases"）。
  - 必要なデータだけを作る（データが大量なら設計を疑う）。fixture ではなく factory を使う。
  - `let` は遅延評価、`let!` はクエリ用データなど即時に作る必要がある場合だけ使う。
  - モックは使いすぎない。
  - 外部HTTPは WebMock/VCR でスタブする（"you should stub it with solutions like webmock"）。
  - 新規コードでは `expect` 構文を使い、`should` は使わない。
- Kent C. Dodds「Common mistakes with React Testing Library」（2020-05-04公開。古いが現在も広く参照される）[取得済] — [記事](https://kentcdodds.com/blog/common-mistakes-with-react-testing-library)
  - 記事が High としている誤り
    - DOMプロパティを直接 assert する（`toBeDisabled()` など jest-dom マッチャーを使うべき）
    - アクセシブルなクエリで取れるのに `getByTestId` を使う
    - 冗長または誤った ARIA を付ける
    - 存在確認に `query*` を使う（`query*` は不在確認専用）
    - `waitFor(() => getBy…)` と書く（`findBy*` を使うべき）
    - 空の `waitFor` コールバック
    - `waitFor` 内で副作用を起こす
  - 記事が Medium としている誤り
    - `screen` を使わない
    - 不要な `act` で囲む
    - `fireEvent` を使う（`user-event` を使うべき）
    - ESLint プラグイン（eslint-plugin-testing-library / eslint-plugin-jest-dom）を入れていない
    - 手動で `cleanup` を呼ぶ
- Testing Library の基本原則（"The more your tests resemble the way your software is used, the more confidence they can give you."）。コンポーネントのインスタンスではなく DOM ノードを扱う [取得済] — [Guiding Principles](https://testing-library.com/docs/guiding-principles)
- Playwright Best Practices [取得済] — [playwright.dev/docs/best-practices](https://playwright.dev/docs/best-practices)
  - ユーザーに見える振る舞いをテストする。テストは互いに完全に独立させる。
  - "Only test what you control"。外部依存は Network API でスタブする。
  - `getByRole` などユーザー向けの属性を優先したロケーターを使い、CSS/XPath は避ける。
  - auto-wait 付きの web-first assertion を使う。`isVisible()` のような即時評価の手動 assertion は使わない。
  - missing await を防ぐため `@typescript-eslint/no-floating-promises` を有効にする。
  - CI の失敗調査には動画やスクショではなく trace viewer を使う。

#### チェックリスト (A)

| # | 観点 | 重大度 | 判定 | 出典 |
|---|---|---|---|---|
| A1 | プロダクションコードで変わった振る舞い（新分岐・新しいエラー経路・バグ修正）それぞれに対応するテストがある。バグ修正なら、修正前のコードで落ちる回帰テストがある | must | 差分（本体diffと突き合わせ） | [SWE Book ch.12](https://abseil.io/resources/swe-book/html/ch12.html) |
| A2 | 正常系だけでなく、異常系・境界値（nil/空/上限/権限外/not found/バリデーション失敗/外部APIエラー）を網羅している | should | 差分 | [Betterspecs](https://www.betterspecs.org/) |
| A3 | 空振りテストになっていない。例: assertion がない、`expect` の書き忘れ、`waitFor` の空コールバック、`query*` で存在確認、`await` 漏れの Promise、条件分岐の中に assertion がある、`it` の中身が空や `skip` / `xit` / `.only` のまま | must | 差分 | [Kent C. Dodds](https://kentcdodds.com/blog/common-mistakes-with-react-testing-library); [Playwright BP](https://playwright.dev/docs/best-practices) |
| A4 | テストが一度は失敗するのを確認したか（実装を壊すと落ちるか）。PR説明に記載があるとよい | should | 文脈 | [SWE Book ch.12](https://abseil.io/resources/swe-book/html/ch12.html)（失敗メッセージの明確さ） |
| A5 | 実装詳細のテストを避けている。private メソッドの直接テスト、内部 state やコンポーネントインスタンスへのアクセス、呼び出し回数だけを検証するテストは避け、public API／ユーザーに見える結果で検証する | should | 差分 | [SWE Book ch.12](https://abseil.io/resources/swe-book/html/ch12.html); [Testing Library Principles](https://testing-library.com/docs/guiding-principles) |
| A6 | モックしすぎていない。自分が所有するクラスをモックで置き換えすぎて、何もテストしていない状態になっていない。`allow_any_instance_of` や広範な `jest.mock` を多用していない | should | 差分 | [SWE Book ch.12](https://abseil.io/resources/swe-book/html/ch12.html); [Betterspecs](https://www.betterspecs.org/) |
| A7 | 外部HTTP・外部SaaSへの実通信がない（WebMock/VCR、MSW、Playwright `page.route`）。VCR カセットに秘密情報（トークン等）が含まれていない | must | 差分 | [Betterspecs](https://www.betterspecs.org/); [Playwright BP](https://playwright.dev/docs/best-practices) |
| A8 | 時刻に依存しない。`Time.current` / `Date.now()` を直接比較せず、`travel_to` / `freeze_time` や `vi.useFakeTimers()` / `jest.useFakeTimers()` で固定している。タイムゾーン・月末・うるう年・DST を考慮している | must | 差分 | [Martin Fowler: Eradicating Non-Determinism in Tests](https://martinfowler.com/articles/nonDeterminism.html) [既知] |
| A9 | 固定 sleep を使っていない（`sleep`、`page.waitForTimeout`、`cy.wait(ms)`、`setTimeout` 待ち）。Capybara の待機付きマッチャー（`have_content` 等）、Playwright の web-first assertion、`findBy*` を使っている | must | 差分 | [Playwright BP](https://playwright.dev/docs/best-practices); [Kent C. Dodds](https://kentcdodds.com/blog/common-mistakes-with-react-testing-library) |
| A10 | 順序に依存しない。テスト間で状態（グローバル変数・クラス変数・DB・ENV・キャッシュ・localStorage）を共有していない。RSpec の `--order random` やテストランナーの並列実行で通る | must | 差分＋文脈（CI設定） | [Playwright BP](https://playwright.dev/docs/best-practices)（"completely isolated"） |
| A11 | 乱数・Faker の値に依存して結果が変わらない（seed が固定されている。ユニーク制約のある値は sequence で作る） | should | 差分 | [Martin Fowler: Non-Determinism](https://martinfowler.com/articles/nonDeterminism.html) [既知] |
| A12 | FactoryBot が肥大化していない。デフォルト factory には必須属性だけを書き、任意の関連は trait に分ける。`create` で済むところを `build` / `build_stubbed` にできないか検討する。関連による連鎖 create（factory cascade）が起きていない | should | 差分＋文脈（factories/） | [Betterspecs](https://www.betterspecs.org/)（"Create only the data you need"）; [TestProf](https://test-prof.evilmartians.io/) [既知] |
| A13 | `let!` / `before` を使いすぎていない。どの例でも使われない eager なデータを作っていない。共通 setup が深くネストしすぎて、各テストに必要な情報が読み取れない状態になっていない（DAMP） | should | 差分 | [Betterspecs](https://www.betterspecs.org/); [SWE Book ch.12](https://abseil.io/resources/swe-book/html/ch12.html) |
| A14 | テスト内にロジックがない（if/ループ/期待値の計算）。期待値はリテラルで書かれている | should | 差分 | [SWE Book ch.12](https://abseil.io/resources/swe-book/html/ch12.html) |
| A15 | テスト名・describe/context が振る舞いと期待結果を表している（context は when/with/without で始める。`should` を使わず三人称現在形で書く） | nit | 差分 | [Betterspecs](https://www.betterspecs.org/); [SWE Book ch.12](https://abseil.io/resources/swe-book/html/ch12.html) |
| A16 | Testing Library のクエリ優先順位を守っている（`getByRole`（name付き）> `getByLabelText` > … > `getByTestId`）。`container.querySelector` を使っていない。`screen` と `user-event` を使っている | should | 差分 | [Kent C. Dodds](https://kentcdodds.com/blog/common-mistakes-with-react-testing-library); [Queries priority](https://testing-library.com/docs/queries/about/#priority) [既知] |
| A17 | E2E/システムテストのロケーターが role・text・label ベースで、CSSクラスや DOM 構造に依存していない | should | 差分 | [Playwright BP](https://playwright.dev/docs/best-practices) |
| A18 | スナップショットを乱用していない。巨大なスナップショットや、意図の分からないスナップショット更新（`-u` で一括更新した差分）をレビューなしで受け入れていない。スナップショットは小さく焦点を絞る | should | 差分 | [Jest: Snapshot Testing Best Practices](https://jestjs.io/docs/snapshot-testing#best-practices) [既知] |
| A19 | テストピラミッド／トロフィーのバランスが取れている。単体で十分な検証をシステムテストで書いていない（遅い）。逆に、統合点（コントローラ→サービス→DB、APIクライアント⇔UI）がモックだけで終わっていない | should | 文脈 | [Betterspecs](https://www.betterspecs.org/)（"Test what you see"）; [Kent C. Dodds: Write tests. Not too many. Mostly integration.](https://kentcdodds.com/blog/write-tests) [既知] |
| A20 | 遅いテストを追加していない（不要な JS ドライバ、システムテストでの大量データ、`sleep`）。CI 実行時間の増加を確認する | should | 文脈（CI時間） | [Betterspecs](https://www.betterspecs.org/)（Faster tests） |
| A21 | flaky テストを `retry` や `skip` で黙らせていない。隔離する場合は issue を作り、PR に理由を書いている | must | 差分 | [Martin Fowler: Non-Determinism](https://martinfowler.com/articles/nonDeterminism.html) [既知]（quarantine の推奨） |
| A22 | テスト用の lint を入れている、または追加したテストが既存 lint に違反していない（rubocop-rspec、eslint-plugin-testing-library、eslint-plugin-jest-dom、`@typescript-eslint/no-floating-promises`） | nit | 差分＋文脈 | [Kent C. Dodds](https://kentcdodds.com/blog/common-mistakes-with-react-testing-library); [Playwright BP](https://playwright.dev/docs/best-practices); [RSpec Style Guide](https://rspec.rubystyle.guide/) [既知] |
| A23 | `.only` / `fit` / `fdescribe` / `focus: true` のコミット漏れ、デバッグ用の `binding.pry` / `debugger` / `console.log` / `save_and_open_page` が残っていない | must | 差分 | 一般的慣行（直接の出典は Gaps 参照） |
| A24 | 失敗時に原因が分かる assertion にしている（`expect(x).to eq(...)` や jest-dom マッチャーを使い、`expect(a == b).to be true` は避ける） | nit | 差分 | [SWE Book ch.12](https://abseil.io/resources/swe-book/html/ch12.html); [Kent C. Dodds](https://kentcdodds.com/blog/common-mistakes-with-react-testing-library) |

### Inferences
- 差分だけで判定できる項目（A3, A7–A9, A14, A16–A18, A23）は機械的に検出しやすく、AIレビューや lint で自動化するのに向いている。逆に A1, A4, A19, A20 は本体の diff・CI 結果・既存テスト構成を見る必要がある。
- Rails ではテスト時の時刻、外部HTTP、FactoryBot の連鎖 create が flaky と遅さの主な原因になりやすい。TS 側では await 漏れ、fake timers の後始末漏れ、MSW ハンドラーの共有状態が同じ位置づけになる（推論。定量データはない）。
- Kent C. Dodds の記事は2020年公開。Testing Library 自体の API（`user-event` v14 の `userEvent.setup()` 等）はその後も変わっているので、最新ドキュメントとの照合を推奨する。

### Gaps
- Google Testing Blog の flaky テスト記事（2016-05-27）は本文を取得できず、「Google のテストの約1.5%が flaky」といった数値は検証していないため記載しなかった。
- TestProf（let_it_be / FactoryProf）のページは取得時に404だった。URL が移転した可能性がある。
- Martin Fowler「Eradicating Non-Determinism in Tests」、Jest のスナップショット BP、Testing Library のクエリ優先順位ページ、RSpec Style Guide は今回再取得していない（[既知]）。
- A23（`.only` やデバッグコードの残存）について、権威ある単一の出典は見つけていない。一般的慣行として扱う。

---

## (B) ドキュメント（README、docs/*.md、ADR、APIドキュメント、コードコメント、CHANGELOG、PR説明）

### Takeaway
ドキュメント変更で最も重要なのは「コードと一致しているか」だ。古い手順、壊れたコマンドやリンクは must 扱いにする。次に、読者と文書タイプが合っているかを見る（Diátaxis の4分類）。文体（Google / Microsoft / JTF / textlint）は原則 nit〜should とし、lint で自動化するのがよい。ADR は Zimmermann のレビュー7問で中身の妥当性を確認する。

### Cited Findings

#### 一次情報の要点
- Diátaxis の文書は4種類。どれも「行動か認知か」「習得（study）か適用（work）か」の2軸で決まる [取得済] — [Diátaxis compass](https://diataxis.fr/compass/), [diataxis.fr](https://diataxis.fr/)
  - Tutorial: 行動 × 習得
  - How-to guide: 行動 × 適用
  - Reference: 認知 × 適用
  - Explanation: 認知 × 習得
  - コンパスは「文書の中身がユーザーのニーズと合っているか」を確かめるための道具として紹介されている。
- Google developer documentation style guide の要点 [取得済] — [Highlights](https://developers.google.com/style/highlights)
  - 会話的でフレンドリーな文体にする。将来機能の予告は書かない。
  - 二人称（you）と能動態で書く。条件節は指示の前に置く。
  - 見出しは sentence case にする。手順は番号付きリスト、それ以外は箇条書きにする。
  - コードは code font、UI 要素は太字にする。誤読されない日付形式を使う。
  - リンクテキストは行き先が分かる表現にする。代替テキストを付けるなどアクセシビリティに配慮し、非ネイティブ読者も想定する。
- textlint-rule-preset-ja-technical-writing は23ルールで構成される [取得済] — [GitHub](https://github.com/textlint-ja/textlint-rule-preset-ja-technical-writing)
  - 主な既定値: sentence-length 100（v3.0.0以降。それ以前は90）、max-comma 3、max-ten 3、max-kanji-continuous-len 6。
  - 主なルール: no-mix-dearu-desumasu（本文はですます、箇条書きはである）、ja-no-mixed-period「。」、no-doubled-joshi、no-double-negative-ja、no-dropping-the-ra、no-exclamation-question-mark、no-hankaku-kana、ja-no-weak-phrase、ja-no-redundant-expression、ja-unnatural-alphabet、no-zero-width-spaces、no-nfd、no-unmatched-pair など。
  - README は既定値を「やや厳しめ」とし、調整を前提にしている。安定版は1月と7月の半年ごとにリリースされる。
- Olaf Zimmermann の ADR レビュー観点（2023-04-05公開、2026-08-28更新）[取得済] — [How to review ADRs](https://www.ozimmer.ch/practices/2023/04/05/ADRReview.html)
  - 7つの問い
    1. ADR にするほど重要な問題か
    2. 選択肢は現実的か、漏れはないか
    3. 判断基準（decision drivers）は互いに独立していて網羅的か
    4. 基準が衝突する場合に優先順位があるか
    5. 選んだ案は問題を解決し、根拠に説得力があるか
    6. 各案の良い帰結と悪い帰結を客観的に書いているか
    7. 実行可能で要件まで追跡でき、有効期限や見直し日があるか
  - レビュー側のアンチパターン: Pass Through、Copy Edit（中身ではなく文言だけを直す）、Power Game など。
- ADR の定義: 1つの ADR は1つの設計判断と、その根拠・トレードオフ・帰結を記録する。プロジェクト内の ADR の集合が decision log になる。Nygard（2011）が普及させた [取得済] — [adr.github.io](https://adr.github.io/), [Nygard 2011](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions.html)

#### チェックリスト (B)

| # | 観点 | 重大度 | 判定 | 出典 |
|---|---|---|---|---|
| B1 | 記述がコードと一致している（コマンド、オプション名、環境変数名、設定キー、APIのパス・パラメータ・レスポンス例、デフォルト値）。コード変更PRで関連ドキュメントの更新漏れがないかも見る | must | 文脈 | [Google style: Highlights](https://developers.google.com/style/highlights)（正確性の前提）; 一般的慣行 |
| B2 | セットアップ・実行手順が現状で動く（Ruby/Node のバージョン、`bin/setup`、`yarn`/`pnpm` の別、Docker 手順）。古い手順や削除済みスクリプトへの参照がない | must | 文脈 | 同上 |
| B3 | リンク切れ、アンカー切れ、相対パスの誤りがない。CI で lychee や markdown-link-check などのリンクチェッカーを回すとよい | should | 差分（リンク先は文脈） | [lychee](https://github.com/lycheeverse/lychee) [既知] |
| B4 | 文書タイプが混在していない（チュートリアルにリファレンスの網羅表を詰め込む、How-to の手順中に長い設計説明を挟む、など）。読者と目的が冒頭で分かる | should | 差分 | [Diátaxis compass](https://diataxis.fr/compass/) |
| B5 | 手順は番号付きリストで書き、条件は指示の前に置き、コード・コマンドはコードブロックかインラインコードにする。コピペで動くコマンドにする（`$` プロンプトや出力を混ぜない） | should | 差分 | [Google style: Highlights](https://developers.google.com/style/highlights) |
| B6 | リンクテキストが行き先を表す（「こちら」「here」を避ける）。画像に代替テキストがある | nit | 差分 | [Google style: Highlights](https://developers.google.com/style/highlights); [Microsoft Writing Style Guide](https://learn.microsoft.com/en-us/style-guide/welcome/) [既知] |
| B7 | 見出し階層が正しい（H1は1つ、レベルを飛ばさない）。見出しは sentence case（英語の場合） | nit | 差分 | [Google style: Highlights](https://developers.google.com/style/highlights) |
| B8 | 日本語の文体が統一されている（です・ます／である の混在なし、句点の統一、全角と半角の扱い、半角カナなし、一文が長すぎない（目安100字）、読点が多すぎない、二重否定や冗長表現・弱い表現がない）。textlint preset の結果を確認する | nit（CIで強制するなら should） | 差分 | [textlint preset ja-technical-writing](https://github.com/textlint-ja/textlint-rule-preset-ja-technical-writing); [JTF日本語標準スタイルガイド](https://www.jtf.jp/tips/styleguide) [既知] |
| B9 | 用語・表記がリポジトリ内で統一されている（プロダクト名、機能名、カタカナ語の長音、英字の大文字小文字） | nit | 文脈 | [JTF日本語標準スタイルガイド](https://www.jtf.jp/tips/styleguide) [既知]; textlint の prh ルール等 |
| B10 | 機密情報を含まない（実トークン、内部URL、顧客データ、個人のメールアドレス、本番ホスト名）。サンプル値はダミーだと明示されている | must | 差分 | [GitHub Actions secure use](https://docs.github.com/en/actions/reference/security/secure-use)（秘密情報の扱い全般） |
| B11 | ADR に Context / Decision / Status / Consequences（Nygard 形式）、または検討した選択肢・判断基準・各案の長所と短所（MADR 形式）がそろっている | should | 差分 | [adr.github.io](https://adr.github.io/); [Nygard 2011](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions.html) |
| B12 | ADR の中身が妥当である（Zimmermann の7問: 重要性、選択肢の現実性と網羅性、基準の独立性と網羅性、基準の優先順位、根拠、良い帰結と悪い帰結の客観性、追跡可能性と見直し日）。文言だけを直すレビュー（Copy Edit）で終わらせない | should | 差分＋文脈 | [Zimmermann: How to review ADRs](https://www.ozimmer.ch/practices/2023/04/05/ADRReview.html) |
| B13 | 既存の ADR を書き換えて判断を変えていない。判断を変えるなら新しい ADR を作り、旧 ADR を Superseded にしてリンクする | should | 差分 | [Nygard 2011](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions.html) [既知の内容。本セッションでは本文未取得] |
| B14 | APIドキュメント（OpenAPI / rswag / TypeDoc / YARD）が実装と一致し、エラーレスポンス・認可要件・破壊的変更が明記されている。生成物の場合は生成元と同期している | must（公開APIの場合） | 文脈 | 一般的慣行（直接の出典は Gaps 参照） |
| B15 | コードコメントが「何をしているか」ではなく「なぜそうしたか」を説明し、コードの変更後に古くなっていない。TODO には issue リンクか担当者がある | should | 差分 | [SWE Book ch.10 Documentation](https://abseil.io/resources/swe-book/html/ch10.html) [既知] |
| B16 | CHANGELOG がユーザー向けの変更を Added / Changed / Deprecated / Removed / Fixed / Security に分けて記載し、破壊的変更と移行手順を明示している | should | 差分 | [Keep a Changelog](https://keepachangelog.com/) [既知] |
| B17 | PR説明に目的（なぜ）、変更概要、影響範囲、テスト方法・確認結果、リスクとロールバック手順、関連 issue があり、スクリーンショットが UI 変更と一致している | should | 差分（PR本文） | [Google Eng Practices: Writing good CL descriptions](https://google.github.io/eng-practices/review/developer/cl-descriptions.html) [既知] |
| B18 | 将来機能の予告や日付の曖昧な表現（「近日」「最新の」）を避け、バージョンや日付を明記している | nit | 差分 | [Google style: Highlights](https://developers.google.com/style/highlights) |

### Inferences
- B1, B2, B14 はドキュメントだけの diff では判断できない。コード側の diff や実際に手順を流した結果と突き合わせる必要があるため、レビュー支援ツールでは「関連コードの参照」を前提に設計するのが妥当だろう。
- 日本語の文体（B8, B9）は textlint で自動化し、人手のレビューは nit 扱いにするとノイズが減る。Zimmermann の Copy Edit アンチパターンも、人の注意を中身に向けるべきだと示している。

### Gaps
- Diátaxis の各タイプのページ（tutorials/ や how-to-guides/ 等）は取得しておらず、「タイプを混ぜるな」という明示的な文言は compass ページでは確認できなかった。
- JTF日本語標準スタイルガイド、Microsoft Writing Style Guide、Keep a Changelog、Google Eng Practices の CL description、SWE Book 10章は今回取得していない（[既知]）。最新版の日付は未確認。
- API ドキュメントのレビュー観点として、権威ある単一の出典は見つけていない。

---

## (C) 設定・CI・依存関係（Gemfile/Gemfile.lock、package.json/lockfile、GitHub Actions、Dockerfile、config/*.yml、credentials、フィーチャーフラグ）

### Takeaway
サプライチェーンと権限が最大のリスクになる。主に次の3点を見る。
- **Actions**: SHA ピン（または新しい workflow dependency lockfile）を使い、`permissions` を最小化し、`${{ github.event.* }}` を `run:` に直接埋め込まず（スクリプトインジェクション）、`pull_request_target` で未信頼コードを checkout していないか。
- **依存関係**: 追加の必要性、メンテナンス状況、ライセンス、lockfile の整合性、メジャーアップデートの破壊的変更を確認する。2025年の Shai-Hulud 以降は、install scripts の制限と minimumReleaseAge も確認項目に加わった。
- **Docker・環境設定**: 非 root で実行し、ベースイメージを digest でピンし、秘密情報を焼き込まず、環境間の設定差分が意図どおりか確認する。

### Cited Findings

#### GitHub Actions（docs.github.com「Secure use reference」）[取得済] — [docs.github.com](https://docs.github.com/en/actions/reference/security/secure-use)
- アクションはフルの commit SHA でピンする。タグは移動や削除ができるので、作者を信頼できる場合に限る。SHA は fork ではなく本家リポジトリのものか確認する。
- **新しい推奨（2026年時点のページで確認）**: 利用できる場合は workflow dependency lockfile を使う。推移的依存を含む正確なコミットを記録し、ページは "the strongest protection available" と呼んでいる。これを採用したリポジトリでは SHA ピンより優先される。本機能の提供開始日と GA 状況は未確認。
- `GITHUB_TOKEN` は既定を contents read のみにし、必要なジョブだけで権限を上げる。
- `github.event.pull_request.title` などの未信頼入力を `run:` に直接埋め込まず、中間の環境変数を経由させる（"set the value of the expression to an intermediate environment variable"）。
- `pull_request_target` / `workflow_run` は高い権限で動くので、不要なら使わない。これらのワークフローで未信頼の PR コードを checkout しない。他ワークフローの artifact も慎重に扱う。
- 秘密情報の扱い
  - 構造化データ（JSON/YAML）を1つの secret にしない（マスクは完全一致で効くため）。値ごとに個別の secret にする。
  - 派生値（Base64 化したもの、署名した JWT）も secret として登録する。
  - 漏れたらログを消してローテーションする。
  - environment の required reviewers で secret の利用を制御する。
- self-hosted runner は public リポジトリでは「ほぼ使うべきでない」。使うなら JIT（エフェメラル）にする。
- クラウド認証は OIDC にして長期のクレデンシャルを持たない。
- `.github/workflows` を CODEOWNERS に入れる。
- Dependabot でアクションを更新する（ただし SHA ピンしたアクションは Dependabot alerts の対象外）。
- `dependency-review-action` を使い、サードパーティアクションのソースを監査し、code scanning と OpenSSF Scorecard を有効にする。

#### Dockerfile（Docker Docs「Building best practices」）[取得済] — [docs.docker.com](https://docs.docker.com/build/building/best-practices/)
- multi-stage ビルドで最終イメージを小さくする。
- 信頼できる最小のベースイメージを使い、digest でピンする（タグは可変）。定期的に再ビルドする（`--pull`、`--no-cache`）。
- `.dockerignore` を用意し、不要なパッケージは入れない。1コンテナ1関心にする。
- `apt-get update` と `install` は同じ RUN に書く。パイプには `set -o pipefail` を付ける。
- 可能なら `USER` で非 root にする。COPY を ADD より優先する。キャッシュを意識してレイヤーを並べる。
- 注: このページには build secrets（ARG/ENV で秘密を渡さない）と HEALTHCHECK の記述はなかった。

#### npm / pnpm のサプライチェーン
- pnpm 公式「Supply chain security」[取得済] — [pnpm.io/supply-chain-security](https://pnpm.io/supply-chain-security)
  - `minimumReleaseAge` の既定は1440分（1日）で、`10080`（1週間）も例に挙がっている。
  - 依存の build script は `allowBuilds` に列挙したものだけを実行し、`strictDepBuilds` は既定で有効。`dangerouslyAllowAllBuilds` は避ける。
  - postinstall を持つ信頼済みパッケージの更新は慎重にレビューする。
  - `trustPolicy: no-downgrade` で信頼レベルの低下（trusted publisher だったパッケージが provenance なしになる等）をブロックする。
  - `blockExoticSubdeps` は既定で有効で、推移依存の git や tarball URL を拒否する。
  - lockfile をコミットして更新を意図的に行う。`pnpm-lock.yaml` を読むスキャナーや SBOM ツールは2ドキュメント形式に対応しているか確認する。
  - ページにバージョン番号の記載はない。
- 二次情報（要検証）[取得済]
  - Shai-Hulud（2025年9月）は npm の lifecycle scripts を悪用して拡散し、2025年11月の 2.0 では約796パッケージが侵害されたと報じられている。
  - pnpm 11.0（2026年4月とされる）で minimumReleaseAge=1440 が既定になったという報道がある。
  - pnpm 10.0.0–10.25 に lockfile integrity bypass の CVE（CVE-2025-69263/69264）があるとされる。
  - 出典: [Snyk](https://snyk.io/pt-BR/articles/npm-security-best-practices-shai-hulud-attack/), [lilting.ch](https://lilting.ch/en/articles/pnpm-11-minimum-release-age-default-shai-hulud-defense), [mondoo](https://mondoo.com/blog/npm-supply-chain-security-package-manager-defenses-2026)
  - 検索結果の要約によると、これらの出典は、release-age による待機は数時間〜数日で削除されるバージョンしか防げず、長期潜伏型の侵害には効かないと指摘している。

#### チェックリスト (C)

**C-1 依存関係（Gemfile / package.json / lockfile）**

| # | 観点 | 重大度 | 判定 | 出典 |
|---|---|---|---|---|
| C1 | 追加した依存は本当に必要か（標準ライブラリ、Rails や ActiveSupport の機能、既存の依存で代替できないか）。同じ用途の依存が重複していないか | should | 文脈 | 一般的慣行; [OpenSSF Scorecard](https://github.com/ossf/scorecard/blob/main/docs/checks.md) [既知] |
| C2 | メンテナンス状況（最終リリース、メンテナ数、未対応の issue、archive されていないか）、ダウンロード数、OpenSSF Scorecard、既知の脆弱性を確認したか | should | 文脈（外部情報） | [OpenSSF Scorecard](https://securityscorecards.dev/) [既知]; [GitHub dependency-review-action](https://docs.github.com/en/actions/reference/security/secure-use) |
| C3 | ライセンスがプロジェクトのポリシーと両立する（GPL/AGPL 系、ライセンス不明、ライセンス変更など） | must（商用・配布物の場合） | 文脈 | dependency review（ライセンス検査機能）[既知] |
| C4 | manifest と lockfile が整合している（Gemfile を変えたのに Gemfile.lock がない、package.json と lockfile がずれている、複数のパッケージマネージャーの lockfile が混在している）。CI で `bundle install --frozen` / `npm ci` / `pnpm install --frozen-lockfile` を使っている | must | 差分 | [pnpm Supply chain security](https://pnpm.io/supply-chain-security)（lockfile をコミットする） |
| C5 | lockfile の差分が manifest の変更に見合っている（意図しない大量の推移依存の更新、レジストリ URL や `resolved` の変更、git や tarball 由来の依存の追加がない） | must | 差分 | [pnpm Supply chain security](https://pnpm.io/supply-chain-security)（blockExoticSubdeps, namedRegistries） |
| C6 | install scripts（postinstall 等）を持つ依存を追加・更新していないか。`allowBuilds` / `onlyBuiltDependencies` を不必要に広げていないか | must | 差分 | [pnpm Supply chain security](https://pnpm.io/supply-chain-security); [Snyk (Shai-Hulud)](https://snyk.io/pt-BR/articles/npm-security-best-practices-shai-hulud-attack/) |
| C7 | 公開直後のバージョンを採用していないか（minimumReleaseAge・cooldown の設定を緩めていないか） | should | 差分 | [pnpm Supply chain security](https://pnpm.io/supply-chain-security); [lilting.ch](https://lilting.ch/en/articles/pnpm-11-minimum-release-age-default-shai-hulud-defense)（二次情報） |
| C8 | バージョン指定方針に合っている（アプリなら lockfile で固定。`*`、`latest`、`>=` だけの指定は避ける。Gemfile の pessimistic constraint `~>` の使い方） | should | 差分 | 一般的慣行; [Bundler docs: Gemfile](https://bundler.io/guides/gemfile.html) [既知] |
| C9 | メジャーアップデートで CHANGELOG / release notes / 移行ガイドを読み、破壊的変更への対応（コード修正、設定変更、Rails なら `new_framework_defaults` や `load_defaults`）が PR に含まれている | must | 文脈 | [Rails Upgrading Guide](https://guides.rubyonrails.org/upgrading_ruby_on_rails.html) [既知] |
| C10 | Gemfile.lock の `PLATFORMS`（例: `x86_64-linux` が CI・本番用に入っているか）と `BUNDLED WITH`、`.ruby-version` / `.node-version` / `engines` / `packageManager` が環境間で一致している | should | 差分 | 一般的慣行（Bundler の `bundle lock --add-platform`）[既知] |
| C11 | Renovate / Dependabot の PR では、CI が緑か、release notes、変更の大きさ（patch/minor/major）、自動マージ対象の範囲（devDependencies の patch のみ等）、まとめて上げた更新の分割、lockfile maintenance の差分の妥当性を見る | should | 差分＋文脈 | [Renovate config options](https://docs.renovatebot.com/configuration-options/)（minimumReleaseAge / lockFileMaintenance 等の項目の存在のみ確認）; [GitHub Dependabot](https://docs.github.com/en/actions/reference/security/secure-use) |

**C-2 GitHub Actions ワークフロー**

| # | 観点 | 重大度 | 判定 | 出典 |
|---|---|---|---|---|
| C12 | サードパーティアクションをフル commit SHA でピンしている（コメントにバージョンを書く）。workflow dependency lockfile が使えるなら採用する。SHA が本家リポジトリのものか | must（サードパーティ）/ should（GitHub公式 actions/*） | 差分 | [GitHub secure use](https://docs.github.com/en/actions/reference/security/secure-use) |
| C13 | `permissions:` をトップレベルで最小（`contents: read` か `{}`）にし、必要なジョブだけで書き込み権限を付けている。`write-all` を使っていない | must | 差分 | [GitHub secure use](https://docs.github.com/en/actions/reference/security/secure-use) |
| C14 | `run:` や `actions/github-script` の `script:` に `${{ github.event.issue.title }}`、`...pull_request.body`、`...head_ref`、`...comment.body` などの未信頼入力を直接展開していない（`env:` 経由で `"$VAR"` として渡す） | must | 差分 | [GitHub secure use](https://docs.github.com/en/actions/reference/security/secure-use) |
| C15 | `pull_request_target` / `workflow_run` を使う場合、PR の head を checkout してビルドやスクリプト実行をしていない。secret や書き込みトークンが未信頼コードに渡らない。artifact は未信頼データとして扱う | must | 差分 | [GitHub secure use](https://docs.github.com/en/actions/reference/security/secure-use); [GitHub Security Lab: Preventing pwn requests](https://securitylab.github.com/resources/github-actions-preventing-pwn-requests/) [既知] |
| C16 | secret をログに出していない（`echo`、`set -x`、デバッグ出力）。JSON 等の構造化 secret がない。派生値もマスクしている。fork PR に secret が渡る設定になっていない | must | 差分 | [GitHub secure use](https://docs.github.com/en/actions/reference/security/secure-use) |
| C17 | クラウドへのデプロイが長期キーではなく OIDC を使い、本番デプロイは environment の required reviewers で保護されている | should | 差分＋文脈 | [GitHub secure use](https://docs.github.com/en/actions/reference/security/secure-use) |
| C18 | public リポジトリで self-hosted runner を使っていない（使う場合はエフェメラル／JIT） | must | 差分 | [GitHub secure use](https://docs.github.com/en/actions/reference/security/secure-use) |
| C19 | `.github/workflows` が CODEOWNERS の対象で、ワークフロー変更にセキュリティ担当者のレビューが入る | should | 文脈 | [GitHub secure use](https://docs.github.com/en/actions/reference/security/secure-use) |
| C20 | 静的解析を通している（actionlint、zizmor、OpenSSF Scorecard、CodeQL の Actions 解析）。必要なら StepSecurity Harden-Runner で egress を監視する | nit〜should | 差分＋文脈 | [GitHub secure use](https://docs.github.com/en/actions/reference/security/secure-use)（code scanning・Scorecard）; [zizmor](https://github.com/zizmorcore/zizmor) [既知]; [StepSecurity harden-runner](https://github.com/step-security/harden-runner) [既知] |
| C21 | CI の変更がテストを弱めていない（`continue-on-error: true`、テストの除外、`if: false`、必須チェックからの除外、カバレッジ閾値の引き下げ）。その理由が PR に書かれている | must | 差分 | 一般的慣行 |
| C22 | キャッシュキーに lockfile のハッシュを含めている。`concurrency` で重複実行をキャンセルしている。`timeout-minutes` を設定している。matrix の Ruby/Node バージョンが `.ruby-version` などと一致している | nit〜should | 差分 | 一般的慣行 |

**C-3 Dockerfile / コンテナ**

| # | 観点 | 重大度 | 判定 | 出典 |
|---|---|---|---|---|
| C23 | ベースイメージが信頼できる最小のもので、タグだけでなく digest でもピンしている（`ruby:3.x-slim@sha256:...`） | should | 差分 | [Docker best practices](https://docs.docker.com/build/building/best-practices/) |
| C24 | multi-stage ビルドで、ビルドツール（build-essential、node_modules の dev 依存、`.git`）が最終イメージに残っていない | should | 差分 | [Docker best practices](https://docs.docker.com/build/building/best-practices/) |
| C25 | `USER` で非 root 実行している | must（本番イメージ） | 差分 | [Docker best practices](https://docs.docker.com/build/building/best-practices/) |
| C26 | 秘密情報（`RAILS_MASTER_KEY`、トークン）を `ARG` / `ENV` / `COPY` でイメージに焼き込んでいない（BuildKit の `--mount=type=secret` を使う）。`.dockerignore` で `.env`、`config/master.key`、`log/`、`tmp/`、`node_modules` を除外している | must | 差分 | [Docker best practices](https://docs.docker.com/build/building/best-practices/)（.dockerignore）; [Docker build secrets](https://docs.docker.com/build/building/secrets/) [既知] |
| C27 | `apt-get update && apt-get install --no-install-recommends` を同じ RUN に書き、キャッシュを削除している。パイプには `set -o pipefail` を付けている。COPY を ADD より優先している。キャッシュが効く順序（Gemfile/package.json を先に COPY）になっている | should / nit | 差分 | [Docker best practices](https://docs.docker.com/build/building/best-practices/) |

**C-4 Rails 環境設定・credentials・フィーチャーフラグ**

| # | 観点 | 重大度 | 判定 | 出典 |
|---|---|---|---|---|
| C28 | `config/master.key`、`config/credentials/*.key`、`.env` がコミットされていない。平文の秘密が `config/*.yml` や `database.yml` に書かれていない（ENV か credentials を使う） | must | 差分 | [Rails Security Guide: Custom Credentials](https://guides.rubyonrails.org/security.html#custom-credentials) [既知] |
| C29 | `config/environments/{development,test,production}.rb` の差分が意図どおりで、本番だけ異なる設定がレビューされている（`force_ssl`、`config.hosts`、ログレベル、`eager_load`、キャッシュストア、`action_mailer` の配信設定、`active_storage.service`） | should | 差分＋文脈 | [Rails Configuring Guide](https://guides.rubyonrails.org/configuring.html) [既知] |
| C30 | 新しい ENV 変数や設定キーについて、全環境（ステージング・本番・CI・ローカルの `.env.example`）への追加と、未設定時の挙動（`fetch` で早期失敗するか、デフォルト値で動くか）が明記されている | must | 文脈 | 一般的慣行 |
| C31 | フィーチャーフラグの既定値が安全側（OFF）で、ON と OFF の両方の経路にテストがある。削除予定（期限・担当）が決まっている。フラグ削除PRでは死んだ分岐をすべて取り除いている | should | 差分＋文脈 | 一般的慣行（直接の出典は Gaps 参照） |
| C32 | 設定変更が後方互換で段階的にロールアウトできる（デプロイ順序、ロールバック時の挙動）。Rails の `new_framework_defaults_*.rb` を一度に全部有効にしていない | should | 文脈 | [Rails Upgrading Guide](https://guides.rubyonrails.org/upgrading_ruby_on_rails.html) [既知] |

### Inferences
- Actions の C12–C16 と Docker の C25・C26 は diff だけで判定でき、actionlint、zizmor、hadolint で大部分を自動化できる。人手のレビューは「必要性・影響範囲・環境間の差分」（C1, C9, C29, C30）に集中させるのが効率的だろう。
- 2025年の npm サプライチェーン攻撃以降、lockfile diff のレビュー（C5, C6）は「機械が生成した差分だから読まない」では済まない項目になった。Renovate/Dependabot の PR でも、install scripts を持つ依存の更新と lockfile の大量変更には人の目が必要と考えられる。
- GitHub 公式ドキュメントに workflow dependency lockfile が「SHA ピンより強い」と書かれた。このため C12 の推奨は今後「SHA ピン → lockfile」に移る可能性がある（提供範囲は要確認）。

### Gaps
- Renovate のドキュメントは非常に長く（35万字超）、`minimumReleaseAge`、`pinDigests`、`rangeStrategy`、`config:best-practices` の具体的な記述と既定値は取得範囲に含まれず、未検証。
- Dependabot の `cooldown` オプション（公開後の待機日数）は2025年に追加されたと記憶しているが、今回は検証していない。
- GitHub の workflow dependency lockfile の正式名称、提供開始日、GA 状況は未確認（secure-use ページの記述のみ）。
- pnpm 11 で minimumReleaseAge が既定化された時期（2026年4月）と、pnpm の CVE 番号は二次情報のみ。公式リリースノートでは確認していない。
- Docker の build secrets と HEALTHCHECK、Rails の credentials と設定ガイド、OpenSSF Scorecard のチェック一覧、GitHub Security Lab の pwn request 記事、zizmor、StepSecurity は今回取得していない（[既知]）。
- フィーチャーフラグのレビュー観点（C31）について、権威ある単一の出典は見つけていない（Martin Fowler の「Feature Toggles」(https://martinfowler.com/articles/feature-toggles.html) が候補だが未取得）。
