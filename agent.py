# app.py
#
# Self-Critiquing Planner (GPT-4o, single file)
#
# - Planner: decomposes goal into JSON steps
# - Critic: reviews plan, returns JSON critique
# - HITL: Streamlit UI for approval/editing
# - Executor: safe, simulated step execution
# - Memory: JSON file of past sessions for light adaptation
#
# Requirements (example):
#   pip install streamlit openai python-dotenv
#
# Usage:
#   export OPENAI_API_KEY="sk-..."   # or use a .env file
#   streamlit run app.py
#

import json
import os
from datetime import datetime
from typing import Any, Dict, List

import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

# -------------------------------------------------------------------
# Environment & OpenAI client setup
# -------------------------------------------------------------------

load_dotenv()  # loads from .env if present[cite:37][cite:43]

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    st.warning(
        "OPENAI_API_KEY is not set. "
        "Set it in your environment or in a .env file."
    )

# The official OpenAI client automatically reads OPENAI_API_KEY from env[cite:33][cite:41]
client = OpenAI()

DEFAULT_MODEL = "gpt-4o"

# -------------------------------------------------------------------
# Prompts
# -------------------------------------------------------------------

PLANNER_SYSTEM_PROMPT = """
You are a senior planning agent for a developer.

Your job:
- Decompose the user's goal into a concise set of concrete, executable steps.
- Prefer steps that can be executed by tools (e.g., shell commands, scripts) or by the user.
- Minimize unnecessary steps.
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
"""

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

JSON_FIX_SYSTEM_PROMPT = """
You are a JSON fixer.
The user will provide some text that should have been JSON.
Your job is to return only valid JSON that best matches the intended structure.
Do NOT include any explanations, notes, or markdown. Only raw JSON.
"""

# -------------------------------------------------------------------
# LLM helpers
# -------------------------------------------------------------------


def call_gpt_4o(
    messages: List[Dict[str, str]],
    model: str = DEFAULT_MODEL,
    temperature: float = 0.2,
    max_tokens: int = 2048,
) -> str:
    """
    Wrapper around OpenAI chat.completions for GPT-4o[cite:31][cite:32][cite:33][cite:41].
    """
    completion = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return completion.choices[0].message.content


def fix_json(raw: str, temperature: float, max_tokens: int) -> Dict[str, Any]:
    """
    Ask GPT-4o to repair invalid JSON into valid JSON.
    """
    fixed = call_gpt_4o(
        messages=[
            {"role": "system", "content": JSON_FIX_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Fix this into valid JSON:\n{raw}",
            },
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return json.loads(fixed)


# -------------------------------------------------------------------
# Memory store (JSON file)
# -------------------------------------------------------------------

MEMORY_PATH = "memory.json"


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


# -------------------------------------------------------------------
# Planner and Critic
# -------------------------------------------------------------------


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


def critic_critique(
    user_goal: str,
    plan: Dict[str, Any],
    temperature: float,
    max_tokens: int,
) -> Dict[str, Any]:
    """
    Call GPT-4o as a critic.
    """
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


# -------------------------------------------------------------------
# Executor (safe, simulated)
# -------------------------------------------------------------------


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


# -------------------------------------------------------------------
# Streamlit UI
# -------------------------------------------------------------------

st.set_page_config(
    page_title="Self-Critiquing Planner (GPT-4o)",
    layout="wide",
)

st.title("🧠 Self-Critiquing Planner (GPT‑4o, 2026-style)")
st.write(
    "Planner → Critic → Human‑in‑the‑loop → Executor, powered by GPT‑4o."
)

# Sidebar settings
with st.sidebar:
    st.header("Execution Settings")
    auto_execute = st.checkbox("Auto-execute low-risk steps (simulated)", value=False)
    manual_only = st.checkbox("Treat all steps as manual (no shell/code)", value=False)

    st.header("Model Parameters")
    temp = st.slider(
        "Temperature", min_value=0.0, max_value=1.0, value=0.2, step=0.05
    )
    max_tokens = st.slider(
        "Max tokens", min_value=256, max_value=4096, value=2048, step=256
    )

    st.header("Domain Preset")
    preset = st.selectbox(
        "Preset",
        ["Generic", "Code Refactor", "Learning Plan", "Workflow Design"],
    )

    if st.button("Reset Memory (danger)"):
        save_memory({"sessions": []}, path=MEMORY_PATH)
        st.success("Memory reset (memory.json cleared).")

# Build domain hint
domain_hint = ""
if preset == "Code Refactor":
    domain_hint = "Focus on modularization, tests, and CI/CD safety."
elif preset == "Learning Plan":
    domain_hint = "Focus on daily/weekly learning blocks with concrete resources."
elif preset == "Workflow Design":
    domain_hint = "Focus on repeatable processes, time-blocking, and clear checklists."

# Show recent sessions
with st.expander("Recent Sessions (for adaptation)", expanded=False):
    recents = recent_outcomes(limit=5, path=MEMORY_PATH)
    if not recents:
        st.write("No previous sessions yet.")
    else:
        for s in recents:
            ts = s.get("timestamp", "")
            g = s.get("goal", "")
            outcome = s.get("outcome", "unknown")
            st.markdown(
                f"- **{ts}** – Goal: {g[:80]}... Outcome: `{outcome}`"
            )

user_goal_input = st.text_area(
    "Describe your goal",
    placeholder="Example: 'Refactor my monolithic script into modules with tests.'",
    height=120,
)

if "last_result" not in st.session_state:
    st.session_state["last_result"] = None

# Compose full goal with domain hint
if user_goal_input.strip():
    if domain_hint:
        full_goal = (
            user_goal_input.strip() + f"\n\n[Domain hint] {domain_hint}"
        )
    else:
        full_goal = user_goal_input.strip()
else:
    full_goal = ""

# Plan & Critique button
if st.button("Plan & Critique", type="primary") and full_goal:
    with st.spinner("Planning and critiquing with GPT‑4o..."):
        adaptive_context = build_adaptive_context(limit=5, path=MEMORY_PATH)
        plan_result = planner_plan(
            user_goal=full_goal,
            temperature=temp,
            max_tokens=max_tokens,
            adaptive_context=adaptive_context,
        )
        plan = plan_result["plan"]
        critique = critic_critique(
            user_goal=full_goal,
            plan=plan,
            temperature=temp,
            max_tokens=max_tokens,
        )
        result = {
            "user_goal": full_goal,
            "augmented_goal": plan_result["augmented_goal"],
            "plan": plan,
            "critique": critique,
        }
        st.session_state["last_result"] = result

result = st.session_state.get("last_result")

if result:
    st.markdown("---")
    st.subheader("Plan & Critique")

    col1, col2 = st.columns(2)

    # JSON plan (with optional editing)
    with col1:
        st.markdown("### Proposed Plan (JSON)")
        editable_plan_json = st.checkbox(
            "Edit plan JSON before approval", value=False
        )
        plan_str = json.dumps(result["plan"], indent=2)
        if editable_plan_json:
            plan_str = st.text_area(
                "Edit Plan JSON", value=plan_str, height=300
            )
            try:
                result["plan"] = json.loads(plan_str)
            except json.JSONDecodeError:
                st.error(
                    "Invalid JSON in plan editor. Reverting to previous plan."
                )
        st.code(json.dumps(result["plan"], indent=2), language="json")

    # JSON critique (with re-run button)
    with col2:
        st.markdown("### Critique (JSON)")
        st.code(json.dumps(result["critique"], indent=2), language="json")
        if st.button("Re-run Critique on Current Plan"):
            with st.spinner("Re-critiquing with GPT‑4o..."):
                new_critique = critic_critique(
                    user_goal=result["user_goal"],
                    plan=result["plan"],
                    temperature=temp,
                    max_tokens=max_tokens,
                )
                result["critique"] = new_critique
                st.session_state["last_result"] = result
                st.experimental_rerun()

    # Human-readable summaries
    st.markdown("### Human-Readable Plan")
    for step in result["plan"].get("steps", []):
        st.markdown(
            f"- **{step.get('id')}** "
            f"({step.get('type')} / risk: {step.get('estimated_risk')}): "
            f"{step.get('description')}"
        )

    st.markdown("### Human-Readable Critique Summary")
    st.write(result["critique"].get("overall_assessment", ""))
    for issue in result["critique"].get("issues", []):
        st.markdown(
            f"- Step `{issue.get('step_id')}` "
            f"[{issue.get('severity')}] – {issue.get('issue')} "
            f"→ _Suggested_: {issue.get('suggested_change')}"
        )

    # Step approval & execution
    st.markdown("---")
    st.subheader("Step Approval & Execution")

    steps = result["plan"].get("steps", [])
    approved_ids: List[str] = []

    for step in steps:
        step_id = step.get("id")
        desc = step.get("description", "")
        risk = step.get("estimated_risk", "unknown")
        step_type = step.get("type", "plan")

        col_a, col_b, col_c, col_d = st.columns([3, 1, 1, 1])

        with col_a:
            st.markdown(f"**{step_id}** – {desc}")
        with col_b:
            st.markdown(f"Risk: `{risk}`")
        with col_c:
            st.markdown(f"Type: `{step_type}`")
        with col_d:
            default_approved = risk == "low" and auto_execute
            approve = st.checkbox(
                f"Approve {step_id}",
                key=f"approve_{step_id}",
                value=default_approved,
            )
            if approve:
                approved_ids.append(step_id)

    if manual_only:
        st.info(
            "Manual-only mode is enabled: shell/code steps will be treated as manual in the executor."
        )

    if st.button("Execute Approved Steps (simulated)"):
        with st.spinner("Executing approved steps (simulated)..."):
            # Filter approved steps
            selected = [s for s in steps if s.get("id") in approved_ids]

            # Optionally treat shell/code as manual
            if manual_only:
                for s in selected:
                    if s.get("type") in ("shell", "code"):
                        s["type"] = "manual"

            execution_results = execute_plan(selected)

            # Store session (outcome can be refined based on user feedback)
            add_session(
                goal=result["user_goal"],
                plan=result["plan"],
                critique=result["critique"],
                outcome="user_executed",
                path=MEMORY_PATH,
            )

            st.markdown("### Execution Results")
            st.code(json.dumps(execution_results, indent=2), language="json")

else:
    st.info("Enter a goal and click 'Plan & Critique' to get started.")
