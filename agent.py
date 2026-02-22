# Self-Critiquing Planner – backward-compatible entry point
# Functionality lives in: planner.py, critic.py, executor.py, app.py
# Preferred: streamlit run app.py
# This file runs app.py so "streamlit run agent.py" still works.

import runpy

if __name__ == "__main__":
    runpy.run_path("app.py", run_name="__main__")
