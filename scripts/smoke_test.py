"""Smoke test: verifies the API key works for gemini-4-argon and the Antigravity managed agent."""
import sys
import time

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
client = genai.Client(http_options=types.HttpOptions(timeout=15 * 60 * 1000))
ok = True

t = time.time()
try:
    r = client.interactions.create(
        model="gemini-4-argon",
        input="Reply with exactly: ARGON_OK",
        generation_config={"thinking_level": "low"},
    )
    print(f"[model gemini-4-argon] {r.status} in {time.time()-t:.1f}s -> {r.output_text!r}")
except Exception as e:
    ok = False
    print(f"[model gemini-4-argon] FAILED: {e}")

t = time.time()
try:
    r = client.interactions.create(
        agent="antigravity-preview-09-2026",
        agent_config={"type": "antigravity", "model": "gemini-4-argon"},
        input="Run `python3 -c 'print(6*7)'` in the shell and reply with only the printed number.",
        environment="remote",
    )
    print(f"[agent antigravity+argon] {r.status} in {time.time()-t:.1f}s env={r.environment_id} -> {r.output_text!r}")
    print("  steps:", [s.type for s in (r.steps or [])])
except Exception as e:
    ok = False
    print(f"[agent antigravity+argon] FAILED: {e}")

sys.exit(0 if ok else 1)
