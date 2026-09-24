import json
import os
from typing import Optional

import requests

from .models import Lead, Signals


def optional_classification(lead: Lead, signals: Signals) -> Optional[str]:
    """Return a short local-only LLM note, or None when Ollama is not enabled/available."""
    if os.getenv("USE_OLLAMA", "0") != "1":
        return None
    prompt = ("Give one concise GTM research note. Do not claim the fictional contact is real. "
              f"Company: {lead.company}; industry: {lead.industry}; signals: {json.dumps(signals.model_dump())}")
    try:
        response = requests.post(
            f"{os.getenv('OLLAMA_URL', 'http://localhost:11434')}/api/generate",
            json={"model": os.getenv("OLLAMA_MODEL", "llama3.2:3b"), "prompt": prompt, "stream": False},
            timeout=45,
        )
        response.raise_for_status()
        return response.json().get("response", "").strip()[:600] or None
    except requests.RequestException:
        return "Ollama was enabled but unavailable; deterministic routing was used."
