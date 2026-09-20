"""Response-only interpretation with an enforced, text-free input schema."""

from pydantic import BaseModel, ConfigDict


class Episode(BaseModel):
    model_config = ConfigDict(extra="forbid")
    start: float
    end: float
    mean: float
    agreeing_seeds: int


class AffectInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    seeds: int
    temporal_criterion_met: bool
    descending_criterion_met: bool
    mean_rate_difference: float
    tail_mean_difference: float
    episodes: list[Episode]


def interpret(summary: AffectInput):
    if summary.temporal_criterion_met:
        opening = "The difference between these auditory inputs takes a repeatable temporal form in the modeled downstream response."
        affect = "Through an affect-theory lens, the encounter is articulated in time: the disturbance has a repeatable course rather than only a total magnitude. The apparatus makes these changing relations available to interpretation, while leaving subjective experience inaccessible."
    else:
        opening = "The downstream temporal difference does not meet the declared repeatability criterion in this ensemble."
        affect = "Through an affect-theory lens, this encounter remains underdetermined by the instrument. A measured disturbance does not yet warrant a coherent account of how differently the receiver was moved."
    if summary.episodes:
        peak = max(summary.episodes, key=lambda e: abs(e.mean))
        opening += f" Among the selected half-second episodes, the largest average separation falls at {peak.start:.1f}–{peak.end:.1f} seconds, with {peak.agreeing_seeds}/{summary.seeds} seeds in the same direction."
        if summary.temporal_criterion_met:
            direction = "higher" if peak.mean > 0 else "lower" if peak.mean < 0 else "equal"
            affect += f" At {peak.start:.1f}–{peak.end:.1f} seconds, the comparison produces a {direction} downstream firing-rate response relative to silence than the reference. This local contrast can be read as uneven recruitment over time, without assigning an emotional value."
            if any(e.mean > 0 for e in summary.episodes) and any(
                e.mean < 0 for e in summary.episodes
            ):
                affect += " The selected episodes include both higher and lower recruitment: this contrast cannot be rendered faithfully as a single increase or decrease in force."
    functional = (
        "The pooled descending population also meets the temporal criterion, but the model has no calibrated mapping from this signal to a bodily action."
        if summary.descending_criterion_met
        else "The pooled descending population does not meet the temporal criterion. These measurements do not establish a differentiated disposition toward bodily action."
    )
    return dict(
        provider="response-only-temporal-affect-v1",
        measurement=opening,
        functional_limit=functional,
        affect_reading=affect,
        qualification="The affect reading is a theoretical extrapolation from a modeled encounter, not a report of what a living fly felt. Selected episodes are exploratory, not independently validated discoveries.",
        input_summary=summary.model_dump(),
    )
