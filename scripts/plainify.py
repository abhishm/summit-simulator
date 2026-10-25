"""Add plain-language versions of the AI's notes to a saved run (critique, changes, visual critic, agreements).

Usage: uv run python scripts/plainify.py demo-5block visual-loop-v3 ...
The originals are kept; the UI shows the *_plain fields when "plain English" is ticked.
"""
import asyncio
import json
import sys
from pathlib import Path

from pydantic import BaseModel, Field

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.gemini import FLASH, structured  # noqa: E402

RUNS = Path(__file__).resolve().parents[1] / "data" / "runs"

STYLE = """Rewrite each item below for a general audience (think: a smart friend who doesn't work in AI policy).
Rules: short sentences, everyday words, no jargon, no acronyms (say "AI safety institute", not "AISI"), no score
names like "Gini" or "cross_faction". Refer to guests by plain role (e.g. "the EU regulator", "the union leader",
"the Global South advocate", "the open-source lead"). Keep the meaning and the key facts. Keep each item about half
as long as the original or shorter. Return the same number of items, in the same order."""


class PlainRound(BaseModel):
    critique: str = Field(description="The critique in 2-3 short plain sentences ('' if none given)")
    changes: list[str] = Field(description="One plain line per change, under 15 words each")
    visual_summary: str = Field(description="The visual verdict in 1-2 plain sentences ('' if none given)")
    flaws: list[str] = Field(description="One plain sentence per flaw: the problem and the fix")
    previous: list[str] = Field(description="One plain line per previous flaw, under 12 words")
    agreements: list[str] = Field(description="One plain sentence per agreement, under 25 words")


async def plain_round(h: dict) -> None:
    v = h.get("visual") or {}
    ags = [a for g in h["result"]["groups"] for a in g["agreements"]]
    items = {
        "critique": h.get("critique") or "",
        "changes": h.get("changes") or [],
        "visual_summary": v.get("summary", ""),
        "flaws": [f"{f['issue']} FIX: {f['fix']}" for f in v.get("flaws", [])],
        "previous": [x["issue"] for x in v.get("previous", [])],
        "agreements": [a["text"] for a in ags],
    }
    out = await structured(FLASH, STYLE + "\n\nITEMS (JSON):\n" + json.dumps(items, indent=1), PlainRound)
    if items["critique"]:
        h["critique_plain"] = out.critique
    if len(out.changes) == len(items["changes"]):
        h["changes_plain"] = out.changes
    if v:
        v["summary_plain"] = out.visual_summary
        for f, t in zip(v.get("flaws", []), out.flaws):
            f["plain"] = t
        for x, t in zip(v.get("previous", []), out.previous):
            x["plain"] = t
    if len(out.agreements) == len(ags):
        for a, t in zip(ags, out.agreements):
            a["plain"] = t
    print(f"  round {h['round']}: critique {len(h.get('critique_plain', ''))} chars, {len(out.changes)}/{len(items['changes'])} changes, "
          f"{len(out.flaws)}/{len(items['flaws'])} flaws, {len(out.agreements)}/{len(ags)} agreements", flush=True)


async def main(ids: list[str]) -> None:
    for rid in ids:
        f = RUNS / f"{rid}.json"
        run = json.loads(f.read_text())
        print(rid, flush=True)
        await asyncio.gather(*(plain_round(h) for h in run["history"]))
        f.write_text(json.dumps(run, indent=1))


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1:]))
