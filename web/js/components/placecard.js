import { h, icon } from "../dom.js";
import { pct100, REACT, REACT_HINT } from "../format.js";
import { dayColor } from "./map.js";

function Indicator(kind, d) {
  const title = kind === "region" ? `${d.emd ?? "읍면동 미상"} 지표 (읍면동 단위)` : `장소 반경 ${d.radius_km}km 지표`;
  if (d.missing) {
    return h("div", { class: "ind missing" }, h("div", { class: "ind-t" }, title), h("div", { class: "ind-v" }, "지표 없음"),
      h("div", { class: "ind-s" }, `${d.source_id} · ${d.period}`));
  }
  const v = kind === "region"
    ? h("div", { class: "ind-v" }, "방문/거주 비율 ", h("b", {}, Number(d.visit_ratio).toFixed(2)))
    : h("div", { class: "ind-v" }, "렌터카 체류 ", h("b", {}, d.quiet_count), "건");
  return h("div", { class: "ind" }, h("div", { class: "ind-t" }, title), v,
    h("div", { class: "ind-bar", title: `범위 내 백분위 ${pct100(d.pct)}` }, h("i", { style: { width: `${pct100(d.pct)}%` } })),
    h("div", { class: "ind-s" }, `범위 내 백분위 ${pct100(d.pct)} · ${d.source_id} · ${d.period}`));
}

const SRC = { tourapi: "TourAPI", hub_811: "허브 811", hub_812: "허브 812", hub_784: "허브 784", hub_858: "허브 858", keyword: "이름 규칙", none: "" };

// 방문객용 한 줄 카드. 근거(지표·설명·대안)는 '근거 보기'로 펼친다.
export function PlaceRow({ place, num, day, explanations, alternatives, places, open, onToggle, badge, reaction, onReact, legKm }) {
  const p = place;
  return h("div", { class: "prow" + (open ? " open" : ""), "data-place": p.place_id },
    h("div", { class: "prow-main" },
      h("div", { class: "pnum", style: { background: dayColor(day) } }, num),
      h("div", { class: "prow-txt" },
        h("div", { class: "prow-name" }, p.name, badge || null),
        h("div", { class: "prow-meta" }, p.category ?? "분류 없음", legKm != null ? h("span", { class: "leg" }, ` · 앞 장소에서 직선 ${legKm}km`) : null)),
      onReact ? h("div", { class: "react mini" },
        ["interest", "must", "dislike"].map((v) => h("button", { class: `${v} ${reaction === v ? "on" : ""}`, title: `${REACT[v]} — ${REACT_HINT[v]}`,
          onclick: (ev) => { ev.stopPropagation(); onReact(v); } }, v === "interest" ? icon("star", 15) : v === "must" ? icon("pin", 15) : icon("x", 15), REACT[v]))) : null,
      h("button", { class: "btn btn-sm btn-ghost why-btn", onclick: onToggle, "aria-expanded": open ? "true" : "false" }, open ? "접기" : "근거 보기", h("span", { class: "chev" + (open ? " up" : "") }, "▾"))),
    open ? h("div", { class: "prow-more" },
      p.overview ? h("p", { class: "pov" }, p.overview) : null,
      h("div", { class: "ind-grid" }, Indicator("region", p.indicators.region), Indicator("nearby", p.indicators.nearby)),
      explanations?.length ? h("ul", { class: "why" }, explanations.map((t) => h("li", {}, t))) : null,
      alternatives?.length ? h("div", { class: "alts" }, "같은 권역 대안 ", alternatives.map((id, i) => [i ? " · " : "", h("b", {}, places?.[id]?.name ?? id)])) : null,
      h("div", { class: "src-line" }, `분류 출처 ${SRC[p.category_source] || "없음"} · 장소 출처 ${p.source === "1349" ? "제주데이터허브 1349" : "TourAPI"}`)) : null);
}
