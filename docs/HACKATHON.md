# Gemini 4 Argon SF Hackathon: full reference

Sources: `details.pdf` (Cerebral Valley participant guide) and `docs/builder_guide.pdf` (Google builder guide).

## Event

- **Date:** Sunday, Oct 25, 2026, at Shack15, 1 Ferry Building Suite 201, San Francisco
- **Organizers:** Cerebral Valley + Google DeepMind
- **Discord:** https://discord.gg/Qr5KBzGm. Ask Google questions in #google-deepmind and CV questions in #questions (ping @CV).
- **Contact:** gina@cerebralvalley.ai

### Schedule

| Time | Event |
|---|---|
| 10:30 AM | Hacking begins |
| 1:00 PM | Lunch |
| **5:00 PM** | **Project submissions due** |
| 5:00–7:00 PM | Round 1 judging (in groups across rooms) |
| 7:00–8:00 PM | Final round (top 6, on stage) |
| 8:15 PM | Winners announced |

Internal target: **feature freeze at 4:00 PM**. Spend 4:00–5:00 on the demo video, README and submission form.

## Problem statements (build at least one)

1. **Million Token Engineering.** Argon leads on codebase understanding, with up to 1M continuous output tokens in a single response. Build systems that work across hundreds of files and keep interfaces consistent. Good targets are long-deferred work: legacy migrations, language translations, framework upgrades. **Pick a monumental task, do it, and measure the improvement over a baseline.**
2. **More Dimensions.** Argon also leads on long video understanding and can generate high-fidelity 3D games and procedural worlds in a single pass. A single pass is only the first draft. **Build a system that renders what it made, watches the result, critiques it against the goal and fixes it in a loop.**

## Rules

- Repository **must be public**.
- Teams have 1–4 members.
- **New work only.** The demo must show only what was built during the hackathon, and judges must be able to tell clearly what is new. If they can't, the team is disqualified immediately.
- No projects that violate legal, ethical or platform policies, or that use code, data or assets you don't have rights to.

### Projects to avoid

These are not allowed:

- AI mental health advisor
- Basic RAG apps
- Streamlit apps
- Image analyzers
- "AI for Education" chatbot
- AI job application screener
- AI nutrition coach
- Personality analyzers
- Anything that gives medical advice
- Dashboard-as-main-feature
- Sports analyzers or coaches

## Judging

**Round 1:** about 3 minutes of live demo, then 1–2 minutes of Q&A.

| Weight | Criterion | Question judges ask |
|---|---|---|
| **50%** | Working live demo | Does it run live with real inputs? Does it use `gemini-4-argon`, Managed Agents or companion models effectively, **with a real verification loop**? |
| 25% | Problem and usefulness | Does it solve a concrete problem for a specific person, in one of the tracks? Could it become a real product or open-source tool? |
| 15% | Originality ("never built before") | Is it only possible because of Argon's 1M unified context, long decode, frontier reasoning or multimodal orchestration? |
| 10% | Clarity of pitch | Does it show who the user is, and demo the product clearly in 3 minutes **without slides**? |

**Round 2:** the top 6 teams demo on stage, with the same format and criteria **weighted equally**.

The builder guide's 4 tests for a strong project:

1. It solves a specific problem for a real, nameable person.
2. It needs Argon: long-horizon coding, autonomous verification loops, multi-file synthesis, 3D/WebGPU generation or multi-agent orchestration.
3. It keeps a person in control of actions that affect external systems, money or private data.
4. It runs live with real inputs in under 3 minutes.

## Prizes

| Prize | Amount |
|---|---|
| 1st place | $7,500 |
| 2nd place | $5,000 |
| 3rd place | $2,500 |
| **Best use of Managed Agents** (separate prize) | **$5,000** |

## Submission form (all fields required)

- [ ] Team name
- [ ] Team members (all added via **+**)
- [ ] Project description: what it is and what problem it solves
- [ ] Public GitHub repo URL (check that it's public and has a README)
- [ ] 1-minute demo video, as a YouTube link. Make it unlisted (not private), and show only features and code built today.
- [ ] Description of the Google products used (models, agents, Interactions API, AI Studio, Antigravity)
- [ ] Feedback for the Google DeepMind team on Argon. Keep a running log in `docs/FEEDBACK.md`.

## Models and agents

| Job | Model / agent ID |
|---|---|
| Lead reasoning, long-horizon coding, 3D, orchestration | `gemini-4-argon` |
| Autonomous sandbox execution (managed agent) | `antigravity-preview-09-2026` |
| Fast parallel subagents and tool calls | `gemini-3.8-flash` |
| Low-latency routing, classification, guardrails | `gemini-3.5-flash-lite` |
| Deep web research with citations (agent) | `deep-research-preview-04-2026` |
| Real-time voice and camera | `gemini-3.8-live`, or `gemini-3.8-live-extended-thinking` |
| Live speech-to-text | `gemini-3.5-transcribe-live`; for recorded audio with speaker labels, `gemini-3.5-transcribe` |
| Live speech-to-speech translation (70+ languages) | `gemini-3.5-live-translate-preview` |
| Text to speech (130 languages, voice design and replication) | `gemini-3.8-flash-tts`; faster: `gemini-3.8-flash-lite-tts` |
| Images, UI assets, textures, sprites (up to 4K, 8:1) | `gemini-nano-banana-2.1`; sub-second: `gemini-3.1-flash-lite-image` |
| Video with native audio (run in the background) | `gemini-omni-1.1-flash` |
| Music, vocals, loops | `lyria-3.5`; 30-second loops: `lyria-3-clip-preview` |
| Open / on-device | `gemma-4-31b-it` (the E2B and E4B sizes run locally) |

Typical setup: Argon as the lead architect and orchestrator, with 1–2 fast companion models.

## API essentials (Interactions API)

- **Use the Interactions API** (`client.interactions.create`) with `google-genai` / `@google/genai` **version 2.3.0 or later**. It covers models and managed agents, keeps server-side state (`previous_interaction_id`) and supports background execution.
- **`thinking_level`**: `"low"` | `"medium"` (default) | `"high"`. Use high for multi-file debugging, security fixes and system design. Use low for routing and extraction.
- **Context:** input, thinking and output share one **1M-token** window. Default output is capped at 65,536 tokens. To generate more, set `background=True`, set `max_output_tokens` above 65536, and poll `client.interactions.get(id=...)` while the status is `queued` or `in_progress`.
- **Deprecated for Argon:** `thinking_budget` (use `thinking_level`), `temperature`, `top_p`, `top_k`, and explicit `cached_content`. Implicit caching gives a 95% discount on cached input.
- **Timeouts:** set HTTP timeouts to 15–20 minutes for `"high"` thinking, or use `background=True`.
- **Pricing (introductory, through Nov 30, 2026):** $2 per 1M input tokens, $10 per 1M output tokens.

```python
from google import genai
client = genai.Client()

# Plain model call
r = client.interactions.create(
    model="gemini-4-argon",
    input="...",
    generation_config={"thinking_level": "medium"},
)
print(r.output_text)

# Managed agent: hosted Linux sandbox; Argon writes code, runs tests, calls MCP tools, searches the web
r = client.interactions.create(
    agent="antigravity-preview-09-2026",
    agent_config={"type": "antigravity", "model": "gemini-4-argon"},
    input="...",
    environment="remote",
)
```

**Verified:** both calls above work with this repo's key. Run `uv run python scripts/smoke_test.py` to check them again.

**Secrets for managed agents:** register tokens with `client.credentials.create` and restrict the network allowlist with `environment={"type": "remote", "network": {"allowlist": [...]}}`. The proxy then injects secrets, so they never enter the model context.

## 5 time-saving patterns (from the builder guide)

1. **Agree on the plan before long runs.** Have Argon raise questions, edge cases and trade-offs first, then let it run the full build.
2. **Give Argon a verification loop.** Use tests, compiler output, logs or a headless Chrome script. Record a baseline and iterate until every check passes with zero regressions.
3. **Use multimodal references.** Give 1–2 reference images for UI and 3D work, or have Argon extract a `DESIGN.md`. For UI or timing bugs, send a screen recording plus console logs.
4. **Orchestrate.** Argon decomposes the work and reviews diffs. Flash subagents handle leaf modules. Media models handle assets, voice and music.
5. **Record quirks.** Write non-obvious lessons into `AGENTS.md`. Before the demo, generate an HTML architecture diagram.

## Resources

- Argon developer guide: https://aistudio.google.com/learn/gemini-4-argon-developer-guide
- AI Studio: https://aistudio.google.com (Build mode: /build)
- Antigravity: https://antigravity.google
- Gemini skills: https://github.com/google-gemini/gemini-skills (installed in `.agents/skills/`)
- Docs and cookbook: https://ai.google.dev/gemini-api/docs, https://github.com/google-gemini/cookbook
- Live API examples: https://github.com/google-gemini/gemini-live-api-examples
- Feedback: gemini-developer-feedback@google.com
