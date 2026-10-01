// Browser decoding boundary: PCM only is uploaded to the simulator.
export async function prepareUpload(file, context) {
  if (!file || file.size > 64_000_000)
    throw new Error('Choose an audio file below 64 MB for each performance.');
  const bytes = await file.arrayBuffer();
  const digest = await crypto.subtle.digest('SHA-256', bytes);
  const hash = [...new Uint8Array(digest)]
    .map((b) => b.toString(16).padStart(2, '0'))
    .join('');
  let decoded;
  try {
    decoded = await context.decodeAudioData(bytes.slice(0));
  } catch {
    throw new Error(
      'This browser cannot decode one recording. Export it as a WAV or MP3 and try again.',
    );
  }
  if (decoded.duration < 1 || decoded.duration > 120)
    throw new Error('Each recording must be between 1 and 120 seconds.');
  if (decoded.sampleRate !== 48000)
    throw new Error(
      'This browser did not provide 48 kHz decoding. Use PCM16 WAV through the API.',
    );
  const wav = new ArrayBuffer(44 + decoded.length * 2),
    view = new DataView(wav);
  const text = (offset, value) =>
    [...value].forEach((c, i) => view.setUint8(offset + i, c.charCodeAt(0)));
  text(0, 'RIFF');
  view.setUint32(4, wav.byteLength - 8, true);
  text(8, 'WAVEfmt ');
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, 1, true);
  view.setUint32(24, 48000, true);
  view.setUint32(28, 96000, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  text(36, 'data');
  view.setUint32(40, decoded.length * 2, true);
  const channels = Array.from({ length: decoded.numberOfChannels }, (_, i) =>
    decoded.getChannelData(i),
  );
  for (let i = 0; i < decoded.length; i++) {
    const value =
      channels.reduce((sum, channel) => sum + channel[i], 0) / channels.length;
    if (!Number.isFinite(value) || Math.abs(value) > 1)
      throw new Error(
        'Decoded audio exceeds PCM range. Export a peak-safe WAV; the app will not silently clip it.',
      );
    view.setInt16(
      44 + 2 * i,
      Math.max(-32768, Math.min(32767, Math.round(value * 32768))),
      true,
    );
  }
  return { blob: new Blob([wav], { type: 'audio/wav' }), hash };
}
