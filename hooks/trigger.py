"""PostToolUse / Stop hook — check triggers and execute matching workflows."""

import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.workflow_parser import load_workflows, match_trigger
from server.workflow_engine import execute_workflow


def main():
    data = {}
    try:
        data = json.loads(sys.stdin.read())
    except Exception:
        pass

    cwd = data.get("cwd", os.getcwd())
    hook_event = data.get("hook_event_name", "")
    tool_name = data.get("tool_name", "")

    # Build tool_input string for matching
    tool_input = data.get("tool_input", "")
    if isinstance(tool_input, dict):
        tool_input = json.dumps(tool_input)
    elif not isinstance(tool_input, str):
        tool_input = str(tool_input)

    workflows = load_workflows(cwd)
    if not workflows:
        json.dump({"result": "continue"}, sys.stdout)
        return

    messages = []
    for wf in workflows:
        if not match_trigger(wf, hook_event, tool_name, tool_input):
            continue

        context = {
            "cwd": cwd,
            "hook_event": hook_event,
            "tool_name": tool_name,
            "tool_input": tool_input,
        }
        result = execute_workflow(wf, context)

        # Build summary
        status = result.get("status", "unknown").upper()
        lines = [f"[Workflow: {wf['name']}] {status}"]

        for step in result.get("steps", []):
            s = step["status"]
            if s == "skipped":
                continue
            icon = "OK" if s == "success" else "PROMPT" if s == "agent_prompt" else "FAIL"
            lines.append(f"  [{icon}] {step['name']}: {step.get('output', '')[:200]}")

        if result.get("agent_prompts"):
            lines.append("\nPlease perform these actions:")
            for prompt in result["agent_prompts"]:
                lines.append(f"  -> {prompt}")

        messages.append("\n".join(lines))

    if messages:
        json.dump({"result": "continue", "message": "\n\n".join(messages)}, sys.stdout)
    else:
        json.dump({"result": "continue"}, sys.stdout)


if __name__ == "__main__":
    main()
