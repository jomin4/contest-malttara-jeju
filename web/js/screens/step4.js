import { h, icon } from "../dom.js";
import { set } from "../state.js";
import { api } from "../api.js";
import { CHANGE, violationText } from "../format.js";
import { LogPanel, Stepper } from "../components/log.js";
import { LineChart } from "../components/chart.js";
import { DayList, MapCard, TransportNote } from "./step2.js";
import { WhyButton, WhySection } from "../components/why.js";
import { QrModal, planText } from "../components/qr.js";
import { ViewSwitch, PickerView, PickTray } from "../components/picker.js";

const LINE_COLORS = ["#0f766e", "#ea580c", "#2563eb", "#9333ea", "#ca8a04", "#db2777"];
let loadingTrends = false;

function Charts(st, ctx, A, B) {
  const P = B.places;
  const ids = B.itinerary.days.flatMap((d) => d.place_ids);
  const emds = [...new Set(ids.map((id) => P[id]?.emd).filter(Boolean))].slice(0, 6);
  if (!ctx.monthly) queueMicrotask(() => A.loadMonthly());
  const months = Array.from({ length: 12 }, (_, i) => i + 1);
  const M = ctx.monthly;
  const c1 = !M ? h("div", { class: "log-status" }, h("span", { class: "spinner" }), "월별 통계 불러오는 중…")
    : M.error ? h("div", { class: "side-empty" }, M.error)
    : LineChart({
        labels: months.map((m) => `${m}월`),
        series: emds.map((e, i) => ({ name: e, color: LINE_COLORS[i % LINE_COLORS.length],
          values: months.map((m) => (M.months[m] || M.months[String(m)] || []).find((x) => x.emd === e)?.visit_ratio ?? null) })),
      });

  const trendIds = ids.filter((id) => P[id]?.has_trend);
  const need = trendIds.filter((id) => !ctx.trends[id]);
  if (need.length && !loadingTrends) {
    loadingTrends = true;
    Promise.all(need.map((id) => api.trend(id).then((t) => { ctx.trends[id] = t; }))).finally(() => { loadingTrends = false; set({}); });
  }
  let c2;
  if (!trendIds.length) c2 = h("div", { class: "side-empty" }, "해당 장소의 입장객 통계 없음");
  else if (need.length) c2 = h("div", { class: "log-status" }, h("span", { class: "spinner" }), "입장객 추이 불러오는 중…");
  else {
    const ts = trendIds.map((id) => ctx.trends[id]).filter((t) => t.series.length);
    const labels = ts[0]?.series.map((x) => x.year_month.slice(2).replace("-", ".")) || [];
    const series = [];
    ts.forEach((t, i) => {
      series.push({ name: `${P[t.place_id].name} 내국인`, color: LINE_COLORS[(i * 2) % LINE_COLORS.length], values: t.series.map((x) => x.domestic) });
      series.push({ name: `${P[t.place_id].name} 외국인`, color: LINE_COLORS[(i * 2 + 1) % LINE_COLORS.length], values: t.series.map((x) => x.foreign) });
    });
    c2 = ts.length ? LineChart({ labels, series }) : h("div", { class: "side-empty" }, "해당 장소의 입장객 통계 없음");
  }
  const period2 = trendIds.map((id) => ctx.trends[id]?.period).find(Boolean) || "—";
  return h("section", { class: "evidence" },
    h("h2", { class: "sec-title" }, "자세한 데이터 (참고)"),
    h("p", { class: "muted", style: { margin: "-6px 0 14px" } }, "왼쪽: 일정이 있는 동네가 달마다 얼마나 붐비는지 — 높을수록 사는 사람 대비 찾아오는 사람이 많아요. 오른쪽: 일정 속 관광지의 실제 입장객 수 변화."),
    h("div", { class: "charts" },
      h("div", { class: "card" }, h("div", { class: "card-head" }, h("div", { class: "card-title" }, "일정 지역의 월별 방문/거주 비율 (읍면동 단위)")),
        h("div", { class: "card-body" }, c1, h("div", { class: "source" }, `출처 제주데이터허브 563 · ${ctx.monthly?.period ?? ctx.stats[0]?.period ?? ""} · 읍면동 통계이며 장소 혼잡도가 아닙니다`))),
      h("div", { class: "card" }, h("div", { class: "card-head" }, h("div", { class: "card-title" }, "관광지 입장객 추이")),
        h("div", { class: "card-body" }, c2, h("div", { class: "source" }, `출처 제주데이터허브 189·190 · ${period2}`)))));
}

export function Step4(st, ctx, A) {
  const a = st.batchA?.result;
  if (!a) return h("div", { class: "page" }, "경로가 아직 없습니다.");
  const b = st.batchB;
  if (!b) queueMicrotask(() => { if (!st.batchB) A.runBatch("B"); });
  const r = b?.result;
  const logOpen = st.logOpen ?? !r;
  const print = () => { const u = api.printUrl(r.batch_id); if (u) window.open(u, "_blank"); else window.print(); };
  const diff = r?.diff || [];
  const byNew = Object.fromEntries(diff.filter((x) => x.change !== "keep" && x.change !== "remove").map((x) => [x.replaced_by || x.place_id, x]));
  const badgeFor = (id) => {
    const x = byNew[id]; if (!x) return null;
    return h("span", { class: `chg ${x.change}`, title: x.reason }, CHANGE[x.change]);
  };
  const footFor = (day) => {
    const lines = diff.filter((x) => x.day === day && (x.change === "replace" || x.change === "remove" || x.change === "pin" || x.change === "add"));
    if (!lines.length) return null;
    return h("ul", { class: "changes" }, lines.map((x) => h("li", {},
      h("span", { class: `chg ${x.change}` }, CHANGE[x.change]),
      x.change === "replace" ? [h("s", {}, r.places[x.place_id]?.name), " → ", h("b", {}, r.places[x.replaced_by]?.name)] : h("b", {}, r.places[x.place_id]?.name),
      h("span", { class: "muted" }, ` · ${x.reason}`))));
  };
  const changed = diff.filter((x) => x.change !== "keep").length;
  return h("div", { class: "page" },
    h("div", { class: "pagehead" },
      h("div", {}, h("div", { class: "eyebrow" }, "04 최종 계획"),
        h("h1", {}, r ? "나만의 제주 여행 계획" : "반응을 반영해 다시 짜는 중"),
        h("div", { class: "muted lead" }, r ? (changed ? `반응을 반영해 ${changed}곳을 바꿨어요. 최종 선택은 여러분이 합니다.` : "반응이 없어 처음 경로를 그대로 두었어요. 최종 선택은 여러분이 합니다.") : "꼭 갈래요는 고정하고, 별로예요는 같은 권역 대안으로 바꿉니다."),
        TransportNote(st.goal)),
      h("div", { class: "actions no-print" },
        h("button", { class: "btn", onclick: () => A.go(3) }, "다시 둘러보기"),
        r ? WhyButton() : null,
        h("button", { class: "btn", disabled: !r, onclick: print }, icon("print", 15), "인쇄"),
        h("button", { class: "btn btn-primary btn-lg", disabled: !r, onclick: () => set({ qrOpen: true }) }, icon("spark", 16), "휴대폰으로 가져가기"))),
    r ? null : Stepper({ kind: "B", batch: b }),
    h("div", { class: "s2" },
      h("div", { class: "s2-left" },
        r?.violations_remaining?.length ? h("div", { class: "viol" },
          h("h4", {}, "그대로 둔 부분이 있어요"),
          h("ul", {}, r.violations_remaining.map((v) => h("li", {}, violationText(v, r.places),
            v.type === "regions" && st.picks.some((x) => x.day === v.day) ? " — 직접 고른 장소라 바꾸지 않았어요" : "")))) : null,
        r ? ViewSwitch(st, ctx) : null,
        r && st.listView === "pick" ? PickerView({ st, ctx, A, r }) : (r ? DayList(st, ctx, A, r, { badgeFor, footFor }) : null),
        LogPanel({ title: "AI가 한 일", batch: b, onRetry: () => A.runBatch("B"), open: logOpen, onToggle: r ? () => set({ logOpen: !logOpen }) : null,
          sub: b?.id ? `${b.id} ← 이전 ${a.batch_id}` : null })),
      h("div", { class: "s2-right" }, MapCard(st, ctx, r, "최종 경로"))),
    r ? WhySection({ st, ctx, r, events: b.events, kind: "B", feedback: st.feedback }) : null,
    r ? Charts(st, ctx, A, r) : null,
    r ? PickTray({ st, A, r }) : null,
    r && st.qrOpen ? QrModal({ text: planText(st.goal, r, (rid) => ctx.map.regions.find((x) => x.region_id === rid)?.name || rid),
      onClose: () => set({ qrOpen: false }), onPrint: () => { set({ qrOpen: false }); print(); } }) : null);
}
