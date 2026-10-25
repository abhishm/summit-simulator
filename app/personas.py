"""Personas: seed placeholders + extraction from Deep Research reports (data/personas/<id>.md -> <id>.json)."""
import asyncio
import json
from pathlib import Path

from pydantic import BaseModel, Field

from .gemini import FLASH, aclient, structured
from .models import ISSUES, Persona

DIR = Path(__file__).resolve().parent.parent / "data" / "personas"

# Placeholders used until Deep Research briefs are extracted. Values are rough priors and get replaced by research.
SEED: list[dict] = [
    dict(id="eu_regulator", title="EU AI Office regulator", faction="regulator", power="high",
         stances=dict(regulation=4.5, open_weights=-1, compute_controls=2, evals_liability=4, benefit_sharing=2)),
    dict(id="us_natsec", title="US national-security advisor (AI)", faction="government", power="high",
         stances=dict(regulation=0.5, open_weights=-3.5, compute_controls=4.5, evals_liability=1.5, benefit_sharing=-1)),
    dict(id="uk_aisi", title="UK AI Security Institute director", faction="government", power="medium",
         stances=dict(regulation=1, open_weights=-1, compute_controls=2, evals_liability=4.5, benefit_sharing=0)),
    dict(id="china_policy", title="Chinese AI governance policy expert", faction="government", power="medium",
         stances=dict(regulation=3, open_weights=2.5, compute_controls=-4, evals_liability=2, benefit_sharing=2)),
    dict(id="frontier_lab_ceo", title="Frontier-lab CEO", faction="industry", power="high",
         stances=dict(regulation=-1, open_weights=-3, compute_controls=2.5, evals_liability=0, benefit_sharing=-1.5)),
    dict(id="open_weights_lead", title="Open-weights model company head", faction="industry", power="medium",
         stances=dict(regulation=-3, open_weights=5, compute_controls=-2.5, evals_liability=-2.5, benefit_sharing=0)),
    dict(id="big_tech_policy", title="Big Tech VP of public policy", faction="industry", power="high",
         stances=dict(regulation=-2, open_weights=1, compute_controls=0, evals_liability=-2, benefit_sharing=-3)),
    dict(id="safety_researcher", title="Academic AI safety researcher", faction="academia", power="low",
         stances=dict(regulation=3, open_weights=-2, compute_controls=3, evals_liability=4.5, benefit_sharing=1)),
    dict(id="global_south_cso", title="Global South digital-rights leader", faction="civil_society", power="low",
         stances=dict(regulation=3, open_weights=3, compute_controls=-3, evals_liability=2.5, benefit_sharing=5)),
    dict(id="labor_advocate", title="Labor union AI lead", faction="civil_society", power="low",
         stances=dict(regulation=4, open_weights=0, compute_controls=0, evals_liability=3, benefit_sharing=5)),
]


def _seed(d: dict) -> Persona:
    return Persona(summary=f"Placeholder for {d['title']} (awaiting Deep Research).", red_lines=[], tradeoffs=[],
                   engagement="", **d)


class _IssueStance(BaseModel):
    issue: str = Field(description=f"One of: {', '.join(ISSUES)}")
    position: float = Field(description="-5..5")
    evidence: str


class _Extracted(BaseModel):
    title: str
    summary: str
    stances: list[_IssueStance]
    red_lines: list[str]
    tradeoffs: list[str]
    engagement: str
    power: str = Field(description="high | medium | low")
    sources: list[str] = Field(description="Up to 6 most important source URLs or titles cited in the report")


def _axes() -> str:
    return "\n".join(f"- {k}: -5 = {lo}; +5 = {hi}" for k, (lo, hi) in ISSUES.items())


async def extract(pid: str, faction: str, report: str) -> Persona:
    prompt = (f"Convert this research brief about a stakeholder ROLE into a structured persona for a meeting "
              f"simulation. Use only positions grounded in the brief. Do not infer personality traits.\n\n"
              f"Place the role on each issue axis:\n{_axes()}\n\nBRIEF:\n{report}")
    x = await structured(FLASH, prompt, _Extracted)
    stances = {s.issue: max(-5, min(5, s.position)) for s in x.stances if s.issue in ISSUES}
    power = x.power if x.power in ("high", "medium", "low") else "medium"
    return Persona(id=pid, faction=faction, title=x.title, summary=x.summary, stances=stances,
                   red_lines=x.red_lines, tradeoffs=x.tradeoffs, engagement=x.engagement, power=power,
                   sources=x.sources)


async def extract_all() -> list[str]:
    """Extract any completed reports that don't have a JSON yet."""
    jobs = json.loads((DIR / "jobs.json").read_text()) if (DIR / "jobs.json").exists() else {}
    todo = [(pid, j) for pid, j in jobs.items() if (DIR / f"{pid}.md").exists() and not (DIR / f"{pid}.json").exists()]

    async def one(pid, job):
        p = await extract(pid, job["faction"], (DIR / f"{pid}.md").read_text())
        (DIR / f"{pid}.json").write_text(p.model_dump_json(indent=2))
        return pid

    return list(await asyncio.gather(*(one(pid, j) for pid, j in todo)))


def load() -> list[Persona]:
    """Researched persona if available, else the seed placeholder."""
    out = []
    for d in SEED:
        f = DIR / f"{d['id']}.json"
        out.append(Persona.model_validate_json(f.read_text()) if f.exists() else _seed(d))
    for f in sorted(DIR.glob("*.json")):
        if f.stem != "jobs" and f.stem not in {d["id"] for d in SEED}:
            out.append(Persona.model_validate_json(f.read_text()))
    return out


if __name__ == "__main__":
    print("extracted:", asyncio.run(extract_all()))
    for p in load():
        print(f"{p.id:20} {p.faction:14} {'researched' if p.sources else 'seed':10} {p.stances}")
