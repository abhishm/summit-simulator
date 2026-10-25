# TODO

Future steps that are out of scope for the hackathon.

## Briefing packets (Antigravity)

- [ ] **Stricter packet check.** Today `verify()` in `app/packets.py` and the agent's `check.py` only test that the start time, room name and co-participant IDs appear *somewhere* in a packet. Instead:
  - Parse each `HH:MM-HH:MM | room | title` line and check that the time and room match **on the same line**.
  - Flag **extra or wrong** co-participants, not just missing ones.
  - Check that the "openings" and "Know your counterparts" sections exist and refer to the actual co-participants' red lines and tradeoffs.
- [ ] **Give the sandbox real work** so that Antigravity adds more than a plain Argon call:
  - Create `.ics` calendar invites and a PDF for each guest, and check that they parse.
  - Score the packets' suggested openings with the simulator to show that they raise consensus.
  - Return a zip bundle for the organizer to approve before anything is sent.
