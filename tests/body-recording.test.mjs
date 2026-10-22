import test from "node:test";
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { gunzipSync } from "node:zlib";
import { decodeBodyRecording } from "../static/body-recording.js";
import { FollowCameraTrack } from "../static/follow-camera.js";

const root = new URL("../", import.meta.url);
// Use the actual Python packer, not a second implementation of the writer.
const packed = execFileSync(
  "python3",
  [
    "-c",
    `
import gzip,json,sys
from scripts.pack_playback import pack_body
data=json.loads(gzip.decompress(open('experiments/encounter-v3/a-sound-1101.json.gz','rb').read()))
sys.stdout.buffer.write(pack_body(data))
`,
  ],
  { cwd: root, maxBuffer: 20000000 },
);
const buffer = () =>
  packed.buffer.slice(packed.byteOffset, packed.byteOffset + packed.byteLength);
test("browser decoder preserves every pose and the camera path of a real recording", () => {
  const original = JSON.parse(
    gunzipSync(
      readFileSync(
        new URL(
          "../experiments/encounter-v3/a-sound-1101.json.gz",
          import.meta.url,
        ),
      ),
    ),
  );
  const decoded = decodeBodyRecording(buffer());
  for (const key of Object.keys(original)) {
    if (key === "time")
      assert.deepEqual(Array.from(decoded.time), original.time);
    else if (key === "positions" || key === "quaternions") {
      for (let i = 0; i < original[key].length; i++)
        for (let j = 0; j < original.body_names.length; j++)
          assert.deepEqual(Array.from(decoded[key][i][j]), original[key][i][j]);
    } else assert.deepEqual(decoded[key], original[key]);
  }
  const index = original.body_names.indexOf("walker/thorax");
  const a = new FollowCameraTrack(original, index),
    b = new FollowCameraTrack(decoded, index);
  for (const time of [0, 1.01, 9.62, 20.53, 29.2]) {
    const old = a.sample(time),
      next = b.sample(time);
    assert.deepEqual(Array.from(next.position), old.position);
    assert.deepEqual(Array.from(next.target), old.target);
  }
});
test("truncated, unrecognized, or extended body files are rejected", () => {
  assert.throws(() => decodeBodyRecording(new ArrayBuffer(3)), /invalid/);
  const wrong = buffer();
  new Uint8Array(wrong)[0] = 0;
  assert.throws(() => decodeBodyRecording(wrong), /invalid/);
  assert.throws(() => decodeBodyRecording(buffer().slice(0, -1)), /invalid/);
  const extra = new Uint8Array(packed.length + 1);
  extra.set(packed);
  assert.throws(() => decodeBodyRecording(extra.buffer), /invalid/);
});
