import fs from "node:fs/promises";
import zlib from "node:zlib";
import { BodyPolicy } from "../static/body-policy.js";

const report = [];
for (const kind of ["walking", "flight"]) {
  const metadata = JSON.parse(
    await fs.readFile(`static/assets/body-v1/${kind}.json`),
  );
  const raw = zlib.gunzipSync(
    await fs.readFile(`static/assets/body-v1/${kind}.f32.gz`),
  );
  const { instance } = await WebAssembly.instantiate(
    await fs.readFile("static/body-dense.wasm"),
  );
  const policy = new BodyPolicy(
    metadata,
    raw.buffer.slice(raw.byteOffset, raw.byteOffset + raw.byteLength),
    instance.exports,
  );
  const fixtures = JSON.parse(
    await fs.readFile(`results/body-controller/export/${kind}-fixtures.json`),
  );
  let maximum = 0,
    relative = 0,
    clipped = 0;
  for (const f of fixtures) {
    if (!f.ctrlrange)
      throw new Error("Regenerate fixtures with their actual action limits.");
    const observation = Object.fromEntries(
      Object.entries(f.observation).map(([k, v]) => [k, v.flat(Infinity)]),
    );
    const actual = policy.infer(observation);
    const expected = f.expected;
    let delta = 0,
      scale = 1;
    for (let i = 0; i < actual.length; i++) {
      delta = Math.max(delta, Math.abs(actual[i] - expected[i]));
      scale = Math.max(scale, Math.abs(expected[i]));
      // Exact actuator limits are checked by the shared fixture below.
      if (f.ctrlrange) {
        const clamp = (x) =>
          Math.min(f.ctrlrange[i][1], Math.max(f.ctrlrange[i][0], x));
        clipped = Math.max(
          clipped,
          Math.abs(clamp(actual[i]) - clamp(expected[i])),
        );
      }
    }
    maximum = Math.max(maximum, delta);
    relative = Math.max(relative, delta / scale);
  }
  report.push({
    kind,
    fixtures: fixtures.length,
    max_absolute: maximum,
    relative_infinity: relative,
    max_clipped: clipped,
  });
}
console.log(JSON.stringify(report, null, 2));
await fs.writeFile(
  "results/body-controller/export/browser-policy-parity.json",
  JSON.stringify(report, null, 2),
);
if (report.some((r) => r.relative_infinity > 1e-5 || r.max_clipped > 1e-4))
  process.exitCode = 1;
