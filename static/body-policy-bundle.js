import { BodyPolicy } from "./body-policy.js";

// Walking and flight inference are serial in one body worker. Pack their exact
// weights into one WASM memory and reuse the same scratch buffers between calls.
export function createBodyPolicies(metadata, weights, kernel) {
  const flightOffset = (weights.walking.byteLength + 15) & ~15;
  const total = flightOffset + weights.flight.byteLength;
  if (((total + 15) & ~15) + 8192 > kernel.memory.buffer.byteLength)
    throw new Error("The body policies exceed their allocated memory.");
  const packed = new Uint8Array(total);
  packed.set(new Uint8Array(weights.walking));
  packed.set(new Uint8Array(weights.flight), flightOffset);
  const flight = {
    ...metadata.flight,
    arrays: metadata.flight.arrays.map((array) => ({
      ...array,
      offset: array.offset + flightOffset,
    })),
  };
  return {
    walking: new BodyPolicy(metadata.walking, packed.buffer, kernel),
    flight: new BodyPolicy(flight, packed.buffer, kernel),
  };
}
