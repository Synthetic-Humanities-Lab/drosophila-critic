// FLYBODY1: JSON metadata, then byte-shuffled little-endian float64 arrays.
// Decode to the existing playback shape. This changes storage, not the trajectory.
export function decodeBodyRecording(buffer) {
  const bytes = new Uint8Array(buffer),
    view = new DataView(buffer);
  const invalid = () => {
    throw new Error("The saved body recording is incomplete or invalid.");
  };
  if (
    bytes.length < 12 ||
    new TextDecoder().decode(bytes.subarray(0, 8)) !== "FLYBODY1"
  )
    invalid();
  const headerLength = view.getUint32(8, true);
  if (headerLength > bytes.length - 12) invalid();
  const { record, shapes } = JSON.parse(
    new TextDecoder().decode(bytes.subarray(12, 12 + headerLength)),
  );
  if (
    !Array.isArray(shapes) ||
    shapes.length !== 3 ||
    !Array.isArray(record?.body_names)
  )
    invalid();
  let offset = 12 + headerLength;
  const fields = ["time", "positions", "quaternions"];
  for (let field = 0; field < fields.length; field++) {
    const shape = shapes[field];
    if (
      !Array.isArray(shape) ||
      shape.length !== (field ? 3 : 1) ||
      shape.some((n) => !Number.isSafeInteger(n) || n <= 0) ||
      shape[0] !== shapes[0][0] ||
      (field &&
        (shape[1] !== record.body_names.length || shape[2] !== field + 2))
    )
      invalid();
    const count = shape.reduce((a, b) => a * b, 1);
    if (!Number.isSafeInteger(count) || count * 8 > bytes.length - offset)
      invalid();
    const numbers = new Float64Array(count),
      raw = new Uint8Array(numbers.buffer);
    for (let byte = 0; byte < 8; byte++)
      for (let i = 0; i < count; i++)
        raw[i * 8 + byte] = bytes[offset + byte * count + i];
    // The file is little-endian even on a big-endian host.
    if (new Uint8Array(new Uint16Array([1]).buffer)[0] !== 1) {
      const values = new DataView(numbers.buffer);
      for (let i = 0; i < count; i++)
        numbers[i] = values.getFloat64(i * 8, true);
    }
    for (const value of numbers) if (!Number.isFinite(value)) invalid();
    offset += count * 8;
    record[fields[field]] =
      field === 0
        ? numbers
        : Array.from({ length: shape[0] }, (_, frame) =>
            Array.from({ length: shape[1] }, (_, body) => {
              const start = (frame * shape[1] + body) * shape[2];
              return numbers.subarray(start, start + shape[2]);
            }),
          );
  }
  if (
    offset !== bytes.length ||
    ["states", "airborne", "commands"].some(
      (key) => record[key]?.length !== record.time.length,
    )
  )
    invalid();
  return record;
}
