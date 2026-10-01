"""Short public interpretation; receives only the validated numeric response schema."""

import argparse
import hashlib
import json
from pathlib import Path

from .performance_reading import ComparisonSummary
from .pipeline import save_json


def interpret(summary: ComparisonSummary):
    auditory = next(
        x for x in summary.differences if x.population == "direct JON postsynaptic partners"
    )
    if auditory.temporal_separation_rms < 1e-12 and all(
        abs(v) < 1e-12 for v in auditory.seed_differences
    ):
        return "These deliveries leave the same measured downstream trace. This apparatus offers no basis for a different reading of their effects."
    timing = auditory.temporal_separation_rms > auditory.temporal_variability_rms
    text = (
        "The two deliveries disturb this receiver at different moments. "
        if timing
        else "These deliveries leave different traces, but their temporal distinction is uncertain across repeated runs. "
    )
    stable = [p for p in summary.passages if p.boundary_direction_consistent]
    if stable:
        numbers = ", ".join(str(p.number) for p in stable)
        text += f"In passages {numbers}, the downstream difference keeps its direction across the tested repetitions and timing shifts. "
    text += (
        "Read as an encounter, delivery changes the pattern of disturbance that the poem leaves behind. "
        "This is our interpretation of a simulated response, not a report of the fly’s feelings."
    )
    return text


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("result", type=Path)
    args = parser.parse_args()
    result = json.loads(args.result.read_text())
    summary = ComparisonSummary.model_validate(result["reading"]["input_summary"])
    save_json(
        args.result.with_name("presentation-reading.json"),
        {
            "provider": "response-only-encounter-template-v1",
            "input_summary": summary.model_dump(),
            "text": interpret(summary),
            "source_result_sha256": hashlib.sha256(args.result.read_bytes()).hexdigest(),
            "implementation_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        },
    )


if __name__ == "__main__":
    main()
