"""An ordinary two-stage LangChain agent. Nothing here knows it runs on Trase.

Stage 1 (inspect)   — a tool-using ReAct agent that measures the input text.
Stage 2 (summarize) — a second agent that turns stage 1's raw findings into a
                      short brief. It has no tools, so it cannot go back to the
                      source; it can only work from what stage 1 reported.

The two stages are genuinely chained: stage 2's prompt is built from stage 1's
output, so a failure in stage 1 is visible in stage 2's result rather than
silently skipped.

The model is Gemini on Vertex AI, reached through the platform's governance
gateway. Two constructor arguments are platform-shaped (see _model below); the
platform injects every value they read, and the sandbox never holds a Google key.
"""

from __future__ import annotations

import os

from google.oauth2.credentials import Credentials
from langchain.agents import create_agent
from langchain_google_genai import ChatGoogleGenerativeAI

from agent.tools import ALL_TOOLS

# Overridable without a rebuild: which model the Vertex connector accepts can vary
# by environment.
MODEL = os.environ.get("AGENT_MODEL", "gemini-2.5-flash")

# The graphs are built at import, which the build-time topology inspector also does
# -- without a sandbox's environment. These placeholders let construction succeed
# there; the inspector never invokes the model, and a real run overrides all three.
_INSPECTION_ONLY = "topology-inspection-only"

INSPECT_PROMPT = """You are a text inspector with three tools.

Call word_stats to measure the text, sha256_hex to fingerprint it, and
base64_codec to encode the first few words. Use every tool at least once.

Then report the raw results as plain lines, one per tool, with no commentary."""

SUMMARIZE_PROMPT = """You are a technical writer.

You are given raw tool output from an inspection stage. Write exactly three
lines:

CONTENT: what the source text is about, in one sentence
MEASURES: the word and character figures, quoted exactly as reported
FINGERPRINT: the first 12 characters of the SHA-256 digest

Do not invent figures. If something is missing from the input, write "not reported"."""


def _model() -> ChatGoogleGenerativeAI:
    """Gemini on Vertex, through the governance gateway.

    - ``credentials``: the run credential the platform injects as
      TRASE_RUN_CREDENTIAL. It is how the gateway identifies this run; the gateway
      swaps it for a real Google token upstream, so it never reaches Google. It
      also keeps google-genai from searching for Google credentials, which a
      sandbox correctly does not have.
    - ``base_url``: TRASE_VERTEX_BASE_URL, the gateway's Vertex route. google-genai
      has no environment variable for its base URL, so it is passed here.
    """
    return ChatGoogleGenerativeAI(
        model=MODEL,
        vertexai=True,
        project=os.environ.get("GOOGLE_CLOUD_PROJECT", _INSPECTION_ONLY),
        location=os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1"),
        credentials=Credentials(token=os.environ.get("TRASE_RUN_CREDENTIAL", _INSPECTION_ONLY)),
        base_url=os.environ.get("TRASE_VERTEX_BASE_URL"),
    )


def build_inspector():
    """Stage 1: a ReAct agent with the deterministic toolset."""
    return create_agent(_model(), tools=ALL_TOOLS, system_prompt=INSPECT_PROMPT)


def build_summarizer():
    """Stage 2: no tools — it can only use what stage 1 handed it."""
    return create_agent(_model(), tools=[], system_prompt=SUMMARIZE_PROMPT)


# Constructed at import, not per call. The build-time topology inspector imports the
# entrypoint module and calls get_graph() on an exported graph; it never invokes
# factories, so a graph built inside main() is invisible to it and the build records
# no topology.
inspector = build_inspector()
summarizer = build_summarizer()


def _last_message(result) -> str:
    return result["messages"][-1].content


def main(text: str) -> str:
    """Run both stages and return a report showing each stage's output."""
    inspection = _last_message(
        inspector.invoke(
            {"messages": [{"role": "user", "content": f"Inspect this text:\n\n{text}"}]}
        )
    )

    brief = _last_message(
        summarizer.invoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": (
                            f"Source text:\n{text}\n\n"
                            f"Inspection tool output:\n{inspection}"
                        ),
                    }
                ]
            }
        )
    )

    return "\n".join(
        [
            "=== STAGE 1: inspection (tool calls) ===",
            inspection,
            "",
            "=== STAGE 2: brief ===",
            brief,
        ]
    )
