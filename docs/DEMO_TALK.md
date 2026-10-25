# Demo talk track (3 minutes)

Spoken script with the screen action for each part. Setup for Tabs A, B and C is in [DEMO.md](DEMO.md).
Speaking time is about 2 minutes, which leaves room for clicks.

## 1. The problem (0:00, Tab A, empty venue)

Click **Run live** on Tab A first (3 sessions, 1 round, medium thinking, visual critic unticked).

> Getting groups with opposite interests to agree is one of the hardest things today. We hold summits to do it,
> yet we keep hearing that delegates walked out of a UN or G20 meeting. It happens when people feel they weren't
> heard, or were pushed around by a stronger group.
>
> So we built **Summit Simulator**, powered by Gemini 4 Argon. It lets an organizer test a summit before holding it.

## 2. The guests (0:25, Tab A, guest list and stance dots)

> Say we're organizing an AI-safety summit with ten delegations. Open-weights builders don't want open models
> treated like weapons. Safety researchers want to prevent rogue AI. Big Tech wants to scale. US national security
> wants to keep using AI for defense.
>
> First, Google's **Deep Research agent** builds a detailed profile of each delegation: their positions, their red
> lines and what they'd trade. Every profile cites the group's public statements.

## 3. The simulation (0:50, Tab B, click Replay)

> We start with a typical agenda for a one-day summit. Each session has a format: a **plenary**, where everyone is
> in one room; **breakouts**, in small groups; or **pairs**, two people in the lounge.
>
> **Gemini Flash** plays every delegate through the day. Then a separate, skeptical **Flash judge** scores it: did
> minds move, did everyone feel heard, did rival sides agree on anything?

## 4. Argon redesigns (1:15, Tab B, point at the chart and the Diagnosis panel)

> Then **Gemini 4 Argon** reads the transcripts and the score, explains in plain English what went wrong, and
> **redesigns the agenda**: who sits in which room, in what format, and what question the chair opens with. Then we
> run it again. The first agenda scored 29. After Argon fixed it: 77.

## 5. Argon looks at the room (1:40, Tab C, point at the ✅/❌ list, click a picture)

> Argon also looks at screenshots of the 3D venue, like a human organizer would. It spots problems: this person is
> outnumbered, these people only talk to their own side. Then it checks the next version to see if its fixes
> worked. Here, 2 of 3 did.

## 6. Approve and packets (2:15, Tab B, chart bar R2, then Approve)

> Nothing goes out until I approve it. When I do, the **Antigravity agent, running on Argon**, writes a briefing
> packet for every guest: where to be, who they'll meet, and how to open. It also builds calendar invites and PDFs.

Pick `global_south_cso` in the dropdown, then hover **Bundle**, then click **Close**. Never click **Regenerate**.

## 7. Close (2:45, back to Tab A)

> And the summit we started three minutes ago just finished. Argon already made it better.
>
> **Summit Simulator: test your meeting before you hold it.**

## Say it right

| Don't say | Say |
|---|---|
| "Deep Research builds the summit" | Deep Research builds the **guests**. Argon designs the summit. |
| "Argon scores the meeting" | A skeptical **Flash judge** scores it. Argon diagnoses and **redesigns**. |
| "Playwright MCP" | "takes screenshots of the 3D venue" (we use the Playwright library) |
| "each candidate / real people" | "each **delegation**": profiles are roles, like the EU AI Office, not named people |
| "Argon writes the packets" | the **Antigravity agent, running on Argon**, writes them |

## Quick answers for judges

- **Who proposes the new agenda?** Argon. One call returns the diagnosis, the list of changes and the new plan.
  A small code check fixes rule slips, like a guest missing from a session.
- **Can Argon cheat?** It did, twice. It told guests to "state a compromise" (score 50 → 98), then wrote a
  600-word treaty into the closing session (35 → 100). We capped its instructions at 60 words, made guests push
  back based on their red lines, and added a skeptical judge. Both cheating runs are kept in `data/archive/`.
- **What can Argon control?** The agenda, the seating and the chair's 60-word opening. It can't change the
  guests, the simulator's rules, the judge or the scoring.
- **Does the visual critic help?** It's best as a checker: it confirms whether fixes landed (2/3, 1/3, 2/3 in
  `visual-loop-v3`). The text critic already knows who sits in which room, so its effect on the score isn't proven.
  The next step is a same-settings comparison with it switched on and off.
- **Which models?** Argon redesigns the agenda, critiques the screenshots and runs the Antigravity packet agent.
  Flash plays the guests and judges. Deep Research builds the guests.
