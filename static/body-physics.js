// This build changes compiler output, not the model's simulation contract.
// The original distribution remains the numerical reference for saved silence.
export const BODY_PHYSICS_BUILD = Object.freeze({
  version: "mujoco-3.14.0-strict-simd-v1",
  source_commit: "9ecbb9d7b5ee623f54745638d36799ff90e6f7cd",
  emscripten: "4.0.10",
  flags: "-O3 -msimd128 -ffp-contract=off; single threaded; no fast math",
  reference_sha256:
    "2d380f1070a556c3003b4a7c7c10c98a5f61db4e91815de1075ec478e9487e76",
  sha256: "30656f5922f4144b68e9b62c7d2b3d3a86fcb82890b3ab51e422f9f1538a7655",
  bytes: 4632279,
  loader_sha256:
    "64f5909a08be90cb958a715850e1d4680c696a5d6e6c285f0fba285a11b00071",
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
    file: "../../vendor/mujoco-simd/mujoco.wasm",
    bytes: BODY_PHYSICS_BUILD.bytes,
    sha256: BODY_PHYSICS_BUILD.sha256,
    download_bytes:
      manifest.download_bytes -
      manifest.physics.bytes +
      BODY_PHYSICS_BUILD.bytes,
  };
}
