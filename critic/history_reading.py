"""Interpret only the declared response contrasts, never performance content."""

from pydantic import BaseModel, ConfigDict


class GapSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")
    gap_seconds: float
    early_interaction: bool
    full_interaction: bool
    early_lingering: bool
    full_lingering: bool
    probe_after_a: bool
    probe_after_b: bool
    full_probe_after_a: bool
    full_probe_after_b: bool
    descending_interaction: bool
    early_mean: float


class HistorySummary(BaseModel):
    model_config = ConfigDict(extra="forbid")
    seeds: int
    gaps: list[GapSummary]


def interpret(summary: HistorySummary):
    early = [g.gap_seconds for g in summary.gaps if g.early_interaction]
    full = [g.gap_seconds for g in summary.gaps if g.full_interaction]
    residual = [g.gap_seconds for g in summary.gaps if g.early_lingering or g.full_lingering]
    if early:
        response = f"The primary test detects a changed probe increment after gaps of {', '.join(map(str, early))} seconds."
        reading = "The shared passage reaches a receiver already differently affected. Its measured recruitment depends on what preceded it, beyond the activity that would have continued in its absence. Within this apparatus, the encounter has a history that conditions renewed contact."
    elif full:
        response = (
            "The primary half-second test does not meet the criterion. The secondary two-second test does after gaps of "
            + ", ".join(map(str, full))
            + " seconds."
        )
        reading = "The longer observation suggests that preceding contact can condition the shared passage, but the declared early test remains unresolved. This is a qualified basis for reading the encounter as history-dependent."
    else:
        response = "Neither the primary half-second nor the secondary two-second interaction meets the declared criterion at any tested gap."
        if residual:
            reading = "The earlier encounter leaves a distinguishable continuation, but this instrument does not resolve a changed reception of the shared passage beyond that continuation. An aftereffect and a transformation of subsequent receptivity remain distinct possibilities."
        else:
            reading = "The apparatus does not resolve a reliable conditioning of this passage by these preceding encounters. Its earlier differences should not be carried into an account of changed receptivity without further evidence. This limit belongs to the present model, stimulus and measurement, rather than to every possible encounter."
    if not all(g.probe_after_a and g.probe_after_b for g in summary.gaps):
        response += " Some first-half-second passage-response checks also fall below the criterion, limiting what this early null can tell us."
    if all(g.full_probe_after_a and g.full_probe_after_b for g in summary.gaps):
        response += " All full two-second probe-response checks meet the criterion: the passage itself registers after both histories at every gap."
    functional = (
        "A descending interaction meets the primary criterion in at least one condition. This is an output-related neural difference, without a calibrated mapping to an action."
        if any(g.descending_interaction for g in summary.gaps)
        else "No pooled descending interaction meets the primary criterion. These measurements do not identify a changed bodily disposition."
    )
    return dict(
        provider="response-only-history-v1",
        response=response,
        functional=functional,
        reading=reading,
        input_summary=summary.model_dump(),
        limitation="The criterion is descriptive. Failure to meet it is not equivalence. A detected dependence could arise from membrane/spike dynamics or recurrence; it does not establish learning, recollection or a living fly’s experience.",
    )
