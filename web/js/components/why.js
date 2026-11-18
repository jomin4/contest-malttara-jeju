// "왜 이렇게 짰나요?" — 조건 → 고르는 기준 → AI가 한 판단 → 날짜별 이유 → (다시 짜기) 바꾼 이유 → 사용한 데이터
// 문장과 수치는 모두 서버 응답(goal, events, explanations, diff, indicators)에서 가져온다. 프론트는 고르고 배치만 한다.
import { h, icon } from "../dom.js";
import { periodLabel, TOOL_KO, ACTOR, CHANGE, REACT, distanceLabel, DIST_NOTE } from "../format.js";
import { dayColor } from "./map.js";

const WHY_TOOLS = new Set(["plan_tasks", "get_region_data", "analyze_tourism", "check_data_quality", "create_itinerary",
  "inject_error", "validate_itinerary", "revise_itinerary", "analyze_feedback", "decide_keep_replace", "compare_itineraries"]);

function Step({ n, title, children }) {
  return h("div", { class: "why-step" },
    h("div", { class: "why-n" }, n),
    h("div", { class: "why-c" }, h("h3", {}, title), children));
}

export function WhyButton() {
  return h("button", { class: "btn btn-why", onclick: () => document.getElementById("why")?.scrollIntoView({ behavior: "smooth", block: "start" }) },
    icon("spark", 16), "왜 이렇게 짰나요?");
}

export function WhySection({ st, ctx, r, events, kind, feedback }) {
  const g = r.goal || st.goal || {};
  const regionName = (rid) => ctx.map.regions.find((x) => x.region_id === rid)?.name || rid;
  const unset = [["이동수단", g.transport], ["동행", g.companion], ["출발지·숙소", g.origin || g.stay?.label], ["날짜", g.month && `${g.month}월`]]
    .filter(([, v]) => !v).map(([k]) => k);
  const used = [periodLabel(g), g.pace && `여유 ${g.pace}`, g.interests?.length && `관심 ${g.interests.join("·")}`, g.quiet_pref && "한적한 곳 선호",
    g.transport && `이동수단 ${g.transport}(표시만)`, g.companion && `동행 ${g.companion}(표시만)`].filter(Boolean);
  const decisions = (events || []).filter((e) => WHY_TOOLS.has(e.tool) && e.status !== "ok" || ["create_itinerary", "decide_keep_replace", "compare_itineraries"].includes(e.tool));
  const srcPeriod = (sid) => Object.values(r.places).map((p) => (sid === "563" ? p.indicators.region : p.indicators.nearby)).find((x) => !x.missing)?.period;

  let n = 0;
  return h("section", { class: "why", id: "why" },
    h("div", { class: "why-head" }, h("h2", { class: "sec-title" }, kind === "B" ? "왜 이렇게 바꿨나요?" : "왜 이렇게 짰나요?"),
      h("p", { class: "muted" }, "AI가 실제로 한 판단과, 판단에 쓴 데이터를 순서대로 보여드려요. 숫자는 모두 데이터에서 계산한 값이에요.")),
    Step({ n: ++n, title: "말씀하신 조건을 이렇게 이해했어요", children: [
      h("div", { class: "why-chips" }, used.map((t) => h("span", { class: "badge badge-accent" }, t))),
      unset.length ? h("p", { class: "why-p muted" }, `입력하지 않은 ${unset.join(" · ")}은(는) 임의로 채우지 않았어요.`) : null] }),
    Step({ n: ++n, title: "이런 기준으로 장소를 골랐어요", children: [
      h("ul", { class: "why-list" },
        h("li", {}, h("b", {}, "관심사가 맞는 곳"), "을 가장 먼저 봤어요. 장소 분류(해수욕장, 오름, 카페 등)가 관심사와 같은지로 판단해요."),
        h("li", {}, "그다음 ", h("b", {}, "사람이 덜 몰리는 동네"), "를 앞에 뒀어요 — 동네마다 '사는 사람 대비 찾아오는 사람' 비율 (제주데이터허브 563, ", srcPeriod("563") || "", ")."),
        h("li", {}, "그리고 ", h("b", {}, "주변에 렌터카가 덜 머무는 곳"), "을 더 쳐줬어요 — 장소 반경 1km 렌터카 체류 기록 (허브 1208, ", srcPeriod("1208") || "", ")."),
        g.quiet_pref ? h("li", {}, "‘조용한 곳’ 요청이 있어서 덜 붐비는 정도를 평소보다 더 크게 반영했어요.") : null,
        h("li", {}, "하루는 한 권역 안에서만 다니고, 가까운 곳끼리 순서대로 이었어요. ", h("span", { class: "muted" }, `(${DIST_NOTE})`)))] }),
    decisions.length ? Step({ n: ++n, title: kind === "B" ? "반응을 보고 AI가 이렇게 판단했어요" : "AI가 이렇게 판단하고, 스스로 고쳤어요", children:
      h("ol", { class: "why-timeline" }, decisions.map((e) => h("li", { class: e.status },
        h("span", { class: "why-tl-t" }, TOOL_KO[e.tool] || e.tool, h("span", { class: `who ${e.actor}` }, ACTOR[e.actor] || e.actor)),
        h("span", {}, e.message)))) }) : null,
    kind === "B" && r.diff?.some((x) => x.change !== "keep") ? Step({ n: ++n, title: "이렇게 바꿨어요", children:
      h("ul", { class: "why-list" }, r.diff.filter((x) => x.change !== "keep").map((x) => h("li", {},
        h("span", { class: `chg ${x.change}` }, CHANGE[x.change]), " ",
        x.change === "replace" ? [h("s", {}, r.places[x.place_id]?.name), " → ", h("b", {}, r.places[x.replaced_by]?.name)] : h("b", {}, r.places[x.place_id]?.name),
        h("span", { class: "muted" }, ` — ${x.reason}`)))) }) : null,
    Step({ n: ++n, title: "날짜별로 이 장소들을 고른 이유", children:
      r.itinerary.days.map((d) => {
        const route = r.routes.find((x) => x.day === d.day);
        return h("div", { class: "why-day" },
          h("div", { class: "why-day-h" }, h("span", { class: "sw", style: { background: dayColor(d.day) } }), `${d.day}일차 · ${regionName(d.region_id)}`,
            route ? h("span", { class: "muted" }, ` · ${distanceLabel(route.total_km)}`) : null),
          d.place_ids.map((id, i) => {
            const p = r.places[id]; if (!p) return null;
            const why = (r.explanations?.[id] || []).slice(0, 3);
            return h("div", { class: "why-place" },
              h("b", {}, `${i + 1}. ${p.name}`), feedback?.[id] ? h("span", { class: "badge" }, `내 반응: ${REACT[feedback[id]]}`) : null,
              h("ul", {}, why.map((t) => h("li", {}, t))));
          }));
      }) }),
    Step({ n: ++n, title: "사용한 데이터", children:
      h("ul", { class: "why-list" },
        h("li", {}, "장소 목록: 제주데이터허브 1349 (VISIT JEJU 여행장소) + 한국관광공사 TourAPI(분류·음식점)"),
        h("li", {}, `동네 붐빔: 제주데이터허브 563 내국인 유동인구 (${srcPeriod("563") || "—"}) — 동네 단위 통계라 개별 장소의 혼잡도는 아니에요`),
        h("li", {}, `장소 주변 한적함: 제주데이터허브 1208 렌터카 체류 거점 (${srcPeriod("1208") || "—"})`),
        h("li", {}, "지도 경계: 통계청 SGIS 행정동 경계(가공: vuski/admdongkor)"),
        h("li", { class: "muted" }, `분류가 없는 장소 ${r.quality?.no_category ?? 0}곳 · 동네 지표 없음 ${r.quality?.no_region_indicator ?? 0}곳 · 주변 지표 없음 ${r.quality?.no_nearby_indicator ?? 0}곳은 중립값으로 계산했어요.`)) }));
}
