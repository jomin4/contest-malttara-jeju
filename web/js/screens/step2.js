import { h, icon } from "../dom.js";
import { set } from "../state.js";
import { distanceLabel, DIST_NOTE, violationText, periodLabel } from "../format.js";
import { SvgMap, dayColor } from "../components/map.js";
import { LogPanel, Stepper } from "../components/log.js";
import { PlaceRow } from "../components/placecard.js";
import { WhyButton, WhySection } from "../components/why.js";
import { ViewSwitch, PickerView, PickTray, pickMarks } from "../components/picker.js";

// 이동수단·동행은 표시만 한다는 것을 분명히 알린다 (원칙 2·6)
export function TransportNote(goal) {
  if (!goal) return null;
  const parts = [];
  if (goal.transport) parts.push(`이동수단 '${goal.transport}'`);
  if (goal.companion) parts.push(`동행 '${goal.companion}'`);
  if (!parts.length) return null;
  return h("div", { class: "transport-note" }, icon("alert", 15),
    `${parts.join(", ")}은(는) 화면에 표시만 하고 경로 계산에는 쓰지 않았어요. 거리는 직선 기준이며 버스 노선·이동시간은 반영하지 않습니다.`);
}

export function DayTabs(st, itin, places) {
  return h("div", { class: "daytabs" },
    h("button", { class: "daytab" + (!st.activeDay ? " on" : ""), onclick: () => set({ activeDay: null }) }, "전체"),
    itin.days.map((d) => h("button", { class: "daytab" + (st.activeDay === d.day ? " on" : ""), onclick: () => set({ activeDay: d.day }) },
      h("span", { class: "sw", style: { background: dayColor(d.day) } }), `${d.day}일차`)));
}

// 날짜별 한 줄 카드 목록. opts.badgeFor(id, day) → 배지, opts.onReact, opts.footFor(day) → 날짜 아래 문구
export function DayList(st, ctx, A, r, opts = {}) {
  const regionName = (rid) => ctx.map.regions.find((x) => x.region_id === rid)?.name || rid;
  const days = st.activeDay ? r.itinerary.days.filter((d) => d.day === st.activeDay) : r.itinerary.days;
  return h("div", { class: "daylist" }, days.map((d) => {
    const route = r.routes.find((x) => x.day === d.day);
    return h("section", { class: "day" },
      h("div", { class: "day-head" },
        h("h3", {}, h("span", { class: "sw", style: { background: dayColor(d.day) } }), `${d.day}일차`, h("span", { class: "muted", style: { fontWeight: 500 } }, regionName(d.region_id))),
        route ? h("span", { class: "dist", title: DIST_NOTE }, distanceLabel(route.total_km), h("small", {}, ` · ${DIST_NOTE}`)) : null),
      d.place_ids.map((id, i) => {
        const p = r.places[id]; if (!p) return null;
        return PlaceRow({ place: p, num: i + 1, day: d.day, explanations: r.explanations?.[id], alternatives: r.alternatives?.[id], places: r.places,
          open: !!st.open[id], onToggle: () => A.toggleOpen(id), badge: opts.badgeFor?.(id, d.day),
          reaction: st.feedback[id], onReact: opts.onReact ? (v) => opts.onReact(id, v) : null, legKm: i > 0 ? route?.legs_km?.[i - 1] : null });
      }),
      opts.footFor?.(d.day) || null);
  }));
}

export function MapCard(st, ctx, r, title) {
  return h("div", { class: "card map-card" },
    h("div", { class: "card-head" }, h("div", { class: "card-title" }, icon("map", 15), title), r ? DayTabs(st, r.itinerary, r.places) : null),
    h("div", { class: "card-body map-fit" },
      SvgMap({ map: ctx.map, itinerary: r?.itinerary, places: r?.places, activeDay: st.activeDay, marks: r ? pickMarks(st) : null,
        highlightRegion: r && st.activeDay ? r.itinerary.days.find((d) => d.day === st.activeDay)?.region_id : null,
        onPlaceClick: (id, day) => { set({ open: { ...st.open, [id]: true }, activeDay: day }); setTimeout(() => document.querySelector(`[data-place="${id}"]`)?.scrollIntoView({ behavior: "smooth", block: "center" }), 30); } }),
      h("div", { class: "legend", style: { marginTop: "8px" } }, h("span", {}, "선은 방문 순서를 잇는 직선입니다 (도로·이동시간 아님)"), h("span", {}, ctx.map.attribution || "경계: 통계청 SGIS 행정동 (가공: vuski/admdongkor)"))));
}

export function Step2(st, ctx, A) {
  const b = st.batchA;
  if (!b && st.goal) queueMicrotask(() => { if (!st.batchA) A.runBatch("A"); });
  const r = b?.result;
  const logOpen = st.logOpen ?? !r;
  return h("div", { class: "page" },
    h("div", { class: "pagehead" },
      h("div", {},
        h("div", { class: "eyebrow" }, "02 경로 만들기"),
        h("h1", {}, r ? "경로가 준비됐어요" : b?.error ? "경로를 만들지 못했어요" : "AI가 경로를 짜고 있어요"),
        h("div", { class: "muted lead" }, [periodLabel(st.goal), st.goal?.pace, ...(st.goal?.interests || [])].filter(Boolean).join(" · ")),
        TransportNote(st.goal)),
      h("div", { class: "actions" },
        ctx.demo ? h("label", { class: "switch", title: "초안에 일부러 잘못된 장소를 넣어 검증·수정 과정을 보여줍니다" },
          h("input", { type: "checkbox", checked: st.injectError, onchange: (e) => set({ injectError: e.target.checked }) }), h("span", { class: "track" }), "오류 주입") : null,
        ctx.demo ? h("button", { class: "btn", disabled: b && !r && !b.error, onclick: () => A.runBatch("A") }, icon("reset", 15), "다시 만들기") : null,
        r ? WhyButton() : null,
        h("button", { class: "btn btn-primary btn-lg", disabled: !r, onclick: () => A.go(3) }, "미리 둘러보기", icon("arrow", 16)))),
    r ? null : Stepper({ kind: "A", batch: b }),
    h("div", { class: "s2" },
      h("div", { class: "s2-left" },
        r?.violations_remaining?.length ? h("div", { class: "viol" },
          h("h4", {}, "고치지 못한 부분이 있어요"), h("ul", {}, r.violations_remaining.map((v) => h("li", {}, violationText(v, r.places))))) : null,
        r ? ViewSwitch(st, ctx) : null,
        r && st.listView === "pick" ? PickerView({ st, ctx, A, r }) : [
          r ? h("p", { class: "summary" }, r.summary) : null,
          r ? DayList(st, ctx, A, r) : null],
        LogPanel({ title: "AI가 한 일", batch: b, onRetry: () => A.runBatch("A"), open: logOpen, onToggle: r ? () => set({ logOpen: !logOpen }) : null,
          sub: r ? `분류 없음 ${r.quality.no_category}곳 · 읍면동 지표 없음 ${r.quality.no_region_indicator}곳 · 반경 지표 없음 ${r.quality.no_nearby_indicator}곳` : null })),
      h("div", { class: "s2-right" }, MapCard(st, ctx, r, "경로 지도"))),
    r ? WhySection({ st, ctx, r, events: b.events, kind: "A" }) : null,
    r ? PickTray({ st, A, r }) : null);
}
