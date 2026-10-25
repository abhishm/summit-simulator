"""FastAPI server: live optimization runs streamed over SSE, saved-run replay, approval, live Deep Research.

uv run uvicorn app.server:app --port 8000
DEMO_MODE=1 makes "new run" replay the best saved run (no API calls), the offline fallback for the demo.
"""
import asyncio
import json
import os
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import personas as P
from .models import ISSUES, Persona
from .optimize import optimize
from .simulate import ROOMS, _clamp_moves

ROOT = Path(__file__).resolve().parent.parent
RUNS, APPROVED, WEB = ROOT / "data" / "runs", ROOT / "data" / "approved", ROOT / "web"
VISUAL = ROOT / "data" / "visual"
DEMO_MODE = os.getenv("DEMO_MODE") == "1"

app = FastAPI(title="Summit Simulator")
LIVE: dict[str, dict] = {}  # run_id -> {"events": [...], "done": bool, "cond": asyncio.Condition}


class RunReq(BaseModel):
    rounds: int = 3
    blocks: int = 3
    thinking: str = "medium"
    visual: bool = False  # Playwright screenshots + Argon visual critique before each revision


class ApproveReq(BaseModel):
    run_id: str
    round: int | None = None


class ResearchReq(BaseModel):
    id: str
    faction: str
    description: str


# ---------- helpers ----------
def _saved(run_id: str) -> dict:
    f = RUNS / f"{run_id}.json"
    if not f.exists():
        raise HTTPException(404, f"no run {run_id}")
    return json.loads(f.read_text())


def _run_list() -> list[dict]:
    out = []
    for f in sorted(RUNS.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True):
        try:
            d = json.loads(f.read_text())
            h = d["history"]
            out.append(dict(id=d.get("id", f.stem), rounds=len(h) - 1, config=d.get("config", {}),
                            scores=[r["result"]["score"]["total"] for r in h], best=d["best"]))
        except Exception:
            continue
    return out


def _replay_events(run: dict) -> list[tuple[str, dict]]:
    """Reconstruct the live event stream from a saved run so the frontend has a single code path."""
    by_id = {p["id"]: p for p in run["personas"]}
    ev = []
    for h in run["history"]:
        r, res = h["round"], h["result"]
        if r > 0:
            ev.append(("thinking", {"round": r}))
        ev.append(("round_start", {"round": r, "plan": h["plan"], "critique": h["critique"], "changes": h["changes"]}))
        stances = {k: dict(v) for k, v in res["initial_stances"].items()}
        for bi, block in enumerate(h["plan"]["blocks"]):
            gs = [g for g in res["groups"] if g["block"] == bi]
            for g in gs:
                for pid, upd in g["stance_updates"].items():
                    if pid in stances:
                        stances[pid].update(_clamp_moves(block["format"], stances[pid], upd))
            ev.append(("block", {"round": r, "block": bi, "groups": gs, "stances": stances}))
            stances = {k: dict(v) for k, v in stances.items()}
        ev.append(("round_done", {"round": r, "score": res["score"], "ratings": res["ratings"]}))
        if h.get("visual"):
            ev.append(("visual", h["visual"]))
    ev.append(("done", {"run_id": run.get("id"), "best": run["best"], "personas": list(by_id)}))
    return ev


async def _push(run_id: str, kind: str, data: dict):
    st = LIVE[run_id]
    async with st["cond"]:
        st["events"].append((kind, data))
        st["cond"].notify_all()


async def _do_run(run_id: str, req: RunReq):
    t0 = time.time()
    try:
        if DEMO_MODE:
            runs = _run_list()
            if not runs:
                raise RuntimeError("DEMO_MODE but no saved runs")
            demos = [r for r in runs if r["id"].startswith("demo")] or runs
            src = max(demos, key=lambda r: max(r["scores"]))
            for kind, data in _replay_events(_saved(src["id"]))[:-1]:
                await asyncio.sleep(2.5 if kind == "thinking" else 1.2)
                await _push(run_id, kind, data)
            await _push(run_id, "done", {"run_id": src["id"], "best": _saved(src["id"])["best"]})
            return
        else:
            out = await optimize(P.load(), rounds=req.rounds, n_blocks=req.blocks, thinking=req.thinking,
                                 emit=lambda k, d: _push(run_id, k, d), visual=req.visual, run_id=run_id)
        out.update(id=run_id, config=req.model_dump() | {"demo_mode": DEMO_MODE}, seconds=round(time.time() - t0))
        RUNS.mkdir(parents=True, exist_ok=True)
        (RUNS / f"{run_id}.json").write_text(json.dumps(out, indent=1))
        await _push(run_id, "done", {"run_id": run_id, "best": out["best"]})
    except Exception as e:  # surface failures to the UI instead of hanging the stream
        await _push(run_id, "error", {"message": f"{type(e).__name__}: {e}"})
    finally:
        LIVE[run_id]["done"] = True
        async with LIVE[run_id]["cond"]:
            LIVE[run_id]["cond"].notify_all()


def _sse(kind: str, data: dict) -> str:
    return f"event: {kind}\ndata: {json.dumps(data)}\n\n"


# ---------- API ----------
@app.get("/api/meta")
def meta():
    return {"issues": {k: list(v) for k, v in ISSUES.items()}, "rooms": ROOMS, "demo_mode": DEMO_MODE}


@app.get("/api/personas")
def personas():
    return [p.model_dump() | {"researched": bool(p.sources)} for p in P.load()]


@app.get("/api/runs")
def runs():
    return _run_list()


@app.get("/api/runs/{run_id}")
def run(run_id: str):
    return _saved(run_id)


@app.post("/api/runs")
async def start_run(req: RunReq):
    run_id = time.strftime("live-%H%M%S")
    LIVE[run_id] = {"events": [], "done": False, "cond": asyncio.Condition()}
    asyncio.create_task(_do_run(run_id, req))
    return {"run_id": run_id, "demo_mode": DEMO_MODE}


@app.get("/api/runs/{run_id}/events")
async def events(run_id: str, speed: float = 1.0):
    if run_id in LIVE:
        async def live():
            st, i = LIVE[run_id], 0
            while True:
                async with st["cond"]:
                    while i >= len(st["events"]) and not st["done"]:
                        try:
                            await asyncio.wait_for(st["cond"].wait(), timeout=15)
                        except asyncio.TimeoutError:
                            break
                    batch, i = st["events"][i:], len(st["events"])
                    done = st["done"]
                for kind, data in batch:
                    yield _sse(kind, data)
                if not batch and not done:
                    yield ": keepalive\n\n"
                if done and i >= len(st["events"]):
                    return
        gen = live()
    else:
        evs = _replay_events(_saved(run_id))

        async def gen_replay():
            for kind, data in evs:
                yield _sse(kind, data)
                await asyncio.sleep({"thinking": 1.5, "block": 1.0, "round_done": 1.0, "visual": 1.0}.get(kind, 0.3) / max(speed, 0.1))
        gen = gen_replay()
    return StreamingResponse(gen, media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


def _run_of_show(run: dict, rnd: int) -> str:
    h = run["history"][rnd]
    plan, res = h["plan"], h["result"]
    titles = {p["id"]: p["title"] for p in run["personas"]}
    s = res["score"]
    lines = [f"# Run of show: {plan['name']}", "",
             f"Approved from run `{run.get('id')}` round {rnd}. Simulated score **{s['total']}/100** "
             f"(consensus {s['consensus']}/40, inclusion {s['inclusion']}/30, airtime {s['airtime']}/15, "
             f"cross-faction {s['cross_faction']}/15).", "", f"_{plan.get('rationale', '')}_", ""]
    t = 9 * 60
    for bi, b in enumerate(plan["blocks"]):
        dur = 45 if b["format"] == "plenary" else 60
        lines += [f"## {t // 60:02d}:{t % 60:02d}–{(t + dur) // 60:02d}:{(t + dur) % 60:02d} · {b['title']} "
                  f"({b['format']}, topic: {b['topic']})", "", f"**Facilitator prompt:** {b['prompt']}", ""]
        rooms = ROOMS[b["format"]]
        for gi, g in enumerate(b["groups"]):
            room = rooms[min(gi, len(rooms) - 1)] + (f" {gi + 1}" if b["format"] == "pairs" else "")
            lines.append(f"- **{room}:** " + "; ".join(titles.get(x, x) for x in g))
        lines.append("")
        t += dur + 15
    agreements = s["detail"].get("cross_agreements", [])
    if agreements:
        lines += ["## Agreements reached in simulation", ""] + [f"- {a}" for a in agreements] + [""]
    if h.get("critique"):
        lines += ["## Why this design (Gemini 4 Argon critique)", "", h["critique"], ""]
        lines += [f"- {c}" for c in h.get("changes", [])] + [""]
    lines += ["## Predicted felt-heard", ""] + [f"- {titles.get(r['id'], r['id'])}: {r['felt_heard']}/10 — {r['reason']}"
                                                for r in res["ratings"]]
    return "\n".join(lines) + "\n"


@app.post("/api/approve", response_class=PlainTextResponse)
def approve(req: ApproveReq):
    run = _saved(req.run_id)
    rnd = run["best"] if req.round is None else req.round
    md = _run_of_show(run, rnd)
    APPROVED.mkdir(parents=True, exist_ok=True)
    (APPROVED / f"{req.run_id}-r{rnd}.md").write_text(md)
    (APPROVED / f"{req.run_id}-r{rnd}.json").write_text(json.dumps(run["history"][rnd]["plan"], indent=1))
    return md


# ---------- Antigravity briefing packets for an approved plan ----------
PACKETS: dict[str, dict] = {}


async def _do_packets(key: str, run: dict, rnd: int):
    from .packets import generate  # noqa: PLC0415
    t0 = time.time()
    try:
        out = await generate(run, rnd)
        d = APPROVED / f"{key}-packets"
        d.mkdir(parents=True, exist_ok=True)
        for pid, md in out["packets"].items():
            (d / f"{pid}.md").write_text(md)
        PACKETS[key] = {"status": "done", "seconds": round(time.time() - t0), **out}
    except Exception as e:
        PACKETS[key] = {"status": "error", "message": f"{type(e).__name__}: {e}"}


@app.post("/api/packets")
async def packets_start(req: ApproveReq):
    run = _saved(req.run_id)
    rnd = run["best"] if req.round is None else req.round
    key = f"{req.run_id}-r{rnd}"
    if PACKETS.get(key, {}).get("status") != "running":
        PACKETS[key] = {"status": "running"}
        asyncio.create_task(_do_packets(key, run, rnd))
    return {"key": key}


@app.get("/api/packets/{key}")
def packets_status(key: str):
    if key in PACKETS:
        return PACKETS[key]
    d = APPROVED / f"{key}-packets"
    if d.exists():  # cached from an earlier session
        return {"status": "done", "cached": True, "packets": {f.stem: f.read_text() for f in sorted(d.glob("*.md"))},
                "local_errors": [], "agent_checks_passed": True}
    raise HTTPException(404)


# ---------- live Deep Research for a new guest ----------
RESEARCH: dict[str, dict] = {}


@app.post("/api/research")
def research_start(req: ResearchReq):
    from scripts.research_personas import AGENT, PROMPT, client  # noqa: PLC0415
    it = client().interactions.create(agent=AGENT, input=PROMPT.format(desc=req.description), background=True)
    RESEARCH[req.id] = {"interaction": it.id, "faction": req.faction, "status": it.status}
    return {"id": req.id, "interaction": it.id, "status": it.status}


@app.get("/api/research/{pid}")
async def research_status(pid: str):
    if pid not in RESEARCH:
        raise HTTPException(404)
    job = RESEARCH[pid]
    if job["status"] not in ("completed", "failed", "persona"):
        from scripts.research_personas import client  # noqa: PLC0415
        it = client().interactions.get(id=job["interaction"])
        job["status"] = it.status
        if it.status == "completed":
            report = it.output_text or ""
            (P.DIR / f"{pid}.md").write_text(report)
            p: Persona = await P.extract(pid, job["faction"], report)
            (P.DIR / f"{pid}.json").write_text(p.model_dump_json(indent=2))
            job["status"] = "persona"
    return job


# ---------- static ----------
@app.get("/")
def index():
    return FileResponse(WEB / "index.html")


app.mount("/web", StaticFiles(directory=WEB), name="web")
VISUAL.mkdir(parents=True, exist_ok=True)
app.mount("/data/visual", StaticFiles(directory=VISUAL), name="visual")  # visual-critic screenshots
