import { RecordedAudio } from './audio-player.js';
const labels = {
  reference: 'Unchanged recording',
  earlier: 'Emphasis earlier',
  later: 'Emphasis later',
};
const pairs = {
  earlier_later: ['earlier', 'later'],
  earlier_reference: ['earlier', 'reference'],
  later_reference: ['later', 'reference'],
};
const group = 'direct JON postsynaptic partners';
const fmt = (v) => `${v >= 0 ? '+' : ''}${v.toFixed(3)}`;
export class EmphasisPlayer {
  constructor(root) {
    this.root = root;
    this.q = (key) => root.querySelector(`[data-em="${key}"]`);
    this.audio = new RecordedAudio();
    this.active = false;
    this.busy = false;
    this.last = -1;
    this.q('play').addEventListener('click', async () => {
      if (this.playPending) return;
      this.playPending = true;
      this.q('play').disabled = true;
      try {
        if (this.audio.paused) await this.audio.play();
        else this.audio.pause();
      } catch (e) {
        this.q('status').textContent = `Playback failed: ${e.message}`;
        this.q('status').hidden = false;
      } finally {
        this.playPending = false;
        this.q('play').disabled = this.busy || !this.audio.bytes;
      }
    });
    this.q('seek').addEventListener('input', () => {
      this.audio.currentTime = Number(this.q('seek').value);
      this.update();
    });
    for (const event of ['play', 'pause', 'ended'])
      this.audio.addEventListener(event, () => {
        this.q('play').textContent = this.audio.paused ? 'PLAY' : 'PAUSE';
        this.update();
      });
    this.audio.addEventListener('error', () => {
      this.q('status').textContent =
        'Audio playback failed. You can download the WAV.';
      this.q('status').hidden = false;
    });
    this.q('comparison').addEventListener('change', () =>
      this.selectComparison().catch((e) => this.fail(e)),
    );
    this.q('first').addEventListener('click', () =>
      this.select(this.pair[0]).catch((e) => this.fail(e)),
    );
    this.q('second').addEventListener('click', () =>
      this.select(this.pair[1]).catch((e) => this.fail(e)),
    );
    for (let i = 0; i < 2; i++)
      this.q(`target${i + 1}`).addEventListener('click', () => {
        this.audio.currentTime = Math.max(
          0,
          this.data.manifest.targets[i].start - 0.2,
        );
        this.update();
      });
    const tick = () => {
      if (this.active && this.data && !this.busy) this.update();
      requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  }
  pause() {
    this.active = false;
    this.audio.pause();
  }
  fail(e) {
    this.q('status').textContent = `Comparison unavailable: ${e.message}`;
    this.q('status').hidden = false;
  }
  async show(poem) {
    this.active = true;
    if (this.data) return;
    try {
      const response = await fetch('./experiments/emphasis-v4/comparison.json');
      if (!response.ok) throw new Error('experiment data could not be loaded');
      this.data = await response.json();
      this.encodings = {};
      for (const name of ['reference', 'earlier', 'later']) {
        const r = await fetch(
          `./experiments/emphasis-v4/${name}/encoding.json`,
        );
        if (!r.ok) throw new Error('input trace unavailable');
        this.encodings[name] = await r.json();
      }
      this.q('poem').replaceChildren(
        ...poem.split(/\r?\n/).map((text, i) => {
          const row = document.createElement('div');
          row.textContent = text || '\u00a0';
          row.dataset.line = i + 1;
          if ([2, 17].includes(i + 1)) row.className = 'em-target';
          return row;
        }),
      );
      await this.selectComparison();
      this.q('body').hidden = false;
      this.q('status').hidden = true;
    } catch (e) {
      this.data = null;
      this.fail(e);
    }
  }
  async selectComparison() {
    this.pair = pairs[this.q('comparison').value];
    this.audio.pause();
    this.q('first').textContent = `Listen: ${labels[this.pair[0]]}`;
    this.q('second').textContent = `Listen: ${labels[this.pair[1]]}`;
    const key = this.q('comparison').value,
      c = this.data.comparisons[key][group],
      r = this.data.readings[key];
    for (const name of ['response', 'reading', 'functional'])
      this.q(name).textContent = r[name];
    this.q('windows').replaceChildren(
      ...c.windows.map((w) => {
        const p = document.createElement('p');
        p.textContent = `${w.start.toFixed(2)}–${w.end.toFixed(2)} s: ${fmt(w.mean.mean)} Hz/neuron (first minus second); ${w.mean.positive} runs higher, ${w.mean.negative} lower, ${w.mean.zero} equal. ${w.temporal.criterion_met ? 'Declared criterion met.' : 'Criterion not met.'}`;
        return p;
      }),
    );
    this.q('averages').textContent =
      `Whole-recording difference: ${fmt(c.whole.mean)} Hz/neuron. Off-target difference: ${fmt(c.off_target.mean)}. A local response need not change the overall average.`;
    this.draw();
    await this.select(this.pair[0]);
  }
  async select(name) {
    if (this.busy) return;
    this.busy = true;
    this.audio.pause();
    const position = this.audio.currentTime;
    const controls = [
      'play',
      'first',
      'second',
      'comparison',
      'seek',
      'target1',
      'target2',
    ];
    for (const c of controls) this.q(c).disabled = true;
    try {
      await this.audio.load(`./experiments/emphasis-v4/${name}/audio.wav`);
      this.audio.duration = this.data.manifest.conditions[name].duration;
      this.audio.currentTime = position;
      this.name = name;
      this.q('seek').max = this.audio.duration;
      this.q('download').href = `./experiments/emphasis-v4/${name}/audio.wav`;
      for (const [key, n] of [
        ['first', this.pair[0]],
        ['second', this.pair[1]],
      ])
        this.q(key).setAttribute('aria-pressed', String(n === name));
      const p = this.data.manifest.conditions[name];
      this.q('exposure').textContent =
        `Selected: ${labels[name]}. RMS ${p.rms.toFixed(6)}; duration ${p.duration.toFixed(2)} s; integrated injected drive ${p.integrated_drive.toFixed(6)}; ${p.capped_frames} capped frames. Switching recordings retains the listening position and pauses playback.`;
      this.last = -1;
      this.update();
    } finally {
      this.busy = false;
      for (const c of controls) this.q(c).disabled = false;
      this.q('play').disabled = !this.audio.bytes;
    }
  }
  draw() {
    const svg = this.q('chart');
    svg.replaceChildren();
    const streams = this.pair.map((n) => this.data.timeline[n][group]);
    const values = streams.flatMap((s) => [...s.low, ...s.high]);
    const lo = Math.min(0, ...values),
      hi = Math.max(0.001, ...values),
      duration = this.data.manifest.conditions.reference.duration;
    const x = (t) => 42 + (t / duration) * 590,
      y = (v) => 190 - ((v - lo) / (hi - lo)) * 170;
    const node = (tag, attrs, text) => {
      const e = document.createElementNS('http://www.w3.org/2000/svg', tag);
      for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
      if (text !== undefined) e.textContent = text;
      svg.append(e);
      return e;
    };
    node('line', {
      x1: 42,
      x2: 632,
      y1: y(0),
      y2: y(0),
      stroke: '#999',
      'stroke-dasharray': '4 4',
    });
    for (const v of [lo, hi])
      node(
        'text',
        { x: 0, y: y(v), 'font-size': 11, fill: 'currentColor' },
        v.toFixed(2),
      );
    for (let i = 0; i < 2; i++) {
      const s = streams[i],
        color = i ? '#a55235' : '#39635d',
        points = (a) => a.map((v, j) => `${x(j * 0.1)},${y(v)}`);
      node('polygon', {
        points: [...points(s.high), ...points(s.low).reverse()].join(' '),
        fill: color,
        opacity: 0.1,
      });
      node('polyline', {
        points: points(s.mean).join(' '),
        stroke: color,
        'stroke-width': 1.5,
        fill: 'none',
      });
    }
    for (const t of this.data.manifest.targets)
      node('rect', {
        x: x(t.start),
        y: 10,
        width: x(t.end) - x(t.start),
        height: 185,
        fill: '#a55235',
        opacity: 0.06,
      });
    this.cursor = node('line', {
      x1: x(0),
      x2: x(0),
      y1: 10,
      y2: 195,
      stroke: '#262923',
    });
    this.chartX = x;
    node(
      'text',
      { x: 42, y: 220, 'font-size': 11, fill: 'currentColor' },
      '0 s',
    );
    node(
      'text',
      {
        x: 632,
        y: 220,
        'text-anchor': 'end',
        'font-size': 11,
        fill: 'currentColor',
      },
      `${duration.toFixed(1)} s`,
    );
    this.q('legend').textContent =
      `Green: ${labels[this.pair[0]]}. Rust: ${labels[this.pair[1]]}. Shaded vertical regions mark the amplitude edits.`;
  }
  update() {
    if (!this.name || !this.data) return;
    const t = this.audio.currentTime,
      index = Math.min(
        this.data.timeline[this.name][group].mean.length - 1,
        Math.floor(t / 0.1),
      );
    this.q('time').textContent =
      `${t.toFixed(1)} / ${this.audio.duration.toFixed(1)} s`;
    this.q('seek').value = t;
    this.cursor.setAttribute('x1', this.chartX(t));
    this.cursor.setAttribute('x2', this.chartX(t));
    const rate = this.data.timeline[this.name][group].mean[index];
    this.q('current').textContent =
      `${labels[this.name]}: ${fmt(rate)} Hz/neuron relative to silence.`;
    const frame =
      this.encodings[this.name][
        Math.min(this.encodings[this.name].length - 1, Math.floor(t / 0.02))
      ];
    this.q('input').textContent =
      `Waveform RMS ${frame.rms.toFixed(4)} → injected JON drive ${frame.injected_voltage.toFixed(4)}.`;
    const line = this.data.manifest.lines.find(
      (l) => t >= l.start && t < l.end,
    )?.line;
    this.q('line').textContent = line ? `LINE ${line}` : 'PAUSE';
    if (line !== this.last) {
      for (const row of this.q('poem').children)
        row.classList.toggle('active', Number(row.dataset.line) === line);
      this.last = line;
      const active = this.q('poem').querySelector('.active');
      if (active) {
        const box = active.getBoundingClientRect(),
          pane = this.q('poem').getBoundingClientRect();
        if (box.bottom > pane.bottom || box.top < pane.top)
          this.q('poem').scrollTop += box.top - pane.top - 20;
      }
    }
  }
}
