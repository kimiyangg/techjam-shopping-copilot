"""Optional LLM extraction layer for free-form (non-template) messages.

The official evaluator only ever emits templated messages, so this layer is
never on the scored path. It exists so the agent generalizes: when a human
types a real sentence in the demo, Claude extracts the same slot structure
the template parser would have produced.

Degrades to None (deterministic path continues) when the `anthropic` package
is missing, no credentials are configured, the call times out, or anything
else goes wrong. It must never be able to fail a session.
"""
from __future__ import annotations

import json

SYSTEM_PROMPT = (
    "You extract shopping constraints from one customer message in a "
    "conversational product-search session over an apparel catalog. Return "
    "the product category (if stated) and every concrete constraint the "
    "customer expressed: material, color, style, size, use case, brand, or "
    "budget (as 'budget around $X'). Use short phrases likely to appear "
    "verbatim in product listings. If the message retracts an earlier "
    "preference, list only the new one."
)

EXTRACTION_FORMAT = {
    "type": "json_schema",
    "schema": {
        "type": "object",
        "properties": {
            "category": {"type": ["string", "null"]},
            "constraints": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["category", "constraints"],
        "additionalProperties": False,
    },
}


def extract(message: str) -> dict | None:
    """Extract {category, constraints, usage} from free text, or None."""
    try:
        import anthropic
    except ImportError:
        return None
    try:
        client = anthropic.Anthropic()
        response = client.with_options(timeout=8.0, max_retries=0).messages.create(
            model="claude-opus-5",
            max_tokens=2000,
            output_config={"effort": "low", "format": EXTRACTION_FORMAT},
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": message}],
        )
        if response.stop_reason == "refusal":
            return None
        text = next(b.text for b in response.content if b.type == "text")
        data = json.loads(text)
        return {
            "category": data.get("category"),
            "constraints": [c for c in data.get("constraints", []) if isinstance(c, str)],
            "usage": {
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
            },
        }
    except Exception:
        return None
