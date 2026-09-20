# multi-step-langchain-agent

A Trase OS agent bundle: a **two-stage** LangChain agent that makes real LLM
calls through the platform's governed egress proxy.

Companion to [`text-pipeline-agent`](https://github.com/adubashi/text-pipeline-agent),
which is deliberately LLM-free. This one exercises the path that agent avoids:
model egress, tool calling, and multi-stage chaining.

## The two stages

```
stage 1  inspect    ReAct agent + 3 tools  ──▶  raw tool output
stage 2  summarize  agent with NO tools    ──▶  three-line brief
```

Stage 2 has no tools on purpose. It cannot go back to the source, so it can only
work from what stage 1 reported — which means a stage-1 failure shows up in the
stage-2 output instead of being silently papered over.

The tools are deterministic and do no I/O:

| Tool | Does |
| --- | --- |
| `word_stats` | word count, distinct words, mean word length |
| `sha256_hex` | SHA-256 fingerprint of the text |
| `base64_codec` | encode, or decode with `mode="decode"` |

Keeping them free of network calls means that when a run misbehaves, the tools
are never the variable — only the model's choice of which to call.

## Layout

```
trase-agent.yaml      name / framework / entrypoint
requirements.txt      langchain, langchain-openai
agent/main.py         entrypoint shim — aliases the egress env vars
agent/agent.py        the two stages; knows nothing about Trase
agent/tools.py        the three deterministic tools
```

The bundle is at the **repository root**, which onboarding requires.

## Egress

`main.py` aliases the platform's injected variables onto the names the OpenAI
SDK reads:

```
TRASE_OPENAI_BASE_URL  ->  OPENAI_BASE_URL
TRASE_RUN_ID           ->  OPENAI_API_KEY
```

`TRASE_RUN_ID` doubles as the run credential, so it is aliased but never logged.
The agent code itself is stock LangChain — no `base_url` or `api_key` threaded
through it.

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `AGENT_INPUT` | a built-in sample | text to inspect |
| `AGENT_MODEL` | `gpt-4o-mini` | model name, since what the egress proxy accepts varies by environment |

`AGENT_MODEL` is overridable so a model-name mismatch can be fixed without
rebuilding the bundle.

## Run it locally

```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt

export OPENAI_API_KEY=...            # or point at any OpenAI-compatible endpoint
export OPENAI_BASE_URL=...
.venv/bin/python -c "from agent.agent import main; print(main('your text here'))"
```

The tools can be exercised with no model at all:

```bash
.venv/bin/python -c "
from agent.tools import word_stats
print(word_stats.invoke({'text': 'the quick brown fox'}))"
```
