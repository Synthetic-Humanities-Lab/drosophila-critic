import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs/promises";
import zlib from "node:zlib";
import crypto from "node:crypto";
import { silencePrefix } from "../static/silence-control.js";

test("saved silence reproduces the previously verified full Safari run, including its partial last bin", async () => {
  const base = new URL("../static/assets/silence-v1/", import.meta.url);
  const manifest = JSON.parse(
    await fs.readFile(new URL("manifest.json", base)),
  );
  const reference = JSON.parse(
    await fs.readFile(
      new URL(
        "../experiments/mobile-v1/safari-simulator-robot.json",
        import.meta.url,
      ),
    ),
  );
  const steps = reference.neural.silence.steps;
  const chunks = await Promise.all(
    manifest.chunks
      .filter((part) => part.start < steps)
      .map(async (part) =>
        JSON.parse(
          zlib.gunzipSync(await fs.readFile(new URL(part.file, base))),
        ),
      ),
  );
  const { run, body } = silencePrefix(
    manifest,
    chunks,
    steps,
    reference.duration,
  );
  const hash = (value) =>
    crypto.createHash("sha256").update(JSON.stringify(value)).digest("hex");
  for (const [key, field] of [
    ["counts", "counts"],
    ["group_counts", "groups"],
    ["spatial", "spatial"],
  ])
    assert.equal(hash(run[key]), reference.neural.silence[field], key);
  for (const key of ["positions", "quaternions"])
    assert.equal(hash(body[key]), reference.body.silence[key], key);
  for (const [key, expected] of Object.entries(
    reference.body.silence.metrics,
  )) {
    if (key === "wall_seconds") continue;
    if (typeof expected === "number")
      // Math.atan2/sin reductions differ by a few last bits between JS engines.
      assert.ok(Math.abs(body.metrics[key] - expected) < 1e-12, key);
    else assert.deepEqual(body.metrics[key], expected, key);
  }
});
