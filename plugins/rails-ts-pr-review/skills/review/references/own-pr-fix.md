# 自分の PR の修正

自分の PR かは `gh pr view --json author` の author と `gh api user --jq .login` が一致することで判定する。該当する場合は投稿の代わりに、修正するか、どの指摘を直すかをユーザーに選んでもらう。修正は一時 worktree ではなく、ユーザーの実際のチェックアウトに直接入れる。

修正の前に次を確認する。

1. `git branch --show-current` が PR の `headRefName` と一致する。
2. `git status --porcelain` が空である。
3. `git rev-parse HEAD` が PR の `headRefOid` と一致する。

いずれかが違う場合は、ブランチ、未コミット変更、または head の不一致を明示して警告し、修正前にユーザーの判断を仰ぐ。警告を省略して修正を始めない。コミット、push、依存のインストール、テスト実行はユーザーが指示するまでしない。他人の PR では修正しない。
