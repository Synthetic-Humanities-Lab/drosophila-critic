// Ground projection of measured thorax positions; never advance beyond playback.
export class RecordedPath {
  constructor(positions) {
    this.positions = positions;
    this.floor = new Float32Array(positions.length * 3);
    this.mapPoints = [];
    positions.forEach((p, i) => {
      this.floor.set([p[0], 0.008, -p[1]], i * 3);
      if (i % 5 === 0) this.mapPoints.push(this.mapPoint(p));
    });
    this.lastMapIndex = -1;
  }
  mapPoint(p) {
    return `${(p[0] + 10).toFixed(3)},${(8 - p[1]).toFixed(3)}`;
  }
  sample({ frame: { lo }, position }) {
    const mapIndex = Math.floor(lo / 5);
    if (mapIndex !== this.lastMapIndex) {
      this.mapPrefix = `M${this.mapPoints.slice(0, mapIndex + 1).join(" L")}`;
      this.lastMapIndex = mapIndex;
    }
    const p = this.positions[lo];
    return {
      count: lo + 1,
      tip: [p[0], 0.008, -p[1], position[0], 0.008, -position[1]],
      map: `${this.mapPrefix} L${this.mapPoint(position)}`,
    };
  }
}
