import { RecordedAudio } from './audio-player.js';
import { FlyScene } from './fly-scene.js';
import { NeuralScene } from './neural-scene.js';

const base = new URL('.', import.meta.url);
const site = await fetch(new URL('site-config.json', base), {cache: 'no-cache'}).then(r => r.json());
const recorded = site.mode === 'recorded';
function resource(path) {
  if (recorded && path.startsWith('/api/readings/')) {
    const parts = path.slice('/api/readings/'.length).split('/');
    path = `recordings/${parts[0]}/${parts[1] || 'status.json'}`;
  }
  return new URL(path.replace(/^\//, ''), base).href;
}

const $ = (id) => document.getElementById(id);
const audio = new RecordedAudio();
const flyScene = new FlyScene($('fly-scene'));
const neuralScene = new NeuralScene($('neural-scene'));
let playPending = false;
let affectSelected = false;
$('play').addEventListener('click', async () => {
  if (playPending) return;
  if (!audio.paused) { audio.pause(); return; }
  playPending = true; $('play').disabled = true;
  try { await audio.play(); } catch (e) { error(`Audio playback failed: ${e.message}. The WAV download remains available.`); }
  finally { playPending = false; $('play').disabled = false; }
});
$('seek').addEventListener('input', () => { audio.currentTime = Number($('seek').value); updateReplay(audio.currentTime); });
$('view-toggle').addEventListener('click', () => {
  const dorsal = $('view-toggle').getAttribute('aria-pressed') !== 'true';
  $('view-toggle').setAttribute('aria-pressed', String(dorsal));
  $('view-toggle').textContent = dorsal ? 'Oblique view ↗' : 'Dorsal view ↗';
  flyScene.setView(dorsal);
});
let result = null;
let chartRange = null;
let tailStarted = null;
let lastFrame = -1;
let lastLine = null;
let sourceText = '';
let polling = false;
const signed = (n, digits = 3) => `${n >= 0 ? '+' : '−'}${Math.abs(n).toFixed(digits)}`;
const stamp = (n) => `${String(Math.floor(Math.max(0, n) / 60)).padStart(2, '0')}:${(Math.max(0, n) % 60).toFixed(2).padStart(5, '0')}`;

async function request(path, options) {
  const response = await fetch(resource(path), {cache: 'no-cache', ...options});
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(typeof body.detail === 'string' ? body.detail : `Request failed (${response.status}).`);
  }
  return response.json();
}
function error(message) {
  $('error').textContent = message;
  $('error').hidden = false;
}
function element(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
}
function updateCount() {
  $('count').textContent = `${$('poem').value.length.toLocaleString()} / 2,000`;
  if ($('poem').value !== sourceText) $('source').replaceChildren();
}
$('poem').addEventListener('input', updateCount);
async function loadExample() {
  try {
    const example = recorded ? site.example : await request('/api/example');
    $('poem').value = example.poem;
    sourceText = example.poem;
    const link = element('a', `${example.title} — ${example.author} · public domain`);
    link.href = example.source;
    link.target = '_blank';
    link.rel = 'noopener';
    $('source').replaceChildren(link);
    updateCount();
  } catch (e) { error(e.message); }
}
$('example').addEventListener('click', loadExample);

const descriptions = {
  'QUEUED': 'Preparing the local instrument.',
  'LOADING CONNECTOME': 'Loading and verifying the full MaleCNS network. The first run also compiles the simulator.',
  'SYNTHESIZING VOICE': 'One fixed local Kokoro neural voice. Identical voice, speed and processing for every poem.',
  'TRANSDUCING AUDIO': 'Normalizing PCM and measuring its 20 ms RMS envelope.',
  'READING': 'Running the complete frozen connectome: silence baseline, auditory input, then decay.',
  'BENCHMARKING SILENCE': 'Repeating the full duration with the same reset and noise seed, but zero auditory input.',
  'MEASURING RESPONSE': 'Counting recorded spikes and calculating changes from baseline.',
  'INTERPRETING RESPONSE': 'Composing a reading from measurements alone. No poem text is provided.'
};
async function poll(id) {
  polling = true;
  try {
    while (polling) {
      const state = await request(`/api/readings/${id}`);
      if (state.status === 'failed') throw new Error(state.error);
      if (state.status === 'complete') {
        await loadResult(id);
        return;
      }
      $('stage').textContent = state.stage;
      $('progress-detail').textContent = descriptions[state.stage] || 'Preparing recorded playback.';
      if (['READING', 'BENCHMARKING SILENCE'].includes(state.stage)) {
        $('progress').value = state.fraction;
        $('progress-number').textContent = `${Math.round(state.fraction * 100)}% OF TIMESTEPS`;
      } else {
        $('progress').removeAttribute('value');
        $('progress-number').textContent = '';
      }
      await new Promise(resolve => setTimeout(resolve, 600));
    }
  } finally { polling = false; }
}
$('submit').addEventListener('click', async () => {
  if (!$('poem').value.trim()) { error('Place a poem in the text area first.'); $('poem').focus(); return; }
  $('error').hidden = true;
  $('submit').disabled = true;
  $('entry').hidden = true;
  $('progress-panel').hidden = false;
  try {
    const response = await request('/api/readings', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({poem: $('poem').value})
    });
    history.replaceState(null, '', `?reading=${response.id}`);
    await poll(response.id);
  } catch (e) {
    loadFailure(e);
  } finally { $('submit').disabled = false; }
});

function svgNode(tag, attributes, text) {
  const node = document.createElementNS('http://www.w3.org/2000/svg', tag);
  for (const [key, value] of Object.entries(attributes)) node.setAttribute(key, value);
  if (text !== undefined) node.textContent = text;
  return node;
}
function drawCharts() {
  const rows = result.timeline.filter(row => row.phase !== 'warmup');
  const minTime = rows[0].time;
  const maxTime = result.response.global.audio_window_seconds + result.response.global.tail_observed_seconds;
  chartRange = {minTime, maxTime};
  const x = t => 38 + (t - minTime) / (maxTime - minTime) * 590;
  const base = result.response.baseline.hz_per_neuron;
  const band = result.response.measurement_rules.transition_band_hz_per_neuron;
  const controls = (result.benchmark?.timeline || []).filter(row => row.time >= minTime);
  const values = [...rows.map(row => row.smoothed_hz_per_neuron), ...controls.map(row => row.silence_hz_per_neuron)];
  const low = Math.max(0, Math.min(...values, base - band) - 0.04);
  const high = Math.max(...values, base + band) + 0.04;
  const y = v => 156 - (v - low) / Math.max(high - low, 0.01) * 139;
  const neural = $('neural-chart');
  neural.replaceChildren();
  neural.append(svgNode('rect', {x: 38, y: y(base + band), width: 590, height: y(base - band) - y(base + band), class: 'chart-band'}));
  neural.append(svgNode('line', {x1: 38, x2: 628, y1: y(base), y2: y(base), class: 'baseline'}));
  for (const value of [low, base, high]) neural.append(svgNode('text', {x: 0, y: y(value) + 3, class: 'axis-text'}, value.toFixed(2)));
  neural.append(svgNode('path', {d: rows.map((row, i) => `${i ? 'L' : 'M'}${x(row.time).toFixed(2)},${y(row.smoothed_hz_per_neuron).toFixed(2)}`).join(' '), class: 'chart-path'}));
  if (controls.length) {
    neural.append(svgNode('path', {d: controls.filter(row => row.time >= minTime).map((row,i) => `${i?'L':'M'}${x(row.time).toFixed(2)},${y(row.silence_hz_per_neuron).toFixed(2)}`).join(' '), class:'control-path'}));
    $('trace-legend').textContent='— poem · ┄ matched silence';
  }
  for (const event of (result.benchmark ? [{kind:'peak poem-minus-silence separation', time:result.benchmark.global.peak_time}] : result.response.events)) {
    const marker = svgNode('circle', {cx: x(event.time), cy: 8, r: event.kind === 'peak perturbation' ? 3 : 1.7, class: 'event-mark'});
    marker.append(svgNode('title', {}, `${event.kind} at ${event.time.toFixed(2)} s`));
    neural.append(marker);
  }
  for (const [time, label, anchor] of [[0, 'voice begins', 'start'], [result.audio.duration, 'voice ends', 'end']]) {
    neural.append(svgNode('text', {x: x(time), y: 181, class: 'axis-text', 'text-anchor': anchor}, label));
  }
  neural.append(svgNode('line', {id: 'neural-cursor', x1: x(0), x2: x(0), y1: 10, y2: 162, class: 'cursor'}));
  const envelope = $('audio-chart');
  envelope.replaceChildren();
  const maxRms = Math.max(...rows.map(row => row.rms), 0.01);
  const ey = v => 60 - v / maxRms * 48;
  envelope.append(svgNode('path', {d: `M${x(minTime)},60 ` + rows.map(row => `L${x(row.time).toFixed(2)},${ey(row.rms).toFixed(2)}`).join(' ') + ` L${x(maxTime)},60 Z`, class: 'envelope-path'}));
  envelope.append(svgNode('text', {x: 0, y: 15, class: 'axis-text'}, maxRms.toFixed(2)));
  envelope.append(svgNode('text', {x: x(0), y: 80, class: 'axis-text'}, '0 s'));
  envelope.append(svgNode('text', {x: x(maxTime), y: 80, class: 'axis-text', 'text-anchor': 'end'}, `${maxTime.toFixed(1)} s`));
  envelope.append(svgNode('line', {id: 'audio-cursor', x1: x(0), x2: x(0), y1: 8, y2: 63, class: 'cursor'}));
}

function table(id, rows, limit) {
  $(id).replaceChildren(...rows.slice(0, limit).map(row => {
    const tr = element('tr');
    for (const text of [row.name, row.neurons, row.available === false ? 'unavailable' : row.audio_hz_per_neuron.toFixed(2), row.available === false ? '—' : signed(row.delta_hz_per_neuron, 2)]) tr.append(element('td', text));
    return tr;
  }));
}
function populateResults() {
  const response = result.response;
  const g = response.global;
  const metrics = [
    ['BASELINE', response.baseline.hz_per_neuron.toFixed(3), 'Hz/neuron · 1 s of silence'],
    ['DURING THE VOICE', g.during_hz_per_neuron.toFixed(3), `${signed(g.deviation_hz_per_neuron)} from baseline`],
    ['PEAK VS INITIAL BASELINE', signed(g.peak_perturbation_hz_per_neuron), `Hz/neuron at ${g.peak_time.toFixed(2)} s`],
    ['TAIL VS INITIAL BASELINE', signed(g.tail_deviation_hz_per_neuron), 'mean Δ Hz/neuron · 1 s tail'],
    ['RETURN TO BAND', g.recovery_censored ? 'Unobserved' : `${g.recovery_seconds_after_audio_window.toFixed(2)} s`, 'start of first 200 ms within baseline band'],
    ['TRANSITIONS', String(response.events.filter(e => e.kind === 'activity transition').length), 'sustained crossings of the descriptive band'],
    ['AUDIO DURATION', `${result.audio.duration.toFixed(2)} s`, `${result.audio.voice} · ${result.audio.provider}`],
    ['NETWORK', result.fly.neurons.toLocaleString(), `${result.fly.connections.toLocaleString()} connections · frozen`]
  ];
  if (result.benchmark) {
    const b=result.benchmark.global;
    metrics.unshift(['MATCHED SILENCE', b.silence_hz_per_neuron.toFixed(3), 'Hz/neuron · equal duration'], ['POEM − SILENCE', signed(b.delta_hz_per_neuron), 'mean Hz/neuron · same noise seed']);
    $('benchmark-panel').hidden=false;
    $('benchmark-verdict').textContent=`With the poem: ${b.poem_hz_per_neuron.toFixed(3)} Hz/neuron. With silence: ${b.silence_hz_per_neuron.toFixed(3)}. The difference is ${signed(b.delta_hz_per_neuron)}. The strongest global separation occurs at ${b.peak_time.toFixed(2)} s (${signed(b.peak_delta_hz_per_neuron)} Hz/neuron).`;
  } else $('benchmark-panel').hidden=true;
  $('metrics').replaceChildren(...metrics.map(([label, value, note]) => {
    const node = element('div', undefined, 'metric');
    node.append(element('div', label, 'metric-label'), element('div', value, 'metric-value'), element('div', note, 'metric-note'));
    return node;
  }));
  table('population-table', result.benchmark?.populations || response.populations, 10);
  table('group-table', result.benchmark?.monitored_populations || response.monitored_populations, 10);
  table('activity-table', response.strongest_activity, 10);
  $('events').replaceChildren(...response.events.map(event => element('p', `${event.time.toFixed(2)} s${event.line ? ` · line ${event.line}` : ''} — ${event.kind}${event.state ? `: ${event.state}` : ''} (${signed(event.delta_hz_per_neuron)} Hz/neuron)`)));
  $('reading-text').textContent = result.reading.text;
  $('affect-lens').disabled = !result.reading.affect;
  $('affect-text').textContent = result.reading.affect?.text || '';
  $('affect-scope').textContent = result.reading.affect?.scope || '';
  $('affect-sources').replaceChildren(...(result.reading.affect?.sources || []).map(source=>{
    const link=element('a',source.title+' ↗');link.href=source.url;link.target='_blank';link.rel='noopener';return link;
  }));
  selectLens(affectSelected && Boolean(result.reading.affect));
  $('circuit-meanings').replaceChildren(...(result.reading.functional_notes || []).map(note => {
    const card=element('article', undefined, 'circuit-card');
    card.append(element('h4',note.label),element('span',note.population,'circuit-id'),element('p',note.role),element('p',note.measurement,'circuit-measurement'),element('p',note.inference),element('p',note.limit,'small'));
    const link=element('a','Basis for this circuit association ↗');
    link.href=note.source;link.target='_blank';link.rel='noopener';card.append(link);
    return card;
  }));
  if (!result.reading.functional_notes?.length) $('circuit-meanings').textContent='This record has no mapped functional interpretation. New paired readings include source-linked circuit explanations.';
  $('reading-input').textContent = JSON.stringify(result.reading.input_summary, null, 2);
  $('provenance-json').textContent = JSON.stringify({poem_id: result.poem_id, audio: result.audio, fly: result.fly, encoder: result.encoder, provenance: result.provenance}, null, 2);
  $('downloads').replaceChildren(...[
    ...(result.benchmark ? [['benchmark.json','Matched silence comparison'], ['silence-spikes.npz','All silence spike events'], ['silence-populations.npz','Silence population counts'], ['neural-display.json','Spatial display evidence']] : []),
    ...(result.audio.provider === 'librivox-recording' ? [['recording-source.json','Recording source and edit bounds'],['original.mp3','Original LibriVox recording']] : []),
    ['result.json', 'Full response JSON'], ['audio.wav', 'Voice / WAV'], ['encoding.json', 'Every auditory injection'],
    ['reading-input.json', 'Interpretation input'], ['spikes.npz', 'All spike events'],
    ['populations.npz', 'Population counts'], ['population_metrics.json', 'All population metrics'], ['METHOD.md', 'Method snapshot']
  ].map(([file, label]) => {
    const link = element('a', `${label} ↗`);
    link.href = resource(`/api/readings/${result.id}/${file}`); link.target = '_blank'; link.rel = 'noopener';
    return link;
  }));
}

function loadFailure(e) {
  result = null; chartRange = null; audio.pause();
  $('replay').hidden = true; $('results').hidden = true; $('progress-panel').hidden = true;
  $('entry').hidden = recorded;
  error(`The saved performance could not be displayed. Reload the page to retry. ${e.message}`);
  for (const button of $('performance-tabs').children) button.disabled = false;
}

async function loadResult(id) {
  $('error').hidden = true;
  $('replay').hidden = true; $('results').hidden = true; $('entry').hidden = true;
  $('progress-panel').hidden = false; $('stage').textContent = 'LOADING RECORDED RESPONSE';
  $('show-results').disabled = true; $('show-reading').disabled = true;
  for (const button of $('performance-tabs').children) button.disabled = true;
  audio.pause(); neuralScene.clear(); tailStarted = null; result = null; chartRange = null;
  $('play').disabled = true; $('seek').disabled = true;
  result = await request(`/api/readings/${id}/result.json`);
  // Preserve ranking when replaying earlier result files that stored alphabetical traces.
  const rank = new Map(result.response.populations.map((population, i) => [population.name, i]));
  result.population_timeline.sort((a, b) => rank.get(a.name) - rank.get(b.name));
  tailStarted = null; lastFrame = -1; lastLine = null; chartRange = null;
  $('entry').hidden = true;
  $('results').hidden = true; $('error').hidden = true;
  $('poem').value = result.display.poem;
  $('spoken-poem').replaceChildren(...result.display.poem.split(/\r?\n/).map((line, i) => {
    const row = element('div', undefined, 'poem-line');
    row.dataset.line = i + 1;
    row.append(element('span', String(i + 1).padStart(2, '0'), 'line-number'), document.createTextNode(line || '\u00a0'));
    return row;
  }));
  $('live-populations').replaceChildren(...(result.benchmark?.monitored_populations || result.response.monitored_populations).filter(p=>p.available).slice(0,5).map(population => {
    const row = element('div', undefined, 'live-pop');
    row.dataset.name = population.name;
    row.append(element('span', population.name), element('span', '—'));
    row.title=`Mean difference ${signed(population.delta_hz_per_neuron)} Hz/neuron ${result.benchmark?'against matched silence':'against initial baseline'}`;
    return row;
  }));
  $('run-note').textContent = `Recorded, not live computation · seed ${result.fly.seed} · ${result.fly.timestep * 1000} ms steps`;
  $('play').disabled = true;
  $('seek').disabled = true;
  try { await audio.load(resource(`/api/readings/${id}/audio.wav`)); }
  catch (e) { error(`Audio unavailable: ${e.message}. The recorded interpretation remains available.`); }
  audio.duration = result.audio.duration;
  $('seek').max = result.audio.duration; $('seek').value = 0;
  $('audio-download').href = resource(`/api/readings/${id}/audio.wav`);
  $('voice-credit').textContent = `${result.audio.provider} / ${result.audio.voice}${result.audio.provider === 'librivox-recording' ? ' · human performance' : ' · fixed voice'}`;
  const performance = site.performances?.find(p=>p.id===id);
  $('performance-note').textContent = (performance?.description || '') + (performance ? ` Actual normalized RMS: ${result.audio.normalization.output_rms.toFixed(3)}. Equal processing does not guarantee equal loudness under the peak limit.` : '');
  for (const button of $('performance-tabs').children) button.setAttribute('aria-pressed',String(button.dataset.id===id));

  if (result.provenance.neural_display) {
    try { neuralScene.load(await request(`/api/readings/${id}/neural-display.json`)); }
    catch { $('neural-caption').textContent='Spatial data unavailable; measurements remain available.'; }
  } else $('neural-caption').textContent='This earlier record has no spatial spike export.';
  drawCharts(); populateResults();
  $('progress-panel').hidden = true; $('replay').hidden = false; $('results').hidden = false;
  flyScene.resize(); neuralScene.resize(); updateReplay(0);
  $('play').disabled = !audio.bytes; $('seek').disabled = !audio.bytes;
  $('show-results').disabled = false; $('show-reading').disabled = false;
  $('playback-note').textContent = 'Press play to hear the poem and replay its recorded neural trajectory.';
  for (const button of $('performance-tabs').children) button.disabled = false;
}

function updateReplay(time) {
  if (!result) return;
  const index = Math.max(0, Math.min(result.timeline.length - 1, Math.floor((time - result.timeline[0].time) / result.fly.timestep)));
  if (index === lastFrame) return;
  lastFrame = index;
  const row = result.timeline[index];
  $('clock').textContent = stamp(time);
  $('seek').value = Math.min(time, result.audio.duration);
  $('player-time').textContent = `${stamp(Math.min(time, result.audio.duration))} / ${stamp(result.audio.duration)}`;
  flyScene.update({...row, time});
  neuralScene.update(time);
  $('jon-rate').textContent = `JON ${(row.groups['JO-A/B input'] || 0).toFixed(1)} Hz/neuron`;
  $('current-rate').textContent = row.smoothed_hz_per_neuron.toFixed(3);
  $('current-delta').textContent = result.benchmark ? `${signed(result.benchmark.timeline[index].delta_hz_per_neuron)} vs silence` : `${signed(row.delta_hz_per_neuron)} from baseline`;
  $('voltage').textContent = `JON input ${row.injected_voltage.toFixed(3)}`;
  const x = 38 + (time - chartRange.minTime) / (chartRange.maxTime - chartRange.minTime) * 590;
  for (const id of ['neural-cursor', 'audio-cursor']) { $(id).setAttribute('x1', x); $(id).setAttribute('x2', x); }
  const activeLine = time < result.audio.duration ? row.line : null;
  for (const node of $('spoken-poem').children) node.classList.toggle('active', Number(node.dataset.line) === activeLine);
  if (activeLine !== lastLine && activeLine !== null) {
    const pane = $('spoken-poem');
    const active = pane.querySelector('.active');
    if (active) {
      const bounds = active.getBoundingClientRect();
      const visible = pane.getBoundingClientRect();
      if (bounds.bottom > visible.bottom || bounds.top < visible.top) {
        pane.scrollTop += bounds.top - visible.top - 20;
      }
    }
  }
  lastLine = activeLine;
  $('line-label').textContent = activeLine ? `LINE ${String(activeLine).padStart(2, '0')}` : time >= result.audio.duration ? 'AFTER THE VOICE' : 'LINE BREAK';
  for (const node of $('live-populations').children) {
    const population=(result.benchmark?.monitored_populations || result.response.monitored_populations).find(p=>p.name===node.dataset.name);
    node.lastChild.textContent=`${(row.groups[node.dataset.name] || 0).toFixed(1)} / Δ ${signed(population.delta_hz_per_neuron,2)}`;
  }
}
$('show-reading').addEventListener('click', () => { revealResults(); $('reading-heading').scrollIntoView({behavior: 'smooth', block: 'start'}); });
function revealResults() { $('results').hidden = false; }
$('show-results').addEventListener('click', () => { revealResults(); $('response-heading').scrollIntoView({behavior: 'smooth', block: 'start'}); });
audio.addEventListener('play', () => { $('play').textContent = 'PAUSE'; tailStarted = null; $('playback-note').textContent = 'Replaying the computed response in sync with the voice.'; });
audio.addEventListener('seeking', () => { tailStarted = null; lastFrame = -1; });
audio.addEventListener('pause', () => { $('play').textContent = 'PLAY'; });
audio.addEventListener('ended', () => { $('play').textContent = 'REPLAY'; tailStarted = performance.now(); $('playback-note').textContent = 'The voice has stopped. Replaying the recorded silent aftermath.'; });
audio.addEventListener('error', () => error('The saved audio could not be loaded. The measurements remain available below.'));
function animate(now) {
  if (result && chartRange && !$('replay').hidden) {
    let time = audio.currentTime;
    if (tailStarted !== null) {
      time = Math.min(chartRange.maxTime - result.fly.timestep, result.audio.duration + (now - tailStarted) / 1000);
      if (time >= chartRange.maxTime - result.fly.timestep) {
        revealResults();
        $('playback-note').textContent = 'Replay complete. RESPONSE and READING are separated below.';
      }
    }
    updateReplay(time);
  }
  requestAnimationFrame(animate);
}
requestAnimationFrame(animate);
$('new').addEventListener('click', () => {
  audio.pause(); tailStarted = null; result = null;
  $('replay').hidden = true; $('results').hidden = true; $('entry').hidden = false;
  history.replaceState(null, '', base.pathname); updateCount(); $('poem').focus();
});

function selectLens(affect) {
  affectSelected = affect;
  $('affect-reading').hidden=!affect;
  $('reading-text').hidden=affect;
  $('circuit-lens').setAttribute('aria-pressed',String(!affect));
  $('affect-lens').setAttribute('aria-pressed',String(affect));
}
$('circuit-lens').addEventListener('click',()=>selectLens(false));
$('affect-lens').addEventListener('click',()=>selectLens(true));
if (recorded && site.performances?.length > 1) {
  $('performance-tabs').hidden=false;
  for(const performance of site.performances) {
    const button=element('button',performance.label);button.type='button';button.dataset.id=performance.id;
    button.setAttribute('aria-pressed',String(performance.id===site.reading));
    button.addEventListener('click',async()=>{
      const wasReading = $('reading-heading').getBoundingClientRect().top < window.innerHeight && $('reading-heading').getBoundingClientRect().top >= 0;
      for(const item of $('performance-tabs').children)item.disabled=true;
      try {await loadResult(performance.id);if(wasReading){revealResults();$('reading-heading').scrollIntoView({block:'start'});}else{$('replay').scrollIntoView({block:'start'});}$('method-link').href=resource(`/api/readings/${performance.id}/METHOD.md`);}
      catch(e){loadFailure(e);}
      finally{for(const item of $('performance-tabs').children)item.disabled=false;}
    });
    $('performance-tabs').append(button);
  }
}
if (recorded) {
  $('edition-notice').hidden = false;
  $('edition-notice').textContent = 'PUBLIC RECORDED EDITION · William Blake, The Fly (1794). Compare performances, each coupled to its own saved full-connectome response. New poems require the Python simulator; this page does not run a live backend.';
  $('new').hidden = true;
  $('storage-note').textContent = 'This edition replays a published reading. It accepts and stores no submitted poems.';
  $('method-link').href = resource(`/api/readings/${site.reading}/METHOD.md`);
}
const saved = recorded ? site.reading : new URLSearchParams(location.search).get('reading');
if (saved && /^[a-z0-9-]{1,64}$/.test(saved)) {
  $('progress-label').textContent='RETRIEVING A SAVED READING';
  $('stage').textContent='LOADING RECORDED RESPONSE';
  $('progress-detail').textContent='Downloading the saved voice, measurements and spatial spike display.';
  $('entry').hidden = true; $('progress-panel').hidden = false;
  poll(saved).catch(loadFailure);
}

if (!saved) loadExample();

if (!recorded) request('/api/settings').then(settings => {
  if (settings.public) $('storage-note').textContent = 'Submitted poems and recordings are stored temporarily on this server for up to 24 hours. Anyone with a reading link can view it. Download artifacts to retain them.';
}).catch(() => {});
