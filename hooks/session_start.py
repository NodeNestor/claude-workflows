"""SessionStart hook — scan for workflows and report active ones."""

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
        result = {
            "result": "continue",
            "message": "",
        }
        json.dump(result, sys.stdout)
        return

    lines = [f"[Workflows] {len(workflows)} active workflow(s):"]
    for wf in workflows:
        trigger = wf.get("trigger", {})
        t_event = trigger.get("event", trigger.get("cron", "manual"))
        t_matcher = trigger.get("matcher", "")
        desc = wf.get("description", "")
        line = f"  - {wf['name']}: trigger={t_event}"
        if t_matcher:
            line += f" matcher={t_matcher}"
        if desc:
            line += f" ({desc})"
        lines.append(line)

    result = {
        "result": "continue",
        "message": "\n".join(lines),
    }
    json.dump(result, sys.stdout)


if __name__ == "__main__":
    main()
