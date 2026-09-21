"""Response-only reading of fixed population candidates."""

from pydantic import BaseModel, ConfigDict


class Candidate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    population: str
    passage: int
    difference: float
    survives: bool


class ReadingInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    candidates: list[Candidate]


def interpret(data: ReadingInput):
    found = [c for c in data.candidates if c.survives]
    if not found:
        return "This screen does not establish a repeatable population-specific difference beyond the three amplitude approximations at the scale of corresponding stanzas. The apparatus registers differences in delivery, but these measurements do not support a more specific disposition toward action or feeling. This limit belongs to the selected populations and measurement scale, not to every possible neural response."
    details = " ".join(
        f"{c.population}, passage {c.passage}: the second recording has a {'higher' if c.difference > 0 else 'lower'} firing rate."
        for c in found
    )
    return (
        "Some differences remain localized to annotated populations after all three input-only approximations and repeat across held-out noise runs. "
        + details
        + " As an interpretation, delivery distributes disturbance unevenly across the modeled network. These residuals exceed these particular approximations; they do not establish a percept, action, emotion or uniquely connectome-dependent mechanism. The annotations here identify cells and anatomical contact, not an experience."
    )
