# AGENTS.md

Context for any coding agent on this project. Full details are in `docs/HACKATHON.md`. **The build plan and its decisions are in `docs/PLAN.md`. Follow it.**

## What this is

An entry for the **Gemini 4 Argon SF Hackathon** (Cerebral Valley + Google DeepMind), held on **Sunday, Oct 25, 2026**.

- **Hard deadline: submissions are due at 5:00 PM PT.**
- **Feature freeze: 4:00 PM.** After that, only fix bugs, polish the demo and write docs.

## What must be true at the end

- A **live demo** that runs with real inputs in under 3 minutes, without slides. This is 50% of the score.
- The project uses **`gemini-4-argon`**, ideally with **Managed Agents** (`antigravity-preview-09-2026`). Managed Agents have a separate $5K prize.
- There is a **real verification loop**: the system checks its own output against a pass/fail signal and fixes it.
- It solves a concrete problem for a **specific, nameable person**, in one of these tracks:
  1. **Million Token Engineering:** a huge codebase task (migration, translation, upgrade), measured against a baseline.
  2. **More Dimensions:** 3D, games, worlds or video that the system renders, watches, critiques and fixes in a loop.
- It's clearly only possible because of Argon: 1M-token context, long decode, frontier reasoning or multimodal orchestration.
- A person approves any action that affects external systems, money or private data.

## Rules (breaking them means disqualification)

- The repo must be **public**. Never commit secrets: use `.env` (gitignored) or the Credentials API.
- **Only new work.** Everything here is built today. Keep the README clear about what was built at the hackathon.
- **Banned project types:** basic RAG, Streamlit apps, image analyzers, chatbots for education, mental health, medical advice, nutrition, job screening, personality or sports, and anything where a dashboard is the main feature.

## Environment

- Python 3.12, managed with **uv** (`pyproject.toml`, `.venv/`). Add packages with `uv add <pkg>` and run commands with `uv run ...`. Don't use pip directly.
- Start JupyterLab with `uv run jupyter lab --port 8888`.
- The API key is in `.env` as `GOOGLE_API_KEY=...` (it's gitignored). Load it with `python-dotenv`. `genai.Client()` reads either `GOOGLE_API_KEY` or `GEMINI_API_KEY`.
- **Smoke test:** `uv run python scripts/smoke_test.py` checks the key with a plain `gemini-4-argon` call and an Antigravity managed-agent run (using Argon) in a remote sandbox. It exits non-zero on failure. Run it first if API calls start failing. It last passed at 11:00 AM PT on Oct 25 (Argon about 5s, agent about 22s).

## Coding conventions for Gemini

- Use the **Interactions API** (`client.interactions.create`), with `google-genai` or `@google/genai` **version 2.3.0 or later**. Before writing Gemini code, load the `gemini-api-dev` skill (or `gemini-live-api-dev` for real-time voice and video). Both are in `.agents/skills/`.
- Control reasoning with `thinking_level` (`low` | `medium` | `high`). **Don't use** `thinking_budget`, `temperature`, `top_p`, `top_k` or `cached_content`. Argon ignores or deprecates them.
- For output over 64K tokens or long `high` runs, use `background=True`, set `max_output_tokens`, and poll `interactions.get`. Otherwise set HTTP timeouts of 15–20 minutes.
- Keep `docs/HACKATHON.md` as the source of truth for the model IDs table.

## Working style

- Agree on the plan first, then build in long autonomous stretches.
- Every feature should have a check: tests, a script or a headless browser run.
- Prefer a small scope that reliably demos well over a large, fragile one.
- Log Argon feedback (what worked, what broke, what you wished existed) in `docs/FEEDBACK.md` as you go. The submission form requires it.
- When you hit a non-obvious quirk, add it under "Lessons learned" below.

## Project: Summit Simulator (what's built)

- `app/models.py` holds the data models. `app/personas.py` turns Deep Research reports into personas. `app/simulate.py` simulates with Flash, judges with Flash-Lite and scores. `app/optimize.py` runs the Argon critique/revise loop. `app/server.py` is the FastAPI + SSE server. `web/index.html` is the Three.js UI, with three.js vendored in `web/vendor/`.
- Run the app: `uv run uvicorn app.server:app --port 8000`, then open http://localhost:8000. Use `DEMO_MODE=1` for an offline replay of the best saved run.
- Pre-run for the demo: `uv run python scripts/run_optimize.py --rounds 4 --blocks 5 --thinking high --name demo-5block`, which writes to `data/runs/`.
- Persona research: `uv run python scripts/research_personas.py start|collect`, then `uv run python -m app.personas`.
- UI check: a Playwright headless screenshot. Use the default `chromium.launch()`, because the swiftshader GL flags hang `goto`.

## Submission checklist

Team name · all members added · description · public GitHub URL · 1-minute YouTube demo (unlisted) · Google products used · Argon feedback.

## Lessons learned

- `.env` uses `GOOGLE_API_KEY`, not `GEMINI_API_KEY`. No rename is needed because the SDK reads both.
- Verified working with `google-genai` 2.33.0: `client.interactions.create(model="gemini-4-argon", generation_config={"thinking_level": "low"})` and `client.interactions.create(agent="antigravity-preview-09-2026", agent_config={"type": "antigravity", "model": "gemini-4-argon"}, environment="remote")`. The agent's code runs appear in `r.steps` as `code_execution_call` and `code_execution_result` steps. Reuse `r.environment_id` and `previous_interaction_id` to continue in the same sandbox.
- The managed agent call is synchronous and took about 22s for a trivial task. Create the client with a long HTTP timeout: `genai.Client(http_options=types.HttpOptions(timeout=15*60*1000))`.
- Run modules from the repo root (`uv run python -m app.x`, or scripts that add the root to `sys.path`). Scripts in /tmp can't import `app`.
- LLM output schemas: avoid `dict` fields in structured-output models. Use lists of `{key, value}` objects and convert them in code.
- Timings: a Flash group simulation takes about 10–15s per block (groups run in parallel). A 5-block round with the judge takes about 70s, and an Argon revision takes about 60s at `medium`. A 3-block, 1-round live run takes about 2 min.
- The simulator is gameable. Argon quickly learns tricks like "instruct everyone to state a compromise". WORLD_RULES now say facilitation can't compel positions, the last block is forced to be a closing plenary, and the judge rubric is calibrated. Keep the simulator honest, or the score jumps look fake (the first version went from 50 to 98 in one round).
- three.js from the unpkg CDN hung headless Chrome, so it's vendored to `web/vendor/`, which also keeps it working offline.
