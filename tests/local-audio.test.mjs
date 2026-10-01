import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
const code = await readFile(
  new URL('../static/local-audio.js', import.meta.url),
  'utf8',
);
const { levelMatch, mechanicalInput, mono, summarize, localReading } =
  await import(
    `data:text/javascript;base64,${Buffer.from(code).toString('base64')}`
  );
const manifest = JSON.parse(
  await readFile(
    new URL('../static/browser-model-v1/manifest.json', import.meta.url),
    'utf8',
  ),
);
const fixture = JSON.parse(
  await readFile(
    new URL('./receiver-browser-fixture.json', import.meta.url),
    'utf8',
  ),
);
test('browser displacement receiver matches Python on tone, offset and ringdown', () => {
  const x = Float64Array.from({ length: 48000 }, (_, i) =>
    i < 24000 ? 0.07 * Math.sin((2 * Math.PI * 200 * i) / 48000) : 0,
  );
  const drive = mechanicalInput(x, manifest.receiver);
  assert.equal(drive.length, fixture.drive.length);
  for (let i = 0; i < drive.length; i++)
    assert.ok(
      Math.abs(drive[i] - fixture.drive[i]) < 1e-10,
      `${i}: ${drive[i]} vs ${fixture.drive[i]}`,
    );
  assert.deepEqual(
    mechanicalInput(new Float64Array(48000), manifest.receiver),
    Array(55).fill(0),
  );
});
test('paired normalization preserves zeros and uses common achievable RMS without clipping', () => {
  const a = Float64Array.from([0, 0.1, -0.1, 0]),
    b = Float64Array.from([0, 0.8, -0.8, 0]);
  const m = levelMatch(a, b);
  assert.deepEqual(m.a, m.b);
  assert.equal(m.a[0], 0);
  assert.equal(m.a[3], 0);
  assert.ok(m.target <= 0.05);
  assert.throws(() => levelMatch(new Float64Array(4), b), /silent/);
  assert.throws(() => levelMatch([NaN], b), /range/);
});
test('decoder rejects long recordings and wrong processing rate', () => {
  assert.throws(() => mono({ sampleRate: 44100, duration: 2 }), /48 kHz/);
  assert.throws(() => mono({ sampleRate: 48000, duration: 61 }), /60 seconds/);
});
test('response subtracts silence and interpretation preserves the identical-input null', () => {
  const r = {
      group_counts: [
        [0, 2],
        [0, 4],
        [0, 2],
        [0, 1],
      ],
      group_sizes: [1, 2],
    },
    c = {
      group_counts: [
        [0, 1],
        [0, 1],
        [0, 1],
        [0, 1],
      ],
    };
  const result = summarize(r, c, 1, 2);
  assert.equal(result.mean, 50);
  assert.equal(result.tail, 0);
  assert.match(localReading(result, result), /no basis/);
});
