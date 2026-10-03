// PCG XSL RR 128/64. Eight base-65536 limbs keep every product exact in JS.
// SeedSequence initialization is exported from the pinned NumPy implementation.
const BASE = 65536;
function limbs(value) {
  let n = BigInt(value);
  const a = new Float64Array(8);
  for (let i = 0; i < 8; i++) {
    a[i] = Number(n & 65535n);
    n >>= 16n;
  }
  return a;
}
export class PCG64 {
  constructor(state) {
    this.state = limbs(state.state);
    this.increment = limbs(state.inc);
    this.multiplier = limbs('47026247687942121848144207491837523525');
    this.nextState = new Float64Array(8);
  }
  next() {
    const a = this.state,
      b = this.multiplier,
      out = this.nextState;
    let carry = 0;
    for (let k = 0; k < 8; k++) {
      let sum = carry + this.increment[k];
      for (let j = 0; j <= k; j++) sum += a[j] * b[k - j];
      // Sums are exact integers below 2^36. The mask retains their low 16 bits
      // like modulo BASE, without a floating-point remainder in this hot loop.
      out[k] = sum & 65535;
      carry = Math.floor(sum / BASE);
    }
    this.state = out;
    this.nextState = a;
    const lo = ((out[0] + out[1] * BASE) ^ (out[4] + out[5] * BASE)) >>> 0;
    const hi = ((out[2] + out[3] * BASE) ^ (out[6] + out[7] * BASE)) >>> 0;
    let rotation = out[7] >>> 10,
      l = lo,
      h = hi;
    if (rotation >= 32) {
      l = hi;
      h = lo;
      rotation -= 32;
    }
    if (rotation) {
      const nl = ((l >>> rotation) | (h << (32 - rotation))) >>> 0;
      h = ((h >>> rotation) | (l << (32 - rotation))) >>> 0;
      l = nl;
    }
    return (h * 2097152 + (l >>> 11)) / 9007199254740992;
  }
}
