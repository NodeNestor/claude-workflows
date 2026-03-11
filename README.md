# claude-workflows

Agent controller for Claude Code. Define YAML workflows that react to events, poll remote state, and spawn agents to handle work automatically.

## Install

```bash
/plugin install claude-workflows
```

## What it does

- **React to local events** — run tests after push, lint after edits, clean up on session end
- **Poll remote state** — watch for new PRs, CI failures, issues, deployments
- **Schedule recurring tasks** — morning triage, hourly checks, periodic cleanup
- **Spawn agents** — workflows can tell Claude to spawn agents for complex tasks

## Quick start

Create `.claude/workflows/auto-test.yml`:

```yaml
name: auto-test
description: Run tests after git push, fix failures automatically
trigger:
  event: PostToolUse
  matcher: Bash
  condition: "git push"
steps:
  - name: run-tests
    run: "npm test"
    timeout: 120
    on_failure: stop

  - name: fix-tests
    when: "steps.run-tests.exit_code != 0"
    agent: "Tests failed after push. Examine the output and fix the failing tests."
```

## Triggers

### Hook triggers — react to Claude's actions

```yaml
# After git push
trigger:
  event: PostToolUse
  matcher: Bash
  condition: "git push"

# After file edits
trigger:
  event: PostToolUse
  matcher: "Edit|Write"

# On session end
trigger:
  event: Stop
```

### Cron triggers — scheduled via Claude Code's built-in CronCreate

```yaml
trigger:
  cron: "*/10 * * * *"    # every 10 minutes
  cron: "57 8 * * 1-5"    # weekdays at ~9am
  cron: "0 * * * *"       # hourly
```

On session start, cron workflows are automatically scheduled. They run while the session is active.

## Steps

```yaml
steps:
  # Shell command
  - name: run-tests
    run: "npm test"
    timeout: 120
    on_failure: stop       # stop | continue | retry
    max_retries: 2

  # Conditional step
  - name: fix
    when: "steps.run-tests.exit_code != 0"
    agent: "Fix the failing tests based on the output above."

  # Agent step — Claude spawns an agent to handle this
  - name: review
    agent: "Review the PR and leave feedback."
```

### Conditions

```yaml
when: "steps.build.exit_code == 0"
when: "steps.run-tests.exit_code != 0"
when: "contains(steps.check-ci.output, 'failure')"
when: "steps.build.exit_code == 0 and steps.test.exit_code == 0"
```

## Example workflows

### Watch PRs and review them
```yaml
name: pr-watch
trigger:
  cron: "*/10 * * * *"
steps:
  - name: fetch-prs
    run: "gh pr list --state open --json number,title,author,updatedAt --limit 10"
  - name: review
    agent: "Review new/updated PRs. Spawn an agent to review code and comment."
```

### Monitor CI and auto-fix failures
```yaml
name: ci-watch
trigger:
  cron: "*/5 * * * *"
steps:
  - name: check-ci
    run: "gh run list --limit 5 --json status,conclusion,headBranch"
  - name: fix
    when: "contains(steps.check-ci.output, 'failure')"
    agent: "CI failed. Check the logs with 'gh run view <id> --log-failed' and fix it."
```

### Triage new issues
```yaml
name: issue-watch
trigger:
  cron: "*/15 * * * *"
steps:
  - name: fetch-issues
    run: "gh issue list --state open --json number,title,body,labels --limit 10"
  - name: triage
    agent: "Triage new unlabeled issues. Add labels with 'gh issue edit'."
```

### Morning standup
```yaml
name: morning-triage
trigger:
  cron: "57 8 * * 1-5"
steps:
  - name: check-issues
    run: "gh issue list --state open --limit 10"
  - name: check-prs
    run: "gh pr list --state open --limit 10"
  - name: triage
    agent: "Summarize what needs attention today and suggest priorities."
```

## MCP tools

| Tool | Description |
|------|-------------|
| `list_workflows` | List all workflows with triggers |
| `run_workflow` | Manually trigger a workflow |
| `create_workflow` | Create a new workflow YAML |
| `workflow_history` | Show recent execution logs |
| `pause_workflow` | Pause a workflow |
| `resume_workflow` | Resume a paused workflow |

## How it works

```
.claude/workflows/
├── auto-test.yml          # hook-triggered
├── pr-watch.yml           # cron-triggered
├── ci-watch.yml           # cron-triggered
└── runs/                  # execution logs (JSON)
```

- **Hook workflows** fire automatically via plugin hooks
- **Cron workflows** are scheduled via `CronCreate` on session start
- **Agent steps** tell Claude to spawn agents for complex work
- **Execution logs** track every run with timestamps, outputs, and status

## Requirements

- Python 3.10+
- No pip dependencies (pure stdlib)
- `gh` CLI for GitHub workflows (optional)
