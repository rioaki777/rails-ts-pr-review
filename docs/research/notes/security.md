# セキュリティ観点のPRレビューチェックリスト（Rails + TypeScript）

調査日: 2026-10-28。重大度の凡例: **must** = マージ前に必ず修正、**should** = 原則修正（理由があれば例外可）、**nit** = 改善提案。判定の凡例: **Diff** = 差分だけで判定できる、**Ctx** = リポジトリ文脈（他ファイル、設定、ポリシー、ルーティング）が必要。

## Q1. 最新のOWASP標準（Top 10 2025、ASVS 5.0、Code Review Guide）と差分上の具体パターン

### Takeaway
OWASP Top 10:2025 は A01 Broken Access Control（SSRFを統合）、A02 Security Misconfiguration、A03 Software Supply Chain Failures（新設）、A05 Injection、A10 Mishandling of Exceptional Conditions（新設）などで構成される。ASVS 5.0（2025年5月公開、全17章）は、Top 10の各項目を具体的なレビュー観点へ分解するための章立てとして使える。OWASP Code Review Guide は v2.0（2017年頃）から更新されておらず古い。Rails固有の観点は Rails Cheat Sheet、Rails Guides、Brakeman で補う。

### Cited Findings
- Top 10:2025 の構成: A01 Broken Access Control / A02 Security Misconfiguration / A03 Software Supply Chain Failures / A04 Cryptographic Failures / A05 Injection / A06 Insecure Design / A07 Authentication Failures / A08 Software or Data Integrity Failures / A09 Security Logging and Alerting Failures / A10 Mishandling of Exceptional Conditions — [OWASP Top 10:2025](https://top10.owasp.org/2025)
- 2021年版からの変更: 新設2カテゴリと統合1件。A03 は「A06:2021 Vulnerable and Outdated Components の拡張」。A10 は2025年の新カテゴリ。SSRF は A01 に統合された。A02 Misconfiguration は #5 から #2 に上昇し、A04 Crypto は #2 から #4、A05 Injection は #3 から #5 に下降した。A07 は「Identification and Authentication Failures」から「Authentication Failures」へ、A09 は「Monitoring」から「Alerting」へ名称変更 — [Top 10:2025 Introduction](https://top10.owasp.org/2025/0x00_2025-Introduction/)
- ASVS 5.0 の章立て: V1 Encoding and Sanitization, V2 Validation and Business Logic, V3 Web Frontend Security, V4 API and Web Service, V5 File Handling, V6 Authentication, V7 Session Management, V8 Authorization, V9 Self-contained Tokens, V10 OAuth and OIDC, V11 Cryptography, V12 Secure Communication, V13 Configuration, V14 Data Protection, V15 Secure Coding and Architecture, V16 Security Logging and Error Handling, V17 WebRTC — [OWASP ASVS GitHub 5.0/en](https://github.com/OWASP/ASVS/tree/master/5.0/en)
- ASVS 5.0.0 の公開は2025年5月（Global AppSec EU Barcelona）。要件は約350件・3レベル。要件IDは `v5.0.0-<章>.<節>.<項>` 形式で、バージョン付きの引用が推奨されている — [Appknox](https://www.appknox.com/cyber-security-jargons/owasp-asvs) / [Security Compass](https://www.securitycompass.com/blog/what-is-owasp-asvs/)（どちらも二次情報）
- OWASP Code Review Guide v2.0 のRC公開は2017年で、2017年8月に最終版の予定とされていた。これ以降の更新は確認できなかった — [OWASP wiki: Code Review Guide V2.0 Roadmap](https://wiki.owasp.org/index.php/Projects/OWASP_Code_Review_Project/Releases/Code_Review_Guide_V2.0/Roadmap)
- IPA「安全なウェブサイトの作り方」の最新は改訂第7版（2021-03-31）。対象はSQLi、OSコマンド、パス名パラメータ/ディレクトリトラバーサル、セッション管理、XSS、CSRF、HTTPヘッダインジェクション、メールヘッダインジェクション、クリックジャッキング、バッファオーバーフロー、アクセス制御/認可制御の欠落 — [IPA](https://www.ipa.go.jp/security/vuln/websecurity/about.html)

### OWASP Top 10:2025 → ASVS 5.0 → 差分パターン対応表
| Top 10:2025 | ASVS 5.0 章 | Rails 差分パターン | TS/ブラウザ 差分パターン |
|---|---|---|---|
| A01 Broken Access Control（+SSRF） | V8, V4 | `Model.find(params[:id])` にスコープがない、`before_action` の skip、Pundit の `authorize` 漏れ、ユーザー指定URLへの `Net::HTTP`/`Faraday` | Server Action/route handler の中で認可していない、クライアント側の `isAdmin` 判定だけに頼っている |
| A02 Security Misconfiguration | V13, V12, V3 | `config.force_ssl`、`config.hosts`、CSPの緩和、CORSの `*`、`protect_from_forgery` の除外 | `next.config` の headers/CSP、`allowedOrigins`、`*` CORS |
| A03 Software Supply Chain Failures | V15（依存管理） | `Gemfile`/`Gemfile.lock` への新規gem、`source` やgit参照の変更 | `package.json`/lockfile の変更、`postinstall`/`preinstall`、新しいレジストリ |
| A04 Cryptographic Failures | V11, V14 | 独自暗号、MD5/SHA1（Brakeman "Weak Hash"）、`secret_key_base` の直書き | `Math.random()` でトークン生成、秘密値をバンドルに含める |
| A05 Injection（XSS含む） | V1, V2 | `where("... #{}")`、`html_safe`/`raw`、`system`/バッククォート、`render inline:` | `dangerouslySetInnerHTML`、`innerHTML`、`eval`、`javascript:` URL |
| A06 Insecure Design | V2, V15 | 業務ロジックの抜け（価格・数量・状態遷移）、レート制限がない | クライアントだけで検証している |
| A07 Authentication Failures | V6, V7, V9, V10 | ログイン後に `reset_session` がない、`rate_limit` がない、トークン比較が非定数時間 | localStorage へのトークン保存、JWT の `alg` 検証 |
| A08 Integrity Failures | V15, V9 | `Marshal.load`/`YAML.load`、署名のないcookie、Webhook署名の未検証 | SRIなしのCDNスクリプト、未検証の `postMessage` |
| A09 Logging & Alerting | V16, V14 | `filter_parameters` の未更新、PII のログ出力、監査ログの欠如 | `console.log` へのトークン出力、Sentry へのPII送信 |
| A10 Exceptional Conditions | V16, V15 | `rescue => e` の握り潰し、fail-open の認可（例外時に許可）、詳細なエラー表示 | `catch {}` で認可失敗を無視、エラーメッセージからの情報漏洩 |

### Inferences
- PRレビューの観点表には Top 10:2025 の番号を「分類ラベル」として付け、具体的な判定基準は ASVS 5.0 の章で引くと運用しやすい。Code Review Guide v2.0 は2017年の内容なので、主要な参照元にはしないほうがよい。
- A10（Exceptional Conditions）は新カテゴリだが、差分レビューで最も判定しやすい。`rescue`/`catch` の握り潰しや、例外発生時に認可を素通りさせるコードは差分だけで指摘できる。
- 上表の A04/A08/A10 列にある `Math.random`、JWT `alg`、SRI、fail-open などは一般的な知見にもとづいて割り当てたもので、OWASP 原文との1対1対応はまだ確認していない。

### Gaps
- Top 10:2025 の正式リリース日と、RC ではなく最終版かどうかは、公式ページで確認できなかった。ページには "2025 version" とだけ記載されている。2025年11月にRCが出た記憶はあるが、未検証。
- ASVS 5.0 の各要件ID（例: v5.0.0-8.2.1）とチェック項目の個別対応はまだ作れていない。

## Q2. Rails 固有の観点（Brakeman を含む）

### Takeaway
最優先は認可漏れ（IDOR、スコープなしの `find`）。Rails には IDOR に対する組み込みの防御がない。その次が SQLi（文字列補間）、XSS（`html_safe`/`raw`、`link_to` に渡される `javascript:` URL）、オープンリダイレクト、コマンド実行と危険な `send`/`constantize`、デシリアライズ。Rails 7.0 以降の `redirect_to` は外部ホストへのリダイレクトを既定で拒否するので、差分では `allow_other_host: true` の追加を探すのが効率的。Brakeman は31種の警告を出すが、認可ロジックや業務ロジックの欠陥は検出できない。

### Cited Findings
- Rails は IDOR に対する組み込み保護を持たない。コントローラで認可するか、CanCanCan/Pundit を使う — [OWASP Rails Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Ruby_on_Rails_Cheat_Sheet.html)
- SQLi の脆弱な例は `Project.where("name like '" + name + "'")`、安全な例は `where("name like ?", "%#{ActiveRecord::Base.sanitize_sql_like(params[:name])}%")` — [OWASP Rails Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Ruby_on_Rails_Cheat_Sheet.html)
- `find`/`find_by` は自動でエスケープされるが、`where` の文字列フラグメント、`find_by_sql`、`connection.execute` は手動で保護する必要がある。プレースホルダ（`?`、`:name`）かハッシュ条件を使う — [Rails Security Guide](https://guides.rubyonrails.org/security.html)
- XSS: `raw`、`<%== %>`、`.html_safe` は自動エスケープを迂回する。`link_to "...", @user.website` は `javascript:` URL を許してしまう（スキームの許可リストがない）。`sanitize` には繰り返し欠陥が見つかっており、完全な解決策ではない — [OWASP Rails Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Ruby_on_Rails_Cheat_Sheet.html)
- `sanitize()` を使うなら `tags`/`attributes` を許可リストで指定する。ビューを通さないAjax応答はコントローラ側でエスケープする — [Rails Security Guide](https://guides.rubyonrails.org/security.html)
- コマンドインジェクション: `eval`、`system`、バッククォート、`exec`、`spawn`、`IO.popen` にユーザー入力を渡さない。どうしても必要なら許可リストで検証する — [OWASP Rails Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Ruby_on_Rails_Cheat_Sheet.html)
- 動的レンダーパス: `render` のテンプレート名やパーシャル名にユーザー入力を使わない — [OWASP Rails Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Ruby_on_Rails_Cheat_Sheet.html)
- オープンリダイレクト: `redirect_to params[:to]` は危険。`redirect_to url_from(params[:url]) || "/"` を使う。`URI.parse(v).path` による検証は `//evil.example` で破られる。正規表現で検証するなら `^`/`$` ではなく `\A`/`\z` を使う — [OWASP Rails Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Ruby_on_Rails_Cheat_Sheet.html)
- `redirect_to` は既定で外部ホストへのリダイレクトを拒否する。`allow_other_host: true` を付けると無効になり、公式ドキュメントは「ユーザー指定のパラメータと組み合わせるのは unsafe」と明記している。`action_on_open_redirect` は `:log`/`:notify`/`:raise` から選べる。`action_on_path_relative_redirect` は `example.com` や `@attacker.com` のような先頭スラッシュなしのURLを検知する。`url_from` はホストが完全一致しなければ `nil` を返す。`redirect_back_or_to` の referer に対する `allow_other_host` は既定 true（Rails 8.1.4 のドキュメント） — [Rails API: ActionController::Redirecting](https://api.rubyonrails.org/classes/ActionController/Redirecting.html)
- リダイレクト先に `data:` URL を許可しない — [Rails Security Guide](https://guides.rubyonrails.org/security.html)
- CSRF: `protect_from_forgery with: :exception` を使い、新規アプリでは `default_protect_from_forgery` で有効になる。状態を変える処理を GET で受けない。レイアウトに `csrf_meta_tags` を置く。XSS があると CSRF 対策は迂回される — [Rails Security Guide](https://guides.rubyonrails.org/security.html)
- `protect_from_forgery except: :show` のような除外は意図的なものか確認する。トークン認証だけなら CSRF 対策は不要だが、cookie を使う経路では必要 — [OWASP Rails Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Ruby_on_Rails_Cheat_Sheet.html)
- `send_file`: `params` をパスに連結しない。パスを展開して想定ディレクトリ内にあるか確認するか、DB上のIDからファイル名を決める。アップロードファイル名は許可文字リストでフィルタし、`/public` 配下（ドキュメントルート）に保存しない — [Rails Security Guide](https://guides.rubyonrails.org/security.html)
- セッション: ログイン後に `reset_session` を呼ぶ（固定化対策）。cookie に機密を入れない（約4KB、クライアントが制御できる）。サーバー側で有効期限を管理する。`config.force_ssl = true` で HTTPS と HSTS を有効にする — [Rails Security Guide](https://guides.rubyonrails.org/security.html)
- CookieStore はサーバー側で失効しないため、リプレイが可能。機密情報はセッションに入れず、必要に応じて `:active_record_store` を使う — [OWASP Rails Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Ruby_on_Rails_Cheat_Sheet.html)
- レート制限: `rate_limit to: 10, within: 3.minutes, only: :create`（SessionsController の例）。パスワードリセット画面では汎用的なメッセージを返す — [Rails Security Guide](https://guides.rubyonrails.org/security.html)
- `rate_limit` は Rails 7.2 で導入された。Rails 8 の認証ジェネレータはログインとパスワードリセットだけを生成し、認可、監査ログ、2FA、不正利用対策はアプリ側の責任 — [Saeloun 2026-04-28](https://blog.saeloun.com/2026/04/28/rails-security-best-practices-a-comprehensive-guide/) / [Rails Security Guide](https://guides.rubyonrails.org/security.html)
- `filter_parameters` は部分一致の正規表現で、既定値に `:passw`, `:secret`, `:token` を含む — [Rails Security Guide](https://guides.rubyonrails.org/security.html)
- 機密ファイル: `config/database.yml`、`secret_token.rb`、`db/seeds.rb`（初期管理者アカウント）、`*.sqlite3` に注意。本番の秘密情報は `config/credentials.yml.enc` に置く — [OWASP Rails Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Ruby_on_Rails_Cheat_Sheet.html) / [Rails Security Guide](https://guides.rubyonrails.org/security.html)
- ルーティング: `match ':controller(/:action(/:id(.:format)))'` のようなキャッチオールルートは全ての public メソッドを公開してしまう — [OWASP Rails Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Ruby_on_Rails_Cheat_Sheet.html)
- CORS: `rack-cors` で origin、ヘッダ、メソッドを明示的な許可リストにする — [OWASP Rails Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Ruby_on_Rails_Cheat_Sheet.html)
- Host Authorization は development では既定で有効だが、それ以外の環境では `config.hosts` を自分で設定する必要がある。`perform_deep_munge = false` は危険 — [Rails Security Guide](https://guides.rubyonrails.org/security.html)
- CSP は `config/initializers/content_security_policy.rb` で設定する。コントローラ単位の `content_security_policy false` による無効化に注意 — [Rails Security Guide](https://guides.rubyonrails.org/security.html)
- Brakeman の警告種別（31種）: Attribute Restriction, Authentication, Basic Authentication, Command Injection, CSRF, XSS, XSS (Content Tag), XSS (JSON), Dangerous Evaluation, Dangerous Send, Default Routes, Denial of Service, Divide By Zero, Dynamic Render Paths, File Access, Format Validation, Information Disclosure, Mail Link, Mass Assignment, Path Traversal, Remote Code Execution, Remote Execution in YAML.load, Session Manipulation, Session Settings, SQL Injection, SSL Verification Bypass, Unmaintained Dependencies, Unsafe Deserialization, Unscoped Find, Unsafe Redirects, Weak Hash — [Brakeman Warning Types](https://brakemanscanner.org/docs/warning_types/)
- 本番CIでは tests、Brakeman、bundler-audit を回すことが推奨されている — [Saeloun](https://blog.saeloun.com/2026/04/28/rails-security-best-practices-a-comprehensive-guide/)

### Rails チェックリスト（優先度順）
| # | 観点（差分で探すパターン） | 重大度 | 判定 | OWASP | 出典 |
|---|---|---|---|---|---|
| R1 | `Model.find(params[:id])` / `find_by(id:)` が `current_user.xxx.find` や `policy_scope` を経由していない（IDOR、Brakeman "Unscoped Find"） | must | Ctx（所有関係とテナント設計） | A01 / V8 | [Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Ruby_on_Rails_Cheat_Sheet.html), [Brakeman](https://brakemanscanner.org/docs/warning_types/) |
| R2 | 新しいアクションやコントローラに `authorize`（Pundit）/ `authorize!`・`load_and_authorize_resource`（CanCanCan）がない。`skip_before_action :authenticate_*` や `skip_authorization` が追加されている | must | Diff + Ctx（`verify_authorized` の有無） | A01 / V8 | [Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Ruby_on_Rails_Cheat_Sheet.html) |
| R3 | `params.permit!`、`permit(:role, :admin, :user_id, :owner_id, :price)` など権限やモデル所有に関わる属性の permit、`update(params[:x])` の直渡し（Brakeman "Mass Assignment"/"Attribute Restriction"） | must | Diff | A01 / V2, V8 | [Brakeman](https://brakemanscanner.org/docs/warning_types/) |
| R4 | `where("... #{...}")`、`order(params[:sort])`、`pluck("#{...}")`、`find_by_sql`/`execute`/`select`/`group`/`joins` への文字列補間。プレースホルダか許可リストに替える | must | Diff | A05 / V1 | [Rails Guide](https://guides.rubyonrails.org/security.html), [Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Ruby_on_Rails_Cheat_Sheet.html) |
| R5 | `html_safe` / `raw` / `<%==` / `content_tag` へのユーザー入力 / `sanitize` の許可リストの拡大 / `render inline:` / `render html:` | must | Diff | A05 / V1 | [Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Ruby_on_Rails_Cheat_Sheet.html), [Rails Guide](https://guides.rubyonrails.org/security.html) |
| R6 | `link_to` / `href` / `src` にユーザー指定のURLが入るのに http/https の許可リストがない（`javascript:`、`data:`） | must | Diff | A05 / V1, V3 | [Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Ruby_on_Rails_Cheat_Sheet.html) |
| R7 | `redirect_to params[...]`、`allow_other_host: true` の追加、`^...$` による検証、`URI.parse(...).path` による検証。`url_from` に替える | must | Diff | A01 / V15 | [Rails API](https://api.rubyonrails.org/classes/ActionController/Redirecting.html), [Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Ruby_on_Rails_Cheat_Sheet.html) |
| R8 | `system`/バッククォート/`%x`/`exec`/`spawn`/`IO.popen`/`Open3` に文字列でユーザー入力を渡している。`eval`/`instance_eval`/`class_eval` | must | Diff | A05 / V1 | [Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Ruby_on_Rails_Cheat_Sheet.html) |
| R9 | `params[:x].constantize` / `safe_constantize` / `send(params[:m])` / `public_send` / `try(params[...])`（Brakeman "Remote Code Execution"/"Dangerous Send"） | must | Diff | A05 / V15 | [Brakeman](https://brakemanscanner.org/docs/warning_types/) |
| R10 | `Marshal.load`、`YAML.load`（`safe_load` ではない）、`Oj.load` を外部データに使っている（Brakeman "Unsafe Deserialization"/"Remote Execution in YAML.load"） | must | Diff | A08 / V15 | [Brakeman](https://brakemanscanner.org/docs/warning_types/) |
| R11 | `send_file`/`File.read`/`File.open` のパスに `params` を連結している。展開後に基準ディレクトリ配下か検証していない（"Path Traversal"/"File Access"） | must | Diff | A01 / V5 | [Rails Guide](https://guides.rubyonrails.org/security.html) |
| R12 | `render params[:template]` / `render partial: params[...]`（"Dynamic Render Paths"） | must | Diff | A05 | [Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Ruby_on_Rails_Cheat_Sheet.html) |
| R13 | `protect_from_forgery` の削除や `except:`/`skip_forgery_protection` の追加。GET ルートで状態を変更している | must | Diff | A01 / V3 | [Rails Guide](https://guides.rubyonrails.org/security.html) |
| R14 | ユーザー指定のURLへのサーバー側HTTP（`Net::HTTP`、`Faraday`、`URI.open`、`open-uri`、画像取得、Webhook送信先）にホスト許可リストや内部IPの拒否がない（SSRF） | must | Diff + Ctx | A01（SSRF統合） | [Top10 Intro](https://top10.owasp.org/2025/0x00_2025-Introduction/) |
| R15 | `OpenSSL::SSL::VERIFY_NONE` / `verify: false`（"SSL Verification Bypass"） | must | Diff | A04 / V12 | [Brakeman](https://brakemanscanner.org/docs/warning_types/) |
| R16 | 秘密値の直書き（APIキー、`secret_key_base`、`database.yml` のパスワード）、`.env` や `master.key` のコミット | must | Diff | A02, A04 / V13 | [Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Ruby_on_Rails_Cheat_Sheet.html) |
| R17 | ログインやセッション変更の後に `reset_session` がない。`session[:...]` に機密を保存している。cookie の `httponly`/`secure`/`same_site` の弱体化 | should→must | Diff | A07 / V7 | [Rails Guide](https://guides.rubyonrails.org/security.html) |
| R18 | ログイン、パスワードリセット、OTP、招待、メール送信のエンドポイントに `rate_limit`（Rails 7.2+）や rack-attack がない | should | Ctx | A07, A06 / V6 | [Rails Guide](https://guides.rubyonrails.org/security.html) |
| R19 | 認証ジェネレータの生成コードを改変している（`allow_unauthenticated_access` の追加範囲、パスワードリセットトークンの有効期限、エラーメッセージでのユーザー列挙） | should | Diff + Ctx | A07 / V6 | [Saeloun](https://blog.saeloun.com/2026/04/28/rails-security-best-practices-a-comprehensive-guide/) |
| R20 | 正規表現での検証に `^`/`$` を使っている（`\A`/`\z` にすべき）（"Format Validation"） | should | Diff | A05 / V2 | [Rails Guide](https://guides.rubyonrails.org/security.html) |
| R21 | 新しいパラメータ名（`otp`、`ssn`、`card`、`api_key` など）が `filter_parameters` に含まれていない | should | Diff + Ctx | A09 / V16 | [Rails Guide](https://guides.rubyonrails.org/security.html) |
| R22 | CSP/CORS/`config.hosts`/`force_ssl` の緩和（`origins '*'`、`unsafe-inline`、`content_security_policy false`） | should | Diff | A02 / V3, V13 | [Rails Guide](https://guides.rubyonrails.org/security.html), [Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Ruby_on_Rails_Cheat_Sheet.html) |
| R23 | アップロード: content_type/拡張子の検証なし、`/public` への保存、ファイル名を無加工で使用、SVG/HTML を同一オリジンで inline 配信 | should | Diff + Ctx | A05, A08 / V5 | [Rails Guide](https://guides.rubyonrails.org/security.html) |
| R24 | MD5/SHA1 をパスワードやトークンに使っている。独自暗号。トークンを `==` で比較している（`secure_compare` を使うべき） | should | Diff | A04 / V11 | [Brakeman](https://brakemanscanner.org/docs/warning_types/), [Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Ruby_on_Rails_Cheat_Sheet.html) |
| R25 | キャッチオールルートや `resources` の過剰公開（`only:` の指定漏れ）（"Default Routes"） | should | Diff | A01 | [Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Ruby_on_Rails_Cheat_Sheet.html) |
| R26 | `rescue => e` で握り潰して処理を続行（fail-open）。本番で詳細なエラーを表示（`consider_all_requests_local`）（"Information Disclosure"） | should | Diff | A10 / V16 | [Top10](https://top10.owasp.org/2025), [Brakeman](https://brakemanscanner.org/docs/warning_types/) |
| R27 | ユーザー入力を正規表現やループ回数に使い、DoS につながる（"Denial of Service"） | nit→should | Diff | A06 | [Brakeman](https://brakemanscanner.org/docs/warning_types/) |

### Inferences
- Brakeman の警告は構文レベルの検出なので、IDOR の大半（`policy_scope` の誤り、テナント境界の漏れ）、業務ロジック、SSRF、レート制限の欠如は人間のレビューで見る必要がある。Brakeman を CI 必須にし、R1/R2/R14/R18 をレビュアーの重点項目にする分担が合理的。
- Rails 7.0 以降は `redirect_to` が既定で外部ホストへのリダイレクトを拒否するため、差分で検索すべき主な対象は `allow_other_host: true`。`redirect_back_or_to` は referer に対して既定 true なので注意する。
- Pundit の `after_action :verify_authorized` / `verify_policy_scoped` と、CanCanCan の `check_authorization` は認可漏れを検出する保険になる。これらが無効化されていないかは Ctx で確認する（Pundit/CanCanCan の公式ドキュメントは今回取得していない）。
- Active Storage には、クライアント申告の content_type を信用する問題や、SVG/HTML の inline 配信によるXSSリスクがあるとされる（Rails 側の `content_types_allowed_inline` などの設定）。今回は一次情報を取得していない。

### Gaps
- Rails 8.x で導入されたとされる CSRF 関連の新機能（Sec-Fetch-Site ヘッダによる検証など）は、Security Guide の取得範囲では確認できなかった。
- Rails 8 認証ジェネレータの具体的な既知の落とし穴（パスワードリセットトークン、タイミング攻撃など）について、一次情報の解説は見つからなかった。
- Brakeman の最新バージョン番号と、2025〜2026年に追加された警告種別は未確認。
- Pundit/CanCanCan、Active Storage、`YAML.safe_load` の一次ドキュメントは時間の都合で未取得。

## Q3. TypeScript/ブラウザ側の観点

### Takeaway
フロント側の must 項目は5つ。①HTML挿入シンク（`dangerouslySetInnerHTML`、`innerHTML`、`eval`）と `javascript:` URL、②`postMessage` の origin 検証、③トークンを localStorage に置かない、④`NEXT_PUBLIC_`/`VITE_` 経由で秘密値がバンドルに入ること、⑤Server Actions を公開 POST エンドポイントとみなし、内部で認証・認可・入力検証・戻り値の絞り込みを行うこと。RSC には React2Shell（CVE-2025-55182、CVSS 10.0、2025年12月）の前例があるため、React/Next.js のバージョンもレビュー対象に含める。

### Cited Findings
- `postMessage`: 第2引数に `*` ではなく明示的な origin を指定する。`event.origin` は完全一致で検証する（`indexOf(".owasp.org")` は `owasp.org.attacker.com` で破られる）。`event.data` を `eval`/`innerHTML` に渡さず、`textContent` を使う — [OWASP HTML5 Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/HTML5_Security_Cheat_Sheet.html)
- localStorage にセッションIDや機密データを保存しない。XSS が1つあれば読み書きされる — [OWASP HTML5 Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/HTML5_Security_Cheat_Sheet.html)
- CORS は特定 origin の許可リストにする（`*` や Origin のエコーバックはしない）。`target=_blank` には `rel="noopener noreferrer"` を付ける。信頼できないコンテンツは `sandbox` 付き iframe で表示する — [OWASP HTML5 Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/HTML5_Security_Cheat_Sheet.html)
- プロトタイプ汚染の対策: キー付きデータには `Map`/`Set` を使う、`Object.create(null)` を使う、組み込みプロトタイプを `Object.freeze` する、Node の `--disable-proto=delete`（多層防御）。`Object.seal` は不十分 — [OWASP Prototype Pollution Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Prototype_Pollution_Prevention_Cheat_Sheet.html)
- Vite: 「`VITE_` で始まる変数はバンドル後のクライアントソースに露出する」「`VITE_*` に API キーなどの機密を入れてはならない」。`.env.*.local` は `.gitignore` に入れる — [Vite: Env Variables and Modes](https://vite.dev/guide/env-and-mode)
- Next.js: `NEXT_PUBLIC_` の付いた環境変数はクライアントに露出する。`process.env` を読むのは Data Access Layer だけに限定する。`import 'server-only'` を使うと、クライアントから import されたときにビルドエラーになる。Taint API（`experimental_taintObjectReference`/`taintUniqueValue`）は追加の防御層 — [Next.js Data Security（2026-10-06 更新）](https://nextjs.org/docs/app/guides/data-security)
- Server Component から Client Component へ DB レコードをそのまま props で渡すと、全フィールドがクライアントに露出する。DTO で必要なフィールドだけ返す — [Next.js Data Security](https://nextjs.org/docs/app/guides/data-security)
- Server Actions は直接 POST で呼べるので、各アクションの中で認証・認可（所有権チェック = IDOR 対策）を行う。ページ側の認証チェックは Server Action には及ばない。戻り値はクライアントへシリアライズされるため、生の DB レコードを返さない。クロージャで捕捉した変数は暗号化されるが、暗号化だけに頼らない。Origin と Host を比較する CSRF 対策があり、`serverActions.allowedOrigins` で調整できる。レンダリング中に副作用（cookie 削除など）を起こさない — [Next.js Data Security](https://nextjs.org/docs/app/guides/data-security)
- Next.js の監査ポイント: `"use client"` の props 型が広すぎないか、`"use server"` で入力検証・再認可・所有権チェック・戻り値の絞り込みをしているか、`[param]` フォルダ（ユーザー入力）を検証しているか、`proxy.ts`/`route.ts` を重点的に見る — [Next.js Data Security](https://nextjs.org/docs/app/guides/data-security)
- `searchParams.isAdmin` のようなクライアント値で権限を判定しない — [Next.js Data Security](https://nextjs.org/docs/app/guides/data-security)
- React2Shell（CVE-2025-55182）: RSC の Flight プロトコルに起因する認証不要の RCE で、CVSS 10.0。修正版は react-server-dom 19.0.3/19.1.4/19.2.3、Next.js 15.0.5/15.1.9/15.2.6/15.3.6/15.4.8/15.5.7/16.0.7。2025-12-05 から悪用が観測された — [Zscaler](https://www.zscaler.com/jp/blogs/security-research/react2shell-remote-code-execution-vulnerability-cve-2025-55182), [Wiz](https://www.wiz.io/ja-jp/blog/critical-vulnerability-in-react-cve-2025-55182), [Rapid7](https://rapid7.com/blog/post/etr-react2shell-cve-2025-55182-critical-unauthenticated-rce-affecting-react-server-components)
- Rails 側の `link_to` と同じく、ユーザー指定のURLを属性に入れるなら http/https の許可リストが必要 — [OWASP Rails Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Ruby_on_Rails_Cheat_Sheet.html)

### TypeScript/ブラウザ チェックリスト
| # | 観点 | 重大度 | 判定 | OWASP | 出典 |
|---|---|---|---|---|---|
| T1 | `dangerouslySetInnerHTML` / `innerHTML` / `outerHTML` / `insertAdjacentHTML` / `document.write` にユーザー由来の値が入る。必要なら DOMPurify などでサニタイズする | must | Diff | A05 / V1, V3 | [HTML5 CS](https://cheatsheetseries.owasp.org/cheatsheets/HTML5_Security_Cheat_Sheet.html) |
| T2 | `eval` / `new Function` / 文字列を渡す `setTimeout` | must | Diff | A05 | [HTML5 CS](https://cheatsheetseries.owasp.org/cheatsheets/HTML5_Security_Cheat_Sheet.html) |
| T3 | `href`/`src`/`window.location`/`router.push` にユーザー指定のURLを入れるときにスキームの許可リスト（http/https）がない（`javascript:`、オープンリダイレクト） | must | Diff | A05, A01 | [Rails CS](https://cheatsheetseries.owasp.org/cheatsheets/Ruby_on_Rails_Cheat_Sheet.html) |
| T4 | `addEventListener('message')` に `event.origin` の完全一致検証がない。`postMessage(x, '*')` | must | Diff | A08 / V3 | [HTML5 CS](https://cheatsheetseries.owasp.org/cheatsheets/HTML5_Security_Cheat_Sheet.html) |
| T5 | アクセストークン、リフレッシュトークン、セッションIDの `localStorage`/`sessionStorage` への保存（HttpOnly cookie を推奨） | must | Diff | A07 / V7, V3 | [HTML5 CS](https://cheatsheetseries.owasp.org/cheatsheets/HTML5_Security_Cheat_Sheet.html) |
| T6 | `NEXT_PUBLIC_*`/`VITE_*` に秘密値（APIシークレット、DB、署名鍵）を追加している。クライアントコードで `process.env.SECRET` を参照している | must | Diff | A02, A04 / V13 | [Vite](https://vite.dev/guide/env-and-mode), [Next.js](https://nextjs.org/docs/app/guides/data-security) |
| T7 | `'use server'` 関数の内部に認証・認可・所有権チェックがない（ページ側のチェックに依存している）。引数を zod などで検証していない | must | Diff | A01 / V8, V4 | [Next.js](https://nextjs.org/docs/app/guides/data-security) |
| T8 | Server Component から Client Component へ DB の行やユーザーオブジェクトを丸ごと渡している。Server Action が生レコードを返している。DTO や `server-only` を使っていない | must | Diff | A01 / V14 | [Next.js](https://nextjs.org/docs/app/guides/data-security) |
| T9 | `route.ts`/`proxy.ts`(middleware)/API ルートの認可漏れ。middleware だけで認可を完結させている | must | Ctx | A01 | [Next.js](https://nextjs.org/docs/app/guides/data-security) |
| T10 | React/Next.js のバージョンが既知の重大な CVE の修正版より古い（React2Shell など） | must | Diff（lockfile） | A03 | [Zscaler](https://www.zscaler.com/jp/blogs/security-research/react2shell-remote-code-execution-vulnerability-cve-2025-55182) |
| T11 | ユーザーJSONの deep merge や `obj[key] = value` の再帰代入で `__proto__`/`constructor` を除外していない。辞書に `{}` を使っている（`Map`/`Object.create(null)` を推奨） | should | Diff | A08, A05 | [Prototype Pollution CS](https://cheatsheetseries.owasp.org/cheatsheets/Prototype_Pollution_Prevention_Cheat_Sheet.html) |
| T12 | CSP の緩和（`unsafe-inline`/`unsafe-eval` の追加、nonce の撤去）。`serverActions.allowedOrigins` へのワイルドカード追加 | should | Diff | A02 / V3 | [Next.js](https://nextjs.org/docs/app/guides/data-security), [Rails Guide](https://guides.rubyonrails.org/security.html) |
| T13 | SSR で `<script>` に JSON を埋め込む際（`JSON.stringify` の値をそのまま `dangerouslySetInnerHTML`）に `</script>` や `<` をエスケープしていない | should | Diff | A05 | （一次情報は未取得: Inference 参照） |
| T14 | `target="_blank"` に `rel="noopener noreferrer"` がない（`window.open` も同様） | nit | Diff | A05 / V3 | [HTML5 CS](https://cheatsheetseries.owasp.org/cheatsheets/HTML5_Security_Cheat_Sheet.html) |
| T15 | 信頼できない埋め込みに `sandbox` 属性のない iframe を使っている | should | Diff | V3 | [HTML5 CS](https://cheatsheetseries.owasp.org/cheatsheets/HTML5_Security_Cheat_Sheet.html) |
| T16 | クライアント側だけで権限判定や入力検証をしている（`searchParams.isAdmin`、UI 非表示だけによる制御） | must | Diff + Ctx | A01, A06 | [Next.js](https://nextjs.org/docs/app/guides/data-security) |
| T17 | `console.log` やエラー監視（Sentry など）へのトークンや PII の出力 | should | Diff | A09 / V16 | （Q5 参照） |

### Inferences
- React は JSX の `{}` 補間を自動でエスケープするが、`href={userUrl}` の `javascript:` スキームは防げない（React 19 で警告やブロックが入ったとされるが未確認）。そのためT3は引き続き must 扱いが妥当。
- SSR で状態を埋め込むときのXSS（T13）は、Rails の `json_escape`/`j` 相当の問題で、一般によく知られた手法だが今回は一次情報を取得していない。
- Rails をAPIとして使い、TS SPA が cookie セッションで呼ぶ構成では、Rails 側の CSRF 対策（`X-CSRF-Token` ヘッダ）と CORS の `credentials` 設定の組み合わせを Ctx で確認する必要がある。

### Gaps
- React 19.x における `javascript:` URL の扱い（警告かブロックか）について、公式の記述を確認できていない。
- React2Shell 以降（2026年）の RSC/Next.js の重大な CVE は調査していない。

## Q4. サプライチェーン（依存追加、lockfile、タイポスクワッティング、2024〜2026年の事例）

### Takeaway
2025年9月の Shai-Hulud（chalk/debug の乗っ取りを含め500以上のパッケージ）以降、npm では自己増殖ワームが繰り返し発生している。2026年にも、TanStack 等（5月）、node-gyp/Miasma（6月）、ChainDrop（8月、400以上）が続いた。ChainDrop では、正規の GitHub Actions/OIDC 経由で公開されたため、悪性版にも有効な provenance が付いていた。つまり provenance だけでは安全を保証できない。RubyGems でも2026年に休眠アカウントや古いgemの乗っ取り（SleeperGem）と、レジストリを流出経路に使う悪用（GemStuffer）が起きている。PRレビューでは、新規依存の妥当性、lockfile の想定外の変更、install scripts、公開直後のバージョンを見る。

### Cited Findings
- Shai-Hulud（CISA アラート 2025-09-23）: 自己増殖ワームが500以上のパッケージを侵害した。GitHub PAT と AWS/GCP/Azure キーを窃取し、npm に再公開して拡散した。推奨対策は、依存関係のレビュー、ネストした依存まで含めた lockfile の確認、アーティファクトキャッシュの確認、2025-09-16 以前の安全版へのピン留め、認証情報の即時ローテーション — [CISA](https://www.cisa.gov/news-events/alerts/2025/09/23/widespread-supply-chain-compromise-impacting-npm-ecosystem)
- 2025-09-08 に chalk/debug（それぞれ週2.5億DL超）の侵害が報告された。GitHub は npm 対策として、ローカル公開時の MFA 必須化と granular token の有効期限7日化を計画した — [Pulsedive](https://blog.pulsedive.com/npm-compromise-the-wrath-of-the-shai-hulud-supply-chain-attack/)（二次情報）
- TanStack / Mistral AI / UiPath などで、npm と PyPI の160以上のパッケージが侵害された（2026-05-12 公表）。GitHub Actions の弱点を連鎖させてリリース資格情報を奪取した — [Orca Security](https://orca.security/resources/blog/tanstack-npm-supply-chain-worm/)
- node-gyp / "Miasma"（2026年6月）: 57パッケージ。npm、GitHub、クラウド、Vault、K8s の資格情報を窃取し、他メンテナのアカウントで再公開して拡散した — [Snyk](https://snyk.io/blog/node-gyp-supply-chain-compromise-self-propagating-npm-worm-binding-gyp/)
- ChainDrop（2026年8月、Microsoft 2026-08-04）: keyv、flat-cache、cache-manager など400以上のパッケージ。`preinstall` で `setup.mjs` を実行し、Bun ベースのペイロードを起動した。多くの悪性版には対応するコミット、タグ、PR がなかった。GitHub OIDC 経由で公開された版は有効な provenance を持っていた。リポジトリに Claude/VS Code の設定ファイルを注入して永続化した。推奨対策は、npm CLI v12 の `min-release-age` の利用、lockfile と推移的依存の確認、ピン留め、キャッシュのパージ、クリーンな端末からの資格情報ローテーション、トークンスコープ・ワークフロー承認・保護環境の見直し — [Microsoft Security Blog](https://www.microsoft.com/en-us/security/blog/2026/08/04/chaindrop-supply-chain-compromise-anatomy-self-propagating-worm/)
- ChainDrop の規模は報告によって異なる: Aikido は444パッケージ/1381バージョン（8/5 時点）、BleepingComputer は1,300超、Microsoft は400超 — [Aikido](https://www.aikido.dev/blog/keyv-and-friends-compromised-in-npm-supply-chain-attack), [BleepingComputer](https://www.bleepingcomputer.com/news/security/massive-chaindrop-npm-supply-chain-attack-infects-hundreds-of-packages/)
- シンガポール CSA も Keyv 関連の Shai-Hulud について注意喚起を出している（AD-2026-009） — [CSA Singapore](https://www.csa.gov.sg/alerts-and-advisories/advisories/ad-2026-009/)
- SleeperGem（2026年7月）: git_credential_manager、Dendreo、fastlane プラグインの悪性版。ローダーとして2段目を取得し、CI 環境では実行を回避し、開発者端末に常駐デーモンを仕込む。git_credential_manager は累計57.4万DL以上。2017〜2018年に公開された古いgemが乗っ取られたとみられる — [StepSecurity](https://www.stepsecurity.io/blog/sleepergem-compromised-rubygems-drop-persistent-backdoor), [The Hacker News](https://thehackernews.com/2026/07/sleepergem-uses-three-malicious.html)
- GemStuffer（2026年5月）: 150以上のgemが RubyGems をデータ流出経路として使っていた（Socket 報告）。RubyGems は一時的に新規アカウント登録を停止したと報じられている（関連は不明） — [The Hacker News Ruby ラベル](https://thehackernews.com/search/label/Ruby)（AI エージェントが実行したという Rescana の主張は単独ソースで未検証）
- Brakeman には "Unmaintained Dependencies" 警告がある。CI で bundler-audit を回すことが推奨されている — [Brakeman](https://brakemanscanner.org/docs/warning_types/), [Saeloun](https://blog.saeloun.com/2026/04/28/rails-security-best-practices-a-comprehensive-guide/)

### サプライチェーン チェックリスト
| # | 観点 | 重大度 | 判定 | 出典 |
|---|---|---|---|---|
| S1 | 新規依存（gem/npm）の追加理由、メンテナンス状況、DL数、公開者、名前の綴り（タイポスクワッティングやスコープの紛らわしさ）。標準ライブラリや既存依存で代替できないか | must（新規追加時） | Diff + 外部確認 | [CISA](https://www.cisa.gov/news-events/alerts/2025/09/23/widespread-supply-chain-compromise-impacting-npm-ecosystem) |
| S2 | lockfile（`package-lock.json`/`pnpm-lock.yaml`/`yarn.lock`/`Gemfile.lock`）に、manifest の変更と対応しない差分がある（推移的依存の大量更新、`resolved` URL やレジストリの変更、integrity hash の変化） | must | Diff | [CISA](https://www.cisa.gov/news-events/alerts/2025/09/23/widespread-supply-chain-compromise-impacting-npm-ecosystem), [Microsoft](https://www.microsoft.com/en-us/security/blog/2026/08/04/chaindrop-supply-chain-compromise-anatomy-self-propagating-worm/) |
| S3 | `preinstall`/`postinstall`/`install` スクリプトを持つ依存の追加。自プロジェクトの `package.json` scripts の変更。`.npmrc` の `ignore-scripts` の撤回 | must | Diff | [Microsoft](https://www.microsoft.com/en-us/security/blog/2026/08/04/chaindrop-supply-chain-compromise-anatomy-self-propagating-worm/) |
| S4 | 公開から数日以内のバージョンへの更新（ワームの多くは数時間〜数日で検知される）。`min-release-age` などのクールダウン設定を推奨 | should | Diff + 外部確認 | [Microsoft](https://www.microsoft.com/en-us/security/blog/2026/08/04/chaindrop-supply-chain-compromise-anatomy-self-propagating-worm/) |
| S5 | `Gemfile` の `git:`/`github:`/`path:` ソースや、`source` に追加された非公式レジストリ。npm の `git+https`/tarball URL 依存 | must | Diff | [CISA](https://www.cisa.gov/news-events/alerts/2025/09/23/widespread-supply-chain-compromise-impacting-npm-ecosystem) |
| S6 | バージョン指定の緩和（`^`/`*`/`>=`/`latest`）。lockfile のコミット漏れ | should | Diff | [CISA](https://www.cisa.gov/news-events/alerts/2025/09/23/widespread-supply-chain-compromise-impacting-npm-ecosystem) |
| S7 | GitHub Actions の変更: `pull_request_target` と PR コードの checkout、`permissions` の拡大、SHA ピン留めなしの third-party action、`id-token: write`、公開ワークフローの承認や保護環境の撤去 | must | Diff | [Orca](https://orca.security/resources/blog/tanstack-npm-supply-chain-worm/), [Microsoft](https://www.microsoft.com/en-us/security/blog/2026/08/04/chaindrop-supply-chain-compromise-anatomy-self-propagating-worm/) |
| S8 | リポジトリへの不審な AI エージェントや IDE の設定ファイル（`.claude/`、`.vscode/` の tasks/settings）の追加 | should | Diff | [Microsoft](https://www.microsoft.com/en-us/security/blog/2026/08/04/chaindrop-supply-chain-compromise-anatomy-self-propagating-worm/) |
| S9 | 既知の脆弱性を持つバージョンの導入（`npm audit`/bundler-audit/Brakeman "Unmaintained Dependencies" の CI 結果） | must（Critical/High） | Diff + CI | [Brakeman](https://brakemanscanner.org/docs/warning_types/), [Saeloun](https://blog.saeloun.com/2026/04/28/rails-security-best-practices-a-comprehensive-guide/) |
| S10 | CDN から読み込む `<script>` に SRI（`integrity`）がない | should | Diff | （Inference） |

### Inferences
- ChainDrop では provenance が有効だったことから、「provenance あり」を安全の根拠にしてはいけない。provenance は「どのワークフローでビルドされたか」を示すだけで、ワークフロー自体が乗っ取られれば意味をなさない。
- SleeperGem のように CI では発火せず開発者端末でだけ動くマルウェアもあるため、CI のスキャンが通っていても依存追加の妥当性レビュー（S1）は省けない。
- タイポスクワッティングの判定は差分だけでは難しい。新規パッケージ名はレジストリのページ（公開日、メンテナ、DL数、リポジトリとの対応）を確認する手順を、レビュー規約に明記するのが現実的。Socket などの PR 自動コメントツールで補完できる。

### Gaps
- npm CLI v12 の `min-release-age` の正式な仕様や既定値、pnpm/yarn の同等機能（`minimumReleaseAge` など）の一次ドキュメントは未取得。
- npm の trusted publishing / granular token 7日制限の実施状況（2026年10月時点）は未確認。
- 2024年の事例（xz-utils、rspack など）と RubyGems 側の公式インシデント報告（rubygems.org blog）は今回カバーできていない。
- SleeperGem の侵害手口（休眠アカウントの乗っ取りか）は報告によって一致していない。

## Q5. プライバシー/PII とログ

### Takeaway
Rails の `filter_parameters` は部分一致の正規表現で、既定で `passw`/`secret`/`token` を含む。新しい機密パラメータ名がこれに当たらない場合は追記が必要。ASVS 5.0 では V14 Data Protection と V16 Security Logging and Error Handling が該当し、Top 10:2025 では A09 Logging & **Alerting** Failures が該当する。Next.js 側は、DTO で必要なフィールドだけ返すことが、PII がクライアントに漏れることへの主な対策になる。

### Cited Findings
- `config.filter_parameters << :password`。部分一致の正規表現で、既定値は `:passw, :secret, :token` を含む — [Rails Security Guide](https://guides.rubyonrails.org/security.html)
- cookie やセッションに機密データを入れない — [Rails Security Guide](https://guides.rubyonrails.org/security.html), [OWASP Rails Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Ruby_on_Rails_Cheat_Sheet.html)
- `db/development.sqlite3` に実データが入りうる。`db/seeds.rb` に管理者アカウントが入りうる — [OWASP Rails Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Ruby_on_Rails_Cheat_Sheet.html)
- ASVS 5.0 の V14 Data Protection と V16 Security Logging and Error Handling — [ASVS 5.0](https://github.com/OWASP/ASVS/tree/master/5.0/en)
- A09 は「Security Logging & Alerting Failures」に名称変更された（監視からアラートへ重点が移った） — [Top 10 2025 Intro](https://top10.owasp.org/2025/0x00_2025-Introduction/)
- 電話番号などはプライバシールールに従って閲覧者ごとに出し分け、必要なフィールドだけを DTO で返す（W3C の API Minimization の考え方） — [Next.js Data Security](https://nextjs.org/docs/app/guides/data-security)
- 認証ジェネレータの範囲外として、監査ログはアプリ側の責任 — [Saeloun](https://blog.saeloun.com/2026/04/28/rails-security-best-practices-a-comprehensive-guide/)

### PII/ログ チェックリスト
| # | 観点 | 重大度 | 判定 | 出典 |
|---|---|---|---|---|
| P1 | `Rails.logger`/`puts`/`console.log`/APM/Sentry にパスワード、トークン、カード番号、マイナンバー、健康情報を出力している。`params.inspect` や `to_json` をログに出している | must | Diff | [Rails Guide](https://guides.rubyonrails.org/security.html) |
| P2 | 新しい機密パラメータやカラムが `filter_parameters` に入っていない（`otp`, `pin`, `ssn`, `card_number`, `dob` など。`passw`/`secret`/`token` に部分一致しないもの） | should | Diff + Ctx | [Rails Guide](https://guides.rubyonrails.org/security.html) |
| P3 | API レスポンスやシリアライザ（`as_json`, jbuilder, `render json: @user`）、Server Action の戻り値が PII や内部フィールド（`password_digest`, `*_token`, `email` など）を丸ごと返している | must | Diff | [Next.js](https://nextjs.org/docs/app/guides/data-security) |
| P4 | PII を URL クエリ、GET パラメータ、Referer で送っている（アクセスログや外部サービスに残る） | should | Diff | [HTML5 CS](https://cheatsheetseries.owasp.org/cheatsheets/HTML5_Security_Cheat_Sheet.html)（Referrer-Policy） |
| P5 | 機密カラムの暗号化（Active Record Encryption など）や保持期間・削除処理の欠如。新しい PII カラムの追加時に分類・暗号化・削除の方針があるか | should | Ctx | [ASVS V14](https://github.com/OWASP/ASVS/tree/master/5.0/en) |
| P6 | 認証の成功・失敗や権限変更など、重要操作の監査ログがない。ログインジェクション（改行の混入）への対処がない | should | Ctx | [ASVS V16](https://github.com/OWASP/ASVS/tree/master/5.0/en), [Saeloun](https://blog.saeloun.com/2026/04/28/rails-security-best-practices-a-comprehensive-guide/) |
| P7 | テスト、seed、fixture、スクリーンショットへの実データの混入。`.sqlite3` のコミット | must | Diff | [Rails CS](https://cheatsheetseries.owasp.org/cheatsheets/Ruby_on_Rails_Cheat_Sheet.html) |
| P8 | エラーメッセージで、ユーザーの存在（列挙）、スタックトレース、SQL を露出している | should | Diff | [Rails Guide](https://guides.rubyonrails.org/security.html)（汎用メッセージ）, [Brakeman "Information Disclosure"](https://brakemanscanner.org/docs/warning_types/) |

### Inferences
- Rails の `filter_attributes`（`ActiveRecord::Base.filter_attributes`、`inspect` 時のマスク）は `filter_parameters` と連動すると理解しているが、今回は一次ドキュメントを取得していない。
- 日本の個人情報保護法（漏えい時の報告義務など）を踏まえると、PII のログ出力（P1）は社内規定上 must 扱いが妥当と考える。法令の一次情報は今回の範囲外。

### Gaps
- ASVS 5.0 の V14 と V16 の個別要件文（ログに含めてはならないデータの定義など）は未取得。
- フロントエンドのエラー監視 SDK（Sentry など）の PII スクラビング設定の一次ドキュメントは未取得。
- 日本語資料のうち、徳丸本（『体系的に学ぶ 安全なWebアプリケーションの作り方 第2版』）関連の一次情報は取得できなかった。IPA の資料は2021年版が最新で、Top 10:2025 の新カテゴリ（サプライチェーン、例外処理）はカバーしていない。
