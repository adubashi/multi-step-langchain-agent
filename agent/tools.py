"""Deterministic tools the agent can call. No network, no secrets.

Kept free of I/O on purpose: when a run misbehaves, the tools are never the
variable — only the model's choice of which to call and with what.
"""

from __future__ import annotations

import base64
import hashlib
import re

from langchain_core.tools import tool


@tool
def word_stats(text: str) -> str:
    """Count words, distinct words and mean word length in TEXT."""
    words = re.findall(r"[a-z0-9']+", text.lower())
    if not words:
        return "words=0 unique=0 avg_len=0"
    avg = round(sum(len(w) for w in words) / len(words), 2)
    return f"words={len(words)} unique={len(set(words))} avg_len={avg}"


@tool
def sha256_hex(text: str) -> str:
    """Return the SHA-256 hex digest of TEXT. Useful as a content fingerprint."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@tool
def base64_codec(text: str, mode: str = "encode") -> str:
    """Base64-encode TEXT, or decode it when MODE is 'decode'."""
    if mode == "decode":
        try:
            return base64.b64decode(text.encode("ascii")).decode("utf-8", "replace")
        except Exception as exc:  # noqa: BLE001 - surfaced to the model, not raised
            return f"decode failed: {exc}"
    return base64.b64encode(text.encode("utf-8")).decode("ascii")


ALL_TOOLS = [word_stats, sha256_hex, base64_codec]
