export function selection(search) {
  const q = new URLSearchParams(search);
  const stanza = Number(q.get('stanza'));
  return {
    reader: q.get('reader') === 'human' ? 'b' : 'a',
    stanza:
      Number.isInteger(stanza) && stanza >= 1 && stanza <= 5
        ? stanza - 1
        : null,
  };
}
export function interval(manifest, reader, stanza) {
  const p = manifest.performances[reader];
  return stanza === null ? { start: 0, end: p.duration } : p.passages[stanza];
}
export function traceIndex(timeline, time) {
  return Math.max(
    0,
    Math.min(
      timeline.mean.length - 1,
      Math.floor((time - timeline.start_seconds) / timeline.bin_seconds),
    ),
  );
}
export function signed(value, digits = 3) {
  return `${value >= 0 ? '+' : ''}${value.toFixed(digits)}`;
}
