"""SessionStart hook — scan for workflows, report active ones, prompt cron scheduling."""

import sys
import os
import json

# Allow imports from plugin root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.workflow_parser import load_workflows


def main():
    data = {}
    try:
        data = json.loads(sys.stdin.read())
    except Exception:
        pass

    cwd = data.get("cwd", os.getcwd())
    workflows = load_workflows(cwd)

    if not workflows:
        json.dump({"result": "continue", "message": ""}, sys.stdout)
        return

    lines = [f"[Workflows] {len(workflows)} active workflow(s):"]
    cron_workflows = []

    for wf in workflows:
        trigger = wf.get("trigger", {})
        cron_expr = trigger.get("cron", "")
        t_event = trigger.get("event", "")
        t_matcher = trigger.get("matcher", "")
        desc = wf.get("description", "")

        if cron_expr:
            line = f"  - {wf['name']}: cron={cron_expr}"
            cron_workflows.append({"name": wf["name"], "cron": cron_expr, "description": desc})
        else:
            line = f"  - {wf['name']}: trigger={t_event}"
            if t_matcher:
                line += f" matcher={t_matcher}"
        if desc:
            line += f" ({desc})"
        lines.append(line)

    # Prompt Claude to schedule cron workflows
    if cron_workflows:
        lines.append("")
        lines.append("ACTION REQUIRED: Schedule these cron workflows using CronCreate:")
        for cw in cron_workflows:
            lines.append(
                f'  CronCreate(cron: "{cw["cron"]}", '
                f'prompt: "Run the workflow \'{cw["name"]}\' using the run_workflow MCP tool.")'
            )

    result = {
        "result": "continue",
        "message": "\n".join(lines),
    }
    json.dump(result, sys.stdout)


if __name__ == "__main__":
    main()
