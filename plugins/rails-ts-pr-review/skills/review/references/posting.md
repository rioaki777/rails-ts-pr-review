# GitHub への投稿

これはユーザーが会話で「投稿して」と明示したときだけ読む。PR のないブランチレビューでは投稿できないと返す。

1. 投稿直前に `gh pr view <N> --json headRefOid` で head を取り直し、レビュー時の `headRefOid` と違えば、その旨を伝えて再レビューするか確認する。`gh pr diff <N>` の hunk で、変更後（RIGHT 側）に実在する行だと確認できた指摘だけをインラインコメントにする。差分外の `file:line` を指す指摘、全体所感、カバレッジ要約はレビュー本文に入れる。
2. ラベルは must を `issue (blocking):`、should を `suggestion (non-blocking):`、nit を `nitpick:`、要確認を `question:` にする。イベントは既定 `COMMENT` とし、`APPROVE` / `REQUEST_CHANGES` はユーザーが指定したときだけ使う。
3. 投稿前に、送信先 PR URL、イベント、全インラインコメント（`path`、`line`、本文）、レビュー本文を表示し、明示的な OK を待つ。この確認は省略しない。
4. OK の後に一度だけ、JSON を標準入力で渡して投稿する。`<<'JSON'` のようにクォートしたヒアドキュメントを使い、シェル展開させない。

   ```bash
   gh api repos/{owner}/{repo}/pulls/<N>/reviews --method POST --input - <<'JSON'
   {"commit_id": "<headRefOid>", "event": "COMMENT", "body": "...", "comments": [{"path": "app/x.rb", "line": 12, "side": "RIGHT", "body": "issue (blocking): ..."}]}
   JSON
   ```

   JSON は `commit_id` に `headRefOid`、`event`、`body`、`comments` を含める。各 `comments[]` は `path`、`line`、`side: "RIGHT"`、`body` を持つ。
5. 投稿後に結果を示し、worktree と `refs/pr-review/<N>` を後片付けする。

別の `gh api` POST、確認前の投稿、複数レビューへの分割はしない。
