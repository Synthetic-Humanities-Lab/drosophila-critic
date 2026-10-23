# Faster visitor calculation, 23 October 2026

Visitor audio stays on the device. This change speeds up the neural calculation
after a recording is selected; it does not send the recording to a server.
The connectome, receiver, random sequence, timestep, body physics, policies,
movement adapter and visual sampling are unchanged.

## Measured whole-workflow improvement

Two full runs of the public 26.165-second robot waveform per build through the
actual recording panel in iPhone 17 / iOS 26.5 Simulator, Safari 26.5, on the
available Mac. Trials ran sequentially with cached models and local delivery.

| Stage | Previous release, mean | Final version, mean |
| --- | ---: | ---: |
| Neural calculation | 40.41 s | 11.59 s |
| Body calculation, including initialization | 139.74 s | 139.76 s |
| Complete processing | **181.95 s** | **152.94 s** |

This removed **29.01 seconds (15.94%)** from the total wait; the neural stage was
71.33% shorter. Final total times were 153.041 and 152.845 seconds, versus 178.498
and 185.400 seconds before. Processed PCM, global/population counts, displayed
spikes, every recorded body position/orientation and all movement measurements
matched exactly. Cancellation completed in 1 ms in its separate test, released
the workers, and a subsequent full run completed. Completed results saved and
reloaded intact.

These are simulator-on-Mac measurements, not physical-iPhone timings or first
internet downloads. Body physics remains the largest cost. The same model files
and cached assets are reused, so installing this update does not require another
full model download. Evidence, including the rejected intermediate candidate,
is in [the comparison report](../experiments/visitor-speed-v1/comparison.json).

## Change

The original neural loop draws a PCG64 value for every neuron at every 20 ms
step: about 256 million draws for the public 26.165-second robot recording,
including baseline and decay. Its JavaScript implementation uses eight 16-bit
limbs to perform exact 128-bit arithmetic.

`scripts/neural_noise.wat` implements the same generator with WebAssembly's
64-bit integer operations. Two words hold the same 128-bit state. A batch still
draws one number per neuron, in the same order, and returns up to 32 threshold
decisions in a bit mask. JavaScript expands these into the same ordered neuron
indices. It does not skip draws,
approximate the distribution or substitute a different random generator.

`CompiledNoiseBrain` passes those indices to the existing `BrowserBrain.step`
supplied-noise interface. Synaptic propagation, the four accumulation
partitions, float32 rounding, voltage updates, hearing input, thresholding and
reset remain in the reference implementation. Body processing receives the
same captured spikes and uses the same physics binary as before.

The compiled module is **403 bytes**. It loads only when processing starts,
is checked against its SHA-256 digest before execution, and reserves **no
WebAssembly linear memory**. Its reusable JavaScript output buffer is 666,800
bytes for the full model. Its digest is recorded in each calculated
neural run. A missing or corrupt module produces a retryable error; it does not
silently change the simulation. Workers still release their heaps and terminate
on cancellation.

The saved silence artifact remains valid: its original source implementation is
unchanged, and the compiled implementation is checked against that implementation
and the independent Python fixtures. Historical results are not rewritten.

## Verification

- Four million random outputs, including the final 128-bit states, match the
  independent NumPy fixtures exactly across seeds 1101–1104.
- Batched thresholds match the JavaScript reference at probabilities 0, 0.024,
  0.5 and 1, including a carry-overflow case and resets.
- Supplied-noise and generated-noise neural steps match voltages and spikes.
- All 3,230 steps of the existing saved silence reproduce exact global counts,
  population counts and displayed spike identities under the compiled generator.
- The browser checks also compare complete recording responses, body poses and
  displayed measurements with the previous release, and check saved-result
  round-tripping and cancellation.

## Safari memory interaction

An earlier, discarded implementation wrote neuron indices into its own
WebAssembly linear memory. It reduced neural time but increased subsequent body
time in two full Safari trials, making the whole process slower. The final
module returns bit masks and has no linear memory, including no imported memory.
The test suite guards that boundary.

This design avoids a likely source of contention with the body engine's three
WASM memories. WebKit's [memory implementation and configured limits](https://github.com/WebKit/WebKit/blob/main/Source/JavaScriptCore/runtime/OptionsList.h)
provide a small pool of fast memories (three on the smaller-address-space
configuration, eight on the larger one). Exhausting it can change how memory
accesses are checked. This is a source-informed explanation, not an instrumented
diagnosis of that Safari build. Whole-workflow measurements determine whether
the final change is useful; the isolated random-generator benchmark is not the
release criterion.

## Reproduce

The small binary is committed so normal builds need no new dependency. To
rebuild it, use WABT 1.0.37's `wat2wasm`:

```sh
npm exec --yes --package=wabt@1.0.37 -- wat2wasm scripts/neural_noise.wat -o /tmp/neural-noise.wasm
cmp static/neural-noise.wasm /tmp/neural-noise.wasm
node --test tests/compiled-noise.test.mjs
node scripts/check_neural_noise.mjs
```

The last command requires the existing Python export in
`results/browser-benchmark`, checks compressed chunks and original array hashes,
and compares every voltage/spike fixture. It writes a numerical and timing
report to `output/visitor-speed/neural-equivalence.json`. CI rebuilds the binary
from the text source and compares its bytes. The unit suite also checks its
digest; changing it requires explicit requalification.

The largest remaining cost is MuJoCo body physics. This release retains its
20,000 integration steps per simulated second. First use still downloads the
brain and body assets; subsequent uses can read them from the browser cache.
Cached completed readings still reopen without either calculation.
