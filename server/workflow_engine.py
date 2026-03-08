"""Execute workflows — run steps sequentially with conditions and error handling."""

import os
import json
import subprocess
import time
from datetime import datetime, timezone

from . import condition_eval


def execute_workflow(workflow: dict, context: dict) -> dict:
    """Execute a workflow's steps sequentially.

    context: {cwd: str, hook_event: str, tool_name: str, tool_input: str, ...}
    Returns: {workflow: str, status: str, steps: [...], started: str, finished: str}
    """
    cwd = context.get("cwd", os.getcwd())
    started = datetime.now(timezone.utc).isoformat()
    step_results = {}  # name -> {exit_code, output, status}
    all_steps = []
    overall_status = "success"
    agent_prompts = []

    for step in workflow.get("steps", []):
        if not isinstance(step, dict):
            continue

        step_name = step.get("name", f"step_{len(all_steps)}")
        when = step.get("when", "")

        # Evaluate condition
        if when and not condition_eval.evaluate(str(when), step_results):
            result = {"name": step_name, "status": "skipped", "exit_code": -1, "output": ""}
            step_results[step_name] = result
            all_steps.append(result)
            continue

        # Agent step — can't spawn subagent, collect prompt to return
        if step.get("agent"):
            result = {
                "name": step_name,
                "status": "agent_prompt",
                "exit_code": 0,
                "output": step["agent"],
            }
            agent_prompts.append(step["agent"])
            step_results[step_name] = result
            all_steps.append(result)
            continue

        # Run step — shell command
        cmd = step.get("run", "")
        if not cmd:
            result = {"name": step_name, "status": "skipped", "exit_code": -1, "output": "no command"}
            step_results[step_name] = result
            all_steps.append(result)
            continue

        timeout = int(step.get("timeout", 120))
        on_failure = step.get("on_failure", "stop")
        max_retries = int(step.get("max_retries", 0))

        result = _run_command(cmd, cwd, timeout, on_failure, max_retries, step_name)
        step_results[step_name] = result
        all_steps.append(result)

        if result["status"] == "failed" and on_failure == "stop":
            overall_status = "failed"
            break

    finished = datetime.now(timezone.utc).isoformat()

    execution = {
        "workflow": workflow.get("name", "unknown"),
        "status": overall_status,
        "steps": all_steps,
        "started": started,
        "finished": finished,
    }

    if agent_prompts:
        execution["agent_prompts"] = agent_prompts

    # Log execution
    _log_execution(cwd, execution)

    return execution


def _run_command(cmd: str, cwd: str, timeout: int, on_failure: str,
                 max_retries: int, step_name: str) -> dict:
    """Run a shell command with retry logic."""
    attempts = 0
    max_attempts = 1 + (max_retries if on_failure == "retry" else 0)

    while attempts < max_attempts:
        attempts += 1
        try:
            proc = subprocess.run(
                cmd,
                shell=True,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            exit_code = proc.returncode
            output = (proc.stdout or "") + (proc.stderr or "")
            # Trim output to avoid huge payloads
            if len(output) > 4000:
                output = output[:2000] + "\n...[truncated]...\n" + output[-2000:]

            if exit_code == 0:
                return {
                    "name": step_name,
                    "status": "success",
                    "exit_code": exit_code,
                    "output": output.strip(),
                    "attempts": attempts,
                }
            elif attempts >= max_attempts:
                return {
                    "name": step_name,
                    "status": "failed",
                    "exit_code": exit_code,
                    "output": output.strip(),
                    "attempts": attempts,
                }
        except subprocess.TimeoutExpired:
            if attempts >= max_attempts:
                return {
                    "name": step_name,
                    "status": "timeout",
                    "exit_code": -1,
                    "output": f"Command timed out after {timeout}s",
                    "attempts": attempts,
                }
        except Exception as e:
            if attempts >= max_attempts:
                return {
                    "name": step_name,
                    "status": "error",
                    "exit_code": -1,
                    "output": str(e),
                    "attempts": attempts,
                }

    return {"name": step_name, "status": "error", "exit_code": -1, "output": "unexpected", "attempts": attempts}


def _log_execution(cwd: str, execution: dict):
    """Log workflow execution to .claude/workflows/runs/."""
    runs_dir = os.path.join(cwd, ".claude", "workflows", "runs")
    try:
        os.makedirs(runs_dir, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        wf_name = execution.get("workflow", "unknown").replace(" ", "_")
        filename = f"{ts}_{wf_name}.json"
        filepath = os.path.join(runs_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(execution, f, indent=2)
    except Exception:
        pass  # Don't fail the workflow because of logging


def get_history(cwd: str, limit: int = 10) -> list[dict]:
    """Read recent workflow execution logs."""
    runs_dir = os.path.join(cwd, ".claude", "workflows", "runs")
    if not os.path.isdir(runs_dir):
        return []
    files = sorted(
        [f for f in os.listdir(runs_dir) if f.endswith(".json")],
        reverse=True,
    )
    results = []
    for fname in files[:limit]:
        try:
            with open(os.path.join(runs_dir, fname), "r", encoding="utf-8") as f:
                results.append(json.load(f))
        except Exception:
            continue
    return results
