#include "wasm/codegen/generated/bindings.h"

namespace mujoco::wasm {
// BodyRuntime supplies an unchanged position/velocity state from mj_forward.
// All acceleration dynamics, constraints, sensors and integration still run.
void critic_step_after_forward(const MjModel& model, MjData& data) {
  const mjModel* m = model.get();
  mjData* d = data.get();
  mj_checkPos(m, d);
  mj_checkVel(m, d);
  // A numerical auto-reset invalidates the saved stages. Conservatively retain
  // full recomputation after any position/velocity warning, including old ones.
  if (d->warning[mjWARN_BADQPOS].number || d->warning[mjWARN_BADQVEL].number) {
    mj_forward(m, d);
  }
  // step2 subtracts the step1 timer count. We reused forward instead of calling
  // step1, so compensate to retain one counted step per integration step.
  d->timer[mjTIMER_STEP].number++;
  mj_step2(m, d);
}
EMSCRIPTEN_BINDINGS(critic_forward_reuse) {
  function("critic_step_after_forward", &critic_step_after_forward);
}
}
