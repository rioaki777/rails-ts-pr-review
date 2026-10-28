# check-security チェックリスト

このファイルは scripts/extract_checklists.py で docs/research/report.md から生成。直接編集しない。

凡例は次のとおり。**既定**は重要度の初期値で、must はマージ前に必須、should は強く推奨（理由があれば見送り可）、nit は任意を表す。検証段階で上げ下げできる。**判定**は、指摘に必要な情報の範囲を表す。diff は差分だけで判断できる、repo は呼び出し元・スキーマ・設定・lint 設定などリポジトリ文脈が必要、PR は PR 説明やチケットが必要、実行は実機・CI 結果・本番統計・外部レジストリが必要、という意味だ。判定が「実行」の項目は静的レビューでは確定できないので、カバレッジ報告で「人間による確認が必要」と明示する。出典が「慣行」の項目は、権威ある単一の一次情報が見つからなかったものだ。

| # | 観点 | 既定 | 判定 | 出典 |
|---|---|---|---|---|
| SEC1 | IDOR：`Model.find(params[:id])` や `find_by(id:)` が `current_user.xxx` や `policy_scope` を経由していない | must | repo | [Rails CS](https://cheatsheetseries.owasp.org/cheatsheets/Ruby_on_Rails_Cheat_Sheet.html); [Brakeman](https://brakemanscanner.org/docs/warning_types/) |
| SEC2 | 認可の漏れ：新しいアクションに `authorize` がない。`skip_before_action :authenticate_*` や `skip_authorization` が追加されている。`'use server'` 関数、`route.ts`、`proxy.ts` の中で認証・認可・所有権チェックをしていない（ページ側のチェックは Server Action に及ばない） | must | diff+repo | 同上; [Next.js Data Security](https://nextjs.org/docs/app/guides/data-security) |
| SEC3 | クライアント側だけで権限を判定している（`searchParams.isAdmin`、UI の非表示だけで制御） | must | diff+repo | [Next.js Data Security](https://nextjs.org/docs/app/guides/data-security) |
| SEC4 | Mass assignment：`permit!`、`role`/`admin`/`user_id`/`price` の permit、`update(params[:x])` の直渡し | must | diff | [Brakeman](https://brakemanscanner.org/docs/warning_types/) |
| SEC5 | SQL インジェクション：`where`/`order`/`pluck`/`find_by_sql`/`execute`/`group`/`joins` への文字列補間 | must | diff | [Rails Security Guide](https://guides.rubyonrails.org/security.html) |
| SEC6 | XSS シンク：`html_safe`、`raw`、`<%==`、`render inline:`、`sanitize` の許可リスト拡大、`dangerouslySetInnerHTML`、`innerHTML`、`insertAdjacentHTML`、`document.write`、`eval`、`new Function` | must | diff | [Rails CS](https://cheatsheetseries.owasp.org/cheatsheets/Ruby_on_Rails_Cheat_Sheet.html); [HTML5 CS](https://cheatsheetseries.owasp.org/cheatsheets/HTML5_Security_Cheat_Sheet.html) |
| SEC7 | `link_to`/`href`/`src`/`window.location` にユーザー指定の URL を入れるのに、http/https の許可リストがない（`javascript:`、`data:`） | must | diff | [Rails CS](https://cheatsheetseries.owasp.org/cheatsheets/Ruby_on_Rails_Cheat_Sheet.html) |
| SEC8 | オープンリダイレクト：`redirect_to params[...]`、`allow_other_host: true` の追加、`^...$` や `URI.parse(...).path` による検証（`url_from` を使う） | must | diff | [Rails API Redirecting](https://api.rubyonrails.org/classes/ActionController/Redirecting.html) |
| SEC9 | コマンド実行・動的呼び出し：`system`、バッククォート、`exec`、`IO.popen`、`eval` へのユーザー入力。`params[:x].constantize`、`send(params[:m])` | must | diff | [Rails CS](https://cheatsheetseries.owasp.org/cheatsheets/Ruby_on_Rails_Cheat_Sheet.html); [Brakeman](https://brakemanscanner.org/docs/warning_types/) |
| SEC10 | 外部データに対する `Marshal.load`、`YAML.load`（`safe_load` ではない）、`Oj.load` | must | diff | [Brakeman](https://brakemanscanner.org/docs/warning_types/) |
| SEC11 | パストラバーサル・動的レンダー：`send_file`/`File.read` のパスへの `params` 連結、`render params[:template]` | must | diff | [Rails Security Guide](https://guides.rubyonrails.org/security.html) |
| SEC12 | SSRF：ユーザー指定の URL へのサーバー側 HTTP（Webhook の送信先、画像取得）に、ホスト許可リストや内部 IP の拒否がない | must | diff+repo | [Top 10:2025 Intro](https://top10.owasp.org/2025/0x00_2025-Introduction/) |
| SEC13 | CSRF：`protect_from_forgery` の削除や除外、GET での状態変更、`serverActions.allowedOrigins` へのワイルドカード追加 | must | diff | [Rails Security Guide](https://guides.rubyonrails.org/security.html); [Next.js](https://nextjs.org/docs/app/guides/data-security) |
| SEC14 | 秘密情報：API キーや `secret_key_base` の直書き、`master.key`/`.env` のコミット、平文の `config/*.yml`、`NEXT_PUBLIC_*`/`VITE_*` への秘密値、ドキュメント内の実トークン | must | diff | [Rails CS](https://cheatsheetseries.owasp.org/cheatsheets/Ruby_on_Rails_Cheat_Sheet.html); [Vite](https://vite.dev/guide/env-and-mode); [Next.js](https://nextjs.org/docs/app/guides/data-security) |
| SEC15 | TLS 検証の無効化（`VERIFY_NONE`、`verify: false`） | must | diff | [Brakeman](https://brakemanscanner.org/docs/warning_types/) |
| SEC16 | データの過剰露出：`render json: @user`、シリアライザ、Server Component から Client Component への props、Server Action の戻り値で、`password_digest`、`*_token`、PII を丸ごと返している | must | diff | [Next.js Data Security](https://nextjs.org/docs/app/guides/data-security) |
| SEC17 | トークンやセッション ID を `localStorage`/`sessionStorage` に保存している | must | diff | [HTML5 CS](https://cheatsheetseries.owasp.org/cheatsheets/HTML5_Security_Cheat_Sheet.html) |
| SEC18 | `postMessage(x, '*')`、`message` イベントで `event.origin` を完全一致で検証していない | must | diff | 同上 |
| SEC19 | ログや監視（`Rails.logger`、`console.log`、Sentry）にパスワード、トークン、カード番号、健康情報を出している。`params.inspect` をログに出している | must | diff | [Rails Security Guide](https://guides.rubyonrails.org/security.html) |
| SEC20 | テスト、seed、fixture、スクリーンショットに実データが混入している。`.sqlite3` をコミットしている | must | diff | [Rails CS](https://cheatsheetseries.owasp.org/cheatsheets/Ruby_on_Rails_Cheat_Sheet.html) |
| SEC21 | ログイン後に `reset_session` がない。cookie の `httponly`/`secure`/`same_site` を弱めている。セッションに機密を保存している | should→must | diff | [Rails Security Guide](https://guides.rubyonrails.org/security.html) |
| SEC22 | ログイン、パスワードリセット、OTP、招待のエンドポイントに `rate_limit` や rack-attack がない | should | repo | 同上 |
| SEC23 | 認証ジェネレータの生成コードの改変（`allow_unauthenticated_access` の範囲）、エラーメッセージによるユーザー列挙、スタックトレースや SQL の露出 | should | diff+repo | [Saeloun](https://blog.saeloun.com/2026/04/28/rails-security-best-practices-a-comprehensive-guide/); [Brakeman](https://brakemanscanner.org/docs/warning_types/) |
| SEC24 | CSP/CORS/`config.hosts`/`force_ssl` の緩和（`origins '*'`、`unsafe-inline`、`content_security_policy false`） | should | diff | [Rails Security Guide](https://guides.rubyonrails.org/security.html) |
| SEC25 | 正規表現の検証で `^`/`$` を使っている（`\A`/`\z` にすべき） | should | diff | 同上 |
| SEC26 | アップロード：content_type の検証がない、`/public` への保存、ファイル名を無加工で使用 | should | diff+repo | 同上 |
| SEC27 | MD5/SHA1 のパスワード・トークンへの使用、独自暗号、`==` によるトークン比較（`secure_compare` を使う） | should | diff | [Brakeman](https://brakemanscanner.org/docs/warning_types/) |
| SEC28 | ルートの過剰公開（キャッチオールルート、`resources` の `only:` 指定漏れ） | should | diff | [Rails CS](https://cheatsheetseries.owasp.org/cheatsheets/Ruby_on_Rails_Cheat_Sheet.html) |
| SEC29 | 新しい機密パラメータ（`otp`、`ssn`、`card_number`）が `filter_parameters` の部分一致（`passw`/`secret`/`token`）に当たらない | should | diff+repo | [Rails Security Guide](https://guides.rubyonrails.org/security.html) |
| SEC30 | PII を URL のクエリで送っている。新しい PII カラムに暗号化・保持期間・削除の方針がない。重要操作の監査ログがない | should | diff+repo | [ASVS V14/V16](https://github.com/OWASP/ASVS/tree/master/5.0/en) |
| SEC31 | プロトタイプ汚染（deep merge で `__proto__` を除外していない、辞書に `{}` を使っている） | should | diff | [Prototype Pollution CS](https://cheatsheetseries.owasp.org/cheatsheets/Prototype_Pollution_Prevention_Cheat_Sheet.html) |
| SEC32 | 信頼できない iframe に `sandbox` がない。`target="_blank"` に `noopener` がない | should／nit | diff | [HTML5 CS](https://cheatsheetseries.owasp.org/cheatsheets/HTML5_Security_Cheat_Sheet.html) |
| SEC33 | AI エージェントや IDE の設定ファイル（`.claude/`、`.vscode/` の tasks）の追加・変更 | should（不審なら must） | diff | [Microsoft ChainDrop](https://www.microsoft.com/en-us/security/blog/2026/08/04/chaindrop-supply-chain-compromise-anatomy-self-propagating-worm/) |
