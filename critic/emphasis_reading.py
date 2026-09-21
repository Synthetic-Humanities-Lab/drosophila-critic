"""Response-only interpretation of declared local windows."""

from pydantic import BaseModel, ConfigDict


class Window(BaseModel):
    model_config = ConfigDict(extra="forbid")
    start: float
    end: float
    mean: float
    criterion: bool


class Summary(BaseModel):
    model_config = ConfigDict(extra="forbid")
    windows: list[Window]
    descending_criterion: bool
    whole_mean: float
    off_target_mean: float


def interpret(s: Summary):
    met = [w for w in s.windows if w.criterion]
    response = (
        (
            "Local downstream differences meet the declared criterion at "
            + ", ".join(f"{w.start:.2f}–{w.end:.2f} s" for w in met)
            + "."
        )
        if met
        else "Neither declared local window meets the downstream criterion in this ensemble."
    )
    reading = (
        "The shift in delivery becomes a difference in where the modeled encounter gathers force. Here force names a local change in neural recruitment, without assigning pleasure, fear or preference."
        if met
        else "This restrained change in delivery does not yield a reliably distinguished local encounter at the declared sensitivity. The interpretation retains that limit rather than converting an audible difference into an assumed affect."
    )
    if met:
        reading += " " + " ".join(
            f"At {w.start:.2f}–{w.end:.2f} seconds, recruitment is relatively {'higher' if w.mean > 0 else 'lower'} in the first rendition of this comparison."
            for w in met
        )
    return dict(
        response=response,
        reading=reading,
        functional=(
            "A descending contrast meets the criterion; no action is calibrated from these rates."
            if s.descending_criterion
            else "No descending contrast meets the criterion in these windows; no differentiated bodily action is established."
        ),
    )
