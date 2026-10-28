# DBマイグレーション / スキーマ変更 / データ移行のPRレビュー観点（Rails 7.1+/8.x, PostgreSQL 15+, MySQL 8.x）

凡例: 重大度 = must / should / nit、判定 = 「差分」(diffだけで判定可) / 「文脈」(テーブル規模・トラフィック・デプロイ方式・DBバージョン等のrepo/DB文脈が必要)
調査日: 2026-10-28。strong_migrations 最新版は 2.8.0 (2026-05-14)。

## Q1. 本番で危険な操作と安全な代替（strong_migrations の全チェック含む）

### Takeaway
strong_migrations 2.8.0 の検出項目（カラム削除・型変更・リネーム・FK/CHECK制約・非CONCURRENTLYインデックス・NOT NULL化・volatile default・json・enum値リネーム・MySQLのCOPY/LOCK指定など）はほぼそのままレビュー観点の「must」リストとして使える。ただしバックフィルや `execute` の生SQLは自動検出されないため、人間のレビューで必ず見る必要がある。

### Cited Findings
**strong_migrations のバージョン動向**
- 最新は 2.8.0 (2026-05-14)。`rename_enum_value` のチェックを追加 — [CHANGELOG](https://github.com/ankane/strong_migrations/blob/master/CHANGELOG.md)
- 2.7.0 (2026-04-25): MySQL/MariaDB 向けに `add_foreign_key` と、callable（式）default 付き `add_column` のチェックを追加 — [CHANGELOG](https://github.com/ankane/strong_migrations/blob/master/CHANGELOG.md)
- 2.6.0 (2026-04-07): MySQL/MariaDB 向けに `algorithm: :copy`、`lock: :shared` / `lock: :exclusive` のチェックを追加。Ruby 3.3 未満と Active Record 7.2 未満のサポートを終了 — [CHANGELOG](https://github.com/ankane/strong_migrations/blob/master/CHANGELOG.md)
- 2.5.0 (2025-07-27): `rename_schema` のチェックを追加。`auto_analyze` が `add_reference` にも適用されるようになった。2.4.0 (2025-06-23): `remove_invalid_indexes` オプションと実験的な `transaction_timeout` を追加。2.3.0 (2025-04-03): Postgres で CHECK 制約付きカラムへの `change_column` のチェックを追加 — [CHANGELOG](https://github.com/ankane/strong_migrations/blob/master/CHANGELOG.md)
- 含意: Rails 7.1 のプロジェクトで使える strong_migrations は 2.5.x が上限（2.6.0 以降は AR 7.2+ が必要） — [CHANGELOG](https://github.com/ankane/strong_migrations/blob/master/CHANGELOG.md)

**共通チェック（PG/MySQL 共通）** — 出典はすべて [strong_migrations README](https://github.com/ankane/strong_migrations)
- **カラム削除**: Active Record がカラム情報をキャッシュしているため、`remove_column` を直接実行すると稼働中アプリがエラーになる。手順は ①モデルに `self.ignored_columns += ["col"]` を追加してデプロイ ②`safety_assured { remove_column ... }` のマイグレーションをデプロイ ③ignore 行を削除。
- **型変更**: `change_column` はテーブルを書き換える。新カラム追加 → 二重書き込み → バックフィル → 読み取り切替 → 旧カラムへの書き込み停止 → 削除、の順で行う。安全な例外 (PG): `cidr`→`inet`、`citext`→`text`（インデックスなしの場合）、`string` の `:limit` を増やす/外す、`string`→`text`、`text`→`string`（limit なし）、`decimal` を同じ scale で precision を増やす、`datetime`/`interval`/`time` の precision を増やす/外す、セッション TZ が UTC の場合の `datetime`↔`timestamptz`。(MySQL/MariaDB) `string` の `:limit` 増加は、エンコーディングで決まる閾値（例: utf8mb3 で 85、latin1 で 255）を越えない範囲だけが安全。
- **カラムのリネーム / テーブルのリネーム**: 型変更と同じ expand/contract 手順（新カラム・新テーブル→二重書き込み→バックフィル→読み取り切替→旧を削除）。
- **`create_table ... force: true`**: 既存テーブルを消すおそれがある。`force` は付けない。
- **自動採番カラムの追加** (`add_column ... :primary_key`): テーブル書き換えが起きる。MySQL の statement-based レプリカでは採番値がずれることもある。新テーブルを作って移す。
- **stored 生成カラムの追加** (`stored: true`): テーブル書き換えが起きる。通常カラム＋コールバック/トリガーにするか、virtual 生成カラムを使う。
- **外部キーの追加**: `add_foreign_key` / `add_reference ... foreign_key: true` は両テーブルの書き込みをブロックする。PG では `validate: false` で追加し、別マイグレーションで `validate_foreign_key`。MySQL/MariaDB では、全行が正しくコネクションプーラーを使っていない場合に限り、`SET SESSION foreign_key_checks = 0` で囲み、`ensure` で 1 に戻す。
- **CHECK 制約の追加**: PG では行チェック中に読み書きをブロックし、MySQL では書き込みをブロックする。PG は `validate: false` → 別マイグレーションで `validate_check_constraint`。MySQL/MariaDB には安全な方法がない。
- **`execute` の生SQL**: 中身を検査できないため既定でブロックされる。安全を確認したうえで `safety_assured { execute ... }` を使う。`change_table` も同様に検査不能。
- **バックフィル**: 自動検出されない。スキーマ変更と同じトランザクションでの `update_all` は不可。`in_batches(of: 10000)` と `sleep` でスロットリングし、Rails console か `disable_ddl_transaction!` 付きマイグレーションでトランザクション外で実行する。`update_all` 以外でモデルを使うなら `reset_column_information` を呼ぶ。
- **ベストプラクティス**: 4カラム以上の非ユニーク複合インデックスは効果が乏しいことが多い。絞り込み効果の大きいカラムを先頭に置く。

**PostgreSQL 固有** — [strong_migrations README](https://github.com/ankane/strong_migrations)
- **非CONCURRENTLYのインデックス追加**: `disable_ddl_transaction!` と `algorithm: :concurrently` を使う（disable を忘れるとマイグレーションが失敗する）。新規テーブルには不要。
- **`add_reference`**: Rails は非 CONCURRENTLY のインデックスを張るため、`index: {algorithm: :concurrently}` と `disable_ddl_transaction!` を指定する。
- **`add_unique_constraint`**: 読み書きをブロックする。先に `add_index ... unique: true, algorithm: :concurrently` で作り、`add_unique_constraint using_index:` で制約化する。
- **`add_exclusion_constraint`**: NOT VALID にできないため安全な方法はない。
- **`json` カラム**: 等値演算子がなく `SELECT DISTINCT` が壊れる。`jsonb` を使う。
- **volatile な default**（例: `gen_random_uuid()`）: テーブル書き換えが起きる。default なしで追加 → `change_column_default` → バックフィル。
- **既存カラムの NOT NULL 化**: `change_column_null false` は危険。`IS NOT NULL` の CHECK 制約を `validate: false` で追加 → 別途 validate → `change_column_null` → CHECK 制約を削除。
- **`rename_enum_value`** (2.8.0〜): `add_enum_value` で新しい値を追加し、コードを両方の値に対応させてからバックフィルする。enum 値の削除は新しい enum 型を作らない限りできない。
- **`rename_schema`**: expand/contract で行う。

**MySQL/MariaDB 固有** — [strong_migrations README](https://github.com/ankane/strong_migrations)
- `algorithm: :copy` は書き込みをブロックする。`lock: :shared` は書き込みを、`lock: :exclusive` は読み書きをブロックする。デフォルトのまま使う。
- 式 default（例: `default: -> { "(now())" }`）付きの `add_column` はテーブル書き換えと書き込みブロックを起こす。default なしで追加 → `change_column_default` → バックフィル。

**MySQL 8.0 InnoDB Online DDL の事実** — [MySQL 8.0 Online DDL Operations](https://dev.mysql.com/doc/refman/8.0/en/innodb-online-ddl-operations.html)
- カラム追加: 8.0.12 以降は既定で INSTANT。カラム削除: 8.0.29 以降は INSTANT（行バージョンは 64 回が上限、超えると ERROR 4092）。リネーム: 8.0.28 以降は INSTANT。default の変更はメタデータのみ。
- セカンダリインデックスの追加・削除は INPLACE で、DML の並行実行も可能。ただし `CREATE INDEX` はテーブルにアクセス中の全トランザクションが終わるまで完了しない。
- **データ型の変更は COPY のみ**（再構築あり、DML の並行実行不可）。VARCHAR を 256 バイト未満から 256 バイト以上へ広げる変更も INPLACE 不可。
- NOT NULL 化は INPLACE だが再構築あり。strict SQL_MODE が必要で、NULL 行があると失敗する。
- FK 追加が INPLACE になるのは `foreign_key_checks=0` のときだけで、それ以外は COPY。主キーの再定義は常にデータコピーを伴う。`CONVERT TO CHARACTER SET` は DML の並行実行不可。
- INSTANT が使えないケース: `ROW_FORMAT=COMPRESSED`、FULLTEXT インデックスを持つテーブル、一時テーブル。

**PostgreSQL のロックモード** — [PostgreSQL: Explicit Locking](https://www.postgresql.org/docs/current/explicit-locking.html)
- ACCESS EXCLUSIVE は SELECT すらブロックする唯一のモード。多くの `ALTER TABLE` と `DROP TABLE`/`TRUNCATE` が取得する。
- `CREATE INDEX`（非 CONCURRENTLY）は SHARE ロックで書き込みをブロックする。`CREATE INDEX CONCURRENTLY` は SHARE UPDATE EXCLUSIVE で読み書きとも可能。
- 衝突するロックは無期限に待つ。長時間開いたトランザクションは待機の原因になる。
- 補足（今回の取得ページには記載がなく、[ALTER TABLE リファレンス](https://www.postgresql.org/docs/current/sql-altertable.html)で要確認）: ADD FOREIGN KEY は SHARE ROW EXCLUSIVE、VALIDATE CONSTRAINT は SHARE UPDATE EXCLUSIVE、SET NOT NULL は ACCESS EXCLUSIVE（有効な `IS NOT NULL` CHECK 制約があればフルスキャンを省略、PG12+）。

**その他**
- Rails ガイド: `change_column` は不可逆。`change_column_default` は `from:`/`to:` を指定したときだけ可逆。`remove_column` は型を指定しないと可逆にならない — [Rails Guides: Active Record Migrations](https://guides.rubyonrails.org/active_record_migrations.html)
- GitLab: PostgreSQL 11 以降なら default 付き `add_column` は問題ない。NOT NULL カラムの default は同じマイグレーションではなく、後続の post-deploy migration で外す — [GitLab Migration Style Guide](https://docs.gitlab.com/development/migration_style_guide/)

### Inferences
**チェックリスト（危険操作）**

| # | 観点（日本語） | 重大度 | 判定 | 出典 |
|---|---|---|---|---|
| 1 | 既存テーブルへの `add_index` / `add_reference` (PG) に `algorithm: :concurrently` と `disable_ddl_transaction!` が付いているか（新規テーブルなら不要） | must | 差分（新規テーブルかどうかは差分で分かる） | [strong_migrations](https://github.com/ankane/strong_migrations) |
| 2 | `remove_index` も大きなテーブルでは CONCURRENTLY にしているか（strong_migrations では opt-in の `enable_check(:remove_index)`） | should | 文脈（行数） | 同上, [GitLab](https://docs.gitlab.com/development/migration_style_guide/) |
| 3 | MySQL でインデックス追加・カラム変更に `algorithm: :copy` や `lock: :shared/:exclusive` を指定していないか。型変更や VARCHAR の 255 バイト境界越えは COPY になるので、gh-ost/pt-osc 等の利用を検討しているか | must | 差分＋文脈（行数） | [strong_migrations](https://github.com/ankane/strong_migrations), [MySQL docs](https://dev.mysql.com/doc/refman/8.0/en/innodb-online-ddl-operations.html) |
| 4 | `change_column`（型変更）は安全な例外リストに該当するか。該当しなければ新カラム＋二重書き込み＋バックフィル＋切替で行う | must | 差分（例外判定は旧型を schema で確認） | [strong_migrations](https://github.com/ankane/strong_migrations) |
| 5 | `rename_column` / `rename_table` を稼働中コードがあるまま実行していないか（expand/contract を使う） | must | 差分 | 同上, [PlanetScale](https://planetscale.com/blog/zero-downtime-rails-migrations-planetscale-rails-gem) |
| 6 | `remove_column` の前に、前のリリースで `ignored_columns` が入りデプロイ済みか。同じPRで ignore と削除を同時に行っていないか | must | 差分＋文脈（デプロイ履歴） | [strong_migrations](https://github.com/ankane/strong_migrations), [GitLab](https://docs.gitlab.com/development/database/avoiding_downtime_in_migrations/) |
| 7 | 既存カラムの NOT NULL 化 (PG) は CHECK 制約 (`validate: false`) → validate → `change_column_null` → CHECK 制約削除の手順か。MySQL では NULL 行が残っていないか、再構築コストは許容できるか | must | 差分＋文脈 | 同上, [MySQL docs](https://dev.mysql.com/doc/refman/8.0/en/innodb-online-ddl-operations.html) |
| 8 | FK 追加 (PG) は `validate: false` と、別マイグレーションでの `validate_foreign_key` に分けているか。1 マイグレーションに FK は 1 つまでか | must | 差分 | [strong_migrations](https://github.com/ankane/strong_migrations), [GitLab](https://docs.gitlab.com/development/migration_style_guide/) |
| 9 | FK 追加 (MySQL) で COPY にならないか（`foreign_key_checks=0` 運用の前提が成り立つか、プーラーは使っていないか） | must | 文脈 | 同上, [MySQL docs](https://dev.mysql.com/doc/refman/8.0/en/innodb-online-ddl-operations.html) |
| 10 | CHECK 制約 (PG) は `validate: false` と別途 validate に分けているか。MySQL の CHECK 制約追加は大きなテーブルでは書き込みブロックを伴うことを了承しているか | must | 差分＋文脈 | [strong_migrations](https://github.com/ankane/strong_migrations) |
| 11 | `add_unique_constraint` (PG) は、CONCURRENTLY で作ったユニークインデックスを `using_index:` で制約化しているか | must | 差分 | 同上 |
| 12 | volatile な default（`gen_random_uuid()`, `now()` 式など）を既存テーブルの `add_column` で指定していないか（PG・MySQL とも） | must | 差分 | 同上 |
| 13 | `json` ではなく `jsonb` を使っているか (PG) | should | 差分 | 同上 |
| 14 | `create_table ... force: true` を使っていないか | must | 差分 | 同上 |
| 15 | 既存テーブルへの自動採番カラムや `stored: true` 生成カラムの追加を避けているか | must | 差分 | 同上 |
| 16 | `safety_assured { execute ... }` の生SQLは、レビュアーがロックレベルと実行時間を確認したか（`safety_assured` は正当化理由のコメント付きか） | must | 差分 | 同上, [GitLab](https://docs.gitlab.com/development/migration_style_guide/) |
| 17 | PG の enum 型で値のリネーム・削除をしていないか（`add_enum_value` を使い、コードを両方の値に対応させる） | must | 差分 | [strong_migrations](https://github.com/ankane/strong_migrations) |
| 18 | `add_exclusion_constraint` を既存の大きなテーブルに追加していないか | must | 文脈 | 同上 |
| 19 | 4カラム以上の非ユニーク複合インデックスは妥当か（先頭カラムの選択性） | nit〜should | 差分＋文脈（クエリ） | 同上 |
| 20 | strong_migrations 導入済みなら、`safe_by_default`, `target_version`, `start_after`, `remove_invalid_indexes`, `alphabetize_schema` の設定と、gem 自体のバージョン（AR 7.1 なら 2.5.x まで）が適切か | should | 文脈（initializer） | [README](https://github.com/ankane/strong_migrations), [CHANGELOG](https://github.com/ankane/strong_migrations/blob/master/CHANGELOG.md) |

- Rails 側の enum（integer で保存する `enum`）の変更は、strong_migrations の対象外のアプリ層リスクとして見るべき（筆者推論）。既存値の数値マッピングを並べ替え・削除するとデータの意味が変わる（must、差分で判定可）。値の追加は、旧コードが新しい値を読んだときに `ArgumentError` 等にならないかを確認する（文脈）。この点を明示した一次ソースは今回取得できていない。
- MySQL の Rails 標準 `add_index` には `algorithm: :inplace` に相当する指定の慣行がある（Rails の `index_algorithm`）。ただ、日本の事例では `LOCK=NONE` / `ALGORITHM=INSTANT` を最終 SQL に付け、オンラインで実行できない DDL をエラーにして検出する手法が紹介されている — [Railsのマイグレーション、どこまで安全にできるか (Gotanda.rb#54, 2023-08-24)](https://speakerdeck.com/mnmandahalf/railsnomaiguresiyon-dokomadean-quan-nidekiruka)

### Gaps
- PG の ALTER TABLE 各フォームのロックレベルは explicit-locking ページに記載がなく、ALTER TABLE リファレンスでの一次確認は未実施（上記はモデル知識。要検証）。
- 「PG ではロック待ちのキューに入った ACCESS EXCLUSIVE 要求が、後続の SELECT までブロックする」という定番の注意点は、公式ドキュメントで明示記述を確認できなかった（取得ページにも記載なし）。
- Rails の `enum` 変更（7.1 の `validate: true` オプションなど）は一次ソースを今回取得していない。

## Q2. ゼロダウンタイムデプロイのパターン（expand/contract, 多段デプロイ, ローリングデプロイ中の後方互換）

### Takeaway
「スキーマ変更は先、コードは後。削除は逆順（コードから先に消す）」が業界共通の原則。リネーム・型変更・削除はすべて複数リリースに分ける。各段階で「旧コード＋新スキーマ」「新コード＋旧スキーマ」の両方が正しく動くかを確認することが、レビューの中心になる。

### Cited Findings
- PlanetScale: スキーマ変更とコードはアトミックにデプロイできないため、スキーマ変更をそのカラムを使うコードより先にデプロイする。カラム削除はコードを先に出す（`ignored_columns`）。Insights でクエリが使っていないことを確認してから drop し、最後に ignore を外す — [PlanetScale blog](https://planetscale.com/blog/zero-downtime-rails-migrations-planetscale-rails-gem)
- PlanetScale: リネームは「新カラム追加 → 両方に書く → スクリプトでバックフィル → 新カラムから読み、二重書き込みをやめる → 旧カラム削除」。各ステップを別々の本番デプロイにする — [PlanetScale blog](https://planetscale.com/blog/zero-downtime-rails-migrations-planetscale-rails-gem)
- PlanetScale: インデックス削除の前に `sys.schema_unused_indexes` で未使用を確認する。ただし頻度の低いバッチのクエリは現れないことがある — [PlanetScale blog](https://planetscale.com/blog/zero-downtime-rails-migrations-planetscale-rails-gem)
- GitLab のカラム削除は 3 リリース: M で `ignore_column`（`remove_with`/`remove_after` 付き）を入れてコード参照を除去、M+1 で post-deployment migration で drop、M+2 で ignore を削除。「ignore と drop を同じリリースで行ってはならない」 — [GitLab: Avoiding downtime in migrations](https://docs.gitlab.com/development/database/avoiding_downtime_in_migrations/)
- GitLab のリネーム（小さいテーブル）: 通常マイグレーションで `rename_column_concurrently`、post-deploy で `cleanup_concurrent_column_rename`。大きいテーブルは batched background migration を使う。型変更は `change_column_type_concurrently`（一時カラムと同期トリガー）→ `cleanup_concurrent_column_type_change` — [GitLab](https://docs.gitlab.com/development/database/avoiding_downtime_in_migrations/)
- GitLab: NOT NULL の追加はアプリ変更のデプロイ後に post-deploy migration で行い、削除は通常マイグレーションで行う。default の変更は 2 マイナーリリースに分ける（`SafelyChangeColumnDefault` と `columns_changing_default`）。モデル側で値を明示的に入れてから default を変更する — [GitLab](https://docs.gitlab.com/development/database/avoiding_downtime_in_migrations/)
- GitLab のテーブル削除: M でコードを除去、M+1 で FK を個別の post-deploy migration（高トラフィックテーブルは `with_lock_retries`）で外してから drop。int→bigint の PK 変換は N〜N+3 の 4 リリース — [GitLab](https://docs.gitlab.com/development/database/avoiding_downtime_in_migrations/)
- GitLab: 通常マイグレーション（`db/migrate`）は新しいコードのデプロイ前に走る。post-deployment migration（`db/post_migrate`）はカラム削除や非クリティカルなインデックスに使う。`create_table`/`add_column` は通常マイグレーションでなければならない — [GitLab Migration Style Guide](https://docs.gitlab.com/development/migration_style_guide/)
- GitHub: `DROP TABLE` は直接実行せず `RENAME TABLE repositories TO _repositories_DROP_20200101123456` のようにリネームし、数日後に GC する（即時に戻せるようにするため）。DROP TABLE は「コードがまだ依存しているかもしれない」ため最も危険な文として扱う — [GitHub blog (2020-02-14, 2021-08-12 更新)](https://github.blog/engineering/infrastructure/automating-mysql-schema-migrations-with-github-actions-and-more/)
- strong_migrations: Active Record のカラムキャッシュのため、`remove_column` 直後に稼働中プロセスがエラーになる（`ignored_columns` が必要な根拠） — [strong_migrations](https://github.com/ankane/strong_migrations)

### Inferences
**チェックリスト（デプロイ互換性）**

| # | 観点 | 重大度 | 判定 | 出典 |
|---|---|---|---|---|
| 1 | 同じPRに「スキーマ変更」と「そのスキーマを前提にしたコード」が混在する場合、マイグレーション適用前後とローリング中の旧/新 Pod の混在で壊れないか（例: 新しい NOT NULL カラムに旧コードが INSERT すると失敗する） | must | 文脈（デプロイ方式：マイグレーションをデプロイ前に流すか後に流すか） | [PlanetScale](https://planetscale.com/blog/zero-downtime-rails-migrations-planetscale-rails-gem), [GitLab](https://docs.gitlab.com/development/migration_style_guide/) |
| 2 | カラム/テーブル削除PRは、コード参照の除去（＋`ignored_columns`）を先行リリースで済ませているか。`ignored_columns` の後始末（次リリースで削除）のチケットや期限（GitLab の `remove_after` 相当）があるか | must | 差分＋文脈 | [GitLab](https://docs.gitlab.com/development/database/avoiding_downtime_in_migrations/) |
| 3 | リネーム・型変更が単一PRで完結していないか。expand（追加＋二重書き込み）→ migrate（バックフィル）→ contract（読み替え→削除）のどの段階のPRかが説明されているか | must | 差分 | [PlanetScale](https://planetscale.com/blog/zero-downtime-rails-migrations-planetscale-rails-gem) |
| 4 | NOT NULL 追加は、全ての書き込み経路が値を入れるコードがデプロイされた後か（GitLab では post-deploy） | must | 文脈 | [GitLab](https://docs.gitlab.com/development/database/avoiding_downtime_in_migrations/) |
| 5 | default 変更時、旧コードが「旧 default 前提」で動く窓を考慮しているか（モデル側の `attribute` default 等で明示しているか） | should | 文脈 | 同上 |
| 6 | テーブル削除の前に FK を外し、実データの退避や rename による猶予期間（GitHub 方式）を検討したか | should | 文脈 | [GitHub blog](https://github.blog/engineering/infrastructure/automating-mysql-schema-migrations-with-github-actions-and-more/) |
| 7 | インデックス削除は、本番で未使用であること（PG `pg_stat_user_indexes`、MySQL `sys.schema_unused_indexes`、低頻度バッチの考慮）を確認済みか | should | 文脈（DB 統計） | [PlanetScale](https://planetscale.com/blog/zero-downtime-rails-migrations-planetscale-rails-gem), [GitLab](https://docs.gitlab.com/development/migration_style_guide/) |
| 8 | 削除系の操作（drop column/table）でロールバック計画（データ復元手段）が説明されているか | should | 差分（PR説明） | [GitHub blog](https://github.blog/engineering/infrastructure/automating-mysql-schema-migrations-with-github-actions-and-more/) |

- Rails 標準には GitLab の post-deploy migration に相当する仕組みはない。そのため「どのマイグレーションをコードのデプロイ前に流すか後に流すか」は PR を分けて表現するしかない、というのが筆者推論。レビュアーは「このPRはどの段階か」を必ず確認するとよい。

### Gaps
- Shopify の具体的なゼロダウンタイム手順（Schema Migrations Service の詳細）は公開記事の全文を確認できず、トーク概要レベルしか取得できなかった。

## Q3. lock_timeout / statement_timeout、トランザクション、可逆性、schema.rb の差分、インデックス設計

### Takeaway
マイグレーション専用に短い `lock_timeout`（例: 10s）と長めの `statement_timeout` を設定し、リトライと組み合わせるのが定石。レビューでは、`disable_ddl_transaction!` の要否と副作用（途中失敗時に中途半端な状態が残ること）、`change` で可逆か、schema.rb/structure.sql の無関係な差分（チャーン）を確認する。Rails 8.1 は schema.rb のカラムをアルファベット順に出力するため、アップグレード直後の大きな並べ替え差分はこれが原因と判断できる。

### Cited Findings
**タイムアウトとリトライ**
- strong_migrations: `StrongMigrations.lock_timeout = 10.seconds`、`statement_timeout = 1.hour`。`ALTER ROLE myuser SET lock_timeout = '10s'` でも設定できる。PgBouncer の transaction mode ではユーザー単位で設定する — [strong_migrations](https://github.com/ankane/strong_migrations)
- strong_migrations: `lock_timeout_retries = 3`（実験的）と `lock_timeout_retry_delay`。トランザクション外ではステートメント単位で、DDL トランザクション内（PG のみ）ではマイグレーション全体をリトライする — [strong_migrations](https://github.com/ankane/strong_migrations)
- strong_migrations: ロックタイムアウトで残った INVALID インデックスを、再実行時に削除する `remove_invalid_indexes = true` — [strong_migrations](https://github.com/ankane/strong_migrations)
- アプリ側の推奨値 (database.yml): PG は `statement_timeout: 15s`, `lock_timeout: 10s`。MySQL は `max_execution_time: 15000`, `lock_wait_timeout: 10`。MariaDB は `max_statement_time: 15` — [strong_migrations](https://github.com/ankane/strong_migrations)
- GitLab: 高トラフィックテーブルへの FK・カラム追加削除、`change_column_default`、`create_table`/`drop_table` には `with_lock_retries`（`lock_timeout` 付きで最大 50 回リトライ、`change` 内では使えず up/down が必要）を使う。GitLab.com の statement timeout は 15s — [GitLab Migration Style Guide](https://docs.gitlab.com/development/migration_style_guide/)
- GitLab: 1 マイグレーションで取るロックは 1 つが望ましい。FK は 1 トランザクションに 1 つ（参照先テーブルもロックされるため） — [GitLab](https://docs.gitlab.com/development/migration_style_guide/)
- GitLab の時間制限: 通常マイグレーションは 3 分以内、post-deploy は 10 分以内（並行インデックス作成は 20 分）。background migration の各クエリはコールドキャッシュで 1 秒未満 — [GitLab](https://docs.gitlab.com/development/migration_style_guide/)
- MySQL: メタデータロック待ち（長い SELECT の後ろに ALTER が並び、その後ろに後続の読み取りが詰まる）は Online DDL でも避けられない。マイグレーションのセッションで `lock_wait_timeout` を短く（例: 5 秒）して早めに失敗させる — [Gotanda.rb#54 スライド](https://speakerdeck.com/mnmandahalf/railsnomaiguresiyon-dokomadean-quan-nidekiruka)

**トランザクションと可逆性**
- Rails: `disable_ddl_transaction!` はトランザクション内で実行できない文（例: `ALTER TYPE ... ADD VALUE`）に使う。その中でも自分でトランザクションを張れる — [Rails Guides](https://guides.rubyonrails.org/active_record_migrations.html)
- Rails: 基本は `change`。不可逆な処理は `reversible` ブロックか up/down で書き、戻せないものは `ActiveRecord::IrreversibleMigration` を raise する。`drop_table` は元のオプションとブロックが必要。`remove_check_constraint` は元の式が必要 — [Rails Guides](https://guides.rubyonrails.org/active_record_migrations.html)
- GitLab: すべてのマイグレーションに動作する `down` を書き、可逆性をどう検証したかをコメントで残す。不可逆なデータ移行は `down` を no-op にして理由をコメントする — [GitLab](https://docs.gitlab.com/development/migration_style_guide/)
- strong_migrations はロールバック時のチェックを既定で無効にしている（`check_down = true` で有効化） — [strong_migrations](https://github.com/ankane/strong_migrations)

**スキーマファイル**
- Rails 8.1 は schema.rb のカラムを名前順で出力する（無効化不可）。アップグレード後の初回 dump で全テーブルが並び替わる。正確なカラム順が必要なら structure.sql を使う（Rails PR #53281） — [Saeloun blog](https://blog.saeloun.com/2025/12/29/rails-sorts-table-columns-by-name-when-dumping-schema/), [Rails Upgrade Guide](https://guides.rubyonrails.org/upgrading_ruby_on_rails.html)
- 8.1 未満では strong_migrations の `alphabetize_schema = true` で同じ効果が得られる — [strong_migrations](https://github.com/ankane/strong_migrations)
- トリガー・シーケンス・ストアドプロシージャなど Ruby DSL で表現できない機能を使う場合は `schema_format = :sql`（structure.sql）にする。スキーマファイルはソース管理に含める — [Rails Guides](https://guides.rubyonrails.org/active_record_migrations.html)
- GitLab: structure.sql は手で編集しない。カラムの並べ替えも手で行わない。ローカルスキーマがずれたら再生成スクリプトで作り直す — [GitLab](https://docs.gitlab.com/development/migration_style_guide/)
- マイグレーションクラスは `ActiveRecord::Migration[8.1]` のようにバージョンを固定し、Rails バージョンごとの挙動を保つ — [Rails Guides](https://guides.rubyonrails.org/active_record_migrations.html)

**インデックス・制約設計**
- 4 カラム以上の非ユニークインデックスはまれにしか有効でない。選択性の高いカラムを先頭に置く。`auto_analyze` でインデックス追加後に ANALYZE を実行できる — [strong_migrations](https://github.com/ankane/strong_migrations)
- GitLab: まずインデックスが本当に必要か確認する。削除前に 30 日分の `idx_scan` で未使用を確かめる。約 1,000 行未満のテーブルなら通常の `remove_index` でもよい。インデックス名は明示する — [GitLab](https://docs.gitlab.com/development/migration_style_guide/)

### Inferences
**チェックリスト（トランザクション・可逆性・スキーマ・インデックス）**

| # | 観点 | 重大度 | 判定 | 出典 |
|---|---|---|---|---|
| 1 | マイグレーション実行時に `lock_timeout`（PG）/ `lock_wait_timeout`（MySQL）が短く設定されているか（プロジェクトの設定またはマイグレーション内） | must（プロジェクト単位） | 文脈 | [strong_migrations](https://github.com/ankane/strong_migrations), [スライド](https://speakerdeck.com/mnmandahalf/railsnomaiguresiyon-dokomadean-quan-nidekiruka) |
| 2 | `statement_timeout` がアプリ用（15s など）のままで、長時間の DDL（CONCURRENTLY 等）が途中で落ちないか | should | 文脈 | 同上 |
| 3 | `disable_ddl_transaction!` を使うマイグレーションは 1 操作に絞っているか。途中失敗時に再実行可能か（`if_not_exists:` / `if_exists:`、INVALID インデックスの扱い） | must | 差分 | [strong_migrations](https://github.com/ankane/strong_migrations), [Rails Guides](https://guides.rubyonrails.org/active_record_migrations.html) |
| 4 | 1 マイグレーションで複数テーブルに強いロックを取っていないか（FK は 1 つ/マイグレーション） | should | 差分 | [GitLab](https://docs.gitlab.com/development/migration_style_guide/) |
| 5 | `change` 内の操作が可逆か（`remove_column` に型がある、`change_column_default` に `from:/to:` がある、`drop_table` にブロックがある、`change_column` / `execute` は reversible か up/down） | must | 差分 | [Rails Guides](https://guides.rubyonrails.org/active_record_migrations.html) |
| 6 | 不可逆なマイグレーションは `IrreversibleMigration` を raise しているか、no-op に理由が書かれているか | should | 差分 | 同上, [GitLab](https://docs.gitlab.com/development/migration_style_guide/) |
| 7 | 可逆性を検証したか（`db:migrate:redo`、または rollback → migrate で schema 差分が出ないこと） | should | 文脈（CI/手元） | [GitLab](https://docs.gitlab.com/development/migration_style_guide/) |
| 8 | schema.rb/structure.sql の差分がマイグレーション内容と一致しているか（無関係なカラム順の入れ替え、他ブランチ由来のカラム、`version` の巻き戻り、ローカル DB のバージョン差による出力差がないか） | must | 差分 | [GitLab](https://docs.gitlab.com/development/migration_style_guide/), [Saeloun](https://blog.saeloun.com/2025/12/29/rails-sorts-table-columns-by-name-when-dumping-schema/) |
| 9 | Rails 8.1 へのアップグレードPRでの schema.rb の全面並べ替えは想定内（一度きり）として、機能PRとは分けているか | nit〜should | 差分 | [Saeloun](https://blog.saeloun.com/2025/12/29/rails-sorts-table-columns-by-name-when-dumping-schema/) |
| 10 | マイグレーションファイルがあるのに schema ファイルの差分がない（またはその逆）ということがないか | must | 差分 | [Rails Guides](https://guides.rubyonrails.org/active_record_migrations.html) |
| 11 | `ActiveRecord::Migration[x.y]` が現行の Rails バージョンか（古いバージョン指定のコピペで挙動が変わる） | nit | 差分 | 同上 |
| 12 | `belongs_to` / `add_reference` の外部キーカラムにインデックスがあるか（PG は FK を張っても自動ではインデックスを作らない） | should | 差分 | 筆者推論（下記 Gaps） |
| 13 | `validates :x, uniqueness:` だけで一意性を担保していないか（ユニークインデックスがあるか）。逆に、ユニークインデックス追加前に既存の重複データを解消しているか | must | 差分＋文脈（既存データ） | 筆者推論（下記 Gaps） |
| 14 | 複合インデックスのカラム順（等値条件 → 範囲・ソートの順）と、既存インデックスの前方一致で冗長になっていないか | should | 差分＋文脈（クエリ） | [strong_migrations](https://github.com/ankane/strong_migrations) |
| 15 | インデックス名が長すぎないか（PG 63 バイト制限）、明示的に名前を付けているか | nit | 差分 | [GitLab](https://docs.gitlab.com/development/migration_style_guide/) |
| 16 | カラムの型が適切か: ID 系は bigint、時刻は timestamptz の方針、文字列の長さ制限（GitLab の `add_text_limit`）、jsonb のサイズ制限 | should | 差分 | [GitLab](https://docs.gitlab.com/development/migration_style_guide/) |

### Gaps
- 「PG は FK カラムにインデックスを自動作成しない／MySQL InnoDB は自動作成する」は一般的な知識だが、今回のセッションでは一次ソースを取得していない（要: PG docs の CREATE TABLE / MySQL docs の FOREIGN KEY 制約）。
- 「uniqueness バリデーションは競合状態を防げないのでユニークインデックスが必要」は Rails Guides（Active Record Validations）に記載があるはずだが、今回は未取得。

## Q4. データ移行の実践（スキーマ移行との分離、バッチ、冪等性、maintenance_tasks / data_migrate）と MySQL/PG 固有の事情

### Takeaway
Rails Guides 自身が「マイグレーションファイルでのデータ移行は一般に推奨しない」として maintenance_tasks を推奨している。大量データの更新は、スキーマ変更とは別のトランザクションで、バッチ化・スロットリング・冪等性・再開可能性を備えて実行するのが基本。MySQL の大きなテーブルでは、Online DDL で済まない変更（型変更など）に gh-ost / pt-osc / Vitess（PlanetScale）を使うのが業界標準。

### Cited Findings
- Rails Guides: 「it is generally not advised to perform data migrations using migration files」。代わりに `maintenance_tasks` gem を推奨。シードコードは冪等にする — [Rails Guides](https://guides.rubyonrails.org/active_record_migrations.html)
- strong_migrations: スキーマ変更と同じトランザクションで `update_all` をしない。`in_batches(of: 10000)` と `sleep` によるスロットリングで、トランザクション外で実行する — [strong_migrations](https://github.com/ankane/strong_migrations)
- maintenance_tasks: データ移行（例: NOT NULL 化の前のバックフィル）用の Rails エンジン。`collection` と `process` を定義し、`throttle_on`（既定バックオフ 30 秒）、一時停止・再開・キャンセル、カーソルによる再開ができる。job-iteration の既定最大実行時間は 5 分。Sidekiq では停止時に再エンキューされ、少なくとも 1 イテレーションは再実行されうるため、`process` は冪等にする。1 要素あたりの処理は約 25 秒以内。スキーマ変更には使わず、マイグレーションを使う。タスクは使い捨て（定期実行には使わない） — [Shopify/maintenance_tasks](https://github.com/Shopify/maintenance_tasks)
- GitLab: マイグレーション内でアプリのモデルを使わず、`MigrationRecord` を継承したローカルモデルを `table_name` 付きで定義する。テーブル変更後は `reset_column_information` を呼ぶ。データ変更は `each_batch_range` と `BATCH_SIZE` でバッチ化する。post-deploy の時間内に収まらないデータ作業は batched background migration（Sidekiq、スキーマ変更は禁止）で行う — [GitLab Migration Style Guide](https://docs.gitlab.com/development/migration_style_guide/)
- Shopify: LHM（シャドウテーブル＋トリガー＋バッチコピー＋スワップ）は変更内容によってはレコードを落としうると Shopify 自身が分析し、NOT NULL カラム追加の安全性を検証した — [Shopify Engineering](https://shopify.engineering/add-not-null-colums-to-database)。その後トリガー方式の LHM からトリガーレスの gh-ost に移行した（Vienna.rb の講演概要） — [RubyEvents](https://www.rubyevents.org/talks/rails-migrations-at-scale-how-shopify-moved-from-trigger-based-online-schema-changes-to-gh-ost)
- Shopify は Rails 7.0 で、マイグレーションの実行方法を差し替えられる「swappable migration backend」を Rails に入れた — [Rails at Scale (2025-12-08)](https://railsatscale.com/2025-12-08-swappable-migration-backends-in-rails/)
- GitHub: skeema（宣言的スキーマ）＋ GitHub Actions で PR に `skeema diff` をコメント → `migration:for:review` ラベルで DB インフラチームがレビュー（主要な RoR リポジトリでは db-schema-reviewers も必須）→ skeefree が gh-ost を実行（クラスタあたり同時に 1 つの ALTER、スロットリング可）。1 日平均 2 件のマイグレーション — [GitHub blog](https://github.blog/engineering/infrastructure/automating-mysql-schema-migrations-with-github-actions-and-more/)
- PlanetScale: safe migrations を有効にしたブランチでは直接の DDL を拒否し、deploy request（Vitess の online DDL、ゴーストテーブルへの同期）で適用する。schema revert で旧テーブルを保持し、データを失わずに戻せる — [PlanetScale blog](https://planetscale.com/blog/zero-downtime-rails-migrations-planetscale-rails-gem), [PlanetScale safe migrations docs](https://planetscale.com/docs/concepts/safe-migrations)
- 日本の事例（primeNumber）: MySQL で `ALGORITHM=INSTANT` / `LOCK=NONE` を強制し、オンラインで実行できない DDL をエラーにして通常リリースから分離する。カラム追加は許可し、位置指定（AFTER）での追加は禁止。`Rake::Task["db:migrate"].enhance` や Mysql2Adapter の `execute` の prepend で SQL にオプションを付ける。Ridgepole には `--alter-extra` オプションがある — [Gotanda.rb#54 スライド](https://speakerdeck.com/mnmandahalf/railsnomaiguresiyon-dokomadean-quan-nidekiruka)、関連記事 [Zenn (primeNumber)](https://zenn.dev/primenumber/articles/7af6e95ddbb91d)

### Inferences
**チェックリスト（データ移行・DB固有）**

| # | 観点 | 重大度 | 判定 | 出典 |
|---|---|---|---|---|
| 1 | `db/migrate` 内で大量の `update_all` / `find_each` による更新をしていないか。している場合、スキーマ変更とは別のマイグレーション/タスクに分け、`disable_ddl_transaction!` を付け、バッチ化しているか | must | 差分＋文脈（行数） | [strong_migrations](https://github.com/ankane/strong_migrations), [Rails Guides](https://guides.rubyonrails.org/active_record_migrations.html) |
| 2 | マイグレーション内でアプリのモデル（将来変わる可能性のあるクラス・バリデーション・コールバック・default_scope）を直接使っていないか（ローカルで定義したモデル＋SQL を使う） | should | 差分 | [GitLab](https://docs.gitlab.com/development/migration_style_guide/) |
| 3 | 同じマイグレーションでカラムを追加してからモデル経由で書き込む場合、`reset_column_information` を呼んでいるか | must | 差分 | [strong_migrations](https://github.com/ankane/strong_migrations), [GitLab](https://docs.gitlab.com/development/migration_style_guide/) |
| 4 | データ移行は冪等で再実行可能か（WHERE で未処理行だけを対象にするなど）。途中失敗から再開できるか | must | 差分 | [maintenance_tasks](https://github.com/Shopify/maintenance_tasks) |
| 5 | バッチサイズ・スロットリング（sleep / `throttle_on`）・レプリカ遅延への配慮があるか | should | 差分＋文脈 | 同上, [strong_migrations](https://github.com/ankane/strong_migrations) |
| 6 | maintenance_tasks のタスクにテストがあるか。使い捨て前提で、実行後に削除する計画があるか。デプロイとの順序（スキーマ追加 → タスク実行 → NOT NULL 化）が PR に書かれているか | should | 差分 | [maintenance_tasks](https://github.com/Shopify/maintenance_tasks) |
| 7 | バックフィル中に新しく書き込まれる行も新しい値になるよう、アプリの二重書き込みが先にデプロイされているか | must | 文脈 | [PlanetScale](https://planetscale.com/blog/zero-downtime-rails-migrations-planetscale-rails-gem) |
| 8 | 1 ステートメント/1 バッチあたりの実行時間が statement timeout 以内か（GitLab では 1 クエリ 1 秒未満が目安） | should | 文脈 | [GitLab](https://docs.gitlab.com/development/migration_style_guide/) |
| 9 | (MySQL) 変更が INSTANT/INPLACE で済むか。COPY になる変更（型変更、VARCHAR 境界越え、FK 追加、PK 変更、charset 変換）を大きなテーブルに対してマイグレーションで直接実行していないか（gh-ost / pt-osc / LHM / PlanetScale deploy request に回す） | must | 差分＋文脈 | [MySQL docs](https://dev.mysql.com/doc/refman/8.0/en/innodb-online-ddl-operations.html), [GitHub](https://github.blog/engineering/infrastructure/automating-mysql-schema-migrations-with-github-actions-and-more/) |
| 10 | (MySQL) `add_column ... after:` のような位置指定は避けているか（8.0.29 未満では INSTANT にならない） | should | 差分＋文脈（MySQL バージョン） | [スライド](https://speakerdeck.com/mnmandahalf/railsnomaiguresiyon-dokomadean-quan-nidekiruka), [MySQL docs](https://dev.mysql.com/doc/refman/8.0/en/innodb-online-ddl-operations.html) |
| 11 | (MySQL) INSTANT での add/drop の繰り返しで、行バージョン上限 64 に近づいていないか | nit | 文脈 | [MySQL docs](https://dev.mysql.com/doc/refman/8.0/en/innodb-online-ddl-operations.html) |
| 12 | (MySQL) 長時間トランザクションによるメタデータロック待ちの対策（`lock_wait_timeout`、ピーク時間を避けた実行）があるか | should | 文脈 | [スライド](https://speakerdeck.com/mnmandahalf/railsnomaiguresiyon-dokomadean-quan-nidekiruka) |
| 13 | (PG) CONCURRENTLY のインデックス作成が失敗した場合の INVALID インデックスの扱い（`remove_invalid_indexes` または手動の DROP）が決まっているか | should | 文脈 | [strong_migrations](https://github.com/ankane/strong_migrations) |
| 14 | (PG) PgBouncer の transaction mode を使っている場合、`SET lock_timeout` がセッションをまたいで効かないことを考慮しているか（ロール単位で設定する） | should | 文脈 | [strong_migrations](https://github.com/ankane/strong_migrations) |
| 15 | (共通) 大きなインデックス作成の後に統計を更新しているか（`auto_analyze`） | nit | 文脈 | 同上 |
| 16 | Ridgepole など宣言的スキーマ管理の場合、生成される ALTER（`--dry-run` の出力）を PR に貼ってレビューしているか（GitHub の skeema diff コメントに相当） | should | 差分 | [GitHub](https://github.blog/engineering/infrastructure/automating-mysql-schema-migrations-with-github-actions-and-more/), [スライド](https://speakerdeck.com/mnmandahalf/railsnomaiguresiyon-dokomadean-quan-nidekiruka) |

- data_migrate gem（`db/data` にデータ移行を置き、スキーマ移行と同じ流れで実行する方式）は、maintenance_tasks に比べるとスロットリングや再開の仕組みが弱い、というのが筆者推論。今回のセッションでは README を取得していないため、比較は未検証。

### Gaps
- data_migrate gem の最新の仕様（Rails 8 対応状況、`data_schema.rb` の扱い）は未取得。
- maintenance_tasks の最新バージョンと必要な Rails バージョンは README に記載がなく、gemspec は未確認。
- Shopify の gh-ost 移行の具体的な手順（カットオーバー、レビュー体制）は講演概要しかなく、詳細は不明。

## Q5. 各社が公開しているマイグレーションレビューの体制

### Takeaway
GitLab は「database reviewer/maintainer」による必須レビュー、時間予算（3分/10分）、マイグレーションの 3 分類、可逆性の検証コメントを制度化している。GitHub は DB インフラチームと db-schema-reviewers によるラベル駆動の承認と、gh-ost の自動実行を組み合わせている。PlanetScale は deploy request とスキーマ revert をプラットフォーム側で提供する。日本では MySQL の INSTANT 強制やメタデータロック対策の事例が公開されている。

### Cited Findings
- GitLab: 生 SQL は database reviewer に相談する。`disable_ddl_transaction!` の要否に迷ったら RuboCop と database review に委ねる。高トラフィックテーブルの一覧を `rubocop/rubocop-migrations.yml` で管理し、分析用途だけのカラムをそこへ追加しない。新しいテーブルは database dictionary に登録する。`db/schema_migrations/<timestamp>` のチェックサムをコミットする。マイグレーションのタイムスタンプは 21 日以内、`milestone` の指定が必須 — [GitLab Migration Style Guide](https://docs.gitlab.com/development/migration_style_guide/)
- GitLab: post-deploy migration の名前に対象テーブル名を含め、wraparound vacuum との競合を自動チェックできるようにする。高トラフィックテーブルへのトリガーは post-deploy で `with_lock_retries` を使い、冪等に作る — [GitLab](https://docs.gitlab.com/development/migration_style_guide/)
- GitHub: ラベル `migration:for:review` が付くまで DB インフラチームは PR を認識しない（早すぎるレビューを避けるため）。DB インフラチームが承認権限を持ち、gh-ost ジョブの中断やスロットリングもできる — [GitHub blog](https://github.blog/engineering/infrastructure/automating-mysql-schema-migrations-with-github-actions-and-more/)
- Intercom（2025年の講演）: マイグレーションのチェックリストを GitHub Action で PR に自動投稿し、RuboCop のルールで危険なマイグレーションを検出している — [RubyEvents: Taming the Beast](https://www.rubyevents.org/talks/taming-the-beast-safely-managing-database-operations-in-rails-in-a-team-of-100s)
- 日本: strong_migrations は PG と汎用的な危険操作が中心で、MySQL の Online DDL のチェックは弱い（2023年時点の指摘。その後 2.6.0/2.7.0 で MySQL の COPY/LOCK/FK/式 default のチェックが追加された） — [スライド (2023)](https://speakerdeck.com/mnmandahalf/railsnomaiguresiyon-dokomadean-quan-nidekiruka), [CHANGELOG](https://github.com/ankane/strong_migrations/blob/master/CHANGELOG.md)

### Inferences
**チェックリスト（プロセス）**

| # | 観点 | 重大度 | 判定 | 出典 |
|---|---|---|---|---|
| 1 | PR 説明に「対象テーブルの行数とトラフィック」「想定実行時間」「取得するロック」「デプロイ順序（何段目か）」「ロールバック手順」が書かれているか | should | 差分（PR 本文） | [GitLab](https://docs.gitlab.com/development/migration_style_guide/), [GitHub](https://github.blog/engineering/infrastructure/automating-mysql-schema-migrations-with-github-actions-and-more/) |
| 2 | 高トラフィック/巨大テーブルへの変更は DB 担当者（DBA/SRE）のレビューを通しているか（CODEOWNERS で `db/` を割り当てる） | should | 文脈 | 同上 |
| 3 | 危険操作の検出を CI で自動化しているか（strong_migrations / RuboCop / online_migrations） | should | 文脈 | [strong_migrations](https://github.com/ankane/strong_migrations), [Intercom講演](https://www.rubyevents.org/talks/taming-the-beast-safely-managing-database-operations-in-rails-in-a-team-of-100s) |
| 4 | 本番相当の規模のデータで実行時間を計測したか（GitLab の `db:gitlabcom-database-testing` 相当） | should | 文脈 | [GitLab](https://docs.gitlab.com/development/migration_style_guide/) |
| 5 | マイグレーションのタイムスタンプが、マージ順と前後しても問題ないか（古いタイムスタンプが後からマージされると、環境によって適用順が変わる） | nit〜should | 差分 | [GitLab](https://docs.gitlab.com/development/migration_style_guide/)（21 日ルールの趣旨からの推論） |

- online_migrations gem（fatkodima、PG 専用、strong_migrations の拡張版を自称）は、GitLab 風のヘルパー（リネーム・型変更の concurrently 版、バックグラウンド移行）を提供するとされるが、今回は詳細を未確認 — [Algolia docsearch 上の一覧](https://docsearch.algolia.com/mcp/docs/repo/fatkodima/online_migrations)

### Gaps
- Shopify の社内マイグレーションレビュー体制（Schema Migrations Service）の詳細な公開記事は見つからなかった。
- 日本の Rails 企業（クックパッド、SmartHR、マネーフォワードなど）の公開ガイドラインは、今回の検索では具体的なものを取得できなかった（Ridgepole 運用の事例を含め、追加調査の余地あり）。
