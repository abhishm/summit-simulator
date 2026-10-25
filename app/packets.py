"""Antigravity managed agent (running on Gemini 4 Argon) writes one briefing packet per guest for an approved plan.

The agent writes the packets in its sandbox, writes and runs a checker that each packet matches the plan (rooms,
co-participants, times), fixes anything that fails, and returns a JSON bundle. We re-verify locally.
"""
import json
import re

from .gemini import aclient

AGENT = "antigravity-preview-09-2026"


def schedule(plan: dict) -> list[dict]:
    """Timed blocks with concrete room names; same timing as the run of show."""
    from .simulate import ROOMS
    out, t = [], 9 * 60
    for bi, b in enumerate(plan["blocks"]):
        dur = 45 if b["format"] == "plenary" else 60
        rooms = ROOMS[b["format"]]
        groups = [{"room": rooms[min(gi, len(rooms) - 1)] + (f" {gi + 1}" if b["format"] == "pairs" else ""),
                   "members": g} for gi, g in enumerate(b["groups"])]
        out.append({"block": bi + 1, "start": f"{t // 60:02d}:{t % 60:02d}",
                    "end": f"{(t + dur) // 60:02d}:{(t + dur) % 60:02d}", "title": b["title"], "format": b["format"],
                    "topic": b["topic"], "facilitator_prompt": b["prompt"], "groups": groups})
        t += dur + 15
    return out


def verify(sched: list[dict], packets: dict[str, str], ids: list[str]) -> list[str]:
    """Each guest has a packet that names, for every block, the right time and room and all co-participants."""
    errs = []
    for pid in ids:
        md = packets.get(pid)
        if not md:
            errs.append(f"{pid}: missing packet")
            continue
        for blk in sched:
            g = next((g for g in blk["groups"] if pid in g["members"]), None)
            if not g:
                continue
            if blk["start"] not in md:
                errs.append(f"{pid}: block {blk['block']} start time {blk['start']} missing")
            if g["room"] not in md:
                errs.append(f"{pid}: block {blk['block']} room '{g['room']}' missing")
            if blk["format"] != "plenary":
                for other in g["members"]:
                    if other != pid and other not in md:
                        errs.append(f"{pid}: block {blk['block']} co-participant {other} missing")
    return errs


def _prompt(plan: dict, sched: list[dict], personas: list[dict]) -> str:
    brief = [{k: p[k] for k in ("id", "title", "faction", "summary", "stances", "red_lines", "tradeoffs")}
             for p in personas]
    return f"""You are preparing delegate briefing packets for an approved 1-day AI-safety summit: "{plan['name']}".

Work in /workspace/summit. Steps:
1. Save the schedule and guest list below to schedule.json and guests.json.
2. For EVERY guest, write packets/<guest_id>.md with:
   - A header with the guest's title and a one-paragraph purpose for their day.
   - "Your day": one line per block in the form `HH:MM-HH:MM | <exact room name> | <session title>`, plus, for
     non-plenary blocks, "with:" followed by the exact guest ids of the co-participants and their titles.
   - For each non-plenary block: 2-3 bullet "openings". These are concrete offers or questions that address
     the co-participants' red lines and tradeoffs (from guests.json) and move toward agreement.
   - "Know your counterparts": a short cheat sheet of each co-participant's top red line and what they'd trade.
3. Write check.py. It loads schedule.json and every packet and asserts that, for each guest and each block, the
   packet contains the block start time, the exact room name and (for non-plenary blocks) every co-participant
   id. Run it, fix any packet that fails, and repeat until it passes.
4. Reply with ONLY a JSON object (no prose, no code fences):
   {{"checks_passed": true|false, "check_output": "<last check.py output>",
     "packets": {{"<guest_id>": "<full markdown>", ...}}}}

SCHEDULE (authoritative):
{json.dumps(sched, indent=1)}

GUESTS:
{json.dumps(brief, indent=1)}"""


def _parse(text: str) -> dict:
    text = (text or "").strip()
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ValueError(f"agent returned no JSON: {text[:300]}")
    return json.loads(m.group(0))


async def generate(run: dict, rnd: int, model: str = "gemini-4-argon") -> dict:
    plan = run["history"][rnd]["plan"]
    sched = schedule(plan)
    ids = [p["id"] for p in run["personas"]]
    r = await aclient().interactions.create(
        agent=AGENT, agent_config={"type": "antigravity", "model": model},
        input=_prompt(plan, sched, run["personas"]), environment="remote")
    out = _parse(r.output_text)
    packets = {k: v for k, v in (out.get("packets") or {}).items() if k in ids}
    errs = verify(sched, packets, ids)
    steps = [s.type for s in (r.steps or [])]
    return {"interaction": r.id, "environment": getattr(r, "environment_id", None), "packets": packets,
            "agent_checks_passed": out.get("checks_passed"), "agent_check_output": out.get("check_output", ""),
            "local_errors": errs, "tool_steps": sum(t.endswith("_call") for t in steps)}
