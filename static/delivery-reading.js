// This interpreter accepts paired response statistics only, never a poem or waveform.
export function describeContrast(stats, seeds) {
  if (stats.zero === seeds)
    return 'At this measurement scale, the receiver does not distinguish the comparison from the reference. Check the temporal evidence and exact controls before interpreting that as equivalence.';
  const consistent =
    Math.max(stats.positive, stats.negative) === seeds &&
    Math.abs(stats.mean) > stats.sd;
  return consistent
    ? `Across the recorded seeds, this delivery produces a consistently ${stats.mean > 0 ? 'larger' : 'smaller'} average change in the selected population. The distinction belongs to this acoustic input and this model. It does not identify a feeling or establish that the delivery is preferred.`
    : 'The selected population does not support a stable average-rate separation under the bench’s descriptive rule. Temporal differences may still be present; consult the paired trace before drawing a conclusion about delivery.';
}
