// 사용 가이드(코치 마크): 화면을 어둡게 하고 설명할 곳만 밝게 비추며 단계별로 이동한다.
// 앱은 상태가 바뀔 때마다 화면을 통째로 다시 그리므로, 가이드는 앱 밖(body)에 따로 두고
// 매 프레임 대상 요소를 다시 찾아 위치를 맞춘다. 01→04 화면을 넘어가며 이어진다.
import { h, icon } from "../dom.js";
import { state, subscribe } from "../state.js";

const $ = (sel) => document.querySelector(sel);
const btnText = (t, scope = document) => [...scope.querySelectorAll("button")].find((b) => b.offsetParent && b.textContent.includes(t));
const click = (el) => el && el.click();

// 화면별 단계. target: 요소를 돌려주는 함수, prepare: 보여주기 전에 화면을 준비(예시 넣기 등),
// waitText: 대상이 아직 없을 때 보여줄 안내, last: 이 화면 마지막 → go로 다음 화면 이동
const TOURS = {
  1: [
    { target: () => $(".composer"), title: "여행을 한 줄로 적어요",
      body: "기간·여유·관심사를 문장 그대로 적으면 AI가 읽어요. 예: “2박 3일 바다 보며 여유롭게, 현지 음식도”." },
    { target: () => $(".examples"), title: "예시로 바로 시작",
      body: "잘 모르겠으면 예시를 눌러 보세요. 가이드에서는 첫 번째 예시를 넣어 볼게요." },
    { target: () => $(".conds"), prepare: () => { if (!state.goal) click($(".example")); }, waitText: "조건을 읽는 중…",
      title: "이렇게 이해했어요",
      body: "읽은 조건이 칩으로 나와요. 칩을 누르면 고칠 수 있어요. 회색은 입력하지 않은 조건이에요 — 임의로 채우지 않아요." },
    { target: () => $(".plan-panel"), title: "숙소와 다닐 범위",
      body: "지도에서 숙소 동네를 누르면 4개 권역 중 어디인지 보여요. 섬 전체·숙소 근처·해안·중산간 중 다닐 범위도 고를 수 있어요." },
    { target: () => btnText("경로 만들기"), title: "경로 만들기", last: true, nextLabel: "경로 만들기",
      body: "준비되면 눌러 주세요. AI가 후보를 찾고, 일정을 짜고, 스스로 검증해 고치는 과정을 그대로 보여 드려요.",
      go: () => click(btnText("경로 만들기")) },
  ],
  2: [
    { target: () => $(".stepper") || $(".s2-left .card"), title: "AI가 일하는 과정",
      body: "조건 이해 → 후보 찾기 → 일정 짜기 → 검증 → 수정. 무엇을 판단했는지 한 줄씩 기록돼요.", skipIf: () => !!state.batchA?.result },
    { target: () => $(".daylist .day"), waitText: "AI가 경로를 짜는 중이에요…", title: "날짜별 일정",
      body: "하루에 한 권역만 다니고, 가까운 곳끼리 이었어요. ‘근거 보기’를 누르면 고른 이유와 데이터 숫자가 나와요." },
    { target: () => $(".map-card"), title: "지도",
      body: "방문 순서를 잇는 선이에요(직선 거리). 위 일차 탭으로 하루씩 볼 수 있어요." },
    { target: () => $(".view-switch"), title: "직접 고르기",
      body: "추천이 마음에 안 들면 ‘직접 고르기’로 전체 장소에서 골라 담을 수 있어요. 담은 곳은 다시 짤 때 꼭 넣어요." },
    { target: () => $(".btn-why"), title: "왜 이렇게 짰나요?",
      body: "조건을 어떻게 이해했고, 어떤 데이터로 골랐고, 무엇을 고쳤는지 순서대로 설명해 드려요." },
    { target: () => btnText("미리 둘러보기"), title: "미리 둘러보기", last: true, nextLabel: "미리 둘러보기",
      body: "말을 타고 일정을 미리 둘러보며 장소마다 반응을 남겨요.", go: () => click(btnText("미리 둘러보기")) },
  ],
  3: [
    { target: () => $(".stage"), waitText: "지도를 불러오는 중…", title: "말 타고 미리 둘러보기",
      body: "제주 지형 위로 오늘 갈 곳이 핀으로 표시돼요. 말이 순서대로 달려가요." },
    { target: () => $(".typebar"), title: "지명을 치면 달려가요",
      body: "아래 지명을 그대로 입력하면 친 만큼 말이 움직여요. 귀찮으면 ‘건너뛰기’를 눌러도 돼요." },
    { target: () => $(".typebar"), title: "도착하면 반응을 남겨요",
      body: "1 좋아요 · 2 꼭 갈래요 · 3 별로예요. 꼭 갈래요는 고정, 별로예요는 같은 권역의 다른 곳으로 바꿔 다시 짜요." },
    { target: () => $(".stage-head .stage-right") || $(".stage-head"), title: "보기 바꾸기",
      body: "3D·2D 지도, 게임·목록 보기를 바꿀 수 있어요. 반응 수도 여기서 보여요." },
    { target: () => btnText("다시 짜기", $(".stage-head") || document) || btnText("다시 짜기"), title: "다시 짜기", last: true, nextLabel: "다시 짜기",
      body: "남긴 반응을 반영해 일정을 다시 짜요. 둘러보기를 다 마치지 않아도 괜찮아요.",
      go: () => click(btnText("다시 짜기", $(".stage-head") || document) || btnText("다시 짜기")) },
  ],
  4: [
    { target: () => $(".daylist .day"), waitText: "반응을 반영해 다시 짜는 중…", title: "최종 계획",
      body: "바뀐 곳에는 고정·교체·추가 표시와 이유가 붙어요. 최종 선택은 여러분이 해요." },
    { target: () => btnText("휴대폰으로 가져가기"), title: "휴대폰으로 가져가기",
      body: "QR을 휴대폰 카메라로 비추면 일정 글이 나와요. 인터넷이 없어도 보여요." },
    { target: () => btnText("인쇄"), title: "인쇄", body: "종이로 받고 싶으면 인쇄할 수 있어요." },
    { target: () => $('button[title="처음부터"]'), title: "다음 분을 위해", last: true, nextLabel: "가이드 마치기",
      body: "다 보셨으면 ‘처음부터’를 눌러 주세요. 2분 동안 아무것도 안 하면 자동으로 처음 화면으로 돌아가요." },
  ],
};

let T = null;   // { screen, i, follow, done:Set } — 진행 중인 가이드
let root = null, raf = 0, shownAt = 0, prepared = new Set();

function steps() { return (TOURS[T.screen] || []).filter((s) => !s.skipIf?.()); }

export function startTour(follow = true) {
  T = { screen: state.step, i: 0, follow, done: new Set() };
  prepared = new Set();
  mount();
}

export function stopTour() {
  if (T) T.done.add(T.screen);
  T = null;
  cancelAnimationFrame(raf);
  root?.remove(); root = null;
  document.documentElement.classList.remove("touring");
}

function go(delta) {
  const list = steps();
  const s = list[T.i];
  if (delta > 0 && s?.last) {
    T.done.add(T.screen);
    if (s.go) { s.go(); hideWhileMoving(); return; }   // 다음 화면으로 → subscribe가 이어 받음
    return stopTour();
  }
  T.i = Math.max(0, Math.min(list.length - 1, T.i + delta));
  shownAt = 0;
}

function hideWhileMoving() { if (root) root.dataset.state = "moving"; }

// 화면이 바뀌면 그 화면 가이드로 이어서 진행
subscribe(() => {
  if (!T) return;
  if (state.step !== T.screen) {
    if (!T.follow || T.done.has(state.step)) return stopTour();
    T.screen = state.step; T.i = 0; shownAt = 0;
  }
});

function mount() {
  root?.remove();
  document.documentElement.classList.add("touring");
  root = h("div", { class: "tour", role: "dialog", "aria-modal": "true", "aria-live": "polite" },
    ["t", "r", "b", "l"].map((k) => h("div", { class: `tour-shade tour-${k}` })),
    h("div", { class: "tour-hole" }),
    h("div", { class: "tour-tip" }));
  // 어두운 곳을 눌러도 아무 일 없게(실수로 앱 버튼이 눌리지 않게)
  root.addEventListener("pointerdown", (e) => { if (e.target.classList.contains("tour-shade")) e.preventDefault(); });
  document.body.appendChild(root);
  loop();
}

function loop() {
  cancelAnimationFrame(raf);
  raf = requestAnimationFrame(() => { if (T && root) { frame(); loop(); } });
}

function frame() {
  const list = steps();
  if (!list.length) return stopTour();
  if (T.i >= list.length) T.i = list.length - 1;
  const s = list[T.i];
  const key = `${T.screen}:${T.i}`;
  if (s.prepare && !prepared.has(key)) { prepared.add(key); s.prepare(); }
  const el = s.target?.();
  const tip = root.querySelector(".tour-tip");
  const vw = window.innerWidth, vh = window.innerHeight;
  if (!el || !el.getBoundingClientRect().width) {   // 아직 없음(처리 중) → 가운데 안내
    root.dataset.state = "wait";
    place(null, vw, vh);
    renderTip(tip, s, list, s.waitText || "잠시만요…", true);
    centerTip(tip, vw, vh);
    return;
  }
  if (!shownAt) { shownAt = performance.now(); el.scrollIntoView({ block: "center", behavior: "smooth" }); }
  root.dataset.state = "on";
  const r = el.getBoundingClientRect();
  const pad = 8;
  const box = { x: Math.max(4, r.left - pad), y: Math.max(4, r.top - pad), w: Math.min(vw - 8, r.width + pad * 2), h: Math.min(vh - 8, r.height + pad * 2) };
  place(box, vw, vh);
  renderTip(tip, s, list, null, false);
  positionTip(tip, box, vw, vh);
}

function place(b, vw, vh) {
  const [t, rr, bb, l] = root.querySelectorAll(".tour-shade");
  const hole = root.querySelector(".tour-hole");
  if (!b) { Object.assign(t.style, { left: 0, top: 0, width: vw + "px", height: vh + "px" }); [rr, bb, l].forEach((x) => (x.style.height = "0")); hole.style.opacity = 0; return; }
  hole.style.opacity = 1;
  Object.assign(t.style, { left: 0, top: 0, width: vw + "px", height: b.y + "px" });
  Object.assign(bb.style, { left: 0, top: b.y + b.h + "px", width: vw + "px", height: Math.max(0, vh - b.y - b.h) + "px" });
  Object.assign(l.style, { left: 0, top: b.y + "px", width: b.x + "px", height: b.h + "px" });
  Object.assign(rr.style, { left: b.x + b.w + "px", top: b.y + "px", width: Math.max(0, vw - b.x - b.w) + "px", height: b.h + "px" });
  Object.assign(hole.style, { left: b.x + "px", top: b.y + "px", width: b.w + "px", height: b.h + "px" });
}

let lastSig = "";
function renderTip(tip, s, list, waitText, waiting) {
  const sig = `${T.screen}|${T.i}|${list.length}|${waiting}`;
  if (sig === lastSig && tip.firstChild) return;
  lastSig = sig;
  tip.replaceChildren(
    h("div", { class: "tour-top" },
      h("span", { class: "tour-screen" }, `0${T.screen} 화면`),
      h("span", { class: "tour-count" }, `${T.i + 1} / ${list.length}`),
      h("button", { class: "tour-x", "aria-label": "가이드 닫기", onclick: stopTour }, icon("x", 16))),
    h("div", { class: "tour-title" }, waiting ? [h("span", { class: "spinner sm" }), " ", waitText] : s.title),
    waiting ? null : h("div", { class: "tour-body" }, s.body),
    h("div", { class: "tour-dots" }, list.map((_, i) => h("i", { class: i === T.i ? "on" : "" }))),
    h("div", { class: "tour-actions" },
      h("button", { class: "btn btn-ghost btn-sm", onclick: stopTour }, "그만 보기"),
      h("span", { class: "grow" }),
      T.i > 0 ? h("button", { class: "btn btn-sm", onclick: () => go(-1) }, "이전") : null,
      h("button", { class: "btn btn-primary btn-sm", disabled: waiting, onclick: () => go(1) },
        s.last ? (s.nextLabel || "다음 화면") : "다음", h("span", { class: "tour-enter" }, "Enter"))),
    h("div", { class: "tour-keys" },
      h("span", { class: "kbd" }, "Enter"), " 또는 ", h("span", { class: "kbd" }, "→"), " 다음 · ",
      h("span", { class: "kbd" }, "←"), " 이전 · ", h("span", { class: "kbd" }, "Esc"), " 닫기"));
}

function centerTip(tip, vw, vh) {
  tip.dataset.side = "center";
  tip.style.left = Math.max(12, (vw - tip.offsetWidth) / 2) + "px";
  tip.style.top = Math.max(12, (vh - tip.offsetHeight) / 2) + "px";
}

function positionTip(tip, b, vw, vh) {
  const tw = tip.offsetWidth, th = tip.offsetHeight, gap = 14, m = 12;
  let side, x, y;
  if (vw < 640) { side = b.y + b.h / 2 > vh / 2 ? "top-sheet" : "bottom-sheet"; }
  else if (b.y + b.h + gap + th < vh - m) side = "bottom";
  else if (b.y - gap - th > m) side = "top";
  else if (b.x + b.w + gap + tw < vw - m) side = "right";
  else if (b.x - gap - tw > m) side = "left";
  else side = "inside";
  if (side === "bottom") { x = b.x; y = b.y + b.h + gap; }
  else if (side === "top") { x = b.x; y = b.y - gap - th; }
  else if (side === "right") { x = b.x + b.w + gap; y = b.y; }
  else if (side === "left") { x = b.x - gap - tw; y = b.y; }
  else if (side === "inside") { x = b.x + b.w - tw - m; y = b.y + b.h - th - m; }
  else if (side === "bottom-sheet") { x = m; y = vh - th - m; }
  else { x = m; y = m; }
  tip.dataset.side = side;
  tip.style.left = Math.round(Math.max(m, Math.min(vw - tw - m, x))) + "px";
  tip.style.top = Math.round(Math.max(m, Math.min(vh - th - m, y))) + "px";
}

// 키보드: → / Enter 다음, ← 이전, Esc 닫기. 앱 단축키(게임 Enter 등)보다 먼저 받는다.
window.addEventListener("keydown", (e) => {
  const offer = document.querySelector(".guide-offer");
  if (offer && !T && !e.isComposing && (e.key === "Enter" || e.key === "Escape")) {   // 첫 화면 제안 카드
    e.preventDefault(); e.stopImmediatePropagation();
    offer.querySelector(e.key === "Enter" ? ".btn-primary" : ".btn:not(.btn-primary)")?.click();
    return;
  }
  if (!T || !root) return;
  if (e.isComposing) return;
  const k = e.key;
  if (k === "Escape") { stopTour(); }
  else if (k === "ArrowRight" || k === "Enter") { if (root.dataset.state === "on") go(1); }
  else if (k === "ArrowLeft") { go(-1); }
  else return;
  e.preventDefault(); e.stopImmediatePropagation();
}, { capture: true });

// 스크롤 중에는 밝은 영역이 늦게 따라오지 않게 애니메이션을 끈다
let scrollT = 0;
window.addEventListener("scroll", () => {
  if (!root) return;
  root.classList.add("noanim");
  clearTimeout(scrollT);
  scrollT = setTimeout(() => root?.classList.remove("noanim"), 180);
}, { passive: true, capture: true });

export const tourActive = () => !!T;

// 첫 화면 처음 열었을 때 한 번: 가이드 볼지 묻는 카드
export function GuideOffer({ onStart, onSkip }) {
  return h("div", { class: "guide-offer", role: "dialog" },
    h("div", { class: "guide-card" },
      h("div", { class: "guide-badge" }, icon("spark", 16), "처음이세요?"),
      h("div", { class: "guide-t" }, "30초 사용 가이드"),
      h("div", { class: "guide-d" }, "어떻게 쓰는지 화면을 따라가며 짚어 드릴게요. 언제든 위쪽 ‘가이드’ 버튼으로 다시 볼 수 있어요."),
      h("div", { class: "guide-a" },
        h("button", { class: "btn", onclick: onSkip }, "괜찮아요"),
        h("button", { class: "btn btn-primary", onclick: onStart }, "가이드 시작", h("span", { class: "tour-enter" }, "Enter"))),
      h("div", { class: "tour-keys" }, "가이드 중에는 ", h("span", { class: "kbd" }, "Enter"), "로 다음 설명으로 넘어가요")));
}
