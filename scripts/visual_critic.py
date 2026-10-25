"""Render one round of a saved run, have Gemini 4 Argon critique the screenshots, and attach it to the run JSON.

uv run python scripts/visual_critic.py demo-5block 2 [--thinking medium]
Stored as history[<round>]["visual"] (images under data/visual/<run>/), so replays show it without waiting.
"""
import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.visual import visual_round  # noqa: E402

RUNS = Path(__file__).resolve().parents[1] / "data" / "runs"


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run")
    ap.add_argument("round", type=int, nargs="?", help="default: the run's best round")
    ap.add_argument("--thinking", default="medium")
    a = ap.parse_args()
    f = RUNS / f"{a.run}.json"
    run = json.loads(f.read_text())
    rnd = run["best"] if a.round is None else a.round
    h = run["history"][rnd]
    pv = (run["history"][rnd - 1].get("visual") or {}).get("flaws") if rnd > 0 else None
    v = await visual_round(run["personas"], h["plan"], h["result"]["groups"], h["result"]["ratings"], a.run, rnd,
                           a.thinking, pv)
    run = json.loads(f.read_text())  # re-read in case it changed meanwhile
    run["history"][rnd]["visual"] = v
    f.write_text(json.dumps(run, indent=1))
    print(f"{a.run} round {rnd}: visual score {v['score']}/10 (render {v['render_seconds']}s, total {v['seconds']}s)")
    print(v["summary"])
    if v.get("resolved"):
        print(f"previous flaws fixed: {v['resolved']['fixed']}/{v['resolved']['total']}")
        for x in v["previous"]:
            print(f"  {'FIXED' if x['fixed'] else 'OPEN '} B{x['block']}: {x['issue']} | {x['evidence']}")
    for fl in v["flaws"]:
        print(f"- B{fl['block']}: {fl['issue']}\n    fix: {fl['fix']}")
    print("images:", *v["images"])


if __name__ == "__main__":
    asyncio.run(main())
