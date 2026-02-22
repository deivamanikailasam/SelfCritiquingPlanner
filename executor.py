"""
Executor: safe, simulated step execution.
"""
from typing import Any, Dict, List


def execute_step(step: Dict[str, Any]) -> Dict[str, Any]:
    step_type = step.get("type", "plan")
    description = step.get("description", "")

    if step_type == "shell":
        return {
            "status": "simulated",
            "detail": f"[SIMULATION] Would run shell command: {description}",
        }
    elif step_type == "code":
        return {
            "status": "simulated",
            "detail": f"[SIMULATION] Would execute code/script: {description}",
        }
    elif step_type == "manual":
        return {
            "status": "pending_user",
            "detail": f"User should perform this step manually: {description}",
        }
    else:  # "plan" or unknown
        return {
            "status": "noop",
            "detail": f"Planning-only step, nothing executed: {description}",
        }


def execute_plan(steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    results = []
    for step in steps:
        result = execute_step(step)
        results.append({"step": step, "result": result})
    return results
