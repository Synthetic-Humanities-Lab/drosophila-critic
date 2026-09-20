import test from 'node:test';
import assert from 'node:assert/strict';
import {RecordedAudio} from '../static/audio-player.js';

class FakeContext {
  currentTime = 0;
  destination = {};
  async resume() {}
  async decodeAudioData() { return {duration: 10}; }
  createBufferSource() {
    return {connect() {}, disconnect() {}, stop() {}, start(when, offset) { this.offset = offset; }};
  }
}
globalThis.AudioContext = FakeContext;

test('audio clock freezes on pause, resumes from offset, and seeks without a false end', async () => {
  const player = new RecordedAudio(); player.bytes = new ArrayBuffer(8);
  let ends = 0; player.addEventListener('ended', () => ends++);
  await player.play(); player.context.currentTime = 3;
  assert.equal(player.currentTime, 3);
  const firstSource = player.source;
  player.pause(); player.context.currentTime = 5;
  assert.equal(player.currentTime, 3); assert.equal(firstSource.onended, null);
  await player.play(); player.context.currentTime = 7;
  assert.equal(player.currentTime, 5);
  player.pause(); player.currentTime = 8;
  await player.play(); assert.equal(player.source.offset, 8);
  player.source.onended(); assert.equal(ends, 1); assert.equal(player.currentTime, 10);
  await player.play(); assert.equal(player.source.offset, 0);
});

test('leaving a reading during audio initialization cancels the pending playback', async () => {
  const player = new RecordedAudio(); player.bytes = new ArrayBuffer(8);
  const pending = player.play(); player.pause(); await pending;
  assert.equal(player.paused, true); assert.equal(player.source, null);
});

test('a failed replacement cannot replay the previous performance', async () => {
  const player = new RecordedAudio(); player.bytes = new ArrayBuffer(8);
  const fetchBefore = globalThis.fetch;
  globalThis.fetch = async () => ({ok: false});
  try {
    await assert.rejects(player.load('/missing.wav'));
    assert.equal(player.bytes, null);
    assert.equal(player.buffer, null);
    assert.equal(player.paused, true);
  } finally { globalThis.fetch = fetchBefore; }
});
