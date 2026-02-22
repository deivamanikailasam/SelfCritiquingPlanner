"""
LLM helpers: OpenAI client wrapper, JSON fixer.
"""
import json
from typing import Any, Dict, List

import config

JSON_FIX_SYSTEM_PROMPT = """
You are a JSON fixer.
The user will provide some text that should have been JSON.
Your job is to return only valid JSON that best matches the intended structure.
Do NOT include any explanations, notes, or markdown. Only raw JSON.
"""


def call_gpt_4o(
    messages: List[Dict[str, str]],
    model: str = None,
    temperature: float = 0.2,
    max_tokens: int = 2048,
) -> str:
    """Wrapper around OpenAI chat.completions for GPT-4o."""
    if model is None:
        model = config.DEFAULT_MODEL
    if config.client is None:
        raise RuntimeError(
            "OpenAI API key is not set. Enter your API key in the input at the top of the page."
        )
    completion = config.client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return completion.choices[0].message.content


def fix_json(raw: str, temperature: float, max_tokens: int) -> Dict[str, Any]:
    """Ask GPT-4o to repair invalid JSON into valid JSON."""
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
