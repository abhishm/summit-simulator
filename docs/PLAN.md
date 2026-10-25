# Plan: Summit Simulator (decisions from the grill-me session, 11:15 AM)

## One-liner
An organizer of an AI-safety summit enters a guest list and a goal. The system simulates the day, scores how much consensus and inclusion it achieves, and Gemini 4 Argon revises the agenda in a loop until it improves. The organizer approves the final plan.

## Decisions

| # | Topic | Decision |
|---|---|---|
| 1 | User | Organizer of a 1-day AI-safety summit with **8–12 guests** from labs, government and civil society. Pain: "regulators and lab CEOs talked past each other; civil society never got a word in." |
| 2 | Personas | **Role-based**, not real people, e.g. "EU AI Office regulator" or "frontier-lab CEO". Grounded in Deep Research on real public positions. Profile positions and priorities, never personality traits (avoids the banned "personality analyzer" category). Same JSON schema either way. |
| 3 | Decision space | Fixed venue: plenary hall, 3 breakout rooms, coffee lounge. **5 blocks**; each block sets `format` (plenary / breakouts of 3–4 / 1:1 coffee pairs), `topic`, and `groupings`. The plan is one JSON object. |
| 4 | Simulation | **One `gemini-3.8-flash` call per group per block**, run in parallel within a block. Returns a short transcript plus per-guest state updates (stance on 3–4 key issues, agreements). State carries across blocks. About 20 calls and 30–60 s per sim. Argon doesn't play guests. |
| 5 | Scoring (0–100) | Consensus 40 (stances move closer + explicit agreements) · Inclusion 30 (**lowest** "felt heard" of any guest, rated by a separate `gemini-3.5-flash-lite` judge from transcripts) · Airtime fairness 15 (word-count spread) · Cross-faction contact 15 (share of cross-faction pairs who met). Everything except "felt heard" is computed in code. |
| 6 | Optimizer | Naive starting plan (all plenary, seated by faction). Each round, `gemini-4-argon` (`thinking_level="high"`) gets plan + transcripts + score breakdown and returns a critique and a revised plan JSON. Rounds are chained with `previous_interaction_id`. Up to 4 rounds, stop early if the score stops improving, keep the best plan. |
| 7 | Managed Agents | **Core:** `deep-research-preview-04-2026` writes a cited brief per role (positions, red lines, priorities, what they'd trade), pre-run in the background; one new role is added live in the demo. **Stretch:** Antigravity creates guest briefing packets and the run-of-show from the approved plan. |
| 8 | 3D | Single-file **Three.js** isometric venue. Avatars are colored by faction, move between rooms each block, conversations show as lines, a halo shows "felt heard". Toggle to replay the starting plan vs the best plan. **Stretch:** headless screenshot of each block → Argon multimodal critique. |
| 9 | Stack | Python + **FastAPI** (uv), `asyncio` for parallel calls, **SSE** to stream round updates. Frontend is one `index.html` with Three.js from a CDN. Prototype in Jupyter first. An **"Approve plan"** button is required before export. No Streamlit. |
| 10 | Demo (≤3 min) | 0:00–0:20 user + problem · 0:20–0:40 add a guest role (Deep Research starts live; the demo uses a cached result) · 0:40–2:20 **live** loop: starting plan + 2 rounds, `medium` thinking, 3 blocks · 2:20–3:00 switch to the **pre-run 4-round result** + 3D replay, then Approve. A `DEMO_MODE` flag replays a recorded run if the network fails. |
| 11 | Team / time | Solo + Copilot. See the timeline below. |

## Timeline
- **11:15:** start Deep Research for ~10 roles (background).
- **11:15–12:30:** schemas, simulator, scorer in Jupyter, using placeholder personas.
- **12:30–1:30:** starting plan + Argon loop → first real score improvement.
- **1:30–2:45:** FastAPI + SSE, Three.js replay, Approve button.
- **2:45–3:30:** pre-run the full 4-round result, demo mode, offline fallback.
- **3:30–4:00:** README ("built today" note) + rehearsal. **4:00 feature freeze.**
- **4:00–5:00:** 1-minute video + submission form.

Stretch goals (Antigravity packets, screenshot critique) only happen if we're ahead at 2:45.

## Persona research
`scripts/research_personas.py` started 10 Deep Research jobs at 11:23 AM. Job IDs are in `data/personas/jobs.json`. Run `uv run python scripts/research_personas.py collect` to save the finished reports to `data/personas/<role>.md`. Run `start <role_id>` to re-run a single role.

## Open items
- Discord: waiting for the organizers' answer on the "personality analyzer" question. Role-based personas are the safe default regardless.
- The API key is in `.env` as `GOOGLE_API_KEY`. Run `uv run python scripts/smoke_test.py` to verify access.
