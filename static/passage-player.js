import { RecordedAudio } from './audio-player.js';
const group = 'direct JON postsynaptic partners';
const names = { reference: 'Synthetic reference', human: 'Denny Sayers' };
const signed = (v) => `${v >= 0 ? '+' : ''}${v.toFixed(3)}`;
export class PassagePlayer {
  constructor(root) {
    this.root = root;
    this.q = (key) => root.querySelector(`[data-p="${key}"]`);
    this.audio = new RecordedAudio();
    this.active = false;
    this.busy = false;
    this.q('source').addEventListener('change', () =>
      this.selectSource().catch((e) => this.fail(e)),
    );
    this.q('passage').addEventListener('change', () => this.selectPassage());
    this.q('baseline').addEventListener('change', () => this.render());
    this.q('play').addEventListener('click', async () => {
      if (this.pending) return;
      this.pending = true;
      this.q('play').disabled = true;
      try {
        if (!this.audio.paused) this.audio.pause();
        else {
          if (this.audio.currentTime >= this.window.end)
            this.audio.currentTime = this.window.start;
          await this.audio.play();
        }
      } catch (e) {
        this.fail(e);
      } finally {
        this.pending = false;
        this.q('play').disabled = this.busy || !this.audio.bytes;
      }
    });
    this.q('seek').addEventListener('input', () => {
      this.audio.currentTime = Number(this.q('seek').value);
      this.update();
    });
    for (const event of ['play', 'pause', 'ended'])
      this.audio.addEventListener(event, () => {
        this.q('play').textContent = this.audio.paused
          ? 'PLAY STANZA'
          : 'PAUSE';
      });
    this.audio.addEventListener('error', () =>
      this.fail(new Error('Playback failed; the WAV remains downloadable.')),
    );
    const tick = () => {
      if (this.active && this.data && !this.busy && this.window) {
        if (!this.audio.paused && this.audio.currentTime >= this.window.end) {
          this.audio.pause();
          this.audio.currentTime = this.window.end;
        }
        this.update();
      }
      requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  }
  pause() {
    this.active = false;
    this.audio.pause();
  }
  fail(e) {
    this.q('status').hidden = false;
    this.q('status').textContent = `Comparison unavailable: ${e.message}`;
  }
  async show(poem) {
    this.active = true;
    if (this.data) return;
    try {
      const r = await fetch('./experiments/passages-v5/comparison.json');
      if (!r.ok) throw new Error('saved passage analysis could not be loaded');
      this.data = await r.json();
      this.poem = poem.split(/\r?\n/);
      this.q('reading').textContent = this.data.reading.text;
      this.q('limits').textContent = this.data.reading.limits;
      this.q('table').replaceChildren(
        ...this.data.passages.map((p) => {
          const c = p.comparisons[group];
          const tr = document.createElement('tr');
          for (const text of [
            p.number,
            signed(c.mean),
            `${c.positive} / ${c.negative}`,
            c.boundary_robust ? 'Yes' : 'No',
          ]) {
            const td = document.createElement('td');
            td.textContent = text;
            tr.append(td);
          }
          return tr;
        }),
      );
      await this.selectSource();
      await this.loadPopulations();
      this.q('body').hidden = false;
      this.q('status').hidden = true;
    } catch (e) {
      this.data = null;
      this.fail(e);
    }
  }
  async loadPopulations() {
    try {
      const response = await fetch(
        './experiments/populations-v6/comparison.json',
      );
      if (!response.ok)
        throw new Error('saved population evidence unavailable');
      const result = await response.json();
      this.q('population-status').textContent =
        `${result.eligible_count} annotated types, ${result.screened_pairs} type/stanza comparisons. ${result.qualified_discovery} passed discovery; five candidates were frozen before validation. ${result.candidates.filter((r) => r.survives).length} of ${result.candidates.length} survived held-out checks.`;
      this.q('population-reading').textContent = result.reading;
      this.q('population-table').replaceChildren(
        ...result.candidates.map((row) => {
          const tr = document.createElement('tr'),
            title = document.createElement('td');
          const button = document.createElement('button');
          button.type = 'button';
          button.textContent = `${row.type} / stanza ${row.stanza}`;
          button.addEventListener('click', () => {
            if (this.busy) return;
            this.q('passage').value = String(row.stanza);
            this.selectPassage();
            this.q('play').focus();
          });
          title.append(button);
          tr.append(title);
          const residuals = Object.values(row.validation.residuals).map(
            (checks) => checks[4].mean,
          );
          for (const value of [
            `${row.total} / ${row.direct}`,
            signed(row.validation.raw[4].mean),
            `${signed(Math.min(...residuals))} to ${signed(Math.max(...residuals))}`,
            row.survives ? 'Yes' : 'No',
          ]) {
            const td = document.createElement('td');
            td.textContent = value;
            tr.append(td);
          }
          return tr;
        }),
      );
    } catch (e) {
      this.q('population-status').textContent =
        `Population follow-up unavailable: ${e.message}`;
    }
  }
  async selectSource() {
    if (this.busy) return;
    this.busy = true;
    this.audio.pause();
    for (const k of ['source', 'passage', 'play', 'seek'])
      this.q(k).disabled = true;
    try {
      this.name = this.q('source').value;
      const url = `./experiments/delivery-v1/${this.name}/audio.wav`;
      await this.audio.load(url);
      this.audio.duration = this.data.conditions[this.name].duration;
      this.q('download').href = url;
      this.selectPassage();
    } finally {
      this.busy = false;
      for (const k of ['source', 'passage', 'play', 'seek'])
        this.q(k).disabled = false;
      this.q('play').disabled = !this.audio.bytes;
    }
  }
  selectPassage() {
    this.audio.pause();
    this.passage = this.data.passages[Number(this.q('passage').value) - 1];
    this.window = this.passage.performances[this.name];
    this.audio.currentTime = this.window.start;
    this.q('seek').min = this.window.start;
    this.q('seek').max = this.window.end;
    this.q('poem').replaceChildren(
      ...this.poem
        .slice(this.passage.lines[0] - 1, this.passage.lines[1])
        .map((text, i) => {
          const row = document.createElement('div');
          row.textContent = text;
          row.dataset.line = this.passage.lines[0] + i;
          return row;
        }),
    );
    this.render();
    this.update();
  }
  render() {
    const p = this.passage,
      c = p.comparisons[group],
      key = this.q('baseline').value;
    const residual = p.residuals[key],
      model = this.data.models[key],
      s = model.scores.human;
    this.q('measurement').textContent =
      `Stanza ${p.number}: human minus synthetic ${signed(c.mean)} Hz/neuron; ${c.positive} runs higher and ${c.negative} lower. Boundary check: ${c.boundary_robust ? 'passes' : 'does not pass'}. After this input-only baseline: ${signed(residual.mean)} Hz/neuron; boundary check ${residual.boundary_robust ? 'passes' : 'does not pass'}.`;
    this.q('exposure').textContent = ['reference', 'human']
      .map((n) => {
        const w = p.performances[n],
          mean = w.downstream_rates.reduce((a, b) => a + b) / 8;
        return `${names[n]}: ${w.duration.toFixed(2)} s; mean injected drive ${w.mean_drive.toFixed(3)}; integrated drive ${w.integrated_drive.toFixed(3)}; downstream ${signed(mean)} Hz/neuron vs silence; ${(w.excess_spikes_per_neuron.reduce((a, b) => a + b) / 8).toFixed(3)} excess spikes/neuron across this interval.`;
      })
      .join(' ');
    this.q('baseline-score').textContent =
      `Across the complete human recording, this baseline has R² ${s.r2.toFixed(3)} and RMSE ${s.rmse.toFixed(3)} Hz/neuron (zero-response prediction: ${s.zero_rmse.toFixed(3)}). Its gain ${model.gain.toFixed(3)} was fitted only on earlier synthetic runs. These scores concern the eight-run mean, not an individual biological fly.`;
    this.draw('chart', false);
    this.draw('drive', true);
  }
  draw(key, input) {
    const svg = this.q(key),
      stream = this.data.timeline[this.name],
      w = this.window;
    const first = Math.floor(w.start / 0.1),
      last = Math.min(stream.mean.length, Math.ceil(w.end / 0.1));
    const prediction = stream.predictions[this.q('baseline').value];
    const arrays = input
      ? [stream.drive]
      : [stream.low, stream.high, prediction];
    const values = arrays.flatMap((a) => a.slice(first, last));
    const lo = Math.min(0, ...values),
      hi = Math.max(0.001, ...values);
    const x = (t) => 50 + ((t - w.start) / (w.end - w.start)) * 560,
      y = (v) => 155 - ((v - lo) / (hi - lo)) * 135;
    svg.replaceChildren();
    const add = (tag, attrs, text) => {
      const e = document.createElementNS('http://www.w3.org/2000/svg', tag);
      for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
      if (text !== undefined) e.textContent = text;
      svg.append(e);
      return e;
    };
    const points = (a) =>
      a
        .slice(first, last)
        .map(
          (v, i) =>
            `${x(Math.max(w.start, Math.min(w.end, (first + i + 0.5) * 0.1)))},${y(v)}`,
        );
    add('line', {
      x1: 50,
      x2: 610,
      y1: y(0),
      y2: y(0),
      stroke: '#aaa',
      'stroke-dasharray': '3 3',
    });
    if (!input)
      add('polygon', {
        points: [...points(stream.high), ...points(stream.low).reverse()].join(
          ' ',
        ),
        fill: '#39635d',
        opacity: 0.15,
      });
    for (const [a, color, dash] of input
      ? [[stream.drive, '#a55235', '']]
      : [
          [stream.mean, '#39635d', ''],
          [prediction, '#a55235', '5 3'],
        ])
      add('polyline', {
        points: points(a).join(' '),
        fill: 'none',
        stroke: color,
        'stroke-width': 2,
        'stroke-dasharray': dash,
      });
    for (const v of [lo, hi])
      add(
        'text',
        { x: 0, y: y(v), 'font-size': 11, fill: 'currentColor' },
        v.toFixed(2),
      );
    add(
      'text',
      { x: 50, y: 183, 'font-size': 11, fill: 'currentColor' },
      `${w.start.toFixed(2)} s`,
    );
    add(
      'text',
      {
        x: 610,
        y: 183,
        'font-size': 11,
        'text-anchor': 'end',
        fill: 'currentColor',
      },
      `${w.end.toFixed(2)} s`,
    );
    this[key + 'Cursor'] = add('line', {
      x1: 50,
      x2: 50,
      y1: 10,
      y2: 160,
      stroke: '#262923',
    });
    this.chartX = x;
  }
  update() {
    const t = this.audio.currentTime;
    this.q('seek').value = t;
    this.q('time').textContent =
      `${t.toFixed(2)} / ${this.window.end.toFixed(2)} s · native recording clock`;
    for (const key of ['chart', 'drive'])
      if (this[key + 'Cursor'])
        for (const axis of ['x1', 'x2'])
          this[key + 'Cursor'].setAttribute(axis, this.chartX(t));
    const line = this.data.conditions[this.name].lines.find(
      (l) => t >= l.start && t < l.end,
    )?.line;
    for (const row of this.q('poem').children)
      row.classList.toggle('active', Number(row.dataset.line) === line);
  }
}
