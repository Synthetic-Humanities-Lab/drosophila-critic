"""Acoustic delivery diagnostics and paired statistics; no semantic inputs."""

import hashlib
import wave

import numpy as np


def read_wav(path):
    with wave.open(str(path), "rb") as f:
        if f.getnchannels() != 1 or f.getsampwidth() != 2:
            raise ValueError("Expected mono PCM16 source")
        return np.frombuffer(f.readframes(f.getnframes()), "<i2").astype(
            np.float64
        ) / 32768, f.getframerate()


def rms(x):
    return float(np.sqrt(np.mean(np.asarray(x, dtype=float) ** 2)))


def equalize(waves, ceiling=0.95):
    if not waves or not 0 < ceiling <= 1:
        raise ValueError("Expected nonempty waveforms and a peak ceiling in (0, 1]")
    for x in waves.values():
        if np.ndim(x) != 1 or not len(x) or not np.all(np.isfinite(x)) or rms(x) == 0:
            raise ValueError("Level matching requires finite non-silent mono waveforms")
    target = min(0.05, *(ceiling * rms(x) / np.max(np.abs(x)) for x in waves.values()))
    output, metadata = {}, {}
    for name, x in waves.items():
        gain = target / rms(x)
        pcm = np.rint(x * gain * 32767).astype("<i2")
        y = pcm.astype(np.float64) / 32768
        output[name] = y
        metadata[name] = dict(
            target_rms=target,
            input_rms=rms(x),
            gain=gain,
            output_rms=rms(y),
            output_peak=float(np.max(np.abs(y))),
            pcm_sha256=hashlib.sha256(pcm.tobytes()).hexdigest(),
        )
    return output, metadata


def variants(x, rate, lines):
    """Line boundaries are acoustic cut metadata, never supplied to the brain."""
    starts = [round(line["start"] * rate) for line in lines]
    ends = [round(line["end"] * rate) for line in lines]
    if starts[0] != 0:
        raise ValueError("Synthetic reference must begin at sample zero")
    stops = starts[1:] + [len(x)]
    gaps = [x[end:stop] for end, stop in zip(ends, stops)]
    if any(np.any(gap != 0) for gap in gaps):
        raise ValueError("Pause manipulation requires verified digital silence")
    gap_lengths = [len(g) for g in gaps]
    redistributed = gap_lengths.copy()
    for i in range(0, len(gaps) - 1, 2):
        redistributed[i], redistributed[i + 1] = 0, gap_lengths[i] + gap_lengths[i + 1]
    pause, pause_lines, position = [], [], 0
    for line, start, end, gap in zip(lines, starts, ends, redistributed):
        speech = x[start:end]
        pause_lines.append(
            dict(line=line["line"], start=position / rate, end=(position + len(speech)) / rate)
        )
        pause.extend([speech, np.zeros(gap)])
        position += len(speech) + gap
    emphasis = x.copy()
    for i, (start, end) in enumerate(zip(starts, ends)):
        emphasis[start:end] *= 0.5 if i % 2 == 0 else 1.5
    order, order_lines, position = [], [], 0
    for i in reversed(range(len(lines))):
        part = x[starts[i] : stops[i]]
        order.append(part)
        order_lines.append(
            dict(
                line=lines[i]["line"],
                start=position / rate,
                end=(position + ends[i] - starts[i]) / rate,
            )
        )
        position += len(part)
    return {
        "pauses": (np.concatenate(pause), pause_lines),
        "emphasis": (emphasis, lines),
        "reordered": (np.concatenate(order), order_lines),
    }


def paired_stats(values):
    x = np.asarray(values, dtype=float)
    sd = float(x.std(ddof=1)) if len(x) > 1 else 0.0
    mean = float(x.mean())
    return dict(
        values=x.tolist(),
        mean=mean,
        sd=sd,
        minimum=float(x.min()),
        maximum=float(x.max()),
        positive=int(np.sum(x > 0)),
        negative=int(np.sum(x < 0)),
        zero=int(np.sum(x == 0)),
        absolute_mean_over_sd=abs(mean) / sd if sd else None,
    )


def bin_rates(counts, sizes, dt=0.02, width=5):
    counts = np.asarray(counts, dtype=float)
    return np.array(
        [
            counts[i : i + width].mean(axis=0) / (np.asarray(sizes) * dt)
            for i in range(0, len(counts), width)
        ]
    )
