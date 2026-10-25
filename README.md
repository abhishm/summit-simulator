# Summit Simulator

**Gemini 4 Argon designs your AI-safety summit and proves the design works before anyone books a flight.**

Built for the Gemini 4 Argon SF Hackathon (Oct 25, 2026), **More Dimensions** track.

## The problem

An organizer of a multistakeholder AI-safety summit (think Bletchley Park / Seoul / Paris-style meetings) has
one day and ten delegations that disagree on everything: binding regulation, open weights, compute controls,
evaluations and liability, benefit sharing. The default agenda is keynotes plus breakouts grouped by
constituency. It produces speeches, not agreements, and the least powerful voices (Global South civil society,
labor) leave feeling unheard.

**Who it's for:** the summit's program lead, who has to sign off on the run of show.

## What it does

1. **Deep Research builds the guest list.** One `deep-research-preview-04-2026` background job per stakeholder
   *role*: EU AI Office, US natsec, UK AISI, a Chinese policy think tank, a frontier-lab CEO, an open-weights
   company, Big Tech policy, a safety researcher, Global South civil society and labor. Each job produces a cited
   brief. Flash turns each brief into a persona: stances on 5 issue axes (-5..+5), red lines, tradeoffs,
   engagement style and institutional power. Personas are **role-based and grounded in public positions**, not
   psychological profiles of real people.
2. **Flash simulates the summit.** Each agenda block runs every room in parallel with `gemini-3.8-flash`, under
   strict realism rules. High-power guests dominate plenaries, same-faction rooms only reinforce views,
   positions move only when a concern is acknowledged or a tradeoff is offered, red lines hold, and facilitation
   can't compel positions. Stance moves are capped in code.
3. **An independent judge scores it.** A skeptical `gemini-3.8-flash` judge rates how heard each guest was. The final score
   (0–100) combines:
   - **consensus (40):** stance-spread reduction plus agreements spanning 3+ factions
   - **inclusion (30):** the *minimum* felt-heard rating
   - **airtime equity (15):** 1 − Gini of words spoken
   - **cross-faction contact (15):** the share of cross-faction pairs who met in groups of 5 or fewer
4. **Gemini 4 Argon critiques and redesigns. That's the verification loop.** Argon reads the full transcripts,
   the scores and the stance movements, then returns a diagnosis and a revised agenda as structured output. It
   changes groupings, formats, sequencing, chairs and facilitation prompts. The new plan is re-simulated and
   re-scored. Rounds are chained with `previous_interaction_id`, so Argon remembers what it tried, and the loop
   stops after 2 rounds without improvement.
5. **You watch it in 3D and approve.** A Three.js isometric venue (plenary hall, four breakout rooms, a lounge)
   animates guests moving between rooms, talking (lines), and how heard they felt (halos). Dots on a stance strip
   visibly converge. A score chart compares the baseline with each Argon round. **Nothing is final until the
   organizer clicks Approve**, which exports a timed run of show: rooms, who sits where, facilitator prompts, the
   agreements reached in simulation and Argon's rationale.
6. **Antigravity writes the briefing packets, and checks them.** After approval, the Antigravity managed agent
   (`antigravity-preview-09-2026` running `gemini-4-argon`) works in a remote sandbox. It writes one packet per
   delegate: their personal schedule, who they'll sit with, concrete openings that address each counterpart's
   red lines, and a counterpart cheat sheet. It then writes and runs `check.py`, which confirms every packet
   matches the approved schedule (times, rooms, co-participants), and fixes failures until the check passes.
   The server re-verifies locally. (10/10 packets, both checks pass, about 5 minutes.)

## Why Argon

The critique step is the hard part. Argon reads ~20–40K tokens of multi-room transcripts plus score breakdowns,
works out *why* a guest felt excluded or why two factions never converged, and redesigns a combinatorial
agenda (10 guests × 5 blocks × groupings × prompts) that satisfies hard constraints. Flash is fast enough to
run each world. Argon is what makes the loop actually improve.

It is also a very good reward hacker. Hardening the simulator became part of the build:

1. **Lenient world (50 → 98.4 in one round).** Argon reordered speaker lists to game the airtime metric and told
   guests to "state a compromise". Fix: facilitation can't compel positions, the closing plenary is mandatory,
   and agreements must span 3+ factions.
2. **Pre-drafted deal (34.9 → 99.6, every guest rated 10/10).** Argon wrote a 600-word treaty into the closing
   plenary prompt, and the Flash delegates simply endorsed it. Fix: facilitation prompts are capped at 60 words,
   drafts are contested per red lines, every session needs pushback, and a skeptical Flash judge asks what each
   guest conceded.

Both runs are kept in `data/archive/` as evidence.

## Run it

```bash
uv sync
echo "GOOGLE_API_KEY=..." > .env
uv run uvicorn app.server:app --port 8000      # open http://localhost:8000
```

- **Replay** a saved run, such as the pre-run `demo-5block` (4 Argon rounds at high thinking).
- **Run live:** 3 blocks, 1–3 rounds, medium thinking. That takes about 2 minutes per round.
- **Add a guest:** start a live Deep Research job for a new role. The new persona joins the next run.
- `DEMO_MODE=1 uv run uvicorn app.server:app` makes "Run live" replay the best saved run (offline fallback).

Rebuild the data:

```bash
uv run python scripts/research_personas.py start   # 10 Deep Research jobs (~15 min)
uv run python scripts/research_personas.py collect
uv run python -m app.personas                       # brief -> persona JSON
uv run python scripts/run_optimize.py --rounds 4 --blocks 5 --thinking high --name demo-5block
```

## Architecture

```
Deep Research (x10, background) ──> data/personas/*.md ──Flash──> persona JSON
                                                                   │
          ┌───────────────────────────── optimize loop ────────────┴──────────────┐
          │ plan ──> simulate (Flash, rooms in parallel per block) ──> judge (Flash)│
          │   ▲                                                         │ score   │
          │   └── repair() <── Revision{critique, changes, plan} <── Gemini 4 Argon│
          └────────────────────────────────────────────────────────────────────────┘
FastAPI (SSE events: round_start / block / thinking / round_done) ──> Three.js venue + chart
Approve ──> data/approved/<run>-r<round>.md (run of show) ──> Antigravity+Argon sandbox ──> per-guest packets (self-checked)
```

| File | Purpose |
|---|---|
| `app/models.py` | Persona, Plan/Block, simulation and score models |
| `app/personas.py` | Brief → persona extraction (structured output) |
| `app/simulate.py` | World rules, per-room simulation, judge, scoring |
| `app/optimize.py` | Baseline plan, constraint repair, Argon critique/revise loop |
| `app/server.py` | API, live SSE runs, replay, approval export, packets, live Deep Research |
| `app/packets.py` | Antigravity briefing packets + in-sandbox and local verification |
| `web/index.html` | Three.js venue, stance strip, score chart, critique panel |
| `scripts/` | Persona research, CLI optimizer runs, API smoke test |

## Built today

Everything in this repo was written on Oct 25, 2026 during the hackathon. That includes the persona research
pipeline, simulator, scorer, Argon loop, server and 3D UI. The only third-party code is three.js (MIT),
vendored in `web/vendor/`.

## Limits and honesty

- It's a simulation. Personas are role-level syntheses of public positions, not predictions about specific
  people. Each plan is scored from one stochastic run, so treat score differences of a few points as noise.
- The output is a *draft* run of show for a human organizer, who approves it.
