// 목업 서버 (주소에 ?mock=1). 계약 모양 그대로 응답한다. 장소명·수치는 모두 모의 값.
const cache = {};
const load = async (name) => (cache[name] ??= await (await fetch(`mock/${name}.json`)).json());

const INTEREST_CATS = { "바다": ["해수욕장", "해변"], "오름": ["오름"], "숲": ["숲길"], "실내·전시": ["박물관"],
  "체험·레저": ["체험"], "음식": ["음식점"], "카페": ["카페"] };
const SLOTS = ["음식", "카페"];
const REGION_ORDER = ["west", "south", "east", "city"];
const K = { "여유롭게": 3, "보통": 4, "빡빡하게": 5 };

const batches = {};
const feedback = {}; // batch_id -> {place_id: value}

const pad = (n) => String(n).padStart(2, "0");
function newId(kind) {
  const d = new Date();
  return `${kind}-${pad(d.getMonth() + 1)}${pad(d.getDate())}-${pad(d.getHours())}${pad(d.getMinutes())}${pad(d.getSeconds())}`;
}
function hav(a, b) {
  const R = 6371, r = Math.PI / 180;
  const dLat = (b.lat - a.lat) * r, dLon = (b.lon - a.lon) * r;
  const x = Math.sin(dLat / 2) ** 2 + Math.cos(a.lat * r) * Math.cos(b.lat * r) * Math.sin(dLon / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(x));
}
const r1 = (x) => Math.round(x * 10) / 10;
function routeOf(day, ids, P) {
  const legs = [];
  for (let i = 1; i < ids.length; i++) legs.push(r1(hav(P[ids[i - 1]], P[ids[i]])));
  return { day, legs_km: legs, total_km: r1(legs.reduce((a, b) => a + b, 0)) };
}
function nnOrder(ids, P) {
  if (ids.length < 2) return ids;
  const rest = ids.slice(1), out = [ids[0]];
  while (rest.length) {
    const last = P[out[out.length - 1]];
    rest.sort((a, b) => hav(last, P[a]) - hav(last, P[b]));
    out.push(rest.shift());
  }
  return out;
}

function matches(p, interests) {
  return interests.filter((k) => (INTEREST_CATS[k] || []).includes(p.category));
}

function explain(p, interests) {
  const out = [];
  const m = matches(p, interests);
  if (m.length) out.push(`관심사 '${m[0]}' ↔ 분류 '${p.category}' 일치`);
  else if (interests.length) out.push("관심사와 일치하는 분류 아님 (권역 내 점수 상위로 포함)");
  const reg = p.indicators.region, nb = p.indicators.nearby;
  out.push(reg.missing ? `${reg.emd} 읍면동 지표 없음 → 중립값으로 계산` : `${reg.emd} 방문/거주 비율 ${reg.visit_ratio} (563, 범위 내 백분위 ${Math.round(reg.pct * 100)})`);
  out.push(nb.missing ? "장소 반경 지표 없음 → 중립값으로 계산" : `장소 반경 ${nb.radius_km}km 렌터카 체류 ${nb.quiet_count}건 (1208)`);
  return out;
}

async function buildA(goal, inject) {
  const P = await load("places");
  const interests = goal.interests || [];
  const k = K[goal.pace] || 4;
  const days = goal.days;
  const regs = [];
  for (let d = 0; d < days; d++) regs.push(REGION_ORDER[d % REGION_ORDER.length]);
  const used = new Set();
  const itin = { days: [] };
  const alternatives = {};
  for (let d = 0; d < days; d++) {
    const rid = regs[d];
    const cands = Object.values(P).filter((p) => p.region_id === rid && !used.has(p.place_id));
    const rank = (p) => (interests.length ? (matches(p, interests).length ? 1 : 0) * 0.6 : 0.6) + p.score * 0.4;
    const pick = [];
    for (const sk of SLOTS) {
      if (!interests.includes(sk)) continue;
      const c = cands.filter((p) => (INTEREST_CATS[sk] || []).includes(p.category)).sort((a, b) => b.score - a.score)[0];
      if (c && pick.length < k) pick.push(c.place_id);
    }
    const general = cands.filter((p) => !["음식점", "카페"].includes(p.category) && !pick.includes(p.place_id))
      .sort((a, b) => rank(b) - rank(a) || (a.place_id < b.place_id ? -1 : 1));
    for (const p of general) { if (pick.length >= k) break; pick.push(p.place_id); }
    pick.sort((a, b) => P[b].score - P[a].score);
    const ordered = nnOrder(pick, P);
    ordered.forEach((id) => used.add(id));
    itin.days.push({ day: d + 1, region_id: rid, place_ids: ordered });
  }
  // 대안: 같은 권역 미사용 상위 2개
  for (const dd of itin.days) {
    const pool = Object.values(P).filter((p) => p.region_id === dd.region_id && !used.has(p.place_id)).sort((a, b) => b.score - a.score);
    for (const id of dd.place_ids) alternatives[id] = pool.slice(0, 2).map((p) => p.place_id);
  }
  const places = {};
  const addP = (id) => { places[id] = P[id]; };
  itin.days.forEach((d) => d.place_ids.forEach(addP));
  Object.values(alternatives).flat().forEach(addP);
  const routes = itin.days.map((d) => routeOf(d.day, d.place_ids, P));
  const explanations = {};
  itin.days.forEach((d) => d.place_ids.forEach((id) => { explanations[id] = explain(P[id], interests); }));
  const inItin = itin.days.flatMap((d) => d.place_ids).map((id) => P[id]);
  const quality = {
    no_category: inItin.filter((p) => !p.category).length,
    no_region_indicator: inItin.filter((p) => p.indicators.region.missing).length,
    no_nearby_indicator: inItin.filter((p) => p.indicators.nearby.missing).length,
  };
  const regionNames = itin.days.map((d) => P[d.place_ids[0]]?.region_name).join(" · ");
  const id = newId("A");
  const result = {
    batch_id: id, kind: "A", prev_batch_id: null, goal, itinerary: itin, places, routes,
    violations_remaining: [], explanations,
    summary: `${days}일 일정을 ${regionNames} 순서로 하루 한 권역씩 묶었습니다. 하루 ${k}곳은 여유 조건(${goal.pace ?? "미반영·보통 기준"})에서 정했고, 장소 순서는 점수가 가장 높은 곳에서 시작해 가까운 곳으로 이어집니다. 관심사가 같은 장소끼리는 읍면동 방문 집중도(563)와 장소 주변 체류(1208)가 낮은 쪽을 앞에 두었습니다.`,
    quests: itin.days.map((d) => ({ day: d.day, items: d.place_ids.map((pid) => ({ place_id: pid, label: P[pid].name.replace(/\s+/g, " ") })) })),
    alternatives, quality, diff: null,
  };

  // 실행 로그
  const ev = [];
  const e = (tool, actor, status, message, wait = 380) => ev.push({ tool, actor, status, message, wait });
  e("plan_tasks", "llm", "ok", `필수 6단계 고정 · 관심사 ${interests.length ? interests.join("·") : "없음"}`, 900);
  if (interests.some((x) => SLOTS.includes(x))) e("plan_tasks", "llm", "add", `음식점·카페 탐색 추가 (관심사: ${interests.filter((x) => SLOTS.includes(x)).join("·")})`, 200);
  if (goal.quiet_pref) e("plan_tasks", "llm", "add", "한적함 요청 → get_region_data 추가, 가중치 0.4 / 0.3 / 0.3", 200);
  e("search_places", "code", "ok", `후보 ${Object.keys(P).length}곳 → 권역 ${new Set(regs).size}개에서 점수 계산`);
  e("get_region_data", "code", goal.quiet_pref ? "ok" : "skip", goal.quiet_pref ? "권역별 방문/거주 비율 비교 (563)" : "한적함 요청 없음 → 생략");
  const trendN = inItin.filter((p) => p.has_trend).length;
  e("analyze_tourism", "code", trendN ? "add" : "skip", trendN ? `189·190 매칭 장소 ${trendN}곳 → 입장객 추이 추가` : "매칭 장소 없음 → 생략");
  e("check_data_quality", "code", "ok", `분류 없음 ${quality.no_category} · 읍면동 지표 없음 ${quality.no_region_indicator} · 반경 지표 없음 ${quality.no_nearby_indicator}`);
  e("create_itinerary", "code", "ok", `${days}일 × ${k}곳 · ${regionNames}`);
  e("calculate_route", "code", "ok", routes.map((r) => `${r.day}일차 ${r.total_km}km`).join(" · "));
  if (inject && itin.days.length > 1) {
    const d1 = itin.days[0], other = itin.days[itin.days.length - 1].place_ids[0];
    const tmp = routeOf(1, [...d1.place_ids, other], P);
    e("inject_error", "code", "add", `시연: 1일차에 ${P[other].region_name} 장소 '${P[other].name}' 끼워 넣음`, 500);
    e("validate_itinerary", "code", "fail", `1일차 권역 2곳 방문(기준 1)${tmp.total_km > 60 ? ` · 직선 ${tmp.total_km}km > 60km` : ""}`, 600);
    e("revise_itinerary", "llm", "fix", `허용 행동 중 '제외' 선택 → '${P[other].name}' 제외, ${P[d1.place_ids[0]].region_name} 장소 유지`, 1100);
    e("validate_itinerary", "code", "ok", "재검증 위반 0건 (수정 1회)");
  } else {
    e("validate_itinerary", "code", "ok", "위반 0건");
  }
  e("explain_decisions", "llm", "ok", "근거 문장 정리 (수치는 템플릿 슬롯 값)", 900);
  e("save_agent_state", "code", "ok", `${id} 저장`);
  return { id, ev, result };
}

async function buildB(prevId) {
  const P = await load("places");
  const A = batches[prevId].result;
  const fb = feedback[prevId] || {};
  const k = K[A.goal.pace] || 4;
  const used = new Set(A.itinerary.days.flatMap((d) => d.place_ids));
  const diff = [];
  const days = A.itinerary.days.map((d) => {
    const ids = [];
    for (const id of d.place_ids) {
      const v = fb[id];
      if (v === "must") { ids.push(id); diff.push({ place_id: id, change: "pin", replaced_by: null, day: d.day, reason: "꼭 갈래요 → 고정" }); }
      else if (v === "dislike") {
        const alt = (A.alternatives[id] || []).find((x) => !used.has(x));
        if (alt) { used.add(alt); ids.push(alt); diff.push({ place_id: id, change: "replace", replaced_by: alt, day: d.day, reason: "별로예요 → 같은 권역 대안으로 교체" }); }
        else diff.push({ place_id: id, change: "remove", replaced_by: null, day: d.day, reason: "별로예요 → 같은 권역 대안 없음, 제외" });
      } else {
        ids.push(id);
        diff.push({ place_id: id, change: "keep", replaced_by: null, day: d.day, reason: v === "interest" ? "관심 → 유지, 같은 분류 가중 +0.2" : "반응 없음 → 유지" });
      }
    }
    // 관심 분류 가중으로 빈 자리 채우기
    if (ids.length < k) {
      const likedCats = new Set(Object.entries(fb).filter(([, v]) => v === "interest").map(([pid]) => P[pid]?.category));
      const add = Object.values(P).filter((p) => p.region_id === d.region_id && !used.has(p.place_id))
        .sort((a, b) => (likedCats.has(b.category) - likedCats.has(a.category)) || b.score - a.score)[0];
      if (add) { used.add(add.place_id); ids.push(add.place_id); diff.push({ place_id: add.place_id, change: "add", replaced_by: null, day: d.day, reason: likedCats.has(add.category) ? `관심 분류 '${add.category}' 가중 → 추가` : "빈 자리 → 권역 점수 상위 추가" }); }
    }
    return { day: d.day, region_id: d.region_id, place_ids: ids };
  });
  const itin = { days };
  const places = { ...A.places };
  days.forEach((d) => d.place_ids.forEach((id) => { places[id] = P[id]; }));
  diff.forEach((x) => { places[x.place_id] = P[x.place_id]; if (x.replaced_by) places[x.replaced_by] = P[x.replaced_by]; });
  const routes = days.map((d) => routeOf(d.day, d.place_ids, P));
  const explanations = { ...A.explanations };
  days.forEach((d) => d.place_ids.forEach((id) => { if (!explanations[id]) explanations[id] = explain(P[id], A.goal.interests || []); }));
  const id = newId("B");
  const cnt = (v) => Object.values(fb).filter((x) => x === v).length;
  const ev = [];
  const e = (tool, actor, status, message, wait = 380) => ev.push({ tool, actor, status, message, wait });
  e("analyze_feedback", "code", "ok", `관심 ${cnt("interest")} · 꼭 갈래요 ${cnt("must")} · 별로예요 ${cnt("dislike")} · 가상 도착 ${Object.keys(batches[prevId].arrived || {}).length}`, 500);
  e("decide_keep_replace", "llm", "ok", `고정 ${diff.filter((x) => x.change === "pin").length} · 교체 ${diff.filter((x) => x.change === "replace").length} · 추가 ${diff.filter((x) => x.change === "add").length} · 유지 ${diff.filter((x) => x.change === "keep").length}`, 1000);
  if (diff.some((x) => x.change === "replace" || x.change === "add")) e("search_places", "code", "ok", "같은 권역 미사용 후보에서 대체 장소 탐색");
  e("calculate_route", "code", "ok", routes.map((r) => `${r.day}일차 ${r.total_km}km`).join(" · "));
  e("validate_itinerary", "code", "ok", "위반 0건");
  e("compare_itineraries", "code", "ok", `변경 ${diff.filter((x) => x.change !== "keep").length}건`);
  e("explain_decisions", "llm", "ok", "변경 이유 정리", 800);
  e("save_agent_state", "code", "ok", `${id} 저장 (이전 ${prevId})`);
  const result = { ...A, batch_id: id, kind: "B", prev_batch_id: prevId, itinerary: itin, places, routes, explanations, diff,
    summary: `탐색 반응을 반영해 다시 짰습니다. 꼭 갈래요는 고정하고, 별로예요는 같은 권역의 대안으로 바꿨습니다. 나머지는 이전 일정을 유지했습니다.`,
    quests: days.map((d) => ({ day: d.day, items: d.place_ids.map((pid) => ({ place_id: pid, label: P[pid].name })) })) };
  return { id, ev, result };
}

function schedule(b) {
  let t = Date.now() + 300;
  b.ev = b.ev.map((x, i) => { t += x.wait; return { seq: i + 1, batch_id: b.id, tool: x.tool, actor: x.actor, status: x.status, message: x.message, at: t, ts: new Date(t).toISOString().slice(0, 19) }; });
  b.doneAt = t + 200;
  batches[b.id] = b;
  return b.id;
}

function parse(text) {
  const t = text || "";
  const g = { nights: null, days: null, pace: null, interests: [], quiet_pref: false, transport: null, companion: null, origin: null, month: null, evidence: {} };
  let m;
  if ((m = t.match(/(\d+)\s*박\s*(\d+)\s*일/))) { g.nights = +m[1]; g.days = +m[2]; g.evidence.days = m[0]; }
  else if ((m = t.match(/당일/))) { g.nights = 0; g.days = 1; g.evidence.days = m[0]; }
  if ((m = t.match(/여유|느긋|천천히/))) { g.pace = "여유롭게"; g.evidence.pace = m[0]; }
  else if ((m = t.match(/빡빡|알차게|많이/))) { g.pace = "빡빡하게"; g.evidence.pace = m[0]; }
  const TRG = { "바다": ["바다", "해변", "해수욕"], "오름": ["오름"], "숲": ["숲", "산책", "휴양림"], "실내·전시": ["박물관", "미술관", "전시", "실내"],
    "체험·레저": ["체험", "레저", "액티비티"], "음식": ["음식", "맛집", "식당", "먹고"], "카페": ["카페", "커피"] };
  const ev = [];
  for (const [k, ws] of Object.entries(TRG)) { const w = ws.find((x) => t.includes(x)); if (w) { g.interests.push(k); ev.push(w); } }
  if (ev.length) g.evidence.interests = ev.join(", ");
  if ((m = t.match(/조용|한적|덜 붐비|사람 적/))) { g.quiet_pref = true; g.evidence.quiet_pref = m[0]; }
  if ((m = t.match(/렌터카|렌트카|자동차/))) { g.transport = "렌터카"; g.evidence.transport = m[0]; }
  else if ((m = t.match(/버스/))) { g.transport = "버스"; g.evidence.transport = m[0]; }
  else if ((m = t.match(/도보|걸어서/))) { g.transport = "도보"; g.evidence.transport = m[0]; }
  if ((m = t.match(/(아이와 함께|아이와|아이랑|혼자|친구와|친구랑|가족과|가족이랑|부모님과|연인과)/))) { g.companion = m[1].replace(/와$|랑$|과$|이랑$/, "").replace(" 함께", "") + (m[1].includes("혼자") ? "" : "와 함께"); g.evidence.companion = m[0]; }
  if ((m = t.match(/(1[0-2]|[1-9])\s*월/))) { g.month = +m[1]; g.evidence.month = m[0]; }
  const missing = g.days == null ? ["days"] : [];
  return { goal: g, missing, actor: "rule" };
}

const wait = (ms) => new Promise((ok) => setTimeout(ok, ms));

export const api = {
  health: async () => ({ ok: true, llm_available: true, data_version: "mock" }),
  config: () => load("config"),
  map: () => load("map"),
  emdStats: async (month) => (await load("stats_emd"))[String(month || 0)],
  emdStatsAll: async () => {
    const all = await load("stats_emd");
    const months = {}; for (let m = 1; m <= 12; m++) months[m] = all[m].items;
    return { period: all["0"].period, source_id: "563", months };
  },
  parseGoal: async (text) => { await wait(450); return parse(text); },
  startBatchA: async (goal, inject) => { await wait(150); return schedule(await buildA(goal, inject)); },
  startBatchB: async (prevId) => { await wait(150); return schedule(await buildB(prevId)); },
  events: async (id, after) => {
    const b = batches[id];
    if (!b) throw new Error("없는 배치입니다");
    const now = Date.now();
    return { events: b.ev.filter((x) => x.seq > after && x.at <= now).map(({ at, ...x }) => x), done: now >= b.doneAt, result: now >= b.doneAt ? b.result : null, error: null };
  },
  postEvent: async (e) => {
    if (e.type === "feedback") (feedback[e.batch_id] ??= {})[e.place_id] = e.value;
    if (e.type === "virtual_arrival") (batches[e.batch_id].arrived ??= {})[e.place_id] = true;
    return { ok: true };
  },
  trend: async (id) => (await load("trend"))[id] || { place_id: id, period: null, source_ids: ["189", "190"], series: [] },
  printUrl: () => null,
};
