import { s, h, horseGlyph } from "../dom.js";

export const RAMP = ["#e6f4f1", "#bfe3dc", "#8fcfc4", "#4fa99c", "#0f766e"];
export const DAY_COLORS = ["#0f766e", "#ea580c", "#2563eb", "#9333ea", "#ca8a04", "#db2777", "#4b5563"];
export const dayColor = (d) => DAY_COLORS[(d - 1) % DAY_COLORS.length];

const COS = Math.cos((33.4 * Math.PI) / 180);
export function project(lat, lon, p) {
  return [(lon - p.min_lon) * p.scale * COS, (p.max_lat - lat) * p.scale];
}

const centroidCache = new Map();
function pathCenter(d) {
  if (centroidCache.has(d)) return centroidCache.get(d);
  // 가장 큰 고리(점이 가장 많은 고리)의 꼭짓점 평균
  // "M x,y L x,y" 와 "M x y L x y" 둘 다 처리
  const rings = d.split(/[Mm]/).filter((r) => r.trim()).map((r) => {
    const n = (r.match(/-?\d*\.?\d+(?:e-?\d+)?/g) || []).map(Number);
    const pts = []; for (let i = 0; i + 1 < n.length; i += 2) pts.push([n[i], n[i + 1]]);
    return pts;
  }).filter((r) => r.length);
  const ring = rings.sort((a, b) => b.length - a.length)[0] || [[0, 0]];
  const c = ring.reduce((a, [x, y]) => [a[0] + x, a[1] + y], [0, 0]).map((v) => v / ring.length);
  centroidCache.set(d, c);
  return c;
}

const fillFor = (v) => (v == null ? "url(#hatch)" : RAMP[Math.min(4, Math.floor(v * 5))]);

export function SvgMap(opts) {
  const z = opts.zoom || 1;
  const { map, emdValues, itinerary, places, activeDay, horseAt, highlightRegion, onPlaceClick, markerState, showLabels = true, onlyDay } = opts;
  const [, , W, H] = map.view_box.split(" ").map(Number);
  const svg = s("svg", { class: "map-svg", viewBox: opts.viewBox || map.view_box, role: "img", "aria-label": "제주 지도" });
  svg.appendChild(s("defs", {},
    s("pattern", { id: "hatch", width: 5, height: 5, patternUnits: "userSpaceOnUse", patternTransform: "rotate(45)" },
      s("rect", { width: 5, height: 5, fill: "#fff" }), s("line", { x1: 0, y1: 0, x2: 0, y2: 5, stroke: "#dcdcdc", "stroke-width": 2 }))));

  const gE = s("g");
  for (const e of map.emds) {
    const v = emdValues ? emdValues[e.emd] : undefined;
    gE.appendChild(s("path", { class: "emd" + (emdValues ? "" : " plain"), d: e.d, fill: emdValues ? fillFor(v) : null },
      s("title", {}, e.emd + (emdValues ? (v == null ? " · 지표 없음" : ` · 백분위 ${Math.round(v * 100)}`) : ""))));
  }
  svg.appendChild(gE);

  const gR = s("g");
  for (const r of map.regions) {
    gR.appendChild(s("path", { class: "region" + (r.region_id === "mountain" ? " mtn" : "") + (highlightRegion === r.region_id ? " hl" : ""), d: r.d }));
  }
  svg.appendChild(gR);
  if (showLabels) {
    const gL = s("g");
    for (const r of map.regions) {
      const [x, y] = pathCenter(r.d);
      gL.appendChild(s("text", { class: "rlabel", x, y, "text-anchor": "middle", style: z !== 1 ? `font-size:${19 * z}px;stroke-width:${5 * z}px` : null }, r.name));
    }
    svg.appendChild(gL);
  }

  if (itinerary && places) {
    const gRoute = s("g"), gM = s("g");
    for (const d of itinerary.days) {
      if (onlyDay && d.day !== onlyDay) continue;
      const pts = d.place_ids.filter((id) => places[id]).map((id) => project(places[id].lat, places[id].lon, map.project));
      const dim = activeDay && activeDay !== d.day;
      if (pts.length > 1) {
        gRoute.appendChild(s("polyline", { class: "route" + (dim ? " dim" : ""), points: pts.map((p) => p.join(",")).join(" "), stroke: dayColor(d.day) }));
      }
      d.place_ids.forEach((id, i) => {
        const p = places[id]; if (!p) return;
        const [x, y] = project(p.lat, p.lon, map.project);
        const st = markerState ? markerState(id, d.day, i) : "";
        const m = s("g", { class: `marker ${dim ? "dim" : ""} ${st}`, transform: `translate(${x},${y}) scale(${z})` },
          s("circle", { r: 11, fill: dayColor(d.day) }), s("text", {}, i + 1), s("title", {}, `${d.day}일차 ${i + 1}. ${p.name}`));
        if (onPlaceClick) m.addEventListener("click", () => onPlaceClick(id, d.day));
        gM.appendChild(m);
      });
    }
    svg.appendChild(gRoute);
    svg.appendChild(gM);
  }

  if (horseAt) {
    const g = s("g", { class: "horse", style: `transform: translate(${horseAt[0]}px, ${horseAt[1] - 26 * z}px) scale(${z})` }, horseGlyph());
    svg.appendChild(g);
  }
  return svg;
}

export function MapLegend({ title, source, period, missing = true }) {
  return h("div", { class: "legend" },
    h("div", { class: "ramp" }, h("span", {}, "낮음"), RAMP.map((c) => h("i", { style: { background: c } })), h("span", {}, "높음"),
      missing ? [h("i", { class: "hatch", style: { marginLeft: "10px" } }), h("span", {}, "지표 없음")] : null),
    h("div", { style: { fontSize: "12px" } }, `${title} · 출처 ${source} · ${period}`));
}
