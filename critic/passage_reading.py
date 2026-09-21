"""Interpret only numerical passage evidence; reject extra fields."""

from pydantic import BaseModel, ConfigDict


class Passage(BaseModel):
    model_config = ConfigDict(extra="forbid")
    number: int
    difference: float
    robust: bool
    residual_robust_all: bool
    first_duration: float
    second_duration: float


class ReadingInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    passages: list[Passage]
    human_baseline_r2: list[float | None]
    descending_robust_count: int


def interpret(data: ReadingInput):
    robust = [p for p in data.passages if p.robust]
    if robust:
        reading = "The two deliveries distribute the modeled encounter differently across corresponding passages. "
        reading += " ".join(
            f"In passage {p.number}, the downstream firing rate is {'higher' if p.difference > 0 else 'lower'} in the second recording."
            for p in robust
        )
        reading += " This describes a pattern of susceptibility to sound: where a delivery exerts more or less neural disturbance per unit time, without assigning a feeling to it."
    else:
        reading = "At the scale of whole passages, this apparatus does not consistently distinguish the two deliveries under the declared boundary check. That limit belongs to the measurement; it does not establish that the encounters are identical."
    if robust and all(p.second_duration > p.first_duration for p in robust):
        reading += " The second recording also spends longer in these passages. A lower firing rate does not mean a smaller accumulated response."
    remaining = [p.number for p in data.passages if p.residual_robust_all]
    limits = (
        "Passage differences remain after all three input-only approximations at passages "
        + ", ".join(map(str, remaining))
        + ". These are unexplained by these particular approximations, not evidence of a specific experience."
        if remaining
        else "No passage contrast survives all three input-only approximations and the boundary check. Residual evidence depends on the comparator; this comparison does not isolate a contribution beyond simple amplitude following."
    )
    limits += (
        " No robust pooled descending contrast establishes a differentiated route toward action."
        if data.descending_robust_count == 0
        else "Pooled descending differences do not identify or calibrate an action."
    )
    return dict(text=reading, limits=limits)
