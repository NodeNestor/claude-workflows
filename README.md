# claude-workflows

Declarative workflow engine for Claude Code. Define YAML workflows triggered by hooks or cron, with sequential steps, conditions, and agent actions. Like GitHub Actions but for Claude Code.

## Installation

Install as a Claude Code plugin — no pip dependencies required (pure Python stdlib).

```bash
# From your project directory:
bash install.sh
# or on Windows:
powershell -File install.ps1
```

## Quick Start

Create `.claude/workflows/my-workflow.yml`:

```yaml
name: auto-test
description: Run tests after git push
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
    agent: "Fix the failing tests"
```

## Workflow Format

### Top-level fields

| Field | Required | Description |
|-------|----------|-------------|
| `name` | yes | Workflow identifier |
| `description` | no | Human-readable description |
| `trigger` | yes | When to run (see Triggers) |
| `steps` | yes | List of steps to execute |

### Triggers

**Hook trigger** — runs when a Claude Code hook fires:

```yaml
trigger:
  event: PostToolUse      # Hook event: SessionStart, PostToolUse, Stop
  matcher: "Bash"         # Optional: regex on tool name (e.g. "Edit|Write")
  condition: "git push"   # Optional: regex on tool_input content
```

**Cron trigger** (planned):

```yaml
trigger:
  cron: "0 8 * * 1-5"    # Standard cron expression
```

### Steps

Each step runs sequentially. Fields:

| Field | Default | Description |
|-------|---------|-------------|
| `name` | required | Step identifier (used in conditions) |
| `run` | - | Shell command to execute |
| `agent` | - | Prompt for Claude to act on (alternative to `run`) |
| `when` | always | Condition expression (skip if false) |
| `timeout` | 120 | Seconds before timeout |
| `on_failure` | stop | `stop`, `continue`, or `retry` |
| `max_retries` | 0 | Retry count (only with `on_failure: retry`) |

### Conditions

Use `when` to conditionally run steps based on previous results:

```yaml
# Check exit code
when: "steps.run-tests.exit_code != 0"

# Check output contains string
when: "contains(steps.run-lint.output, 'error')"

# Boolean logic
when: "steps.build.exit_code == 0 and steps.test.exit_code == 0"

# Comparisons: ==, !=, >, <, >=, <=
when: "steps.count.exit_code >= 1"
```

Available step fields: `exit_code`, `output`, `status`

### Agent Steps

Agent steps inject a prompt back to Claude instead of running a shell command:

```yaml
- name: fix-issues
  agent: "Review the test failures above and fix the code"
```

Since hooks can't spawn sub-agents, the prompt is returned as a message that tells Claude what to do next.

## MCP Tools

The plugin exposes these tools via MCP:

- **list_workflows(project_path)** — List all workflows
- **run_workflow(project_path, workflow_name)** — Manually trigger a workflow
- **workflow_history(project_path, limit)** — Show recent executions
- **create_workflow(project_path, name, trigger, steps)** — Create a new workflow
- **pause_workflow(project_path, workflow_name)** — Pause a workflow
- **resume_workflow(project_path, workflow_name)** — Resume a paused workflow

## Execution Logs

All workflow runs are logged to `.claude/workflows/runs/` as JSON files with timestamps, step results, and outputs.

## Pausing Workflows

Pause a workflow by renaming its file with `.paused` suffix (e.g., `auto-test.paused.yml`). The `pause_workflow` and `resume_workflow` MCP tools handle this automatically.

## Examples

See the `examples/` directory for sample workflows:

- `auto-test.yml` — Run tests after git push
- `lint-on-edit.yml` — Run linter after file edits
- `morning-triage.yml` — Daily triage cron workflow
