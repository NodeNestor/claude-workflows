"""Parse workflow YAML files into structured workflow objects."""

import os
import glob as globmod
from . import yaml_parser


def parse_workflow_file(filepath: str) -> dict:
    """Parse a single workflow YAML file. Returns workflow dict or None on error."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            text = f.read()
        wf = yaml_parser.parse_yaml(text)
        if not isinstance(wf, dict):
            return None
        # Attach source path
        wf["_source"] = filepath
        wf.setdefault("name", os.path.splitext(os.path.basename(filepath))[0])
        wf.setdefault("description", "")
        wf.setdefault("trigger", {})
        wf.setdefault("steps", [])
        # Normalize steps
        for step in wf["steps"]:
            if isinstance(step, dict):
                step.setdefault("timeout", 120)
                step.setdefault("on_failure", "stop")
                step.setdefault("max_retries", 0)
        return wf
    except Exception:
        return None


def load_workflows(cwd: str) -> list[dict]:
    """Load all workflows from .claude/workflows/*.yml in the given directory."""
    wf_dir = os.path.join(cwd, ".claude", "workflows")
    if not os.path.isdir(wf_dir):
        return []
    workflows = []
    for pattern in ("*.yml", "*.yaml"):
        for filepath in globmod.glob(os.path.join(wf_dir, pattern)):
            # Skip paused workflows
            basename = os.path.basename(filepath)
            if basename.endswith(".paused.yml") or basename.endswith(".paused.yaml"):
                continue
            wf = parse_workflow_file(filepath)
            if wf:
                workflows.append(wf)
    return workflows


def match_trigger(workflow: dict, hook_event: str, tool_name: str = "",
                  tool_input: str = "") -> bool:
    """Check if a workflow's trigger matches the current hook event."""
    trigger = workflow.get("trigger", {})
    if not trigger:
        return False

    # Event must match
    event = trigger.get("event", "")
    if event != hook_event:
        return False

    # Matcher check (tool name pattern)
    matcher = trigger.get("matcher", "")
    if matcher and tool_name:
        import re
        if not re.search(matcher, tool_name):
            return False
    elif matcher and not tool_name:
        return False

    # Condition check (regex on tool_input)
    condition = trigger.get("condition", "")
    if condition:
        import re
        input_str = tool_input if isinstance(tool_input, str) else str(tool_input)
        if not re.search(condition, input_str):
            return False

    return True
