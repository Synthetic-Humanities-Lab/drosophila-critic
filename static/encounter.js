import { RecordedAudio } from "./audio-player.js";
import { EncounterScene } from "./encounter-scene.js";
import { NeuralScene } from "./neural-scene.js";
import { selection, stanzaAtTime } from "./encounter-data.js";
import { binAt, responseExplanation, timeLabel } from "./playback-data.js";
import { RecordingPanel } from "./recording-panel.js";

const query = new URLSearchParams(location.search);
if (query.has("mode") || query.has("reading"))
  location.replace(`./archive.html${location.search}`);
const $ = (id) => document.getElementById(id),
  base = "./experiments/encounter-v2/";
const audio = new RecordedAudio(),
  stage = new EncounterScene($("stage")),
  neural = new NeuralScene($("neural-scene"));
let manifest,
  record,
  visitor,
  reader = selection(location.search).reader,
  stanza = selection(location.search).stanza,
  silent = query.get("silence") === "1",
  ready = false,
  generation = 0,
  group = 2,
  lastBin = -1,
  lastFrame = -1;
const cache = new Map();
const reducedMotion = matchMedia("(prefers-reduced-motion: reduce)");
function setFlashes(enabled) {
  neural.setFlashes(enabled);
  $("flashes").setAttribute("aria-pressed", String(enabled));
  $("flashes").textContent = enabled ? "Flashes on" : "Flashes off";
}
setFlashes(!reducedMotion.matches);
$("flashes").disabled = !neural.renderer;
reducedMotion.addEventListener("change", (e) => setFlashes(!e.matches));
$("flashes").onclick = () => setFlashes(!neural.flashes);
async function json(path) {
  if (!cache.has(path))
    cache.set(
      path,
      fetch(base + path)
        .then((r) => {
          if (!r.ok)
            throw new Error(
              `The recorded response could not load (${r.status}). Select the recording to retry.`,
            );
          return r.json();
        })
        .catch((e) => {
          cache.delete(path);
          throw e;
        }),
    );
  return cache.get(path);
}
function fail(error) {
  $("error").hidden = false;
  $("error").textContent = error.message || String(error);
}
function locationForSelection() {
  const url = new URL(location.href);
  url.search = "";
  url.hash = "";
  if (reader === "visitor") {
    url.searchParams.set("voice", "1");
    return url;
  }
  url.searchParams.set("reader", reader === "b" ? "human" : "robot");
  if (stanza !== null) url.searchParams.set("stanza", stanza + 1);
  if (silent) url.searchParams.set("silence", "1");
  return url;
}
function stop() {
  audio.pause();
  $("play").textContent = "PLAY ▶";
  if (ready) render();
}
const recording = new RecordingPanel({
  onStart: stop,
  onResult: async (result) => {
    visitor = result;
    manifest.groups.forEach((definition, g) => {
      definition.scale_max = Math.max(
        definition.scale_max,
        ...result.playback.activity.sound.maximum.map((row) => row[g]),
        ...result.playback.activity.silence.maximum.map((row) => row[g]),
      );
    });
    for (const field of ["waveform_rms", "displacement_nm"])
      manifest.input_scales[field] = Math.max(
        manifest.input_scales[field],
        ...result.playback.input[field].map((x) => x * 1.05),
      );
    await choose("visitor", { stanza: null, silent: false });
    $("status").textContent =
      "Your response is ready. Press play to watch the fly listen to your recording.";
    document
      .querySelector(".encounter")
      .scrollIntoView({ behavior: "auto", block: "start" });
    $("play").focus({ preventScroll: true });
  },
});
function openRecording() {
  stop();
  recording.preview.pause();
  $("your-voice").scrollIntoView({ behavior: "auto", block: "center" });
  if (!$("record-start").disabled && !$("record-inputs").hidden)
    $("record-start").focus({ preventScroll: true });
}
function explain() {
  const definition = manifest.groups[group],
    summary = record.summary[group];
  $("response-title").textContent = silent
    ? "What happens without the voice?"
    : definition.label;
  $("response-text").textContent = responseExplanation(
    summary,
    record.seeds.length,
    silent,
  );
  $("population-description").textContent = definition.description;
  const rows = [
    ["During the reading", summary.sound.mean],
    ["During silence", summary.silence.mean],
    ["Difference", summary.change.mean],
    ["Difference after the voice stops", summary.after_change.mean],
  ];
  const table = document.createElement("table");
  const caption = document.createElement("caption");
  caption.textContent = "Spikes per second, per cell";
  table.append(caption);
  for (const [label, value] of rows) {
    const tr = document.createElement("tr"),
      th = document.createElement("th"),
      td = document.createElement("td");
    th.scope = "row";
    th.textContent = label;
    td.textContent = value.toFixed(4);
    tr.append(th, td);
    table.append(tr);
  }
  $("measurements").replaceChildren(table);
  $("neural-caption").textContent =
    `12,000 sampled neurons at MaleCNS coordinates; flashes show one run (seed 1101). ${record.seeds.length === 1 ? "This visitor comparison has one sound run and one silence run." : "Traces show the average and full range of four runs, not a confidence interval."} ${reader === "visitor" && record.normalization.target_rms < 0.05 ? "This recording was set below the examples’ RMS level to avoid clipping; its own silence comparison remains valid." : ""}`;
  $("evidence-link").hidden = reader === "visitor";
  $("input-level").textContent = silent
    ? "No sound input"
    : "Modeled vibration strength";
}
async function choose(nextReader, options = {}) {
  if (!manifest || (nextReader === "visitor" && !visitor)) return;
  const token = ++generation;
  stop();
  recording.preview.pause();
  ready = false;
  neural.clear();
  record = null;
  $("trace").replaceChildren();
  $("input-trace").replaceChildren();
  $("rate").textContent = "—";
  $("input-level").textContent = "—";
  $("clock").textContent = "— / —";
  $("seek").disabled = true;
  $("seek").value = 0;
  $("input-trace").setAttribute("aria-label", "Sound input is loading.");
  $("stage-state").textContent = "LOADING";
  $("response-title").textContent = "Loading this response…";
  $("response-text").textContent = "";
  $("population-description").textContent = "";
  $("measurements").replaceChildren();
  reader = nextReader;
  silent = options.silent ?? false;
  stanza = options.stanza ?? null;
  lastBin = -1;
  lastFrame = -1;
  $("error").hidden = true;
  $("play").disabled = true;
  $("replay").disabled = true;
  $("play").textContent = "LOADING";
  document
    .querySelectorAll("[data-condition]")
    .forEach((b) =>
      b.setAttribute(
        "aria-pressed",
        String(b.dataset.condition === (silent ? "silence" : reader)),
      ),
    );
  $("share").hidden = reader === "visitor";
  const name =
    reader === "visitor"
      ? visitor.example
        ? "ROBOT / LOCAL PROCESSING TEST"
        : "YOUR VOICE"
      : reader === "b"
        ? "HUMAN / DENNY SAYERS"
        : "ROBOT / SYNTHETIC VOICE";
  $("speaker-tag").textContent = silent
    ? `SILENCE / ${reader === "visitor" ? "YOUR RECORDING" : reader === "b" ? "HUMAN LENGTH" : "ROBOT LENGTH"}`
    : name;
  $("trace-reading-label").textContent = silent
    ? "Reading hidden"
    : reader === "b"
      ? "Human"
      : reader === "a"
        ? "Robot"
        : "Your voice";
  $("condition-note").textContent =
    reader === "visitor"
      ? "Your recording · computed on this device"
      : "Recorded full-connectome simulation";
  stage.setReader(
    silent ? "silence" : reader === "visitor" && visitor.example ? "a" : reader,
  );
  $("status").textContent = "Loading this recording’s measured response…";
  history.replaceState(null, "", locationForSelection());
  try {
    let spatial;
    if (reader === "visitor") {
      record = visitor.playback;
      spatial = visitor.spatial[silent ? "silence" : "sound"];
      audio.setRecording({
        samples: visitor.samples,
        duration: record.playback_duration,
        silent,
      });
      $("credit").textContent = visitor.example
        ? "Kokoro af_sarah · public robot example, newly processed on this device"
        : "Your recording · processed locally · no automatic line timing";
    } else {
      const performance = manifest.performances[reader];
      const [nextRecord, nextSpatial] = await Promise.all([
        json(performance.playback),
        json(silent ? performance.silence_spatial : performance.spatial),
      ]);
      if (token !== generation) return;
      record = nextRecord;
      spatial = nextSpatial;
      if (silent)
        audio.setRecording({
          duration: record.playback_duration,
          silent: true,
        });
      else
        await audio.load(base + performance.audio, {
          duration: record.playback_duration,
        });
      $("credit").textContent = performance.credit;
    }
    if (token !== generation) return;
    audio.offset =
      options.time ??
      (stanza === null || reader === "visitor"
        ? 0
        : manifest.performances[reader].passages[stanza].start);
    neural.load(spatial);
    $("seek").max = record.playback_duration;
    $("seek").disabled = false;
    $("play").disabled = false;
    $("replay").disabled = false;
    $("play").textContent = silent ? "PLAY SILENCE ▶" : "PLAY ▶";
    $("poem-hint").textContent =
      reader === "visitor"
        ? "Read along in your own time. Your recording has no automatic line alignment."
        : "Select a stanza to listen from there.";
    document
      .querySelectorAll(".stanza")
      .forEach((b) =>
        b.setAttribute("aria-disabled", String(reader === "visitor")),
      );
    $("status").textContent = silent
      ? `No sound, for the same length as ${reader === "visitor" ? "your recording" : "the " + (reader === "b" ? "human" : "robot") + " reading"}. Neural activity continues.`
      : "Play from any stanza through to the end. Space: play or pause.";
    if (reader === "visitor" && !silent)
      $("status").textContent =
        "Your recording and its measured neural response. Space: play or pause.";
    ready = true;
    explain();
    render();
    if (options.autoplay) await toggle();
  } catch (e) {
    if (token === generation) {
      fail(e);
      $("play").textContent = "UNAVAILABLE";
      $("status").textContent =
        "Choose this recording again to retry, or select another example.";
      $("response-title").textContent = "Response unavailable";
      $("stage-state").textContent = "UNAVAILABLE";
      $("input-trace").setAttribute(
        "aria-label",
        "Sound input is unavailable.",
      );
    }
  }
}
function coordinates(values, xOf, yOf) {
  return values.map((v, i) => `${xOf(i)},${yOf(v)}`).join(" ");
}
function trace(time) {
  const rows = record.activity,
    max = Math.max(
      manifest.groups[group].scale_max,
      ...rows.sound.maximum.map((r) => r[group]),
      ...rows.silence.maximum.map((r) => r[group]),
      0.001,
    );
  const x = (i) =>
    ((record.start_time + i * record.bin_seconds) / record.playback_duration) *
    600;
  const y = (value) => 98 - (value / max) * 87;
  const start = Math.max(
    0,
    Math.round(-record.start_time / record.bin_seconds),
  );
  const path = (values) =>
    coordinates(
      values.slice(start).map((r) => r[group]),
      (i) => x(i + start),
      y,
    );
  const band = (condition) => {
    const upper = condition.maximum
      .slice(start)
      .map((r, i) => `${x(i + start)},${y(r[group])}`);
    const lower = condition.minimum
      .slice(start)
      .map((r, i) => `${x(i + start)},${y(r[group])}`)
      .reverse();
    return [...upper, ...lower].join(" ");
  };
  const cursor = Math.max(
    0,
    Math.min(600, (time / record.playback_duration) * 600),
  );
  $("trace").innerHTML =
    `<path d="M0 98H600" stroke="#435442"/><polygon points="${band(rows.silence)}" fill="#92a695" opacity=".16"/><polyline points="${path(rows.silence.mean)}" fill="none" stroke="#92a695" stroke-width="1.5"/>${silent ? "" : `<polygon points="${band(rows.sound)}" fill="#e9b765" opacity=".16"/><polyline points="${path(rows.sound.mean)}" fill="none" stroke="#e9b765" stroke-width="1.5"/>`}<path d="M${cursor} 6V101" stroke="#eff0d7" stroke-width="1"/><text x="2" y="9" fill="#93a28b" font-size="8">${max.toFixed(1)}</text>`;
  const index = binAt(record, time),
    rate = rows[silent ? "silence" : "sound"].mean[index][group];
  $("rate").textContent = `${rate.toFixed(2)} spikes/s/cell`;
  $("trace-reading-label").textContent = silent
    ? "Reading hidden"
    : reader === "visitor"
      ? "Your voice"
      : reader === "b"
        ? "Human"
        : "Robot";
}
function inputTrace(time) {
  const input = record.input;
  const line = (values, max, color) => {
    const points = coordinates(
      values,
      (i) => ((i * input.frame_seconds) / record.playback_duration) * 420,
      (value) => 97 - Math.min(1, value / max) * 80,
    );
    return `<polyline points="${points}" fill="none" stroke="${color}" stroke-width="1.3" opacity=".85"/>`;
  };
  const x = Math.min(420, (time / record.playback_duration) * 420);
  $("input-trace").innerHTML =
    `<path d="M0 97H420" stroke="#435442"/>${silent ? "" : line(input.waveform_rms, manifest.input_scales.waveform_rms, "#92a695") + line(input.displacement_nm, manifest.input_scales.displacement_nm, "#e9b765") + line(input.injection, manifest.input_scales.injection, "#c87951")}<path d="M${x} 6V101" stroke="#eff0d7"/>`;
}
function render() {
  if (!ready) return;
  const time = audio.currentTime,
    after = time >= record.audio_duration;
  $("clock").textContent =
    `${timeLabel(time)} / ${timeLabel(record.playback_duration)}`;
  $("seek").value = time;
  $("stage-state").textContent = audio.paused
    ? "PAUSED / READY"
    : silent
      ? "NO SOUND"
      : after
        ? "AFTER THE VOICE"
        : "LISTENING";
  const frame = Math.floor(time / record.input.frame_seconds);
  const displacement = silent ? 0 : record.input.displacement_nm[frame] || 0;
  stage.update(
    time,
    !audio.paused && !silent && !after,
    displacement,
    manifest.input_scales.displacement_nm,
  );
  neural.update(time);
  const index = binAt(record, time);
  if (index !== lastBin) {
    lastBin = index;
    trace(time);
    inputTrace(time);
  }
  if (frame !== lastFrame) {
    lastFrame = frame;
    $("input-level").textContent = silent
      ? "No sound input"
      : after
        ? "After the voice"
        : "Vibration strength";
    $("input-trace").setAttribute(
      "aria-label",
      `Sound amplitude and modeled antenna vibration. Current modeled displacement: ${displacement.toFixed(1)} nanometres; 20 millisecond envelope.`,
    );
  }
  document.querySelectorAll(".stanza").forEach((b, i) => {
    const passage =
      reader === "visitor" ? null : manifest.performances[reader].passages[i];
    b.classList.toggle(
      "active",
      !silent &&
        passage !== null &&
        time >= passage.start &&
        time < passage.end,
    );
    b.setAttribute("aria-pressed", String(stanza === i));
  });
}
async function toggle() {
  if (!ready) return;
  if (recording.recorder?.state === "recording") {
    $("status").textContent =
      "Stop the microphone recording before playing an example.";
    return;
  }
  recording.preview.pause();
  try {
    if (audio.paused) {
      if (audio.currentTime >= record.playback_duration - 0.01)
        audio.offset =
          reader === "visitor" || stanza === null
            ? 0
            : manifest.performances[reader].passages[stanza].start;
      await audio.play();
    } else audio.pause();
    $("play").textContent = audio.paused ? "PLAY ▶" : "PAUSE Ⅱ";
    render();
    $("status").textContent = silent
      ? "Silence is playing. Watch the activity that occurs without sound."
      : "The scene and measured response follow the audio. The final seconds show what happens after the voice stops.";
  } catch (e) {
    fail(e);
  }
}
$("play").onclick = toggle;
$("replay").onclick = async () => {
  if (ready) {
    stop();
    audio.offset =
      reader === "visitor" || stanza === null
        ? 0
        : manifest.performances[reader].passages[stanza].start;
    await toggle();
  }
};
$("seek").oninput = () => {
  if (ready) {
    const requestedTime = Number($("seek").value);
    stop();
    stanza = null;
    audio.currentTime = requestedTime;
    history.replaceState(null, "", locationForSelection());
    render();
  }
};
$("whole").onclick = () =>
  choose(reader, { silent, stanza: null, autoplay: true });
$("population").onchange = (e) => {
  group = Number(e.target.value);
  lastBin = -1;
  if (ready) {
    explain();
    render();
  }
};
$("camera").onclick = () => {
  const close = $("camera").getAttribute("aria-pressed") !== "true";
  $("camera").setAttribute("aria-pressed", String(close));
  $("camera").textContent = close ? "Show the reader ↙" : "Closer to the fly ↗";
  stage.setClose(close);
};
$("share").onclick = async () => {
  if (reader === "visitor") return;
  try {
    await navigator.clipboard.writeText(locationForSelection().href);
    $("status").textContent = "Link copied to this example and stanza.";
  } catch {
    $("status").textContent = `Share: ${locationForSelection().href}`;
  }
};
for (const button of document.querySelectorAll("[data-condition]"))
  button.onclick = () => {
    const condition = button.dataset.condition;
    if (condition === "visitor" && !visitor) {
      openRecording();
      return;
    }
    const autoplay = !audio.paused;
    if (condition === "silence") {
      choose(reader, {
        silent: true,
        stanza,
        time: audio.currentTime,
        autoplay,
      });
      return;
    }
    let passage = stanza;
    if (ready && reader !== "visitor" && condition !== "visitor")
      passage = stanzaAtTime(
        manifest,
        reader,
        Math.min(audio.currentTime, record.audio_duration),
      );
    choose(condition, { stanza: passage, silent: false, autoplay });
  };
addEventListener("keydown", (e) => {
  if (
    e.code === "Space" &&
    !["BUTTON", "INPUT", "TEXTAREA", "SELECT", "SUMMARY", "A"].includes(
      document.activeElement.tagName,
    )
  ) {
    e.preventDefault();
    toggle();
  }
});
audio.addEventListener("ended", () => {
  $("play").textContent = "REPLAY ▶";
  $("status").textContent =
    "Playback complete. Compare with silence, switch readers, or try your voice.";
  render();
});
audio.addEventListener("error", () =>
  fail(new Error("Playback failed. Select the recording again to retry.")),
);
function tick() {
  if (!audio.paused) render();
  requestAnimationFrame(tick);
}
addEventListener("pagehide", () => audio.pause());
requestAnimationFrame(tick);
try {
  manifest = await json("manifest.json");
  manifest.groups.forEach((g, i) => {
    const option = document.createElement("option");
    option.value = i;
    option.textContent = g.label;
    $("population").append(option);
  });
  $("population").value = group;
  manifest.poem
    .trim()
    .split(/\n\s*\n/)
    .forEach((text, i) => {
      const button = document.createElement("button");
      button.className = "stanza";
      button.type = "button";
      button.setAttribute(
        "aria-label",
        `Listen from stanza ${i + 1}: ${text.split("\n")[0]}`,
      );
      const number = document.createElement("small");
      number.textContent = `0${i + 1}`;
      button.append(number, document.createTextNode(text));
      button.onclick = () => {
        if (reader !== "visitor")
          choose(reader, { silent, stanza: i, autoplay: true });
      };
      $("poem").append(button);
    });
  await choose(reader, { silent, stanza });
  if (query.has("voice")) openRecording();
} catch (e) {
  fail(
    new Error(
      `${e.message} Reload the page to try loading the encounter again.`,
    ),
  );
  $("play").textContent = "UNAVAILABLE";
  $("status").textContent = "The encounter could not load. Reload to retry.";
  $("your-voice").hidden = true;
}
