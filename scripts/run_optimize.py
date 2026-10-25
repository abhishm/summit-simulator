"""CLI: run the optimization loop and save it to data/runs/<id>.json (used for demo pre-runs).

uv run python scripts/run_optimize.py --rounds 4 --blocks 5 --thinking high [--visual]
"""
import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import personas as P  # noqa: E402
from app.optimize import optimize  # noqa: E402

RUNS = Path(__file__).resolve().parents[1] / "data" / "runs"


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rounds", type=int, default=4)
    ap.add_argument("--blocks", type=int, default=5)
    ap.add_argument("--thinking", default="high")
    ap.add_argument("--name", default=None)
    ap.add_argument("--visual", action="store_true", help="screenshot each block + Argon visual critique per round")
    a = ap.parse_args()
    run_id = a.name or time.strftime("run-%H%M%S")
    ps = P.load()
    t0 = time.time()

    async def emit(kind, data):
        if kind == "round_done":
            s = data["score"]
            print(f"[{time.time() - t0:6.0f}s] round {data['round']}: total={s['total']} cons={s['consensus']} "
                  f"incl={s['inclusion']} air={s['airtime']} cross={s['cross_faction']}", flush=True)
        elif kind == "round_start" and data.get("critique"):
            print(f"[{time.time() - t0:6.0f}s] round {data['round']} plan: "
                  f"{[b['format'] for b in data['plan']['blocks']]}\n  critique: {data['critique'][:400]}",
                  flush=True)
        elif kind == "visual" and not data.get("pending"):
            if data.get("error"):
                print(f"[{time.time() - t0:6.0f}s] visual critic failed: {data['error']}", flush=True)
            else:
                print(f"[{time.time() - t0:6.0f}s] visual critic round {data['round']}: {data['score']}/10 "
                      f"(render {data['render_seconds']}s, total {data['seconds']}s) {data['summary'][:300]}",
                      flush=True)
                if data.get("resolved"):
                    print(f"    previous flaws fixed: {data['resolved']['fixed']}/{data['resolved']['total']}", flush=True)
                for f in data["flaws"]:
                    print(f"    - B{f['block']}: {f['issue'][:160]}", flush=True)
        elif kind == "thinking":
            print(f"[{time.time() - t0:6.0f}s] Argon thinking (round {data['round']})...", flush=True)

    out = await optimize(ps, rounds=a.rounds, n_blocks=a.blocks, thinking=a.thinking, emit=emit,
                         visual=a.visual, run_id=run_id)
    out.update(id=run_id, config=vars(a), seconds=round(time.time() - t0))
    RUNS.mkdir(parents=True, exist_ok=True)
    (RUNS / f"{run_id}.json").write_text(json.dumps(out, indent=1))
    print(f"saved {RUNS / f'{run_id}.json'} best=round {out['best']} in {out['seconds']}s")


if __name__ == "__main__":
    asyncio.run(main())
