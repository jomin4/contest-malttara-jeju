import { h, icon, toast } from "../dom.js";
import { set, state } from "../state.js";
import { normalizeTyping, REACT, REACT_HINT, shortName } from "../format.js";
import { SvgMap, project, dayColor } from "../components/map.js";
import { DayList, DayTabs } from "./step2.js";

const REACT_KEYS = { 1: "interest", 2: "must", 3: "dislike" };
const REACT_ICON = { interest: "star", must: "pin", dislike: "x" };
let live = null;   // 최신 렌더의 동작 (전역 키 처리용)

// 도착 후 반응 고르기: 1·2·3 키, Enter는 다음 장소로 (입력창이 없을 때만)
document.addEventListener("keydown", (e) => {
  if (!live || state.step !== 3 || state.previewMode !== "game" || e.isComposing) return;
  if (state.game.awaiting) {
    if (REACT_KEYS[e.key]) { e.preventDefault(); live.choose(REACT_KEYS[e.key]); }
    else if (e.key === "Enter") { e.preventDefault(); live.next(); }
  } else if (live.dayDone && e.key === "Enter") { e.preventDefault(); live.dayNext(); }
});

const goStep4 = (A) => { set({ batchB: null }); A.go(4); };

let typedBuf = { key: "", v: "" };   // 화면이 다시 그려져도(3D→2D 전환 등) 치던 글자를 유지

// 3D 첫 3초 평균 프레임이 낮으면(저사양) 2D 지도로 자동 전환. 사용자는 버튼으로 다시 3D를 켤 수 있다.
function watchFps() {
  let n = 0, t0 = 0;
  const tick = (t) => {
    if (!t0) t0 = t;
    n++;
    if (t - t0 < 3000) return requestAnimationFrame(tick);
    const fps = (n * 1000) / (t - t0);
    if (fps < 20 && state.map3d && state.step === 3) {
      set({ map3d: false });
      toast("이 PC에서는 3D가 느려서 2D 지도로 바꿨어요. 위쪽 3D 버튼으로 다시 켤 수 있어요.", 4500);
    }
  };
  setTimeout(() => requestAnimationFrame(tick), 1500);   // 지형 올라오는 첫 순간은 빼고 잰다
}

function Game(st, ctx, A, r) {
  const quests = r.quests;
  const q0 = quests.find((x) => x.day === st.game.day) || quests[0];
  const q = { ...q0, items: q0.items.map((it) => ({ ...it, label: shortName(it.label) })) };   // 메모형 이름은 짧게 쳐도 되게
  const idx = st.game.idx;
  const awaiting = st.game.awaiting;            // 방금 도착한 장소 (반응 고르는 중)
  const cur = q.items[idx];
  const done = idx >= q.items.length;
  const P = r.places;
  const nextDay = quests.find((x) => x.day === q.day + 1);

  // 2D 폴백용 확대 범위
  const pos = (id) => project(P[id].lat, P[id].lon, ctx.map.project);
  const lastArrived = idx > 0 ? q.items[idx - 1].place_id : null;
  const horseAt = lastArrived ? pos(lastArrived) : (() => { const [x, y] = pos(q.items[0].place_id); return [x - 34, y + 10]; })();
  const dayItin = { days: r.itinerary.days.filter((d) => d.day === q.day) };
  const [, , MW, MH] = ctx.map.view_box.split(" ").map(Number);
  const pts = q.items.map((it) => pos(it.place_id)), xs = pts.map((p) => p[0]), ys = pts.map((p) => p[1]);
  const AR = 2.4;
  let vw = Math.max(Math.max(...xs) - Math.min(...xs) + 260, 560), vh = vw / AR;
  if (Math.max(...ys) - Math.min(...ys) + 160 > vh) { vh = Math.max(...ys) - Math.min(...ys) + 160; vw = vh * AR; }
  const cx = (Math.max(...xs) + Math.min(...xs)) / 2, cy = (Math.max(...ys) + Math.min(...ys)) / 2;
  const zoomBox = `${Math.min(Math.max(cx - vw / 2, -40), MW - vw + 40).toFixed(0)} ${Math.min(Math.max(cy - vh / 2, -40), MH - vh + 40).toFixed(0)} ${vw.toFixed(0)} ${vh.toFixed(0)}`;

  // 3D는 하드웨어 가속일 때만: 소프트웨어 렌더링(드라이버 차단·원격 데스크톱 등)이면 처음부터 2D
  const can3d = ctx.webgl ?? (ctx.webgl = (() => { try {
    const c = document.createElement("canvas"), o = { failIfMajorPerformanceCaveat: true };
    return !!(c.getContext("webgl2", o) || c.getContext("webgl", o));
  } catch { return false; } })());
  if (can3d && !ctx.terrainState) queueMicrotask(() => A.loadTerrain());
  const use3d = can3d && st.map3d && ctx.terrainState === "ready";
  if (use3d && !ctx.fpsChecked) { ctx.fpsChecked = true; watchFps(); }

  const setGame = (patch) => set({ game: { ...state.game, ...patch } });
  const arriveAt = (arrived) => {
    if (arrived) A.arrive(cur.place_id);
    setGame({ idx: idx + 1, awaiting: arrived ? cur.place_id : null });
  };
  live = {
    choose: (v) => { if (!state.game.awaiting) return; A.react(state.game.awaiting, v); setTimeout(() => setGame({ awaiting: null }), 350); },
    next: () => setGame({ awaiting: null }),
    dayDone: done && !awaiting,
    dayNext: () => (nextDay ? set({ game: { day: nextDay.day, idx: 0, awaiting: null } }) : goStep4(A)),
  };

  const paint = (n) => {   // 띄어쓰기를 뺀 n글자까지 강조 (표시는 원래 띄어쓰기 유지)
    let seen = 0, cut = 0;
    for (const ch of cur.label) { if (seen >= n) break; cut++; if (!/\s/.test(ch)) seen++; }
    const t = document.getElementById("typed"), u = document.getElementById("untyped");
    if (t) t.textContent = cur.label.slice(0, cut);
    if (u) u.textContent = cur.label.slice(cut);
  };
  const tkey = `${q.day}:${idx}`;
  const onInput = (e) => {
    typedBuf = { key: tkey, v: e.target.value };
    if (e.isComposing) return;
    const v = normalizeTyping(e.target.value), target = normalizeTyping(cur.label);
    let n = 0; while (n < v.length && v[n] === target[n]) n++;
    paint(n);
    if (use3d) ctx.T3.setProgress(n / Math.max(1, target.length));   // 메트로타이핑: 친 만큼 선·말 이동
    if (v === target) arriveAt(true);
  };
  const onKey = (e) => {
    if (e.key !== "Enter" || e.isComposing || e.keyCode === 229) return;
    e.preventDefault();
    if (normalizeTyping(e.target.value) === normalizeTyping(cur.label)) { arriveAt(true); return; }
    e.target.classList.remove("shake"); void e.target.offsetWidth; e.target.classList.add("shake");
    const hint = document.getElementById("hint"); if (hint) hint.textContent = `글자 수 힌트: ${normalizeTyping(cur.label).length}자 (띄어쓰기 무시)`;
  };
  if (!done && !awaiting) queueMicrotask(() => { const el = document.getElementById("typein"); if (!el) return; el.focus({ preventScroll: true }); if (el.value) { const n = el.value.length; try { el.setSelectionRange(n, n); } catch { /* */ } const v = normalizeTyping(el.value), tg = normalizeTyping(cur.label); let m = 0; while (m < v.length && v[m] === tg[m]) m++; paint(m); } });

  // ── 아래 패널: 입력 → 도착·반응 → 하루 완료 ──
  let bar;
  if (awaiting) {
    const p = P[awaiting], chosen = st.feedback[awaiting];
    bar = h("div", { class: "typebar arrived" },
      h("div", { class: "arr-head" },
        h("div", {}, h("div", { class: "arr-kicker" }, "가상 도착! 이곳은 어떤 것 같나요?"),
          h("div", { class: "arr-name", title: p.name }, shortName(p.name), h("span", { class: "arr-meta" }, `${p.category ?? "분류 없음"} · ${p.region_name}`))),
        h("button", { class: "btn btn-lg", onclick: live.next }, idx < q.items.length ? "다음 장소로" : "넘어가기", h("span", { class: "kbd" }, "Enter"))),
      h("div", { class: "react big" }, ["interest", "must", "dislike"].map((v, i) => h("button", {
        class: `${v} ${chosen === v ? "on" : ""}`, onclick: () => live.choose(v) },
        h("span", { class: "keycap" }, i + 1),
        h("span", { class: "rb" }, h("span", { class: "rb-t" }, icon(REACT_ICON[v], 18), REACT[v]), h("span", { class: "rb-h" }, REACT_HINT[v]))))),
      h("div", { class: "hint" }, "숫자 키 1·2·3으로 고를 수 있어요. 고르지 않아도 됩니다. 가상 도착은 실제 방문 기록이 아니에요."));
  } else if (done) {
    bar = h("div", { class: "typebar arrived" },
      h("div", { class: "arr-head" },
        h("div", {}, h("div", { class: "arr-kicker" }, `${q.day}일차 완료`),
          h("div", { class: "arr-name" }, nextDay ? `${nextDay.day}일차로 이어서 달릴까요?` : "모든 날을 둘러봤어요")),
        h("button", { class: "btn btn-primary btn-lg", onclick: live.dayNext }, nextDay ? `${nextDay.day}일차로` : "반영해서 다시 짜기", h("span", { class: "kbd kbd-dark" }, "Enter"))));
  } else {
    bar = h("div", { class: "typebar" },
      h("div", {},
        h("div", { class: "target" }, h("span", { class: "lbl" }, `다음 목적지 ${idx + 1}/${q.items.length}`),
          h("span", { class: "name" }, h("span", { class: "typed", id: "typed" }), h("span", { id: "untyped" }, cur.label))),
        h("input", { class: "typein", id: "typein", autocomplete: "off", spellcheck: "false", placeholder: "위 지명을 그대로 입력하세요 — 친 만큼 말이 달려가요", oninput: onInput, onkeydown: onKey,
          value: typedBuf.key === tkey ? typedBuf.v : "",
          oncompositionend: (e) => onInput({ isComposing: false, target: e.target }) }),
        h("div", { class: "hint", id: "hint" }, "띄어쓰기는 무시해요. 어려우면 ‘건너뛰기’나 ‘목록’으로 보세요.")),
      h("div", { style: { display: "flex", flexDirection: "column", gap: "10px", alignItems: "flex-end" } },
        h("div", { class: "progress" }, q.items.map((_, i) => h("i", { class: i < idx ? "done" : i === idx ? "cur" : "" }))),
        h("button", { class: "btn", onclick: () => arriveAt(false) }, icon("skip", 15), "건너뛰기")));
  }

  const c = (v) => Object.values(st.feedback).filter((x) => x === v).length;
  return h("div", { class: "card stage" + (use3d ? " game3d" : "") },
    h("div", { class: "card-head stage-head" },
      h("div", { class: "stage-left" },
        h("div", { class: "card-title" }, h("span", { class: "pnum", style: { background: dayColor(q.day), width: "26px", height: "26px", fontSize: "12px" } }, q.day), `${q.day}일차`),
        h("div", { class: "daytabs" }, quests.map((x) => h("button", { class: "daytab" + (x.day === q.day ? " on" : ""), onclick: () => set({ game: { day: x.day, idx: 0, awaiting: null } }) },
          h("span", { class: "sw", style: { background: dayColor(x.day) } }), `${x.day}일차`)))),
      h("div", { class: "stage-right" },
        h("div", { class: "tally" }, h("span", {}, "좋아요 ", h("b", {}, c("interest"))), h("span", {}, "꼭 갈래요 ", h("b", {}, c("must"))), h("span", {}, "별로예요 ", h("b", {}, c("dislike")))),
        can3d ? h("div", { class: "seg" },
          h("button", { class: st.map3d ? "on" : "", onclick: () => set({ map3d: true }) }, ctx.terrainState === "loading" ? "3D…" : "3D"),
          h("button", { class: st.map3d ? "" : "on", onclick: () => set({ map3d: false }) }, "2D")) : null,
        h("div", { class: "seg" },
          h("button", { class: "on" }, "게임"),
          h("button", { onclick: () => set({ previewMode: "list" }) }, "목록")),
        h("button", { class: "btn btn-primary", onclick: () => goStep4(A) }, "다시 짜기", icon("arrow", 15)))),
    h("div", { class: "stage-map" },
      use3d
        ? ctx.T3.Terrain3D({ map: ctx.map, places: P, items: q.items, idx, color: dayColor(q.day) })
        : SvgMap({ map: ctx.map, itinerary: dayItin, places: P, horseAt, showLabels: true, viewBox: zoomBox, zoom: Math.min(1, vw / 900),
            markerState: (id, day, i) => (i < idx ? "done" : i === idx ? "next" : "") }),
      use3d ? h("div", { class: "terrain-credit" }, ctx.T3.terrainAttribution()) : null),
    bar);
}

export function Step3(st, ctx, A) {
  const r = st.batchA?.result;
  if (!r) return h("div", { class: "page" }, "경로가 아직 없습니다.");
  if (st.previewMode === "game") { return h("div", { class: "page page-game" }, Game(st, ctx, A, r)); }
  live = null;
  const c = (v) => Object.values(st.feedback).filter((x) => x === v).length;
  return h("div", { class: "page" },
    h("div", { class: "pagehead" },
      h("div", {}, h("div", { class: "eyebrow" }, "03 미리 둘러보기"),
        h("h1", {}, "장소를 보고 반응을 남겨 주세요"),
        h("div", { class: "muted lead" }, "좋아요는 비슷한 곳을 더, 꼭 갈래요는 고정, 별로예요는 다른 곳으로 바꿔요.")),
      h("div", { class: "actions" },
        h("div", { class: "seg seg-lg" },
          h("button", { onclick: () => set({ previewMode: "game" }) }, "게임으로 보기"),
          h("button", { class: "on" }, "목록으로 보기")))),
    h("div", { class: "list-wrap" }, h("div", { style: { marginBottom: "8px" } }, DayTabs(st, r.itinerary, r.places)), DayList(st, ctx, A, r, { onReact: (id, v) => A.react(id, v) })),
    h("div", { class: "footer-cta" },
      h("div", { class: "tally" }, h("span", {}, "좋아요 ", h("b", {}, c("interest"))), h("span", {}, "꼭 갈래요 ", h("b", {}, c("must"))), h("span", {}, "별로예요 ", h("b", {}, c("dislike"))),
        h("span", {}, "· 반응이 없어도 괜찮아요")),
      h("button", { class: "btn btn-primary btn-lg", onclick: () => goStep4(A) }, "반영해서 다시 짜기", icon("arrow", 16))));
}
