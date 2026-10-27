import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs/promises";
import { createHash } from "node:crypto";
import {
  BODY_PHYSICS_BUILD,
  bodyPhysicsAsset,
} from "../static/body-physics.js";
import loadOptimized from "../static/vendor/mujoco-simd/mujoco.js";
import { loadBodyAssets } from "../scripts/body_browser_assets.mjs";
import { BodyRuntime } from "../static/body-runtime.js";
import { createBodyPolicies } from "../static/body-policy-bundle.js";
import { gunzipSync } from "node:zlib";

const root = new URL("../", import.meta.url);
const read = (name) => fs.readFile(new URL(name, root));
const digest = (bytes) => createHash("sha256").update(bytes).digest("hex");
const manifest = JSON.parse(await read("static/assets/body-v1/manifest.json"));

test("the faster physics build is pinned and leaves the reference contract intact", async () => {
  const wasm = await read("static/vendor/mujoco-simd/mujoco.wasm");
  assert.equal(digest(wasm), BODY_PHYSICS_BUILD.sha256);
  assert.equal(wasm.length, BODY_PHYSICS_BUILD.bytes);
  assert.equal(
    digest(await read("static/vendor/mujoco-simd/mujoco.js")),
    BODY_PHYSICS_BUILD.loader_sha256,
  );
  assert.equal(
    digest(await read("static/vendor/mujoco/mujoco.wasm")),
    BODY_PHYSICS_BUILD.reference_sha256,
  );
  const copy = structuredClone(manifest);
  const asset = bodyPhysicsAsset(manifest);
  assert.equal(
    asset.download_bytes,
    manifest.download_bytes - manifest.physics.bytes + wasm.length,
  );
  assert.deepEqual(manifest, copy);
  assert.throws(() => bodyPhysicsAsset(null), /not been checked/);
  assert.throws(
    () => bodyPhysicsAsset({ ...manifest, physics: null }),
    /not been checked/,
  );
  assert.throws(
    () => bodyPhysicsAsset({ ...manifest, mujoco: "different" }),
    /not been checked/,
  );
  assert.throws(
    () => bodyPhysicsAsset({ ...manifest, physics: { sha256: "different" } }),
    /not been checked/,
  );
});

test("strict SIMD reproduces actuated physics, controller observations and policy outputs exactly", async () => {
  const reference = await loadBodyAssets();
  const optimized = await loadOptimized({
    wasmBinary: await read("static/vendor/mujoco-simd/mujoco.wasm"),
  });
  const bodies = [reference.mj, optimized].map(
    (mj) => new BodyRuntime(mj, reference.assets, reference.policies),
  );
  try {
    for (let step = 0; step < 80; step++) {
      const command = {
        speed: 2,
        turn: step < 30 ? 0 : 0.3,
        state: step < 60 ? "walking" : "takeoff",
        height: 1,
      };
      for (const body of bodies) body.step(command);
      const [before, after] = bodies;
      for (const key of [
        "qpos",
        "qvel",
        "act",
        "ctrl",
        "qacc",
        "qacc_warmstart",
        "sensordata",
      ])
        assert.deepEqual(
          after.d[key],
          before.d[key],
          `${key} at controller step ${step}`,
        );
      assert.deepEqual(after.sensors, before.sensors);
      assert.deepEqual(after.snapshot(), before.snapshot());
      for (const kind of ["walking", "flight"])
        assert.deepEqual(
          after.observation(kind, 2, 0.3, 1, 0),
          before.observation(kind, 2, 0.3, 1, 0),
        );
    }
  } finally {
    for (const body of bodies) body.dispose();
  }
});

test("sharing policy memory preserves weights and alternating inference exactly", async () => {
  const reference = await loadBodyAssets();
  const metadata = {},
    weights = {};
  for (const kind of ["walking", "flight"]) {
    metadata[kind] = JSON.parse(
      await read(`static/assets/body-v1/${kind}.json`),
    );
    const raw = gunzipSync(await read(`static/assets/body-v1/${kind}.f32.gz`));
    weights[kind] = raw.buffer.slice(
      raw.byteOffset,
      raw.byteOffset + raw.byteLength,
    );
  }
  const originalMetadata = structuredClone(metadata);
  const { instance } = await WebAssembly.instantiate(
    await read("static/body-dense.wasm"),
  );
  const policies = createBodyPolicies(metadata, weights, instance.exports);
  assert.equal(policies.walking.kernel.memory, policies.flight.kernel.memory);
  assert.deepEqual(metadata, originalMetadata);
  for (const kind of ["walking", "flight"])
    for (let index = 0; index < policies[kind].arrays.length; index++)
      assert.deepEqual(
        policies[kind].arrays[index].data,
        reference.policies[kind].arrays[index].data,
      );
  const body = new BodyRuntime(
    reference.mj,
    reference.assets,
    reference.policies,
  );
  try {
    let previous, saved;
    for (let i = 0; i < 24; i++) {
      body.step({ speed: 2, turn: i > 10 ? 0.3 : 0 });
      for (const kind of ["walking", "flight"]) {
        const obs = body.observation(kind, 2, 0.3, 0.1278, 0);
        const actual = policies[kind].infer(obs);
        assert.deepEqual(actual, reference.policies[kind].infer(obs));
        if (previous)
          assert.deepEqual(
            previous,
            saved,
            "returned actions must not alias shared scratch",
          );
        previous = actual;
        saved = actual.slice();
      }
    }
  } finally {
    body.dispose();
  }
  assert.throws(
    () =>
      createBodyPolicies(metadata, weights, {
        memory: { buffer: new ArrayBuffer(32) },
      }),
    /allocated memory/,
  );
});
