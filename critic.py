"""
Critic: reviews plan, returns JSON critique (GPT-4o).
"""
import json
from typing import Any, Dict

from llm import call_gpt_4o, fix_json

CRITIC_SYSTEM_PROMPT = """
You are a critical reviewer of plans for a developer assistant.

Given a proposed plan in JSON and the original goal, you must:
- Identify missing, redundant, ambiguous, or risky steps.
- Suggest improvements and safer alternatives.
- Flag any step that might cause data loss or security issues.

Return your output strictly as valid JSON with this schema:
{
  "overall_assessment": "short summary",
  "issues": [
    {
      "step_id": "step-1",
      "severity": "low" | "medium" | "high",
      "issue": "short description of the problem",
      "suggested_change": "short suggestion for how to improve or fix it"
    }
  ],
  "suggested_global_changes": "text summary of global improvements"
}

Rules:
- Do NOT add explanations outside the JSON.
- Do NOT wrap JSON in backticks.
- Follow the schema exactly.
"""


def critic_critique(
    user_goal: str,
    plan: Dict[str, Any],
    temperature: float,
    max_tokens: int,
) -> Dict[str, Any]:
    """Call GPT-4o as a critic."""
    plan_str = json.dumps(plan, indent=2)
    messages = [
        {"role": "system", "content": CRITIC_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"User goal:\n{user_goal}\n\nProposed plan JSON:\n{plan_str}",
        },
    ]
    raw = call_gpt_4o(
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    try:
        critique = json.loads(raw)
    except json.JSONDecodeError:
        critique = fix_json(raw, temperature=0.0, max_tokens=max_tokens)
    return critique
