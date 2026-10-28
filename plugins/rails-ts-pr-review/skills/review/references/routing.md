# 振り分け

子は次の順で適用する。`check-security` と `check-general` は条件を満たす差分で常時実施し、専門子は該当時だけ実施する。

| 子スキル | 起動条件（主な対象パス） | 責務 |
|---|---|---|
| `check-general` | すべてのコード差分（常時） | ロジック、エッジケース、呼び出し側との契約、例外処理、互換性、並行性、設計、feature flag |
| `check-security` | docs 以外のすべての差分（常時。`.claude/`・`.vscode/` を含む） | OWASP Top 10:2025 に対応する Rails/TS の脆弱性パターン、秘密情報、PII |
| `check-db-migration` | `db/migrate`、`db/schema.rb`、`structure.sql`、`db/data`、`app/tasks/maintenance`、enum を変更したモデル | ロック、ゼロダウンタイム、可逆性、データ移行 |
| `check-rails-app` | `app/{models,controllers,views,helpers,jobs,mailers,services,...}`、`lib/`、`config/routes.rb` | Active Record、トランザクション、ジョブ、時刻、Rails のバージョン差。N+1・無制限ロード |
| `check-frontend` | `app/javascript`、`app/frontend`、`*.ts(x)`、`*.vue`、`*.css`、`app/views/**/*.erb`、`tsconfig.json`、`next.config.*` | 型安全性、React/Next.js、Hotwire、状態管理、a11y、INP、バンドル |
| `check-deps-ci-config` | `Gemfile*`、`package.json`、lockfile、`.npmrc`、`.github/workflows`、`Dockerfile`、`config/environments`、`config/*.yml`、`config/initializers` | サプライチェーン、GitHub Actions、Docker、環境設定 |
| `check-tests` | `spec/`、`test/`、`*.test.ts`、`e2e/`、本体差分の要約 | テスト有無、空振りテスト、非決定性 |
| `check-docs` | `*.md`、`docs/`、`doc/adr`、`CHANGELOG`、コード側の要約 | コードとの一致、手順、ADR、CHANGELOG |

## 分割と対象外

- 一つの子に渡す差分が約400行を超えるときは、ファイル単位で複数回に分ける。P4 の大きな PR は生成コードと削除を除外しても約1000行超または多数ファイルなら分割を提案し、子への配分を細かくする。
- `check-tests` には本体の振る舞い変更の要約を、`check-docs` には変更したコマンド・ENV・API の要約を必ず渡す。テストまたは文書差分がなくても、必要なら「ないこと」を指摘する。
- docs-only PR ではコード向けの子を、どの条件にも合わない変更では全ての非該当子を、カバレッジで明示的に「対象外」とする。対象外や指摘なしを安全の意味にしない。
- 未知の拡張子など子が一つも担当しない変更は「対象外の変更」として列挙する。
- 生成ファイル（先頭に "generated" / "Do not edit" などの生成コメントがある、`generated/`・`vendor/`・`*.min.js`・lockfile 以外の自動生成物など）は専門子の確認対象から外す。P3/P4 として混入や規模を指摘し、カバレッジに「生成ファイルとして除外」と列挙する。lockfile は `check-deps-ci-config` の対象のまま残す。
