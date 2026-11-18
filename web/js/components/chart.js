import { s, h } from "../dom.js";

// series: [{name, color, values: (number|null)[]}], labels: string[]
export function LineChart({ series, labels, unit = "", height = 220, fmt }) {
  const W = 560, H = height, L = 46, R = 24, T = 12, B = 28;
  const all = series.flatMap((x) => x.values).filter((v) => v != null);
  const max = all.length ? Math.max(...all) : 1;
  const min = 0;
  const nice = (() => { const p = 10 ** Math.floor(Math.log10(max || 1)); const m = Math.ceil(max / p); return (m <= 2 ? 2 : m <= 5 ? 5 : 10) * p; })();
  // 눈금 간격에 맞춰 소수 자릿수 자동 (예: 0.25 → 2자리)
  const step4 = nice / 4;
  const dec = Math.min(3, (String(+step4.toPrecision(6)).split(".")[1] || "").length);
  fmt = fmt || ((v) => (v >= 1000 ? `${Math.round(v / 1000)}k` : v.toFixed(dec)));
  const x = (i) => L + (i * (W - L - R)) / Math.max(1, labels.length - 1);
  const y = (v) => T + (H - T - B) * (1 - (v - min) / (nice - min));
  const svg = s("svg", { class: "chart-svg", viewBox: `0 0 ${W} ${H}` });
  const grid = s("g", { class: "grid" }), axis = s("g", { class: "axis" });
  for (let i = 0; i <= 4; i++) {
    const v = (nice * i) / 4, yy = y(v);
    grid.appendChild(s("line", { x1: L, x2: W - R, y1: yy, y2: yy }));
    axis.appendChild(s("text", { x: L - 8, y: yy + 3, "text-anchor": "end" }, fmt(v)));
  }
  const step = Math.ceil(labels.length / 8);
  labels.forEach((lb, i) => { if (i % step === 0 || i === labels.length - 1) axis.appendChild(s("text", { x: x(i), y: H - 8, "text-anchor": "middle" }, lb)); });
  svg.appendChild(grid); svg.appendChild(axis);
  for (const se of series) {
    let seg = [];
    const flush = () => { if (seg.length > 1) svg.appendChild(s("polyline", { class: "line", stroke: se.color, points: seg.join(" ") })); else if (seg.length === 1) { const [a, b] = seg[0].split(","); svg.appendChild(s("circle", { cx: a, cy: b, r: 2.5, fill: se.color })); } seg = []; };
    se.values.forEach((v, i) => { if (v == null) flush(); else seg.push(`${x(i).toFixed(1)},${y(v).toFixed(1)}`); });
    flush();
  }
  return h("div", {}, svg, h("div", { class: "chart-legend" }, series.map((se) => h("span", {}, h("i", { style: { background: se.color } }), se.name))));
}
