// 전역 상태 하나 + 구독. 배치 응답은 session_id가 다르면 버린다.
const listeners = new Set();

function initial(session_id = 0) {
  return {
    session_id,
    step: 1,
    text: "",
    goal: null,
    missing: [],
    parseActor: null,
    parsing: false,
    openChip: null,
    batchA: null,     // {id, events, result, error, slow}
    batchB: null,
    injectError: false,
    feedback: {},     // place_id -> interest|must|dislike
    arrived: {},      // place_id -> true (가상 도착)
    previewMode: "game",
    map3d: true,
    showCrowd: false, // 01 지도에 붐비는 정도 겹쳐 보기
    qrOpen: false,      // 03 게임 지도: 3D 지형(가능할 때) / 2D
    activeDay: 1,
    selPlace: null,
    game: { day: 1, idx: 0, awaiting: null },
    open: {},        // 근거를 펼친 place_id
    logOpen: null,   // null = 실행 중에만 펼침
    listView: "rec", // 02·04 왼쪽: rec = AI 추천 일정, pick = 직접 고르기
    picks: [],       // [{place_id, day|null, place}] 직접 고른 장소 → Batch B picks
    pickQ: { q: "", region: null, interest: null, sort: "score" },
    pickRes: null,   // {key, items, total, loading, error}
    pickHot: null,   // 목록에서 가리킨 place_id (지도 강조)
  };
}

export const state = initial();

export function set(patch, { silent = false } = {}) {
  Object.assign(state, typeof patch === "function" ? patch(state) : patch);
  if (!silent) listeners.forEach((fn) => fn(state));
}

export function reset() {
  const sid = state.session_id + 1;
  Object.keys(state).forEach((k) => delete state[k]);
  Object.assign(state, initial(sid));
  listeners.forEach((fn) => fn(state));
}

export const subscribe = (fn) => listeners.add(fn);

export function maxStep() {
  if (state.batchB) return 4;
  if (state.batchA?.result) return 4;
  if (state.goal && !state.missing.includes("days")) return 2;
  return 1;
}
