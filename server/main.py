"""MCP server for claude-workflows — exposes workflow management tools."""

import os
import sys
import json

# Add parent to path so we can import as package
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.mcp_stdio import MCPServer
from server.workflow_parser import load_workflows, parse_workflow_file, match_trigger
from server.workflow_engine import execute_workflow, get_history
from server.yaml_parser import parse_yaml

mcp = MCPServer("claude-workflows", "1.0.0")


@mcp.tool(
    "list_workflows",
    "List all workflows found in .claude/workflows/ for a project",
    {
        "properties": {
            "project_path": {"type": "string", "description": "Absolute path to the project root"},
        },
        "required": ["project_path"],
    },
)
def list_workflows(project_path: str):
    workflows = load_workflows(project_path)
    if not workflows:
        return "No workflows found in .claude/workflows/"

    lines = [f"Found {len(workflows)} workflow(s):\n"]
    for wf in workflows:
        trigger = wf.get("trigger", {})
        t_event = trigger.get("event", trigger.get("cron", "manual"))
        t_matcher = trigger.get("matcher", "")
        steps_count = len(wf.get("steps", []))
        lines.append(
            f"  - **{wf['name']}**: {wf.get('description', 'No description')}\n"
            f"    Trigger: {t_event}"
            + (f" (matcher: {t_matcher})" if t_matcher else "")
            + f" | Steps: {steps_count}"
            + f"\n    Source: {wf.get('_source', '?')}"
        )

    # Check for paused workflows
    wf_dir = os.path.join(project_path, ".claude", "workflows")
    if os.path.isdir(wf_dir):
        paused = [f for f in os.listdir(wf_dir)
                  if f.endswith(".paused.yml") or f.endswith(".paused.yaml")]
        if paused:
            lines.append(f"\nPaused ({len(paused)}):")
            for p in paused:
                lines.append(f"  - {p}")

    return "\n".join(lines)


@mcp.tool(
    "run_workflow",
    "Manually trigger a workflow by name",
    {
        "properties": {
            "project_path": {"type": "string", "description": "Absolute path to the project root"},
            "workflow_name": {"type": "string", "description": "Name of the workflow to run"},
        },
        "required": ["project_path", "workflow_name"],
    },
)
def run_workflow(project_path: str, workflow_name: str):
    workflows = load_workflows(project_path)
    target = None
    for wf in workflows:
        if wf.get("name") == workflow_name:
            target = wf
            break

    if not target:
        available = [wf.get("name") for wf in workflows]
        return f"Workflow '{workflow_name}' not found. Available: {available}"

    context = {"cwd": project_path, "hook_event": "manual", "tool_name": "", "tool_input": ""}
    result = execute_workflow(target, context)

    lines = [f"Workflow **{workflow_name}** — {result['status'].upper()}"]
    for step in result.get("steps", []):
        icon = "OK" if step["status"] == "success" else "SKIP" if step["status"] == "skipped" else "FAIL"
        lines.append(f"  [{icon}] {step['name']}: {step['status']}")
        if step.get("output") and step["status"] != "skipped":
            # Show first few lines of output
            out_lines = step["output"].split("\n")[:5]
            for ol in out_lines:
                lines.append(f"       {ol}")

    if result.get("agent_prompts"):
        lines.append("\nAgent actions requested:")
        for prompt in result["agent_prompts"]:
            lines.append(f"  -> {prompt}")

    return "\n".join(lines)


@mcp.tool(
    "workflow_history",
    "Show recent workflow execution history",
    {
        "properties": {
            "project_path": {"type": "string", "description": "Absolute path to the project root"},
            "limit": {"type": "number", "description": "Max entries to show (default 10)"},
        },
        "required": ["project_path"],
    },
)
def workflow_history(project_path: str, limit: int = 10):
    history = get_history(project_path, int(limit))
    if not history:
        return "No workflow execution history found."

    lines = [f"Recent workflow executions ({len(history)}):\n"]
    for entry in history:
        step_summary = []
        for s in entry.get("steps", []):
            step_summary.append(f"{s['name']}:{s['status']}")
        lines.append(
            f"  {entry.get('started', '?')} | {entry.get('workflow', '?')} | "
            f"{entry.get('status', '?').upper()} | "
            f"Steps: {', '.join(step_summary)}"
        )
    return "\n".join(lines)


@mcp.tool(
    "create_workflow",
    "Create a new workflow YAML file",
    {
        "properties": {
            "project_path": {"type": "string", "description": "Absolute path to the project root"},
            "name": {"type": "string", "description": "Workflow name (used as filename)"},
            "description": {"type": "string", "description": "What this workflow does"},
            "trigger": {
                "type": "object",
                "description": "Trigger config: {event, matcher?, condition?} or {cron}",
            },
            "steps": {
                "type": "array",
                "description": "List of step objects: [{name, run?, agent?, when?, timeout?, on_failure?, max_retries?}]",
            },
        },
        "required": ["project_path", "name", "trigger", "steps"],
    },
)
def create_workflow(project_path: str, name: str, description: str = "",
                    trigger: dict = None, steps: list = None):
    wf_dir = os.path.join(project_path, ".claude", "workflows")
    os.makedirs(wf_dir, exist_ok=True)

    filename = name.replace(" ", "-").lower() + ".yml"
    filepath = os.path.join(wf_dir, filename)

    if os.path.exists(filepath):
        return f"Workflow file already exists: {filepath}"

    # Build YAML manually
    lines = [f"name: {name}"]
    if description:
        lines.append(f"description: {description}")

    if trigger:
        lines.append("trigger:")
        for k, v in trigger.items():
            if isinstance(v, str) and (" " in v or '"' in v):
                lines.append(f'  {k}: "{v}"')
            else:
                lines.append(f"  {k}: {v}")

    if steps:
        lines.append("steps:")
        for step in steps:
            first = True
            for k, v in step.items():
                prefix = "  - " if first else "    "
                first = False
                if isinstance(v, str) and (" " in v or '"' in v or "'" in v):
                    lines.append(f'{prefix}{k}: "{v}"')
                else:
                    lines.append(f"{prefix}{k}: {v}")

    content = "\n".join(lines) + "\n"

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    return f"Created workflow: {filepath}\n\n```yaml\n{content}```"


@mcp.tool(
    "pause_workflow",
    "Pause a workflow by adding .paused suffix to its file",
    {
        "properties": {
            "project_path": {"type": "string", "description": "Absolute path to the project root"},
            "workflow_name": {"type": "string", "description": "Name of the workflow to pause"},
        },
        "required": ["project_path", "workflow_name"],
    },
)
def pause_workflow(project_path: str, workflow_name: str):
    workflows = load_workflows(project_path)
    for wf in workflows:
        if wf.get("name") == workflow_name:
            src = wf["_source"]
            base, ext = os.path.splitext(src)
            dst = base + ".paused" + ext
            os.rename(src, dst)
            return f"Paused workflow '{workflow_name}': {dst}"
    return f"Workflow '{workflow_name}' not found or already paused."


@mcp.tool(
    "resume_workflow",
    "Resume a paused workflow by removing .paused suffix",
    {
        "properties": {
            "project_path": {"type": "string", "description": "Absolute path to the project root"},
            "workflow_name": {"type": "string", "description": "Name of the workflow to resume"},
        },
        "required": ["project_path", "workflow_name"],
    },
)
def resume_workflow(project_path: str, workflow_name: str):
    wf_dir = os.path.join(project_path, ".claude", "workflows")
    if not os.path.isdir(wf_dir):
        return "No workflows directory found."

    for fname in os.listdir(wf_dir):
        if ".paused." in fname:
            # Parse to check name
            filepath = os.path.join(wf_dir, fname)
            wf = parse_workflow_file(filepath)
            if wf and wf.get("name") == workflow_name:
                new_name = fname.replace(".paused", "")
                dst = os.path.join(wf_dir, new_name)
                os.rename(filepath, dst)
                return f"Resumed workflow '{workflow_name}': {dst}"

    return f"No paused workflow named '{workflow_name}' found."


if __name__ == "__main__":
    mcp.run()
