# check-rails-app チェックリスト

このファイルは scripts/extract_checklists.py で docs/research/report.md から生成。直接編集しない。

凡例は次のとおり。**既定**は重要度の初期値で、must はマージ前に必須、should は強く推奨（理由があれば見送り可）、nit は任意を表す。検証段階で上げ下げできる。**判定**は、指摘に必要な情報の範囲を表す。diff は差分だけで判断できる、repo は呼び出し元・スキーマ・設定・lint 設定などリポジトリ文脈が必要、PR は PR 説明やチケットが必要、実行は実機・CI 結果・本番統計・外部レジストリが必要、という意味だ。判定が「実行」の項目は静的レビューでは確定できないので、カバレッジ報告で「人間による確認が必要」と明示する。出典が「慣行」の項目は、権威ある単一の一次情報が見つからなかったものだ。

| # | 観点 | 既定 | 判定 | 出典 |
|---|---|---|---|---|
| RB1 | **N+1（必ず探す）**：ループ、ビュー、シリアライザ、ジョブの中での関連アクセス。`includes`/`preload` が漏れていないか。Bullet が見逃す `Model.find(x.foo_id)` の繰り返しや、関連に対する `first`/`pluck` も対象 | must（ホットパス）／should | diff+repo | [Prosopite](https://github.com/charkost/prosopite); [GitLab Query limits](https://docs.gitlab.com/development/database/query_count_limits/) |
| RB2 | **無制限ロード（必ず探す）**：件数が無制限になりうるテーブルに `all.each`/`.map` を使っている（`find_each`/`in_batches` を使う）。一覧 API や画面にページネーションがない | must | diff | [Rails Style Guide](https://rails.rubystyle.guide/); [rubocop-rails](https://docs.rubocop.org/rubocop-rails/latest/cops_rails.html) |
| RB3 | コールバックを飛ばす一括操作（`update_all`、`delete_all`、`update_column(s)`、`insert_all`、`upsert_all`、`touch_all`、`increment!` など）。監査ログ、検索インデックス、キャッシュ無効化をコールバックに頼っていないか | must（意図の確認） | diff+repo | [Callbacks guide](https://guides.rubyonrails.org/active_record_callbacks.html) |
| RB4 | トランザクション内や `after_save` で、ジョブ投入・メール送信・外部 API 呼び出しをしている（`after_commit`、`tx.after_commit`、`after_all_transactions_commit` を使う） | must | diff | 同上; [Rails 7.2 notes](https://guides.rubyonrails.org/7_2_release_notes.html) |
| RB5 | `ApplicationJob` で `enqueue_after_transaction_commit` が有効か（現行ガイドでは既定で無効。Rails 8 の Solid Queue は既定で別 DB に置かれ、アプリのトランザクションに含まれない） | must | repo | [Active Job Basics](https://guides.rubyonrails.org/active_job_basics.html) |
| RB6 | ジョブの冪等性（同じ引数で複数回実行しても安全か） | must | repo | [GitLab idempotent jobs](https://docs.gitlab.com/development/sidekiq/idempotent_jobs/) |
| RB7 | Active Job は既定でリトライしない。`retry_on`/`discard_on` は適切か。`ActiveJob::DeserializationError` の扱いを決めているか | must | diff | [Active Job Basics](https://guides.rubyonrails.org/active_job_basics.html) |
| RB8 | `find_by` の nil を考慮しているか。`@x \|\|= find_by(...)` でメモ化していないか | must | diff | [Rails Style Guide](https://rails.rubystyle.guide/) |
| RB9 | `Time.now`/`Date.today` を使っていないか（`Time.current`/`Date.current` を使う） | must | diff | 同上 |
| RB10 | enum をハッシュ構文で、値を明示して定義しているか。Rails 8.0 で削除されたキーワード引数形式を使っていないか。既存値の変更・削除・並べ替え（データの意味が変わるので `db-migration` にも回す） | must | diff | [Rails 8.0 notes](https://guides.rubyonrails.org/8_0_release_notes.html); [Rails Style Guide](https://rails.rubystyle.guide/) |
| RB11 | コールバックを止めるのに `false` を返している（`throw :abort` を使う） | must | diff | [Callbacks guide](https://guides.rubyonrails.org/active_record_callbacks.html) |
| RB12 | 削除済み API が残っていないか（`Rails.application.secrets`、`Time` と `TimeWithZone` の演算、複数パスのルート）。deprecated の API（`order` なしの `first`、組み込みの sidekiq アダプタ、`mb_chars`）を使っていないか | must（削除済み）／should（deprecated） | diff+repo | [7.2](https://guides.rubyonrails.org/7_2_release_notes.html), [8.0](https://guides.rubyonrails.org/8_0_release_notes.html), [8.1](https://guides.rubyonrails.org/8_1_release_notes.html) notes |
| RB13 | `after_commit` の落とし穴（同じメソッド名で create/update 用を定義すると最後の定義しか効かない、例外で後続が実行されない） | should | diff | [Callbacks guide](https://guides.rubyonrails.org/active_record_callbacks.html) |
| RB14 | コールバックで複雑なフローや中核のドメイン処理を組み立てていないか。コールバック内で `save`/`update` を呼んでいないか | should | repo | [37signals](https://dev.37signals.com/globals-callbacks-and-other-sacrileges/); [Callbacks guide](https://guides.rubyonrails.org/active_record_callbacks.html) |
| RB15 | `before_destroy` による削除可否の検証を、`dependent: :destroy` より前に宣言しているか（または `prepend: true`） | should | diff | 同上 |
| RB16 | `dependent:` を明示しているか。大量の子レコードに対して `:destroy` と `:delete_all` のどちらが適切か | should | repo | [rubocop-rails](https://docs.rubocop.org/rubocop-rails/latest/cops_rails.html) |
| RB17 | `default_scope` を新しく追加していないか | should | diff | 同上 |
| RB18 | `save`/`update` の戻り値（false）を無視していないか | should | diff | 同上 |
| RB19 | トランザクションブロック内の `return`/`break`/`throw`（7.2 以降はロールバックではなく commit される） | should | diff | [Rails 7.2 notes](https://guides.rubyonrails.org/7_2_release_notes.html) |
| RB20 | `normalizes` は生 SQL には適用されず、既存レコードは再保存するまで正規化されない。既存データの移行は必要か | should | diff | [Rails 7.1 notes](https://guides.rubyonrails.org/7_1_release_notes.html) |
| RB21 | コントローラは薄いか。Rails 8 なら `params.expect` を使っているか。`allow_browser` が API クライアントに 406 を返していないか | should | diff | [Rails Style Guide](https://rails.rubystyle.guide/); [8.0](https://guides.rubyonrails.org/8_0_release_notes.html)/[7.2](https://guides.rubyonrails.org/7_2_release_notes.html) notes |
| RB22 | メールを `deliver_later` で、commit 後に送っているか | should | diff | [Rails Style Guide](https://rails.rubystyle.guide/) |
| RB23 | `perform_all_later` が enqueue コールバックを実行しないこと、`limits_concurrency` のコスト、長時間ジョブに `ActiveJob::Continuable` を使うかを考慮しているか | should | diff | [Active Job Basics](https://guides.rubyonrails.org/active_job_basics.html); [8.1 notes](https://guides.rubyonrails.org/8_1_release_notes.html) |
| RB24 | `Current` 属性が、ジョブやコンソールからの実行で空になる前提で設計されているか | should | repo | [37signals](https://dev.37signals.com/globals-callbacks-and-other-sacrileges/) |
| RB25 | アプリコード中の `Rails.env.production?` 分岐や `ENV` の直接参照 | should | diff | [rubocop-rails](https://docs.rubocop.org/rubocop-rails/latest/cops_rails.html) |
| RB26 | フラグメントキャッシュのキーに、表示に影響する属性（ロケール、権限、関連の `updated_at`）が含まれているか。Solid Cache を低レイテンシ前提の用途に使っていないか | should | diff+repo | [Rails 8.0 notes](https://guides.rubyonrails.org/8_0_release_notes.html); キャッシュキーは慣行 |
| RB27 | `config.load_defaults` のバージョンによって同じコードの挙動が変わる箇所（`raise_on_missing_required_finder_order_columns`、`strict_freshness` など） | should | repo | [Configuring Rails](https://guides.rubyonrails.org/configuring.html) |
| RB28 | `pluck`/`pick`/`ids`/`size`/`exists?` の使い分け、`find_by` と動的 finder（リンターが有効なら指摘しない） | nit | diff | [Rails Style Guide](https://rails.rubystyle.guide/) |
