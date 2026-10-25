"""Antigravity managed agent (running on Gemini 4 Argon) prepares a draft delegate bundle for an approved plan.

In its sandbox the agent writes one markdown briefing packet, one .ics calendar invite and one PDF per guest, writes and
runs a checker (schedule lines, co-participants, openings, counterparts, .ics and PDF parse), fixes what fails, and
zips everything with a manifest. We download the zip from the sandbox and re-verify it locally. Nothing is sent: the
organizer reviews and downloads the bundle.
"""
import asyncio
import io
import json
import re
import time
import zipfile
from pathlib import Path

from .gemini import aclient, client

AGENT = "antigravity-preview-09-2026"
SUMMIT_DATE = "2026-11-02"  # placeholder date for the .ics invites
TZ = "America/Los_Angeles"
ROOT = Path(__file__).resolve().parent.parent
APPROVED = ROOT / "data" / "approved"
SANDBOX_DIR = "/workspace/summit"

LINE_RE = re.compile(r"(\d{1,2}:\d{2})\s*[-–]\s*(\d{1,2}:\d{2})\s*\|\s*([^|]+?)\s*\|\s*(.*)")
STOP = set("""about above after again against their there these those which while would could should other where being
having under until where with within without into from that this have will been were they them than then also only
other such each more most some very what when your yours over between through across before during model models
including include ensure provide providers system systems based level strict strictly major""".split())


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


# ---------- strict local verification ----------
def keywords(texts: list[str]) -> set[str]:
    words = re.findall(r"[a-z0-9][a-z0-9\-']{4,}", " ".join(texts).lower())
    return {w.strip("-'") for w in words} - STOP


def _ids_in(text: str, ids: list[str]) -> set[str]:
    return {i for i in ids if re.search(rf"(?<![A-Za-z0-9_]){re.escape(i)}(?![A-Za-z0-9_])", text)}


def _shingles(text: str, n: int) -> set[str]:
    w = re.findall(r"[a-z0-9']+", text.lower())
    return {" ".join(w[i:i + n]) for i in range(len(w) - n + 1)}


def _sections(md: str, level: str = "## ") -> list[tuple[str, str]]:
    out, title, buf = [], "", []
    for line in md.splitlines():
        if line.startswith(level):
            out.append((title, "\n".join(buf)))
            title, buf = line[len(level):].strip().lower(), []
        else:
            buf.append(line)
    out.append((title, "\n".join(buf)))
    return out


def _section(md: str, word: str) -> str | None:
    hits = [body for t, body in _sections(md) if word in t]
    return hits[0] if hits else None


def _entries(body: str, ids: list[str]) -> dict[str, str]:
    """Counterpart entries: a chunk starts at a bullet/heading line and belongs to the first guest id it names."""
    chunks: list[str] = []
    for line in body.splitlines():
        if re.match(r"\s*([-*#]|\d+\.)", line) or not chunks:
            chunks.append(line)
        else:
            chunks[-1] += "\n" + line
    out: dict[str, str] = {}
    last = None
    for c in chunks:
        found = [i for i in ids if i in _ids_in(c, ids)]
        first = min(found, key=lambda i: c.find(i)) if found else None
        if first:
            out[first] = out.get(first, "") + "\n" + c
            last = first
        elif last:
            out[last] += "\n" + c
    return out


def verify(sched: list[dict], packets: dict[str, str], ids: list[str], personas: list[dict] | None = None) -> list[str]:
    """Strict check of every packet against the schedule (and, given personas, the openings and counterparts)."""
    errs = []
    by_id = {p["id"]: p for p in personas or []}
    for pid in ids:
        md = packets.get(pid)
        if not md:
            errs.append(f"{pid}: missing packet")
            continue
        mine = [(b, g) for b in sched for g in b["groups"] if pid in g["members"]]
        day = _section(md, "your day")
        if day is None:
            errs.append(f"{pid}: no 'Your day' section")
            day = ""
        lines = day.splitlines()
        parsed = []
        for li, line in enumerate(lines):
            m = LINE_RE.search(line)
            if m:
                rest = m.group(4)
                nxt = lines[li + 1] if li + 1 < len(lines) else ""
                if not LINE_RE.search(nxt) and "with" in nxt.lower():
                    rest += " " + nxt
                parsed.append((m.group(1).zfill(5), m.group(2).zfill(5), m.group(3).strip(" *`_"), rest))
        starts = {b["start"] for b, _ in mine}
        for s, *_ in parsed:
            if s not in starts:
                errs.append(f"{pid}: schedule line at {s} matches none of your blocks")
        met: set[str] = set()
        for b, g in mine:
            n = b["block"]
            hits = [p for p in parsed if p[0] == b["start"]]
            if not hits:
                errs.append(f"{pid}: block {n} has no '{b['start']}-{b['end']} | room | title' line")
                continue
            if len(hits) > 1:
                errs.append(f"{pid}: block {n} has {len(hits)} schedule lines")
            _, end, room, rest = hits[0]
            if end != b["end"]:
                errs.append(f"{pid}: block {n} ends {end}, expected {b['end']}")
            if room != g["room"]:
                errs.append(f"{pid}: block {n} room '{room}' on the {b['start']} line, expected '{g['room']}'")
            if b["format"] == "plenary":
                continue
            want = set(g["members"]) - {pid}
            met |= want
            got = _ids_in(rest, ids) - {pid}
            for o in sorted(want - got):
                errs.append(f"{pid}: block {n} co-participant {o} missing from the {b['start']} line")
            for o in sorted(got - want):
                errs.append(f"{pid}: block {n} lists {o}, who is not in your group")
        if not by_id:
            continue
        op = _section(md, "opening")
        if op is None:
            errs.append(f"{pid}: no 'Openings' section")
        else:
            subs = _sections(op, "### ")
            all_b = [ln for _, body in subs for ln in re.findall(r"(?m)^\s*(?:[-*]|\d+\.)\s+\S.*$", body)]
            counts: dict[str, int] = {}
            for ln in all_b:
                for sh in _shingles(ln, 6):
                    counts[sh] = counts.get(sh, 0) + 1
            common = [sh for sh, c in counts.items() if c >= 3 and c >= len(all_b) / 2]
            if common:
                errs.append(f"{pid}: openings are templated ('{common[0]}…' in {counts[common[0]]}/{len(all_b)} bullets)")
            for b, g in mine:
                if b["format"] == "plenary":
                    continue
                n, want = b["block"], set(g["members"]) - {pid}
                sub = next((body for t, body in subs if b["start"] in t or re.search(rf"block {n}\b", t)), None)
                if sub is None:
                    errs.append(f"{pid}: no openings subsection for block {n}")
                    continue
                bullets = "\n".join(re.findall(r"(?m)^\s*(?:[-*]|\d+\.)\s+\S.*$", sub))
                if bullets.count("\n") < 1:
                    errs.append(f"{pid}: block {n} openings have fewer than 2 bullets")
                named = _ids_in(sub, ids) - {pid}
                if not _ids_in(bullets, ids) & want:
                    errs.append(f"{pid}: block {n} openings name none of your co-participants")
                for o in sorted(named - want):
                    errs.append(f"{pid}: block {n} openings address {o}, who is not in your group")
                ctx = keywords([x for o in want for x in by_id[o]["red_lines"][:3] + by_id[o]["tradeoffs"][:3]])
                src = [x for o in want for x in by_id[o]["red_lines"] + by_id[o]["tradeoffs"]]
                if _shingles(bullets, 10) & _shingles(" || ".join(src), 10):
                    errs.append(f"{pid}: block {n} openings paste persona red lines/tradeoffs verbatim")
                if len(keywords([bullets]) & ctx) < 3:
                    errs.append(f"{pid}: block {n} openings don't engage co-participants' red lines/tradeoffs")
        cp = _section(md, "counterpart")
        if cp is None:
            errs.append(f"{pid}: no 'Know your counterparts' section")
            continue
        ent = _entries(cp, ids)
        for o in sorted(met):
            e = ent.get(o)
            if not e:
                errs.append(f"{pid}: counterparts missing {o}")
                continue
            if len(keywords([e]) & keywords(by_id[o]["red_lines"][:3])) < 2:
                errs.append(f"{pid}: counterpart {o} entry doesn't reflect their red lines")
            if len(keywords([e]) & keywords(by_id[o]["tradeoffs"][:3])) < 2:
                errs.append(f"{pid}: counterpart {o} entry doesn't reflect their tradeoffs")
        for o in sorted(set(ent) - met - {pid}):
            errs.append(f"{pid}: counterparts lists {o}, whom you never meet in a small group")
    return errs


def _ics_events(text: str) -> list[dict]:
    text = re.sub(r"\r?\n[ \t]", "", text)  # unfold
    evs = []
    for blk in re.findall(r"BEGIN:VEVENT(.*?)END:VEVENT", text, re.S):
        ev = {}
        for line in blk.strip().splitlines():
            k, _, v = line.partition(":")
            ev[k.split(";")[0].upper()] = v.replace("\\,", ",").replace("\\;", ";").strip()
        evs.append(ev)
    return evs


def verify_artifacts(sched: list[dict], files: dict[str, bytes], ids: list[str]) -> list[str]:
    """Dependency-free re-check of the sandbox's .ics, PDF and manifest files."""
    errs = []
    if "manifest.json" not in files:
        errs.append("bundle: manifest.json missing")
    ymd = SUMMIT_DATE.replace("-", "")
    for pid in ids:
        mine = [(b, g) for b in sched for g in b["groups"] if pid in g["members"]]
        ics = files.get(f"ics/{pid}.ics")
        if ics is None:
            errs.append(f"{pid}: ics missing")
        else:
            text = ics.decode("utf-8", "replace")
            evs = _ics_events(text)
            if "BEGIN:VCALENDAR" not in text or len(evs) != len(mine):
                errs.append(f"{pid}: ics has {len(evs)} events, expected {len(mine)}")
            for b, g in mine:
                st, en = f"{ymd}T{b['start'].replace(':', '')}00", f"{ymd}T{b['end'].replace(':', '')}00"
                ev = next((e for e in evs if e.get("DTSTART", "").startswith(st)), None)
                if ev is None:
                    errs.append(f"{pid}: ics has no event starting {st}")
                elif not ev.get("DTEND", "").startswith(en) or ev.get("LOCATION") != g["room"]:
                    errs.append(f"{pid}: ics event {st} has end/location {ev.get('DTEND')}/{ev.get('LOCATION')}")
        pdf = files.get(f"pdf/{pid}.pdf")
        if pdf is None:
            errs.append(f"{pid}: pdf missing")
        elif not pdf.startswith(b"%PDF-") or b"%%EOF" not in pdf[-1024:] or not re.search(rb"/Type\s*/Page[^s]", pdf):
            errs.append(f"{pid}: pdf is not a valid PDF with pages")
    return errs


# ---------- the agent ----------
def _prompt(plan: dict, sched: list[dict], personas: list[dict], key: str) -> str:
    brief = [{k: p[k] for k in ("id", "title", "faction", "summary", "stances", "red_lines", "tradeoffs")}
             for p in personas]
    return f"""You are preparing a DRAFT delegate bundle for an approved 1-day AI-safety summit: "{plan['name']}".
Nothing will be sent; the organizer reviews the bundle first. Summit date {SUMMIT_DATE}, timezone {TZ}.

Work in {SANDBOX_DIR}. `pip install icalendar fpdf2 pypdf` first. Steps:
1. Save the schedule and guest list below to schedule.json and guests.json.
2. For EVERY guest write packets/<guest_id>.md in exactly this structure:
   # <title> (`<guest_id>`)
   <one paragraph: the purpose of their day>
   ## Your day
   One bullet per block the guest attends, ALL on ONE line:
   - HH:MM-HH:MM | <exact room name of THEIR group> | <session title> | with: <id> (<title>), <id> (<title>)
   For plenary blocks omit the "| with: ..." part. List exactly the other members of their group: no one else.
   ## Openings
   For each non-plenary block a subsection `### Block N: HH:MM-HH:MM | <room>` with 2-3 bullets. Each bullet is a
   concrete, session-specific offer or question that THIS guest makes (from their own stances and tradeoffs),
   addressed by id to a co-participant IN THAT GROUP, that steers clear of that person's red lines and meets what
   they'd trade. Paraphrase in the guest's voice: do NOT paste red lines/tradeoffs verbatim, do NOT fill a string
   template, and do NOT reuse the same sentence frame across bullets. Write each packet's openings yourself, guest
   by guest (scripts may only assemble/validate files). Never mention guest ids who are not in that group.
   ## Know your counterparts
   One bullet per guest they share a non-plenary group with (exactly those, no one else):
   - **<id>** (<title>) — Top red line: <from their red_lines> | Would trade: <from their tradeoffs>
3. For every guest write ics/<guest_id>.ics with the `icalendar` library: one VEVENT per block they attend,
   DTSTART/DTEND with TZID={TZ} on {SUMMIT_DATE}, SUMMARY=session title, LOCATION=exact room name,
   DESCRIPTION=co-participant ids, UID=<guest_id>-b<N>@{key}.
4. For every guest render pdf/<guest_id>.pdf from their packet with fpdf2 (use a Unicode TTF font such as DejaVuSans
   if present, otherwise transliterate non-Latin-1 characters). The PDF text must contain the guest id and every
   block start time.
5. Write check.py that, for every guest, asserts:
   a. In "## Your day", each block they attend has exactly one `HH:MM-HH:MM | room | title` line whose start, end AND
      room match that block on the SAME line; no lines for blocks they don't attend; for non-plenary blocks the guest
      ids on that line are exactly their group minus themselves (flag missing AND extra ids).
   b. "## Openings" has a `### Block N` subsection per non-plenary block with >= 2 bullets that name at least one
      co-participant id, name no id outside the group, and share >= 3 distinctive words (5+ letters) with those
      co-participants' red_lines + tradeoffs; no 10-word run copied verbatim from those red_lines/tradeoffs; and no
      6-word phrase repeated in half or more (and >= 3) of the packet's opening bullets (that means templated text).
   c. "## Know your counterparts" has an entry for exactly the guests met in non-plenary groups, each sharing >= 2
      distinctive words with that guest's red_lines and >= 2 with their tradeoffs.
   d. ics/<id>.ics parses with icalendar.Calendar.from_ical, has one VEVENT per attended block, and each event's
      start, end and LOCATION match the schedule.
   e. pdf/<id>.pdf opens with pypdf.PdfReader, has >= 1 page, and its extracted text contains the guest id and every
      block start time.
   f. bundle.zip (if present) passes zipfile.testzip() and contains every packet, ics, pdf plus manifest.json.
   Run it, fix whatever fails (fix the artifacts, never weaken the checks), and repeat until it passes.
6. Write manifest.json: {{"summit", "date", "status": "DRAFT - awaiting organizer approval; nothing has been sent",
   "guests": [{{"id", "title", "blocks", "packet", "ics", "pdf", "sha256": {{file: hash}}}}]}}. Then zip packets/, ics/,
   pdf/, manifest.json, check.py and check_output.txt (the last check.py output) into {SANDBOX_DIR}/bundle.zip
   (paths inside the zip relative to {SANDBOX_DIR}). Run check.py once more and confirm it passes with the zip.
7. Reply with ONLY a JSON object (no prose, no code fences):
   {{"checks_passed": true|false, "check_output": "<last check.py output, max 1500 chars>",
     "fixes": "<one sentence: what failed during your checks and how you fixed it>",
     "bundle": "{SANDBOX_DIR}/bundle.zip"}}

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


async def _download(env: str, path: str) -> bytes:
    def get():
        return bytes(client().environments.files.download(environment=env, path=path))
    return await asyncio.to_thread(get)


async def generate(run: dict, rnd: int, model: str = "gemini-4-argon", key: str | None = None) -> dict:
    plan = run["history"][rnd]["plan"]
    sched = schedule(plan)
    ids = [p["id"] for p in run["personas"]]
    key = key or f"{run.get('id', 'run')}-r{rnd}"
    r = await aclient().interactions.create(
        agent=AGENT, agent_config={"type": "antigravity", "model": model},
        input=_prompt(plan, sched, run["personas"], key), environment="remote")
    out = _parse(r.output_text)
    zbytes = await _download(r.environment_id, out.get("bundle") or f"{SANDBOX_DIR}/bundle.zip")
    files = {n: zipfile.ZipFile(io.BytesIO(zbytes)).read(n) for n in zipfile.ZipFile(io.BytesIO(zbytes)).namelist()
             if not n.endswith("/")}
    files = {re.sub(r"^(\./|workspace/summit/|/workspace/summit/)", "", n): b for n, b in files.items()}
    packets = {Path(n).stem: b.decode() for n, b in files.items()
               if n.startswith("packets/") and n.endswith(".md") and Path(n).stem in ids}
    errs = verify(sched, packets, ids, run["personas"]) + verify_artifacts(sched, files, ids)
    steps = [s.type for s in (r.steps or [])]
    return {"interaction": r.id, "environment": r.environment_id, "packets": packets, "bundle_bytes": zbytes,
            "bundle_files": sorted(files), "agent_checks_passed": out.get("checks_passed"),
            "agent_check_output": out.get("check_output", ""), "agent_fixes": out.get("fixes", ""),
            "local_errors": errs, "tool_steps": sum(t.endswith("_call") for t in steps)}


# ---------- cache ----------
def save(key: str, out: dict) -> dict:
    d = APPROVED / f"{key}-packets"
    d.mkdir(parents=True, exist_ok=True)
    for pid, md in out["packets"].items():
        (d / f"{pid}.md").write_text(md)
    if out.get("bundle_bytes"):
        (APPROVED / f"{key}-bundle.zip").write_bytes(out["bundle_bytes"])
    meta = {k: v for k, v in out.items() if k not in ("packets", "bundle_bytes")}
    (APPROVED / f"{key}-packets.json").write_text(json.dumps(meta, indent=1))
    return meta


def load(key: str, run: dict | None = None) -> dict | None:
    d = APPROVED / f"{key}-packets"
    if not d.exists():
        return None
    packets = {f.stem: f.read_text() for f in sorted(d.glob("*.md"))}
    mf = APPROVED / f"{key}-packets.json"
    meta = json.loads(mf.read_text()) if mf.exists() else {"agent_checks_passed": True}
    if run is not None:  # always re-run the current (strict) check on what's cached
        rnd = int(key.rsplit("-r", 1)[1])
        sched, ids = schedule(run["history"][rnd]["plan"]), [p["id"] for p in run["personas"]]
        meta["local_errors"] = verify(sched, packets, ids, run["personas"])
        bz = APPROVED / f"{key}-bundle.zip"
        if bz.exists():
            z = zipfile.ZipFile(bz)
            meta["local_errors"] += verify_artifacts(sched, {n: z.read(n) for n in z.namelist()}, ids)
    of = APPROVED / f"{key}-openings.json"
    return {"status": "done", "cached": True, **meta, "packets": packets,
            "bundle": (APPROVED / f"{key}-bundle.zip").exists(),
            "openings_score": json.loads(of.read_text()) if of.exists() else None}


# ---------- do the suggested openings raise consensus? ----------
def openings_text(md: str) -> str:
    op = _section(md, "opening") or ""
    out = []
    for t, body in _sections(op, "### "):
        bullets = [re.sub(r"^\s*([-*]|\d+\.)\s+", "", ln).strip() for ln in body.splitlines()
                   if re.match(r"\s*([-*]|\d+\.)\s+\S", ln)]
        if t and bullets:
            out.append(f"{t.split('|')[0].strip().title()}: " + " / ".join(bullets))
    return " || ".join(out)


async def score_openings(run: dict, rnd: int, packets: dict[str, str], cap: int = 1500) -> dict:
    """Re-simulate the approved plan once without and once with each guest's packet openings in their brief."""
    from .models import Persona, Plan
    from .simulate import simulate
    plan = Plan.model_validate(run["history"][rnd]["plan"])
    base = [Persona.model_validate(p) for p in run["personas"]]
    prepped = []
    for p in base:
        o = openings_text(packets.get(p.id, ""))[:cap]
        prepped.append(p.model_copy(update={"engagement": p.engagement + (
            f"\n  prepared openings from their briefing packet (they open with these offers): {o}" if o else "")}))
    t0 = time.time()
    a, b = await asyncio.gather(simulate(base, plan), simulate(prepped, plan))
    keys = ("total", "consensus", "inclusion", "airtime", "cross_faction")
    sa, sb = a.score.model_dump(), b.score.model_dump()
    return {"without": {k: sa[k] for k in keys} | {"cross_agreements": len(sa["detail"]["cross_agreements"]),
                                                   "spread_after": sa["detail"]["spread_after"]},
            "with": {k: sb[k] for k in keys} | {"cross_agreements": len(sb["detail"]["cross_agreements"]),
                                                "spread_after": sb["detail"]["spread_after"]},
            "delta_consensus": round(sb["consensus"] - sa["consensus"], 1),
            "delta_total": round(sb["total"] - sa["total"], 1),
            "saved_round_score": run["history"][rnd]["result"]["score"]["total"],
            "seconds": round(time.time() - t0), "note": "one Flash simulation each; single-sample, noisy"}

