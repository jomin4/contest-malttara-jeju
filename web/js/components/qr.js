// 휴대폰으로 가져가기: 일정 글을 QR 코드에 그대로 담는다 (인터넷 없이 찍으면 글이 나옴).
// qrcode-generator (MIT, vendor/qrcode) — 외부 서버 없이 화면에서 바로 만든다.
import qrcode from "../../vendor/qrcode/qrcode.mjs";
import { stringToBytes } from "../../vendor/qrcode/qrcode_UTF8.mjs";
import { h, s, icon } from "../dom.js";
import { periodLabel } from "../format.js";

qrcode.stringToBytes = stringToBytes;

export function planText(goal, r, regionName) {
  const lines = [`말따라 제주 · ${periodLabel(goal) ?? ""} 여행 계획`];
  for (const d of r.itinerary.days) {
    const route = r.routes.find((x) => x.day === d.day);
    lines.push("");
    lines.push(`[${d.day}일차 · ${regionName(d.region_id)}]${route ? ` 직선 ${route.total_km}km` : ""}`);
    d.place_ids.forEach((id, i) => {
      const p = r.places[id];
      if (p) lines.push(`${i + 1}. ${p.name}${p.category ? ` (${p.category})` : ""}`);
    });
  }
  lines.push("");
  lines.push("거리는 직선 기준(도로·이동시간 아님). 데이터: 제주데이터허브");
  return lines.join("\n");
}

export function QrSvg(text, px = 300) {
  let qr = null;
  for (const level of ["M", "L"]) {   // 길면 오류정정 수준을 낮춰 담는다
    try { qr = qrcode(0, level); qr.addData(text, "Byte"); qr.make(); break; } catch { qr = null; }
  }
  if (!qr) return h("div", { class: "side-empty" }, "일정이 길어 QR에 다 담지 못했어요. 인쇄를 이용해 주세요.");
  const n = qr.getModuleCount(), m = 4, size = n + m * 2;
  let d = "";
  for (let r = 0; r < n; r++) for (let c = 0; c < n; c++) if (qr.isDark(r, c)) d += `M${c + m},${r + m}h1v1h-1z`;
  return s("svg", { viewBox: `0 0 ${size} ${size}`, width: px, height: px, "shape-rendering": "crispEdges", role: "img", "aria-label": "일정 QR 코드" },
    s("rect", { width: size, height: size, fill: "#fff" }), s("path", { d, fill: "#0a0a0a" }));
}

let escClose = null;   // Esc로 닫기 (모달이 다시 그려져도 하나만)
document.addEventListener("keydown", (e) => { if (e.key === "Escape" && escClose && document.querySelector(".qr-modal")) escClose(); });

export function QrModal({ text, onClose, onPrint }) {
  escClose = onClose;
  const bg = h("div", { class: "modal-bg", onclick: (e) => { if (e.target === bg) onClose(); } },
    h("div", { class: "modal qr-modal" },
      h("div", { class: "qr-top" }, h("div", { class: "modal-t" }, "휴대폰으로 가져가기"),
        h("button", { class: "btn btn-sm btn-ghost", onclick: onClose }, icon("x", 16))),
      h("div", { class: "qr-body" },
        h("div", { class: "qr-box" }, QrSvg(text, 320)),
        h("div", { class: "qr-side" },
          h("ol", { class: "qr-steps" },
            h("li", {}, "휴대폰 카메라를 QR 코드에 비춰 주세요."),
            h("li", {}, "일정 글이 나타나면 복사하거나 메모에 저장하세요."),
            h("li", {}, "인터넷이 없어도 글은 그대로 보입니다.")),
          h("pre", { class: "qr-preview" }, text),
          onPrint ? h("button", { class: "btn", onclick: onPrint }, icon("print", 15), "인쇄하기") : null))));
  return bg;
}
