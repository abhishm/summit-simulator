# TODO

Future steps, in priority order.

## P0: Screenshot critique loop (do this first)

A stretch goal in `docs/PLAN.md` (decision 8 and line 31). It's missing from the status checklist and isn't built yet. It's needed for the **More Dimensions** track, which expects "render → watch → critique → fix" (see the AI Studio guide *Building 3D Games and Procedural Worlds with Gemini 4 Argon*, workflow 3: Adversarial Critic).

- [x] Add Playwright (`uv add playwright`) and write a script that opens `web/index.html`, steps through each block of a run and takes a screenshot of each block.
- [x] Send the screenshots to `gemini-4-argon` as a multimodal critic. It should list at least 3 specific flaws (for example, a guest isolated in a corner or factions that never mix) and give a score out of 10.
- [x] Add that critique to the next `revise()` prompt in `app/optimize.py`, so the visual check affects the plan.
- [x] Show the critique in the UI and the demo (screenshot plus flaws, per round).

## P1: Briefing packets (Antigravity)

- [x] **Stricter packet check.** Today `verify()` in `app/packets.py` and the agent's `check.py` only test that the start time, room name and co-participant IDs appear *somewhere* in a packet. Instead:
  - Parse each `HH:MM-HH:MM | room | title` line and check that the time and room match **on the same line**.
  - Flag **extra or wrong** co-participants, not just missing ones.
  - Check that the "openings" and "Know your counterparts" sections exist and refer to the actual co-participants' red lines and tradeoffs.
- [x] **Give the sandbox real work** so that Antigravity adds more than a plain Argon call:
  - Create `.ics` calendar invites and a PDF for each guest, and check that they parse.
  - Score the packets' suggested openings with the simulator to show that they raise consensus.
  - Return a zip bundle for the organizer to approve before anything is sent.
