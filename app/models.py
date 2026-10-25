"""Core data models for the summit simulator."""
from typing import Literal

from pydantic import BaseModel, Field

# Each issue is an axis from -5 to +5. The labels describe what each end means.
ISSUES: dict[str, tuple[str, str]] = {
    "regulation": ("voluntary commitments only", "binding, enforceable regulation"),
    "open_weights": ("restrict open-weight release of frontier models", "open-weight release by default"),
    "compute_controls": ("no compute/export controls, national autonomy", "strong compute controls + international coordination"),
    "evals_liability": ("no mandatory evals or developer liability", "mandatory pre-deployment evals + developer liability"),
    "benefit_sharing": ("market decides who benefits", "mandated benefit sharing + labor protections"),
}

FACTIONS = ["regulator", "government", "industry", "academia", "civil_society"]

Format = Literal["plenary", "breakouts", "pairs"]


class Persona(BaseModel):
    id: str
    title: str = Field(description="Role title, e.g. 'EU AI Office regulator'")
    faction: str
    summary: str = Field(description="2-3 sentence summary of the role's priorities")
    stances: dict[str, float] = Field(description="issue -> position in [-5, 5]")
    red_lines: list[str]
    tradeoffs: list[str] = Field(description="What they'd concede in exchange for what")
    engagement: str = Field(description="How the role typically engages in multistakeholder meetings")
    power: Literal["high", "medium", "low"] = Field(description="Typical institutional leverage in the room")
    sources: list[str] = Field(default_factory=list)


class Block(BaseModel):
    title: str
    format: Format
    topic: str = Field(description="One of the ISSUES keys, or 'opening' / 'synthesis'")
    prompt: str = Field(description="Facilitation prompt given to the group(s)")
    groups: list[list[str]] = Field(description="Persona ids per group; plenary has exactly one group")


class Plan(BaseModel):
    name: str
    rationale: str = ""
    blocks: list[Block]


class Turn(BaseModel):
    speaker: str
    text: str


class Agreement(BaseModel):
    text: str
    parties: list[str]
    plain: str = Field(default="", description="The same agreement in one short sentence (under 25 words) of everyday words a non-expert understands")


class GroupResult(BaseModel):
    block: int
    group: int
    room: str
    members: list[str]
    transcript: list[Turn]
    stance_updates: dict[str, dict[str, float]]
    agreements: list[Agreement]


class GuestRating(BaseModel):
    id: str
    felt_heard: float = Field(description="0-10")
    reason: str


class Score(BaseModel):
    total: float
    consensus: float
    inclusion: float
    airtime: float
    cross_faction: float
    detail: dict


class SimResult(BaseModel):
    plan: Plan
    groups: list[GroupResult]
    initial_stances: dict[str, dict[str, float]]
    final_stances: dict[str, dict[str, float]]
    ratings: list[GuestRating]
    score: Score
