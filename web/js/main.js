import { h, s as svgEl, clear, icon, toast } from "./dom.js";
import { state, set, reset, subscribe, maxStep } from "./state.js";
import { api, pollBatch, MOCK } from "./api.js";
import { ctx } from "./ctx.js";
import { Step1 } from "./screens/step1.js";
import { Step2 } from "./screens/step2.js";
import { Step3 } from "./screens/step3.js";
import { Step4 } from "./screens/step4.js";

const root = document.getElementById("app");
// 시연용 기능(오류 주입 토글 등)은 ?demo=1 또는 Ctrl+Shift+D 로만 보인다
ctx.demo = new URLSearchParams(location.search).get("demo") === "1";
let aborts = [];

// ── 동작 ─────────────────────────────────────────
export const actions = {
  async parse() {
    const text = state.text.trim();
    if (!text) { toast("여행을 한 줄로 적어 주세요"); return; }
    const sid = state.session_id;
    set({ parsing: true, openChip: null });
    try {
      const r = await api.parseGoal(text);
      if (sid !== state.session_id) return;
      set({ goal: r.goal, missing: r.missing, parseActor: r.actor, parsing: false, batchA: null, batchB: null, feedback: {}, arrived: {} });
      if (r.goal.month) actions.loadStats(r.goal.month);
    } catch (e) {
      if (sid !== state.session_id) return;
      set({ parsing: false }); toast(e.message, 3500);
    }
  },
  editGoal(patch) {
    const g = { ...state.goal, ...patch, evidence: { ...(state.goal?.evidence || {}) } };
    for (const k of Object.keys(patch)) delete g.evidence[k === "nights" ? "days" : k];
    if ("days" in patch) g.nights = patch.days == null ? null : patch.days - 1;
    const missing = g.days == null ? ["days"] : [];
    set({ goal: g, missing, batchA: null, batchB: null, feedback: {}, arrived: {} });
    if ("month" in patch) actions.loadStats(patch.month);
  },
  async loadStats(month) {
    const m = month || 0;
    if (ctx.stats[m]) { set({}); return; }
    try { ctx.stats[m] = await api.emdStats(m || null); set({}); } catch (e) { toast(e.message); }
  },
  // 월별 1~12 통계를 한 번에 (GET /api/stats/emd?month=all)
  async loadMonthly() {
    if (ctx.monthly || ctx.monthlyLoading) return;
    ctx.monthlyLoading = true;
    try {
      const r = await api.emdStatsAll();
      ctx.monthly = { period: r.period, source_id: r.source_id, months: r.months };
    } catch (e) { ctx.monthly = { error: e.message }; }
    ctx.monthlyLoading = false;
    set({});
  },
  go(step) { if (step <= maxStep()) { set({ step, openChip: null }); window.scrollTo({ top: 0 }); } },
  async runBatch(kind) {
    const sid = state.session_id;
    const key = kind === "A" ? "batchA" : "batchB";
    const ac = new AbortController(); aborts.push(ac);
    set({ [key]: { id: null, events: [], result: null, error: null, slow: false }, activeDay: null, selPlace: null, open: {}, logOpen: null, ...(kind === "A" ? { batchB: null, game: { day: 1, idx: 0 }, arrived: {}, feedback: {} } : {}) });
    try {
      const id = kind === "A" ? await api.startBatchA(state.goal, state.injectError) : await api.startBatchB(state.batchA.id);
      if (sid !== state.session_id) return;
      set({ [key]: { ...state[key], id } });
      const result = await pollBatch(id, (evs) => {
        if (sid !== state.session_id) return;
        set({ [key]: { ...state[key], events: [...state[key].events, ...evs] } });
      }, ac.signal, () => { if (sid === state.session_id) set({ [key]: { ...state[key], slow: true } }); });
      if (sid !== state.session_id) return;
      set({ [key]: { ...state[key], result, slow: false } });
    } catch (e) {
      if (e.name === "AbortError" || sid !== state.session_id) return;
      set({ [key]: { ...state[key], error: e.message } });
    }
  },
  react(placeId, value) {
    set({ feedback: { ...state.feedback, [placeId]: value } });
    api.postEvent({ batch_id: state.batchA.id, place_id: placeId, type: "feedback", value }).catch((e) => toast(e.message));
  },
  arrive(placeId) {
    if (state.arrived[placeId]) return;
    set({ arrived: { ...state.arrived, [placeId]: true } }, { silent: true });
    api.postEvent({ batch_id: state.batchA.id, place_id: placeId, type: "virtual_arrival", value: null }).catch((e) => toast(e.message));
  },
  toggleOpen(id) { set({ open: { ...state.open, [id]: !state.open[id] } }); },
  restart() {
    aborts.forEach((a) => a.abort()); aborts = [];
    reset();
    window.scrollTo({ top: 0 });
  },
};

// ── 화면 ─────────────────────────────────────────
const STEPS = [[1, "여행 설명"], [2, "경로 만들기"], [3, "미리보기"], [4, "다시 짜기"]];

function Header() {
  const ms = maxStep();
  return h("header", { class: "topbar no-print" }, h("div", { class: "topbar-inner" },
    h("div", { class: "brand" },
      h("span", { class: "brand-mark" }, svgEl("svg", { width: 16, height: 16, viewBox: "0 0 24 24" }, svgEl("path", { d: "M7 19V10a5 5 0 0 1 10 0v9", fill: "none", stroke: "#fff", "stroke-width": 2.6, "stroke-linecap": "round" }))),
      "말따라 제주"),
    h("nav", { class: "steps" }, STEPS.map(([n, label]) => h("button", {
      class: "step" + (state.step === n ? " active" : ""), disabled: n > ms, onclick: () => actions.go(n),
    }, h("span", { class: "n" }, `0${n}`), label))),
    h("div", { class: "top-right" },
      MOCK ? h("span", { class: "badge badge-mock", title: "목업 데이터로 동작 중입니다. 화면의 장소명·수치는 실제가 아닙니다." }, "MOCK DATA") : null,
      ctx.demo ? h("span", { class: "badge badge-warn" }, "시연 모드") : null,
      ctx.health && !ctx.health.llm_available ? h("span", { class: "badge badge-rule", title: "AI 연결이 없어 규칙 기반으로 판단합니다" }, h("span", { class: "dot" }), "규칙 모드") : null,
      h("button", { class: "btn btn-sm", onclick: actions.restart }, icon("reset", 14), "처음부터"))));
}

function Screen() {
  if (ctx.bootError) {
    return h("div", { class: "page" }, h("div", { class: "card errbox", style: { padding: "24px" } },
      h("b", {}, "서버에 연결할 수 없습니다"), h("div", {}, ctx.bootError),
      h("button", { class: "btn btn-sm", onclick: () => location.reload() }, icon("reset", 14), "다시 시도")));
  }
  if (!ctx.map) return h("div", { class: "page" }, h("div", { class: "log-status" }, h("span", { class: "spinner" }), "불러오는 중…"));
  return [Step1, Step2, Step3, Step4][state.step - 1](state, ctx, actions);
}

function render() {
  // 입력 포커스·커서 보존
  const a = document.activeElement;
  const keep = a && a.id ? { id: a.id, start: a.selectionStart, end: a.selectionEnd } : null;
  clear(root);
  root.appendChild(Header());
  root.appendChild(h("main", {}, Screen()));
  if (keep) {
    const el = document.getElementById(keep.id);
    if (el) { el.focus({ preventScroll: true }); try { el.setSelectionRange(keep.start, keep.end); } catch { /* 선택 불가 요소 */ } }
  }
}

subscribe(render);

// 키오스크 자동 초기화: 120초 동안 입력이 없으면 15초 안내 후 처음 화면으로
const IDLE_MS = 120000, GRACE = 15;
let lastInput = Date.now(), idleBox = null;
const touch = () => { lastInput = Date.now(); if (idleBox) { idleBox.remove(); idleBox = null; } };
["pointerdown", "keydown", "wheel", "touchstart"].forEach((t) => window.addEventListener(t, touch, { passive: true, capture: true }));
setInterval(() => {
  const busy = state.step > 1 || state.text || state.goal;
  if (!busy) return;
  const idle = Date.now() - lastInput;
  if (idle < IDLE_MS) return;
  const left = Math.max(0, GRACE - Math.floor((idle - IDLE_MS) / 1000));
  if (left === 0) { touch(); actions.restart(); return; }
  if (!idleBox) {
    idleBox = h("div", { class: "modal-bg" }, h("div", { class: "modal" },
      h("div", { class: "modal-t" }, "계속 이용하시나요?"),
      h("div", { class: "modal-d" }, h("b", { id: "idle-left" }, left), "초 뒤 처음 화면으로 돌아갑니다. 입력한 내용은 지워집니다."),
      h("button", { class: "btn btn-primary btn-lg", onclick: touch }, "계속하기")));
    document.body.appendChild(idleBox);
  } else { const el = document.getElementById("idle-left"); if (el) el.textContent = left; }
}, 1000);
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && state.openChip) set({ openChip: null });
  if (e.ctrlKey && e.shiftKey && (e.key === "D" || e.key === "d")) { e.preventDefault(); ctx.demo = !ctx.demo; toast(ctx.demo ? "시연 모드 켜짐" : "시연 모드 꺼짐"); set({}); }
});

(async function boot() {
  render();
  try {
    const [health, config, map, stats0] = await Promise.all([api.health(), api.config(), api.map(), api.emdStats(null)]);
    Object.assign(ctx, { health, config, map }); ctx.stats[0] = stats0;
  } catch (e) { ctx.bootError = e.message; }
  render();
})();
