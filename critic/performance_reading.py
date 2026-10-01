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


class PassageDifference(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    number: int = Field(ge=1, le=20)
    durations: list[float] = Field(min_length=2, max_length=2)
    mean_drives: list[float] = Field(min_length=2, max_length=2)
    direct_rate_difference: float
    seed_differences: list[float] = Field(min_length=2)
    boundary_direction_consistent: bool


class ComparisonSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    durations: list[float] = Field(min_length=2, max_length=2)
    seeds: list[int] = Field(min_length=2)
    differences: list[PopulationDifference]
    passages: list[PassageDifference] = Field(default_factory=list, max_length=20)


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
    passage_text = ""
    if summary.passages:
        strongest = max(summary.passages, key=lambda p: abs(p.direct_rate_difference))
        if abs(strongest.direct_rate_difference) > 1e-12:
            direction = "higher" if strongest.direct_rate_difference > 0 else "lower"
            consistency = (
                "The direction remains the same across every tested seed and boundary shift."
                if strongest.boundary_direction_consistent
                else "Its direction is not consistent across every seed and boundary shift."
            )
            passage_text = (
                f" Among the supplied corresponding passages, passage {strongest.number} has the "
                f"largest average direct-recipient contrast: B is {direction} by "
                f"{abs(strongest.direct_rate_difference):.3f} spikes/second/neuron. {consistency} "
                "This passage was selected after measurement; timing annotations and input differences "
                "still limit the inference."
            )
    return (
        f"{opening} {timing}{passage_text} These are changes in a simulated capacity to be affected by sound; "
        "they do not identify an emotion or an experienced meaning. Different durations, pauses "
        "and injected drive remain part of the explanation."
    )
