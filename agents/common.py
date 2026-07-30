from __future__ import annotations

import json
import os
import re
from typing import Any

from config import get_ai_provider_chain, get_deepseek_model, get_groq_model, get_openai_model


def _extract_json(text: str) -> dict[str, Any]:
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        raise ValueError("No JSON object found in model response.")
    return json.loads(match.group(0))


def _call_groq(instructions: str, prompt: str) -> str:
    from openai import OpenAI

    client = OpenAI(
        api_key=os.getenv("GROQ_API_KEY"),
        base_url="https://api.groq.com/openai/v1",
    )
    response = client.chat.completions.create(
        model=get_groq_model(),
        messages=[
            {"role": "system", "content": instructions},
            {"role": "user", "content": prompt},
        ],
        temperature=0,
    )
    return response.choices[0].message.content or ""


def _call_deepseek(instructions: str, prompt: str) -> str:
    from openai import OpenAI

    client = OpenAI(
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        base_url="https://api.deepseek.com",
    )
    response = client.chat.completions.create(
        model=get_deepseek_model(),
        messages=[
            {"role": "system", "content": instructions},
            {"role": "user", "content": prompt},
        ],
        temperature=0,
    )
    return response.choices[0].message.content or ""


def _call_openai(instructions: str, prompt: str) -> str:
    from openai import OpenAI

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = client.responses.create(
        model=get_openai_model(),
        instructions=instructions,
        input=prompt,
    )
    return response.output_text


_PROVIDER_CALLS = {"groq": _call_groq, "deepseek": _call_deepseek, "openai": _call_openai}


def _generate_ai_text(instructions: str, prompt: str) -> tuple[str, str]:
    """Try each configured provider in order (e.g. groq -> deepseek -> openai).

    Returns (text, provider_used). Raises the last provider's error if every
    configured provider fails, so callers can fall back to the local parser.
    """
    chain = get_ai_provider_chain()
    if not chain:
        raise RuntimeError("No external AI provider is configured.")
    last_error: Exception | None = None
    for provider in chain:
        try:
            return _PROVIDER_CALLS[provider](instructions, prompt), provider
        except Exception as error:  # try the next provider in the chain
            last_error = error
    assert last_error is not None
    raise last_error
