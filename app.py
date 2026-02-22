#
# Self-Critiquing Planner (GPT-4o) – Streamlit UI
#
# Planner → Critic → Human-in-the-loop → Executor
#
# Usage: streamlit run app.py
#

import json
from typing import List

import streamlit as st

from config import MEMORY_PATH, set_api_key
from critic import critic_critique
from executor import execute_plan
from memory import add_session, build_adaptive_context, recent_outcomes, save_memory
from planner import planner_plan

# -------------------------------------------------------------------
# Page config & title
# -------------------------------------------------------------------

st.set_page_config(
    page_title="Self-Critiquing Planner (GPT-4o)",
    layout="wide",
)

st.title("🧠 Self-Critiquing Planner (GPT‑4o, 2026-style)")
st.write(
    "Planner → Critic → Human‑in‑the‑loop → Executor, powered by GPT‑4o."
)

# -------------------------------------------------------------------
# Layman's explanations: What is the Plan? What is the Critic?
# -------------------------------------------------------------------

with st.expander("📖 What is the Plan / Steps? What is the Critic? (plain English)", expanded=True):
    st.markdown("""
    **What is the Plan / Steps?**  
    The **plan** is your goal broken down into a clear list of **steps**—small, doable actions you can follow one by one.  
    Think of it like a recipe: instead of “make dinner,” you get “chop onions,” “heat the pan,” “add oil,” etc.  
    Each step has:
    - **id** — e.g. step-1, step-2 (so we can refer to it).
    - **description** — what to do in plain language.
    - **type** — whether it’s a shell command, code/script, something you do by hand, or a planning-only note.
    - **estimated_risk** — low / medium / high, so you know where to be extra careful.

    There is **no fixed maximum** number of steps: if your goal is big or detailed, the planner can give you many steps (e.g. 20, 30, or more) so you don’t miss anything.

    **What is the Critic?**  
    The **critic** is a second pass over the plan. It doesn’t run anything—it **reviews** the plan like a careful colleague would.  
    It looks for: missing steps, unclear or risky steps, things that could cause data loss or security issues, and suggests better or safer alternatives.  
    You get an **overall assessment** plus **per-step issues** (with severity and suggested changes).  
    Use it to improve the plan before you approve and run any steps.
    """)

# -------------------------------------------------------------------
# API key input (at the beginning)
# -------------------------------------------------------------------

if "openai_api_key" not in st.session_state:
    st.session_state["openai_api_key"] = ""

api_key = st.text_input(
    "OpenAI API key",
    type="password",
    placeholder="sk-...",
    help="Your key is used only in this session and not stored.",
    key="api_key_input",
)
# Persist key when user enters it; use persisted key when input is empty (e.g. after rerun)
if api_key and api_key.strip():
    st.session_state["openai_api_key"] = api_key.strip()
    set_api_key(api_key.strip())
elif st.session_state["openai_api_key"]:
    set_api_key(st.session_state["openai_api_key"])
else:
    set_api_key("")
    st.info("Enter your OpenAI API key above to use Plan & Critique.")

# -------------------------------------------------------------------
# Sidebar settings
# -------------------------------------------------------------------

with st.sidebar:
    st.header("Execution Settings")
    auto_execute = st.checkbox("Auto-execute low-risk steps (simulated)", value=False)
    manual_only = st.checkbox("Treat all steps as manual (no shell/code)", value=False)

    st.header("Model Parameters")
    temp = st.slider(
        "Temperature", min_value=0.0, max_value=1.0, value=0.2, step=0.05
    )
    max_tokens = st.slider(
        "Max tokens (higher = longer plans allowed)",
        min_value=1024,
        max_value=8192,
        value=4096,
        step=512,
    )

    st.header("Domain Preset")
    PRESET_OPTIONS = ["Generic", "Code Refactor", "Learning Plan", "Workflow Design"]
    preset_index = st.selectbox(
        "Preset",
        range(len(PRESET_OPTIONS)),
        format_func=lambda i: PRESET_OPTIONS[i],
        key="preset_select",
    )
    preset = PRESET_OPTIONS[preset_index]

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

# -------------------------------------------------------------------
# Recent sessions expander
# -------------------------------------------------------------------

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

# -------------------------------------------------------------------
# Goal input
# -------------------------------------------------------------------

user_goal_input = st.text_area(
    "Describe your goal",
    placeholder="Example: 'Refactor my monolithic script into modules with tests.'",
    height=120,
)

if "last_result" not in st.session_state:
    st.session_state["last_result"] = None

if user_goal_input.strip():
    full_goal = (
        user_goal_input.strip() + f"\n\n[Domain hint] {domain_hint}"
        if domain_hint
        else user_goal_input.strip()
    )
else:
    full_goal = ""

# -------------------------------------------------------------------
# Plan & Critique button
# -------------------------------------------------------------------

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

# -------------------------------------------------------------------
# Plan & Critique display
# -------------------------------------------------------------------

if result:
    st.markdown("---")
    st.subheader("Plan & Critique")

    col1, col2 = st.columns(2)

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
                st.rerun()

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

    # -------------------------------------------------------------------
    # Step approval & execution
    # -------------------------------------------------------------------

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
            selected = [s for s in steps if s.get("id") in approved_ids]

            if manual_only:
                for s in selected:
                    if s.get("type") in ("shell", "code"):
                        s["type"] = "manual"

            execution_results = execute_plan(selected)

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
