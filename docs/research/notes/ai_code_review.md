# State of the Art in AI/LLM-Assisted PR Review (2024–2026): Design Lessons for a Multi-Part Claude Code Review Skill

Research date: 2026-10-28. Dates of sources are flagged inline. "Secondary" marks claims sourced only from press/aggregators.

## Q1. How effective is LLM code review? (academic + industry studies and benchmarks)

### Takeaway
LLM reviewers are useful but far from complete. On realistic benchmarks of real bugs, recall is roughly 15–35% and precision is low. Live deployments see roughly 8% to 75% acceptance, depending on how acceptance is measured. Recall drops on large PRs and on bugs that need context outside the diff, such as performance (N+1), memory/runtime, and usability/functional-suitability bugs. Aggregating several review runs reliably improves results.

### Cited Findings
- **SWR-Bench (arXiv 2509.01494, Sep 2025):** 1,000 manually verified GitHub PRs with full project context. Its LLM-based evaluation agrees with humans about 90% of the time. ACR tools are "more adept at detecting functional errors". A simple **multi-review aggregation** strategy improves F1 by "up to 43.67%". — [arXiv abstract](https://arxiv.org/abs/2509.01494)
- **SWR-Bench tables:** LLM reviewers reach precision of about 8–20% and recall of about 14–26%. Precision stays fairly stable across PR sizes, but **recall falls sharply on larger PRs**. Example: Gemini-2.5-Pro precision 8.02 / recall 21.29 / F1 11.65. — [SWR-Bench HTML](https://arxiv.org/html/2509.01494v2)
- **CR-Bench (arXiv 2603.11078, Mar 2026):** 584 instances (174 verified) derived from SWE-Bench. It adds Usefulness Rate and SNR metrics. On the verified set:
  - Single-shot GPT-5.2: recall 27.0%, precision 3.6%, usefulness 83.6%, SNR 5.11.
  - Reflexion (iterative) GPT-5.2: recall 32.8%, usefulness 66.1%, SNR 1.95.
  - Iteration buys recall at the cost of noise. A smaller model under Reflexion collapsed to SNR 0.91, which the authors attribute to hallucinated issues.
  — [CR-Bench](https://arxiv.org/html/2603.11078v1)
- **CR-Bench by bug category:**
  - Structural and Interface/Integration bugs are found reliably.
  - **Memory bugs had 0% recall for all agents** (they need runtime traces).
  - Usability and functional-suitability bugs are weak because of missing system context outside the diff.
  - High-severity bugs are found most often, and low-severity bugs have the lowest recall.
  - The authors recommend routing style/format issues to linters and supplying broader repo context.
  — [CR-Bench](https://arxiv.org/html/2603.11078v1)
- **"Bigger Isn't Always Better" (arXiv 2606.15689, Jun 2026):** 5 LLMs, 150 samples (100 synthetic, 50 real bug-fix PRs).
  - Best real-PR F1 was 0.066, against 0.847 on synthetic samples (a 92% degradation).
  - Haiku 4.5 had higher recall than Sonnet 4.6 (0.293 vs 0.248), and Sonnet had higher precision (0.558 vs 0.486).
  - **Performance bugs (N+1 queries, unbounded queries) had 0% recall for 4 of 5 models.**
  - Figures are from search-result extraction of the paper; I did not read the full paper.
  — [arXiv 2606.15689](https://arxiv.org/html/2606.15689v1)
- **Mozilla + Ubisoft (RevMate, arXiv 2411.07091, Nov 2024):**
  - Over 587 patch reviews, 8.1% (Mozilla) and 7.2% (Ubisoft) of LLM comments were accepted. A further 14.6% and 20.5% were judged useful as tips.
  - **Refactoring comments were accepted far more than functional ones** (18.2% / 18.6% vs 4.8% / 5.2%).
  — [alphaxiv 2411.07091](https://alphaxiv.org/abs/2411.07091); [Ubisoft La Forge, Sep 2025](https://www.ubisoft.com/en-us/studio/laforge/news/3SsR9KkpyUCBvy1Wyw3lTS/impact-of-an-llmbased-code-review-assistant-in-practice)
- **Beko (arXiv 2412.18531, Dec 2024):** A Qodo PR-Agent-based tool was given to about 238 practitioners. Of 4,335 PRs, 1,568 received automated reviews, and 73.8% of comments were "resolved". A related thesis reports that **PR closure time increased**. The "resolved" vs "engaged" wording differs between sources, so treat the 73.8% with care. — [arXiv 2412.18531](https://arxiv.org/abs/2412.18531v2)
- **ByteDance BitsAI-CR (FSE 2025 industry):** Reports 75.0% precision on generated review comments. It tracks an "Outdated Rate" adoption metric (26.7% for Go). Precision and adoption are different metrics. — [FSE 2025](https://conf.researchr.org/details/fse-2025/fse-2025-industry-papers/24/BitsAI-CR-Automated-Code-Review-via-LLM-in-Practice)
- **Google AutoCommenter (arXiv 2405.13565, 2024):**
  - An LLM enforces coding best practices in C++, Java, Python and Go.
  - In 50% of 6,000 snapshot pairs, the comment had disappeared from the submitted snapshot. A manual check of 40 found 80% were directly resolved by the author.
  - Explicit feedback was rare (about 10%).
  - Comments "lack diversity" relative to human reviewers.
  — [arXiv 2405.13565](https://arxiv.org/pdf/2405.13565); [DX newsletter summary](https://newsletter.getdx.com/p/ai-assisted-code-reviews-at-google)
- **Google ML-suggested edits (ICSE-SEIP 2024):** Authors address about 5% of all reviewer comments by applying an ML-suggested edit (other Google pages say 7.5%). — [ICSE-SEIP 2024](https://conf.researchr.org/details/icse-2024/icse-2024-software-engineering-in-practice/35/Resolving-Code-Review-Comments-with-Machine-Learning)
- **Microsoft internal AI review assistant (2025, secondary):** About 600k PRs/month, nearly 90% of PRs (ZenML says over 90%). Reported 10–20% median PR completion-time improvement in early-adopter repos. Lessons fed into GitHub Copilot code review. I did not find the primary Microsoft blog. — [Neowin](https://www.neowin.net/news/microsoft-is-using-ai-copilot-internally-for-code-reviews-impacting-600000-prs-per-month/); [ZenML](https://www.zenml.io/llmops-database/ai-powered-code-review-assistant-at-enterprise-scale)
- **Cursor Bugbot (Jan 2026 blog):**
  - The main metric is **resolution rate**: an LLM judges at merge time whether the flagged bug was fixed.
  - Over 40 experiments, resolution rate rose from 52% to over 70%. Bugs flagged per run went from 0.4 to 0.7, and resolved bugs per PR from about 0.2 to 0.5.
  - Bugbot reviews over 2M PRs/month.
  — [Cursor blog](https://cursor.com/blog/building-bugbot)

### Inferences
- With recall this low, the skill should not trust any single pass to catch serious issues. Use multiple passes or perspectives and aggregate, which is what SWR-Bench and Bugbot both validate.
- Category-specific child reviewers should be told explicitly to hunt known blind spots, especially for Rails/TS:
  - N+1 and unbounded queries
  - missing pagination or limits
  - memory/resource leaks
  - cross-file contract breaks
  Generic LLMs reportedly score near zero on performance bugs.
- Large PRs need chunking or per-file/per-category dispatch, because recall degrades with PR size (SWR-Bench).
- Measure your own skill by resolution or acceptance on real PRs, not by finding count.

### Gaps
- I found no rigorous public study of Meta's internal LLM review deployment.
- I did not read the full Microsoft/GitHub "60 million Copilot reviews" blog.
- The figures in arXiv 2606.15689 came from a search-tool extraction and were not verified in the full text.

## Q2. How do commercial and open tools work? (architecture and categories)

### Takeaway
The 2025–2026 convergence is an **agentic, multi-agent "find → verify → dedupe/rank → post" pipeline**. Its parts:
- parallel finders, with diversity from randomization or specialization
- tool-driven retrieval of context beyond the diff
- a separate verification step to kill false positives
- severity ranking
- repo-specific rule files: CLAUDE.md / REVIEW.md, Bugbot rules, CodeRabbit learnings

### Cited Findings
- **Anthropic Code Review (managed service, launched about Mar 9 2026; docs current):**
  - Four stages:
    1. **Find**: several agents examine the diff *and surrounding code* in parallel.
    2. **Verify**: candidate findings are checked against the code to filter false positives.
    3. **Rank**: findings are deduplicated and severity-ranked.
    4. **Post**: inline comments, a summary, and a check run.
  - It never approves or blocks a PR.
  - It focuses by default on correctness ("bugs that would break production, not formatting preferences or missing test coverage").
  - Review levels are Quick, Standard and Deep.
  - It reads the diff and code **without building or running it**.
  — [code.claude.com/docs/en/code-review](https://code.claude.com/docs/en/code-review)
- **Anthropic Code Review, secondary figures:**
  - About 20 minutes and about $15–25 per review.
  - Anthropic internal: under 1% incorrect findings, and PRs with substantive review comments rose from 16% to 54%.
  - Not independently verified.
  — [noqta.tn](https://www.noqta.tn/en/news/anthropic-claude-code-review-multi-agent-pr-2026); [The New Stack](https://thenewstack.io/?p=22816662)
- **Anthropic Code Review customization (REVIEW.md + CLAUDE.md):**
  - Finder *and* verifier agents receive REVIEW.md.
  - The final-writing step consults it for severity.
  - Subdirectory REVIEW.md/CLAUDE.md files apply to changes under their path.
  - Severities include 🔴 Important and 🟡 Nit.
  — [code-review-customize](https://code.claude.com/docs/en/code-review-customize)
- **Anthropic `/code-review` (local, bundled skill):**
  - Runs as a **background forked subagent** with its own context.
  - Reads CLAUDE.md but not REVIEW.md.
  - Effort levels trade coverage for confidence: "At `low`, the review reports the findings it's most confident in … From `medium` through `max`, the review broadens coverage".
  - `--max-findings` defaults to a limit (32 via the findings tool), or `all`.
  - Findings carry a category tag (e.g., `correctness`).
  - A project/personal skill named `code-review` **overrides the bundled one**.
  — [code-review-local](https://code.claude.com/docs/en/code-review-local)
- **Anthropic claude-code-security-review (GitHub Action):**
  - Diff-aware: it analyzes only changed files, with Claude doing semantic analysis.
  - Pipeline: findings with severity and remediation, then a **false-positive filtering step**, then inline comments.
  - Categories: injection (SQL/command/LDAP/XPath/NoSQL/XXE), authN/authZ, data exposure, crypto, input validation, business logic (race/TOCTOU), config, supply chain, code execution (deserialization/eval), XSS.
  - **Excluded by default:** DoS, rate limiting, resource exhaustion, generic input validation without proven impact, open redirects.
  - Supports custom filtering/scan instruction files and an `evals/` directory.
  — [README](https://raw.githubusercontent.com/anthropics/claude-code-security-review/main/README.md)
- **Cursor Bugbot evolution (Jul 2025 → Jan 2026):**
  - **V1:** 8 parallel passes with **randomized diff order**, then grouping, then **majority voting** (drop bugs found by only one pass), then merge, then a category filter (drop compiler warnings and doc errors), then a **validator model**, then dedupe against earlier runs.
  - **Fall 2025:** moved to a **fully agentic design** (tool calls, choosing where to investigate, dynamic context), which gave the largest gains.
  - The agent turned out *too cautious*, so prompts were made **more aggressive** about flagging suspicious patterns. "Tool design had an outsized effect."
  - Bugbot rules hold codebase-specific checks.
  - Future work: running code to verify bugs.
  — [Cursor blog](https://cursor.com/blog/building-bugbot)
- **GitHub Copilot code review:**
  - Moved to an **agentic, tool-calling architecture** that pulls in related code, directory structure and references (GA changelog Mar 5 2026). It runs on GitHub Actions.
  - Secondary sources say a public preview started around Oct 2025 and describe a hybrid with deterministic tools (CodeQL, ESLint).
  - A Sep 2026 roundup says reviews resolve addressed comments and can use shell tools to validate changes.
  — [GitHub changelog 2026-03-05](https://github.blog/changelog/2026-03-05-copilot-code-review-now-runs-on-an-agentic-architecture/); [agentpatterns.ai](https://agentpatterns.ai/code-review/agentic-code-review-architecture/); [GitHub changelog 2026-09-18](https://github.blog/changelog/2026-09-18-github-copilot-weekly-releases-september-14)
- **CodeRabbit:**
  - Pairs its LLM with 40+ linters/static analyzers (secondary).
  - Its context-engineering post lists knowledge integration from multiple sources, strategic context assembly, and **verification agents** as means to reduce false positives.
  - Secondary comparisons say CodeRabbit uses diff + file context rather than a persistent full-repo graph, and that Greptile does deeper codebase-graph analysis.
  — [CodeRabbit blog](https://coderabbit.ai/blog/the-art-and-science-of-context-engineering); [levelop.dev](https://levelop.dev/blog/best-ai-code-review-tools-2026-coderabbit-greptile-qodo-compared); [vantaige.io](https://vantaige.io/ai-tool/greptile)
- **Greptile vs CodeRabbit bug-catch figures conflict:**
  - One comparison reports Greptile 76% vs CodeRabbit 82%. Greptile's own 2025 benchmark claims 82% vs 44%.
  - Greptile is reported to catch the most bugs but with the most false positives (11 vs 2 in one test).
  - All vendor or small-sample results.
  — [getpanto.ai](https://www.getpanto.ai/blog/coderabbit-vs-greptile-ai-code-review-tools-compared)

### Inferences
- A parent orchestrator that classifies and dispatches category-specific children matches the industry pattern of "specialized parallel finders". The orchestrator should also own:
  - a **verify** stage (separate from finders)
  - a **dedupe/rank** stage
- Diversity among finders matters. Bugbot used randomized order, and specialization by category is another source.
- Bugbot's experience suggests that **agentic children with tool access** (Grep/Read of callers, schema, routes) beat fixed-context prompts, and that finders should be prompted *aggressively* while precision is handled downstream.
- Encode deterministic checks (lint, types, rubocop, brakeman, tsc) as tools or skips rather than LLM work. LLM review should focus on semantic defects.

### Gaps
- I did not obtain primary architecture docs for Graphite Diamond/Agent, Qodo PR-Agent internals, Sourcery, Ellipsis, or OpenAI Codex review within the tool budget.
- The GitHub raw prompt for Anthropic's open-source `plugins/code-review` returned 404. Its exact confidence threshold (reportedly 0–100 scoring with a cutoff) is unverified.

## Q3. Techniques for raising recall without drowning signal

### Takeaway
Separate **generation** (high recall, aggressive, diverse) from **filtering** (verification against code with evidence, severity calibration, nit caps). Report by severity so Important findings are never buried. Configure through repo rule files with "always check" lists and "do not report" lists.

### Cited Findings
- **Multi-run aggregation** raises F1 by up to 43.67%. — [SWR-Bench](https://arxiv.org/abs/2509.01494)
- **Majority voting across 8 randomized passes, then a validator model.** Later, an agentic loop with *more aggressive* prompts caught more bugs "without a comparable rise in false positives". — [Cursor](https://cursor.com/blog/building-bugbot)
- **Iterative/Reflexion review raises recall about 6 pts but cuts SNR from 5.11 to 1.95.** Suggested use: iterative for security or high-risk changes, single-shot for low-noise workflows. — [CR-Bench](https://arxiv.org/html/2603.11078v1)
- **Evidence requirement as an FP filter:** "behavior claims need a `file:line` citation in the source, not an inference from naming". — [code-review-customize](https://code.claude.com/docs/en/code-review-customize)
- **Severity recalibration and nit capping** via REVIEW.md:
  - Define what "Important" means (broken behavior, data leak, unscoped DB queries, PII in logs, non-backward-compatible migrations).
  - Cap nits ("at most five").
  - Skip generated files, lockfiles, and anything CI enforces.
  - Add an "Always check" list (e.g., new API routes have integration tests; queries scoped to tenant).
  - Set a higher bar for some paths ("in `scripts/`, only report if near-certain and severe").
  — [code-review-customize](https://code.claude.com/docs/en/code-review-customize)
- **Effort or confidence knob:** low effort gives only the most confident findings, while higher effort broadens coverage. A `--max-findings all` escape hatch exists. — [code-review-local](https://code.claude.com/docs/en/code-review-local)
- **Explicit exclusion lists** cut low-value security noise (DoS, rate limiting, open redirect, unproven input validation). — [claude-code-security-review](https://raw.githubusercontent.com/anthropics/claude-code-security-review/main/README.md)
- **Read beyond the diff:**
  - Anthropic's agents read "the diff and the surrounding code". — [code-review](https://code.claude.com/docs/en/code-review)
  - Copilot's agentic review pulls related code and references. — [GitHub changelog](https://github.blog/changelog/2026-03-05-copilot-code-review-now-runs-on-an-agentic-architecture/)
  - CR-Bench attributes usability/functional misses to missing out-of-diff context. — [CR-Bench](https://arxiv.org/html/2603.11078v1)
- **PR intent:** CR-Bench instances carry PR descriptions (about 900 chars on average) as reviewer input. — [CR-Bench](https://arxiv.org/html/2603.11078v1)
- **Dedupe against prior runs, and resolve outdated comments on re-review:**
  - Bugbot dedupes against previous runs. — [Cursor](https://cursor.com/blog/building-bugbot)
  - Copilot resolves addressed comments. — [GitHub changelog Sep 2026](https://github.blog/changelog/2026-09-18-github-copilot-weekly-releases-september-14)
  - Anthropic resolves its own earlier threads. — [code-review](https://code.claude.com/docs/en/code-review)
- **"No findings ≠ safe":** Anthropic's docs warn that a review with no findings does not mean the code is error-free. — [code-review](https://code.claude.com/docs/en/code-review)
- **Refactoring comments get accepted more than functional ones.** Acceptance rate is therefore a biased proxy for value; serious functional findings are rarer and accepted less often. — [Mozilla/Ubisoft](https://alphaxiv.org/abs/2411.07091)

### Inferences
- For the user's high-recall priority, the recommended pipeline is:
  1. Category-specific finders, prompted to over-report, each with a checklist of must-check viewpoints for its category.
  2. A verifier that requires `file:line` evidence and either confirms, downgrades or drops each finding. Uncertain-but-serious findings are *downgraded to "needs human check"*, not dropped. That keeps recall while marking confidence.
  3. Severity-sorted output with Important first and nits capped or collapsed.
  4. A **coverage report** listing which viewpoints and categories were checked, which were skipped (e.g., no migrations in this PR), and which were not checkable statically (runtime/perf). This counters the "no findings = safe" fallacy.
  - The coverage report is my inference, not found as a named feature in a primary source; Anthropic's check run and summary are the closest analog.
- Use a stronger model for verification or iterative passes, because small models degrade sharply in SNR under iteration (CR-Bench). Cheaper models can serve as finders; Haiku 4.5 had higher recall than Sonnet 4.6 in arXiv 2606.15689.

### Gaps
- I found no published ablation that isolates "confidence label shown to the user" vs. "filtered out" for developer trust.
- I found no primary source quantifying checklist-driven coverage gains specifically.

## Q4. Known failure modes

### Takeaway
The main failure modes are:
- hallucinated or unsupported issues
- noise and nitpicks that erode trust
- misses that need cross-file, runtime or performance context
- recall collapse on large diffs
- **prompt injection via PR and issue content**, which is serious when the reviewer has write tokens or secrets
- cost and latency (minutes and dollars per deep review)

### Cited Findings
- **Hallucinated findings** rise with iterative probing on smaller models (SNR 0.91). Precision is 3–5% in all CR-Bench configurations. — [CR-Bench](https://arxiv.org/html/2603.11078v1)
- **Large-diff degradation:** recall falls sharply on larger PRs. — [SWR-Bench](https://arxiv.org/html/2509.01494v2)
- **Performance/N+1 blind spot:** 0% recall for 4 of 5 models. — [arXiv 2606.15689](https://arxiv.org/html/2606.15689v1)
- **Memory bugs have 0% recall** (runtime needed). — [CR-Bench](https://arxiv.org/html/2603.11078v1)
- **Low diversity:** comments repeat the same key guidelines. — [Google AutoCommenter](https://arxiv.org/pdf/2405.13565)
- **Process cost:** PR closure time increased after the automated review rollout at Beko. — [arXiv 2412.18531](https://arxiv.org/abs/2412.18531v2)
- **Over-caution:** Bugbot's agent was "overly cautious" until its prompts were made more aggressive. — [Cursor](https://cursor.com/blog/building-bugbot)
- **Prompt injection, real incidents 2025–2026:**
  - Aikido's "PromptPwnd": hidden instructions in issues/PRs made agents in Actions run commands and leak secrets. Affected: Gemini CLI, Claude Code, Codex, GitHub AI Inference.
  - Johns Hopkins researchers' "Comment and Control" hit Claude Code Security Review, Gemini CLI Action and Copilot via malicious PR titles and issue bodies.
  - GMO Flatt Security reported a Claude Code Action issue (Jun 2026), patched in 4 days, CVSS 7.8.
  - Trail of Bits (Aug 2025) showed an injected issue leading Copilot to insert a backdoor.
  - Severity numbers vary by source.
  — [CSA research note](https://labs.cloudsecurityalliance.org/research/csa-research-note-ai-github-actions-security-20260503-csa-st/); [CSA Comment and Control](https://labs.cloudsecurityalliance.org/research/csa-research-note-comment-control-github-prompt-injection-20/); [Trail of Bits](https://blog.trailofbits.com/2025/08/06/prompt-injection-engineering-for-attackers-exploiting-github-copilot/); [Kudelski on PR-Agent](https://kudelskisecurity.com/research/careful-where-you-code-multiple-vulnerabilities-in-ai-powered-pr-agent)
- **Anthropic's security-review action** is "not hardened against prompt injection attacks". It should review trusted PRs only, and maintainer approval is recommended for external contributors. — [README](https://raw.githubusercontent.com/anthropics/claude-code-security-review/main/README.md)
- **Anthropic Code Review's injection mitigation:** it reads REVIEW.md only from the base or default branch, **never from the PR's own changes**. Protected-branch status is required to honor exclusions. Review access is read-only and pushes no commits. — [code-review-customize](https://code.claude.com/docs/en/code-review-customize); [code-review](https://code.claude.com/docs/en/code-review)
- **Cost and latency:** about 20 minutes and $15–25 per managed review (secondary). Quick/Standard/Deep levels exist to trade cost for thoroughness. — [noqta.tn](https://www.noqta.tn/en/news/anthropic-claude-code-review-multi-agent-pr-2026); [code-review](https://code.claude.com/docs/en/code-review)

### Inferences
- The skill should:
  - Treat PR title/body, commit messages, code comments and diff text as **untrusted data**. Instructions found there must not change reviewer behavior. A finding should be raised if the PR contains text that looks like agent instructions.
  - Load review rules only from the base branch or the skill itself, never from files changed in the PR. This matters most if the skill reads repo-level review config.
  - Keep child reviewers read-only (allowed-tools limited to Read/Grep/Glob/git read-only).
  - Split large PRs by category or file group, so each child sees a manageable slice plus pulled-in context.

### Gaps
- I found no quantitative study of injection success rates against review agents specifically.

## Q5. Claude Code specifics: skills, subagents, plugins, authoring best practices

### Takeaway
A skill is a folder with SKILL.md (YAML frontmatter + Markdown) plus supporting files loaded on demand. `context: fork` + `agent:` runs a skill in a subagent, and subagents can preload skills via a `skills` field. Plugins namespace skills as `/plugin:skill` and are installed via `/plugin`. Anthropic's guidance:
- keep SKILL.md under 500 lines
- keep references one level deep
- write a third-person what+when description
- use checklists and validate→fix loops
- build evals first and test across Haiku/Sonnet/Opus

### Cited Findings
- **Frontmatter fields:** `name`, `description` (with `when_to_use`, truncated at 1,536 chars combined in the listing), `argument-hint`, `arguments`, `disable-model-invocation`, `user-invocable`, `allowed-tools`, `disallowed-tools`, `model`, `effort`, `context: fork`, `agent`, `background`, `hooks`, `paths`, `shell`. Only `description` is recommended, and unknown fields are silently ignored. — [code.claude.com/docs/en/skills](https://code.claude.com/docs/en/skills)
- **Forked skills:**
  - With `context: fork`, the skill content becomes the subagent's prompt.
  - The subagent **does not see conversation history**, so instructions must be self-contained.
  - It runs in the background by default; `background: false` waits.
  - Custom subagents can preload skills through their `skills` field.
  - The page describes no general direct skill→skill invocation mechanism.
  — [skills docs](https://code.claude.com/docs/en/skills)
- **Dynamic context:** a `` !`command` `` (e.g., `` !`git diff HEAD` ``) runs before the prompt is sent. A failed or unapproved command aborts the skill. Substitutions include `$ARGUMENTS`, `$0..$N`, and `${CLAUDE_SKILL_DIR}`. — [skills docs](https://code.claude.com/docs/en/skills)
- **Locations:** enterprise > personal (`~/.claude/skills`) > project (`.claude/skills`). Nested subdir skills also exist. Plugin skills are namespaced `/plugin-name:skill-name`. Compaction re-attaches skills up to 5k tokens each within a 25k budget. — [skills docs](https://code.claude.com/docs/en/skills)
- **Name collision:** a project/personal skill named `code-review` replaces the bundled `/code-review`. — [code-review-local](https://code.claude.com/docs/en/code-review-local)
- **Authoring best practices:**
  - **Conciseness:** assume Claude is smart.
  - **Degrees of freedom:** code review is the canonical "high freedom" example.
  - **Name:** ≤64 chars, lowercase and hyphens, no "anthropic"/"claude"; gerund naming is suggested.
  - **Description:** ≤1,024 chars, third person, what + when.
  - **Size:** body under 500 lines.
  - **References:** **one level deep** from SKILL.md (nested references may be read partially via `head`); add a ToC to reference files over 100 lines.
  - **Domain organization:** organize references by domain (e.g., `reference/finance.md`) so irrelevant domains aren't loaded.
  - **Workflows:** use **copyable checklists** for complex workflows and validate→fix→repeat feedback loops.
  - **Process:** build at least 3 evals before writing extensive docs; test with Haiku, Sonnet and Opus; use forward-slash paths.
  — [platform.claude.com best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices)
- **Reuse in the managed service:** Code Review can include a skill's SKILL.md via an `@.claude/skills/<folder>/SKILL.md` line in REVIEW.md, with these limits:
  - The body only, ≤30,000 bytes.
  - No `!` commands, `$ARGUMENTS` or linked files are processed.
  - Exclusions and nit caps in skill text are not honored.
  - Up to 8 includes, 150 KB total.
  - This lets a team reuse category checklists in both the local skill and the managed service.
  — [code-review-customize](https://code.claude.com/docs/en/code-review-customize)

### Inferences
- **Architecture fit:** a parent SKILL.md (orchestrator) that:
  - runs `!git diff --stat` / `!gh pr view`
  - classifies files into categories
  - spawns category subagents, either as custom agents in `agents/` that preload category skills, or via the Agent tool with prompts built from `reference/<category>.md`
  - runs a verification subagent
  - merges and ranks findings, then emits severity-sorted findings plus a coverage report
- Keep each category checklist in its own `reference/<category>.md` (Rails models/migrations, controllers/auth, TS frontend, etc.), one level deep from SKILL.md. Children are forked and see no history, so give each child a self-contained prompt that includes the PR intent and the untrusted-content rule.
- Package as a plugin in a GitHub-hosted marketplace for team distribution. Avoid naming the skill `code-review` unless replacing the bundled command is intended.

### Gaps
- I did not fetch the plugin-marketplace docs (`marketplace.json` schema) or the sub-agents doc page within the tool budget. The `skills` field on subagents and the Agent tool are confirmed only via the skills page.
- The full Skills docs page was truncated after 100k characters, so sections on "stack several skills in one message" and skill overrides were not fully read.
