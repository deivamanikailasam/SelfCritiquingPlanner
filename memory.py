"""
Memory store: JSON file of past sessions for light adaptation.
"""
import json
import os
from datetime import datetime
from typing import Any, Dict, List

from config import MEMORY_PATH


def init_memory_file(path: str = MEMORY_PATH) -> None:
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"sessions": []}, f)


def load_memory(path: str = MEMORY_PATH) -> Dict[str, Any]:
    init_memory_file(path)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_memory(data: Dict[str, Any], path: str = MEMORY_PATH) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def add_session(
    goal: str,
    plan: Dict[str, Any],
    critique: Dict[str, Any],
    outcome: str,
    path: str = MEMORY_PATH,
) -> None:
    data = load_memory(path)
    data["sessions"].append(
        {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "goal": goal,
            "plan": plan,
            "critique": critique,
            "outcome": outcome,
        }
    )
    save_memory(data, path)


def recent_outcomes(limit: int = 5, path: str = MEMORY_PATH) -> List[Dict[str, Any]]:
    data = load_memory(path)
    return data["sessions"][-limit:]


def build_adaptive_context(limit: int = 5, path: str = MEMORY_PATH) -> str:
    sessions = recent_outcomes(limit=limit, path=path)
    if not sessions:
        return "No previous sessions."
    lines: List[str] = []
    for s in sessions:
        outcome = s.get("outcome", "unknown")
        goal = s.get("goal", "")
        summary = s.get("critique", {}).get("overall_assessment", "")
        lines.append(
            f"- Goal: {goal[:80]}... | Outcome: {outcome} | Critique summary: {summary[:120]}..."
        )
    return "Recent history:\n" + "\n".join(lines)
