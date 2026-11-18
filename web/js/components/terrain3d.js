// 03 게임용 3D 지형 지도 (three.js, 로컬 동봉). WebGL이 없거나 지형 파일을 못 읽으면 호출하는 쪽이 2D로 폴백한다.
// 좌표는 2D 지도와 같은 투영(map.project)을 쓰고, 높이는 Copernicus DEM(web/assets/terrain.*)을 과장(EXAG)해 올린다.
import * as THREE from "../../vendor/three/three.module.js";

const COS = Math.cos((33.4 * Math.PI) / 180);
const EXAG = 4.0;                 // 높이 과장 배율 (표시용)
let terrainData = null;           // {meta, h: Int16Array}
let view = null;                  // 싱글턴: 화면을 다시 그려도 캔버스·장면을 유지

export function webglOK() {
  try {
    const c = document.createElement("canvas");
    return !!(window.WebGLRenderingContext && (c.getContext("webgl2") || c.getContext("webgl")));
  } catch { return false; }
}

export async function loadTerrain() {
  if (terrainData) return terrainData;
  const meta = await (await fetch("assets/terrain.json")).json();
  const buf = await (await fetch("assets/terrain.bin")).arrayBuffer();
  terrainData = { meta, h: new Int16Array(buf) };
  return terrainData;
}

export const terrainAttribution = () => terrainData?.meta?.attribution || "";

// ── 좌표 ────────────────────────────────────────
function makeProj(map) {
  const p = map.project;
  const perMeter = p.scale / 111000;   // 위도 1° ≈ 111km
  return {
    x: (lon) => (lon - p.min_lon) * p.scale * COS,
    z: (lat) => (p.max_lat - lat) * p.scale,
    lon: (x) => x / (p.scale * COS) + p.min_lon,
    lat: (z) => p.max_lat - z / p.scale,
    yOf: (m) => Math.max(0, m) * perMeter * EXAG,
  };
}

function heightAt(lon, lat) {
  const { meta, h } = terrainData;
  const fx = (lon - meta.west) / meta.dlon, fy = (meta.north - lat) / meta.dlat;
  const x0 = Math.floor(fx), y0 = Math.floor(fy);
  if (x0 < 0 || y0 < 0 || x0 >= meta.cols - 1 || y0 >= meta.rows - 1) return 0;
  const tx = fx - x0, ty = fy - y0, i = y0 * meta.cols + x0;
  const a = h[i], b = h[i + 1], c = h[i + meta.cols], d = h[i + meta.cols + 1];
  return (a * (1 - tx) + b * tx) * (1 - ty) + (c * (1 - tx) + d * tx) * ty;
}

// ── 텍스처 (번호 원, 말, 이름표) ────────────────────
function circleTex(text, color, ring) {
  const s = 128, cv = document.createElement("canvas"); cv.width = cv.height = s;
  const g = cv.getContext("2d");
  g.beginPath(); g.arc(s / 2, s / 2, s / 2 - 8, 0, Math.PI * 2);
  g.fillStyle = color; g.fill();
  g.lineWidth = ring ? 12 : 9; g.strokeStyle = ring ? "#0a0a0a" : "#ffffff"; g.stroke();
  g.fillStyle = "#fff"; g.font = "600 58px Geist, Pretendard, sans-serif"; g.textAlign = "center"; g.textBaseline = "middle";
  g.fillText(text, s / 2, s / 2 + 3);
  const t = new THREE.CanvasTexture(cv); t.colorSpace = THREE.SRGBColorSpace; return t;
}
function horseTex() {
  const s = 160, cv = document.createElement("canvas"); cv.width = cv.height = s;
  const g = cv.getContext("2d");
  g.beginPath(); g.arc(s / 2, s / 2, s / 2 - 10, 0, Math.PI * 2);
  g.fillStyle = "#ea580c"; g.fill(); g.lineWidth = 10; g.strokeStyle = "#fff"; g.stroke();
  g.save(); g.translate(s / 2, s / 2); g.scale(3.6, 3.6);
  g.fillStyle = "#fff";
  g.fill(new Path2D("M-7 9 L-7 1 C-7 -5 -3 -9 2 -9 L5 -13 L6 -8.5 C9.5 -7 11 -3.5 10 -1.5 C9.4 -0.3 8 0 6.6 -0.6 L4 -1.6 L3 2 L4 9 Z"));
  g.restore();
  const t = new THREE.CanvasTexture(cv); t.colorSpace = THREE.SRGBColorSpace; return t;
}
function labelTex(text) {
  const cv = document.createElement("canvas"), g = cv.getContext("2d");
  const font = "600 44px Geist, Pretendard, sans-serif"; g.font = font;
  const w = Math.ceil(g.measureText(text).width) + 48, hgt = 76;
  cv.width = w; cv.height = hgt;
  g.font = font; g.fillStyle = "rgba(10,10,10,.88)";
  const r = 18; g.beginPath(); g.roundRect(0, 0, w, hgt, r); g.fill();
  g.fillStyle = "#fff"; g.textBaseline = "middle"; g.fillText(text, 24, hgt / 2 + 2);
  const t = new THREE.CanvasTexture(cv); t.colorSpace = THREE.SRGBColorSpace;
  return { tex: t, aspect: w / hgt };
}
function sprite(tex, px) {          // 화면 크기 고정 스프라이트 (px는 대략적인 픽셀 높이)
  const m = new THREE.SpriteMaterial({ map: tex, depthTest: false, sizeAttenuation: false, transparent: true });
  const sp = new THREE.Sprite(m); sp.renderOrder = 10; sp.userData.px = px;
  return sp;
}

// ── 장면 ────────────────────────────────────────
function landColor(m, out) {
  const stops = [[0, [0.91, 0.94, 0.88]], [40, [0.80, 0.89, 0.76]], [250, [0.66, 0.80, 0.62]],
    [700, [0.53, 0.68, 0.50]], [1200, [0.62, 0.62, 0.55]], [1750, [0.93, 0.93, 0.91]]];
  let i = 0; while (i < stops.length - 2 && m > stops[i + 1][0]) i++;
  const [m0, c0] = stops[i], [m1, c1] = stops[i + 1], t = Math.min(1, Math.max(0, (m - m0) / (m1 - m0)));
  out[0] = c0[0] + (c1[0] - c0[0]) * t; out[1] = c0[1] + (c1[1] - c0[1]) * t; out[2] = c0[2] + (c1[2] - c0[2]) * t;
}

function buildTerrain(P) {
  const { meta, h } = terrainData;
  const { cols, rows } = meta;
  const pos = new Float32Array(cols * rows * 3), col = new Float32Array(cols * rows * 3);
  const c = [0, 0, 0];
  for (let r = 0; r < rows; r++) for (let q = 0; q < cols; q++) {
    const i = r * cols + q, m = h[i];
    const lon = meta.west + q * meta.dlon, lat = meta.north - r * meta.dlat;
    pos[i * 3] = P.x(lon); pos[i * 3 + 1] = m > 0 ? P.yOf(m) : -4; pos[i * 3 + 2] = P.z(lat);
    if (m > 0) landColor(m, c); else { c[0] = 0.86; c[1] = 0.92; c[2] = 0.95; }
    col[i * 3] = c[0]; col[i * 3 + 1] = c[1]; col[i * 3 + 2] = c[2];
  }
  const idx = [];
  for (let r = 0; r < rows - 1; r++) for (let q = 0; q < cols - 1; q++) {
    const a = r * cols + q, b = a + 1, d = a + cols, e = d + 1;
    idx.push(a, d, b, b, d, e);
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.BufferAttribute(pos, 3));
  g.setAttribute("color", new THREE.BufferAttribute(col, 3));
  g.setIndex(idx); g.computeVertexNormals();
  return new THREE.Mesh(g, new THREE.MeshLambertMaterial({ vertexColors: true }));
}

function pathRings(d) {
  return d.split(/[Mm]/).filter((s) => s.trim()).map((s) => {
    const n = (s.match(/-?\d*\.?\d+(?:e-?\d+)?/g) || []).map(Number);
    const pts = []; for (let i = 0; i + 1 < n.length; i += 2) pts.push([n[i], n[i + 1]]);
    return pts;
  }).filter((r) => r.length > 2);
}

function drapedPoints(P, a, b, lift, step = 1.5) {   // a,b: [x,z] — 지형을 따라 촘촘히
  const n = Math.max(1, Math.ceil(Math.hypot(b[0] - a[0], b[1] - a[1]) / step)), out = [];
  for (let i = 0; i <= n; i++) {
    const x = a[0] + (b[0] - a[0]) * (i / n), z = a[1] + (b[1] - a[1]) * (i / n);
    out.push(new THREE.Vector3(x, P.yOf(heightAt(P.lon(x), P.lat(z))) + lift, z));
  }
  return out;
}

function init(map) {
  const P = makeProj(map);
  const canvas = document.createElement("canvas");
  canvas.className = "terrain3d";
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: false });
  renderer.setPixelRatio(Math.min(2, window.devicePixelRatio || 1));
  renderer.setClearColor(0xf4f7f9);
  const scene = new THREE.Scene();
  scene.fog = new THREE.Fog(0xf4f7f9, 420, 1300);
  scene.add(new THREE.HemisphereLight(0xffffff, 0xb8c4bc, 1.25));
  const sun = new THREE.DirectionalLight(0xfff6ea, 2.6); sun.position.set(-500, 260, -150); scene.add(sun);  // 낮은 북서광 → 오름·한라산 음영
  scene.add(buildTerrain(P));
  const sea = new THREE.Mesh(new THREE.PlaneGeometry(4000, 4000), new THREE.MeshBasicMaterial({ color: 0xdbe9ef }));
  sea.rotation.x = -Math.PI / 2; sea.position.set(500, -0.8, 300); scene.add(sea);
  // 권역 경계 (지형 위에 얇게)
  const lineMat = new THREE.LineBasicMaterial({ color: 0x404040, transparent: true, opacity: 0.35 });
  for (const r of map.regions) for (const ring of pathRings(r.d)) {
    const pts = [];
    for (let i = 0; i < ring.length; i++) pts.push(...drapedPoints(P, ring[i], ring[(i + 1) % ring.length], 0.8, 4));
    scene.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts), lineMat));
  }
  const camera = new THREE.PerspectiveCamera(34, 2, 1, 3000);
  const horse = sprite(horseTex(), 46); scene.add(horse);
  view = { map, P, canvas, renderer, scene, camera, horse, dyn: new THREE.Group(), key: null, idx: -1,
    camPos: new THREE.Vector3(500, 400, 900), camLook: new THREE.Vector3(500, 0, 300),
    camPosT: new THREE.Vector3(), camLookT: new THREE.Vector3(), anim: null, raf: 0, size: [0, 0] };
  scene.add(view.dyn);
  return view;
}

function placeXYZ(p, lift = 0) {
  const P = view.P, x = P.x(p.lon), z = P.z(p.lat);
  return new THREE.Vector3(x, P.yOf(heightAt(p.lon, p.lat)) + lift, z);
}

function rebuildDay(items, places, color) {
  const g = view.dyn;
  while (g.children.length) { const c = g.children.pop(); c.geometry?.dispose?.(); c.material?.map?.dispose?.(); c.material?.dispose?.(); }
  const pts = items.map((it) => places[it.place_id]).filter(Boolean);
  // 경로선: 지형을 따라가는 튜브
  for (let i = 1; i < pts.length; i++) {
    const a = placeXYZ(pts[i - 1]), b = placeXYZ(pts[i]);
    const seg = drapedPoints(view.P, [a.x, a.z], [b.x, b.z], 1.2);
    if (seg.length < 2) continue;
    const tube = new THREE.TubeGeometry(new THREE.CatmullRomCurve3(seg), Math.max(8, seg.length * 2), 0.55, 6, false);
    g.add(new THREE.Mesh(tube, new THREE.MeshBasicMaterial({ color })));
  }
  view.markers = pts.map((p, i) => {
    const sp = sprite(circleTex(String(i + 1), color, false), 30);
    sp.position.copy(placeXYZ(p, 3)); sp.userData.i = i; sp.userData.color = color; g.add(sp);
    return sp;
  });
  view.label = null;
}

function setMarkers(idx) {
  (view.markers || []).forEach((sp) => {
    const i = sp.userData.i;
    const state = i < idx ? "done" : i === idx ? "next" : "todo";
    if (sp.userData.state === state) return;
    sp.userData.state = state;
    sp.material.map?.dispose();
    sp.material.map = circleTex(String(i + 1), state === "done" ? "#a3a3a3" : sp.userData.color, state === "next");
    sp.material.needsUpdate = true;
    sp.userData.px = state === "next" ? 38 : 30;
  });
}

function setLabel(text, pos) {
  if (view.label) { view.dyn.remove(view.label); view.label.material.map.dispose(); view.label.material.dispose(); view.label = null; }
  if (!text) return;
  const { tex, aspect } = labelTex(text);
  const sp = sprite(tex, 34); sp.userData.aspect = aspect; sp.center.set(0.5, -0.9);
  sp.position.copy(pos); view.dyn.add(sp); view.label = sp;
}

function aimCamera(target, from) {
  // 다음 목적지를 화면 가운데 조금 위에, 남쪽 위에서 비스듬히 내려다본다
  const d = from ? Math.min(220, Math.max(110, from.distanceTo(target) * 1.4 + 70)) : 150;
  const mid = from ? from.clone().lerp(target, 0.6) : target.clone();
  view.camLookT.set(mid.x, 0, mid.z);
  // 남쪽 아래에서 한라산 쪽(북)을 비스듬히 바라본다 → 지형 기복이 보이게
  view.camPosT.set(mid.x - d * 0.15, d * 0.62, mid.z + d * 1.25);
}

function resize() {
  const parent = view.canvas.parentElement; if (!parent) return;
  const w = parent.clientWidth, hgt = parent.clientHeight;
  if (w === view.size[0] && hgt === view.size[1]) return;
  view.size = [w, hgt];
  view.renderer.setSize(w, hgt, false);
  view.camera.aspect = w / Math.max(1, hgt); view.camera.updateProjectionMatrix();
}

function frame(t) {
  if (!view.canvas.isConnected) { view.raf = 0; return; }
  view.raf = requestAnimationFrame(frame);
  resize();
  const H = view.size[1] || 1;
  // 말 이동 애니메이션 (지형을 따라)
  if (view.anim) {
    const k = Math.min(1, (t - view.anim.t0) / view.anim.dur), e = k < 0.5 ? 2 * k * k : 1 - (-2 * k + 2) ** 2 / 2;
    const path = view.anim.path, f = e * (path.length - 1), i = Math.min(path.length - 2, Math.floor(f));
    view.horse.position.copy(path[i]).lerp(path[i + 1], f - i);
    view.horse.position.y += 6 + Math.sin(k * Math.PI * 6) * 1.2 * (1 - k);
    if (k >= 1) view.anim = null;
  }
  view.camPos.lerp(view.camPosT, 0.06); view.camLook.lerp(view.camLookT, 0.08);
  view.camera.position.copy(view.camPos); view.camera.lookAt(view.camLook);
  // 스프라이트를 화면 픽셀 크기로
  view.scene.traverse((o) => {
    if (o.isSprite && o.userData.px) {
      const s = (o.userData.px / H) * 0.62;   // sizeAttenuation:false → 화면 높이 비율
      o.scale.set(s * (o.userData.aspect || 1), s, 1);
    }
  });
  view.renderer.render(view.scene, view.camera);
}

// items: 그 날 퀘스트 [{place_id, label}], idx: 다음 목적지 순번(0부터, 끝이면 길이)
export function Terrain3D({ map, places, items, idx, color }) {
  if (!view || view.map !== map) {
    if (view) { cancelAnimationFrame(view.raf); view.renderer.dispose(); }
    init(map);
  }
  const wrap = document.createElement("div");
  wrap.className = "terrain-wrap";
  wrap.appendChild(view.canvas);
  const key = items.map((x) => x.place_id).join("|");
  const pts = items.map((x) => places[x.place_id]);
  if (key !== view.key) {
    view.key = key; view.idx = -1;
    rebuildDay(items, places, color);
    const start = placeXYZ(pts[0], 6); start.x -= 8; start.z += 6;
    view.horse.position.copy(start);
    aimCamera(placeXYZ(pts[0]));
    view.camPos.copy(view.camPosT).add(new THREE.Vector3(0, 120, 120));  // 처음엔 위에서 내려오며 시작
    view.camLook.copy(view.camLookT);
  }
  if (idx !== view.idx) {
    const prevIdx = view.idx; view.idx = idx;
    setMarkers(idx);
    if (idx > 0 && prevIdx >= 0 && idx === prevIdx + 1) {            // 방금 도착: 이전 위치 → 도착지
      const from = view.horse.position.clone(), to = placeXYZ(pts[idx - 1], 6);
      const path = drapedPoints(view.P, [from.x, from.z], [to.x, to.z], 6);
      view.anim = { path, t0: performance.now(), dur: Math.min(1800, 500 + path.length * 25) };
    } else if (idx > 0) {
      view.horse.position.copy(placeXYZ(pts[idx - 1], 6));
    }
    const next = pts[idx];
    if (next) {
      setLabel(items[idx].label, placeXYZ(next, 3));
      aimCamera(placeXYZ(next), idx > 0 ? placeXYZ(pts[idx - 1]) : null);
    } else {
      setLabel(null);
      aimCamera(placeXYZ(pts[pts.length - 1]), placeXYZ(pts[0]));
    }
  }
  if (!view.raf) view.raf = requestAnimationFrame(frame);
  return wrap;
}
