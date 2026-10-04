import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import { gunzipSync } from "node:zlib";
import * as THREE from "../static/vendor/three.module.js";
import {
  FollowCameraTrack,
  frameAt,
  closeView,
} from "../static/follow-camera.js";

function recording(position, samples = 101) {
  const time = Array.from({ length: samples }, (_, i) => i / 50);
  return { time, positions: time.map((t, i) => [position(t, i)]) };
}

test("body sampling interpolates between frames and reaches the final frame", () => {
  const track = new FollowCameraTrack(
    recording((t) => [t, 2 * t, 0.14]),
    0,
  );
  assert.deepEqual(track.sample(0.31).position, [0.31, 0.62, 0.14]);
  assert.deepEqual(frameAt([0, 1, 2], 2), { lo: 2, hi: 2, alpha: 0 });
  assert.deepEqual(track.sample(99).position, [2, 4, 0.14]);
  assert.deepEqual(track.sample(-1).position, [0, 0, 0.14]);
});

test("tracking removes small rapid body bobbing without delaying straight travel", () => {
  const track = new FollowCameraTrack(
    recording((t, i) => [t, 0, 0.14 + (i % 2 ? 0.03 : -0.03)]),
    0,
  );
  for (const t of [0.6, 0.62, 0.64, 1]) {
    const { target } = track.sample(t);
    assert.ok(Math.abs(target[0] - t) < 1e-10);
    assert.ok(Math.abs(target[2] - 0.14) < 0.001);
  }
});

test("seeking, pause, reversed playback and different frame rates give identical framing", () => {
  const data = recording((t) => [Math.sin(t * 12), Math.cos(t * 6), 0.2]);
  const original = JSON.stringify(data);
  const track = new FollowCameraTrack(data, 0);
  const expected = track.sample(1.23);
  for (let i = 0; i < 360; i++) track.sample(i / 144);
  track.sample(0);
  assert.deepEqual(track.sample(1.23), expected);
  assert.deepEqual(new FollowCameraTrack(data, 0).sample(1.23), expected);
  assert.equal(JSON.stringify(data), original);
});

test("fast turns cannot pull the camera target away from the fly", () => {
  const track = new FollowCameraTrack(
    recording((t) => [Math.sin(t * 60) * 8, Math.cos(t * 60) * 6, 4]),
    0,
  );
  for (let i = 0; i <= 400; i++) {
    const { target, position } = track.sample(i / 200);
    assert.ok(
      Math.hypot(...target.map((x, j) => x - position[j])) <= 0.240000001,
    );
  }
});

test("the real human and robot trajectories produce finite continuous camera paths", () => {
  for (const reader of ["a", "b"]) {
    const data = JSON.parse(
      gunzipSync(
        fs.readFileSync(
          `experiments/encounter-v3/${reader}-sound-1101.json.gz`,
        ),
      ),
    );
    const track = new FollowCameraTrack(
      data,
      data.body_names.indexOf("walker/thorax"),
    );
    for (const time of data.time.slice(1, -1)) {
      const left = track.sample(time - 1e-7).target;
      const right = track.sample(time + 1e-7).target;
      assert.ok(right.every(Number.isFinite));
      assert.ok(Math.hypot(...left.map((v, i) => v - right[i])) < 0.0001);
    }
  }
});

test("close framing retains every articulated joint through both complete performances", () => {
  for (const reader of ["a", "b"]) {
    const data = JSON.parse(
      gunzipSync(
        fs.readFileSync(
          `experiments/encounter-v3/${reader}-sound-1101.json.gz`,
        ),
      ),
    );
    const track = new FollowCameraTrack(
      data,
      data.body_names.indexOf("walker/thorax"),
    );
    // The inset is narrower than either supported main scene viewport.
    const camera = new THREE.PerspectiveCamera(38, 1.2, 0.005, 200);
    let rawAcceleration = 0,
      cameraAcceleration = 0;
    const samples = data.time.map((time) => track.sample(time));
    samples.forEach((sample, i) => {
      const view = closeView(sample.target);
      camera.fov = view.fov;
      camera.updateProjectionMatrix();
      camera.position.fromArray(view.position);
      camera.lookAt(new THREE.Vector3(...view.lookAt));
      camera.updateMatrixWorld();
      data.positions[i].forEach((position, j) => {
        if (data.body_names[j] === "world") return;
        const p = new THREE.Vector3(
          position[0],
          position[2],
          -position[1],
        ).project(camera);
        assert.ok(
          Math.max(Math.abs(p.x), Math.abs(p.y)) < 0.9,
          `${reader}: ${data.body_names[j]} at ${data.time[i]} falls outside the safe frame`,
        );
      });
      if (i === 0 || i === samples.length - 1) return;
      for (let axis = 0; axis < 3; axis++) {
        rawAcceleration +=
          (samples[i + 1].position[axis] -
            2 * sample.position[axis] +
            samples[i - 1].position[axis]) **
          2;
        cameraAcceleration +=
          (samples[i + 1].target[axis] -
            2 * sample.target[axis] +
            samples[i - 1].target[axis]) **
          2;
      }
    });
    assert.ok(Math.sqrt(cameraAcceleration / rawAcceleration) < 0.55);
  }
});
