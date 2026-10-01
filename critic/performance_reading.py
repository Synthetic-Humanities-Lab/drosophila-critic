"""A text-blind interpretation boundary for paired performance responses."""

from pydantic import BaseModel, ConfigDict, Field


class PopulationDifference(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    population: str
    mean_rate_difference: float
    seed_differences: list[float] = Field(min_length=2)
    persistence_difference: float
    temporal_separation_rms: float
    temporal_variability_rms: float


class ComparisonSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    durations: list[float] = Field(min_length=2, max_length=2)
    seeds: list[int] = Field(min_length=2)
    differences: list[PopulationDifference]


def interpret_comparison(summary: ComparisonSummary) -> str:
    primary = next(
        row for row in summary.differences if row.population == "direct JON postsynaptic partners"
    )
    values = primary.seed_differences
    if all(abs(v) < 1e-12 for v in values) and primary.temporal_separation_rms < 1e-12:
        return (
            "The two deliveries leave the same measured downstream trace in this comparison. "
            "This receiver supplies no basis for distinguishing their effects here."
        )
    consistent = all(v > 1e-12 for v in values) or all(v < -1e-12 for v in values)
    if consistent:
        direction = "higher" if primary.mean_rate_difference > 0 else "lower"
        opening = (
            f"Delivery B leaves {direction} mean activity than A in the direct auditory "
            "recipient population after matched silence is subtracted, in every tested seed."
        )
    else:
        opening = (
            "The mean downstream difference changes direction or reaches zero across seeds. "
            "These runs do not establish a consistent increase or decrease for delivery B."
        )
    if primary.temporal_separation_rms > primary.temporal_variability_rms:
        timing = (
            "The average temporal separation exceeds the across-seed spread of the paired "
            "difference on their shared elapsed-time interval. The distinction is in when "
            "the apparatus is perturbed, as well as any change in its average activity."
        )
    else:
        timing = (
            "The separation of the average timelines does not exceed their across-seed spread "
            "on the shared elapsed-time interval. A stable temporal distinction remains uncertain."
        )
    return (
        f"{opening} {timing} These are changes in a simulated capacity to be affected by sound; "
        "they do not identify an emotion or an experienced meaning. Different durations, pauses "
        "and injected drive remain part of the explanation."
    )
