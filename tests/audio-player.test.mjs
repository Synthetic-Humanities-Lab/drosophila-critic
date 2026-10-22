import test from "node:test";
import assert from "node:assert/strict";
import { gzipSync } from "node:zlib";
import { RecordedAudio } from "../static/audio-player.js";

class FakeContext {
  currentTime = 0;
  destination = {};
  async resume() {}
  async decodeAudioData() {
    return { duration: 10 };
  }
  createBufferSource() {
    return {
      connect() {},
      disconnect() {},
      stop() {},
      start(when, offset) {
        this.offset = offset;
      },
    };
  }
}
globalThis.AudioContext = FakeContext;

test("switching recordings reuses downloaded bytes and the decoded buffer", async () => {
  const player = new RecordedAudio(),
    previous = globalThis.fetch;
  let requests = 0,
    decodes = 0;
  globalThis.fetch = async () => {
    requests++;
    return new Response(new Uint8Array([1, 2, 3]));
  };
  player.context = new FakeContext();
  player.context.decodeAudioData = async () => {
    decodes++;
    return { duration: 10 };
  };
  try {
    await player.load("/a.wav");
    await player.play();
    player.pause();
    await player.load("/b.wav");
    await player.play();
    player.pause();
    await player.load("/a.wav");
    await player.play();
    player.pause();
    assert.equal(requests, 2);
    assert.equal(decodes, 2);
    assert.equal(player.recordings.size, 2);
    await player.load("/c.wav");
    assert.equal(player.recordings.size, 2);
  } finally {
    globalThis.fetch = previous;
  }
});

test("compressed waveforms reconstruct the exact original bytes", async () => {
  const bytes = new Uint8Array([82, 73, 70, 70, 0, 255, 1, 10]),
    previous = globalThis.fetch;
  globalThis.fetch = async () => new Response(gzipSync(bytes));
  try {
    const player = new RecordedAudio();
    await player.load("/recording.wav.gz");
    assert.deepEqual(new Uint8Array(player.bytes), bytes);
  } finally {
    globalThis.fetch = previous;
  }
});

test("failed audio downloads are evicted so retry really fetches again", async () => {
  const previous = globalThis.fetch;
  let calls = 0;
  globalThis.fetch = async () =>
    new Response(new Uint8Array([1]), { status: ++calls === 1 ? 503 : 200 });
  try {
    const player = new RecordedAudio();
    await assert.rejects(player.load("/retry.wav"), /could not be loaded/);
    await player.load("/retry.wav");
    assert.equal(calls, 2);
    assert.equal(player.bytes.byteLength, 1);
  } finally {
    globalThis.fetch = previous;
  }
});

test("audio clock freezes on pause, resumes from offset, and seeks without a false end", async () => {
  const player = new RecordedAudio();
  player.bytes = new ArrayBuffer(8);
  let ends = 0;
  player.addEventListener("ended", () => ends++);
  await player.play();
  player.context.currentTime = 3;
  assert.equal(player.currentTime, 3);
  const firstSource = player.source;
  player.pause();
  player.context.currentTime = 5;
  assert.equal(player.currentTime, 3);
  assert.equal(firstSource.onended, null);
  await player.play();
  player.context.currentTime = 7;
  assert.equal(player.currentTime, 5);
  player.pause();
  player.currentTime = 8;
  await player.play();
  assert.equal(player.source.offset, 8);
  player.source.onended();
  assert.equal(ends, 1);
  assert.equal(player.currentTime, 10);
  await player.play();
  assert.equal(player.source.offset, 0);
});

test("leaving a reading during audio initialization cancels the pending playback", async () => {
  const player = new RecordedAudio();
  player.bytes = new ArrayBuffer(8);
  const pending = player.play();
  player.pause();
  await pending;
  assert.equal(player.paused, true);
  assert.equal(player.source, null);
});

test("a failed replacement cannot replay the previous performance", async () => {
  const player = new RecordedAudio();
  player.bytes = new ArrayBuffer(8);
  const fetchBefore = globalThis.fetch;
  globalThis.fetch = async () => ({ ok: false });
  try {
    await assert.rejects(player.load("/missing.wav"));
    assert.equal(player.bytes, null);
    assert.equal(player.buffer, null);
    assert.equal(player.paused, true);
  } finally {
    globalThis.fetch = fetchBefore;
  }
});

test("a slow superseded download cannot replace the current recording", async () => {
  const player = new RecordedAudio();
  const originalFetch = globalThis.fetch;
  let release;
  globalThis.fetch = async (url) => ({
    ok: true,
    arrayBuffer: () =>
      url === "/old.wav"
        ? new Promise((resolve) => {
            release = resolve;
          })
        : Promise.resolve(new Uint8Array([2]).buffer),
  });
  try {
    const old = player.load("/old.wav");
    await Promise.resolve();
    await player.load("/new.wav");
    release(new Uint8Array([1]).buffer);
    await old;
    assert.equal(new Uint8Array(player.bytes)[0], 2);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("a superseded decode cannot overwrite the next recording buffer", async () => {
  const player = new RecordedAudio();
  player.bytes = new ArrayBuffer(8);
  const context = new FakeContext();
  player.context = context;
  let release;
  context.decodeAudioData = () =>
    new Promise((resolve) => {
      release = resolve;
    });
  const first = player.play();
  await Promise.resolve();
  player.pause();
  player.generation++;
  player.buffer = { duration: 20 };
  release({ duration: 10 });
  await first;
  assert.equal(player.buffer.duration, 20);
  assert.equal(player.paused, true);
});

test("a passage schedules its exact stop on the audio clock", async () => {
  const player = new RecordedAudio();
  player.bytes = new ArrayBuffer(8);
  player.duration = 10;
  const context = new FakeContext();
  player.context = context;
  let startArgs;
  context.createBufferSource = () => ({
    connect() {},
    disconnect() {},
    stop() {},
    start(...args) {
      startArgs = args;
    },
  });
  player.currentTime = 2;
  await player.play(4);
  assert.deepEqual(startArgs, [0, 2, 2]);
  context.currentTime = 8;
  assert.equal(player.currentTime, 4);
  player.source.onended();
  assert.equal(player.currentTime, 4);
  assert.equal(player.paused, true);
  await player.play();
  assert.deepEqual(startArgs, [0, 4, 6]);
});
