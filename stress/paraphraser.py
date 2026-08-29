"""Render simulator events as varied, non-templated natural language.

Used two ways:
- the stress harness paraphrases every official-simulator message before the
  agent sees it, destroying the template parser's advantage on purpose;
- the alignment trainer generates unlimited synthetic customer dialogues
  from catalog products to train on.

Deterministic per seed. Content words (materials, colors, feature phrases)
are preserved the way a real shopper would preserve them; the sentence
frames, fillers, and connectives vary.
"""
from __future__ import annotations

import random
import re

BUDGET_RE = re.compile(r"budget around \$([0-9][0-9.,]*)", re.I)
COLOR_RE = re.compile(r"^color:\s*", re.I)

OPENERS = [
    "hey, i'm shopping for {cat}",
    "hi! looking to buy {cat}",
    "i need {cat}",
    "can you help me find {cat}",
    "on the hunt for {cat}",
    "trying to pick out {cat}",
    "do you have {cat}?",
    "i want to get some {cat}",
]
REQUIREMENT_FRAMES = [
    "it really has to be {c}",
    "{c} is a must for me",
    "non-negotiable: {c}",
    "the important thing is {c}",
    "i specifically need {c}",
    "make sure it's {c}",
]
EXPLORING_TAILS = [
    "just browsing around for now",
    "not sure exactly what i want yet",
    "still figuring out what i like",
    "open to ideas honestly",
    "no strong preferences yet, surprise me",
]
DISCLOSURE_FRAMES = [
    "honestly what matters most is {cs}",
    "i'd say i care about {cs}",
    "hmm, mainly {cs}",
    "good question — {cs} for sure",
    "let me think... {cs}",
    "priorities would be {cs}",
]
NO_PREF_FRAMES = [
    "no real preference on {attr}, whatever you think works",
    "i'm easy about {attr}, you pick",
    "don't care much about {attr} honestly",
]
EXHAUSTED_FRAMES = [
    "that's honestly everything i care about",
    "nothing else comes to mind",
    "no, i think i've told you all my must-haves",
]
OVERRIDE_FRAMES = [
    "you know what, scratch that — i actually want {c}",
    "wait, change of plans: {c} instead",
    "forget what i said before, let's go with {c}",
    "actually i changed my mind, i need {c}",
]
NUDGE_FRAMES = [
    "hmm, none of these feel right. ask me something specific?",
    "not quite what i'm after — what else do you want to know?",
]


class Paraphraser:
    def __init__(self, seed: int = 0) -> None:
        self.rng = random.Random(seed)

    def _constraint(self, text: str) -> str:
        match = BUDGET_RE.search(text)
        if match:
            price = float(match.group(1).replace(",", ""))
            style = self.rng.choice(["under ${:.0f}", "around ${:.0f}", "max ${:.0f} or so"])
            return style.format(price + (1 if "under" in style else 0))
        text = COLOR_RE.sub("in ", text)
        return text.lower().strip(" .")

    def _join(self, constraints: list[str]) -> str:
        rendered = [self._constraint(c) for c in constraints]
        if len(rendered) == 1:
            return rendered[0]
        return f"{', '.join(rendered[:-1])} and also {rendered[-1]}"

    def render(self, event: dict) -> str:
        """Paraphrase a parsed simulator event (see starter/parser.py)."""
        rng = self.rng
        kind = event["type"]
        if kind == "initial_buying":
            opener = rng.choice(OPENERS).format(cat=event["category"].lower())
            frame = rng.choice(REQUIREMENT_FRAMES).format(
                c=self._constraint(event["constraints"][0])
            )
            return f"{opener}. {frame}."
        if kind == "initial_exploring":
            opener = rng.choice(OPENERS).format(cat=event["category"].lower())
            return f"{opener} — {rng.choice(EXPLORING_TAILS)}."
        if kind == "initial_override":
            opener = rng.choice(OPENERS).format(cat=event["category"].lower())
            return f"{opener}. {self._constraint(event['constraints'][0])} sounds good."
        if kind == "disclosure":
            return rng.choice(DISCLOSURE_FRAMES).format(cs=self._join(event["constraints"])) + "."
        if kind == "override":
            return rng.choice(OVERRIDE_FRAMES).format(
                c=self._constraint(event["constraints"][0])
            ) + "."
        if kind == "no_preference":
            return rng.choice(NO_PREF_FRAMES).format(attr=event["attribute"]) + "."
        if kind == "exhausted":
            return rng.choice(EXHAUSTED_FRAMES) + "."
        if kind == "nudge":
            return rng.choice(NUDGE_FRAMES)
        return event.get("text", "")
