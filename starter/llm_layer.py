"""Optional LLM extraction layer for free-form (non-template) messages.

The official evaluator only ever emits templated messages, so this layer is
never on the scored path. It exists so the agent generalizes: when a human
types a real sentence in the demo, Claude extracts the same slot structure
the template parser would have produced.

Degrades to None (deterministic path continues) when the `anthropic` package
is missing, no credentials are configured, the call times out, or anything
else goes wrong. It must never be able to fail a session — but every such
failure is logged at debug level, because a layer that swallows every error
silently is indistinguishable from one that never worked.
"""
from __future__ import annotations

import json
import logging
import os

log = logging.getLogger(__name__)

MODEL = os.environ.get("SHOPPING_COPILOT_MODEL", "claude-opus-5")
# Thinking is on by default on Claude Opus 5 and is billed against max_tokens,
# so a budget sized for the JSON alone can be consumed before any text block is
# emitted — leaving a response with no text at all. Leave room for both.
MAX_TOKENS = 8000
TIMEOUT_SECONDS = 30.0

SYSTEM_PROMPT = (
    "You extract shopping constraints from one customer message in a "
    "conversational product-search session over an apparel catalog. Return "
    "the product category (empty string if not stated) and every concrete "
    "constraint the customer expressed: material, color, style, size, use "
    "case, brand, or budget (as 'budget around $X'). Use short phrases likely "
    "to appear verbatim in product listings. If the message retracts an "
    "earlier preference, list only the new one."
)

EXTRACTION_FORMAT = {
    "type": "json_schema",
    "schema": {
        "type": "object",
        "properties": {
            # A ["string", "null"] union is not reliably accepted by structured
            # outputs; an empty string carries the same "not stated" signal.
            "category": {"type": "string"},
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
        log.debug("anthropic SDK not installed; free-form extraction disabled")
        return None
    try:
        client = anthropic.Anthropic()
        response = client.with_options(
            timeout=TIMEOUT_SECONDS, max_retries=0
        ).messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            output_config={"effort": "low", "format": EXTRACTION_FORMAT},
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": message}],
        )
        if response.stop_reason == "refusal":
            log.debug("extraction refused: %s", response.stop_details)
            return None
        text = next((b.text for b in response.content if b.type == "text"), None)
        if not text:
            # Most likely stop_reason == "max_tokens": thinking consumed the
            # budget before the JSON was produced.
            log.debug("extraction returned no text block (stop=%s)", response.stop_reason)
            return None
        data = json.loads(text)
        category = data.get("category") or None
        return {
            "category": category,
            "constraints": [c for c in data.get("constraints", []) if isinstance(c, str)],
            "usage": {
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
            },
        }
    except Exception:
        log.debug("free-form extraction failed; falling back", exc_info=True)
        return None
