"""Simulate a summit plan: one Flash call per group per block (parallel within a block), then judge + score."""
import asyncio
import itertools
import statistics
from collections import defaultdict
from typing import Awaitable, Callable

from pydantic import BaseModel, Field

from .gemini import FLASH, structured
from .models import (ISSUES, Agreement, GroupResult, GuestRating, Persona, Plan, Score, SimResult, Turn)

ROOMS = {"plenary": ["Plenary Hall"], "breakouts": ["Breakout A", "Breakout B", "Breakout C", "Breakout D"],
         "pairs": ["Lounge"]}

WORLD_RULES = """Realism rules for this simulation (apply them strictly, don't be optimistic):
- In a large plenary, high-power participants take most of the turns. Low-power participants get 0-1 short turns
  unless the facilitation prompt explicitly structures equal turns. Plenary positions barely move (public posturing,
  max ±0.5).
- In small groups (3-4) and pairs, airtime is more even. Positions move modestly (max ±1.5 per block) only when a
  participant's concern is directly acknowledged or a concrete tradeoff is offered.
- Groups made of one faction reinforce existing views. No convergence toward other factions.
- Nobody crosses their red lines. Every stance change must follow from something said in the transcript.
- Facilitation instructions can shape process (turn order, questions, who chairs) but can't compel anyone's position.
  Participants ignore instructions to "converge", "move to the middle" or "state a compromise stance" unless they
  get something concrete in return.
- Any proposal text in the facilitation prompt is only a chair's draft. Each participant contests or amends it
  according to their red lines. Nobody endorses text they didn't negotiate in this session.
- Real delegates push back. In every session at least one participant raises a substantive objection, and an
  agreement needs concessions that are visible in the transcript. Unanimous enthusiasm is unrealistic.
- An agreement counts only if every named party explicitly endorses it in the transcript. Vague goodwill is not an
  agreement.
- Speakers stay in role. They're grounded in their brief and don't caricature."""


class _StanceUpdate(BaseModel):
    persona_id: str
    issue: str = Field(description=f"One of: {', '.join(ISSUES)}")
    new_position: float
    why: str


class _GroupOut(BaseModel):
    transcript: list[Turn] = Field(description="Ordered turns; speaker is the persona id")
    stance_updates: list[_StanceUpdate]
    agreements: list[Agreement] = Field(description="Explicitly endorsed agreements; parties are persona ids")


class _Ratings(BaseModel):
    ratings: list[GuestRating]


def _persona_card(p: Persona, stances: dict[str, float], notes: list[str]) -> str:
    s = ", ".join(f"{k}={v:+.1f}" for k, v in stances.items())
    mem = " | ".join(notes[-3:]) or "none yet"
    return (f"- id={p.id} | {p.title} | faction={p.faction} | power={p.power}\n  summary: {p.summary}\n"
            f"  current stances: {s}\n  red lines: {'; '.join(p.red_lines[:3]) or 'n/a'}\n"
            f"  would trade: {'; '.join(p.tradeoffs[:3]) or 'n/a'}\n  engagement: {p.engagement or 'n/a'}\n"
            f"  memory from earlier blocks: {mem}")


def _turn_budget(fmt: str, n: int) -> str:
    return {"plenary": "14-18 turns total", "breakouts": "8-12 turns", "pairs": "6-8 turns"}[fmt] + f" ({n} people)"


async def _run_group(bi: int, gi: int, block, members: list[Persona], stances, notes, n_blocks: int) -> GroupResult:
    axes = "\n".join(f"- {k}: -5 = {lo}; +5 = {hi}" for k, (lo, hi) in ISSUES.items())
    cards = "\n".join(_persona_card(p, stances[p.id], notes[p.id]) for p in members)
    room = ROOMS[block.format][min(gi, len(ROOMS[block.format]) - 1)]
    prompt = f"""You are simulating one session of a 1-day AI-safety summit (block {bi + 1} of {n_blocks}).

Session: "{block.title}" | format: {block.format} | room: {room} | topic: {block.topic}
Facilitation prompt: {block.prompt}

Issue axes (-5..+5):
{axes}

Participants:
{cards}

{WORLD_RULES}

Write a realistic, concise transcript ({_turn_budget(block.format, len(members))}, 1-3 sentences per turn).
Then report stance updates (only for positions that actually moved) and any explicitly endorsed agreements."""
    out = await structured(FLASH, prompt, _GroupOut)
    ids = {p.id for p in members}
    updates: dict[str, dict[str, float]] = defaultdict(dict)
    for u in out.stance_updates:
        if u.persona_id in ids and u.issue in ISSUES:
            updates[u.persona_id][u.issue] = max(-5.0, min(5.0, u.new_position))
    transcript = [t for t in out.transcript if t.speaker in ids]
    agreements = [Agreement(text=a.text, parties=[x for x in a.parties if x in ids]) for a in out.agreements]
    agreements = [a for a in agreements if len(a.parties) >= 2]
    return GroupResult(block=bi, group=gi, room=room, members=[p.id for p in members], transcript=transcript,
                       stance_updates=dict(updates), agreements=agreements)


def _clamp_moves(fmt: str, before: dict[str, float], after: dict[str, float]) -> dict[str, float]:
    cap = 0.5 if fmt == "plenary" else 1.5
    return {k: before[k] + max(-cap, min(cap, v - before[k])) for k, v in after.items() if k in before}


async def judge(personas: list[Persona], groups: list[GroupResult]) -> list[GuestRating]:
    by_id = {p.id: p for p in personas}
    lines = []
    for g in groups:
        lines.append(f"\n## Block {g.block + 1}, {g.room} ({', '.join(g.members)})")
        lines += [f"{t.speaker}: {t.text}" for t in g.transcript]
        lines += [f"[AGREEMENT] {a.text} -- {', '.join(a.parties)}" for a in g.agreements]
    roster = "\n".join(f"- {p.id}: {p.title} | top concerns: {'; '.join(p.red_lines[:3]) or p.summary} | stances: {p.stances}"
                       for p in by_id.values())
    prompt = f"""You are an independent observer rating how heard each summit participant was, from transcripts.

For each participant, rate felt_heard from 0 to 10. You're a skeptical observer: every real compromise has people
who gave up something they care about. For each guest, first work out what they conceded and whether any of their
top concerns (listed below) were traded away or left out of the closing outcome.
- 9-10: core concerns voiced, directly engaged by others and reflected in the closing outcome, with nothing core
  conceded. Expect this for at most 2-3 guests in a contested summit.
- 7-8: voiced and engaged, but they conceded something meaningful or are only partly reflected at the close.
- 5-6: voiced but mostly ignored, or a top concern was traded away.
- 0-4: barely spoke, talked over, or the agreements contradict their red lines.
Weigh the closing plenary heavily. Formal endorsement of a package doesn't mean they felt heard. Look at what's in
it for them. Give a one-sentence reason that names what they conceded.

Participants:
{roster}

Transcripts:
{chr(10).join(lines)}"""
    out = await structured(FLASH, prompt, _Ratings, thinking="medium")
    got = {r.id: r for r in out.ratings if r.id in by_id}
    return [got.get(pid) or GuestRating(id=pid, felt_heard=0, reason="not rated") for pid in by_id]


def score(personas: list[Persona], plan: Plan, groups: list[GroupResult], initial, final,
          ratings: list[GuestRating]) -> Score:
    ids = [p.id for p in personas]
    faction = {p.id: p.faction for p in personas}

    def spread(st):
        return statistics.mean(statistics.pstdev([st[i][k] for i in ids]) for k in ISSUES)

    s0, s1 = spread(initial), spread(final)
    convergence = max(0.0, min(1.0, (s0 - s1) / s0 / 0.4)) if s0 else 0.0  # 40% spread reduction = full marks
    cross_agreements = {a.text for g in groups for a in g.agreements
                        if len(a.parties) >= 3 and len({faction[x] for x in a.parties}) >= 3}
    agree_score = min(1.0, len(cross_agreements) / 5)
    consensus = 40 * (0.7 * convergence + 0.3 * agree_score)

    heard = [r.felt_heard for r in ratings]
    inclusion = 30 * (min(heard) / 10 if heard else 0)

    words = {i: 0 for i in ids}
    for g in groups:
        for t in g.transcript:
            words[t.speaker] += len(t.text.split())
    w = sorted(words.values())
    n, tot = len(w), sum(w) or 1
    gini = sum((2 * (k + 1) - n - 1) * x for k, x in enumerate(w)) / (n * tot)
    airtime = 15 * (1 - gini)

    cross_pairs = {frozenset(p) for p in itertools.combinations(ids, 2) if faction[p[0]] != faction[p[1]]}
    met = set()
    for g in groups:
        if len(g.members) <= 5:
            met |= {frozenset(p) for p in itertools.combinations(g.members, 2)} & cross_pairs
    cross = 15 * (len(met) / len(cross_pairs) if cross_pairs else 0)

    total = consensus + inclusion + airtime + cross
    return Score(total=round(total, 1), consensus=round(consensus, 1), inclusion=round(inclusion, 1),
                 airtime=round(airtime, 1), cross_faction=round(cross, 1),
                 detail=dict(spread_before=round(s0, 2), spread_after=round(s1, 2),
                             cross_agreements=sorted(cross_agreements), min_heard=min(heard) if heard else 0,
                             least_heard=[r.id for r in ratings if r.felt_heard == min(heard)] if heard else [],
                             words=words, cross_pairs_met=len(met), cross_pairs_total=len(cross_pairs)))


Emit = Callable[[str, dict], Awaitable[None]]


async def simulate(personas: list[Persona], plan: Plan, emit: Emit | None = None) -> SimResult:
    by_id = {p.id: p for p in personas}
    stances = {p.id: {k: float(p.stances.get(k, 0)) for k in ISSUES} for p in personas}
    initial = {k: dict(v) for k, v in stances.items()}
    notes: dict[str, list[str]] = defaultdict(list)
    groups: list[GroupResult] = []
    for bi, block in enumerate(plan.blocks):
        tasks = [_run_group(bi, gi, block, [by_id[x] for x in grp if x in by_id], stances, notes, len(plan.blocks))
                 for gi, grp in enumerate(block.groups) if grp]
        results = await asyncio.gather(*tasks)
        for g in results:
            for pid, upd in g.stance_updates.items():
                stances[pid].update(_clamp_moves(block.format, stances[pid], upd))
            for pid in g.members:
                others = [o for o in g.members if o != pid]
                agreed = [a.text for a in g.agreements if pid in a.parties]
                notes[pid].append(f"B{bi + 1} {block.format} w/ {', '.join(others[:4])}"
                                  + (f"; agreed: {agreed[0]}" if agreed else ""))
            groups.append(g)
        if emit:
            await emit("block", {"block": bi, "groups": [g.model_dump() for g in results],
                                 "stances": {k: dict(v) for k, v in stances.items()}})
    ratings = await judge(personas, groups)
    sc = score(personas, plan, groups, initial, stances, ratings)
    return SimResult(plan=plan, groups=groups, initial_stances=initial, final_stances=stances, ratings=ratings,
                     score=sc)
