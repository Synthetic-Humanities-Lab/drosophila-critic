export const LOCAL_ENGINE_VERSION = "local-listening-v4";
export const LOCAL_SEED = 1101;
export const BASELINE_STEPS = 75;
export const POST_STEPS = 150;

export function stableJSON(value) {
  return JSON.stringify(value, (_, item) =>
    item && typeof item === "object" && !Array.isArray(item)
      ? Object.fromEntries(
          Object.keys(item)
            .sort()
            .map((key) => [key, item[key]]),
        )
      : item,
  );
}

export function simulationContract(model, motor, body) {
  return {
    engine: LOCAL_ENGINE_VERSION,
    seed: LOCAL_SEED,
    baseline_steps: BASELINE_STEPS,
    post_steps: POST_STEPS,
    model: model.version,
    neurons: model.neurons,
    configuration: model.configuration,
    arrays: Object.fromEntries(
      Object.entries(model.arrays).map(([key, spec]) => [key, spec.sha256]),
    ),
    random_state: model.random_states[String(LOCAL_SEED)],
    receiver: model.receiver,
    groups: { ...model.groups, ...motor.groups },
    display_neurons: model.display_neurons,
    body,
  };
}
