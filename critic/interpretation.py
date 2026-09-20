"""A text-blind interpretation boundary. The input schema rejects extra fields."""

from typing import Literal

from pydantic import BaseModel, ConfigDict

from .circuit_roles import ROLES


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class PopulationChange(StrictModel):
    name: str
    neurons: int
    delta_hz_per_neuron: float


class ResponseSummary(StrictModel):
    duration: float
    baseline_hz_per_neuron: float
    deviation_hz_per_neuron: float
    peak_time: float
    peak_line: int | None
    peak_delta_hz_per_neuron: float
    transition_count: int
    tail_delta_hz_per_neuron: float
    recovery_seconds: float | None
    tail_observed_seconds: float
    threshold: float
    populations: list[PopulationChange]
    evidence: Literal["single seeded simulation"] = "single seeded simulation"


def summarize_response(response: dict) -> ResponseSummary:
    """Explicit allowlist, not serialization of the application/result object."""
    g = response["global"]
    peak = next(e for e in response["events"] if e["kind"] == "peak perturbation")
    return ResponseSummary(
        duration=g["audio_window_seconds"],
        baseline_hz_per_neuron=response["baseline"]["hz_per_neuron"],
        deviation_hz_per_neuron=g["deviation_hz_per_neuron"],
        peak_time=g["peak_time"],
        peak_line=peak["line"],
        peak_delta_hz_per_neuron=g["peak_perturbation_hz_per_neuron"],
        transition_count=sum(e["kind"] == "activity transition" for e in response["events"]),
        tail_delta_hz_per_neuron=g["tail_deviation_hz_per_neuron"],
        recovery_seconds=g["recovery_seconds_after_audio_window"],
        tail_observed_seconds=g["tail_observed_seconds"],
        threshold=response["measurement_rules"]["transition_band_hz_per_neuron"],
        populations=[
            PopulationChange(**{k: p[k] for k in PopulationChange.model_fields})
            for p in response["populations"][:3]
        ],
    )


def interpret(summary: ResponseSummary) -> dict:
    """No poem argument, no network/provider call, no semantic access."""
    s = summary
    position = (
        "early"
        if s.peak_time < s.duration / 3
        else "late"
        if s.peak_time > 2 * s.duration / 3
        else "midway"
    )
    location = f"line {s.peak_line}" if s.peak_line is not None else f"{s.peak_time:.2f} seconds"
    if abs(s.peak_delta_hz_per_neuron) <= s.threshold:
        opening = "The global trajectory stays close to its baseline band. This instrument registers little separation between the voice and its own ongoing activity."
    else:
        direction = "an increase" if s.peak_delta_hz_per_neuron > 0 else "a decrease"
        opening = f"The largest departure in global activity is {direction} {position} in the sounding, at {location} ({s.peak_time:.2f} seconds). The temporal emphasis of this reading falls there."
    changed = [p for p in s.populations if abs(p.delta_hz_per_neuron) > 0.01]
    middle = ""
    if changed:
        p = changed[0]
        direction = "increases" if p.delta_hz_per_neuron > 0 else "decreases"
        middle = f" Among annotated cell types, {p.name} {direction} most in absolute mean rate per neuron ({abs(p.delta_hz_per_neuron):.2f} Hz/neuron). This names a concentration of response, not a feeling."
    if s.recovery_seconds is None:
        ending = f" No sustained return to the baseline band is observed in the {s.tail_observed_seconds:.1f}-second aftermath. The voice stops before the measured disturbance settles; closure remains unobserved."
    elif s.recovery_seconds == 0:
        ending = " After the voice, global activity is already within the baseline band for the required interval. At this scale, the ending leaves no sustained departure."
    else:
        ending = f" A sustained return to the baseline band begins {s.recovery_seconds:.2f} seconds after the audio window. The ending acquires a measurable interval of release."
    return {
        "provider": "response-only-template-v1",
        "input_summary": s.model_dump(),
        "text": opening + middle + ending,
        "status": "interpretation of measurements; not cognition or observed behavior",
    }


class CircuitMeasurement(PopulationChange):
    audio_hz_per_neuron: float
    silence_hz_per_neuron: float


class ControlledSummary(StrictModel):
    duration: float
    seed: int
    pairs: int
    poem_hz_per_neuron: float
    silence_hz_per_neuron: float
    delta_hz_per_neuron: float
    peak_delta_hz_per_neuron: float
    peak_time: float
    peak_line: int | None
    tail_delta_hz_per_neuron: float
    populations: list[PopulationChange]
    circuits: list[CircuitMeasurement] = []
    evidence: Literal["matched silence, single paired seed"] = "matched silence, single paired seed"


def summarize_control(benchmark: dict) -> ControlledSummary:
    return ControlledSummary(
        duration=benchmark["duration"],
        seed=benchmark["seed"],
        pairs=benchmark["pairs"],
        **benchmark["global"],
        circuits=[
            CircuitMeasurement(**{k: p[k] for k in CircuitMeasurement.model_fields})
            for p in benchmark["monitored_populations"]
            if p.get("available")
        ],
        populations=[
            PopulationChange(**{k: p[k] for k in PopulationChange.model_fields})
            for p in benchmark["populations"][:3]
        ],
    )


def interpret_control(summary: ControlledSummary) -> dict:
    s = summary
    if abs(s.peak_delta_hz_per_neuron) < 1e-12:
        text = "The sounding leaves the global trajectory indistinguishable from its matched silence. At this scale, the instrument supplies no departure to read."
    else:
        direction = "above" if s.delta_hz_per_neuron >= 0 else "below"
        location = f"line {s.peak_line}, " if s.peak_line else ""
        text = (
            f"Against an equally long silence, the voice shifts mean activity {direction} the control "
            f"by {abs(s.delta_hz_per_neuron):.3f} Hz per neuron. Its greatest global separation "
            f"occurs at {location}{s.peak_time:.2f} seconds. The emphasis belongs to this "
            "difference, rather than to activity the instrument would have produced anyway."
        )
        changed = [p for p in s.populations if abs(p.delta_hz_per_neuron) > 1e-12]
        if changed:
            p = changed[0]
            text += f" The largest mean cell-type difference is in {p.name} ({p.neurons} neurons, {p.delta_hz_per_neuron:+.2f} Hz per neuron)."
        text += (
            f" In the recorded aftermath, the mean difference is {s.tail_delta_hz_per_neuron:+.3f} "
            "Hz per neuron. The end can be read as an interval of separation from silence; "
            "this single paired run does not establish a stable disposition."
        )
    notes = []
    for circuit in s.circuits:
        role = ROLES.get(circuit.name)
        if role is None:
            continue
        net_spikes = round(circuit.delta_hz_per_neuron * circuit.neurons * s.duration)
        direction = (
            "more" if net_spikes > 0 else "fewer" if net_spikes < 0 else "no net difference in"
        )
        measurement = (
            f"{abs(net_spikes):,} {direction} spikes across {circuit.neurons} neurons over "
            f"{s.duration:.2f} seconds; {circuit.delta_hz_per_neuron:+.3f} Hz/neuron "
            "against matched silence."
        )
        notes.append(
            {
                "population": circuit.name,
                **role,
                "measurement": measurement,
                "net_spikes_vs_silence": net_spikes,
                "inference": "Activity increased in this circuit."
                if net_spikes > 0
                else "Activity decreased in this circuit."
                if net_spikes < 0
                else "Total activity matched silence; temporal patterns can still differ.",
            }
        )
    circuits = {c.name: c for c in s.circuits}
    auditory = circuits.get("JO-A/B input")
    downstream = circuits.get("direct JON postsynaptic partners")
    if (
        auditory
        and downstream
        and auditory.delta_hz_per_neuron > 0
        and downstream.delta_hz_per_neuron > 0
    ):
        position = (
            "opening third"
            if s.peak_time < s.duration / 3
            else "final third"
            if s.peak_time > 2 * s.duration / 3
            else "middle third"
        )
        text = (
            "The voice enters through the modeled vibration-sensing pathway and carries beyond it: "
            "both the sensory neurons and their direct postsynaptic partners fire more than in silence. "
            f"The strongest whole-network departure falls in the {position}, at {s.peak_time:.2f} seconds. "
            "As a reading, this is contact and propagation: a patterned disturbance that travels, "
            "without a demonstrated destination in action. The recorded activity gives the encounter "
            "a sensory shape; it does not establish what, if anything, the fly feels."
        )
    return {
        "provider": "response-only-functional-template-v2",
        "functional_notes": notes,
        "scope": "Circuit roles come from research; rate differences come from this model; experience is not measured.",
        "input_summary": s.model_dump(),
        "text": text,
        "status": "Interpretation of a model counterfactual, not cognition or observed behavior",
    }
