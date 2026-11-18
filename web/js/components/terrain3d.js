// 03 게임용 3D 지형 지도 (three.js, 로컬 동봉). WebGL이 없거나 지형 파일을 못 읽으면 호출하는 쪽이 2D로 폴백한다.
// 좌표는 2D 지도와 같은 투영(map.project), 높이는 Copernicus DEM(web/assets/terrain.*)을 과장(EXAG)해 올린다.
// 메트로타이핑 방식: setProgress(0~1)만큼 현재 구간의 선이 차오르고 말이 그만큼 달려간다.
import * as THREE from "../../vendor/three/three.module.js";

const COS = Math.cos((33.4 * Math.PI) / 180);
const EXAG = 4.0;                 // 높이 과장 배율 (표시용)
const SKY = 0xeaf1f5;
let terrainData = null;           // {meta, h: Int16Array}
let view = null;                  // 싱글턴: 화면을 다시 그려도 캔버스·장면을 유지

export function webglOK() {
  try { const c = document.createElement("canvas"); return !!(c.getContext("webgl2") || c.getContext("webgl")); }
  catch { return false; }
}

export async function loadTerrain() {
  if (terrainData) return terrainData;
  const meta = await (await fetch("assets/terrain.json")).json();
  const buf = await (await fetch("assets/terrain.bin")).arrayBuffer();
  terrainData = { meta, h: new Int16Array(buf) };
  return terrainData;
}

export const terrainAttribution = () => terrainData?.meta?.attribution || "";

// ── 좌표·높이 ───────────────────────────────────
function makeProj(map) {
  const p = map.project, perMeter = p.scale / 111000;
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
  return (h[i] * (1 - tx) + h[i + 1] * tx) * (1 - ty) + (h[i + meta.cols] * (1 - tx) + h[i + meta.cols + 1] * tx) * ty;
}
const groundY = (x, z) => view.P.yOf(heightAt(view.P.lon(x), view.P.lat(z)));

// ── 텍스처 ──────────────────────────────────────
function canvasTex(cv) { const t = new THREE.CanvasTexture(cv); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 4; return t; }
function numberTex(text, color) {
  const s = 128, cv = document.createElement("canvas"); cv.width = cv.height = s;
  const g = cv.getContext("2d");
  g.beginPath(); g.arc(s / 2, s / 2, s / 2 - 8, 0, Math.PI * 2); g.fillStyle = color; g.fill();
  g.lineWidth = 9; g.strokeStyle = "#fff"; g.stroke();
  g.fillStyle = "#fff"; g.font = "600 60px Geist, Pretendard, sans-serif"; g.textAlign = "center"; g.textBaseline = "middle";
  g.fillText(text, s / 2, s / 2 + 3);
  return canvasTex(cv);
}
function labelTex(text) {
  const cv = document.createElement("canvas"), g = cv.getContext("2d"), font = "600 46px Geist, Pretendard, sans-serif";
  g.font = font; const w = Math.ceil(g.measureText(text).width) + 52, hgt = 80;
  cv.width = w; cv.height = hgt; g.font = font;
  g.fillStyle = "rgba(10,10,10,.9)"; g.beginPath(); g.roundRect(0, 0, w, hgt, 20); g.fill();
  g.fillStyle = "#fff"; g.textBaseline = "middle"; g.fillText(text, 26, hgt / 2 + 2);
  return { tex: canvasTex(cv), aspect: w / hgt };
}
function screenSprite(tex, px) {   // 화면에서 대략 px 높이로 보이는 스프라이트
  const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, depthTest: false, sizeAttenuation: false, transparent: true }));
  sp.renderOrder = 20; sp.userData.px = px; return sp;
}

// ── 지형 (로우폴리 + 고도 색) ────────────────────
function landColor(m, out) {
  const st = [[0, [0.86, 0.88, 0.78]], [15, [0.66, 0.80, 0.56]], [150, [0.50, 0.70, 0.43]],
    [500, [0.36, 0.56, 0.34]], [1000, [0.42, 0.47, 0.36]], [1500, [0.62, 0.60, 0.54]], [1900, [0.95, 0.95, 0.94]]];
  let i = 0; while (i < st.length - 2 && m > st[i + 1][0]) i++;
  const [m0, c0] = st[i], [m1, c1] = st[i + 1], t = Math.min(1, Math.max(0, (m - m0) / (m1 - m0)));
  for (let k = 0; k < 3; k++) out[k] = c0[k] + (c1[k] - c0[k]) * t;
}
function buildTerrain(P) {
  const { meta, h } = terrainData, { cols, rows } = meta;
  const pos = new Float32Array(cols * rows * 3), col = new Float32Array(cols * rows * 3), c = [0, 0, 0];
  for (let r = 0; r < rows; r++) for (let q = 0; q < cols; q++) {
    const i = r * cols + q, m = h[i];
    pos[i * 3] = P.x(meta.west + q * meta.dlon); pos[i * 3 + 2] = P.z(meta.north - r * meta.dlat);
    pos[i * 3 + 1] = m > 0 ? P.yOf(m) : -1.6;
    if (m > 0) landColor(m, c); else { c[0] = 0.72; c[1] = 0.84; c[2] = 0.89; }
    col.set(c, i * 3);
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
  const mesh = new THREE.Mesh(g, new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.92, metalness: 0 }));
  mesh.receiveShadow = true;
  return mesh;
}

// ── 3D 말 (기본 도형 조립, 머리는 +z) ─────────────
function buildHorse() {
  const coat = new THREE.MeshStandardMaterial({ color: 0x8a5a33, roughness: 0.75, flatShading: true });
  const dark = new THREE.MeshStandardMaterial({ color: 0x2b1d14, roughness: 0.8, flatShading: true });
  const blanket = new THREE.MeshStandardMaterial({ color: 0xea580c, roughness: 0.6, flatShading: true });
  const add = (parent, geo, mat, x, y, z, rx = 0, ry = 0, rz = 0) => {
    const m = new THREE.Mesh(geo, mat); m.position.set(x, y, z); m.rotation.set(rx, ry, rz);
    m.castShadow = true; parent.add(m); return m;
  };
  const horse = new THREE.Group(), body = new THREE.Group(); horse.add(body);
  add(body, new THREE.CapsuleGeometry(1.15, 3.2, 4, 10), coat, 0, 3.6, 0, Math.PI / 2);             // 몸통
  add(body, new THREE.BoxGeometry(2.5, 0.35, 2.4), blanket, 0, 4.75, -0.2);                         // 안장 담요
  add(body, new THREE.CylinderGeometry(0.55, 0.8, 2.6, 8), coat, 0, 5.0, 2.4, -0.75);              // 목
  const head = add(body, new THREE.BoxGeometry(0.85, 0.9, 2.0), coat, 0, 5.9, 3.55, 0.45);           // 머리
  add(head, new THREE.ConeGeometry(0.18, 0.5, 5), dark, 0.25, 0.6, -0.6);                            // 귀
  add(head, new THREE.ConeGeometry(0.18, 0.5, 5), dark, -0.25, 0.6, -0.6);
  add(body, new THREE.BoxGeometry(0.25, 0.6, 2.4), dark, 0, 5.55, 2.1, -0.75);                      // 갈기
  const tail = add(body, new THREE.CylinderGeometry(0.12, 0.35, 2.0, 6), dark, 0, 3.6, -3.0, -0.6); // 꼬리
  const legs = [];
  for (const [x, z] of [[0.6, 1.6], [-0.6, 1.6], [0.6, -1.5], [-0.6, -1.5]]) {
    const pivot = new THREE.Group(); pivot.position.set(x, 3.2, z); body.add(pivot);
    add(pivot, new THREE.CylinderGeometry(0.28, 0.22, 2.9, 6), coat, 0, -1.45, 0);
    add(pivot, new THREE.CylinderGeometry(0.3, 0.3, 0.35, 6), dark, 0, -3.0, 0);                     // 발굽
    legs.push(pivot);
  }
  horse.userData = { body, legs, tail, phase: 0 };
  horse.scale.setScalar(1.5);
  return horse;
}
function animateHorse(horse, speed, dt, t) {
  const u = horse.userData, run = Math.min(1, speed / 25);
  u.phase += dt * (4 + 10 * run);
  const s = Math.sin(u.phase), c = Math.cos(u.phase);
  u.legs[0].rotation.x = s * 0.9 * run; u.legs[1].rotation.x = -s * 0.9 * run;
  u.legs[2].rotation.x = -c * 0.9 * run; u.legs[3].rotation.x = c * 0.9 * run;
  u.body.position.y = Math.abs(s) * 0.5 * run + Math.sin(t / 600) * 0.06 * (1 - run);
  u.body.rotation.x = s * 0.05 * run;
  u.tail.rotation.x = -0.6 - run * 0.5 + c * 0.15;
}

// ── 3D 핀 마커 ──────────────────────────────────
function buildPin(num, color) {
  const g = new THREE.Group();
  const pole = new THREE.Mesh(new THREE.CylinderGeometry(0.18, 0.18, 7, 6), new THREE.MeshStandardMaterial({ color: 0x525252 }));
  pole.position.y = 3.5; pole.castShadow = true; g.add(pole);
  const headMat = new THREE.MeshStandardMaterial({ color, roughness: 0.4, metalness: 0.05 });
  const ball = new THREE.Mesh(new THREE.SphereGeometry(1.5, 16, 12), headMat);
  ball.position.y = 8; ball.castShadow = true; g.add(ball);
  const sp = screenSprite(numberTex(String(num), color), 26); sp.position.y = 11.5; g.add(sp);
  const ring = new THREE.Mesh(new THREE.RingGeometry(2.2, 3.2, 40), new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0, side: THREE.DoubleSide, depthWrite: false }));
  ring.rotation.x = -Math.PI / 2; ring.position.y = 0.6; g.add(ring);
  g.userData = { headMat, sp, ring, num, color };
  return g;
}
function styleMarker(g, state) {
  const u = g.userData; if (u.state === state) return; u.state = state;
  const col = state === "done" ? "#a3a3a3" : u.color;
  u.headMat.color.set(col);
  u.sp.material.map.dispose(); u.sp.material.map = numberTex(String(u.num), col); u.sp.material.needsUpdate = true;
  u.ring.material.opacity = state === "next" ? 0.75 : 0;
}

// ── 경로 (지형을 따라) ───────────────────────────
function draped(a, b, lift, step = 1.2) {
  const n = Math.max(1, Math.ceil(Math.hypot(b.x - a.x, b.z - a.z) / step)), out = [];
  for (let i = 0; i <= n; i++) {
    const x = a.x + (b.x - a.x) * (i / n), z = a.z + (b.z - a.z) * (i / n);
    out.push(new THREE.Vector3(x, groundY(x, z) + lift, z));
  }
  return out;
}
function withLengths(pts) {
  const L = [0]; for (let i = 1; i < pts.length; i++) L.push(L[i - 1] + pts[i].distanceTo(pts[i - 1]));
  return { pts, L, total: L[L.length - 1] || 1e-6 };
}
function pointAt(seg, f) {
  const d = Math.max(0, Math.min(1, f)) * seg.total;
  let i = 1; while (i < seg.L.length - 1 && seg.L[i] < d) i++;
  const t = (d - seg.L[i - 1]) / Math.max(1e-6, seg.L[i] - seg.L[i - 1]);
  return seg.pts[i - 1].clone().lerp(seg.pts[i], t);
}
function partialPoints(seg, f) {
  const d = Math.max(0, Math.min(1, f)) * seg.total, out = [seg.pts[0]];
  for (let i = 1; i < seg.pts.length; i++) { if (seg.L[i] >= d) break; out.push(seg.pts[i]); }
  out.push(pointAt(seg, f));
  return out;
}
function tube(points, radius, mat) {
  if (points.length < 2 || points[0].distanceTo(points[points.length - 1]) < 0.05) return null;
  const g = new THREE.TubeGeometry(new THREE.CatmullRomCurve3(points, false, "centripetal"), Math.max(4, points.length * 2), radius, 8, false);
  const m = new THREE.Mesh(g, mat); m.castShadow = false; return m;
}

// ── 장면 ────────────────────────────────────────
function pathRings(d) {
  return d.split(/[Mm]/).filter((s) => s.trim()).map((s) => {
    const n = (s.match(/-?\d*\.?\d+(?:e-?\d+)?/g) || []).map(Number), pts = [];
    for (let i = 0; i + 1 < n.length; i += 2) pts.push(new THREE.Vector3(n[i], 0, n[i + 1]));
    return pts;
  }).filter((r) => r.length > 2);
}

function init(map) {
  const P = makeProj(map);
  const canvas = document.createElement("canvas"); canvas.className = "terrain3d";
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(2, window.devicePixelRatio || 1));
  renderer.setClearColor(0x000000, 0);                       // 하늘은 CSS 그라데이션
  renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  const scene = new THREE.Scene();
  scene.fog = new THREE.Fog(SKY, 500, 1500);
  scene.add(new THREE.HemisphereLight(0xf4f8ff, 0x8a9a8c, 1.0));
  const sun = new THREE.DirectionalLight(0xfff1de, 2.2);
  sun.castShadow = true; sun.shadow.mapSize.set(2048, 2048);
  Object.assign(sun.shadow.camera, { left: -70, right: 70, top: 70, bottom: -70, near: 1, far: 600 });
  sun.shadow.bias = -0.0008; scene.add(sun, sun.target);
  view = { map, P, canvas, renderer, scene, sun, camera: new THREE.PerspectiveCamera(38, 2, 1, 3000),
    dyn: new THREE.Group(), cur: new THREE.Group(), key: null, idx: -1, size: [0, 0], raf: 0,
    f: 0, fTarget: 0, seg: null, markers: [], label: null, last: performance.now(),
    camPos: new THREE.Vector3(500, 300, 900), camLook: new THREE.Vector3(500, 0, 300),
    camPosT: new THREE.Vector3(), camLookT: new THREE.Vector3(), heading: new THREE.Vector3(0, 0, -1) };
  scene.add(buildTerrain(P));
  const sea = new THREE.Mesh(new THREE.CircleGeometry(2200, 64), new THREE.MeshStandardMaterial({ color: 0xb4d4e1, roughness: 0.55, metalness: 0 }));
  sea.rotation.x = -Math.PI / 2; sea.position.set(500, -0.4, 320); sea.receiveShadow = true; scene.add(sea);
  // 권역 경계: 점선으로 아주 옅게
  const lineMat = new THREE.LineDashedMaterial({ color: 0x3f3f46, dashSize: 3, gapSize: 3, transparent: true, opacity: 0.16 });
  for (const r of map.regions) for (const ring of pathRings(r.d)) {
    const pts = []; for (let i = 0; i < ring.length; i++) pts.push(...draped(ring[i], ring[(i + 1) % ring.length], 0.6, 4));
    const line = new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts), lineMat); line.computeLineDistances(); scene.add(line);
  }
  view.horse = buildHorse(); scene.add(view.horse, view.dyn, view.cur);
  return view;
}

function placeV(p) { const x = view.P.x(p.lon), z = view.P.z(p.lat); return new THREE.Vector3(x, groundY(x, z), z); }
function disposeGroup(g) {
  while (g.children.length) {
    const c = g.children.pop();
    c.traverse((o) => { o.geometry?.dispose?.(); if (o.material) { o.material.map?.dispose?.(); o.material.dispose?.(); } });
  }
}

function rebuildDay(pts, color) {
  disposeGroup(view.dyn);
  view.color = color;
  view.doneMat = new THREE.MeshStandardMaterial({ color, roughness: 0.5, emissive: color, emissiveIntensity: 0.15 });
  view.ghostMat = new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.25, depthWrite: false });
  view.places = pts.map(placeV);
  // 앞으로 갈 구간은 옅게 미리 보여준다
  for (let i = 1; i < pts.length; i++) {
    const m = tube(draped(view.places[i - 1], view.places[i], 0.9), 0.45, view.ghostMat); if (m) view.dyn.add(m);
  }
  view.markers = pts.map((p, i) => { const g = buildPin(i + 1, color); g.position.copy(view.places[i]); view.dyn.add(g); return g; });
  view.doneTubes = [];
}

function startSegment(idx) {
  // idx번 목적지로 가는 구간: 말의 지금 위치(지면) → 목적지
  const to = view.places[idx];
  disposeGroup(view.cur);
  if (!to) { view.seg = null; return; }
  const from = view.horse.position.clone(); from.y = groundY(from.x, from.z);
  view.seg = withLengths(draped(from, to, 1.0));
  view.f = 0; view.fTarget = 0; view.drawnF = -1;
  setLabel(view.items[idx].label, to.clone().setY(to.y + 13));
}

function finishSegment() {   // 현재 구간을 '지나온 길'로 확정
  if (!view.seg) return;
  const m = tube(view.seg.pts, 0.75, view.doneMat); if (m) view.dyn.add(m);
  disposeGroup(view.cur);
}

function setLabel(text, pos) {
  if (view.label) { view.dyn.remove(view.label); view.label.material.map.dispose(); view.label.material.dispose(); view.label = null; }
  if (!text) return;
  const { tex, aspect } = labelTex(text), sp = screenSprite(tex, 34);
  sp.userData.aspect = aspect; sp.center.set(0.5, 0); sp.position.copy(pos); view.dyn.add(sp); view.label = sp;
}

function resize() {
  const parent = view.canvas.parentElement; if (!parent) return;
  const w = parent.clientWidth, hgt = parent.clientHeight;
  if (w === view.size[0] && hgt === view.size[1]) return;
  view.size = [w, hgt]; view.renderer.setSize(w, hgt, false);
  view.camera.aspect = w / Math.max(1, hgt); view.camera.updateProjectionMatrix();
}

function frame(t) {
  if (!view.canvas.isConnected) { view.raf = 0; return; }
  view.raf = requestAnimationFrame(frame);
  resize();
  const dt = Math.min(0.05, (t - view.last) / 1000); view.last = t;
  const H = view.size[1] || 1;
  // 타이핑 진행만큼 선이 차오르고 말이 달린다
  let speed = 0;
  if (view.seg) {
    const prev = view.f;
    view.f += (view.fTarget - view.f) * Math.min(1, dt * 5);
    if (Math.abs(view.fTarget - view.f) < 0.001) view.f = view.fTarget;
    speed = Math.abs(view.f - prev) * view.seg.total / Math.max(dt, 1e-3);
    if (Math.abs(view.f - view.drawnF) > 0.004) {
      disposeGroup(view.cur);
      const m = tube(partialPoints(view.seg, view.f), 0.75, view.doneMat); if (m) view.cur.add(m);
      view.drawnF = view.f;
    }
    const pos = pointAt(view.seg, view.f); pos.y = groundY(pos.x, pos.z);
    const ahead = pointAt(view.seg, Math.min(1, view.f + 0.03));
    const dir = new THREE.Vector3(ahead.x - pos.x, 0, ahead.z - pos.z);
    if (dir.lengthSq() > 1e-4) view.heading.lerp(dir.normalize(), Math.min(1, dt * 6)).normalize();
    view.horse.position.copy(pos);
  }
  view.horse.lookAt(view.horse.position.clone().add(view.heading));
  animateHorse(view.horse, speed, dt, t);
  // 다음 목적지 고리 깜빡임
  for (const g of view.markers) if (g.userData.state === "next") { const k = 1 + 0.25 * Math.sin(t / 250); g.userData.ring.scale.set(k, k, k); }
  // 추격 카메라: 말 뒤 위쪽에서 목적지 방향을 본다. 남은 거리가 멀면 조금 멀리
  const target = view.seg ? view.seg.pts[view.seg.pts.length - 1] : view.horse.position;
  const remain = view.seg ? (1 - view.f) * view.seg.total : 0;
  const dist = Math.min(190, Math.max(85, remain * 0.55 + 70));
  const hp = view.horse.position;
  view.camPosT.set(hp.x - view.heading.x * dist, hp.y + dist * 0.78 + 10, hp.z - view.heading.z * dist);
  view.camLookT.copy(hp).lerp(target, remain > 1 ? 0.45 : 0).setY(hp.y + 4);
  view.camPos.lerp(view.camPosT, Math.min(1, dt * 2.2)); view.camLook.lerp(view.camLookT, Math.min(1, dt * 3));
  view.camera.position.copy(view.camPos); view.camera.lookAt(view.camLook);
  // 그림자는 말 주변만
  view.sun.position.set(hp.x - 120, hp.y + 160, hp.z - 60); view.sun.target.position.copy(hp);
  view.scene.traverse((o) => { if (o.isSprite && o.userData.px) { const s = (o.userData.px / H) * 0.69; o.scale.set(s * (o.userData.aspect || 1), s, 1); } });
  view.renderer.render(view.scene, view.camera);
}

// 타이핑 진행률 (0~1). 맞게 친 글자 수 ÷ 지명 글자 수
export function setProgress(f) { if (view?.seg) view.fTarget = Math.max(0, Math.min(1, f)); }

// items: 그 날 퀘스트 [{place_id, label}], idx: 다음 목적지 순번(0부터, 끝이면 길이)
export function Terrain3D({ map, places, items, idx, color }) {
  if (!view || view.map !== map) { if (view) { cancelAnimationFrame(view.raf); view.renderer.dispose(); } init(map); }
  const wrap = document.createElement("div"); wrap.className = "terrain-wrap"; wrap.appendChild(view.canvas);
  const key = items.map((x) => x.place_id).join("|");
  const pts = items.map((x) => places[x.place_id]);
  if (key !== view.key) {
    view.key = key; view.idx = -1; view.items = items;
    rebuildDay(pts, color);
    // 출발점: 첫 목적지 앞쪽 바깥에서 (그날 경로 반대 방향)
    const p0 = view.places[0], p1 = view.places[1] || p0.clone().add(new THREE.Vector3(10, 0, -10));
    const back = new THREE.Vector3(p0.x - p1.x, 0, p0.z - p1.z).normalize().multiplyScalar(14);
    const start = p0.clone().add(back); start.y = groundY(start.x, start.z);
    view.horse.position.copy(start); view.heading.set(-back.x, 0, -back.z).normalize();
    view.camPos.set(start.x - view.heading.x * 160, start.y + 140, start.z - view.heading.z * 160);
    view.camLook.copy(start);
  }
  if (idx !== view.idx) {
    if (view.idx >= 0 && idx === view.idx + 1) {               // 도착(또는 건너뛰기): 지나온 길 확정
      if (view.seg) { view.f = 1; view.horse.position.copy(view.seg.pts[view.seg.pts.length - 1]); }
      finishSegment();
    } else if (idx > 0) {                                       // 날짜를 바꾸거나 처음 열 때 중간부터
      for (let i = 1; i < idx; i++) { const m = tube(draped(view.places[i - 1], view.places[i], 1.0), 0.75, view.doneMat); if (m) view.dyn.add(m); }
      view.horse.position.copy(view.places[idx - 1]);
    }
    view.idx = idx;
    view.markers.forEach((g, i) => styleMarker(g, i < idx ? "done" : i === idx ? "next" : "todo"));
    if (idx < pts.length) startSegment(idx); else { view.seg = null; disposeGroup(view.cur); setLabel(null); }
  }
  if (!view.raf) { view.last = performance.now(); view.raf = requestAnimationFrame(frame); }
  return wrap;
}
