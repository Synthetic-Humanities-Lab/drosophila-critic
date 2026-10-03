import loadMuJoCo from "./vendor/mujoco/mujoco.js";
import { BodyPolicy } from "./body-policy.js";
import { simulateBody } from "./body-processing.js";

let runtime,
  controller,
  cancelled = false,
  busy = false;
const hash = async (bytes) =>
  Array.from(
    new Uint8Array(await crypto.subtle.digest("SHA-256", bytes)),
    (x) => x.toString(16).padStart(2, "0"),
  ).join("");
const decompress = async (bytes) =>
  new Response(
    new Blob([bytes]).stream().pipeThrough(new DecompressionStream("gzip")),
  ).arrayBuffer();
async function initialize() {
  const base = new URL("./assets/body-v1/", import.meta.url),
    response = await fetch(new URL("manifest.json", base), {
      signal: controller.signal,
    });
  if (!response.ok) throw new Error("The body model is unavailable.");
  const manifest = await response.json();
  let cache;
  try {
    cache = await caches.open(manifest.version);
  } catch {
    cache = null;
  }
  let loaded = 0;
  const file = async (name, spec) => {
    const url = new URL(name, base);
    let r = cache ? await cache.match(url) : null;
    const cached = Boolean(r);
    if (!r) r = await fetch(url, { signal: controller.signal });
    if (!r.ok) throw new Error(`A body asset could not load (${r.status}).`);
    const bytes = await r.arrayBuffer();
    if (spec && (await hash(bytes)) !== spec.sha256) {
      if (cache) await cache.delete(url);
      throw new Error("Body asset checksum mismatch.");
    }
    if (cache && !cached)
      try {
        await cache.put(url, new Response(bytes));
      } catch {
        cache = null;
      }
    loaded += bytes.byteLength;
    postMessage({
      type: "progress",
      stage: "Loading the legs and wings model",
      fraction: Math.min(1, loaded / manifest.download_bytes),
      bytes: loaded,
    });
    return bytes;
  };
  const files = {};
  for (const [name, spec] of Object.entries(manifest.files))
    files[name] = await file(name, spec);
  const text = (name) => new TextDecoder().decode(files[name]),
    json = (name) => JSON.parse(text(name));
  const assets = {
    xml: text("body.xml"),
    model: json("model.json"),
    views: json("views.json"),
    config: json("adapter.json"),
    wingbeat: JSON.parse(
      new TextDecoder().decode(await decompress(files["wingbeat.json.gz"])),
    ),
  };
  const policies = {};
  const kernel = await file("../../body-dense.wasm", manifest.kernel);
  for (const kind of ["walking", "flight"]) {
    const { instance } = await WebAssembly.instantiate(kernel);
    policies[kind] = new BodyPolicy(
      json(kind + ".json"),
      await decompress(files[kind + ".f32.gz"]),
      instance.exports,
    );
  }
  const wasm = await file("../../vendor/mujoco/mujoco.wasm", manifest.physics);
  const mj = await loadMuJoCo({ wasmBinary: wasm });
  runtime = { mj, assets, policies, manifest };
  // MuJoCo does not export Emscripten's HEAPU8 accessor. Its typed state views
  // expose the backing memory without relying on private runtime properties.
  const probeModel = mj.MjModel.from_xml_string(assets.xml),
    probeData = new mj.MjData(probeModel);
  const physicsHeapBytes = probeData.qpos.buffer.byteLength;
  probeData.delete();
  probeModel.delete();
  return {
    asset_manifest: manifest,
    runtime_module: import.meta.url,
    download_bytes: manifest.download_bytes,
    physics_heap_bytes: physicsHeapBytes,
    policy_memory_bytes: Object.values(policies).reduce(
      (total, policy) => total + policy.kernel.memory.buffer.byteLength,
      0,
    ),
  };
}
self.onmessage = async ({ data }) => {
  if (data.type === "cancel") {
    cancelled = true;
    controller?.abort();
    return;
  }
  if (busy) {
    postMessage({
      type: "error",
      message: "The body model is already running.",
    });
    return;
  }
  busy = true;
  cancelled = false;
  controller = new AbortController();
  try {
    if (data.type === "initialize")
      postMessage({ type: "initialized", ...(await initialize()) });
    else if (data.type === "simulate") {
      if (!runtime) throw new Error("Load the body model first.");
      const result = await simulateBody(
        runtime,
        runtime.assets.config,
        data.run,
        {
          duration: data.duration,
          cancelled: () => cancelled,
          onProgress: (p) =>
            postMessage({
              type: "progress",
              stage: data.label || "Calculating body movement",
              ...p,
            }),
        },
      );
      postMessage({ type: "result", result });
    } else throw new Error("Unknown body worker request.");
  } catch (e) {
    postMessage({
      type: cancelled ? "cancelled" : "error",
      message: e.message,
    });
  } finally {
    busy = false;
  }
};
