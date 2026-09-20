import test from 'node:test';
import assert from 'node:assert/strict';
import { describeContrast } from '../static/delivery-reading.js';
test('response-only interpretation preserves null and mixed-seed results', () => {
  assert.match(describeContrast({ zero: 8 }, 8), /does not distinguish/);
  assert.match(
    describeContrast(
      { zero: 0, positive: 4, negative: 4, mean: 0.001, sd: 0.03 },
      8,
    ),
    /does not support a stable average-rate separation/,
  );
  assert.match(
    describeContrast(
      { zero: 0, positive: 8, negative: 0, mean: 0.3, sd: 0.03 },
      8,
    ),
    /consistently larger/,
  );
});
