# claude-workflows — Agent Controller

This plugin is your scheduling and automation layer. Use it to run workflows triggered by events, cron schedules, or manual invocation.

## How to orchestrate workflows

### On session start

1. Check if any workflows have `cron` triggers
2. For each one, schedule it with `CronCreate`:
   ```
   CronCreate(cron: "<expression>", prompt: "Run the workflow '<name>' using the run_workflow MCP tool. Act on any agent steps by spawning Agents.")
   ```
3. Report what was scheduled to the user

### When a workflow runs

The `run_workflow` MCP tool executes shell steps and returns results. For `agent` steps, it returns prompts. You MUST act on these:

- **Spawn an Agent** for each agent prompt — don't just print it
- Use `mode: "bypassPermissions"` for automated workflows
- If the agent prompt references step output (test failures, lint errors, PR data), include that context in the agent's prompt
- Launch independent agents in parallel when possible

### When to use workflows vs direct action

- **Use a workflow** when: the task is recurring, has multiple steps, needs conditions, or should run on a schedule
- **Use direct action** when: it's a one-off task the user asked for right now

## Trigger types

### Hook triggers (automatic)
Handled by the plugin's hooks — fires when Claude uses matching tools:
- `PostToolUse` + `matcher: Bash` + `condition: "git push"` → fires after git push
- `PostToolUse` + `matcher: "Edit|Write"` → fires after file edits
- `Stop` → fires when session ends

### Cron triggers (scheduled via CronCreate)
For polling and recurring tasks. Schedule on session start.

### Manual triggers
User says "run workflow X" or you call `run_workflow` directly.

## Creating workflows for users

When users ask to automate something, create a workflow YAML. Pick the right trigger:

| User says | Trigger type | Example |
|-----------|-------------|---------|
| "run tests after every push" | hook: PostToolUse/Bash/git push | auto-test.yml |
| "lint after edits" | hook: PostToolUse/Edit\|Write | lint-on-edit.yml |
| "check PRs every 10 minutes" | cron: */10 * * * * | pr-watch.yml |
| "morning standup summary" | cron: 57 8 * * 1-5 | morning-triage.yml |
| "watch CI and fix failures" | cron: */5 * * * * | ci-watch.yml |
| "review new issues" | cron: */15 * * * * | issue-watch.yml |

## Polling remote state

For GitHub events (PRs, issues, CI), use cron workflows that poll with `gh` CLI:
- `gh pr list --state open --json number,title,updatedAt,author`
- `gh issue list --state open --json number,title,labels`
- `gh run list --limit 5 --json status,conclusion,headBranch`
- `gh pr checks <number>`

The workflow runs the `gh` command, then an agent step tells Claude what to do with the results.

To avoid acting on the same event twice, agent steps should compare against previous runs. The workflow history (logged in `.claude/workflows/runs/`) provides this context.
