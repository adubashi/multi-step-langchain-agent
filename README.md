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
requirements.txt      langchain, langchain-google-genai, google-genai
agent/main.py         entrypoint — reads the step input, returns the report
agent/agent.py        the two stages, on Gemini via Vertex AI
agent/tools.py        the three deterministic tools
```

The bundle is at the **repository root**, which onboarding requires.

## Model egress (Vertex AI)

The model is Gemini on Vertex AI, reached through the platform's governance
gateway. The sandbox holds no Google key. `agent.py` builds the model with two
platform-injected values:

| Constructor argument | Platform variable | Why |
| --- | --- | --- |
| `credentials=Credentials(token=...)` | `TRASE_RUN_CREDENTIAL` | How the gateway identifies this run. The gateway swaps it for a real Google token upstream. |
| `base_url=` | `TRASE_VERTEX_BASE_URL` | The gateway's Vertex route. google-genai has no env var for its base URL. |

`project` and `location` come from `GOOGLE_CLOUD_PROJECT` / `GOOGLE_CLOUD_LOCATION`,
which the platform also injects.

Use `TRASE_RUN_CREDENTIAL`, **not** `TRASE_RUN_ID`. The run id is for correlation
only; the gateway refuses a call that presents it as the key
(`egress.callerUnidentified`, 403).

## Input

`main.py` reads the step input with `trase_os_sdk.sandbox.read_input()` (the SDK
ships in the platform's base image). It takes the text from a plain string, or
from `user_message` / `query` / `text` / `input` in a JSON body. `user_message`
is what `trase-os-sdk run-workflow --query "..."` sends. With no input it falls
back to a built-in sample.

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `AGENT_MODEL` | `gemini-2.5-flash` | model name, overridable without a rebuild |

## Run it locally

Against Vertex directly, with your own Google credentials (no gateway):

```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt

export GOOGLE_CLOUD_PROJECT=your-project
export TRASE_RUN_CREDENTIAL=$(gcloud auth print-access-token)
.venv/bin/python -c "from agent.agent import main; print(main('your text here'))"
```

Leave `TRASE_VERTEX_BASE_URL` unset and the client calls Vertex's public endpoint.

The tools can be exercised with no model at all:

```bash
.venv/bin/python -c "
from agent.tools import word_stats
print(word_stats.invoke({'text': 'the quick brown fox'}))"
```
