"""Entrypoint shim: point the stock OpenAI SDK at the governed egress proxy.

The platform injects TRASE_OPENAI_BASE_URL and TRASE_RUN_ID. The OpenAI SDK reads
OPENAI_BASE_URL and OPENAI_API_KEY. Aliasing the two here keeps the agent itself
stock — wrap, don't edit.

TRASE_RUN_ID doubles as the run credential, so it is aliased but never logged.
"""

import os


def run() -> str:
    """Called by the platform with no arguments."""
    os.environ["OPENAI_BASE_URL"] = os.environ["TRASE_OPENAI_BASE_URL"]
    os.environ["OPENAI_API_KEY"] = os.environ["TRASE_RUN_ID"]

    from agent.agent import main

    return main(os.environ.get("AGENT_INPUT") or DEFAULT_INPUT)


DEFAULT_INPUT = (
    "The Antikythera mechanism is an Ancient Greek hand-powered orrery, "
    "described as the oldest known example of an analogue computer. "
    "It was used to predict astronomical positions and eclipses decades in advance."
)
