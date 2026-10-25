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
   **Render → watch → critique → fix (optional, `--visual`):** before each redesign, Playwright renders every
   block of the round in the 3D venue and screenshots it, and `gemini-4-argon` critiques the images as an
   adversarial *visual* critic (score /10 plus at least 3 specific flaws such as "us_natsec and china_policy are
   inseparable across all four breakouts" or "Breakouts C/D and the Lounge sit empty all day"). Those flaws go
   into the next `revise()` prompt, so what the plan *looks like* changes the plan. That's the **More
   Dimensions** loop: the 3D world is an input to the model, not just an output.
   The critic also **verifies its own previous flaws** on each new render (✅ fixed / ❌ open, with evidence), so
   the loop is closed. In `visual-loop-v3`: total 32 → 68 → 72 → 74, visual 2.0 → 7.5 → 8.0 → 8.2, and Argon
   verified 2/3, 1/3, 2/3 of the previous round's flaws as fixed.
5. **You watch it in 3D and approve.** A Three.js isometric venue (plenary hall, four breakout rooms, a lounge)
   animates guests moving between rooms, talking (lines), and how heard they felt (halos). Dots on a stance strip
   visibly converge. A score chart compares the baseline with each Argon round. **Nothing is final until the
   organizer clicks Approve**, which exports a timed run of show: rooms, who sits where, facilitator prompts, the
   agreements reached in simulation and Argon's rationale.
6. **Antigravity prepares a draft delegate bundle, and checks it.** After approval, the Antigravity managed agent
   (`antigravity-preview-09-2026` running `gemini-4-argon`) works in a remote sandbox. Per delegate it writes a
   markdown packet (personal schedule, who they'll sit with, concrete openings that address each counterpart's
   red lines and tradeoffs, a counterpart cheat sheet), an `.ics` calendar invite and a PDF. It then writes and runs
   `check.py` and fixes failures until it passes. The check is strict: each `HH:MM-HH:MM | room | title` line must
   match its block on the same line, co-participants must be exactly the group (missing *and* extra ids are
   flagged), openings and counterparts must engage the right people's red lines and tradeoffs without templated or
   pasted text, the `.ics` files must parse with `icalendar` and the PDFs with `pypdf`. It zips everything with a
   manifest; we download the zip from the sandbox (`environments.files.download`) and re-verify it locally
   (`app/packets.py: verify, verify_artifacts`; offline tests in `tests/test_packets_verify.py`). **Nothing is
   sent**: the bundle is a draft the organizer reviews and downloads ("⬇ Bundle (draft)" in the Approve modal).
   Optionally we re-simulate the approved plan with each guest's openings added to their brief, to see whether the
   openings move consensus (`score_openings`, one Flash run each way, noisy).

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

After both rounds of hardening, the `demo-5block` pre-run (4 Argon rounds, high thinking) shows a realistic curve:
**28.9 → 71.6 → 77.3 → 74.2 → 75.5**. Argon's first redesign fixes faction-segregated rooms (cross-faction
pairs met: 5/38 → 38/38). After that, gains are incremental and it trades consensus against inclusion. The best
plan (round 2) is approved, and its Antigravity briefing packets are cached in
`data/approved/demo-5block-r2-packets/`, with the draft bundle in `data/approved/demo-5block-r2-bundle.zip` and the
openings re-simulation in `data/approved/demo-5block-r2-openings.json`. Regenerate with
`uv run python scripts/make_packets.py demo-5block 2` (about 4-10 minutes plus 2 minutes of scoring).

## Run it

```bash
uv sync
uv run playwright install chromium            # only for the visual critic
echo "GOOGLE_API_KEY=..." > .env
uv run uvicorn app.server:app --port 8000      # open http://localhost:8000
```

- **Replay** a saved run, such as the pre-run `demo-5block` (4 Argon rounds at high thinking).
- **Run live:** 3 blocks, 1–3 rounds, medium thinking. That takes about 2 minutes per round.
- **Add a guest:** start a live Deep Research job for a new role. The new persona joins the next run.
- **Click any agenda block** (after a round finishes): guests move to that block's rooms, the opinion dots jump to that point in the day, and the transcript shows that block's full conversation and agreements, room by room.
- **plain English** checkbox (on by default): shows the AI's notes (critique, changes, visual critic, agreements) in everyday language. New runs ask Argon/Flash for a plain version directly; saved runs get one from `scripts/plainify.py <run>`. Untick it for the original detailed text.
- **📋 View plan** (next to Baseline / Best plan): the full run of show for the selected round (times, rooms, who's in each room, facilitator prompts, Argon's rationale) as a draft, without approving it.
- **👁 visual critic** checkbox (live runs) / `--visual` (CLI): screenshot + Argon visual critique before each
  revision (about 5 s to render, 15–30 s for the critique). The "Visual critic" panel shows the score, flaws and
  thumbnails (click to zoom); replays show stored critiques. `demo-5block` round 2 has one cached
  (`uv run python scripts/visual_critic.py demo-5block 2` regenerates it; images in `data/visual/<run>/`).
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
  (--visual) Playwright screenshots each block ──> Argon visual critic {score/10, flaws} ──> next revise() prompt
FastAPI (SSE events: round_start / block / thinking / round_done / visual) ──> Three.js venue + chart
Approve ──> data/approved/<run>-r<round>.md (run of show) ──> Antigravity+Argon sandbox ──> draft bundle.zip (packets, .ics, PDFs; self-checked, re-verified)
```

| File | Purpose |
|---|---|
| `app/models.py` | Persona, Plan/Block, simulation and score models |
| `app/personas.py` | Brief → persona extraction (structured output) |
| `app/simulate.py` | World rules, per-room simulation, judge, scoring |
| `app/optimize.py` | Baseline plan, constraint repair, Argon critique/revise loop |
| `app/server.py` | API, live SSE runs, replay, approval export, packets, live Deep Research |
| `app/visual.py` | Playwright block screenshots (`?static=1` render mode) + Argon multimodal visual critic |
| `app/packets.py` | Antigravity draft bundle (packets, .ics, PDFs, manifest), strict in-sandbox + local verification, openings re-simulation |
| `web/index.html` | Three.js venue, stance strip, score chart, critique panel |
| `scripts/` | Persona research, CLI optimizer runs, visual critique of a saved round, API smoke test |

## Built today

Everything in this repo was written on Oct 25, 2026 during the hackathon. That includes the persona research
pipeline, simulator, scorer, Argon loop, server and 3D UI. The only third-party code is three.js (MIT),
vendored in `web/vendor/`.

## Limits and honesty

- It's a simulation. Personas are role-level syntheses of public positions, not predictions about specific
  people. Each plan is scored from one stochastic run, so treat score differences of a few points as noise.
- The output is a *draft* run of show for a human organizer, who approves it.
