# check-db-migration チェックリスト

このファイルは scripts/extract_checklists.py で docs/research/report.md から生成。直接編集しない。

凡例は次のとおり。**既定**は重要度の初期値で、must はマージ前に必須、should は強く推奨（理由があれば見送り可）、nit は任意を表す。検証段階で上げ下げできる。**判定**は、指摘に必要な情報の範囲を表す。diff は差分だけで判断できる、repo は呼び出し元・スキーマ・設定・lint 設定などリポジトリ文脈が必要、PR は PR 説明やチケットが必要、実行は実機・CI 結果・本番統計・外部レジストリが必要、という意味だ。判定が「実行」の項目は静的レビューでは確定できないので、カバレッジ報告で「人間による確認が必要」と明示する。出典が「慣行」の項目は、権威ある単一の一次情報が見つからなかったものだ。

| # | 観点 | 既定 | 判定 | 出典 |
|---|---|---|---|---|
| DB1 | 既存テーブルへの `add_index`/`add_reference`（PG）に `algorithm: :concurrently` と `disable_ddl_transaction!` が付いているか | must | diff | [strong_migrations](https://github.com/ankane/strong_migrations) |
| DB2 | MySQL で `algorithm: :copy` や `lock:` を指定していないか。大きなテーブルに COPY になる変更（型変更、VARCHAR の 256 バイト境界越え、FK、PK、charset）を直接かけていないか（gh-ost などに回す） | must | diff+repo | 同上; [MySQL Online DDL](https://dev.mysql.com/doc/refman/8.0/en/innodb-online-ddl-operations.html) |
| DB3 | `change_column` による型変更が安全な例外リストにない場合、新カラム→二重書き込み→バックフィル→読み取り切替の手順を踏んでいるか | must | diff | [strong_migrations](https://github.com/ankane/strong_migrations) |
| DB4 | 稼働中のコードがあるまま `rename_column`/`rename_table` をしていないか | must | diff | 同上 |
| DB5 | `remove_column` の前のリリースで `ignored_columns` をデプロイ済みか。ignore と削除を同じ PR でしていないか | must | diff+repo | 同上; [GitLab](https://docs.gitlab.com/development/database/avoiding_downtime_in_migrations/) |
| DB6 | 既存カラムを NOT NULL にする手順：PG では CHECK 制約（`validate: false`）→ validate → `change_column_null`。書き込み経路のコードを先にデプロイしているか | must | diff+repo | 同上 |
| DB7 | FK・CHECK 制約を `validate: false` で追加し、別のマイグレーションで validate しているか。FK は1マイグレーションに1つか。`add_unique_constraint` は `using_index:` を使っているか | must | diff | [strong_migrations](https://github.com/ankane/strong_migrations); [GitLab style](https://docs.gitlab.com/development/migration_style_guide/) |
| DB8 | 既存テーブルへの volatile な default、自動採番カラム、`stored: true` の生成カラムの追加。`create_table force: true` | must | diff | [strong_migrations](https://github.com/ankane/strong_migrations) |
| DB9 | `safety_assured { execute ... }` について、ロックレベルと実行時間を確認し、理由をコメントしているか | must | diff | 同上 |
| DB10 | PG の enum 値をリネーム・削除していないか。Rails の integer enum の数値マッピングを変えていないか | must | diff | 同上 |
| DB11 | ローリングデプロイ中に旧 Pod と新 Pod が混在しても壊れないか（例：新しい NOT NULL カラムに旧コードが INSERT する） | must | repo | [PlanetScale](https://planetscale.com/blog/zero-downtime-rails-migrations-planetscale-rails-gem) |
| DB12 | リネームや型変更を単一の PR で完結させていないか。PR が expand/contract のどの段階かを説明しているか | must | PR+diff | 同上 |
| DB13 | マイグレーション実行時の `lock_timeout`（PG）/`lock_wait_timeout`（MySQL）が短く設定されているか | must（プロジェクト単位） | repo | [strong_migrations](https://github.com/ankane/strong_migrations) |
| DB14 | `disable_ddl_transaction!` を使うマイグレーションは1操作に絞り、`if_not_exists:` などで再実行できるようにしているか | must | diff | 同上; [Rails Guides](https://guides.rubyonrails.org/active_record_migrations.html) |
| DB15 | 可逆性：`remove_column` に型がある、`change_column_default` に `from:`/`to:` がある、不可逆なら `IrreversibleMigration` を raise する | must | diff | [Rails Guides](https://guides.rubyonrails.org/active_record_migrations.html) |
| DB16 | schema.rb/structure.sql の差分がマイグレーションと一致しているか（無関係なカラム、version の巻き戻り、マイグレーションがあるのにスキーマ差分がない） | must | diff | 同上; [GitLab style](https://docs.gitlab.com/development/migration_style_guide/) |
| DB17 | データ移行：`db/migrate` で大量の `update_all` をしていないか。スキーマ変更とは分け、バッチ化・スロットリングし、トランザクション外で実行しているか | must | diff+repo | [Rails Guides](https://guides.rubyonrails.org/active_record_migrations.html); [strong_migrations](https://github.com/ankane/strong_migrations) |
| DB18 | データ移行は冪等で、途中から再開できるか。バックフィルの前に二重書き込みのコードをデプロイしているか | must | diff+repo | [maintenance_tasks](https://github.com/Shopify/maintenance_tasks); [PlanetScale](https://planetscale.com/blog/zero-downtime-rails-migrations-planetscale-rails-gem) |
| DB19 | マイグレーション内でアプリのモデルを直接使っていないか。カラム追加後に `reset_column_information` を呼んでいるか | should／must | diff | [GitLab style](https://docs.gitlab.com/development/migration_style_guide/) |
| DB20 | `validates uniqueness` に対応するユニークインデックスがあるか。インデックス追加の前に既存の重複を解消しているか | must | diff+repo | [rubocop-rails](https://docs.rubocop.org/rubocop-rails/latest/cops_rails.html) |
| DB21 | テーブルやインデックスを削除する前に、本番で未使用であることを確認し、FK を外し、猶予期間（リネームしておく方式）を検討したか | should | 実行 | [GitHub blog](https://github.blog/engineering/infrastructure/automating-mysql-schema-migrations-with-github-actions-and-more/); [PlanetScale](https://planetscale.com/blog/zero-downtime-rails-migrations-planetscale-rails-gem) |
| DB22 | default を変更するとき、旧コードが旧 default を前提に動く期間を考慮しているか | should | repo | [GitLab](https://docs.gitlab.com/development/database/avoiding_downtime_in_migrations/) |
| DB23 | PR 説明に行数、想定実行時間、取得するロック、デプロイの段階、ロールバック手順が書かれているか | should | PR | [GitLab style](https://docs.gitlab.com/development/migration_style_guide/) |
| DB24 | 複合インデックスの列順と冗長性（4列以上の非ユニーク複合インデックスは効果が乏しいことが多い）、`json` ではなく `jsonb`、ID 系は bigint | should | diff | [strong_migrations](https://github.com/ankane/strong_migrations) |
| DB25 | strong_migrations の設定とバージョン（Active Record 7.1 なら 2.5.x が上限） | should | repo | [CHANGELOG](https://github.com/ankane/strong_migrations/blob/master/CHANGELOG.md) |
| DB26 | Rails 8.1 へのアップグレードで schema.rb のカラムが一斉にアルファベット順に並び替わる差分を、機能 PR と分けているか。`Migration[x.y]` が現行バージョンか | nit | diff | [Saeloun](https://blog.saeloun.com/2025/12/29/rails-sorts-table-columns-by-name-when-dumping-schema/) |
