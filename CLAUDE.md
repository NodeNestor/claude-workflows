# claude-workflows

## Cron-triggered workflows

When a workflow has `trigger: cron: "<expression>"`, use Claude Code's built-in `CronCreate` tool to schedule it.

On session start, if workflows with cron triggers are detected, schedule each one:

```
CronCreate(
  cron: "<the cron expression from the workflow>",
  prompt: "Run the workflow '<workflow_name>' using the run_workflow MCP tool."
)
```

This makes cron workflows work automatically during the session. The cron job fires at the scheduled time, which triggers the workflow via the MCP tool.

## Hook-triggered workflows

Hook triggers (PostToolUse, SessionStart, Stop) are handled automatically by the plugin's hooks — no extra setup needed. They fire when the matching Claude Code event occurs.

## Creating workflows

When the user asks to automate something recurring, create a workflow YAML in `.claude/workflows/`:

- For **event-based** automation (after edits, after push): use hook triggers
- For **time-based** automation (every hour, daily): use cron triggers with `CronCreate`
- For **one-shot** scheduled tasks: use `CronCreate` directly without a workflow file
