# Demo playbook

Round 1 is about 3 minutes live with no slides, then 1–2 minutes of Q&A. Judges weight the **working live demo with a real verification loop at 50%**.
The submission also needs a **1-minute YouTube video (unlisted)** showing only work built today.

`[P0]` / `[P1]` mark beats that go in once those branches merge: the visual critic, and the stricter packets plus bundle.

## Setup (T-10 min)

```bash
cd ~/argon-hackathon-10-25-2026
uv run uvicorn app.server:app --port 8000                # normal
DEMO_MODE=1 uv run uvicorn app.server:app --port 8000    # fallback: "Run live" replays demo-5block, no API calls
```

- Two browser tabs on `localhost:8000`, zoomed to 90%, with the dock and notifications hidden.
  - **Tab A (live):** 3 blocks, **1 round**, `medium` thinking. It finishes in about 2:50, so click **Run live** by 0:15. Leave **👁 visual critic unticked** for the live run: it adds 15–30s per round. The demo shows the cached critique instead.
  - **Tab B (pre-run):** run selector on `demo-5block · 29→72→77→74→76` at speed 8×.
  - **Tab C (visual loop):** select `visual-loop-v3 · 32→68→72→74`, click **Replay** at 8×, wait until it finishes, then click chart bar **R3** and scroll so the **Visual critic** panel (8.2/10 plus the ✅/❌ checklist) is on screen. Leave it there.
- Have a phone hotspot ready. If the Wi-Fi is bad, restart the server with `DEMO_MODE=1`.
- Before 5 PM, check the repo is public and the README renders.

## 3-minute live script

| Time | Screen | Say (roughly) |
|---|---|---|
| 0:00 | Tab A, idle venue | "I'm the program lead for an AI-safety summit. Ten delegations, one day: EU regulators, US natsec, a Chinese think tank, frontier labs, open-weights, labor, Global South civil society. The default agenda (keynotes plus breakouts by constituency) produces speeches, not agreements." |
| 0:15 | Click **Run live** | "So before anyone books a flight, Gemini 4 Argon designs the agenda and *tests* it. These ten personas came from Deep Research: one cited brief per role, built on public positions." |
| 0:30 | Rooms light up, transcript scrolls | "Flash runs every room in parallel under realism rules: red lines hold, power dominates plenaries, and facilitation can't force a position. A skeptical Flash judge asks each guest what they conceded." |
| 0:50 | Switch to **Tab B**, click **Replay** | "Here's a pre-run with four Argon rounds at high thinking." Point at the chart: **28.9 → 77.3**. |
| 1:05 | Critique panel | "Argon reads 20–40K tokens of multi-room transcripts plus the scores, and diagnoses: *only 5 of 38 cross-faction pairs ever met*. It redesigns the groupings, and on the re-simulation 38 of 38 meet." |
| 1:25 | 3D venue plus stance strip | "Watch the dots on each issue converge. That's consensus actually forming, not being declared." |
| 1:40 | Switch to **Tab C** (Visual critic panel, R3), point at the ✅/❌ checklist, click a thumbnail | "It also renders the venue, screenshots every block and Argon critiques the *picture*: who's outnumbered, which rooms sit empty, which factions never meet. Those flaws drive the next redesign, and then Argon checks the new render to see if its fixes actually landed. Here it verified 2 of 3. Visual score: 2 to 8.2." |
| 2:00 | Say it, no screen change | "Argon is also a great reward hacker. Its first run hit 98 by reordering speakers. Its second wrote a 600-word treaty into the closing prompt, and everyone signed it. We hardened the simulator twice; the honest curve is this one." |
| 2:15 | **Approve round 2 (best)** | "Nothing ships until I approve. Approve exports a run of show…" |
| 2:25 | Packet selector → `global_south_cso` | "…and the Antigravity agent, running Argon in a sandbox, writes a briefing packet per guest, then writes and runs its own checker until all 50 guest-block assertions pass. We verify it again locally." `[P1]` "It also generates calendar invites and PDFs as one bundle the organizer signs off on." |
| 2:45 | Back to **Tab A** | "And the live run just finished: about 26 → 60. Argon's critique of a run we started three minutes ago." |
| 2:55 | — | "Summit Simulator: Argon designs the room, then proves it works." |

**Rules on stage:** never wait on a spinner. Tab A runs in the background, and every other beat uses cached results. If Tab A errors, skip the 2:45 beat.

## 1-minute video (about 140 spoken words)

| Time | Shot | Voiceover |
|---|---|---|
| 0:00–0:08 | Title on the idle venue | "Ten AI-safety delegations, one day, and a default agenda that produces speeches, not agreements." |
| 0:08–0:18 | Persona roster / Deep Research form | "Deep Research builds cited, role-based personas. Gemini Flash simulates every room in parallel, and a skeptical judge scores it." |
| 0:18–0:35 | Replay at 8×, chart climbing | "Gemini 4 Argon reads the full transcripts, diagnoses why the summit failed (only 5 of 38 cross-faction pairs met) and redesigns it. Re-simulated: 28.9 to 77.3." |
| 0:35–0:45 | Visual critic panel: thumbnails plus ✅/❌ checklist | "Argon also watches the rendered venue, critiques what it sees, and verifies its own fixes on the next render." |
| 0:45–0:55 | Approve → packets `[P1]` bundle | "On approval, the Antigravity agent writes and self-verifies a briefing packet for every guest." |
| 0:55–1:00 | Repo URL | "Built today. Summit Simulator." |

**How to make it:**
- **Option A (manual):** record the screen with QuickTime (⌘⇧5, "Record Selected Portion") and talk over it.
- **Option B (scripted):** a Playwright script records the exact UI flow to `.webm` at 1600×900. `gemini-3.8-flash-tts` reads the voiceover, and ffmpeg combines the two and trims to 60s.
- Upload to YouTube as **Unlisted** (not Private).

## Q&A prep

- **"Isn't it just LLMs agreeing with each other?"** That's the failure mode we hit twice and fixed:
  - prompts are capped at 60 words
  - drafts are contested per red line
  - pushback is mandatory
  - stance moves are capped in code
  - a skeptical judge must name concessions

  Both gamed runs are in `data/archive/`.
- **"Why Argon?"** Each critique reasons over 20–40K tokens of parallel-room transcripts plus scores and stance deltas. It has to attribute failure to specific groupings across rooms and keep a memory across rounds via `previous_interaction_id`. Flash at the same task gave generic advice (say this only if you've seen it; otherwise say "the redesign needs cross-room reasoning").
- **"Are these real people?"** No. Personas are *roles* grounded in public positions, with cited Deep Research briefs. They aren't psychological profiles.
- **"How noisy is the score?"** Each plan is scored from one stochastic run, so ±3 points is noise. The 29 → 72 jump (segregated rooms → full mixing) is structural. Next step: average 3 runs per plan.
- **"Real product?"** It's a pre-mortem for any high-stakes multistakeholder meeting: summits, standards bodies, union negotiations, or co-design workshops. Swap the personas and the issue axes.
- **"Does the visual critic change anything?"** Yes. Its flaws are injected into the next `revise()` prompt, and in the `visual-test` run Argon's critique cited it directly: *"confirmed by both simulation metrics and the visual critic"*. It's a second, independent signal: it catches spatial and power imbalances that the numeric score doesn't measure. It also **closes the loop**: each new render is checked against the previous round's flaws, giving per-flaw ✅/❌ with evidence In `visual-loop-v3` (venue rules plus verification) the visual score rose every round, **2.0 → 7.5 → 8.0 → 8.2**, alongside a total of **32 → 68 → 72 → 74**, and Argon verified 2/3, 1/3 and 2/3 of its own fixes on the new renders. Before those changes (v1/v2) it plateaued at 6.5.
- **"Cost / time?"**
  - a 5-block simulation takes about 90s
  - an Argon revision takes about 1 min at medium thinking and 6–10 min at high
  - the packets take 5–11 min (so they're cached)

## Rehearsal log

| Time | Config | Result | Notes |
|---|---|---|---|
| 14:25 | 1-min video v4 (scripted) | 57.9s | Visual segment now shows visual-loop-v3 R3: 8.2/10 plus the ✅/❌ verification checklist. At `~/Desktop/summit-simulator-1min-draft.mp4` |
| 14:07 | visual-loop-v3: 5 blocks, 3 rounds, medium, visual critic plus verification | total 32→68→72→74; visual 2.0→7.5→8.0→8.2; fixed 2/3, 1/3, 2/3 | 1355s. Best showcase run for the visual critic beat |
| 13:12 | 1-min video draft v2 (scripted) | 53.5s | Playwright recording + `gemini-3.8-flash-tts` (voice Kore) + ffmpeg. At `~/Desktop/summit-simulator-1min-draft.mp4` |
| 12:57 | live: 3 blocks, 2 rounds, medium | 26.3 → 60.0 → 62.4 | Round 1 ends at 168s, round 2 at 264s. Too long for 2 rounds, so use **1 round** live. Argon's critique named 10 missing cross-faction pairs (saved as `rehearsal-live`) |
