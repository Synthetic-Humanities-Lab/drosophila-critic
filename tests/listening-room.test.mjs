import test from "node:test";
import assert from "node:assert/strict";
import * as THREE from "../static/vendor/three.module.js";
import { ListeningRoom, tableView } from "../static/listening-room.js";

function camera(aspect = 1073 / 445) {
  const view = tableView(aspect);
  const result = new THREE.PerspectiveCamera(view.fov, aspect, 0.1, 1000);
  result.position.fromArray(view.position);
  result.lookAt(new THREE.Vector3(...view.lookAt));
  result.updateMatrixWorld();
  return result;
}
function project(point, view) {
  const p = new THREE.Vector3(...point).project(view);
  return [(p.x + 1) / 2, (1 - p.y) / 2];
}

test("the box occupies the approved render's foreground-right quadrilateral", () => {
  const view = camera();
  // Independently measured pixels from the approved 1073 × 445 scene crop.
  const landmarks = [
    [
      [-10, 10, 8],
      [653, 235],
    ],
    [
      [-10, 10, -8],
      [736, 214],
    ],
    [
      [10, 10, -8],
      [948, 235],
    ],
    [
      [10, 10, 8],
      [886, 264],
    ],
    [
      [-10, 0, 8],
      [653, 335],
    ],
    [
      [10, 0, -8],
      [948, 333],
    ],
    [
      [10, 0, 8],
      [886, 377],
    ],
  ];
  for (const [point, expected] of landmarks) {
    const actual = project(point, view).map((v, i) => v * [1073, 445][i]);
    assert.ok(Math.hypot(...actual.map((v, i) => v - expected[i])) < 11);
  }
});

test("the staged book and microphone remain at the reference's reading position", () => {
  const room = new ListeningRoom();
  const view = camera();
  for (const [name, expected] of [
    ["reading-book", [312, 246]],
    ["microphone", [376, 167]],
  ]) {
    const point = room
      .getObjectByName(name)
      .getWorldPosition(new THREE.Vector3());
    const actual = project(point.toArray(), view).map(
      (v, i) => v * [1073, 445][i],
    );
    assert.ok(Math.hypot(...actual.map((v, i) => v - expected[i])) < 3);
  }
  assert.deepEqual(room.scale.toArray(), [1, 1, 1]);
  assert.deepEqual(room.enclosure.scale.toArray(), [1, 1, 1]);
});

test("phone framing preserves the box and reader without changing their physical scale", () => {
  const desktop = camera();
  const phone = camera(364 / 290);
  for (const point of [
    [-10, 0, 8],
    [10, 10, -8],
    [-110, 30, -22],
  ]) {
    const a = project(point, desktop);
    const b = project(point, phone);
    assert.ok(
      Math.abs(a[0] - b[0]) < 1e-10,
      "retain the horizontal composition",
    );
    assert.ok(b.every((v) => v > 0 && v < 1));
  }
});

test("reader changes and cutaway rendering restore the same room and shared reader pose", () => {
  const room = new ListeningRoom();
  const position = room.actor.position.clone();
  room.setReader("silence");
  assert.equal(room.actor.visible, false);
  room.setReader("b");
  assert.equal(room.actor.visible, true);
  assert.equal(room.humanHead.visible, true);
  assert.equal(room.robotHead.visible, false);
  room.setReader("a");
  assert.equal(room.humanHead.visible, false);
  assert.equal(room.robotHead.visible, true);
  assert.deepEqual(room.actor.position, position);
  room.setCutaway(true);
  assert.equal(room.enclosure.visible, false);
  assert.equal(room.actor.visible, false);
  assert.equal(room.floor.visible, true);
  room.setCutaway(false);
  assert.equal(room.enclosure.visible, true);
  assert.equal(room.actor.visible, true);
  room.setReader("silence");
  room.setCutaway(true);
  room.setCutaway(false);
  assert.equal(room.actor.visible, false);
});
