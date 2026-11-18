// 작은 DOM 헬퍼. h("div", {class: "x", onclick}, child, ...)
const SVG_NS = "http://www.w3.org/2000/svg";

function apply(node, props) {
  for (const [k, v] of Object.entries(props || {})) {
    if (v == null || v === false) continue;
    if (k === "class") node.setAttribute("class", v);
    else if (k === "style" && typeof v === "object") Object.assign(node.style, v);
    else if (k.startsWith("on") && typeof v === "function") node.addEventListener(k.slice(2).toLowerCase(), v);
    else if (k === "html") node.innerHTML = v;
    else if (k === "value" && "value" in node) node.value = v;
    else if (v === true) node.setAttribute(k, "");
    else node.setAttribute(k, v);
  }
}

function append(node, children) {
  for (const c of children.flat(Infinity)) {
    if (c == null || c === false) continue;
    node.appendChild(c instanceof Node ? c : document.createTextNode(String(c)));
  }
}

export function h(tag, props, ...children) {
  const node = document.createElement(tag);
  apply(node, props);
  append(node, children);
  return node;
}

export function s(tag, props, ...children) {
  const node = document.createElementNS(SVG_NS, tag);
  apply(node, props);
  append(node, children);
  return node;
}

export function clear(node) { while (node.firstChild) node.removeChild(node.firstChild); return node; }

export function toast(msg, ms = 2200) {
  const t = h("div", { class: "toast" }, msg);
  document.body.appendChild(t);
  setTimeout(() => t.remove(), ms);
}

// 단순 선 아이콘 (직접 그린 도형)
export function icon(name, size = 16) {
  const p = { width: size, height: size, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", "stroke-width": 2,
    "stroke-linecap": "round", "stroke-linejoin": "round" };
  const paths = {
    arrow: [s("path", { d: "M5 12h14M13 6l6 6-6 6" })],
    reset: [s("path", { d: "M3 12a9 9 0 1 0 3-6.7L3 8" }), s("path", { d: "M3 3v5h5" })],
    check: [s("path", { d: "M5 12l5 5L20 7" })],
    star: [s("path", { d: "M12 3l2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1L3.2 9.5l6.1-.9z" })],
    pin: [s("path", { d: "M12 21s-7-6.2-7-11a7 7 0 0 1 14 0c0 4.8-7 11-7 11z" }), s("circle", { cx: 12, cy: 10, r: 2.5 })],
    x: [s("path", { d: "M6 6l12 12M18 6L6 18" })],
    print: [s("path", { d: "M6 9V3h12v6M6 18H4v-7h16v7h-2" }), s("path", { d: "M6 14h12v7H6z" })],
    map: [s("path", { d: "M9 4L3 6v14l6-2 6 2 6-2V4l-6 2z" }), s("path", { d: "M9 4v14M15 6v14" })],
    list: [s("path", { d: "M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01" })],
    skip: [s("path", { d: "M5 5l8 7-8 7zM19 5v14" })],
    alert: [s("path", { d: "M12 9v4M12 17h.01" }), s("path", { d: "M10.3 3.9L1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z" })],
    plus: [s("path", { d: "M12 5v14M5 12h14" })],
    search: [s("circle", { cx: 11, cy: 11, r: 7 }), s("path", { d: "M20 20l-3.5-3.5" })],
    spark: [s("path", { d: "M12 3v4M12 17v4M3 12h4M17 12h4M5.6 5.6l2.8 2.8M15.6 15.6l2.8 2.8M5.6 18.4l2.8-2.8M15.6 8.4l2.8-2.8" })],
  };
  return s("svg", p, ...(paths[name] || []));
}

// 말 실루엣 (직접 그린 단순 도형)
export function horseGlyph() {
  return s("g", {},
    s("circle", { r: 18, fill: "var(--warm)", stroke: "#fff", "stroke-width": 3 }),
    s("path", { d: "M-7 9 L-7 1 C-7 -5 -3 -9 2 -9 L5 -13 L6 -8.5 C9.5 -7 11 -3.5 10 -1.5 C9.4 -0.3 8 0 6.6 -0.6 L4 -1.6 L3 2 L4 9 Z", fill: "#fff" }),
    s("circle", { cx: 4.2, cy: -5.2, r: 1.2, fill: "var(--warm)" }),
  );
}
