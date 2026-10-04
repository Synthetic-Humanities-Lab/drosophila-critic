import test from "node:test";
import assert from "node:assert/strict";
import { RecordedPath } from "../static/recorded-path.js";
import { FollowCameraTrack } from "../static/follow-camera.js";

const positions = Array.from({ length: 21 }, (_, i) => [
  i / 10,
  -i / 20,
  0.2 + i / 10,
]);
const recording = {
  time: positions.map((_, i) => i / 50),
  positions: positions.map((p) => [p]),
};

test("path stays on the floor, uses measured XY, and ends at the interpolated playback position", () => {
  const track = new FollowCameraTrack(recording, 0);
  const path = new RecordedPath(track.positions);
  const state = track.sample(0.13);
  const view = path.sample(state);
  assert.equal(view.count, 7);
  assert.ok(
    view.tip
      .slice(3)
      .every((value, i) => Math.abs(value - [0.65, 0.008, 0.325][i]) < 1e-12),
  );
  assert.equal(view.map, "M10.000,8.000 L10.500,8.250 L10.650,8.325");
  assert.ok(!view.map.includes("12.000"));
  assert.ok(Math.abs(path.floor[20 * 3] - 2) < 1e-6);
  assert.ok(Math.abs(path.floor[20 * 3 + 1] - 0.008) < 1e-6);
});

test("seeking rewinds the trace, reaches the last frame, and never changes recorded movement", () => {
  const original = JSON.stringify(recording);
  const track = new FollowCameraTrack(recording, 0);
  const path = new RecordedPath(track.positions);
  const first = path.sample(track.sample(0));
  const end = path.sample(track.sample(100));
  assert.equal(end.count, 21);
  assert.ok(end.map.endsWith("L12.000,9.000"));
  assert.deepEqual(path.sample(track.sample(0)), first);
  assert.equal(first.count, 1);
  assert.equal(JSON.stringify(recording), original);
});
