import { h, icon } from "../dom.js";
import { set } from "../state.js";
import { normalizeTyping, REACT, REACT_HINT } from "../format.js";
import { SvgMap, project, dayColor } from "../components/map.js";
import { DayList, DayTabs } from "./step2.js";

function Game(st, ctx, A, r) {
  const quests = r.quests;
  const q = quests.find((x) => x.day === st.game.day) || quests[0];
  const idx = st.game.idx;
  const cur = q.items[idx];
  const done = idx >= q.items.length;
  const lastArrived = idx > 0 ? q.items[idx - 1].place_id : null;
  const P = r.places;
  const pos = (id) => project(P[id].lat, P[id].lon, ctx.map.project);
  const horseAt = lastArrived ? pos(lastArrived) : (() => { const [x, y] = pos(q.items[0].place_id); return [x - 34, y + 10]; })();
  const dayItin = { days: r.itinerary.days.filter((d) => d.day === q.day) };
  const [, , MW, MH] = ctx.map.view_box.split(" ").map(Number);
  const pts = q.items.map((it) => pos(it.place_id));
  const xs = pts.map((p) => p[0]), ys = pts.map((p) => p[1]);
  const AR = 2.4; // 게임 지도 영역의 가로:세로
  let vw = Math.max(Math.max(...xs) - Math.min(...xs) + 260, 560), vh = vw / AR;
  if (Math.max(...ys) - Math.min(...ys) + 160 > vh) { vh = Math.max(...ys) - Math.min(...ys) + 160; vw = vh * AR; }
  const cx = (Math.max(...xs) + Math.min(...xs)) / 2, cy = (Math.max(...ys) + Math.min(...ys)) / 2;
  const vx = Math.min(Math.max(cx - vw / 2, -40), MW - vw + 40), vy = Math.min(Math.max(cy - vh / 2, -40), MH - vh + 40);
  const zoomBox = `${vx.toFixed(0)} ${vy.toFixed(0)} ${vw.toFixed(0)} ${vh.toFixed(0)}`;
  const nextDay = quests.find((x) => x.day === q.day + 1);

  const advance = (arrived) => {
    if (arrived) A.arrive(cur.place_id);
    set({ game: { day: q.day, idx: idx + 1 }, selPlace: arrived ? cur.place_id : null });
  };
  const check = (input) => {
    if (normalizeTyping(input.value) === normalizeTyping(cur.label)) { advance(true); return true; }
    return false;
  };
  const paint = (n) => {
    // 띄어쓰기를 뺀 n글자까지 강조 (표시는 원래 띄어쓰기 유지)
    let seen = 0, cut = 0;
    for (const ch of cur.label) { if (seen >= n) break; cut++; if (!/\s/.test(ch)) seen++; }
    const t = document.getElementById("typed"), u = document.getElementById("untyped");
    if (t) t.textContent = cur.label.slice(0, cut);
    if (u) u.textContent = cur.label.slice(cut);
  };
  const onInput = (e) => {
    if (e.isComposing) return;
    const v = normalizeTyping(e.target.value), target = normalizeTyping(cur.label);
    let n = 0; while (n < v.length && v[n] === target[n]) n++;
    paint(n);
    if (v === target) check(e.target);
  };
  const onKey = (e) => {
    if (e.key !== "Enter" || e.isComposing || e.keyCode === 229) return;
    e.preventDefault();
    if (!check(e.target)) {
      e.target.classList.remove("shake"); void e.target.offsetWidth; e.target.classList.add("shake");
      const hint = document.getElementById("hint"); if (hint) hint.textContent = `글자 수 힌트: ${normalizeTyping(cur.label).length}자 (띄어쓰기 무시)`;
    }
  };
  if (!done) queueMicrotask(() => document.getElementById("typein")?.focus({ preventScroll: true }));

  const arrivedPlace = st.selPlace && P[st.selPlace] ? P[st.selPlace] : null;
  return h("div", { class: "card stage" },
      h("div", { class: "card-head" },
        h("div", { class: "card-title" }, h("span", { class: "pnum", style: { background: dayColor(q.day), width: "24px", height: "24px", fontSize: "12px" } }, q.day), `${q.day}일차 경로 따라가기`),
        h("div", { class: "daytabs" }, quests.map((x) => h("button", { class: "daytab" + (x.day === q.day ? " on" : ""), onclick: () => set({ game: { day: x.day, idx: 0 }, selPlace: null }) },
          h("span", { class: "sw", style: { background: dayColor(x.day) } }), `${x.day}일차`)))),
      h("div", { class: "stage-map" },
        SvgMap({ map: ctx.map, itinerary: dayItin, places: P, horseAt, showLabels: true, viewBox: zoomBox, zoom: Math.min(1, vw / 900),
          markerState: (id, day, i) => (i < idx ? "done" : i === idx ? "next" : "") }),
        arrivedPlace ? h("div", { class: "overlay arrive" },
          h("div", { class: "overlay-top" }, h("span", { class: "eyebrow" }, "도착! · 가상 탐험"), h("button", { class: "btn btn-sm btn-ghost", onclick: () => set({ selPlace: null }) }, icon("x", 14))),
          h("div", { class: "ov-name" }, arrivedPlace.name),
          h("div", { class: "prow-meta" }, `${arrivedPlace.category ?? "분류 없음"} · ${arrivedPlace.region_name}`),
          h("div", { class: "react", style: { marginTop: "12px" } }, ["interest", "must", "dislike"].map((v) => h("button", {
            class: `${v} ${st.feedback[arrivedPlace.place_id] === v ? "on" : ""}`, onclick: () => A.react(arrivedPlace.place_id, v) },
            h("span", { class: "rb" }, h("span", { class: "rb-t" }, v === "interest" ? icon("star", 15) : v === "must" ? icon("pin", 15) : icon("x", 15), REACT[v]), h("span", { class: "rb-h" }, REACT_HINT[v]))))),
          h("div", { class: "muted", style: { fontSize: "13.5px", marginTop: "10px" } }, "다시 짤 때 반영해요. 데이터 근거는 ‘목록으로 보기’에서 볼 수 있어요.")) : null),
      h("div", { class: "typebar" },
        done
          ? h("div", {}, h("div", { class: "target" }, h("span", { class: "lbl" }, "완료"), h("span", { class: "name" }, `${q.day}일차 도착!`)),
              h("div", { class: "hint" }, nextDay ? "다음 날로 넘어가세요." : "모든 날을 둘러봤어요. 아래 ‘다시 짜기’를 눌러 주세요."))
          : h("div", {},
              h("div", { class: "target" }, h("span", { class: "lbl" }, `다음 목적지 ${idx + 1}/${q.items.length}`),
                h("span", { class: "name" }, h("span", { class: "typed", id: "typed" }), h("span", { id: "untyped" }, cur.label))),
              h("input", { class: "typein", id: "typein", autocomplete: "off", spellcheck: "false", placeholder: "위 지명을 그대로 입력하고 Enter", oninput: onInput, onkeydown: onKey,
                oncompositionend: (e) => onInput({ isComposing: false, target: e.target }) }),
              h("div", { class: "hint", id: "hint" }, "띄어쓰기는 무시해요. 어려우면 ‘건너뛰기’나 ‘목록으로 보기’를 쓰세요.")),
        h("div", { style: { display: "flex", flexDirection: "column", gap: "10px", alignItems: "flex-end" } },
          h("div", { class: "progress" }, q.items.map((_, i) => h("i", { class: i < idx ? "done" : i === idx ? "cur" : "" }))),
          done ? (nextDay ? h("button", { class: "btn btn-primary btn-lg", onclick: () => set({ game: { day: nextDay.day, idx: 0 }, selPlace: null }) }, `${nextDay.day}일차로`, icon("arrow", 16)) : null)
            : h("button", { class: "btn", onclick: () => advance(false) }, icon("skip", 15), "건너뛰기"))));
}

export function Step3(st, ctx, A) {
  const r = st.batchA?.result;
  if (!r) return h("div", { class: "page" }, "경로가 아직 없습니다.");
  const c = (v) => Object.values(st.feedback).filter((x) => x === v).length;
  return h("div", { class: "page" },
    h("div", { class: "pagehead" },
      h("div", {}, h("div", { class: "eyebrow" }, "03 미리 둘러보기"),
        h("h1", {}, st.previewMode === "game" ? "지명을 입력하면 말이 달려가요" : "장소를 보고 반응을 남겨 주세요"),
        h("div", { class: "muted lead" }, "좋아요는 비슷한 곳을 더, 꼭 갈래요는 고정, 별로예요는 다른 곳으로 바꿔요. 게임은 선택이에요.")),
      h("div", { class: "actions" },
        h("div", { class: "seg seg-lg" },
          h("button", { class: st.previewMode === "game" ? "on" : "", onclick: () => set({ previewMode: "game" }) }, "게임으로 보기"),
          h("button", { class: st.previewMode === "list" ? "on" : "", onclick: () => set({ previewMode: "list" }) }, "목록으로 보기")))),
    st.previewMode === "game" ? Game(st, ctx, A, r)
      : h("div", { class: "list-wrap" }, h("div", { style: { marginBottom: "8px" } }, DayTabs(st, r.itinerary, r.places)), DayList(st, ctx, A, r, { onReact: (id, v) => A.react(id, v) })),
    h("div", { class: "footer-cta" },
      h("div", { class: "tally" }, h("span", {}, "좋아요 ", h("b", {}, c("interest"))), h("span", {}, "꼭 갈래요 ", h("b", {}, c("must"))), h("span", {}, "별로예요 ", h("b", {}, c("dislike"))),
        h("span", {}, "· 반응이 없어도 괜찮아요")),
      h("button", { class: "btn btn-primary btn-lg", onclick: () => { set({ batchB: null }); A.go(4); } }, "반영해서 다시 짜기", icon("arrow", 16))));
}
