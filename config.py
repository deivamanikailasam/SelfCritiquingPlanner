"""
OpenAI client setup. API key is set from the UI (app.py).
"""
from openai import OpenAI

client = None
DEFAULT_MODEL = "gpt-4o"
MEMORY_PATH = "memory.json"


def set_api_key(api_key: str) -> None:
    """Set the OpenAI client with the given API key (called from UI)."""
    global client
    if api_key and api_key.strip():
        client = OpenAI(api_key=api_key.strip())
    else:
        client = None
