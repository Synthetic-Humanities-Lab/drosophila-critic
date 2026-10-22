import test from "node:test";
import assert from "node:assert/strict";
import { forEachConcurrent } from "../static/parallel-load.js";

test("downloads overlap within the memory limit and retain their destination offsets", async () => {
  let active = 0,
    peak = 0;
  const output = [];
  await forEachConcurrent([3, 1, 4, 2, 5], async (value, index) => {
    peak = Math.max(peak, ++active);
    await new Promise((resolve) => setTimeout(resolve, value));
    output[index] = value;
    active--;
  });
  assert.equal(peak, 2);
  assert.deepEqual(output, [3, 1, 4, 2, 5]);
});
test("failure stops dispatch and drains active work before rejecting", async () => {
  const visited = [];
  let finished = false;
  await assert.rejects(
    forEachConcurrent([0, 1, 2, 3], async (value) => {
      visited.push(value);
      if (value === 0) {
        await Promise.resolve();
        throw new Error("Failed chunk");
      }
      await new Promise((resolve) => setTimeout(resolve, 2));
      finished = true;
    }),
    /Failed chunk/,
  );
  assert.deepEqual(visited, [0, 1]);
  assert.equal(finished, true);
  await assert.rejects(
    forEachConcurrent([], () => {}, 0),
    /Invalid/,
  );
});
