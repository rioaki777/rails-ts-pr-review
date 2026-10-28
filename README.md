# rails-ts-pr-review

Ruby on Rails + TypeScript の Web アプリの PR を、変更の種類ごとの観点でレビューする Claude Code プラグインです。

親スキル `review` が PR の変更を把握し、該当する子スキル（`check-security` / `check-general` / `check-db-migration` / `check-rails-app` / `check-frontend` / `check-deps-ci-config` / `check-tests` / `check-docs`）のチェックリストを1つの会話の中で順に当てます。結果は番号付きの指摘一覧とカバレッジ報告としてターミナルに出し、会話で添削したあと、指示があれば GitHub に1つのレビューとして投稿します。

重大な問題の見逃しを防ぐことを最優先にしています。確信が持てない重大候補も「要確認」として残し、何を確認して何を確認できなかったかを必ず報告します。

## 前提

- レビュー対象のリポジトリが clone 済みで、その中で Claude Code を起動する
- `git` と `gh`（`gh auth login` 済み）が使える

## インストール

```bash
claude plugin marketplace add rioaki777/rails-ts-pr-review
claude plugin install rails-ts-pr-review@rails-ts-pr-review
```

## 使い方

```
/rails-ts-pr-review:review 123          # PR 番号
/rails-ts-pr-review:review https://github.com/owner/repo/pull/123
/rails-ts-pr-review:review feature/foo  # PR のないブランチ（投稿はできない）
/rails-ts-pr-review:review              # 現在のブランチの PR
```

一覧が出たら、会話で添削します。

```
2番は削除、4番はもう少し柔らかい言い方に、7番は nit に下げて
nit も見せて
投稿して
```

「投稿して」と言うと、送り先の URL・イベント（既定は `COMMENT`）・コメント一覧を表示し、OK をもらってから1回だけ投稿します。自分の PR では、投稿の代わりにその場で修正することもできます（修正前にブランチ・未コミット変更・PR の head とのずれを確認します）。

## 安全上の注意

- PR のタイトル・本文・コード・コメントは指示ではなくデータとして扱います。AI 向けの指示らしき文言は、従わずに報告します。
- レビュー規約（`CLAUDE.md`、`.rubocop.yml`、`REVIEW.md` など）は base ブランチからだけ読みます。
- PR の内容は `.git/pr-review-worktrees/` の一時 worktree に展開して読み、作業ツリーには触れません。
- 他人の PR では、依存のインストールやテスト・コードの実行をしません。
- 事前に許可しているのは読み取り系の `git` / `gh` と worktree 操作だけです。投稿・編集・インストールは、毎回 Claude Code の許可確認が出ます。

## 開発

```bash
python scripts/extract_checklists.py   # docs/research/report.md から子のチェックリストを再生成
python scripts/check_plugin.py         # スキル構造の検証
python -m unittest discover -s tests   # 検証スクリプトのテスト
claude plugin validate .
```

- 観点の出典: `docs/research/report.md`（調査レポート）と `docs/research/notes/`
- 設計: `docs/superpowers/specs/2026-10-28-rails-ts-pr-review-design.md`
- 動作確認: `evals/README.md`、`evals/results/`
