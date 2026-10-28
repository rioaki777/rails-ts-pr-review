# Rails アプリケーションコードの PR レビュー観点（models / controllers / views / routes / services / concerns / jobs / mailers / caching / config / Ruby イディオム）

前提: 2026-10-28 時点、対象は Rails 7.1+ / 8.x と Ruby 3.3+。DB マイグレーション、セキュリティ、テストは他の調査担当の範囲なので、ここでは Rails 固有で重要なものだけ短く触れる。

凡例
- 重要度: **must** = マージ前に必ず直す / **should** = 原則直す（理由があれば許容） / **nit** = 好み・軽微
- 判定: **[diff]** = diff だけで判断できる / **[ctx]** = リポジトリの文脈（スキーマ、呼び出し元、設定、データ量）が必要
- 「(既知仕様・本セッション未取得)」と付けたソースは、URL は正しいが今回のセッションでは本文を取得していない。いずれも長く安定している Rails の仕様。

---

## Q1. レビュアーが拾うべき Rails 固有の不具合・アンチパターンは何か

### Takeaway
Rails の不具合は「暗黙の挙動」に集中する。たとえば、コールバックやバリデーションを飛ばす一括操作、トランザクションの境界とジョブ投入タイミングのずれ、ループ内の遅延ロード（N+1）、`find_by` の nil、タイムゾーン、ジョブのリトライと冪等性、`default_scope` や enum の暗黙の変化。どれも diff 上は正しく見えるため、リンターより人間のレビューで拾う価値が高い。

### Cited Findings

#### A. モデル（Active Record）: コールバック・永続化
- [must][diff] **`update_all` / `delete_all` / `update_column(s)` / `insert_all` / `upsert_all` / `touch_all` / `increment!` / `update_counters` などはコールバックを飛ばす**。監査ログ、検索インデックス、キャッシュ無効化、`counter_cache` の更新などをコールバックに頼っている場合、データ不整合になる。公式ガイドが列挙する skip 対象は `decrement!`, `decrement_counter`, `delete`, `delete_all`, `delete_by`, `increment!`, `increment_counter`, `insert`, `insert!`, `insert_all`, `insert_all!`, `touch_all`, `update_column`, `update_columns`, `update_all`, `update_counters`, `upsert`, `upsert_all` — [Rails Guides: Active Record Callbacks](https://guides.rubyonrails.org/active_record_callbacks.html)。rubocop-rails の `Rails/SkipsModelValidations` でも検出できるが、意図的な使用かどうかは人間が判断する — [rubocop-rails cops](https://docs.rubocop.org/rubocop-rails/latest/cops_rails.html)
- [should][ctx] **コールバックは「主責務ではない、単純で直交した副作用」に限定する**。37signals は callbacks や `Current` を禁止しない立場だが、「you don't want to orchestrate complex flows using callbacks」「You can put yourself in a deep hole if you misuse or abuse them」と書いている。監査ログのように本筋と直交する処理には向き、複雑なフローや中核のドメイン処理には向かない — [37signals: Globals, callbacks and other sacrileges](https://dev.37signals.com/globals-callbacks-and-other-sacrileges/)
- [must][diff] **外部システム呼び出し（API、メール、ジョブ投入、検索インデックス）は `after_save` ではなく `after_commit` 系で行う**。`after_commit` は「models need to interact with external systems that are not part of the database transaction」ためのもの — [Callbacks guide](https://guides.rubyonrails.org/active_record_callbacks.html)
- [should][diff] **`after_commit` の注意点**:
  - (1) 同じメソッド名で `after_create_commit` と `after_update_commit` を両方定義すると、最後の定義しか効かない（「it will only allow the last callback defined to take effect」）。`after_save_commit` を使う。
  - (2) `after_commit` 内の例外は伝播し、残りの `after_commit` は実行されない。ただしデータはすでに永続化済み。
  - (3) `after_commit` 内はトランザクションの外。
  - (4) 同じトランザクションで同じレコードを複数のオブジェクトとして変更した場合、発火するのは最初のオブジェクトだけ。

  以上 [Callbacks guide](https://guides.rubyonrails.org/active_record_callbacks.html)。(1) は `Rails/AfterCommitOverride` でも検出できる — [rubocop-rails](https://docs.rubocop.org/rubocop-rails/latest/cops_rails.html)
- [must][diff] **コールバックを止めるには `throw :abort` を使う**（`false` を返しても止まらない）。`create!` は `RecordNotSaved`、`destroy!` は `RecordNotDestroyed` を raise する — [Callbacks guide](https://guides.rubyonrails.org/active_record_callbacks.html)
- [should][diff] **`before_destroy` で削除可否を検証する場合は、`dependent: :destroy` の関連より前に宣言するか `prepend: true` を付ける**。そうしないと関連レコードが先に削除される — [Callbacks guide](https://guides.rubyonrails.org/active_record_callbacks.html); [Rails Style Guide](https://rails.rubystyle.guide/)
- [should][diff] **コールバック内で `update` / `save` などの副作用を起こさない**（「Refrain from using methods like `update`, `save`…」） — [Callbacks guide](https://guides.rubyonrails.org/active_record_callbacks.html)
- [should][diff] **`Model.suppress` は複雑さと予期しない挙動を招く**（ガイドに明記） — [Callbacks guide](https://guides.rubyonrails.org/active_record_callbacks.html)
- [should][diff] コールバックは実行順に並べる（`Rails/ActiveRecordCallbacksOrder`）。Active Record の組み込みメソッドを override せず、コールバックを使う（`Rails/ActiveRecordOverride`） — [rubocop-rails](https://docs.rubocop.org/rubocop-rails/latest/cops_rails.html)

#### B. モデル: 関連・スコープ・enum・属性
- [should][ctx] **`has_many` / `has_one` には `dependent:` を明示する**（`Rails/HasManyOrHasOneDependent`）。大量の子レコードに `dependent: :destroy` を付けると 1 件ずつ destroy されて遅い。`:delete_all` にするとコールバックが走らない。どちらを選ぶかはデータ量とコールバックの有無次第 — [rubocop-rails](https://docs.rubocop.org/rubocop-rails/latest/cops_rails.html)
- [nit][diff] 推論できない関連（`foreign_key:` や scope 付き）には `inverse_of:` を付ける（`Rails/InverseOf`） — [rubocop-rails](https://docs.rubocop.org/rubocop-rails/latest/cops_rails.html)
- [should][ctx] **`default_scope` を新しく追加しない**。全クエリ、関連、`new` の初期値に暗黙に効き、`unscoped` で他の条件まで外れてしまう。rubocop-rails の `Rails/DefaultScope` はデフォルト無効なので、レビューで止める必要がある — [rubocop-rails](https://docs.rubocop.org/rubocop-rails/latest/cops_rails.html)
- [must][diff] **enum はハッシュ構文で整数値（または文字列値）を明示する**。配列構文では途中に値を挿入すると既存データの意味がずれる — [Rails Style Guide](https://rails.rubystyle.guide/)
  - **キーワード引数形式の enum 定義（`enum status: {...}`）は Rails 8.0 で削除された**。`enum :status, {...}` の位置引数形式を使う（`Rails/EnumSyntax`） — [Rails 8.0 release notes](https://guides.rubyonrails.org/8_0_release_notes.html); [rubocop-rails](https://docs.rubocop.org/rubocop-rails/latest/cops_rails.html)
  - 値の重複は `Rails/EnumUniqueness` で検出できる。enum に `validate: true` オプションを付けると、不正値の代入が `ArgumentError` ではなくバリデーションエラーになる（Rails 7.1） — [Rails 7.1 release notes](https://guides.rubyonrails.org/7_1_release_notes.html)
  - [must][ctx] 既存 enum の値の変更・削除・並べ替えは既存データの意味を変える。データ移行が必要（DB 側の話は migration 担当へ）。
- [should][diff] **入力の正規化は `before_validation` の自前実装ではなく `normalizes`（7.1+）を使う**。`normalizes` は `where` / `find_by` / `exists?` のキーワード引数にも適用されるが、**生 SQL 文字列には適用されない**。また既存レコードは再保存するまで正規化されないので、既存データの移行が必要か確認する — [Rails 7.1 release notes](https://guides.rubyonrails.org/7_1_release_notes.html)
- [should][diff] パスワードリセットやメール確認のトークンは、自前生成ではなく `generates_token_for` / `find_by_token_for` を使う（埋め込んだデータが変わると自動で無効化される）。ログインには `authenticate_by` を使う（タイミング攻撃対策。詳細はセキュリティ担当へ） — [Rails 7.1 release notes](https://guides.rubyonrails.org/7_1_release_notes.html)
- [should][diff] **`attr_readonly` の属性への代入は、7.1 の defaults 以降 raise する**（`raise_on_assign_to_attr_readonly = true`）。以前は代入しても黙って保存されなかった — [Configuring Rails](https://guides.rubyonrails.org/configuring.html)
- [should][diff] **`order` を付けずに `first` / `last` を呼ばない**。Rails 8.1 では順序依存の finder（`order` なしの `#first`）が deprecated になり、`load_defaults 8.1` で `raise_on_missing_required_finder_order_columns = true` になる — [Rails 8.1 release notes](https://guides.rubyonrails.org/8_1_release_notes.html); [Configuring Rails](https://guides.rubyonrails.org/configuring.html)
- [should][ctx] 関連を廃止するときは、いきなり削除せず `has_many :foo, deprecated: true`（8.1）で使用箇所を洗い出す（モード: `:warn` / `:raise` / `:notify`） — [Rails 8.1 release notes](https://guides.rubyonrails.org/8_1_release_notes.html)
- [should][ctx] 一意性バリデーション `validates :x, uniqueness: true` は DB の一意インデックスがないと競合状態で破れる（`Rails/UniqueValidationWithoutIndex`。schema.rb を参照するので [ctx]） — [rubocop-rails](https://docs.rubocop.org/rubocop-rails/latest/cops_rails.html)
- [nit][diff] `belongs_to` は（`load_defaults` 5.0 以降）デフォルトで required なので、`validates :user, presence: true` は冗長（`Rails/RedundantPresenceValidationOnBelongsTo`） — [rubocop-rails](https://docs.rubocop.org/rubocop-rails/latest/cops_rails.html)
- [should][diff] `errors` をハッシュのように直接操作しない（`errors[:x] << ...` は不可。`errors.add` を使う。`Rails/DeprecatedActiveModelErrorsMethods`） — [rubocop-rails](https://docs.rubocop.org/rubocop-rails/latest/cops_rails.html)

#### C. クエリ・nil 処理・性能
- [must][diff] **ループ内で関連にアクセスすると N+1 になる**。`includes` / `preload` / `eager_load` で事前ロードしているか確認する。ビュー、シリアライザ、ジョブも対象。Bullet は関連の遅延ロードを追跡する。Prosopite は同じコールスタックから同じ形の SQL が繰り返し発行されるのを検出するため、Bullet が見逃す `Model.find(x.foo_id)`、コレクション関連への `first` / `last` / `pluck`、レコード作成直後のクエリなども拾う。COUNT の N+1 には counter cache を提案する — [Prosopite README](https://github.com/charkost/prosopite)
- [should][ctx] **`strict_loading`** を使うと遅延ロード時に raise させられる。グローバル設定は `config.active_record.strict_loading_by_default`（デフォルト false）、`strict_loading_mode = :n_plus_one_only`、`action_on_strict_loading_violation`（`:raise` / `:log`）。ただし strict_loading は「遅延ロードを伴わない N+1」（`find` を繰り返すなど）は拾えない — [Configuring Rails](https://guides.rubyonrails.org/configuring.html); [Prosopite README](https://github.com/charkost/prosopite)
- [should][ctx] **1 リクエスト / 1 ジョブあたりのクエリ数に上限を設ける考え方**。GitLab は各コントローラ、API エンドポイント、Sidekiq ワーカーのクエリを 100 本までとし、テスト環境では超えると raise する。新しいエンドポイントには例外を認めない — [GitLab: Query count limits](https://docs.gitlab.com/development/database/query_count_limits/)
- [must][diff] **件数が無制限になりうるレコードを `all.each` / `.map` でメモリに載せない**。`find_each` / `in_batches` を使う（`Rails/FindEach`）。一覧系の API や画面にはページネーションがあるか確認する（大きいテーブルの offset ページネーションは遅いので、GitLab にもキーセット系のガイドがある） — [Rails Style Guide](https://rails.rubystyle.guide/); [rubocop-rails](https://docs.rubocop.org/rubocop-rails/latest/cops_rails.html); [GitLab: Query count limits の関連ページ](https://docs.gitlab.com/development/database/query_count_limits/)
- [should][diff] 1 カラムだけ必要なら `pluck`、1 件の 1 値なら `pick`、ID なら `ids` を使う。`map(&:name)` でモデルを丸ごと生成しない — [Rails Style Guide](https://rails.rubystyle.guide/)
- [should][diff] `size` / `count` / `length` を使い分ける。Style Guide は `size` を推奨している。`count` は常に SQL を発行し、`length` は全件ロードする。存在確認は `exists?`（`Rails/WhereExists` など） — [Rails Style Guide](https://rails.rubystyle.guide/)
- [must][diff] **`find_by` は nil を返す**ので、呼び出し側で nil を考慮しているか確認する。`find` / `find_by!` は `RecordNotFound` を raise する（コントローラでは 404 になる）。**`find_by` の結果を `@x ||= find_by(...)` でメモ化しない**（nil のとき毎回クエリが走る。`defined?` を使う。`Rails/FindByOrAssignmentMemoization`） — [Rails Style Guide](https://rails.rubystyle.guide/); [rubocop-rails](https://docs.rubocop.org/rubocop-rails/latest/cops_rails.html)
- [nit][diff] `where(...).take` より `find_by`、`find_by_name` のような動的 finder より `find_by(name:)`（`Rails/FindBy`, `Rails/DynamicFindBy`） — [rubocop-rails](https://docs.rubocop.org/rubocop-rails/latest/cops_rails.html)
- [should][diff] `save` / `update` の戻り値（false）を無視しない。失敗を想定しない場所では `save!` を使う（`Rails/SaveBang` はデフォルト無効なので、レビューで見る） — [rubocop-rails](https://docs.rubocop.org/rubocop-rails/latest/cops_rails.html)
- [should][diff] 7.1+ の async クエリ（`load_async`, `async_count`, `async_pluck` など）は `ActiveRecord::Promise` を返すので `.value` が必要。コネクションプールのサイズと、意味のある並列性があるかも確認する — [Rails 7.1 release notes](https://guides.rubyonrails.org/7_1_release_notes.html)
- [should][diff] 8.1 では、関連に未保存レコードを持つ状態での `insert_all` / `upsert_all`、および `WITH` / `DISTINCT` と組み合わせた `update_all` が deprecated — [Rails 8.1 release notes](https://guides.rubyonrails.org/8_1_release_notes.html)
- [nit][diff] 生 SQL ヒアドキュメントは `<<~SQL.squish` で書く — [Rails Style Guide](https://rails.rubystyle.guide/)

#### D. トランザクション
- [must][diff] **トランザクション内でジョブを投入したりメールを送ったり外部 API を呼んだりしない**。ロールバックされても副作用が残る。commit 前にジョブが走ってレコードが見えない、という問題も起きる。対策は以下のいずれか。
  - (a) `after_commit` を使う。
  - (b) Rails 7.2+ の `ActiveRecord::Base.transaction do |tx| tx.after_commit { ... } end` や `ActiveRecord.after_all_transactions_commit { ... }` を使う。
  - (c) ジョブに `enqueue_after_transaction_commit` を設定する。

  — [Rails 7.2 release notes](https://guides.rubyonrails.org/7_2_release_notes.html)
- [should][diff] トランザクションブロック内で `return` / `break` / `throw` を使わない。7.2 でこの扱いが確定し、ブロックを抜けると commit される（ロールバックではない）。意図せず commit されないか確認する（`Rails/TransactionExitStatement`） — [Rails 7.2 release notes](https://guides.rubyonrails.org/7_2_release_notes.html); [rubocop-rails](https://docs.rubocop.org/rubocop-rails/latest/cops_rails.html)
- [should][ctx] トランザクションを長く保持しない（ループ処理全体を 1 トランザクションで包む、トランザクション内で外部 I/O を待つ、など）。ロックの保持とレプリカ遅延の原因になる。（一般原則。本セッションで一次ソースは取得していない）

#### E. コントローラ・ルーティング
- [should][ctx] **コントローラは薄く保つ**。ビジネスロジックはモデルや PORO に置き、各アクションは最初の `find` / `new` の後にメソッドを 1 つ呼ぶ程度にする。ビューに渡すインスタンス変数は最小限にする — [Rails Style Guide](https://rails.rubystyle.guide/)
- [should][diff] **Strong Parameters は Rails 8.0+ では `params.expect(post: [:title, :body])` を推奨**（`require.permit` より安全で、不正な形のパラメータには 500 ではなく 400 を返す。`Rails/StrongParametersExpect`）。`permit!` は must 指摘（詳細はセキュリティ担当） — [Rails 8.0 release notes](https://guides.rubyonrails.org/8_0_release_notes.html); [rubocop-rails](https://docs.rubocop.org/rubocop-rails/latest/cops_rails.html)
- [should][diff] `before_action only: [...]` に、そのクラスに存在しないアクションを指定しない（`Rails/LexicallyScopedActionFilter`）。`flash` は `render` の前ではなく、`flash.now` かリダイレクトと組み合わせて使う（`Rails/ActionControllerFlashBeforeRender`） — [rubocop-rails](https://docs.rubocop.org/rubocop-rails/latest/cops_rails.html)
- [nit][diff] ステータスは数値ではなくシンボル（`:unprocessable_entity` など）で書き、`render plain:` を使う — [Rails Style Guide](https://rails.rubystyle.guide/)
- [should][diff] Rails 7.2+ の `allow_browser versions: :modern` は新規アプリの `ApplicationController` に入っている。API クライアントや古いブラウザを使うユーザーに 406 を返していないか確認する — [Rails 7.2 release notes](https://guides.rubyonrails.org/7_2_release_notes.html)
- [should][diff] 1 つのルートを複数のパスに割り当てる書き方は 8.0 で deprecated、8.1 で削除。`;` をクエリ文字列の区切りに使う挙動や、パラメータ名の先頭の `[` を読み飛ばす挙動も 8.1 で削除された — [Rails 8.0 release notes](https://guides.rubyonrails.org/8_0_release_notes.html); [Rails 8.1 release notes](https://guides.rubyonrails.org/8_1_release_notes.html)
- [should][diff] 8.1 の defaults では、パス相対のリダイレクトは `action_on_path_relative_redirect = :raise` になる — [Configuring Rails](https://guides.rubyonrails.org/configuring.html)

#### F. ビュー・ヘルパー
- [must][diff] ビュー、ヘルパー、パーシャル内のクエリやループ内の関連アクセスは N+1 の主な発生源。コレクションの描画には `render partial:, collection:` を使う（上記 C を参照）
- [should][diff] ヘルパーはインスタンス変数に依存せず、引数で受け取る（`Rails/HelperInstanceVariable`） — [rubocop-rails](https://docs.rubocop.org/rubocop-rails/latest/cops_rails.html)
- [must][diff] `html_safe` / `raw` の使用はセキュリティ担当の範囲だが、diff で見つけたら必ず指摘する（`Rails/OutputSafety`）
- [nit][diff] 文字列リテラルはロケールファイルに置く（`Rails/I18nLocaleTexts`）。`form_with model: nil` は 8.0 で削除された — [Rails 8.0 release notes](https://guides.rubyonrails.org/8_0_release_notes.html)

#### G. バックグラウンドジョブ（Active Job / Solid Queue / Sidekiq）
- [must][ctx] **ジョブは冪等にする**。GitLab の定義は「It can safely run multiple times with the same arguments」で、副作用が 1 回だけ起きるか、2 回目に実行しても影響がないこと。リトライ前提の設計にし、`idempotent!` を宣言して共有テストで検証している。重複排除の戦略（`until_executing` / `until_executed`）と TTL（デフォルト 10 分）も定めている — [GitLab: Sidekiq idempotent jobs](https://docs.gitlab.com/development/sidekiq/idempotent_jobs/)
- [must][diff] **Active Job の失敗はデフォルトではリトライされない**（「A failed job will not be retried, unless configured otherwise」）。Solid Queue では `retry_on` がないと即座に failed executions に入る。`retry_on`（デフォルトは 3 秒待機・5 回）と `discard_on` が適切に設定されているか確認する。Sidekiq ネイティブのワーカーはデフォルトでリトライするので、この違いに注意 — [Active Job Basics](https://guides.rubyonrails.org/active_job_basics.html)
- [should][diff] **引数に AR オブジェクトを渡すと GlobalID でシリアライズされる**。実行前にレコードが削除されると `ActiveJob::DeserializationError` になるので、`discard_on ActiveJob::DeserializationError` などの扱いを決めておく — [Active Job Basics](https://guides.rubyonrails.org/active_job_basics.html)
- [must][ctx] **ジョブ投入とトランザクション commit の順序**。Solid Queue がアプリと同じ DB を共有していれば、投入は同じトランザクションに含まれる。2026 年現在のガイドでは `enqueue_after_transaction_commit` は**デフォルト無効**で、`ApplicationJob` で `self.enqueue_after_transaction_commit = true` として有効にする。
  - 経緯: 7.2 で導入（`:never` / `:always` / `:default` の値）→ 8.0 でグローバル設定 `config.active_job.enqueue_after_transaction_commit` が deprecated → 8.1 でシンボル値とグローバル設定が削除。
  - 7.2 時点の記事にある「デフォルトで commit 後に投入される」という記述は古い。

  — [Active Job Basics](https://guides.rubyonrails.org/active_job_basics.html); [Rails 7.2 release notes](https://guides.rubyonrails.org/7_2_release_notes.html); [Rails 8.0 release notes](https://guides.rubyonrails.org/8_0_release_notes.html); [Rails 8.1 release notes](https://guides.rubyonrails.org/8_1_release_notes.html)
- [should][diff] `perform_all_later`（7.1+）は enqueue コールバック（`around_enqueue` など）を実行せず、`enqueue_all.active_job` を通知する（計測のサブスクライバが見逃す可能性がある）。戻り値は nil。Solid Queue の `limits_concurrency` とは併用できない — [Rails 7.1 release notes](https://guides.rubyonrails.org/7_1_release_notes.html); [Active Job Basics](https://guides.rubyonrails.org/active_job_basics.html)
- [should][diff] Solid Queue の `limits_concurrency`（`to:`, `key:`, `duration:`, `on_conflict:`）にはオーバーヘッドがあり、ガイドは「should be used sparingly」としている。定期実行は `config/recurring.yml` に書く — [Active Job Basics](https://guides.rubyonrails.org/active_job_basics.html)
- [should][diff] 長時間かかるジョブ（全件処理など）は 8.1 の `ActiveJob::Continuable`（`step`, `step.cursor`, `step.advance!`）で再開可能にし、デプロイや再起動で最初からやり直さないようにする — [Rails 8.1 release notes](https://guides.rubyonrails.org/8_1_release_notes.html); [Active Job Basics](https://guides.rubyonrails.org/active_job_basics.html)
- [should][ctx] Rails 組み込みの `sidekiq` アダプタは 8.1 で deprecated（sidekiq gem 側のアダプタに移行）。SuckerPunch アダプタは 8.1 で外部 gem に移った — [Rails 8.1 release notes](https://guides.rubyonrails.org/8_1_release_notes.html)
- [should][ctx] ジョブ内でも N+1 やクエリ数の上限は同じように問題になる（GitLab の 100 クエリ制限は Sidekiq ワーカーにも適用される。Prosopite には Sidekiq ミドルウェアがあり、Active Job では `around_perform` で検査できる） — [GitLab: Query count limits](https://docs.gitlab.com/development/database/query_count_limits/); [Prosopite README](https://github.com/charkost/prosopite)

#### H. メーラー
- [should][diff] メールはリクエスト中に同期送信せず、`deliver_later` でバックグラウンド送信する。トランザクション内なら commit 後に送る（D を参照） — [Rails Style Guide](https://rails.rubystyle.guide/); [Callbacks guide](https://guides.rubyonrails.org/active_record_callbacks.html)
- [nit][diff] HTML とテキストの両方のテンプレートを用意する。送信者は `email_address_with_name` で組み立てる。クラス名は `*Mailer`。`default_url_options` を環境ごとに設定する — [Rails Style Guide](https://rails.rubystyle.guide/)
- [should][diff] `deliver_later` に AR オブジェクトを渡すとジョブと同じく GlobalID を経由するので、削除やロールバックの影響を受ける — [Active Job Basics](https://guides.rubyonrails.org/active_job_basics.html)

#### I. 時刻・タイムゾーン
- [must][diff] **`Time.now` / `Date.today` を使わない**。`Time.current` / `Time.zone.now` / `Date.current` を使う（`Rails/TimeZone`, `Rails/Date`） — [Rails Style Guide](https://rails.rubystyle.guide/); [rubocop-rails](https://docs.rubocop.org/rubocop-rails/latest/cops_rails.html)
- [should][diff] `Time` と `TimeWithZone` の加算や `since` は 8.0 で deprecated、8.1 で削除。8.1 では `to_time` が常にレシーバのタイムゾーンを保持する（`to_time_preserves_timezone` 設定は deprecated） — [Rails 8.0 release notes](https://guides.rubyonrails.org/8_0_release_notes.html); [Rails 8.1 release notes](https://guides.rubyonrails.org/8_1_release_notes.html)
- [nit][diff] `Time.current + 1.day` ではなく `1.day.from_now` と書く（`Rails/DurationArithmetic`） — [rubocop-rails](https://docs.rubocop.org/rubocop-rails/latest/cops_rails.html)

#### J. 設定・環境・Ruby イディオム
- [should][diff] アプリコード中に `Rails.env.production?` の分岐を散らさず、設定値やフィーチャーフラグにする（`Rails/Env`、デフォルト無効）。`ENV` を直接参照せず、設定や credentials を経由する（`Rails/EnvironmentVariableAccess`、デフォルト無効）。`exit` / `abort` を使わない（`Rails/Exit`） — [rubocop-rails](https://docs.rubocop.org/rubocop-rails/latest/cops_rails.html)
- [must][diff] `Rails.application.secrets` は 7.2 で削除された。credentials を使う — [Rails 7.2 release notes](https://guides.rubyonrails.org/7_2_release_notes.html)
- [should][diff] フレームワークのクラスを直接パッチせず、`ActiveSupport.on_load` を使う（`Rails/ActiveSupportOnLoad`） — [rubocop-rails](https://docs.rubocop.org/rubocop-rails/latest/cops_rails.html)
- [should][diff] デバッグログで文字列を補間せず、ブロック形式 `logger.debug { ... }` にする（`Rails/EagerEvaluationLogMessage`） — [rubocop-rails](https://docs.rubocop.org/rubocop-rails/latest/cops_rails.html)
- [nit][diff] `try!` より `&.`、`starts_with?` より `start_with?`、`!include?` より `exclude?`、`to_formatted_s` より `to_fs` を使い、`inquiry` は避ける — [Rails Style Guide](https://rails.rubystyle.guide/)
- [should][diff] 8.1 で deprecated になったもの: `String#mb_chars`、`ActiveSupport::Configurable`、`ActiveRecord::Base.signed_id_verifier_secret`（`Rails.application.message_verifiers` などへ移行）。`Benchmark.ms` は 8.1 で削除（benchmark gem へ） — [Rails 8.1 release notes](https://guides.rubyonrails.org/8_1_release_notes.html)
- [should][diff] Gem: 開発・テスト用 gem は適切なグループに入れる。無名の gem はソースを確認してから入れる。Gemfile.lock をコミットする — [Rails Style Guide](https://rails.rubystyle.guide/)

#### K. Concerns / サービス / PORO / CurrentAttributes
- [should][ctx] 37signals 流の設計では、ドメインモデル（AR と PORO）が公開インターフェースを持ち、コントローラやジョブから直接呼ぶ。サービス層のような独立したオーケストレーション層は必須ではない（「vanilla Rails is plenty」）。concern は「直交する振る舞いのまとまり」（例: `Bucket::Eventable`）に使い、コードを機械的に分割するためだけには使わない — [37signals: Vanilla Rails is plenty](https://dev.37signals.com/vanilla-rails-is-plenty/); [37signals: Globals, callbacks and other sacrileges](https://dev.37signals.com/globals-callbacks-and-other-sacrileges/)
- [should][ctx] `Current`（`ActiveSupport::CurrentAttributes`）は、監査用の作成者のようなリクエストスコープの付随情報に限る。ジョブやコンソールからの実行では `Current` が空になる前提で設計する — [37signals: Globals, callbacks and other sacrileges](https://dev.37signals.com/globals-callbacks-and-other-sacrileges/)

#### L. キャッシュ
- [should][ctx] Rails 8 のデフォルトキャッシュストアは Solid Cache（DB ベースで、主にフラグメントキャッシュ向け）。Redis や Memcached とはレイテンシや容量の特性が違うので、低レイテンシが前提のキャッシュ用途やカウンタ用途で使われていないか確認する — [Rails 8.0 release notes](https://guides.rubyonrails.org/8_0_release_notes.html)
- [should][diff] フラグメントキャッシュのキーに、表示に影響する属性（ロケール、権限、関連の `updated_at`）が含まれているか確認する。子の更新が親のキャッシュを無効化するには `belongs_to ... touch: true` が必要。（一般原則。本セッションでは Caching guide を取得していない。参照先: https://guides.rubyonrails.org/caching_with_rails.html）
- [should][diff] Rails 8.0 の defaults では `action_dispatch.strict_freshness = true` になり、`If-None-Match` があるときは ETag だけで判定する（条件付き GET の挙動が変わる） — [Configuring Rails](https://guides.rubyonrails.org/configuring.html)

### Inferences
- 「diff だけで判断できる」項目（`Time.now`、`update_all`、トランザクション内のジョブ投入、enum の構文、`params.expect`、`find_by` のメモ化など）は、大半が rubocop-rails の cop と対応している。レビューで人間が見るべきなのは「意図的かどうか」（コールバックを飛ばすのは意図的か）と「データ量や文脈」（`dependent:` の選択、N+1 が実際に問題になる件数か、冪等性）。
- 最も重大な事故になりやすいのは、トランザクション、ジョブ、外部副作用の組み合わせ（ロールバック後の通知、commit 前にジョブが実行される、リトライでの二重課金）と、コールバックを飛ばす一括更新。重要度の must はここに集中させるのが妥当。
- `enqueue_after_transaction_commit` は 7.2 → 8.0 → 8.1 でデフォルトや設定方法が揺れた。レビュアーは「プロジェクトの `ApplicationJob` で明示的に有効になっているか」を [ctx] で確認すべきで、古いブログの記述を前提にしてはいけない。

### Gaps
- `rails.rubystyle.guide` の `default_scope` に関する記述は「宣言を先頭に置く」だけで、禁止の推奨は見つからなかった。`default_scope` を避ける根拠は rubocop の `Rails/DefaultScope` の存在と、広く知られた慣行による。
- Caching guide（russian doll、`touch: true`、キャッシュキー）は本セッションで取得していないため、L の 2 項目目は一般原則として扱った。
- トランザクションを長く保持しない、という原則の一次ソースは本セッションで取得していない。

---

## Q2. Rails 7.1 / 7.2 / 8.0 / 8.1 の変更でレビュアーが知っておくべきこと

### Takeaway
新しい API を使っているか（`normalizes`、`generates_token_for`、`params.expect`、`after_commit` 系の transaction API、Continuable）と、削除された API が残っていないか（キーワード引数形式の enum、`Rails.application.secrets`、`Time` 混在の演算、複数パスのルート）が、バージョンアップ後の PR で頻出する観点になる。Rails 8 では Solid Queue / Cache / Cable、Propshaft、Kamal 2、Thruster、認証ジェネレータがデフォルトになり、インフラの前提（Redis 不要、DB 負荷の増加）が変わった。

### Cited Findings
- **7.1**:
  - 新機能: `normalizes`、`generates_token_for` / `find_by_token_for`、`authenticate_by`、async クエリ（`async_count`, `async_sum`, `async_pluck`, `async_pick`, `async_ids` などが `ActiveRecord::Promise` を返す）、複合主キー（`query_constraints`）、`perform_all_later`（enqueue コールバックは実行されない）、enum の validate オプション。
  - 暗号化（`encrypts`）のデフォルトダイジェストが SHA1 から SHA256 に変わった。
  - deprecated: `Rails.application.secrets`、`show_exceptions` の true/false 指定（`:all` / `:rescuable` / `:none` を使う）。

  — [Rails 7.1 release notes](https://guides.rubyonrails.org/7_1_release_notes.html)
- **7.2**:
  - Ruby 3.1 以上が必須。
  - 新機能: `enqueue_after_transaction_commit`、`transaction` ブロックが `ActiveRecord::Transaction` を yield して `after_commit` を登録できる、`ActiveRecord.after_all_transactions_commit`、`allow_browser`。
  - トランザクションブロックを `return` / `break` / `throw` で抜けたときのロールバックは廃止（commit される）。
  - 削除: `Rails.application.secrets`、`ActionController::Parameters` と Hash の比較、`@rails/ujs`（Turbo へ）。
  - `load_defaults 7.2` で YJIT がデフォルト有効。

  — [Rails 7.2 release notes](https://guides.rubyonrails.org/7_2_release_notes.html); [Configuring Rails](https://guides.rubyonrails.org/configuring.html)
- **8.0**:
  - Kamal 2（Kamal Proxy が Traefik を置き換え）、Thruster、Solid Cable（メッセージ保持のデフォルトは 1 日）、Solid Cache、Solid Queue（`FOR UPDATE SKIP LOCKED`。PostgreSQL / MySQL 8.0+ / SQLite に対応）、Propshaft がデフォルトに、認証ジェネレータ。
  - 新機能: `params.expect`。
  - 削除: キーワード引数形式の enum、`ConnectionPool#connection`、`warn_on_records_fetched_greater_than`。
  - deprecated: `enqueue_after_transaction_commit`、`Benchmark.ms`、`Time` と `TimeWithZone` の演算。
  - `Regexp.timeout` のデフォルトが 1 秒になった（ReDoS 対策）。
  - 新しい DB で `db:migrate` を実行すると、先にスキーマをロードする。

  — [Rails 8.0 release notes](https://guides.rubyonrails.org/8_0_release_notes.html)
- **8.0 の Solid Queue**: ガイドは「Rails 8 configures Solid Queue on a separate database by default」で、それが「the safer choice」と説明している。この場合、ジョブ投入はアプリのトランザクションとは別になる — [Active Job Basics](https://guides.rubyonrails.org/active_job_basics.html)
- **8.1**（2025-10 リリース）:
  - 新機能: `ActiveJob::Continuable`、関連の `deprecated: true`、`Rails.event`（構造化イベント）、`format.md`（markdown レンダリング）。
  - deprecated: `order` なしの `#first`、`signed_id_verifier_secret`、関連に未保存レコードを持つ状態での `insert_all` / `upsert_all`、`WITH` / `DISTINCT` と組み合わせた `update_all`、組み込みの sidekiq アダプタ、`mb_chars`、`ActiveSupport::Configurable`。
  - 削除: `enqueue_after_transaction_commit` の `:never` / `:always` / `:default` 値とグローバル設定、`Benchmark.ms`、`Time#since` への `Time` 渡し、複数パスのルート、`;` によるクエリ区切り。
  - `schema.rb` のカラムがアルファベット順になった（diff ノイズに注意）。
  - `load_defaults 8.1` の主な設定: `action_on_path_relative_redirect = :raise`、`raise_on_missing_required_finder_order_columns = true`、`config.yjit = !Rails.env.local?`。

  — [Rails 8.1 release notes](https://guides.rubyonrails.org/8_1_release_notes.html); [Configuring Rails](https://guides.rubyonrails.org/configuring.html)
- strict_loading の設定（`strict_loading_by_default`、`strict_loading_mode :n_plus_one_only`、`action_on_strict_loading_violation :raise|:log`） — [Configuring Rails](https://guides.rubyonrails.org/configuring.html)

### Inferences
- アップグレード直後のコードベースでは、`config.load_defaults` の値と `new_framework_defaults_*.rb` の状態によって同じコードでも挙動が変わる（`raise_on_missing_required_finder_order_columns`、`strict_freshness` など）。これらは [ctx] 項目として「load_defaults のバージョンを確認する」をチェックリストに入れるべき。
- 「Solid Queue を別 DB に置く」のがデフォルトになったため、アプリ DB と同じトランザクションでジョブが投入される保証はない。`enqueue_after_transaction_commit` か `after_commit` を明示的に使うことが一層重要になった。
- 古い記事（7.0 以前）を根拠にした指摘は誤りになりうる。例: `enum status: {}` 構文、`secrets`、`return` によるトランザクションのロールバック。

### Gaps
- 認証ジェネレータが生成するコードのレビュー観点（`Current.session`、`rate_limit` など）は今回取得していない（セキュリティ担当の範囲）。7.2 の rate limiting（`rate_limit to:, within:`）は 7.2 のリリースノート本文に記載が見つからなかった（7.2 の Action Controller で入ったと記憶しているが、未検証）。
- Rails 8.0 / 8.1 に必要な Ruby の最低バージョンは今回確認できなかった。
- 2026-10 時点で Rails 8.2 / 9.0 が出ているかは確認していない。最新の安定版は Rails 8.1 系と想定している。

---

## Q3. rubocop-rails / rubocop-performance / スタイルガイドで、レビューで見るべきものとリンターに任せるもの

### Takeaway
rubocop-rails（2026 年時点のドキュメントは v2.38）は多くの観点を機械で検出できる。ただし、事故に直結する cop の一部（`Rails/SaveBang`、`Rails/DefaultScope`、`Rails/Env`、`Rails/EnvironmentVariableAccess`）はデフォルト無効で、多くの新しい cop は `pending`（`NewCops: enable` を設定しないと無効）になっている。レビュアーは「プロジェクトの .rubocop.yml で有効になっているか」を確認し、有効ならリンターに任せ、無効なら人間がレビューで見る、という分担にすべき。

### Cited Findings
- デフォルトの状態（rubocop-rails v2.38 のドキュメントより）:
  - **Enabled**: `Rails/ActiveRecordOverride`, `Rails/Date`, `Rails/DynamicFindBy`, `Rails/EnumUniqueness`, `Rails/Exit`, `Rails/FindBy`, `Rails/FindEach`, `Rails/HasManyOrHasOneDependent`, `Rails/HelperInstanceVariable`, `Rails/InverseOf`, `Rails/LexicallyScopedActionFilter`
  - **Pending**: `Rails/ActiveRecordCallbacksOrder`, `Rails/ActionControllerFlashBeforeRender`, `Rails/ActiveSupportOnLoad`, `Rails/AfterCommitOverride`, `Rails/DangerousColumnNames`, `Rails/DuplicateAssociation`, `Rails/DuplicateScope`, `Rails/DeprecatedActiveModelErrorsMethods`, `Rails/DurationArithmetic`, `Rails/EagerEvaluationLogMessage`, `Rails/EnumSyntax`, `Rails/FindById`, `Rails/FindByOrAssignmentMemoization`（2.33 で追加）, `Rails/IgnoredColumnsAssignment`
  - **Disabled**: `Rails/DefaultScope`, `Rails/Env`（2.34 で追加）, `Rails/EnvironmentVariableAccess`

  — [rubocop-rails cops](https://docs.rubocop.org/rubocop-rails/latest/cops_rails.html)
- Rails Style Guide の主なルール:
  - Skinny Controllers、One Method、Shared Instance Variables の最小化。
  - enum はハッシュ構文で値を明示する。HABTM より `has_many :through`。`before_destroy` には `prepend: true`。
  - `find_each`、`pluck` / `pick` / `ids`、`size` の推奨。
  - `find_by` を `||=` でメモ化しない。
  - `Time.now` 禁止。
  - メールはバックグラウンドで送る。
  - `&.` / `to_fs` / `exclude?` を使う。

  — [Rails Style Guide](https://rails.rubystyle.guide/)

### Inferences
- **リンターに任せてよいもの**（nit 相当。リンターが有効なら人間は指摘しない）: `DynamicFindBy`, `FindBy`, `pluck` / `pick` / `ids`, `to_fs`, `exclude?`, コールバックの順序, `DurationArithmetic`, `EagerEvaluationLogMessage`, `EnumSyntax`
- **リンターが検出しても人間が意図を判断すべきもの**: `SkipsModelValidations`（意図的な一括更新か）、`HasManyOrHasOneDependent`（destroy と delete_all のどちらにするか）、`UniqueValidationWithoutIndex`、`TransactionExitStatement`、`FindEach`（件数が実際に多いか）
- **リンターでは検出できないので、人間が must で見るもの**: トランザクションとジョブ・外部副作用の順序、ジョブの冪等性とリトライ設定、N+1（静的には検出不可。Bullet、Prosopite、strict_loading といった実行時の検出に頼る）、enum の既存値の変更、コールバック設計の妥当性。

### Gaps
- rubocop-performance のドキュメントは今回取得していない（予算の都合）。代表的な cop（`Performance/Detect`, `Performance/Count`, `Performance/MapCompact`, `Performance/StringInclude`, `Performance/RedundantBlockCall` など）はミクロな最適化が中心で、リンターに任せるのが妥当と考えるが、ソースで検証していない。
- rubocop-rails のページは 100k 文字で切れたため、`SkipsModelValidations`, `Pluck`, `SaveBang`, `WhereExists`, `TransactionExitStatement`, `UniqueValidationWithoutIndex`, `TimeZone`, `StrongParametersExpect`, `OutputSafety` のデフォルト状態は今回確認できなかった（cop の存在自体は既知）。本文中のこれらの cop 名は、存在は確実だが、有効・無効の状態は未検証。

---

## Q4. 大手 Rails 企業（Shopify / GitHub / 37signals / GitLab / 日本企業）が公開しているレビュー観点

### Takeaway
一次ソースで確認できたのは GitLab（クエリ数 100 本の上限、ジョブの冪等性と重複排除）と 37signals（vanilla Rails、callbacks と `Current` を適所で使う、concern は直交する振る舞いに使う）。日本企業（SmartHR、Money Forward、freee、Cookpad）が Rails のレビュー観点をまとめた記事は、今回の検索では見つからなかった。

### Cited Findings
- **GitLab: クエリ数**: 「Each controller, API endpoint and Sidekiq worker is allowed to execute up to 100 SQL queries」。テストでは超えると raise する。新しいエンドポイントには例外を認めない。17.2 以降、`QueryLimiting.disable!` には issue の URL と新しい閾値の指定が必須 — [GitLab: Query count limits](https://docs.gitlab.com/development/database/query_count_limits/)
- **GitLab: Sidekiq の冪等性**: 「It's expected that a job can run again after a failure without major side-effects」。`idempotent!` の宣言は cop で強制し、共有テスト `it_behaves_like 'an idempotent worker'` で検証する。重複排除の戦略は `until_executing`（デフォルト）/ `until_executed`、`including_scheduled: true`、TTL はデフォルト 10 分で、短くすると重複が起きうる — [GitLab: Sidekiq idempotent jobs](https://docs.gitlab.com/development/sidekiq/idempotent_jobs/)
- GitLab には他にも「Query performance guidelines」「Pagination guidelines / Offset pagination optimization」「Cached queries guidelines」「Database review guidelines」「Query Recorder」がある（ナビゲーションから存在を確認、本文は未取得） — [GitLab: Query count limits](https://docs.gitlab.com/development/database/query_count_limits/)
- **37signals**:
  - ドメインモデル（AR と PORO）が公開インターフェースを持ち、コントローラやジョブから直接呼ぶ。別のオーケストレーション層は設けない — [Vanilla Rails is plenty](https://dev.37signals.com/vanilla-rails-is-plenty/)
  - callbacks は主責務ではない単純な処理に向く。`Current` は監査のような直交した関心事に向く。どちらも「deep hole」になりうるので使いどころを選ぶ。絶対的なルールは「rigidity threshold that causes more harm than good」として退けている — [Globals, callbacks and other sacrileges](https://dev.37signals.com/globals-callbacks-and-other-sacrileges/)
- 日本語の一般的な資料としては、永和システムマネジメントの発表（2018）がある。N+1 と eager loading、ループ内の DB アクセス、server ログを確認する習慣をレビュー観点に挙げている — [What we learned from code review (speakerdeck)](https://speakerdeck.com/hisas/what-we-learned-from-code-review)

### Inferences
- GitLab の「数値で上限を決める」「冪等性をコードで宣言させる」方式は、レビュー観点を機械的なチェックに変える好例。チェックリストには「クエリ数の上限や N+1 検出（Prosopite / strict_loading）が CI で強制されているか」を [ctx] の should 項目として入れる価値がある。
- 37signals の立場（callbacks や concerns を使ってよい）と、「callbacks を避けてサービスオブジェクトにする」派は対立している。レビューで callbacks の使用自体を must 指摘するのは不適切で、「複雑なフローや主責務を callbacks で組み立てていないか」を should で見るのが妥当。

### Gaps
- **Shopify Engineering と GitHub Engineering の Rails レビュー観点**は、今回の予算内で一次ソースを取得できなかった。Shopify の job-iteration gem（中断・再開可能なジョブ。Rails 8.1 の Continuable の先行例とされる）や maintenance_tasks の存在は既知だが、本セッションでは未検証。
- **日本企業（SmartHR、Money Forward、freee、Cookpad）の Rails レビュー観点記事**は、2 回の検索ではヒットしなかった。企業名と具体的なキーワード（例:「SmartHR Tech Blog Rails N+1」「クックパッド 開発者ブログ Rails コードレビュー」）で再検索が必要。
- Bullet の公式ドキュメントは未取得（Prosopite README 内での比較のみ）。
