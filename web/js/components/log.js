import { h, icon } from "../dom.js";
import { ACTOR, STATUS_SYM, TOOL_KO, STAGES_A, STAGES_B, stageOf } from "../format.js";

// 방문객용 진행 단계 (가로 막대)
export function Stepper({ kind, batch }) {
  const stages = kind === "B" ? STAGES_B : STAGES_A;
  const cur = stageOf(kind, batch?.events, !!batch?.result);
  const fixed = batch?.events?.some((e) => e.status === "fix");
  return h("div", { class: "stepper" }, stages.map((name, i) => h("div", { class: `stg ${i < cur ? "done" : i === cur ? (batch?.result ? "done" : "cur") : ""}` },
    h("span", { class: "dot" }, i < cur || batch?.result ? icon("check", 12) : i === cur ? h("span", { class: "spinner sm" }) : i + 1),
    h("span", {}, name, name === "검증·수정" && fixed ? h("span", { class: "fixmark" }, " · 1회 고침") : null))));
}

// batch: {id, events, result, error, slow}
export function LogPanel({ title, batch, onRetry, sub, open, onToggle }) {
  const running = batch && !batch.result && !batch.error;
  const n = batch?.events?.length || 0;
  const head = h("button", { class: "card-head disclose-head", onclick: onToggle, "aria-expanded": open ? "true" : "false" },
    h("div", { class: "card-title" }, running ? h("span", { class: "pulse" }) : icon("check", 15), title,
      h("span", { class: "muted", style: { fontWeight: 400 } }, `${n}단계`)),
    h("span", { class: "muted", style: { display: "flex", alignItems: "center", gap: "10px", fontSize: "13px" } },
      h("span", { class: "mono" }, batch?.id || ""), onToggle ? h("span", { class: "chev" + (open ? " up" : "") }, "▾") : null));
  const body = open ? [
    sub ? h("div", { class: "log-sub" }, sub) : null,
    h("div", { class: "log", id: "log-scroll" },
      (batch?.events || []).map((e) => h("div", { class: `log-line ${e.status}` },
        h("span", { class: `st ${e.status}` }, STATUS_SYM[e.status] || "·"),
        h("div", {},
          h("div", { class: "log-t" }, h("b", {}, TOOL_KO[e.tool] || e.tool), h("span", { class: `who ${e.actor}` }, ACTOR[e.actor] || e.actor), h("span", { class: "tool" }, e.tool)),
          h("div", { class: "msg" }, e.message)))),
      !n && running ? h("div", { class: "log-line" }, h("span", { class: "st" }, h("span", { class: "spinner sm" })), h("div", { class: "msg" }, "에이전트를 시작하는 중…")) : null),
  ] : null;
  const foot = [];
  if (running && batch.slow) foot.push(h("div", { class: "log-sub" }, "시간이 걸리고 있습니다… 화면을 그대로 두세요."));
  if (batch?.error) foot.push(h("div", { class: "errbox" }, h("div", {}, icon("alert", 15), " ", batch.error),
    onRetry ? h("button", { class: "btn btn-sm", onclick: onRetry }, icon("reset", 14), "다시 시도") : null));
  if (open) queueMicrotask(() => { const el = document.getElementById("log-scroll"); if (el) el.scrollTop = el.scrollHeight; });
  return h("div", { class: "card" }, head, body, foot);
}
