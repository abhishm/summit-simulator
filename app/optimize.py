"""Baseline plan + Argon critique/revise loop."""
from typing import Awaitable, Callable

from pydantic import BaseModel, Field

from .gemini import ARGON, structured_with_id
from .models import ISSUES, Block, Persona, Plan, SimResult
from .simulate import simulate
from .visual import for_prompt, visual_round

Emit = Callable[[str, dict], Awaitable[None]]
TOPICS = list(ISSUES)
PROMPT_WORDS = 60  # a facilitator's brief, not a pre-written treaty


def baseline(personas: list[Persona], n_blocks: int = 5) -> Plan:
    """What organizers typically do: keynote-style plenaries plus breakouts grouped by faction."""
    ids = [p.id for p in personas]
    by_faction: dict[str, list[str]] = {}
    for p in personas:
        by_faction.setdefault(p.faction, []).append(p.id)
    # Merge factions into at most 3 rooms (regulator+government, industry, academia+civil society).
    rooms = [[], [], []]
    for f, members in by_faction.items():
        rooms[{"regulator": 0, "government": 0, "industry": 1}.get(f, 2)] += members
    rooms = [r for r in rooms if r]
    seq = [
        Block(title="Opening statements", format="plenary", topic="opening",
              prompt="Each delegation states its priorities for AI safety governance.", groups=[ids]),
        Block(title="Regulation track breakouts", format="breakouts", topic="regulation",
              prompt="Discuss the right model for AI regulation.", groups=rooms),
        Block(title="Open models debate", format="plenary", topic="open_weights",
              prompt="Debate the release of open-weight frontier models.", groups=[ids]),
        Block(title="Evaluations breakouts", format="breakouts", topic="evals_liability",
              prompt="Discuss pre-deployment evaluations and liability.", groups=rooms),
        Block(title="Closing plenary", format="plenary", topic="synthesis",
              prompt="Summarize outcomes and next steps.", groups=[ids]),
    ]
    if n_blocks <= 3:
        seq = [seq[0], seq[1], seq[4]]
    return Plan(name="Baseline (typical summit)", rationale="Plenary speeches + breakouts grouped by faction.",
                blocks=seq[:n_blocks])


def repair(plan: Plan, personas: list[Persona]) -> tuple[Plan, list[str]]:
    """Ensure every guest appears exactly once per block, with sensible group sizes."""
    ids = [p.id for p in personas]
    fixes = []
    if plan.blocks and plan.blocks[-1].format != "plenary":
        plan.blocks[-1].format, plan.blocks[-1].topic = "plenary", "synthesis"
        fixes.append("last block forced to a closing plenary (public commitments happen in plenary)")
    for bi, b in enumerate(plan.blocks):
        words = b.prompt.split()
        if len(words) > PROMPT_WORDS:
            b.prompt = " ".join(words[:PROMPT_WORDS]) + " …"
            fixes.append(f"block {bi + 1}: facilitation prompt cut to {PROMPT_WORDS} words (was {len(words)})")
        seen: set[str] = set()
        groups = []
        for g in b.groups:
            g2 = [x for x in g if x in ids and x not in seen]
            seen |= set(g2)
            if g2:
                groups.append(g2)
        missing = [x for x in ids if x not in seen]
        if b.format == "plenary":
            groups = [ids]
        else:
            if not groups:
                groups = [[]]
            for x in missing:
                min(groups, key=len).append(x)
            if missing:
                fixes.append(f"block {bi + 1}: placed missing guests {missing}")
            if b.format == "breakouts" and len(groups) > 4:
                fixes.append(f"block {bi + 1}: merged breakouts down to 4 rooms")
                while len(groups) > 4:
                    a = groups.pop()
                    min(groups, key=len).extend(a)
            for g in [g for g in groups if len(g) == 1]:
                groups.remove(g)
                min(groups, key=len).extend(g)
                fixes.append(f"block {bi + 1}: merged a solo guest")
        b.groups = [g for g in groups if g]
    return plan, fixes


class Revision(BaseModel):
    critique: str = Field(description="Diagnosis of what went wrong, citing specific guests, blocks and score terms")
    changes: list[str] = Field(description="Concrete changes made to the plan and why")
    plan: Plan


def _summarize(res: SimResult, personas: list[Persona]) -> str:
    s = res.score
    lines = [f"SCORE {s.total}/100 = consensus {s.consensus}/40 + inclusion {s.inclusion}/30 + airtime "
             f"{s.airtime}/15 + cross_faction {s.cross_faction}/15",
             f"detail: {s.detail}", "", "felt_heard ratings:"]
    lines += [f"- {r.id}: {r.felt_heard} ({r.reason})" for r in sorted(res.ratings, key=lambda r: r.felt_heard)]
    lines += ["", "stance changes (initial -> final):"]
    for pid in res.final_stances:
        moved = {k: f"{res.initial_stances[pid][k]:+.1f}->{v:+.1f}" for k, v in res.final_stances[pid].items()
                 if abs(v - res.initial_stances[pid][k]) >= 0.25}
        if moved:
            lines.append(f"- {pid}: {moved}")
    lines += ["", "transcripts (condensed):"]
    for g in res.groups:
        lines.append(f"## B{g.block + 1} {g.room}: {', '.join(g.members)}")
        lines += [f"  {t.speaker}: {t.text[:220]}" for t in g.transcript[:14]]
        lines += [f"  [AGREEMENT] {a.text} -- {', '.join(a.parties)}" for a in g.agreements]
    return "\n".join(lines)


def _brief(personas: list[Persona]) -> str:
    return "\n".join(f"- {p.id} | {p.title} | faction={p.faction} | power={p.power} | stances={p.stances} | "
                     f"red lines: {'; '.join(p.red_lines[:2])} | would trade: {'; '.join(p.tradeoffs[:2])}"
                     for p in personas)


async def revise(personas: list[Persona], res: SimResult, n_blocks: int, thinking: str,
                 prev_id: str | None, visual: dict | None = None) -> tuple[Revision, str]:
    vis = "" if not visual else f"""

VISUAL CRITIC: an adversarial reviewer watched screenshots of the 3D venue render of every block of this plan
and reported:
{for_prompt(visual)}
Treat these as hypotheses: fix the ones the simulation results above confirm, and say which you addressed."""
    axes = "\n".join(f"- {k}: -5 = {lo}; +5 = {hi}" for k, (lo, hi) in ISSUES.items())
    prompt = f"""You are the lead facilitator-architect for a 1-day AI-safety summit. Your goal: maximize the
summit score by redesigning the agenda. A simulator plays the guests, and an independent judge rates how heard
each one was.

Scoring (0-100):
- consensus (40): reduction in stance spread across guests on the issues (a 40% reduction earns full marks),
  plus explicit agreements that involve 3+ parties from 3+ factions
- inclusion (30): the MINIMUM felt_heard rating across all guests (one excluded guest sinks it)
- airtime (15): 1 - Gini of words spoken per guest
- cross_faction (15): share of cross-faction guest pairs who met in a group of 5 or fewer

Simulator realism: big plenaries are dominated by high-power guests and barely move positions. Small, mixed groups
with concrete, tradeoff-oriented prompts move positions. Same-faction groups only reinforce. Facilitation prompts
matter: structured turn-taking and explicit tradeoff questions help.

Constraints: exactly {n_blocks} blocks. The LAST block must be a closing plenary (topic "synthesis") where
commitments are made publicly. The judge weighs it heavily, so design its facilitation carefully. format is one of plenary | breakouts (2-4 rooms, 2-5 people each) |
pairs (groups of 2, one trio allowed). Every guest appears exactly once per block. topic is one of
{TOPICS + ['opening', 'synthesis']}. Use only these guest ids.

Issue axes:
{axes}

Guests:
{_brief(personas)}

CURRENT PLAN:
{res.plan.model_dump_json(indent=1)}

RESULT OF SIMULATING IT:
{_summarize(res, personas)}{vis}

Diagnose the specific failures: which guests were excluded, which stances didn't move, which factions never met.
Then return a revised plan that fixes them with real facilitation design (groupings, sequencing, formats, chairs,
tradeoff questions) that a human organizer could actually run. Facilitation prompts must be at most
{PROMPT_WORDS} words: a facilitator's brief, not a pre-written agreement. Longer prompts are truncated. Don't
game the simulator: telling guests to converge, state compromise positions or endorse a pre-drafted package
has no effect. The simulated delegates contest drafts according to their red lines. Keep what worked. Name the
plan briefly."""
    rev, iid = await structured_with_id(ARGON, prompt, Revision, thinking=thinking, previous_interaction_id=prev_id)
    return rev, iid


async def optimize(personas: list[Persona], rounds: int = 4, n_blocks: int = 5, thinking: str = "high",
                   emit: Emit | None = None, start: Plan | None = None, visual: bool = False,
                   run_id: str = "run", visual_thinking: str = "medium") -> dict:
    """visual=True: before each revision, screenshot every block of the round and add Argon's visual critique
    (stored as history[r]["visual"], emitted as a "visual" event) to the revise() prompt."""
    async def e(kind, data):
        if emit:
            await emit(kind, data)

    plan = start or baseline(personas, n_blocks)
    await e("round_start", {"round": 0, "plan": plan.model_dump(), "critique": None, "changes": []})
    res = await simulate(personas, plan, emit=lambda k, d: e(k, {**d, "round": 0}))
    history = [{"round": 0, "plan": plan.model_dump(), "result": res.model_dump(), "critique": None, "changes": []}]
    await e("round_done", {"round": 0, "score": res.score.model_dump(),
                           "ratings": [r.model_dump() for r in res.ratings]})
    best, prev_id = 0, None
    for rnd in range(1, rounds + 1):
        vis = None
        if visual:
            r0 = rnd - 1
            await e("visual", {"round": r0, "pending": True})
            try:
                pv = (history[-2].get("visual") or {}).get("flaws") if len(history) > 1 else None
                vis = await visual_round(personas, res.plan, res.groups, res.ratings, run_id, r0, visual_thinking, pv)
            except Exception as ex:  # the visual check is advisory; never sink the run
                vis_err = {"round": r0, "error": f"{type(ex).__name__}: {ex}"[:300]}
                history[-1]["visual"] = vis_err
                await e("visual", vis_err)
            else:
                history[-1]["visual"] = vis
                await e("visual", vis)
        await e("thinking", {"round": rnd})
        rev, prev_id = await revise(personas, res, n_blocks, thinking, prev_id, vis)
        plan, fixes = repair(rev.plan, personas)
        await e("round_start", {"round": rnd, "plan": plan.model_dump(), "critique": rev.critique,
                                "changes": rev.changes + fixes})
        res = await simulate(personas, plan, emit=lambda k, d, r=rnd: e(k, {**d, "round": r}))
        history.append({"round": rnd, "plan": plan.model_dump(), "result": res.model_dump(),
                        "critique": rev.critique, "changes": rev.changes + fixes})
        await e("round_done", {"round": rnd, "score": res.score.model_dump(),
                               "ratings": [r.model_dump() for r in res.ratings]})
        if res.score.total > history[best]["result"]["score"]["total"]:
            best = rnd
        elif rnd >= 2 and rnd - best >= 2:
            break  # two rounds without improvement
    if visual:  # close the loop: verify the final plan's render against the last round's flaws
        r0 = history[-1]["round"]
        await e("visual", {"round": r0, "pending": True})
        try:
            pv = (history[-2].get("visual") or {}).get("flaws") if len(history) > 1 else None
            vis = await visual_round(personas, res.plan, res.groups, res.ratings, run_id, r0, visual_thinking, pv)
        except Exception as ex:
            vis = {"round": r0, "error": f"{type(ex).__name__}: {ex}"[:300]}
        history[-1]["visual"] = vis
        await e("visual", vis)
    return {"personas": [p.model_dump() for p in personas], "history": history, "best": best}
