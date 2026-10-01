import { RecordedAudio } from './audio-player.js';
import { EncounterScene } from './encounter-scene.js';
import { NeuralScene } from './neural-scene.js';
import {
  selection,
  playbackWindow,
  stanzaAtTime,
  traceIndex,
  signed,
} from './encounter-data.js';

// Preserve historical deep links without mixing experimental UI into the encounter.
if (
  new URLSearchParams(location.search).has('mode') ||
  new URLSearchParams(location.search).has('reading')
)
  location.replace(`./archive.html${location.search}`);
const $ = (id) => document.getElementById(id),
  base = './experiments/encounter-v1/';
const audio = new RecordedAudio(),
  stage = new EncounterScene($('stage')),
  neural = new NeuralScene($('neural-scene'));
let manifest,
  result,
  sensitivity,
  presentation,
  reader = selection(location.search).reader,
  stanza = selection(location.search).stanza,
  generation = 0,
  ready = false,
  lastBin = -1,
  tailStart = null;
const cache = new Map();
async function json(path) {
  const r = await fetch(base + path);
  if (!r.ok)
    throw new Error(
      `The recorded evidence could not load (${r.status}). Please retry.`,
    );
  return r.json();
}
function failure(error) {
  $('error').textContent = error.message || String(error);
  $('error').hidden = false;
  $('status').textContent =
    'Playback is unavailable. The method and evidence links remain accessible.';
}
function timeLabel(t) {
  return `${Math.floor(t / 60)}:${String(Math.floor(t % 60)).padStart(2, '0')}`;
}
function url() {
  const u = new URL(location.href);
  u.search = '';
  u.searchParams.set('reader', reader === 'a' ? 'robot' : 'human');
  if (stanza !== null) u.searchParams.set('stanza', stanza + 1);
  return u;
}
function reveal() {
  if (!result) return;
  $('outcome').hidden = false;
  $('reveal').hidden = true;
}
function comparison() {
  const passages = result.response.passage_comparison.passages;
  const p = stanza === null ? null : passages[stanza];
  const row = p
    ? p.populations[1].difference
    : result.response.differences[1].rate;
  $('response-text').textContent =
    `${p ? `Stanza ${stanza + 1}` : 'Across the full recordings'}: human minus robot, ${signed(row.mean)} spikes/second/neuron in direct auditory recipient cells, after matched silence is subtracted. This measures downstream activity, not an emotion.`;
  const robust = p
    ? sensitivity.passage_consistency[stanza]
    : Object.values(sensitivity.direct_difference_by_strength).every((x) =>
        x.values.every((v) => Math.sign(v) === Math.sign(row.mean)),
      );
  $('sensitivity-text').textContent = robust
    ? 'The direction survives all four seeds and all three tested receiver strengths' +
      (p ? ', including the tested boundary shifts.' : '.')
    : 'This contrast does not keep the same direction throughout the sensitivity checks.';
  $('reading-text').textContent = presentation.text;
}
async function choose(nextReader, nextStanza, autoplay = false) {
  if (!manifest) return;
  const token = ++generation;
  ready = false;
  tailStart = null;
  audio.pause();
  reader = nextReader;
  stanza = nextStanza;
  lastBin = -1;
  $('play').disabled = true;
  $('replay').disabled = true;
  $('play').textContent = 'LOADING';
  $('error').hidden = true;
  neural.clear();
  document
    .querySelectorAll('[data-reader]')
    .forEach((b) =>
      b.setAttribute('aria-pressed', String(b.dataset.reader === reader)),
    );
  stage.setReader(reader);
  $('speaker-tag').textContent =
    reader === 'a' ? 'ROBOT / SYNTHETIC VOICE' : 'HUMAN / DENNY SAYERS';
  $('credit').textContent = manifest.performances[reader].credit;
  $('status').textContent = 'Loading audio and its recorded neural response…';
  history.replaceState(null, '', url());
  comparison();
  try {
    const p = manifest.performances[reader];
    if (!cache.has(reader))
      cache.set(
        reader,
        json(p.spatial).catch((e) => {
          cache.delete(reader);
          throw e;
        }),
      );
    const [, spatial] = await Promise.all([
      audio.load(base + p.audio),
      cache.get(reader),
    ]);
    if (token !== generation) return;
    audio.duration = p.duration;
    audio.offset = playbackWindow(manifest, reader, stanza).start;
    neural.load(spatial);
    $('neural-caption').textContent =
      `${spatial.displayed_neurons.toLocaleString()} sampled neurons · seed ${spatial.seed}. Trace: mean of four runs; same scale for both readers.`;
    $('seek').max = p.duration;
    $('play').disabled = false;
    $('replay').disabled = false;
    $('play').textContent = 'LISTEN ▶';
    ready = true;
    $('status').textContent =
      'Recorded simulation · click a stanza to start there; playback continues to the end. Space: play/pause.';
    render();
    if (autoplay) await toggle();
  } catch (error) {
    if (token === generation) failure(error);
  }
}
function render() {
  if (!ready) return;
  $('stage-state').textContent = audio.paused
    ? 'READY TO LISTEN'
    : 'THE FLY IS LISTENING';
  let t = audio.currentTime;
  if (tailStart !== null) {
    t = audio.duration + Math.min(3.1, (performance.now() - tailStart) / 1000);
  }
  $('clock').textContent =
    `${timeLabel(Math.min(t, audio.duration))} / ${timeLabel(audio.duration)}`;
  $('seek').value = Math.min(t, audio.duration);
  stage.update(t, !audio.paused);
  neural.update(t);
  const timeline = result.response.performances[reader].timeline,
    index = traceIndex(timeline, t);
  if (index !== lastBin) {
    lastBin = index;
    $('rate').textContent = signed(timeline.mean[index][1], 2);
    const min = manifest.scales.downstream_min,
      max = manifest.scales.downstream_max,
      span = max - min || 1;
    const pts = timeline.mean
        .map(
          (row, i) =>
            `${(i / (timeline.mean.length - 1)) * 540},${105 - ((row[1] - min) / span) * 95}`,
        )
        .join(' '),
      y = 105 - ((0 - min) / span) * 95,
      x = (index / (timeline.mean.length - 1)) * 540;
    $('trace').innerHTML =
      `<path d="M0 ${y}H540" stroke="#67755e" stroke-dasharray="4 4"/><polyline points="${pts}" fill="none" stroke="#e9b765" stroke-width="1.6"/><path d="M${x} 5V110" stroke="#e4e7d0" opacity=".8"/>`;
  }
  document.querySelectorAll('.stanza').forEach((b, i) => {
    const w = manifest.performances[reader].passages[i];
    b.classList.toggle('active', t >= w.start && t < w.end);
    b.setAttribute('aria-pressed', String(stanza === i));
  });
}
async function toggle() {
  if (!ready) return;
  try {
    tailStart = null;
    if (audio.paused) {
      const w = playbackWindow(manifest, reader, stanza);
      if (audio.currentTime >= w.end) audio.offset = w.start;
      await audio.play(w.end);
    } else audio.pause();
    $('play').textContent = audio.paused ? 'LISTEN ▶' : 'PAUSE Ⅱ';
  } catch (e) {
    failure(e);
  }
}
$('play').onclick = toggle;
$('replay').onclick = async () => {
  if (!ready) return;
  audio.pause();
  audio.offset = playbackWindow(manifest, reader, stanza).start;
  await toggle();
};
$('seek').oninput = () => {
  if (!ready) return;
  audio.pause();
  tailStart = null;
  stanza = null;
  audio.currentTime = Number($('seek').value);
  $('play').textContent = 'LISTEN ▶';
  comparison();
  history.replaceState(null, '', url());
  render();
};
$('whole').onclick = () => choose(reader, null, true);
$('reveal').onclick = reveal;
$('share').onclick = async () => {
  try {
    await navigator.clipboard.writeText(url().href);
    $('status').textContent = 'Link copied to this reader and stanza.';
  } catch {
    $('status').textContent = `Share this link: ${url().href}`;
  }
};
for (const b of document.querySelectorAll('[data-reader]'))
  b.onclick = () => {
    let passage = stanza;
    if (audio.currentTime > 0 && manifest) {
      passage = stanzaAtTime(manifest, reader, audio.currentTime);
    }
    choose(b.dataset.reader, passage, !audio.paused);
  };
addEventListener('keydown', (e) => {
  if (
    e.code === 'Space' &&
    !['BUTTON', 'INPUT', 'TEXTAREA', 'SUMMARY', 'A'].includes(
      document.activeElement.tagName,
    )
  ) {
    e.preventDefault();
    toggle();
  }
});
audio.addEventListener('ended', () => {
  $('play').textContent = 'LISTEN ▶';
  reveal();
  tailStart = performance.now();
  $('status').textContent =
    'The voice has stopped. Replaying 3.1 seconds of recorded persistence.';
});
audio.addEventListener('error', () =>
  failure(new Error('Audio playback failed. Please select the reader again.')),
);
function tick() {
  render();
  requestAnimationFrame(tick);
}
requestAnimationFrame(tick);
try {
  manifest = await json('manifest.json');
  [result, sensitivity, presentation] = await Promise.all([
    json(manifest.result),
    json(manifest.sensitivity),
    json('presentation-reading.json'),
  ]);
  const stanzas = manifest.poem.trim().split(/\n\s*\n/);
  stanzas.forEach((text, i) => {
    const b = document.createElement('button');
    b.className = 'stanza';
    b.type = 'button';
    b.setAttribute(
      'aria-label',
      `Select stanza ${i + 1}: ${text.split('\n')[0]}`,
    );
    const small = document.createElement('small');
    small.textContent = `0${i + 1} / LISTEN FROM HERE`;
    b.append(small, document.createTextNode(text));
    b.onclick = () => choose(reader, i, true);
    $('poem').append(b);
  });
  await choose(reader, stanza);
} catch (error) {
  failure(error);
}
