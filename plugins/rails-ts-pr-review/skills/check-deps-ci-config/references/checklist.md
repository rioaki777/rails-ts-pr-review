# check-deps-ci-config チェックリスト

このファイルは scripts/extract_checklists.py で docs/research/report.md から生成。直接編集しない。

凡例は次のとおり。**既定**は重要度の初期値で、must はマージ前に必須、should は強く推奨（理由があれば見送り可）、nit は任意を表す。検証段階で上げ下げできる。**判定**は、指摘に必要な情報の範囲を表す。diff は差分だけで判断できる、repo は呼び出し元・スキーマ・設定・lint 設定などリポジトリ文脈が必要、PR は PR 説明やチケットが必要、実行は実機・CI 結果・本番統計・外部レジストリが必要、という意味だ。判定が「実行」の項目は静的レビューでは確定できないので、カバレッジ報告で「人間による確認が必要」と明示する。出典が「慣行」の項目は、権威ある単一の一次情報が見つからなかったものだ。

| # | 観点 | 既定 | 判定 | 出典 |
|---|---|---|---|---|
| DC1 | 新規依存の妥当性：必要性（既存の依存や標準機能で代替できないか）、メンテナンス状況、公開者、ダウンロード数、名前の綴り（typosquat） | must（新規追加） | diff+外部 | [CISA](https://www.cisa.gov/news-events/alerts/2025/09/23/widespread-supply-chain-compromise-impacting-npm-ecosystem) |
| DC2 | lockfile の差分が manifest の変更に見合っているか（推移的依存の大量更新、`resolved` やレジストリの変更、integrity の変化） | must | diff | 同上; [pnpm](https://pnpm.io/supply-chain-security) |
| DC3 | manifest と lockfile の整合（lockfile のコミット漏れ、複数のパッケージマネージャーの混在）、CI で frozen install をしているか | must | diff | [pnpm](https://pnpm.io/supply-chain-security) |
| DC4 | install scripts を持つ依存の追加、`allowBuilds`/`onlyBuiltDependencies` の拡大、`ignore-scripts` の撤回 | must | diff | 同上; [Microsoft](https://www.microsoft.com/en-us/security/blog/2026/08/04/chaindrop-supply-chain-compromise-anatomy-self-propagating-worm/) |
| DC5 | Gemfile の `git:`/`github:`/`path:`、非公式の `source`、npm の `git+https` や tarball 依存 | must | diff | [CISA](https://www.cisa.gov/news-events/alerts/2025/09/23/widespread-supply-chain-compromise-impacting-npm-ecosystem) |
| DC6 | 既知の脆弱性を持つバージョン（bundler-audit、`npm audit`。React2Shell の修正版より古い React/Next.js など） | must（Critical/High） | diff+実行 | [Brakeman](https://brakemanscanner.org/docs/warning_types/); [Zscaler](https://www.zscaler.com/jp/blogs/security-research/react2shell-remote-code-execution-vulnerability-cve-2025-55182) |
| DC7 | ライセンスがプロジェクトのポリシーと両立するか | must（商用・配布物） | 外部 | 慣行 |
| DC8 | メジャーアップデートで破壊的変更に対応しているか（Rails なら `load_defaults` や `new_framework_defaults`。一括で有効にしていないか） | must | repo | [Rails Upgrading](https://guides.rubyonrails.org/upgrading_ruby_on_rails.html) |
| DC9 | 公開直後のバージョンを採用していないか。`minimumReleaseAge` などの cooldown を緩めていないか | should | diff+外部 | [pnpm](https://pnpm.io/supply-chain-security) |
| DC10 | バージョン指定の緩和（`*`、`latest`、`>=`）。`PLATFORMS`、`.ruby-version`、`engines`、`packageManager` の環境間の一致 | should | diff | 慣行 |
| DC11 | Renovate/Dependabot の PR：CI の結果、release notes、patch/minor/major の区分、自動マージの範囲 | should | diff+実行 | [Renovate](https://docs.renovatebot.com/configuration-options/) |
| DC12 | サードパーティのアクションをフル SHA でピンしているか（workflow dependency lockfile が使えるならそれを使う） | must（サードパーティ）／should（`actions/*`） | diff | [GitHub Secure use](https://docs.github.com/en/actions/reference/security/secure-use) |
| DC13 | `permissions:` を最小にしているか（`write-all` を使っていない、`id-token: write` が必要なジョブに限定されている） | must | diff | 同上 |
| DC14 | `run:` や `script:` に `${{ github.event.*.title/body/head_ref }}` などの未信頼入力を直接展開していないか（env 経由で渡す） | must | diff | 同上 |
| DC15 | `pull_request_target`/`workflow_run` で PR の head を checkout してビルドしていないか。artifact を未信頼として扱っているか | must | diff | 同上 |
| DC16 | secret をログに出していないか。構造化した secret を使っていないか。fork からの PR に secret が渡らないか。public リポジトリで self-hosted runner を使っていないか | must | diff | 同上 |
| DC17 | CI を弱める変更（`continue-on-error`、テストの除外、`if: false`、カバレッジ閾値の引き下げ） | must | diff | 慣行 |
| DC18 | OIDC と environment の required reviewers、`.github/workflows` の CODEOWNERS、actionlint/zizmor | should | diff+repo | [GitHub Secure use](https://docs.github.com/en/actions/reference/security/secure-use) |
| DC19 | Docker：本番イメージを非 root で実行しているか。秘密を `ARG`/`ENV`/`COPY` で焼き込んでいないか（`--mount=type=secret` を使う）。`.dockerignore` で `.env` や `master.key` を除外しているか | must | diff | [Docker BP](https://docs.docker.com/build/building/best-practices/); [Docker secrets](https://docs.docker.com/build/building/secrets/) |
| DC20 | Docker：ベースイメージを digest でピンしているか。multi-stage でビルドツールを最終イメージから除いているか。`apt-get` を同じ RUN にまとめ、キャッシュを削除しているか | should／nit | diff | [Docker BP](https://docs.docker.com/build/building/best-practices/) |
| DC21 | 新しい ENV 変数や設定キーを全環境（`.env.example` を含む）に追加し、未設定時の挙動（`fetch` で早期に失敗するか）を決めているか | must | repo | 慣行 |
| DC22 | `config/environments/*.rb` の本番だけ異なる設定（`force_ssl`、`hosts`、`eager_load`、キャッシュストア）が意図どおりか | should | diff+repo | [Configuring Rails](https://guides.rubyonrails.org/configuring.html) |
