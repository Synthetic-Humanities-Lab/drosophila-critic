// This build changes compiler output, not the model's simulation contract.
// The original distribution remains the numerical reference for saved silence.
export const BODY_PHYSICS_BUILD = Object.freeze({
  version: "mujoco-3.14.0-body-v2",
  source_commit: "9ecbb9d7b5ee623f54745638d36799ff90e6f7cd",
  emscripten: "4.0.10",
  flags: "-O3 -msimd128 -ffp-contract=off -flto; single threaded; no fast math",
  binding_sha256:
    "e1ef634a20209f7f6a7bcb90958c81b88cf3e154ed5766586bc915a5f8ccd204",
  reference_sha256:
    "2d380f1070a556c3003b4a7c7c10c98a5f61db4e91815de1075ec478e9487e76",
  sha256: "1f76943fabce08685efa15c2bde149479347bbeed2fd30ee7ba4bedf8aeba324",
  bytes: 4672599,
  loader_sha256:
    "17c82ae37c5d78ede061598dfa4d35dab2b1ff68b111058ddba6897b14e10349",
});

export function bodyPhysicsAsset(manifest) {
  if (
    manifest?.mujoco !== "3.14.0" ||
    manifest.physics?.sha256 !== BODY_PHYSICS_BUILD.reference_sha256
  )
    throw new Error(
      "This body model has not been checked with the faster physics build.",
    );
  return {
    file: "../../vendor/mujoco-body-v2/mujoco.wasm",
    bytes: BODY_PHYSICS_BUILD.bytes,
    sha256: BODY_PHYSICS_BUILD.sha256,
    download_bytes:
      manifest.download_bytes -
      manifest.physics.bytes +
      BODY_PHYSICS_BUILD.bytes,
  };
}
