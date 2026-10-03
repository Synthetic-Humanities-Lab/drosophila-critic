import fs from "node:fs/promises";
import zlib from "node:zlib";
import loadMuJoCo from "../static/vendor/mujoco/mujoco.js";
import { BodyPolicy } from "../static/body-policy.js";

export async function loadBodyAssets() {
  const root = "static/assets/body-v1/",
    json = async (name) => JSON.parse(await fs.readFile(root + name));
  const assets = {
    xml: await fs.readFile(root + "body.xml", "utf8"),
    model: await json("model.json"),
    views: await json("views.json"),
    wingbeat: JSON.parse(
      zlib.gunzipSync(await fs.readFile(root + "wingbeat.json.gz")),
    ),
    config: await json("adapter.json"),
  };
  const policies = {};
  for (const kind of ["walking", "flight"]) {
    const raw = zlib.gunzipSync(await fs.readFile(root + kind + ".f32.gz"));
    const { instance } = await WebAssembly.instantiate(
      await fs.readFile("static/body-dense.wasm"),
    );
    policies[kind] = new BodyPolicy(
      await json(kind + ".json"),
      raw.buffer.slice(raw.byteOffset, raw.byteOffset + raw.byteLength),
      instance.exports,
    );
  }
  const mj = await loadMuJoCo({
    wasmBinary: await fs.readFile("static/vendor/mujoco/mujoco.wasm"),
  });
  return { mj, assets, policies };
}
