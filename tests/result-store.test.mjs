import test from "node:test";
import assert from "node:assert/strict";
import { ResultStore } from "../static/result-store.js";
import { RecordingPanel } from "../static/recording-panel.js";

test("unavailable device storage reports failure instead of claiming a reading was saved", async () => {
  await assert.rejects(
    new ResultStore(null).save({ evidence: { audio: { duration: 1 } } }, {}),
    /unavailable/,
  );
  await assert.rejects(new ResultStore(null).info(), /unavailable/);
});

test("a blocked open closes a late database connection", async () => {
  let request,
    closed = false;
  const store = new ResultStore({
    open() {
      request = {};
      return request;
    },
  });
  const pending = store.info();
  request.onblocked();
  await assert.rejects(pending, /blocking/);
  request.result = {
    close() {
      closed = true;
    },
  };
  request.onsuccess();
  assert.equal(closed, true);
});

test("reopening plays the saved result without invoking simulation", async () => {
  let played;
  const result = { name: "My reading", evidence: { model: "prior-version" } };
  const fields = new Map();
  const panel = Object.assign(Object.create(RecordingPanel.prototype), {
    generation: 0,
    preview: { pause() {} },
    onStart() {},
    onResult: async (value) => {
      played = value;
    },
    store: { load: async () => ({ result, original: { name: "original" } }) },
    session: {
      process() {
        assert.fail("must not recompute a saved result");
      },
    },
    $(id) {
      if (!fields.has(id)) fields.set(id, { setAttribute() {} });
      return fields.get(id);
    },
  });
  await panel.reopen();
  assert.equal(played, result);
  assert.equal(panel.busy, false);
  assert.match(fields.get("record-status").textContent, /ready to play/);
});

test("cancelling a slow saved-result load prevents a late replay", async () => {
  let finish,
    played = false;
  const panel = Object.assign(Object.create(RecordingPanel.prototype), {
    generation: 0,
    onStart() {},
    onResult() {
      played = true;
    },
    store: {
      load: () =>
        new Promise((resolve) => {
          finish = resolve;
        }),
    },
    session: { cancel() {} },
    preview: { pause() {} },
    $() {
      return { setAttribute() {} };
    },
  });
  const pending = panel.reopen();
  panel.cancel();
  finish({ result: {}, original: {} });
  await pending;
  assert.equal(played, false);
  assert.equal(panel.busy, false);
});

test("a full storage device leaves the completed replay usable and explains how to keep it", async () => {
  const fields = new Map();
  let played = false;
  const result = { evidence: {}, samples: new Float64Array([0]) };
  const panel = Object.assign(Object.create(RecordingPanel.prototype), {
    generation: 0,
    draft: { name: "voice.wav", samples: result.samples, hash: "audio" },
    preview: { pause() {} },
    onStart() {},
    keepAwake() {},
    onResult() {
      played = true;
    },
    session: { process: async () => result },
    store: {
      save: async () => {
        throw new DOMException("Full", "QuotaExceededError");
      },
    },
    $(id) {
      if (!fields.has(id)) fields.set(id, { setAttribute() {} });
      return fields.get(id);
    },
  });
  await panel.process();
  assert.equal(played, true);
  assert.equal(panel.result, result);
  assert.equal(panel.busy, false);
  assert.equal(fields.get("voice-downloads").hidden, false);
  assert.match(fields.get("storage-note").textContent, /could not keep a copy/);
  assert.equal(fields.get("record-error").hidden, true);
});
