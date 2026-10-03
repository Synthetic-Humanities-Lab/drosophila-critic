import { test } from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { createHash } from "node:crypto";
const source = await readFile(
  new URL("../static/browser-random.js", import.meta.url),
  "utf8",
);
const { PCG64 } = await import(
  `data:text/javascript;base64,${Buffer.from(source).toString("base64")}`
);
const seed = {
  state: "293291770318435625894158472284679299278",
  inc: "99899682932297841526903930334913964403",
};
test("PCG64 matches NumPy double outputs exactly, including reset", () => {
  const expected = [
    0.888159031098787, 0.07096477075830965, 0.8149580977541088,
    0.8955949954553245, 0.47656071785840826, 0.5535381200553162,
    0.7019922783335115, 0.8583028197576769, 0.8946772760037724,
    0.5030380953108272,
  ];
  for (let repeat = 0; repeat < 2; repeat++) {
    const rng = new PCG64(seed);
    assert.deepEqual(
      expected.map(() => rng.next()),
      expected,
    );
  }
});

test("PCG64 preserves one million exact NumPy samples and final state for every supported seed", async () => {
  const { fixtures } = JSON.parse(
    await readFile(new URL("./pcg64-stream-fixtures.json", import.meta.url)),
  );
  for (const fixture of fixtures) {
    const rng = new PCG64(fixture.initial);
    const bytes = new ArrayBuffer(fixture.count * 8);
    const view = new DataView(bytes);
    for (let i = 0; i < fixture.count; i++)
      view.setFloat64(i * 8, rng.next(), true);
    assert.equal(
      createHash("sha256").update(new Uint8Array(bytes)).digest("hex"),
      fixture.float64_le_sha256,
      `seed ${fixture.seed}`,
    );
    const state = rng.state.reduce(
      (sum, limb, i) => sum + (BigInt(limb) << BigInt(i * 16)),
      0n,
    );
    assert.equal(state.toString(), fixture.final.state);
  }
});
