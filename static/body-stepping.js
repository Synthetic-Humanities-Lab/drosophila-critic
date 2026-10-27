export const BODY_STEPPING_VERSION = "body-forward-reuse-v1";

// Only for BodyRuntime: between its final forward() and the next step(), it
// changes controls and timestep, never positions, velocities or model geometry.
// Retain that forward pass's position/velocity stages for the first substep.
export function bodyStepping(mj) {
  let model = null,
    data = null,
    timestep = null;
  const runtime = {
    MjModel: mj.MjModel,
    MjData: mj.MjData,
    mj_forward(m, d) {
      runtime.mj_step = mj.mj_step;
      model = data = null;
      mj.mj_forward(m, d);
      model = m;
      data = d;
      timestep = m.opt.timestep;
      runtime.mj_step = stepAfterForward;
    },
    mj_step: mj.mj_step,
  };
  function stepAfterForward(m, d) {
    // Keep the remaining 20 kHz substeps on the direct native call. Only the
    // first substep after a forward pass needs the reuse checks.
    runtime.mj_step = mj.mj_step;
    const matching = model === m && data === d;
    model = data = null;
    const opt = matching ? m.opt : null;
    if (opt && opt.timestep === timestep && opt.integrator === 0) {
      mj.critic_step_after_forward(m, d);
    } else {
      mj.mj_step(m, d);
    }
  }
  return runtime;
}
