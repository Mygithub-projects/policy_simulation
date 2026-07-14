from __future__ import annotations

import json
import os
import re
from typing import Any

from config import get_ai_model, get_ai_provider


def _extract_json(text: str) -> dict[str, Any]:
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        raise ValueError("No JSON object found in model response.")
    return json.loads(match.group(0))


def _generate_ai_text(instructions: str, prompt: str) -> str:
    """Call the configured provider while keeping provider details out of agents."""
    from openai import OpenAI

    provider = get_ai_provider()
    model = get_ai_model()
    if provider == "groq":
        client = OpenAI(
            api_key=os.getenv("GROQ_API_KEY"),
            base_url="https://api.groq.com/openai/v1",
        )
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": instructions},
                {"role": "user", "content": prompt},
            ],
            temperature=0,
        )
        return response.choices[0].message.content or ""
    if provider == "openai":
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        response = client.responses.create(
            model=model,
            instructions=instructions,
            input=prompt,
        )
        return response.output_text
    raise RuntimeError("No external AI provider is configured.")
