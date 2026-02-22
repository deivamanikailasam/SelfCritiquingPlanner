"""
Planner: decomposes goal into JSON steps (GPT-4o).
"""
import json
from typing import Any, Dict

from llm import call_gpt_4o, fix_json

PLANNER_SYSTEM_PROMPT = """
You are a senior planning agent for a developer.

Your job:
- Decompose the user's goal into a full set of concrete, executable steps.
- Use as many steps as the goal truly needs—there is NO maximum. If the goal is big or detailed, break it into many steps (e.g. 15, 20, 30+). Do not limit yourself to a small number; match the level of detail the user is asking for.
- Prefer steps that can be executed by tools (e.g., shell commands, scripts) or by the user.
- Include every meaningful sub-task; avoid merging distinct steps into one unless they are trivial.
- Be cautious with anything that could affect files, data, or security.

Return your output strictly as valid JSON with this schema:
{
  "goal": "<copy of user goal>",
  "steps": [
    {
      "id": "step-1",
      "description": "Short description of what to do",
      "type": "plan" | "shell" | "code" | "manual",
      "estimated_risk": "low" | "medium" | "high"
    }
  ]
}

Rules:
- Do NOT add explanations outside the JSON.
- Do NOT wrap JSON in backticks.
- Follow the schema exactly.
- Number steps as step-1, step-2, step-3, ... with no upper limit on how many you create.
"""


def planner_plan(
    user_goal: str,
    temperature: float,
    max_tokens: int,
    adaptive_context: str,
) -> Dict[str, Any]:
    """
    Call GPT-4o as a planner, with adaptive context appended to the goal.
    """
    augmented_goal = (
        f"{user_goal}\n\n[Context from previous sessions]\n{adaptive_context}"
    )

    messages = [
        {"role": "system", "content": PLANNER_SYSTEM_PROMPT},
        {"role": "user", "content": augmented_goal},
    ]
    raw = call_gpt_4o(
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    try:
        plan = json.loads(raw)
    except json.JSONDecodeError:
        plan = fix_json(raw, temperature=0.0, max_tokens=max_tokens)
    return {"augmented_goal": augmented_goal, "plan": plan}
