# Self-Critiquing Planner (GPT-4o)

A **Streamlit** application that turns high-level goals into actionable plans using GPT-4o, then critiques those plans before you approve and (simulated) execute steps. Built around a **Planner → Critic → Human-in-the-loop → Executor** pipeline with optional session memory for adaptive context.

### Quick start

```bash
pip install -r requirements.txt
streamlit run app.py
```

Then open the app in your browser, enter your **OpenAI API key**, describe a goal, and click **Plan & Critique**.

---

## Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [Module Reference](#module-reference)
- [Data Formats](#data-formats)
- [Troubleshooting](#troubleshooting)
- [License](#license)

---

## Features

- **Goal → Plan**: Decompose a natural-language goal into a structured list of steps (no fixed maximum; plans can be long and detailed).
- **Plan → Critique**: A second GPT-4o pass reviews the plan for missing steps, ambiguity, risk, and safety; returns per-step issues and suggested changes.
- **Human-in-the-loop**: You see both plan and critique, can edit the plan JSON, re-run the critic, and approve which steps to “execute.”
- **Simulated execution**: Approved steps are run in a **simulated** mode (shell/code steps are logged, not executed); manual and plan-only steps are handled accordingly.
- **Session memory**: Past sessions (goal, plan, critique, outcome) are stored in `memory.json` and used as adaptive context for future planning.
- **Domain presets**: Optional hints for “Code Refactor,” “Learning Plan,” “Workflow Design,” or “Generic.”
- **Editable plan**: Option to edit the plan JSON before approval and re-critique.

---

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────────────┐     ┌─────────────┐
│   User      │     │   Planner   │     │   Critic             │     │  Executor   │
│   Goal      │────▶│   (GPT-4o)  │────▶│   (GPT-4o)           │────▶│  (simulated)│
└─────────────┘     └─────────────┘     └─────────────────────┘     └─────────────┘
       │                    │                       │                        │
       │                    │                       │                        │
       ▼                    ▼                       ▼                        ▼
  [Domain hint]      [Adaptive context       [Plan + Goal]            [Approved
  [Memory.json]       from memory.json]        → issues/suggestions]    steps only]
```

1. **Planner** (`planner.py`): Takes user goal + optional domain hint + adaptive context from past sessions; returns a JSON plan with `steps` (id, description, type, estimated_risk).
2. **Critic** (`critic.py`): Takes goal + plan; returns JSON with `overall_assessment`, `issues` (per-step), and `suggested_global_changes`.
3. **Human**: Reviews plan and critique, optionally edits plan, approves steps.
4. **Executor** (`executor.py`): “Executes” only approved steps in simulated mode (shell/code → simulated; manual → pending_user; plan → noop).

---

## Prerequisites

- **Python**: 3.8 or higher (3.10+ recommended).
- **OpenAI API key**: Required for Planner and Critic (GPT-4o). Get one at [OpenAI API](https://platform.openai.com/api-keys).
- **Network**: Outbound HTTPS for `api.openai.com`.

---

## Installation

### 1. Clone the repository

```bash
git clone <repository-url>
cd SelfCritiquingPlanner
```

### 2. Create a virtual environment (recommended)

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the application

```bash
streamlit run app.py
```

Alternatively, for backward compatibility:

```bash
streamlit run agent.py
```

The app will open in your browser (default: `http://localhost:8501`).

---

## Configuration

| Item | Where | Description |
|------|--------|-------------|
| **OpenAI API key** | UI (top of page) | Enter in the password field; used only in-session, not persisted to disk. |
| **Memory file** | `config.py` → `MEMORY_PATH` | Default: `memory.json` in the project root. Change here if you want a different path. |
| **Model** | `config.py` → `DEFAULT_MODEL` | Default: `gpt-4o`. Override if you need a different model. |
| **Temperature / Max tokens** | Sidebar | Sliders in the Streamlit UI control LLM behavior for both Planner and Critic. |

No `.env` or config file is required for basic use; the API key is provided through the UI.

---

## Usage

1. **Enter your OpenAI API key** in the text input at the top (required for Plan & Critique).
2. **(Optional)** In the sidebar:
   - Enable **Auto-execute low-risk steps (simulated)** to pre-approve low-risk steps.
   - Enable **Treat all steps as manual** to force all steps to be treated as manual (no shell/code execution simulation).
   - Adjust **Temperature** and **Max tokens**.
   - Choose a **Domain Preset** (Generic, Code Refactor, Learning Plan, Workflow Design).
3. **Describe your goal** in the text area (e.g. *“Refactor my monolithic script into modules with tests.”*).
4. Click **Plan & Critique**. The app will:
   - Build adaptive context from `memory.json` (if any).
   - Call the Planner (GPT-4o) to produce a JSON plan.
   - Call the Critic (GPT-4o) to produce a critique.
5. Review **Proposed Plan (JSON)** and **Critique (JSON)**. You can:
   - Check **Edit plan JSON before approval** to modify the plan and re-run the critic with **Re-run Critique on Current Plan**.
6. In **Step Approval & Execution**, check the steps you want to “execute.”
7. Click **Execute Approved Steps (simulated)**. Results are shown as JSON; the session is appended to `memory.json` for future adaptive context.
8. **(Optional)** Use **Reset Memory (danger)** in the sidebar to clear `memory.json` (sets `sessions` to `[]`).

---

## Project Structure

```
SelfCritiquingPlanner/
├── app.py              # Streamlit UI: goal input, plan/critique display, approval, execution
├── agent.py            # Backward-compatible entry point (runs app.py)
├── config.py           # OpenAI client, API key setter, MEMORY_PATH, DEFAULT_MODEL
├── planner.py          # Planner: goal → JSON plan (GPT-4o)
├── critic.py           # Critic: plan + goal → JSON critique (GPT-4o)
├── executor.py         # Executor: simulated execution of approved steps
├── llm.py              # LLM helpers: call_gpt_4o, fix_json (JSON repair)
├── memory.py           # Memory: load/save memory.json, add_session, build_adaptive_context
├── memory.json         # Persisted sessions (created automatically if missing)
├── requirements.txt    # Python dependencies (openai, streamlit)
└── README.md           # This file
```

---

## Module Reference

| Module | Purpose |
|--------|---------|
| **config** | Holds `OpenAI` client (set via `set_api_key` from UI), `DEFAULT_MODEL` (`gpt-4o`), and `MEMORY_PATH` (`memory.json`). |
| **llm** | `call_gpt_4o(messages, model, temperature, max_tokens)` — chat completion; `fix_json(raw, temperature, max_tokens)` — uses GPT-4o to repair invalid JSON. |
| **planner** | `planner_plan(user_goal, temperature, max_tokens, adaptive_context)` — returns `{ "augmented_goal", "plan" }`; plan has `goal` and `steps`. |
| **critic** | `critic_critique(user_goal, plan, temperature, max_tokens)` — returns critique with `overall_assessment`, `issues`, `suggested_global_changes`. |
| **executor** | `execute_plan(steps)` — returns list of `{ "step", "result" }`; each result has `status` (e.g. `simulated`, `pending_user`, `noop`) and `detail`. |
| **memory** | `load_memory(path)`, `save_memory(data, path)`, `add_session(...)`, `recent_outcomes(limit, path)`, `build_adaptive_context(limit, path)`. |
| **app** | Streamlit app: API key, sidebar settings, goal input, Plan & Critique button, plan/critique display, step approval, Execute button, memory reset. |

---

## Data Formats

### Plan (Planner output)

```json
{
  "goal": "<user goal>",
  "steps": [
    {
      "id": "step-1",
      "description": "Short description of what to do",
      "type": "plan | shell | code | manual",
      "estimated_risk": "low | medium | high"
    }
  ]
}
```

- **type**: `plan` = planning-only; `shell` = shell command; `code` = script/code; `manual` = user does by hand.
- **estimated_risk**: Used for display and for optional auto-approval of low-risk steps when “Auto-execute low-risk steps” is on.

### Critique (Critic output)

```json
{
  "overall_assessment": "Short summary",
  "issues": [
    {
      "step_id": "step-1",
      "severity": "low | medium | high",
      "issue": "Description of the problem",
      "suggested_change": "How to improve or fix"
    }
  ],
  "suggested_global_changes": "Text summary of global improvements"
}
```

### Memory (`memory.json`)

```json
{
  "sessions": [
    {
      "timestamp": "2026-02-23T12:00:00.000000Z",
      "goal": "...",
      "plan": { ... },
      "critique": { ... },
      "outcome": "user_executed"
    }
  ]
}
```

`build_adaptive_context()` turns recent sessions into a short text block passed to the Planner as `[Context from previous sessions]`.

---

## Troubleshooting

| Issue | What to do |
|-------|------------|
| **“OpenAI API key is not set”** | Enter a valid API key in the input at the top and ensure it’s not empty after trimming. |
| **Invalid JSON from Planner/Critic** | The app uses `fix_json()` (GPT-4o) to repair malformed JSON; if it still fails, try again or lower temperature. |
| **Port 8501 in use** | Run `streamlit run app.py --server.port 8502` (or another free port). |
| **Memory not loading** | Ensure `memory.json` exists (it’s created on first use) and is valid JSON with a `sessions` array. |
| **Steps not executing** | Execution is **simulated**: shell/code steps only produce “[SIMULATION] Would run…” messages. |

---

## License

See the repository’s license file, if present. Otherwise, use and modify at your discretion.
