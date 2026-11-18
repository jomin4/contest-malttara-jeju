// 계약(docs/superpowers/plans/2026-11-16-api-contract.md) 2장 래퍼.
// 주소에 ?mock=1 이 있으면 목업(js/mock.js)을 쓴다. 기본은 실서버.
import * as mock from "./mock.js";

export const MOCK = new URLSearchParams(location.search).get("mock") === "1";

async function req(method, path, body) {
  let res;
  try {
    res = await fetch(path, {
      method,
      headers: body ? { "Content-Type": "application/json" } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new Error("서버에 연결할 수 없습니다. 실행 창(run.bat)이 켜져 있는지 확인해 주세요.");
  }
  let data = null;
  try { data = await res.json(); } catch { /* 비어 있음 */ }
  if (!res.ok) throw new Error((data && data.error) || `요청 실패 (${res.status})`);
  return data;
}

const real = {
  health: () => req("GET", "/api/health"),
  config: () => req("GET", "/api/config"),
  parseGoal: (text) => req("POST", "/api/goal/parse", { text }),
  map: () => req("GET", "/api/map"),
  emdStats: (month) => req("GET", "/api/stats/emd" + (month ? `?month=${month}` : "")),
  emdStatsAll: () => req("GET", "/api/stats/emd?month=all"),
  startBatchA: (goal, inject_error) => req("POST", "/api/batch/a", { goal, inject_error }).then((r) => r.batch_id),
  startBatchB: (prev_batch_id, picks) => req("POST", "/api/batch/b", { prev_batch_id, ...(picks?.length ? { picks } : {}) }).then((r) => r.batch_id),
  places: (params) => req("GET", "/api/places?" + new URLSearchParams(Object.entries(params).filter(([, v]) => v !== null && v !== undefined && v !== ""))),
  events: (id, after) => req("GET", `/api/batch/${encodeURIComponent(id)}/events?after=${after}`),
  postEvent: (e) => req("POST", "/api/events", e),
  trend: (id) => req("GET", `/api/places/${encodeURIComponent(id)}/trend`),
  printUrl: (id) => `/api/print/${encodeURIComponent(id)}`,
};

export const api = MOCK ? mock.api : real;

// 500ms 폴링. 20초가 지나면 onSlow() 한 번. signal로 중단.
export async function pollBatch(id, onEvents, signal, onSlow) {
  let after = 0;
  const t0 = Date.now();
  let slowSent = false;
  while (true) {
    if (signal?.aborted) throw new DOMException("중단", "AbortError");
    const r = await api.events(id, after);
    if (signal?.aborted) throw new DOMException("중단", "AbortError");
    if (r.events?.length) {
      after = r.events[r.events.length - 1].seq;
      onEvents(r.events);
    }
    if (r.error) throw new Error(r.error);
    if (r.done) return r.result;
    if (!slowSent && Date.now() - t0 > 20000) { slowSent = true; onSlow?.(); }
    await new Promise((ok) => setTimeout(ok, 500));
  }
}
