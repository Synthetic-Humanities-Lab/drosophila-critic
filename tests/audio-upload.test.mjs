import test from 'node:test';
import assert from 'node:assert/strict';
import {prepareUpload} from '../static/audio-upload.js';

const file = new Blob([new Uint8Array([1, 2, 3])]);
const decoded = (channels, changes = {}) => ({
  duration: 1, sampleRate: 48000, length: channels[0].length,
  numberOfChannels: channels.length, getChannelData: i => channels[i], ...changes,
});

test('conversion saves a source hash and averages channels into PCM16 without normalizing', async () => {
  const result = await prepareUpload(file, {decodeAudioData: async () => decoded([[.5, -.5, 1], [.25, -.25, 1]])});
  assert.equal(result.hash, '039058c6f2c0cb492c533b0a4d14ef77cc0f78abccced5287d84a1a2011cfb81');
  const bytes = await result.blob.arrayBuffer(), view = new DataView(bytes);
  assert.equal(new TextDecoder().decode(bytes.slice(0, 4)), 'RIFF');
  assert.equal(view.getUint16(22, true), 1);
  assert.equal(view.getUint32(24, true), 48000);
  assert.equal(view.getUint32(40, true), 6);
  assert.equal(view.getInt16(44, true), 12288);
  assert.equal(view.getInt16(46, true), -12288);
  assert.equal(view.getInt16(48, true), 32767);
});

test('conversion rejects out-of-range, undecodable and overlong audio', async () => {
  await assert.rejects(prepareUpload(file, {decodeAudioData: async () => decoded([[1.1]])}), /exceeds PCM range/);
  await assert.rejects(prepareUpload(file, {decodeAudioData: async () => decoded([[NaN]])}), /exceeds PCM range/);
  await assert.rejects(prepareUpload(file, {decodeAudioData: async () => decoded([[0]], {duration:121})}), /120 seconds/);
  await assert.rejects(prepareUpload(file, {decodeAudioData: async () => { throw new Error(); }}), /cannot decode/);
});
