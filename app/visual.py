"""Render → watch → critique: screenshot every block of a round in the 3D venue, then Argon critiques the images.

Playwright loads web/index.html in "static" mode with all requests served from disk (no server needed), calls
window.showBlock() for each block and screenshots the venue. The JPEGs go to data/visual/<run>/r<round>-b<block>.jpg
and are sent to gemini-4-argon as an adversarial visual critic whose flaws feed the next revise() prompt.
"""
import base64
import json
import time
from pathlib import Path

from pydantic import BaseModel, Field

from .gemini import ARGON, structured
from .models import ISSUES
from .simulate import ROOMS

ROOT = Path(__file__).resolve().parent.parent
WEB, VISUAL = ROOT / "web", ROOT / "data" / "visual"
BASE = "http://summit.local"
VIEWPORT = {"width": 1024, "height": 640}


class Flaw(BaseModel):
    block: int = Field(description="1-based block number the flaw is visible in")
    issue: str = Field(description="What is visibly wrong, naming guests/rooms/factions")
    fix: str = Field(description="A concrete change to groupings, format or facilitation that fixes it")


class VisualCritique(BaseModel):
    score: float = Field(description="0-10: how well the rendered seating actually mixes, includes and balances guests")
    flaws: list[Flaw] = Field(description="At least 3 specific flaws, most damaging first")
    summary: str = Field(description="One or two sentences: the overall visual verdict")


def _d(x) -> dict:
    return x if isinstance(x, dict) else x.model_dump()


async def _route(route):
    path = route.request.url.removeprefix(BASE).split("?")[0]
    if path in ("", "/"):
        return await route.fulfill(path=WEB / "index.html")
    if path == "/api/meta":
        return await route.fulfill(json={"issues": {k: list(v) for k, v in ISSUES.items()}, "rooms": ROOMS,
                                          "demo_mode": False})
    if path.startswith("/web/"):
        f = (WEB / path.removeprefix("/web/")).resolve()
        if f.is_file() and WEB in f.parents:
            return await route.fulfill(path=f)
    await route.abort()


async def render_round(personas, plan, groups, ratings, run_id: str, rnd: int) -> list[Path]:
    """Screenshot every block of one simulated round. Returns the JPEG paths (one per block)."""
    from playwright.async_api import async_playwright  # noqa: PLC0415  (optional dependency at import time)

    personas, plan = [_d(p) for p in personas], _d(plan)
    groups, ratings = [_d(g) for g in groups], [_d(r) for r in ratings]
    out = VISUAL / run_id
    out.mkdir(parents=True, exist_ok=True)
    paths = []
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        try:
            page = await browser.new_page(viewport=VIEWPORT)
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            await page.route("**/*", _route)
            await page.goto(f"{BASE}/?static=1", wait_until="domcontentloaded")
            try:
                await page.wait_for_function("window.summitReady === true", timeout=20000)
            except Exception as e:
                raise RuntimeError(f"venue did not load: {errors or e}") from e
            for bi in range(len(plan["blocks"])):
                gs = [{"room": g["room"], "members": g["members"]} for g in groups if g["block"] == bi]
                if not gs:  # not simulated yet: fall back to the planned groups
                    rooms = ROOMS[plan["blocks"][bi]["format"]]
                    gs = [{"room": rooms[min(i, len(rooms) - 1)], "members": m}
                          for i, m in enumerate(plan["blocks"][bi]["groups"])]
                await page.evaluate("(a) => window.showBlock(a)", {"personas": personas, "plan": plan, "groups": gs,
                                                                   "block": bi, "ratings": ratings, "round": rnd})
                p = out / f"r{rnd}-b{bi}.jpg"
                await page.screenshot(path=str(p), type="jpeg", quality=72)
                paths.append(p)
        finally:
            await browser.close()
    return paths


def _describe(personas, plan, groups, ratings) -> str:
    by = {p["id"]: p for p in personas}
    heard = {r["id"]: r["felt_heard"] for r in ratings}
    lines = [f'Plan "{plan["name"]}":']
    for bi, b in enumerate(plan["blocks"]):
        lines.append(f'Block {bi + 1}: "{b["title"]}" | {b["format"]} | topic {b["topic"]}')
        for g in [g for g in groups if g["block"] == bi]:
            who = ", ".join(f'{m} ({by[m]["faction"]}, {by[m]["power"]} power)' if m in by else m for m in g["members"])
            lines.append(f'  {g["room"]}: {who}')
    lines.append("Judge's felt-heard ratings (0-10): " + ", ".join(f"{k}={v}" for k, v in sorted(heard.items(),
                                                                                              key=lambda kv: kv[1])))
    return "\n".join(lines)


async def critique(personas, plan, groups, ratings, images: list[Path], rnd: int,
                   thinking: str = "medium") -> VisualCritique:
    personas, plan = [_d(p) for p in personas], _d(plan)
    groups, ratings = [_d(g) for g in groups], [_d(r) for r in ratings]
    prompt = f"""You are an adversarial visual critic for an AI-safety summit agenda. Below are screenshots of a 3D
render of the venue, one per agenda block (round {rnd}). Each avatar is one guest, colored by faction (blue
regulator, orange government, red industry, teal academia, green civil society). The ring under each guest is how
heard the judge says they felt over the day (green >= 8, yellow >= 6, red < 6; bigger = more heard). Rooms: Plenary
Hall, Lounge (pairs), Breakouts A-D.

Look at the images. Find what an experienced convener would object to: guests isolated or stuck at the edge of a
huge plenary circle, factions that cluster together or never share a room across the day, the same people
repeatedly grouped together, empty rooms while others are crowded, low-power guests drowned out by high-power
ones, unbalanced room sizes, red rings that the layout explains. Be specific (name guests, blocks and rooms) and
harsh but fair; only report flaws grounded in the images and the plan below. Give at least 3 flaws, each with a
concrete fix a human organizer could make. Score 0-10 (10 = every block visibly mixes factions in small, balanced,
inclusive groups).

{_describe(personas, plan, groups, ratings)}"""
    content: list[dict] = [{"type": "text", "text": prompt}]
    for i, p in enumerate(images):
        content.append({"type": "text", "text": f"Screenshot of block {i + 1}:"})
        content.append({"type": "image", "data": base64.b64encode(p.read_bytes()).decode(), "mime_type": "image/jpeg"})
    return await structured(ARGON, content, VisualCritique, thinking=thinking)


async def visual_round(personas, plan, groups, ratings, run_id: str, rnd: int, thinking: str = "medium") -> dict:
    """Render + critique one round. Returns the dict stored as history[rnd]["visual"] and emitted as an SSE event."""
    t0 = time.time()
    paths = await render_round(personas, plan, groups, ratings, run_id, rnd)
    t1 = time.time()
    c = await critique(personas, plan, groups, ratings, paths, rnd, thinking)
    return {"round": rnd, **c.model_dump(), "images": [str(p.relative_to(ROOT)) for p in paths],
            "render_seconds": round(t1 - t0, 1), "seconds": round(time.time() - t0, 1)}


def for_prompt(v: dict) -> str:
    """Compact text of a visual critique for the next revise() prompt."""
    flaws = "\n".join(f"- block {f['block']}: {f['issue']} -> fix: {f['fix']}" for f in v["flaws"])
    return f"visual score {v['score']}/10. {v['summary']}\n{flaws}"


if __name__ == "__main__":  # quick render check: uv run python -m app.visual demo-5block 2
    import asyncio
    import sys

    run = json.loads((ROOT / "data" / "runs" / f"{sys.argv[1]}.json").read_text())
    h = run["history"][int(sys.argv[2])]
    t = time.time()
    ps = asyncio.run(render_round(run["personas"], h["plan"], h["result"]["groups"], h["result"]["ratings"],
                                  sys.argv[1], int(sys.argv[2])))
    print(f"{len(ps)} screenshots in {time.time() - t:.1f}s:", *ps, sep="\n")
