"""Entrypoint: read the step input, run both stages, return the report.

The step's input comes from the platform (``trase_os_sdk.sandbox.read_input``),
so a query sent from Studio or ``trase-os-sdk run-workflow --query`` reaches the
agent. The SDK ships in the platform's base image; it is not in requirements.txt.

The graph export happens at IMPORT time rather than inside run(). The build-time
topology inspector imports this module, looks for a single exported graph, and
calls get_graph() on it. It never calls run(), so anything set up inside run()
does not exist as far as inspection is concerned.
"""

from __future__ import annotations

import json
import logging
from typing import Any

# Exactly ONE graph attribute in this module: the inspector accepts one unambiguous
# exported graph and reports `unsupported` when it finds several. `summarizer` stays
# in agent.agent and is deliberately not re-exported here.
from agent.agent import inspector as agent_graph, main as run_agent  # noqa: F401

log = logging.getLogger(__name__)

DEFAULT_INPUT = (
    "The Antikythera mechanism is an Ancient Greek hand-powered orrery, "
    "described as the oldest known example of an analogue computer. "
    "It was used to predict astronomical positions and eclipses decades in advance."
)

# Keys a trigger body may carry the text under. `user_message` is what
# `trase-os-sdk run-workflow --query` and Studio's manual trigger send.
_TEXT_KEYS = ("user_message", "query", "text", "input")


def _text_from(value: Any) -> str | None:
    """Pull the text to inspect out of whatever shape the step input has."""
    if value is None:
        return None
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, dict):
        for key in _TEXT_KEYS:
            text = value.get(key)
            if isinstance(text, str) and text.strip():
                return text.strip()
        return json.dumps(value) if value else None
    return json.dumps(value)


def _step_input() -> str:
    """The step input from the platform, or the built-in sample when there is none."""
    try:
        from trase_os_sdk.sandbox import NoInputError, read_input
    except ImportError:
        log.warning("trase_os_sdk not importable: using the built-in sample input")
        return DEFAULT_INPUT
    try:
        text = _text_from(read_input())
    except NoInputError:
        log.info("step launched with no input: using the built-in sample input")
        return DEFAULT_INPUT
    if text is None:
        log.info("step input carried no text: using the built-in sample input")
        return DEFAULT_INPUT
    return text


def run() -> str:
    """Called by the platform with no arguments. The return value is the step output."""
    return run_agent(_step_input())
