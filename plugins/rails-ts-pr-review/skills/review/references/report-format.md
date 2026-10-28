# 指摘、カバレッジ、提示形式

## 子の出力

子は次だけを返す。

- 指摘: 観点 ID、`file:line`、重要度（must / should / nit）、確信度（確定 / 要確認）、問題、影響、根拠（確認したコードの位置）、修正案。
- カバレッジ: 確認した観点 ID、該当なしだった観点 ID、静的には判定できなかった観点 ID。

迷った指摘は捨てず「要確認」にする。実行が必要な項目は人間による確認が必要としてカバレッジに入れる。

## 統合と検証

- 同じ `file:line` と同じ観点 ID は一つに統合する。多数決で削らない。
- must と「要確認」の根拠を worktree で開き直し、確定、格下げ、要確認のまま、棄却に分ける。
- 根拠が弱い must 候補は棄却せず、`must・要確認` として上位に残す。
- 棄却した指摘は件数と要旨をカバレッジに残す。

## ターミナル出力

日本語で、must → should → 要確認（question）→ nit の順に番号付きで出す。nit は既定で5件まで表示し、残りは件数だけ示す。添削中も番号を固定し、削除は欠番にする。必ず実施した子と観点数、対象外の子、静的には判定できない項目、リンターに委ねた項目、検証で棄却した件数を添える。

```
PR #123「注文キャンセルAPIの追加」  must 3（うち要確認 1） / should 6 / nit 2（+4件折りたたみ） / question 2
── must ──
 1. [SEC1・確定] app/controllers/orders_controller.rb:42
    Order.find(params[:id]) が current_account のスコープ外。他テナントの注文をキャンセルできる。
    修正案: current_account.orders.find(params[:id])
 2. [RB4・確定] app/models/order.rb:88  トランザクション内で RefundJob.perform_later …
 3. [DB1・要確認] db/migrate/20261028_add_index_orders_status.rb:3  orders の行数不明。既存の大テーブルなら CONCURRENTLY が必要
── should ── …
── カバレッジ ──
 実施: general-correctness(15) security(33) rails-app(28) db-migration(26) tests(14)
 対象外: frontend, deps-ci-config, docs（該当する変更なし）／docs: ENV ORDER_CANCEL_WINDOW の追加に対して README の差分なし → should #7
 静的には判定できない: N+1 の実際の件数、migration の実行時間（本番の行数）、a11y のコントラスト
 リンターに委ねた: Rails/FindBy, Rails/DynamicFindBy（.rubocop.yml で有効）
 検証で棄却: 2件（must 候補 0件）
```

「指摘なし」「対象外」「静的には判定できない」は安全を保証しないため、安全・承認可能と表現しない。
