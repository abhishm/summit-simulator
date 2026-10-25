"""Deep Research persona briefs: `start` launches one background job per role; `collect` polls and saves reports.

Usage:
    uv run python scripts/research_personas.py start [role_id ...]
    uv run python scripts/research_personas.py collect
"""
import json
import sys
from pathlib import Path

from dotenv import load_dotenv
from google import genai

AGENT = "deep-research-preview-04-2026"
OUT = Path(__file__).resolve().parent.parent / "data" / "personas"
JOBS = OUT / "jobs.json"

ROLES = {
    "eu_regulator": ("regulator", "Senior official at the EU AI Office implementing the EU AI Act"),
    "us_natsec": ("government", "US national-security advisor focused on AI and export controls"),
    "uk_aisi": ("government", "Director at the UK AI Security Institute (frontier model evaluations)"),
    "china_policy": ("government", "Chinese AI governance policy expert (state-affiliated think tank)"),
    "frontier_lab_ceo": ("industry", "CEO of a closed frontier AI lab"),
    "open_weights_lead": ("industry", "Head of an open-weights AI model company"),
    "big_tech_policy": ("industry", "VP of public policy at a large cloud/AI platform company"),
    "safety_researcher": ("academia", "Academic AI alignment and safety researcher"),
    "global_south_cso": ("civil_society", "Civil-society leader representing Global South digital-rights groups"),
    "labor_advocate": ("civil_society", "Labor union leader focused on AI and workforce displacement"),
}

PROMPT = """Research the publicly stated positions of this stakeholder ROLE on AI safety governance: {desc}.

Ground the brief in real public sources (laws, official statements, published frameworks, op-eds, testimony,
reports) from people and institutions that hold this kind of role. Describe the ROLE's positions, not any
individual's personality or psychology.

Cover:
1. Core priorities and goals for AI safety governance.
2. Stated positions on these issues: (a) binding regulation vs voluntary commitments, (b) open-weight model
   release, (c) compute/export controls and international coordination, (d) pre-deployment evaluations and
   liability, (e) distribution of AI benefits and labor impact.
3. Red lines: what this role would never accept.
4. Tradeoffs: what they would concede in exchange for what.
5. Typical allies and points of friction with other stakeholder groups.
6. How they typically engage in multistakeholder meetings (formal statements vs. working sessions), based on
   public record.

Keep it under 1,200 words, with citations."""


def client() -> genai.Client:
    load_dotenv()
    return genai.Client()


def start(role_ids: list[str]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    jobs = json.loads(JOBS.read_text()) if JOBS.exists() else {}
    c = client()
    for rid in role_ids or ROLES:
        faction, desc = ROLES[rid]
        it = c.interactions.create(agent=AGENT, input=PROMPT.format(desc=desc), background=True)
        jobs[rid] = {"id": it.id, "faction": faction, "description": desc, "status": it.status}
        print(f"started {rid}: {it.id} ({it.status})")
    JOBS.write_text(json.dumps(jobs, indent=2))


def collect() -> None:
    jobs = json.loads(JOBS.read_text())
    c = client()
    for rid, job in jobs.items():
        if job["status"] == "completed" and (OUT / f"{rid}.md").exists():
            continue
        it = c.interactions.get(id=job["id"])
        job["status"] = it.status
        if it.status == "completed":
            (OUT / f"{rid}.md").write_text(it.output_text or "")
        elif it.status == "failed":
            job["error"] = str(getattr(it, "error", ""))
        print(f"{rid}: {it.status}")
    JOBS.write_text(json.dumps(jobs, indent=2))
    done = sum(j["status"] == "completed" for j in jobs.values())
    print(f"{done}/{len(jobs)} completed")


if __name__ == "__main__":
    cmd, *args = sys.argv[1:] or ["collect"]
    start(args) if cmd == "start" else collect()
