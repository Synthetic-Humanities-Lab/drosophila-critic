import * as T from "./vendor/three.module.js";
import { ArticulatedFly } from "./body-view.js";
const $ = (id) => document.getElementById(id),
  canvas = $("view");
const renderer = new T.WebGLRenderer({
  canvas,
  antialias: true,
  preserveDrawingBuffer: true,
});
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = T.PCFSoftShadowMap;
renderer.setClearColor(0x29342b);
const scene = new T.Scene(),
  camera = new T.PerspectiveCamera(40, 1, 0.003, 100);
scene.add(new T.HemisphereLight(0xfff5de, 0x383f43, 2));
const sun = new T.DirectionalLight(0xffdab0, 3);
sun.castShadow = true;
sun.shadow.mapSize.set(2048, 2048);
Object.assign(sun.shadow.camera, { left: -2, right: 2, top: 2, bottom: -2 });
sun.shadow.normalBias = 0.0002;
scene.add(sun, sun.target);
const floor = new T.Mesh(
  new T.PlaneGeometry(20, 16),
  new T.MeshStandardMaterial({ color: 0xb6bba6, roughness: 0.95 }),
);
floor.rotation.x = -Math.PI / 2;
floor.receiveShadow = true;
scene.add(floor);
const grid = new T.GridHelper(20, 20, 0x73866c, 0x819477);
grid.position.y = 0.001;
scene.add(grid);
const fly = new ArticulatedFly(
  new URL("./assets/flybody/flybody.glb", import.meta.url).href,
);
scene.add(fly);
let data,
  time = 0,
  playing = false,
  previous = performance.now(),
  recorder,
  recorded = [],
  capture,
  context;
function stop() {
  playing = false;
  $("play").textContent = "Play proof";
  if (recorder?.state === "recording") recorder.stop();
}
async function init() {
  const r = await fetch("./experiments/encounter-v3/controller-proof.json.gz");
  if (!r.ok) throw new Error("Controller proof is unavailable.");
  data = await new Response(
    r.body.pipeThrough(new DecompressionStream("gzip")),
  ).json();
  await fly.ready;
  $("seek").max = data.time.at(-1);
  requestAnimationFrame(frame);
}
$("play").onclick = () => {
  if (playing) stop();
  else {
    if (time >= data.time.at(-1)) time = 0;
    playing = true;
    previous = performance.now();
    $("play").textContent = "Pause";
  }
};
$("seek").oninput = () => {
  stop();
  time = +$("seek").value;
};
$("record").onclick = () => {
  if (!data) return;
  capture = document.createElement("canvas");
  capture.width = 1280;
  capture.height = 800;
  context = capture.getContext("2d");
  const type = ["video/webm;codecs=vp9", "video/webm", "video/mp4"].find((x) =>
    MediaRecorder.isTypeSupported(x),
  );
  if (!type) {
    $("status").textContent = "This browser cannot save canvas video.";
    return;
  }
  recorded = [];
  recorder = new MediaRecorder(capture.captureStream(30), {
    mimeType: type,
    videoBitsPerSecond: 5000000,
  });
  recorder.ondataavailable = (e) => {
    if (e.data.size) recorded.push(e.data);
  };
  recorder.onstop = () => {
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob(recorded, { type }));
    a.download =
      "flybody-controller-proof." + (type.includes("mp4") ? "mp4" : "webm");
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 60000);
    capture = null;
  };
  time = 0;
  previous = performance.now();
  playing = true;
  recorder.start();
  $("play").textContent = "Pause";
};
function frame(now) {
  requestAnimationFrame(frame);
  if (playing)
    time = Math.min(data.time.at(-1), time + (now - previous) / 1000);
  previous = now;
  let i = Math.min(
    data.time.length - 1,
    Math.max(0, Math.floor(time / 0.02) - 1),
  );
  const pose = fly.pose(data, time);
  fly.setFlightBlur(data.airborne[i]);
  camera.position.copy(pose.position).add(new T.Vector3(0.4, 0.35, 0.8));
  camera.lookAt(pose.position);
  sun.position.copy(pose.position).add(new T.Vector3(-3, 6, 4));
  sun.target.position.copy(pose.position);
  const width = canvas.clientWidth,
    height = canvas.clientHeight;
  if (
    canvas.width !== Math.round(width * renderer.getPixelRatio()) ||
    canvas.height !== Math.round(height * renderer.getPixelRatio())
  )
    renderer.setSize(width, height, false);
  camera.aspect = width / height;
  camera.updateProjectionMatrix();
  renderer.render(scene, camera);
  const c = data.commands[i],
    state = data.states[i],
    status = `${state.toUpperCase()} · reference ${c.body_reference_speed.toFixed(2)} cm/s · turn ${c.body_reference_turn.toFixed(2)} rad/s${c.boundary ? " · ARENA CORRECTION" : ""}`;
  $("status").textContent = status;
  $("time").value = time.toFixed(2) + " s";
  $("seek").value = time;
  if (capture) {
    context.fillStyle = "#101911";
    context.fillRect(0, 0, 1280, 800);
    context.drawImage(canvas, 0, 40, 1280, 680);
    context.fillStyle = "#eadfc5";
    context.font = "20px monospace";
    context.fillText(
      "FLYBODY · FROZEN POLICIES · CONTROLLED STIMULATION TEST",
      24,
      28,
    );
    context.fillText(time.toFixed(2) + " s · " + status, 24, 751);
    context.font = "16px monospace";
    context.fillText(
      "Actuated MuJoCo physics. Takeoff, landing and confinement are added engineering rules.",
      24,
      780,
    );
  }
  if (playing && time >= data.time.at(-1)) stop();
}
init().catch((e) => {
  $("status").textContent = e.message;
});
