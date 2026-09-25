"""Entrypoint shim: point the stock OpenAI SDK at the governed egress proxy.

The platform injects TRASE_OPENAI_BASE_URL and TRASE_RUN_ID. The OpenAI SDK reads
OPENAI_BASE_URL and OPENAI_API_KEY. Aliasing the two here keeps the agent itself
stock -- wrap, don't edit.

TRASE_RUN_ID doubles as the run credential, so it is aliased but never logged.

Both the aliasing and the graph export happen at IMPORT time rather than inside
run(). The build-time topology inspector imports this module, looks for a single
exported graph, and calls get_graph() on it. It never calls run(), so anything set
up inside run() does not exist as far as inspection is concerned.
"""

import os


def _configure_openai_environment() -> None:
    """Alias the platform's variables onto the ones the OpenAI SDK reads.

    Runs at import because the graph below is constructed at import, and
    ChatOpenAI raises at construction when it cannot resolve an API key.
    Topology inspection imports this module without runtime credentials and never
    invokes the graph, so a placeholder stands in; a real run overwrites it with
    the injected run credential.
    """
    base_url = os.environ.get("TRASE_OPENAI_BASE_URL")
    run_id = os.environ.get("TRASE_RUN_ID")
    if base_url:
        os.environ["OPENAI_BASE_URL"] = base_url
    if run_id:
        os.environ["OPENAI_API_KEY"] = run_id
    else:
        os.environ.setdefault("OPENAI_API_KEY", "topology-inspection-only")


_configure_openai_environment()

# Exactly ONE graph attribute in this module: the inspector accepts one unambiguous
# exported graph and reports `unsupported` when it finds several. `summarizer` stays
# in agent.agent and is deliberately not re-exported here.
from agent.agent import inspector as agent_graph, main as run_agent  # noqa: E402

DEFAULT_INPUT = (
    "The Antikythera mechanism is an Ancient Greek hand-powered orrery, "
    "described as the oldest known example of an analogue computer. "
    "It was used to predict astronomical positions and eclipses decades in advance."
)


def run() -> str:
    """Called by the platform with no arguments."""
    return run_agent(os.environ.get("AGENT_INPUT") or DEFAULT_INPUT)
