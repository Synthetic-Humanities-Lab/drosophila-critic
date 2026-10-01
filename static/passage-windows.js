// Display/analysis annotations only; never passed to the auditory encoder.
export function parsePassages(textA, textB) {
  const parse = (text) =>
    text.trim()
      ? text
          .trim()
          .split(/\n+/)
          .map((line) => {
            const values = line.split(',').map((value) => value.trim());
            if (
              values.length !== 2 ||
              values.some((value) => !/^\d+(?:\.\d+)?$/.test(value))
            ) {
              throw new Error(
                'Enter each passage as start,end in seconds, one passage per line.',
              );
            }
            const [start, end] = values.map(Number);
            if (end - start < 0.2 - 1e-9 || end > 120)
              throw new Error(
                'Passages must span at least 0.2 seconds and end within 120 seconds.',
              );
            return { start, end };
          })
      : [];
  const a = parse(textA),
    b = parse(textB);
  if (a.length !== b.length || a.length > 20)
    throw new Error(
      'Supply the same number of passages for A and B, at most twenty.',
    );
  for (const windows of [a, b])
    for (let i = 1; i < windows.length; i++) {
      if (windows[i].start < windows[i - 1].end)
        throw new Error('Passages must be ordered and nonoverlapping.');
    }
  return a.map((window, i) => ({ a: window, b: b[i] }));
}
