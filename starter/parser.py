"""Template parser for the simulator's five sentence patterns.

Every simulator message is one of a handful of f-string templates
(see evaluator/local_evaluator.py: initial_message, customer_reply,
behavior_for). Each parse returns an event dict; anything unrecognized
falls through as {"type": "freeform"} for a later extraction layer.
"""
from __future__ import annotations

import re

EXPLORING_RE = re.compile(r"^I'm looking for (?P<category>.+), but I'm still exploring\.$")
BUYING_RE = re.compile(r"^I'm looking for (?P<category>.+?)\. A key requirement is: (?P<constraint>.+)\.$")
OVERRIDE_START_RE = re.compile(r"^I'm looking for (?P<category>.+?)\. (?P<old_value>.+)$")
MATTERS_RE = re.compile(r"^For that, what matters is: (?P<payload>.+)\.$")
OVERRIDE_RE = re.compile(r"^Actually, ignore my earlier preference\. What I need is: (?P<new_value>.+)\.$")
NO_PREF_RE = re.compile(r"^I don't have a preference for (?P<attribute>.+); please use your judgment\.$")
NO_ADDITIONAL_RE = re.compile(r"^I don't have an additional preference for (?P<attribute>.+)\.$")
NOT_RIGHT_RE = re.compile(r"^Those options are not quite right yet\.")


def parse_message(message: str, turn: int) -> dict:
    message = message.strip()
    if turn == 1:
        match = EXPLORING_RE.match(message)
        if match:
            return {"type": "initial_exploring", "category": match["category"]}
        match = BUYING_RE.match(message)
        if match:
            return {
                "type": "initial_buying",
                "category": match["category"],
                "constraints": [match["constraint"]],
            }
        match = OVERRIDE_START_RE.match(message)
        if match:
            return {
                "type": "initial_override",
                "category": match["category"],
                "constraints": [match["old_value"].rstrip(".")],
            }
    match = MATTERS_RE.match(message)
    if match:
        # `"; "` is the simulator's join separator, but a single constraint may
        # contain it too, so this split is ambiguous. We hand the raw payload
        # along; the agent re-segments it against the known key set
        # (IntentIndex.segment). The naive split stays as the value for callers
        # without an index (e.g. stress/paraphraser.py).
        payload = match["payload"]
        return {
            "type": "disclosure",
            "constraints": payload.split("; "),
            "payload": payload,
        }
    match = OVERRIDE_RE.match(message)
    if match:
        return {"type": "override", "constraints": [match["new_value"]]}
    match = NO_PREF_RE.match(message)
    if match:
        return {"type": "no_preference", "attribute": match["attribute"]}
    match = NO_ADDITIONAL_RE.match(message)
    if match:
        return {"type": "exhausted", "attribute": match["attribute"]}
    if NOT_RIGHT_RE.match(message):
        return {"type": "nudge"}
    return {"type": "freeform", "text": message}
