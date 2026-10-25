"""Generate + cache the Antigravity delegate bundle for a saved run, then score the packets' openings.

uv run python scripts/make_packets.py demo-5block 2 [--no-score] [--score-only]
"""
import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.packets import APPROVED, generate, load, save, score_openings  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("run_id")
ap.add_argument("round", type=int)
ap.add_argument("--no-score", action="store_true")
ap.add_argument("--score-only", action="store_true")
a = ap.parse_args()
run = json.loads((APPROVED.parent / "runs" / f"{a.run_id}.json").read_text())
key = f"{a.run_id}-r{a.round}"


async def main():
    if not a.score_only:
        t0 = time.time()
        out = await generate(run, a.round, key=key)
        out["seconds"] = round(time.time() - t0)
        meta = save(key, out)
        print(json.dumps({k: v for k, v in meta.items() if k != "bundle_files"}, indent=1))
        print("bundle files:", len(meta["bundle_files"]))
    if not a.no_score:
        sc = await score_openings(run, a.round, load(key)["packets"])
        (APPROVED / f"{key}-openings.json").write_text(json.dumps(sc, indent=1))
        print(json.dumps(sc, indent=1))

asyncio.run(main())
