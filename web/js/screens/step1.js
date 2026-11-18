import { h, icon } from "../dom.js";
import { set } from "../state.js";
import { periodLabel } from "../format.js";
import { SvgMap, MapLegend, emdCenter } from "../components/map.js";

const EXAMPLES = [
  ["바다 · 맛집 · 2박 3일", "2박 3일 동안 바다를 보며 여유롭게 쉬고, 현지 음식도 먹고 싶어요"],
  ["아이와 오름 · 체험 · 1박 2일", "아이와 함께 1박 2일, 렌터카로 오름이랑 체험 위주로 다니고 싶어요"],
  ["혼자 조용히 · 카페 · 3박 4일", "혼자 3박 4일, 버스로 조용한 동네와 카페를 천천히 보고 싶어요"],
];

function Chip({ id, k, v, unset, warn, open, pop, title }, st) {
  return h("div", { style: { position: "relative" } },
    h("button", { class: `chip ${unset ? "unset" : ""} ${warn ? "warn" : ""} ${open ? "open" : ""}`, title,
      onclick: (e) => { e.stopPropagation(); set({ openChip: open ? null : id }); } },
      h("span", { class: "k" }, k), h("span", { class: "v" }, v), h("span", { class: "caret" }, "▾")),
    open ? h("div", { class: "pop", onclick: (e) => e.stopPropagation() }, pop) : null);
}

function Opts(values, cur, onPick, { none = true, multi = false, fmt = (x) => x } = {}) {
  const isOn = (v) => (multi ? (cur || []).includes(v) : cur === v);
  return h("div", { class: "opts" },
    values.map((v) => h("button", { class: "opt" + (isOn(v) ? " on" : ""), onclick: () => onPick(v) }, fmt(v))),
    none ? h("button", { class: "opt none" + ((multi ? !(cur || []).length : cur == null) ? " on" : ""), onclick: () => onPick(null) }, "미반영") : null);
}

function TextPop(id, cur, onSave) {
  const inputId = `pop-${id}`;
  return [
    h("input", { type: "text", id: inputId, value: cur ?? "", placeholder: "입력", onkeydown: (e) => { if (e.key === "Enter" && !e.isComposing) onSave(e.target.value.trim() || null); } }),
    h("div", { class: "pop-foot" },
      h("button", { class: "btn btn-sm btn-ghost", onclick: () => onSave(null) }, "지우기"),
      h("button", { class: "btn btn-sm btn-primary", onclick: () => onSave(document.getElementById(inputId).value.trim() || null) }, "적용")),
  ];
}

function Conditions(st, ctx, A) {
  const g = st.goal;
  const ev = g.evidence || {};
  const close = (patch) => { A.editGoal(patch); set({ openChip: null }); };
  const maxDays = ctx.config?.max_days ?? 7;
  const interestKeys = (ctx.config?.interests || []).map((x) => x.key);
  const daysMissing = st.missing.includes("days");
  const t = (k) => (ev[k] ? `원문: “${ev[k]}”` : undefined);
  const chips = [
    { id: "days", k: "기간", v: periodLabel(g) ?? "(미반영)", unset: g.days == null, warn: daysMissing, title: t("days"),
      pop: [h("div", { class: "pop-title" }, "여행 기간 (필수)"), Opts(Array.from({ length: maxDays }, (_, i) => i + 1), g.days, (d) => close({ days: d }), { none: false, fmt: (d) => (d === 1 ? "당일" : `${d - 1}박 ${d}일`) })] },
    { id: "pace", k: "여유", v: g.pace ?? "(미반영·보통 기준 적용)", unset: g.pace == null, title: t("pace"),
      pop: [h("div", { class: "pop-title" }, "하루 일정의 여유"), Opts(["여유롭게", "보통", "빡빡하게"], g.pace, (v) => close({ pace: v }))] },
    { id: "interests", k: "관심", v: g.interests?.length ? g.interests.join(" · ") : "(미반영)", unset: !g.interests?.length, title: t("interests"),
      pop: [h("div", { class: "pop-title" }, "관심사 (여러 개)"),
        Opts(interestKeys, g.interests, (v) => {
          if (v == null) return A.editGoal({ interests: [] });
          const cur = new Set(g.interests || []); cur.has(v) ? cur.delete(v) : cur.add(v);
          A.editGoal({ interests: interestKeys.filter((k) => cur.has(k)) });
        }, { multi: true }),
        h("div", { class: "pop-foot" }, h("button", { class: "btn btn-sm btn-primary", onclick: () => set({ openChip: null }) }, "완료"))] },
    g.quiet_pref ? { id: "quiet", k: "한적함", v: "덜 붐비는 곳 우선", title: t("quiet_pref"),
      pop: [h("div", { class: "pop-title" }, "한적함 요청"), h("div", { class: "opts" },
        h("button", { class: "opt on" }, "반영"), h("button", { class: "opt none", onclick: () => close({ quiet_pref: false }) }, "끄기"))] } : null,
    { id: "transport", k: "이동수단", v: g.transport ? `${g.transport} (표시만)` : "(미반영)", unset: g.transport == null, title: t("transport"),
      pop: [h("div", { class: "pop-title" }, "이동수단 — 화면에 표시만 하고, 경로·거리 계산에는 쓰지 않아요 (직선거리 기준)"), Opts(["렌터카", "버스", "도보"], g.transport, (v) => close({ transport: v }))] },
    { id: "companion", k: "동행", v: g.companion ? `${g.companion} (점수 미반영)` : "(미반영)", unset: g.companion == null, title: t("companion"),
      pop: [h("div", { class: "pop-title" }, "동행 (표시만, 점수 미반영)"), TextPop("companion", g.companion, (v) => close({ companion: v }))] },
    { id: "origin", k: "출발지", v: g.origin ?? "(미반영)", unset: g.origin == null, title: t("origin"),
      pop: [h("div", { class: "pop-title" }, "출발지 (숙소 등)"), TextPop("origin", g.origin, (v) => close({ origin: v }))] },
    { id: "month", k: "날짜", v: g.month ? `${g.month}월` : "(미반영)", unset: g.month == null, title: t("month"),
      pop: [h("div", { class: "pop-title" }, "여행 월"), Opts(Array.from({ length: 12 }, (_, i) => i + 1), g.month, (v) => close({ month: v }), { fmt: (m) => `${m}월` })] },
  ].filter(Boolean);

  const shown = chips.filter((c) => !c.unset || c.warn), hidden = chips.filter((c) => c.unset && !c.warn);
  return h("section", { class: "conds" },
    h("div", { class: "conds-head" },
      h("div", { class: "eyebrow" }, "이렇게 이해했어요 · 눌러서 고칠 수 있어요"),
      h("span", { class: `badge ${st.parseActor === "llm" ? "badge-ai" : "badge-rule"}` }, h("span", { class: "dot" }), `해석: ${st.parseActor === "llm" ? "AI" : "규칙"}`)),
    h("div", { class: "chips" }, shown.map((c) => Chip({ ...c, open: st.openChip === c.id }, st))),
    hidden.length ? h("div", { class: "unset-row" }, h("span", { class: "muted" }, "입력하지 않아 반영하지 않는 조건"),
      h("div", { class: "chips" }, hidden.map((c) => Chip({ ...c, v: "미반영", open: st.openChip === c.id }, st)))) : null,
    daysMissing ? h("div", { class: "notice notice-warn" }, icon("alert", 16), "여행 기간(예: 2박 3일)을 입력하거나 기간 칩을 눌러 골라 주세요") : null);
}

const AREAS = [
  ["all", "섬 전체", "권역을 골고루"],
  ["near", "숙소 근처 위주", "숙소 권역과 가까운 곳"],
  ["coast", "해안 따라", "바닷가 마을·해변 위주"],
  ["inland", "중산간(안쪽)", "오름·숲·마을 안쪽 위주"],
];

// 오른쪽: 숙소(한 곳)와 다닐 범위를 지도에서 고른다. '붐비는 정도'는 켜야 보이는 보조 층.
function PlanPanel(st, ctx, A, values, stats) {
  const g = st.goal || {};
  const stay = g.stay || null;
  const area = g.area || null;
  const supported = (ctx.config?.supports || []);
  const applied = supported.includes("stay") && supported.includes("area");
  const P = ctx.map.project, COS = Math.cos((33.4 * Math.PI) / 180);
  const pick = (e) => {
    const [x, y] = emdCenter(e.d);
    const lon = x / (P.scale * COS) + P.min_lon, lat = P.max_lat - y / P.scale;
    const rn = ctx.map.regions.find((r) => r.region_id === e.region_id)?.name;
    A.editGoal({ stay: { emd: e.emd, region_id: e.region_id, region_name: rn, label: e.emd.replace(/^\S+\s/, ""), lat: +lat.toFixed(5), lon: +lon.toFixed(5) } });
  };
  const pin = stay ? (() => { const e = ctx.map.emds.find((x) => x.emd === stay.emd); return e ? emdCenter(e.d) : null; })() : null;
  return h("div", { class: "card plan-panel", style: { position: "sticky", top: "88px" } },
    h("div", { class: "card-head" },
      h("div", { class: "card-title" }, icon("map", 15), "어디에 머물고, 어디를 다닐까요?"),
      h("label", { class: "switch", title: "동네별 '사는 사람 대비 찾아오는 사람' 비율을 색으로 겹쳐 봅니다" },
        h("input", { type: "checkbox", checked: !!st.showCrowd, onchange: (e) => set({ showCrowd: e.target.checked }) }), h("span", { class: "track" }), "붐비는 정도")),
    h("div", { class: "card-body" },
      h("div", { class: "pp-guide" }, stay ? h("span", {}, "숙소 ", h("b", {}, `${stay.label} · ${stay.region_name}`), " — 다른 동네를 누르면 바뀌어요")
        : h("span", {}, h("b", {}, "숙소가 있는 동네를 지도에서 눌러 주세요."), " 숙소는 보통 한 곳이니, 그 주변부터 동선을 잡아요.")),
      SvgMap({ map: ctx.map, emdValues: st.showCrowd ? values : null, onEmdClick: st.goal ? pick : null, selectedEmd: stay?.emd, pin,
        highlightRegion: stay?.region_id }),
      st.showCrowd ? h("div", { style: { marginTop: "10px" } }, MapLegend({ title: "진할수록 주민 대비 여행객이 많은 동네", source: stats?.source_id ?? "563", period: stats?.period ?? "" })) : null,
      h("div", { class: "pp-label" }, "어디를 다니고 싶나요?"),
      h("div", { class: "area-opts" }, AREAS.map(([k, t, d]) => h("button", {
        class: "area-opt" + ((area || "all") === k ? " on" : ""), disabled: !st.goal || (k === "near" && !stay),
        onclick: () => A.editGoal({ area: k === "all" ? null : k }) }, h("b", {}, t), h("span", {}, d)))),
      !st.goal ? h("div", { class: "notice notice-info", style: { fontSize: "13.5px" } }, "먼저 왼쪽에 여행을 한 줄로 적고 ‘조건 읽기’를 눌러 주세요.") : null,
      st.goal && (stay || area) && !applied ? h("div", { class: "transport-note", style: { marginTop: "12px" } }, icon("alert", 15),
        "숙소·다닐 범위는 지금 서버 버전에서는 표시만 해요. 경로 계산 반영은 업데이트 예정이에요.") : null));
}

export function Step1(st, ctx, A) {
  const stats = ctx.stats[st.goal?.month || 0] || ctx.stats[0];
  const values = Object.fromEntries((stats?.items || []).map((x) => [x.emd, x.pct]));
  const canGo = st.goal && !st.missing.includes("days");
  return h("div", { class: "page", onclick: () => st.openChip && set({ openChip: null }) },
    h("div", { class: "s1" },
      h("div", {},
        h("div", { class: "eyebrow" }, "01 여행 설명"),
        h("h1", { class: "hero-title" }, "나만의 제주 여행을", h("br"), h("em", {}, "한 줄로"), " 들려주세요"),
        h("p", { class: "hero-sub" }, "제주데이터허브 데이터로 방문이 덜 몰리는 지역까지 고려해 AI가 경로를 짜고, 스스로 검증해 고칩니다."),
        h("div", { class: "composer" },
          h("textarea", { id: "intent", rows: 3, placeholder: "예: 2박 3일 동안 바다를 보며 여유롭게 쉬고 싶어요", value: st.text,
            oninput: (e) => set({ text: e.target.value }, { silent: true }),
            onkeydown: (e) => { if (e.key === "Enter" && !e.shiftKey && !e.isComposing && e.keyCode !== 229) { e.preventDefault(); A.parse(); } } }),
          h("div", { class: "composer-foot" },
            h("span", { class: "muted", style: { fontSize: "13.5px" } }, h("span", { class: "kbd" }, "Enter"), " 조건 읽기 · ", h("span", { class: "kbd" }, "Shift"), "+", h("span", { class: "kbd" }, "Enter"), " 줄바꿈"),
            h("button", { class: "btn" + (st.goal ? "" : " btn-dark-outline"), disabled: st.parsing, onclick: A.parse },
              st.parsing ? [h("span", { class: "spinner" }), "읽는 중"] : st.goal ? [icon("reset", 15), "다시 읽기"] : [icon("spark", 15), "조건 읽기"]))),
        h("div", { class: "examples" }, h("span", { class: "muted", style: { fontSize: "14px", alignSelf: "center" } }, "예시"),
          EXAMPLES.map(([label, t]) => h("button", { class: "example", title: t, onclick: () => { set({ text: t }); A.parse(); } }, label))),
        st.goal ? Conditions(st, ctx, A) : null,
        st.goal ? h("div", { class: "cta-row" },
          h("button", { class: "btn btn-primary btn-lg", disabled: !canGo, onclick: () => A.go(2) }, "경로 만들기", icon("arrow", 16)),
          h("span", { class: "muted", style: { fontSize: "14px" } }, "조건이 맞으면 눌러 주세요. AI가 일하는 과정을 그대로 보여드려요")) : null),
      PlanPanel(st, ctx, A, values, stats)));
}
