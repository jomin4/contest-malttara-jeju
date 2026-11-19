// 직접 고르기: DB의 전체 장소를 검색·필터해서 일자에 담는다 → 다시 짜기(Batch B)에 picks로 보낸다.
// 목록은 서버(GET /api/places)가 매번 DB를 읽어 주므로 데이터가 갱신되면 그대로 반영된다.
import { h, icon } from "../dom.js";
import { set } from "../state.js";
import { dayColor } from "./map.js";
import { shortName } from "../format.js";

export const MAX_PICKS = 20;
const SORTS = [["score", "추천순"], ["quiet", "덜 붐비는 순"], ["name", "이름순"]];

// 추천 / 직접 고르기 전환
export function ViewSwitch(st, ctx) {
  if (!(ctx.config?.supports || []).includes("places")) return null;
  const n = st.picks.length;
  return h("div", { class: "seg view-switch", role: "tablist" },
    h("button", { class: st.listView !== "pick" ? "on" : "", role: "tab", onclick: () => set({ listView: "rec" }) }, icon("spark", 14), "AI 추천 일정"),
    h("button", { class: st.listView === "pick" ? "on" : "", role: "tab", onclick: () => set({ listView: "pick" }) },
      icon("list", 14), "직접 고르기", n ? h("span", { class: "count-dot" }, n) : null));
}

// 그날 권역과 같은 날을 기본으로 (없으면 지정 안 함 → 서버가 정함)
function defaultDay(r, place) {
  return r.itinerary.days.find((d) => d.region_id === place.region_id)?.day ?? null;
}

function pctLabel(ind, word) {
  if (!ind || ind.missing || ind.pct == null) return h("span", { class: "meter na" }, `${word} 자료 없음`);
  const v = Math.round((1 - ind.pct) * 100);   // 높을수록 덜 붐빔
  return h("span", { class: "meter", title: `${word}: 제주 전체에서 덜 붐비는 쪽 상위 ${100 - v}%` },
    h("i", { style: { width: `${Math.max(6, v)}%` } }), h("b", {}, word), ` ${v}`);
}

function Row({ p, st, r, A, regionName, inItin }) {
  const pick = st.picks.find((x) => x.place_id === p.place_id);
  const full = !pick && st.picks.length >= MAX_PICKS;
  const dayOf = (d) => r.itinerary.days.find((x) => x.day === d);
  const off = pick?.day && dayOf(pick.day)?.region_id !== p.region_id;
  return h("div", { class: "pick-row" + (pick ? " on" : ""), "data-pick": p.place_id,
      onmouseenter: () => { if (st.pickHot !== p.place_id) set({ pickHot: p.place_id }); },
      onmouseleave: (e) => { if (e.currentTarget.isConnected && st.pickHot === p.place_id) set({ pickHot: null }); } },
    h("div", { class: "pick-main" },
      h("div", { class: "pick-name", title: p.name }, shortName(p.name),
        inItin ? h("span", { class: "badge" }, `${inItin}일차 일정에 있음`) : null),
      h("div", { class: "pick-meta" }, [p.category || "분류 없음", regionName(p.region_id), p.emd?.split(" ")[1]].filter(Boolean).join(" · ")),
      h("div", { class: "pick-meters" }, pctLabel(p.indicators?.region, "동네 한산"), pctLabel(p.indicators?.nearby, "주변 한산")),
      pick ? h("div", { class: "pick-days" },
        h("span", { class: "muted" }, "어느 날?"),
        h("button", { class: "chip-day" + (!pick.day ? " on" : ""), onclick: () => A.setPickDay(p.place_id, null) }, "알아서"),
        r.itinerary.days.map((d) => h("button", { class: "chip-day" + (pick.day === d.day ? " on" : ""), onclick: () => A.setPickDay(p.place_id, d.day) },
          h("span", { class: "sw", style: { background: dayColor(d.day) } }), `${d.day}일차`, h("small", {}, regionName(d.region_id))))) : null,
      off ? h("div", { class: "pick-warn" }, icon("alert", 13), `${pick.day}일차는 ${regionName(dayOf(pick.day).region_id)}이라 이동 거리가 길어질 수 있어요`) : null),
    inItin ? null : h("button", { class: "btn btn-sm " + (pick ? "btn-dark" : ""), disabled: full,
        title: full ? `최대 ${MAX_PICKS}곳까지 담을 수 있어요` : null,
        onclick: () => (pick ? A.unpick(p.place_id) : A.pick(p, defaultDay(r, p))) },
      pick ? [icon("check", 14), "담음"] : [icon("plus", 14), "담기"]));
}

export function PickerView({ st, ctx, A, r }) {
  const regionName = (rid) => ctx.map.regions.find((x) => x.region_id === rid)?.name || "권역 없음";
  const q = st.pickQ;
  const res = st.pickRes;
  const inItin = {};
  r.itinerary.days.forEach((d) => d.place_ids.forEach((id) => { inItin[id] = d.day; }));
  if (!res || res.key !== A.pickKey()) queueMicrotask(() => A.loadPicks());
  const chip = (on, label, onclick, extra) => h("button", { class: "fchip" + (on ? " on" : ""), onclick }, extra || null, label);
  const regionDays = (rid) => r.itinerary.days.filter((d) => d.region_id === rid).map((d) => d.day);

  return h("div", { class: "picker" },
    h("div", { class: "picker-intro" },
      h("b", {}, "마음에 드는 곳을 직접 담아 보세요."),
      " 담은 곳은 ‘꼭 갈래요’처럼 고정하고, 같은 날 비슷한 종류(음식은 음식) 중 점수가 낮은 곳과 바꿔 다시 짭니다."),
    h("div", { class: "picker-tools" },
      h("label", { class: "search" }, icon("search", 16),
        h("input", { id: "pick-q", type: "search", placeholder: "장소 이름으로 찾기 (예: 해수욕장, 오름)", value: q.q,
          oninput: (e) => A.setPickQ({ q: e.target.value }, 250) })),
      h("div", { class: "fchips" },
        chip(!q.region, "전체 권역", () => A.setPickQ({ region: null })),
        ctx.map.regions.map((g) => {
          const ds = regionDays(g.region_id);
          return chip(q.region === g.region_id, g.name, () => A.setPickQ({ region: g.region_id }),
            ds.length ? h("span", { class: "fchip-day" }, ds.map((d) => `${d}일차`).join("·")) : null);
        })),
      h("div", { class: "fchips" },
        chip(!q.interest, "모든 종류", () => A.setPickQ({ interest: null })),
        (ctx.config?.interests || []).map((it) => chip(q.interest === it.key, it.key, () => A.setPickQ({ interest: it.key }))),
        h("span", { class: "grow" }),
        h("div", { class: "seg seg-sm" }, SORTS.map(([k, l]) => h("button", { class: q.sort === k ? "on" : "", onclick: () => A.setPickQ({ sort: k }) }, l))))),
    h("div", { class: "picker-count" },
      res?.loading && !res.items?.length ? h("span", { class: "muted" }, h("span", { class: "spinner sm" }), " 불러오는 중…")
        : res?.error ? h("span", { class: "err" }, res.error, " ", h("button", { class: "btn btn-sm", onclick: () => A.loadPicks() }, "다시 시도"))
        : h("span", {}, h("b", {}, `${(res?.total ?? 0).toLocaleString()}곳`), h("span", { class: "muted" }, " · 제주데이터허브 장소 데이터에서 바로 불러와요. ‘한산’ 숫자가 클수록 덜 붐벼요(563·1208).")),
    ),
    h("div", { class: "pick-list" },
      (res?.items || []).map((p) => Row({ p, st, r, A, regionName, inItin: inItin[p.place_id] })),
      res && !res.error && res.items?.length < res.total
        ? h("button", { class: "btn more", disabled: res.loading, onclick: () => A.loadPicks(true) }, res.loading ? "불러오는 중…" : `더 보기 (${res.total - res.items.length}곳 남음)`) : null,
      res && !res.loading && !res.error && !res.total ? h("div", { class: "empty" }, "조건에 맞는 장소가 없어요. 검색어나 권역을 바꿔 보세요.") : null));
}

// 담은 장소 바구니 + 다시 짜기 (화면 아래 고정)
export function PickTray({ st, A, r }) {
  if (!st.picks.length) return null;
  return h("div", { class: "pick-tray" },
    h("div", { class: "tray-l" },
      h("b", {}, `담은 장소 ${st.picks.length}곳`),
      h("div", { class: "tray-chips" }, st.picks.map((x) => h("span", { class: "tray-chip" },
        h("span", { class: "sw", style: { background: x.day ? dayColor(x.day) : "#a3a3a3" } }),
        shortName(x.place.name), h("small", {}, x.day ? `${x.day}일차` : "알아서"),
        h("button", { "aria-label": `${x.place.name} 빼기`, onclick: () => A.unpick(x.place_id) }, "×"))))),
    h("div", { class: "tray-r" },
      h("button", { class: "btn btn-ghost", onclick: () => set({ picks: [] }) }, "모두 비우기"),
      h("button", { class: "btn btn-primary btn-lg", disabled: !r, onclick: () => A.applyPicks() }, "담은 장소 넣어 다시 짜기", icon("arrow", 16))));
}

// 지도에 담은 장소(별) + 목록에서 가리킨 장소
export function pickMarks(st) {
  const marks = st.picks.map((x) => ({ lat: x.place.lat, lon: x.place.lon, color: x.day ? dayColor(x.day) : "#525252", label: shortName(x.place.name), hot: st.pickHot === x.place_id }));
  const hot = st.pickHot && !st.picks.some((x) => x.place_id === st.pickHot) && st.pickRes?.items?.find((p) => p.place_id === st.pickHot);
  if (hot) marks.push({ lat: hot.lat, lon: hot.lon, color: "#a3a3a3", label: shortName(hot.name), hot: true });
  return marks.filter((m) => m.lat != null && m.lon != null);
}
