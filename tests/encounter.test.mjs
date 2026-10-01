import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
const code = await readFile(
  new URL('../static/encounter-data.js', import.meta.url),
  'utf8',
);
const { selection, interval, playbackWindow, stanzaAtTime, traceIndex } =
  await import(
    `data:text/javascript;base64,${Buffer.from(code).toString('base64')}`
  );
test('share links reject invalid stanzas and select explicit human only', () => {
  assert.deepEqual(selection('?reader=human&stanza=4'), {
    reader: 'b',
    stanza: 3,
  });
  for (const q of ['?stanza=-1', '?stanza=6', '?stanza=1.1', '?stanza=hello'])
    assert.equal(selection(q).stanza, null);
});
test('passages retain native clocks rather than normalized progress', () => {
  const m = {
    performances: {
      a: { duration: 26, passages: [{ start: 1, end: 4 }] },
      b: { duration: 45, passages: [{ start: 2, end: 8 }] },
    },
  };
  assert.deepEqual(interval(m, 'a', 0), { start: 1, end: 4 });
  assert.deepEqual(interval(m, 'b', 0), { start: 2, end: 8 });
  assert.deepEqual(interval(m, 'b', null), { start: 0, end: 45 });
});
test('timeline clamps baseline and persistence to recorded bounds', () => {
  const t = {
    start_seconds: -1,
    bin_seconds: 0.1,
    mean: Array(30).fill([0, 1]),
  };
  assert.equal(traceIndex(t, 0), 10);
  assert.equal(traceIndex(t, 100), 29);
  assert.equal(traceIndex(t, -2), 0);
});

test('selecting a stanza continues past its boundary to the actual recording end', async () => {
  const m = JSON.parse(
    await readFile(
      new URL('../experiments/encounter-v1/manifest.json', import.meta.url),
      'utf8',
    ),
  );
  assert.equal(interval(m, 'a', 0).end, 4.94);
  for (const reader of ['a', 'b']) {
    for (let stanza = 0; stanza < 5; stanza++) {
      assert.deepEqual(playbackWindow(m, reader, stanza), {
        start: m.performances[reader].passages[stanza].start,
        end: m.performances[reader].duration,
      });
    }
  }
  assert.equal(stanzaAtTime(m, 'a', 11), 2);
  assert.equal(stanzaAtTime(m, 'b', 37), 4);
  assert.equal(stanzaAtTime(m, 'a', m.performances.a.duration), 4);
});
