// This file is part of PSMemoryManager.
// SPDX-License-Identifier: GPL-3.0-or-later

import { LANGS, detectLang, getLang, locale, setLang, t, translateDom } from "./i18n.js?v=26c72f47abbf";
import { IconRenderer, isAnimated, parseIcon } from "./ps2icon.js?v=26c72f47abbf";

// Build id of this page (filled in by tools/build_site.py). Every asset URL
// carries it, so a new deploy never mixes old and new files.
const BUILD = "26c72f47abbf";

// ---------------------------------------------------------------------------
// Icons (simple strokes, inherit text color)

const S = 'fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"';
const ICONS = {
  open: `<path ${S} d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v1"/><path ${S} d="M3 7v10a2 2 0 0 0 2 2h12.5a2 2 0 0 0 1.9-1.4L22 11H7.5a2 2 0 0 0-1.9 1.4L3 19"/>`,
  card: `<path ${S} d="M6 3h9l4 4v13a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1z"/><path ${S} d="M8 3v4M11 3v4M14 3v4"/><path ${S} d="M12 11v6M9 14h6"/>`,
  "save-disk": `<path ${S} d="M5 3h11l3 3v13a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2z"/><path ${S} d="M7 3v5h8V3M7 21v-7h10v7"/>`,
  download: `<path ${S} d="M12 3v12M7 10l5 5 5-5"/><path ${S} d="M4 17v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2"/>`,
  undo: `<path ${S} d="M9 14L4 9l5-5"/><path ${S} d="M4 9h10.5a5.5 5.5 0 0 1 0 11H11"/>`,
  "add-file": `<path ${S} d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path ${S} d="M14 3v5h5M12 11v6M9 14h6"/>`,
  "add-folder": `<path ${S} d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><path ${S} d="M12 10v6M9 13h6"/>`,
  "import-folder": `<path ${S} d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><path ${S} d="M12 9v7M9 13l3 3 3-3"/>`,
  "import-save": `<rect ${S} x="2.5" y="9" width="19" height="11" rx="5.5"/><path ${S} d="M12 2v6M9.5 5.5 12 8l2.5-2.5"/><path ${S} d="M7.5 12.5v4M5.5 14.5h4"/>`,
  "export-save": `<rect ${S} x="2.5" y="9" width="19" height="11" rx="5.5"/><path ${S} d="M12 8V2M9.5 4.5 12 2l2.5 2.5"/><path ${S} d="M7.5 12.5v4M5.5 14.5h4"/>`,
  columns: `<rect ${S} x="3" y="4" width="18" height="16" rx="2"/><path ${S} d="M12 4v16"/>`,
  copy: `<rect ${S} x="8" y="8" width="13" height="13" rx="2"/><path ${S} d="M16 8V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h3"/>`,
  close: `<path ${S} d="M6 6l12 12M18 6 6 18"/>`,
  sd: `<path ${S} d="M8 3h9a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V7z"/><path ${S} d="M10 7v3M13 7v3M16 7v3"/>`,
  gear: `<circle ${S} cx="12" cy="12" r="3"/><path ${S} d="M12 2v3M12 19v3M4.9 4.9 7 7M17 17l2.1 2.1M2 12h3M19 12h3M4.9 19.1 7 17M17 7l2.1-2.1"/>`,
  link: `<path ${S} d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1"/><path ${S} d="M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1"/>`,
  plus: `<path ${S} d="M12 5v14M5 12h14"/>`,
  tag: `<path ${S} d="M3 12V4a1 1 0 0 1 1-1h8l9 9-9 9z"/><circle cx="8" cy="8" r="1.4" fill="currentColor"/>`,
  reload: `<path ${S} d="M20 11a8 8 0 1 0-2.3 5.7"/><path ${S} d="M20 4v7h-7"/>`,
  convert: `<path ${S} d="M4 8h13l-3-3M20 16H7l3 3"/>`,
  resize: `<path ${S} d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7"/>`,
  memcard: `<path ${S} d="M6 3h9l4 4v13a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1z"/><path ${S} d="M8 3v4M11 3v4M14 3v4"/>`,
  split: `<path ${S} d="M12 3v6M12 9 6 15v6M12 9l6 6v6"/>`,
  extract: `<path ${S} d="M12 3v12M7 10l5 5 5-5"/><path ${S} d="M4 17v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2"/>`,
  rename: `<path ${S} d="M4 20h4L19 9l-4-4L4 16z"/><path ${S} d="M13 7l4 4"/>`,
  delete: `<path ${S} d="M4 7h16M10 11v6M14 11v6M6 7l1 12a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2l1-12M9 7V4h6v3"/>`,
  check: `<path ${S} d="M12 3l8 3v6c0 4.5-3.4 8-8 9-4.6-1-8-4.5-8-9V6z"/><path ${S} d="M8.5 12l2.5 2.5 4.5-5"/>`,
  folder: `<path ${S} d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>`,
  file: `<path ${S} d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path ${S} d="M14 3v5h5"/>`,
  save: `<rect ${S} x="2.5" y="7" width="19" height="11" rx="5.5"/><path ${S} d="M7.5 10.5v4M5.5 12.5h4"/><circle cx="15.5" cy="11.5" r="1.1" fill="currentColor"/><circle cx="18" cy="13.5" r="1.1" fill="currentColor"/>`,
  lock: `<rect ${S} x="5" y="11" width="14" height="10" rx="2"/><path ${S} d="M8 11V8a4 4 0 0 1 8 0v3"/>`,
  chevron: `<path ${S} d="M9 6l6 6-6 6"/>`,
  sun: `<circle ${S} cx="12" cy="12" r="4"/><path ${S} d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>`,
  moon: `<path ${S} d="M20 14.5A8 8 0 0 1 9.5 4 8 8 0 1 0 20 14.5z"/>`,
  auto: `<circle ${S} cx="12" cy="12" r="8"/><path d="M12 4a8 8 0 0 1 0 16z" fill="currentColor"/>`,
  compare: `<path ${S} d="M4 8h13l-3-3M20 16H7l3 3"/>`,
  search: `<circle ${S} cx="11" cy="11" r="6.5"/><path ${S} d="M16 16l5 5"/>`,
  list: `<path ${S} d="M9 6h11M9 12h11M9 18h11"/><circle cx="4.5" cy="6" r="1.3" fill="currentColor"/><circle cx="4.5" cy="12" r="1.3" fill="currentColor"/><circle cx="4.5" cy="18" r="1.3" fill="currentColor"/>`,
  archive: `<path ${S} d="M3 4h18v4H3z"/><path ${S} d="M5 8v11a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V8"/><path ${S} d="M10 12h4"/>`,
  warn: `<path ${S} d="M12 3.5 2.5 20h19z"/><path ${S} d="M12 10v4.5"/><circle cx="12" cy="17.2" r="1.1" fill="currentColor"/>`,
};
const svg = (name) => `<svg viewBox="0 0 24 24" aria-hidden="true">${ICONS[name] || ""}</svg>`;
function paintIcons(root = document) {
  root.querySelectorAll("i[data-icon]").forEach((el) => { el.innerHTML = svg(el.dataset.icon); });
}

// ---------------------------------------------------------------------------
// Utilities

const $ = (sel, root = document) => root.querySelector(sel);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

function human(n) {
  if (n == null) return "";
  if (n < 1024) return `${n} B`;
  const units = ["KB", "MB", "GB"];
  let v = n / 1024, i = 0;
  while (v >= 1024 && i < units.length - 1) { v /= 1024; i++; }
  const digits = v >= 100 ? 0 : 1;
  const num = new Intl.NumberFormat(locale(), { maximumFractionDigits: digits, minimumFractionDigits: digits }).format(v);
  return `${num} ${units[i]}`;
}
const fmtDate = (iso) => (iso ? new Intl.DateTimeFormat(locale(), { dateStyle: "short", timeStyle: "short" }).format(new Date(iso)) : "—");
const fmtInt = (n) => new Intl.NumberFormat(locale()).format(n);

const CARD_EXT = [".mcd", ".bin", ".vmc", ".ps2", ".mc2", ".mcr", ".gme", ".vmp", ".vgs", ".mem", ".srm", ".mc", ".ps", ".psm", ".ddf", ".mci", ".vm1"];
const SAVE_EXT = [".psu", ".max", ".cbs", ".sps", ".xps", ".psv", ".mcs", ".ps1", ".psx", ".mcb", ".mcx", ".pda"];
const CARD_SIZES = new Set();
for (const mb of [1, 2, 4, 8, 16, 32, 64, 128]) {
  const raw = mb * 1024 * 1024;
  CARD_SIZES.add(raw);
  CARD_SIZES.add(raw / 512 * 528);
}
const PS1_SIZE = 128 * 1024;
// PS1: raw, DexDrive (.gme), Connectix VGS, PSP/Vita (.vmp)
for (const extra of [0, 3904, 64, 128]) CARD_SIZES.add(PS1_SIZE + extra);
const hasExt = (name, list) => list.some((e) => name.toLowerCase().endsWith(e));
// A card extension at 128 KB or more is a card (whatever its exact size: the core
// reports odd sizes); smaller files are saves (a PS1 save has at most 120 KB).
// DexDrive files are often cut after the last used block, so any .gme counts.
const isCardLike = (name, size) => hasExt(name, CARD_EXT) && (size >= PS1_SIZE || hasExt(name, [".gme"]));
const looksLikeCard = (file) => isCardLike(file.name, file.size);
const isPs1 = (p) => p?.summary?.card.platform === "PS1";

function download(name, data, type = "application/octet-stream") {
  const url = URL.createObjectURL(new Blob([data], { type }));
  const a = document.createElement("a");
  a.href = url; a.download = name;
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 30_000);
}

function toast(msg, kind = "") {
  const el = document.createElement("div");
  el.className = `toast ${kind}`;
  el.textContent = msg;
  const box = $("#toasts");
  box.appendChild(el);
  while (box.children.length > 3) box.firstElementChild.remove(); // keep the screen readable
  setTimeout(() => el.remove(), kind === "error" ? 9000 : 4500);
}

// the status line remembers its key so it can be re-translated
let statusMsg = { key: "st.ready", params: null };
function status(key, params = null) { statusMsg = { key, params }; $("#status").textContent = t(key, params); }

const storage = {
  get(k, d) { try { return localStorage.getItem(k) ?? d; } catch { return d; } },
  set(k, v) { try { localStorage.setItem(k, v); } catch { /* no storage */ } },
};

// ---------------------------------------------------------------------------
// PS1 save icons: 16x16, 16 colours, 1-3 frames (animated like on the console)

const iconCache = new Map();
function ps1IconUrl(icon, frame) {
  const key = `${frame}:${icon.pal.join()}:${icon.px.slice(frame * 256, frame * 256 + 256)}`;
  let url = iconCache.get(key);
  if (url) return url;
  const c = document.createElement("canvas");
  c.width = c.height = 16;
  const ctx = c.getContext("2d");
  const img = ctx.createImageData(16, 16);
  const pal = icon.pal.map((h) => (h ? [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16)) : null));
  for (let i = 0; i < 256; i++) {
    const byte = parseInt(icon.px.substr((frame * 128 + (i >> 1)) * 2, 2), 16);
    const col = pal[i & 1 ? byte >> 4 : byte & 15];
    if (col) img.data.set([col[0], col[1], col[2], 255], i * 4);
  }
  ctx.putImageData(img, 0, 0);
  url = c.toDataURL();
  if (iconCache.size > 600) iconCache.clear();
  iconCache.set(key, url);
  return url;
}

function ps1IconHtml(e, cls = "ps1-icon") {
  if (!e.icon || !e.icon.px) return `<span class="${cls} none">${svg("save")}</span>`;
  const frames = Array.from({ length: e.icon.n }, (_, i) => ps1IconUrl(e.icon, i));
  return `<img class="${cls}" alt="" draggable="false" src="${frames[0]}"${frames.length > 1 ? ` data-frames="${frames.join(" ")}"` : ""}>`;
}

let iconTick = 0;
const reduceMotion = window.matchMedia?.("(prefers-reduced-motion: reduce)");
setInterval(() => {
  if (reduceMotion?.matches || document.hidden) return;
  iconTick++;
  document.querySelectorAll("img[data-frames]").forEach((img) => {
    const f = img.dataset.frames.split(" ");
    img.src = f[iconTick % f.length];
  });
}, 280);

// ---------------------------------------------------------------------------
// PS2 save icons: 3D models read on demand after the tree is shown (the card
// opens just as fast). Rows get a still thumbnail; the details panel the
// animated model on the icon.sys background. Saves without an icon (no
// icon.sys, missing or broken icon file) keep the generic save symbol.

const ps2Icons = {
  data: new Map(), // key -> {icon, look} | null (no usable icon)
  thumbs: new Map(), // key -> data URL | null
  pending: new Set(), // keys being fetched
  thumbR: undefined, // shared off-screen renderer; null = no WebGL
};
const THUMB_PX = 48;
// same save content -> same key, also across the two panes and after undo
const iconKey = (e) => `${e.path}|${e.modified}|${e.size}|${e.files}`;
const hasPs2Icon = (p, e) => e.dir && !!e.title && p.parentOf.get(e.path) === "/";

function ps2IconRecord(raw) {
  if (!raw) return null;
  try {
    const bin = atob(raw.data);
    const u8 = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) u8[i] = bin.charCodeAt(i);
    return { icon: parseIcon(u8), look: raw };
  } catch {
    return null;
  }
}

function thumbRenderer() {
  if (ps2Icons.thumbR === undefined) {
    try {
      const c = document.createElement("canvas");
      c.width = c.height = THUMB_PX;
      ps2Icons.thumbR = new IconRenderer(c);
    } catch {
      ps2Icons.thumbR = null;
    }
  }
  return ps2Icons.thumbR;
}

function makeThumb(key) {
  const rec = ps2Icons.data.get(key);
  const r = rec && thumbRenderer();
  let url = null;
  if (r) {
    try {
      r.setIcon(rec.icon, rec.look);
      if (r.draw({ yaw: -0.35, pitch: 0.12 })) url = r.canvas.toDataURL();
    } catch { url = null; }
  }
  if (ps2Icons.thumbs.size > 800) ps2Icons.thumbs.clear();
  ps2Icons.thumbs.set(key, url);
  return url;
}

function ps2RowIcon(p, e) {
  const url = hasPs2Icon(p, e) ? ps2Icons.thumbs.get(iconKey(e)) : null;
  if (url) return `<span class="ricon ps2"><img class="ps2-icon" alt="" draggable="false" src="${url}"></span>`;
  const icon = e.dir ? (e.title ? "save" : "folder") : "file";
  return `<span class="ricon${icon === "save" ? " save" : ""}">${svg(icon)}</span>`;
}

// fetches the icons of the given entries (in small batches, so other actions are not held up)
async function fetchPs2Icons(p, entries) {
  const todo = entries.filter((e) => !ps2Icons.data.has(iconKey(e)) && !ps2Icons.pending.has(iconKey(e)));
  if (!todo.length) return;
  todo.forEach((e) => ps2Icons.pending.add(iconKey(e)));
  const summary = p.summary;
  try {
    for (let i = 0; i < todo.length; i += 8) {
      const chunk = todo.slice(i, i + 8);
      if (p.summary !== summary) break;
      const r = ok(await rpc("icons", [p.slot, chunk.map((e) => e.path)]));
      for (const e of chunk) {
        const key = iconKey(e);
        ps2Icons.data.set(key, ps2IconRecord(r.icons[e.path]));
        ps2Icons.pending.delete(key);
        const url = makeThumb(key);
        if (url && p.summary === summary) {
          const span = p.tree.querySelector(`.row[data-path="${CSS.escape(e.path)}"] .ricon`);
          if (span) span.outerHTML = ps2RowIcon(p, e);
        }
        if (P() === p && !state.dual && p.selected.size === 1 && p.selected.has(e.path)) mountPs2View(p, e);
        await new Promise((r) => setTimeout(r, 0)); // let clicks and scrolling through between icons
      }
    }
  } catch { /* card closed or replaced meanwhile: the next render asks again */ }
  todo.forEach((e) => ps2Icons.pending.delete(iconKey(e)));
}

function queuePs2Icons(p) {
  if (!p.summary || isPs1(p)) return;
  // first time: check for WebGL after the tree is on screen; without a GPU, no icons at all
  if (ps2Icons.thumbR === undefined) {
    if (!ps2Icons.probe) ps2Icons.probe = setTimeout(() => { thumbRenderer(); for (const q of Object.values(panes)) queuePs2Icons(q); }, 30);
    return;
  }
  if (!ps2Icons.thumbR) return;
  const list = p.summary.tree.filter((e) => hasPs2Icon(p, e));
  for (const e of list) {
    const key = iconKey(e);
    if (ps2Icons.data.has(key) && !ps2Icons.thumbs.has(key)) makeThumb(key);
  }
  fetchPs2Icons(p, list);
}

// details panel: one persistent WebGL canvas, animated and draggable
const ps2View = { canvas: null, r: null, key: null, start: 0, yaw: 0, pitch: 0.1, drag: null, raf: 0, spin: true };

function ps2ViewInit() {
  if (ps2View.r !== null || ps2View.canvas) return ps2View.r;
  const c = document.createElement("canvas");
  c.className = "ps2-view";
  ps2View.canvas = c;
  try { ps2View.r = new IconRenderer(c); } catch { ps2View.r = null; return null; }
  c.addEventListener("pointerdown", (ev) => {
    ps2View.drag = { x: ev.clientX, y: ev.clientY, yaw: ps2View.yaw, pitch: ps2View.pitch };
    ps2View.spin = false;
    c.setPointerCapture(ev.pointerId);
  });
  c.addEventListener("pointermove", (ev) => {
    const d = ps2View.drag;
    if (!d) return;
    ps2View.yaw = d.yaw + (ev.clientX - d.x) / 60;
    ps2View.pitch = Math.max(-1.2, Math.min(1.2, d.pitch + (ev.clientY - d.y) / 60));
    ps2ViewFrame();
  });
  const end = () => { ps2View.drag = null; };
  c.addEventListener("pointerup", end);
  c.addEventListener("pointercancel", end);
  c.addEventListener("dblclick", () => { ps2View.yaw = 0; ps2View.pitch = 0.1; ps2View.spin = true; ps2ViewLoop(); });
  return ps2View.r;
}

function ps2ViewFrame(now = performance.now()) {
  const r = ps2View.r;
  if (!r || !ps2View.canvas.isConnected) return false;
  const size = Math.round(ps2View.canvas.clientWidth * (window.devicePixelRatio || 1)) || 320;
  if (ps2View.canvas.width !== size) ps2View.canvas.width = ps2View.canvas.height = size;
  return r.draw({ time: (now - ps2View.start) / 1000, yaw: ps2View.yaw, pitch: ps2View.pitch, background: true });
}

function ps2ViewLoop() {
  cancelAnimationFrame(ps2View.raf);
  let last = performance.now();
  const tick = (now) => {
    if (!ps2View.canvas?.isConnected) return;
    const still = reduceMotion?.matches;
    if (!document.hidden) {
      if (ps2View.spin && !still) ps2View.yaw += ((now - last) / 1000) * 0.6;
      ps2ViewFrame(still ? ps2View.start : now);
    }
    last = now;
    const r = ps2View.r;
    if (!still && (ps2View.spin || (r?.icon && isAnimated(r.icon)))) ps2View.raf = requestAnimationFrame(tick);
  };
  ps2View.raf = requestAnimationFrame(tick);
}

// puts the 3D icon of ``e`` in the details panel (fetching it first if needed)
function mountPs2View(p, e) {
  const slot = document.querySelector("#details .ps2-slot");
  if (!slot || slot.dataset.path !== e.path) return;
  const key = iconKey(e);
  if (!ps2Icons.data.has(key)) { fetchPs2Icons(p, [e]); return; }
  const rec = ps2Icons.data.get(key);
  const r = rec && ps2ViewInit();
  if (!r) { slot.remove(); return; }
  if (ps2View.key !== key) {
    try { r.setIcon(rec.icon, rec.look); } catch { slot.remove(); return; }
    ps2View.key = key;
    ps2View.start = performance.now();
    ps2View.yaw = 0; ps2View.pitch = 0.1; ps2View.spin = true;
  }
  slot.replaceChildren(ps2View.canvas);
  slot.classList.add("ready");
  ps2ViewFrame();
  ps2ViewLoop();
}

// [7, 8, 10, 11, 12] -> "7–8, 10–12"
function blockRanges(blocks) {
  const out = [];
  for (let i = 0; i < blocks.length; i++) {
    let j = i;
    while (j + 1 < blocks.length && blocks[j + 1] === blocks[j] + 1) j++;
    out.push(j > i ? `${blocks[i]}–${blocks[j]}` : String(blocks[i]));
    i = j;
  }
  return out.join(", ");
}
const blocksLabel = (n) => (n === 1 ? t("unit.block") : t("unit.blocks", { n }));

// ---------------------------------------------------------------------------
// Worker (Pyodide)

const worker = new Worker(`worker.js?v=${BUILD}`);
let seq = 0;
const pending = new Map();
let loadStep = "load.preparing";
worker.onmessage = (ev) => {
  const m = ev.data;
  if (m.type === "progress") {
    loadStep = m.step;
    $("#engineText").textContent = t(m.step);
    if (!state.busy) status("st.loading", { step: t(m.step) });
    return;
  }
  const p = pending.get(m.id);
  if (!p) return;
  pending.delete(m.id);
  m.ok ? p.resolve(m.result) : p.reject(new Error(m.error));
};
worker.onerror = (e) => engineFailed(e.message || "worker");

function rpc(op, args = [], transfer = []) {
  return new Promise((resolve, reject) => {
    const id = ++seq;
    pending.set(id, { resolve, reject });
    worker.postMessage({ id, op, args }, transfer);
  });
}

// Resolves when Python is ready. The page can be used before that: actions
// started meanwhile wait for it (see run()), and the worker queues requests.
let engineReadyOk, engineReadyFail;
const engineReady = new Promise((resolve, reject) => { engineReadyOk = resolve; engineReadyFail = reject; });
engineReady.catch(() => {}); // handled where it is awaited

let engineError = null;
function engineFailed(msg) {
  engineError = msg;
  $("#engine").classList.add("error");
  $("#engineText").textContent = t("engine.error");
  $("#engine").title = t("engine.failed", { error: msg });
  status("engine.failed", { error: msg });
  engineReadyFail(new Error(t("engine.failed", { error: msg })));
}

// JSON result coming from Python
function ok(r) {
  if (r && r.ok) return r;
  const err = new Error(r?.error || t("toast.unknown"));
  err.kind = r?.kind;
  throw err;
}

// ---------------------------------------------------------------------------
// State: two panes (card slots "A" and "B")

const state = {
  sdCollapsed: storage.get("psmm-sd-collapsed", "0") === "1", // SD card list folded into a thin rail (more room for the cards)
  compare: false, // compare the two open cards (side-by-side view)
  cmpDiffOnly: false, // while comparing: hide the saves that are the same on both
  ready: false,
  python: "",
  busy: false,
  dual: false,
  active: "A",
  sort: { key: "name", desc: false },
};

const SLOTS = ["A", "B"];
const panes = {};
const otherSlot = (slot) => (slot === "A" ? "B" : "A");
const P = () => panes[state.active];

function makePane(slot) {
  const el = $("#paneTpl").content.firstElementChild.cloneNode(true);
  el.dataset.slot = slot;
  $("#panes").appendChild(el);
  const pane = {
    slot, el,
    tree: $(".tree", el),
    summary: null,
    byPath: new Map(),
    parentOf: new Map(),
    expanded: new Set(),
    selected: new Set(),
    focus: null,
    anchor: null,
    visible: [],
    fileHandle: null, // File System Access API (Chrome/Edge)
    sdPath: null, // path on the open SD card, if the card came from there
  };
  $(".close-card", el).innerHTML = svg("close");
  $(".filter-icon", el).innerHTML = svg("search");
  pane.filter = "";
  $(".cmp-bar", el).addEventListener("click", (ev) => {
    if (ev.target.closest('[data-cmp="copy"]')) actCompareCopy(pane);
  });
  $(".cmp-bar", el).addEventListener("change", (ev) => {
    if (ev.target.matches('[data-cmp="diff"]')) { state.cmpDiffOnly = ev.target.checked; render(); }
  });
  const input = $(".filter", el);
  input.addEventListener("input", () => { pane.filter = input.value; renderTree(pane); });
  input.addEventListener("keydown", (ev) => {
    if (ev.key === "Escape" && input.value) { ev.stopPropagation(); input.value = ""; pane.filter = ""; renderTree(pane); }
    else if (ev.key === "ArrowDown" || ev.key === "Enter") { ev.preventDefault(); pane.tree.focus(); if (pane.visible[0] && !pane.focus) select(pane, pane.visible[0].path); }
  });
  bindTree(pane);
  return pane;
}

// Search: every word must appear in the name, title, game code or game name (no accents, any case)
const fold = (s) => String(s || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
const filterWords = (p) => fold(p.filter).split(/\s+/).filter(Boolean);
function entryMatches(e, words) {
  const serial = e.serial || "";
  const hay = fold(`${e.name} ${e.title || ""} ${serial} ${serial.replace("-", "")} ${gameName(serial) || ""}`);
  return words.every((w) => hay.includes(w));
}

function resetPane(p) {
  p.filter = "";
  $(".filter", p.el).value = "";
  p.summary = null;
  p.fileHandle = null;
  p.sdPath = null;
  p.expanded.clear(); p.selected.clear();
  p.focus = p.anchor = null;
  p.byPath.clear(); p.parentOf.clear();
  p.visible = [];
}

function indexTree(p) {
  p.byPath.clear();
  p.parentOf.clear();
  const walk = (list, parent) => {
    for (const e of list) {
      p.byPath.set(e.path, e);
      p.parentOf.set(e.path, parent);
      if (e.children) walk(e.children, e.path);
    }
  };
  walk(p.summary.tree, "/");
  for (const x of [...p.expanded]) if (!p.byPath.has(x)) p.expanded.delete(x);
  for (const x of [...p.selected]) if (!p.byPath.has(x)) p.selected.delete(x);
  if (p.focus && !p.byPath.has(p.focus)) p.focus = null;
}

function applySummary(p, s) {
  p.summary = s;
  indexTree(p);
  render();
}

// Lightweight on purpose: called on mousedown, so it must not rebuild the trees
// (the click that follows would land on a detached row).
function setActive(slot) {
  if (state.active === slot) return;
  state.active = slot;
  for (const s of SLOTS) panes[s].el.classList.toggle("active", s === slot);
  const a = P();
  const dirtyAny = SLOTS.some((s) => panes[s].summary?.dirty);
  document.title = a.summary ? `${dirtyAny ? "● " : ""}${a.summary.card.name} — PSMemoryManager` : "PSMemoryManager";
  updateActions();
}

async function run(statusKey, params, fn) {
  if (state.busy) return;
  state.busy = true;
  document.body.style.cursor = "progress";
  updateActions();
  try {
    if (!state.ready) {
      // started before Python finished loading: it carries on by itself when it is ready
      status("st.waitEngine", { step: t(loadStep) });
      await engineReady;
    }
    status(statusKey, params);
    return await fn();
  } catch (e) {
    toast(e.message || String(e), "error");
    status("st.error");
  } finally {
    state.busy = false;
    document.body.style.cursor = "";
    updateActions();
    if (sd) renderSd(); // its buttons are disabled while busy
  }
}

// ---------------------------------------------------------------------------
// Rendering

function sortedChildren(list) {
  const { key, desc } = state.sort;
  const val = (e) => key === "size" ? e.size : key === "modified" ? (e.ps1 ? e.block : e.modified || "") : key === "title" ? (e.title || "").toLowerCase() : e.name.toLowerCase();
  return [...list].sort((a, b) => {
    if (a.dir !== b.dir) return a.dir ? -1 : 1;
    const x = val(a), y = val(b);
    const c = x < y ? -1 : x > y ? 1 : a.name.localeCompare(b.name);
    return desc ? -c : c;
  });
}

function render() {
  const a = P();
  const showEmpty = !state.dual && !a.summary && !sd;
  $("#empty").hidden = !showEmpty;
  $("#workspace").hidden = showEmpty;
  $("#layout").classList.toggle("dual", state.dual);
  $("#layout").classList.toggle("has-sd", !!sd);
  $("#layout").classList.toggle("sd-collapsed", !!sd && state.sdCollapsed);
  $("#sdbar").hidden = !sd;
  renderSd();
  document.querySelector('.toolbar [data-act="dual"]').setAttribute("aria-pressed", String(state.dual));
  document.querySelector('.toolbar [data-act="compare"]').setAttribute("aria-pressed", String(comparing()));

  const dirtyAny = SLOTS.some((s) => panes[s].summary?.dirty);
  document.title = a.summary ? `${dirtyAny ? "● " : ""}${a.summary.card.name} — PSMemoryManager` : "PSMemoryManager";

  for (const slot of SLOTS) renderPane(panes[slot]);
  if (!state.dual && a.summary) renderDetails(a);
  updateActions();
}

function renderPane(p) {
  const visible = state.dual || p.slot === state.active;
  p.el.hidden = !visible;
  p.el.classList.toggle("active", p.slot === state.active);
  if (!visible) return;
  const has = !!p.summary;
  $(".cardbar", p.el).hidden = !has;
  $(".tree-wrap", p.el).hidden = !has;
  $(".pane-empty", p.el).hidden = has;
  if (!has) {
    $(".cmp-bar", p.el).hidden = true;
    // empty pane: in single view with an SD card open, point to the SD list
    const fromSd = !!sd && !state.dual;
    $(".pane-empty h2", p.el).textContent = t(fromSd ? "pane.sdTitle" : "pane.emptyTitle");
    $(".pane-empty p", p.el).textContent = t(fromSd ? "pane.sdText" : "pane.emptyText");
    return;
  }

  const s = p.summary, c = s.card;
  $(".slot-badge", p.el).textContent = p.slot;
  $(".card-name", p.el).textContent = c.name;
  const dirty = $(".dirty", p.el);
  dirty.hidden = !s.dirty;
  dirty.textContent = t("card.unsaved");
  dirty.title = t("card.unsaved.tip");
  const close = $(".close-card", p.el);
  close.title = t("pane.close");
  close.setAttribute("aria-label", t("pane.close"));
  const ps1 = c.platform === "PS1";
  const chips = ps1 ? [
    `<span class="chip accent">PS1</span>`,
    `<span class="chip">${esc(t("chip.blocks"))}</span>`,
    `<span class="chip">${esc(c.origin)}</span>`,
  ] : [
    `<span class="chip accent">${esc(c.platform)}</span>`,
    `<span class="chip">${c.sizeMB} MB</span>`,
    `<span class="chip">${esc(t(c.ecc ? "chip.ecc" : "chip.noecc"))}</span>`,
    `<span class="chip">${esc(c.origin)}</span>`,
  ];
  if (ps1 && c.container === "vmp") chips.push(c.signed === false ? `<span class="chip warn">${esc(t("chip.unsigned"))}</span>` : `<span class="chip">${esc(t("chip.signed"))}</span>`);
  if (c.readOnly) chips.push(`<span class="chip warn" title="${esc(t("chip.readOnlyTip"))}">${esc(t(c.freepsxboot ? "chip.freepsxboot" : "chip.readOnly"))}</span>`);
  if (c.sizeMismatch) chips.push(`<span class="chip warn">${esc(t("chip.mismatch"))}</span>`);
  if (p.sdPath) {
    const parts = p.sdPath.split("/"); // MemoryCards/PS2/BOOT/BootCard-1.mcd
    chips.push(`<span class="chip accent" title="${esc(p.sdPath)}">${esc(t("chip.sd", { where: `${parts[1]}/${parts[2]}` }))}</span>`);
  }
  $(".chips", p.el).innerHTML = chips.join("");
  const pct = c.total ? Math.min(100, (c.used / c.total) * 100) : 0;
  const fill = $(".bar-fill", p.el);
  fill.style.width = pct.toFixed(1) + "%";
  fill.className = "bar-fill" + (pct > 95 ? " full" : pct > 80 ? " warn" : "");
  $(".bar", p.el).hidden = ps1;
  $(".blockmap", p.el).hidden = !ps1;
  if (ps1) {
    $(".used", p.el).textContent = t("card.blocksUsed", { used: c.blocksUsed, total: c.blocksTotal });
    $(".free", p.el).textContent = t("card.blocksFree", { free: c.blocksFree });
    renderBlockMap(p);
  } else {
    $(".used", p.el).textContent = t("card.used", { used: human(c.used) });
    $(".free", p.el).textContent = t("card.free", { free: human(c.free), total: human(c.total) });
  }
  $(".tree-head .col-size", p.el).textContent = t(ps1 ? "col.blocks" : "col.size");
  $(".tree-head .col-date", p.el).textContent = t(ps1 ? "col.where" : "col.modified");

  p.el.querySelectorAll(".tree-head button").forEach((b) => {
    b.classList.toggle("sorted", b.dataset.sort === state.sort.key);
    b.classList.toggle("desc", b.dataset.sort === state.sort.key && state.sort.desc);
  });
  renderCompareBar(p);
  renderTree(p);
}

// PS1: the 15 blocks of the card, coloured by save (click selects the save)
function renderBlockMap(p) {
  const owner = new Map();
  const live = p.summary.tree.filter((e) => !e.deleted);
  for (const e of p.summary.tree) for (const b of e.blocks) if (!e.deleted || !owner.has(b)) owner.set(b, e);
  for (const e of live) for (const b of e.blocks) owner.set(b, e);
  const cells = [];
  for (let b = 1; b <= 15; b++) {
    const e = owner.get(b);
    const state = p.summary.card.blockStates[b - 1];
    // in use but no save reaches it (FreePSXBoot, damaged directory): not free
    const odd = !e && state !== 0xA0 && !(state >= 0xA1 && state <= 0xA3);
    const free = !e || e.deleted;
    const hue = e && !e.deleted ? live.indexOf(e) % 6 : 0;
    const tip = odd ? t("block.odd", { n: b }) : !e ? t("block.free", { n: b }) : e.deleted ? t("block.deleted", { n: b, name: e.title || e.name }) : t("block.used", { n: b, name: e.title || e.name });
    const sel = e && p.selected.has(e.path) ? " sel" : "";
    const kind = odd ? " odd" : free ? (e ? " del" : " free") : ` h${hue}`;
    cells.push(`<span class="blk${kind}${sel}" title="${esc(tip)}"${e ? ` data-path="${esc(e.path)}"` : ""}>${b}</span>`);
  }
  $(".blockmap", p.el).innerHTML = cells.join("");
}

function renderPs1Row(p, e, cmpSt = null) {
  const cls = ["row", "ps1row"];
  if (p.selected.has(e.path)) cls.push("selected");
  if (p.focus === e.path) cls.push("focused");
  if (e.deleted) cls.push("deleted");
  const tags =
    (e.deleted ? `<span class="tag del" title="${esc(t(e.restorable ? "tree.deletedTip" : "tree.goneTip"))}">${esc(t("tree.deleted"))}</span>` : "") +
    (e.pocketstation ? `<span class="tag">PocketStation</span>` : "") +
    (e.exploit ? `<span class="tag">${esc(t("tree.exploit"))}</span>` : "") +
    (e.problems.length && !e.deleted ? `<span class="lock" title="${esc(t("tree.problems"))}">${svg("warn")}</span>` : "") +
    cmpBadge(cmpSt, "in-name");
  return `<div class="${cls.join(" ")}" role="treeitem" draggable="${!e.deleted}" aria-level="1" aria-selected="${p.selected.has(e.path)}" data-path="${esc(e.path)}">` +
    `<div class="c-name" style="padding-left:8px"><span class="ricon ps1">${ps1IconHtml(e)}</span>` +
    `<span class="nm" title="${esc(e.name)}">${esc(e.name)}</span>${tags}</div>` +
    `<div class="c-title" title="${esc(e.title)}">${cmpBadge(cmpSt)}${esc(e.title)}</div>` +
    `<div class="c-size">${esc(blocksLabel(e.blocks.length))}</div>` +
    `<div class="c-date">${esc(blockRanges(e.blocks))}</div></div>`;
}

// ---------------------------------------------------------------------------
// Compare the two open cards: what each save at the root looks like on the other
// card. PS2 saves are matched by folder name and told apart by date and size;
// PS1 saves have no dates, so they are only "here only" or "on both".

const canCompare = () => state.dual && !!panes.A.summary && !!panes.B.summary &&
  panes.A.summary.card.platform === panes.B.summary.card.platform;
const comparing = () => state.compare && canCompare();

function compareStatus(p) {
  if (!comparing()) return null;
  const other = panes[otherSlot(p.slot)];
  const live = (list) => list.filter((e) => !e.deleted);
  const theirs = new Map(live(other.summary.tree).map((e) => [e.name, e]));
  const out = new Map();
  for (const e of live(p.summary.tree)) {
    const o = theirs.get(e.name);
    let st;
    if (!o) st = "only";
    else if (isPs1(p)) st = "both";
    else {
      const a = e.modified ? Date.parse(e.modified) : 0, b = o.modified ? Date.parse(o.modified) : 0;
      if (a > b) st = "newer";
      else if (a < b) st = "older";
      else st = e.size === o.size && e.files === o.files ? "same" : "diff";
    }
    out.set(e.path, st);
  }
  return out;
}

// only differences get a badge: the saves that match are counted in the bar
// in-name copy: shown instead when the pane is too narrow for the title column
const cmpBadge = (st, where = "") => (st && st !== "same" && st !== "both"
  ? `<span class="cmp cmp-${st}${where ? " " + where : ""}" title="${esc(t(`cmp.${st}Tip`))}">${esc(t(`cmp.${st}`))}</span>` : "");

function renderCompareBar(p) {
  const bar = $(".cmp-bar", p.el);
  const cmp = compareStatus(p);
  bar.hidden = !cmp;
  if (!cmp) { bar.innerHTML = ""; return; }
  const other = otherSlot(p.slot);
  const n = { only: 0, newer: 0, older: 0, diff: 0, same: 0, both: 0 };
  for (const st of cmp.values()) n[st]++;
  const parts = ["only", "newer", "older", "diff", "same", "both"].filter((k) => n[k]).map((k) => t(`cmp.count.${k}${n[k] === 1 ? "1" : ""}`, { n: n[k] }));
  const toCopy = n.only + n.newer;
  const ro = panes[other].summary.card.readOnly;
  bar.innerHTML =
    `<span class="cmp-sum">${esc(t("cmp.with", { slot: other }))} ${esc(parts.join(" · ") || t("cmp.empty"))}</span>` +
    `<label class="inline"><input type="checkbox" data-cmp="diff"${state.cmpDiffOnly ? " checked" : ""}> ${esc(t("cmp.diffOnly"))}</label>` +
    (toCopy ? `<button class="btn small" data-cmp="copy" ${ro ? "disabled" : ""} title="${esc(t("cmp.copyTip", { slot: other }))}">` +
      `${svg("copy")}${esc(t("cmp.copy", { n: toCopy, slot: other }))}</button>` : "");
}

async function actCompareCopy(p) {
  const cmp = compareStatus(p);
  if (!cmp) return;
  const other = otherSlot(p.slot);
  const only = [...cmp].filter(([, st]) => st === "only").map(([path]) => path);
  const newer = [...cmp].filter(([, st]) => st === "newer").map(([path]) => path);
  if (!only.length && !newer.length) return;
  const yes = await openDialog(
    `<h3>${esc(t("cmp.copyTitle", { slot: other }))}</h3>` +
    `<div class="msg">${esc(t("cmp.copyMsg", { slot: other, what: [
      only.length ? t(only.length === 1 ? "cmp.copyOnly1" : "cmp.copyOnly", { n: only.length, slot: other }) : "",
      newer.length ? t(newer.length === 1 ? "cmp.copyNewer1" : "cmp.copyNewer", { n: newer.length }) : "",
    ].filter(Boolean).join(t("cmp.and")) }))}</div>` +
    (newer.length ? `<div class="warnbox">${esc(t("cmp.copyReplace", { n: newer.length, slot: other }))}</div>` : "") +
    actionsHtml(t("cmp.copyGo")),
    () => true,
  );
  if (!yes || state.busy) return;
  const paths = [...only, ...newer];
  await run("st.copying", { slot: other }, async () => {
    const r = ok(await rpc("copy", [p.slot, paths, other, "/", newer.length > 0]));
    applySummary(panes[other], r);
    toast(t("toast.copied", { n: paths.length, slot: other }), "ok");
    status("st.copied", { slot: other });
  });
}

function renderTree(p) {
  const rows = [];
  p.visible = [];
  const words = filterWords(p);
  if (words.length && !gameDb) loadGameDb();
  const empty = (key) => `<div class="tree-empty">${esc(words.length ? t("filter.none", { q: p.filter.trim() }) : t(key))}</div>`;
  const cmp = compareStatus(p);
  const hideSame = (e) => cmp && state.cmpDiffOnly && ["same", "both"].includes(cmp.get(e.path));
  if (isPs1(p)) {
    for (const e of sortedChildren(p.summary.tree)) {
      if (words.length && !entryMatches(e, words)) continue;
      if (hideSame(e) || (cmp && state.cmpDiffOnly && e.deleted)) continue;
      p.visible.push(e);
      rows.push(renderPs1Row(p, e, cmp?.get(e.path)));
    }
    p.tree.innerHTML = rows.length ? rows.join("") : empty("tree.emptyPs1");
    renderBlockMap(p);
    return;
  }
  // with a search: a folder that matches shows all it has; one that only holds
  // matches is opened to show them
  const keep = (e) => entryMatches(e, words) || (e.children || []).some(keep);
  const walk = (list, depth, filtering) => {
    for (const e of sortedChildren(list)) {
      const self = !filtering || entryMatches(e, words);
      if (!self && !keep(e)) continue;
      if (depth === 0 && hideSame(e)) continue;
      p.visible.push(e);
      const open = p.expanded.has(e.path) || !self;
      const hasKids = e.dir && e.children && e.children.length > 0;
      const cls = ["row"];
      if (p.selected.has(e.path)) cls.push("selected");
      if (p.focus === e.path) cls.push("focused");
      rows.push(
        `<div class="${cls.join(" ")}" role="treeitem" draggable="true" aria-level="${depth + 1}" aria-selected="${p.selected.has(e.path)}"` +
        `${e.dir ? ` aria-expanded="${open}"` : ""} data-path="${esc(e.path)}">` +
        `<div class="c-name" style="padding-left:${8 + depth * 20}px">` +
        `<span class="twisty${open ? " open" : ""}${hasKids ? "" : " leaf"}" data-twisty>${svg("chevron")}</span>` +
        ps2RowIcon(p, e) +
        `<span class="nm" title="${esc(e.name)}">${esc(e.name)}</span>` +
        `${e.protected ? `<span class="lock" title="${esc(t("tree.protected"))}">${svg("lock")}</span>` : ""}` +
        (depth === 0 ? cmpBadge(cmp?.get(e.path), "in-name") : "") +
        `</div>` +
        `<div class="c-title" title="${esc(e.title)}">${depth === 0 ? cmpBadge(cmp?.get(e.path)) : ""}${esc(e.title)}</div>` +
        `<div class="c-size">${human(e.size)}</div>` +
        `<div class="c-date">${fmtDate(e.modified)}</div>` +
        `</div>`
      );
      if (e.dir && open && e.children) walk(e.children, depth + 1, !self);
    }
  };
  walk(p.summary.tree, 0, words.length > 0);
  p.tree.innerHTML = rows.length ? rows.join("") : cmp && state.cmpDiffOnly && !words.length ? `<div class="tree-empty">${esc(t("cmp.noDiff"))}</div>` : empty("tree.empty");
  queuePs2Icons(p);
}

function dl(rows) {
  return `<dl>${rows.map(([k, v]) => `<dt>${esc(k)}</dt><dd>${esc(v)}</dd>`).join("")}</dl>`;
}

function renderPs1Details(p, el, sel) {
  const c = p.summary.card;
  const tree = p.summary.tree;
  if (sel.length === 0) {
    const deleted = tree.filter((e) => e.deleted);
    const rows = [
      [t("det.ps1.saves"), String(tree.length - deleted.length)],
      [t("det.ps1.blocks"), t("det.ps1.blocksValue", { used: c.blocksUsed, free: c.blocksFree })],
    ];
    if (deleted.length) rows.push([t("det.ps1.deleted"), t("det.ps1.deletedValue", { n: deleted.length, r: deleted.filter((e) => e.restorable).length })]);
    if (c.container === "vmp") rows.push([t("det.ps1.signature"), t(c.signed === false ? "det.ps1.sigBad" : "det.ps1.sigOk")]);
    rows.push([t("det.file"), human(c.fileSize)]);
    el.innerHTML = `<h2>${esc(c.name)}</h2><div class="path">${esc(c.describe)}</div>` + dl(rows) +
      (c.readOnly ? `<div class="${c.freepsxboot ? "notebox" : "warnbox"}">${esc(t(c.freepsxboot ? "det.ps1.freepsxboot" : "det.ps1.readOnly"))}</div>` : "") +
      `<p class="hint">${esc(t("det.ps1.hint"))}</p>`;
    return;
  }
  if (sel.length > 1) {
    const blocks = sel.reduce((a, e) => a + e.blocks.length, 0);
    el.innerHTML = `<h2>${esc(t("det.ps1.multi", { n: sel.length }))}</h2>` + dl([[t("det.total"), t("det.ps1.multiBlocks", { n: blocks })]]);
    return;
  }
  const e = sel[0];
  const rows = [];
  if (e.serial) {
    const game = gameName(e.serial);
    if (game) rows.push([t("det.game"), game]);
    rows.push([t("det.serial"), e.serial]);
    if (e.region) rows.push([t("det.region"), e.region]);
  }
  rows.push([t("det.ps1.saveName"), e.name]);
  rows.push([t("det.type"), t(e.exploit ? "det.ps1.exploitType" : e.pocketstation ? "det.ps1.pocket" : "det.type.ps1save")]);
  rows.push([t("det.size"), `${blocksLabel(e.blocks.length)} (${human(e.size)})`]);
  rows.push([t("det.ps1.blockList"), blockRanges(e.blocks)]);
  if (e.icon) rows.push([t("det.ps1.iconFrames"), t("det.ps1.iconValue", { n: e.icon.n })]);
  rows.push([t("det.ps1.status"), t(!e.deleted ? "det.ps1.statusLive" : e.restorable ? "det.ps1.statusDeleted" : "det.ps1.statusGone")]);
  if (e.comment) rows.push([t("det.ps1.comment"), e.comment]);
  el.innerHTML =
    `<div class="ps1-head">${ps1IconHtml(e, "ps1-big")}<h2>${esc(e.title || e.name)}</h2></div>` + dl(rows) +
    (e.exploit ? `<div class="notebox">${esc(t("det.ps1.exploitNote"))}</div>` : "") +
    (e.problems.length ? `<div class="warnbox">${e.problems.map(esc).join("<br>")}</div>` : "") +
    (e.deleted && e.restorable && !c.readOnly ? `<div class="det-actions"><button class="btn" data-act="restore">${esc(t("act.restore"))}</button></div>` : "");
}

function renderDetails(p) {
  const el = $("#details");
  const sel = [...p.selected].map((x) => p.byPath.get(x)).filter(Boolean);
  const c = p.summary.card;
  if (c.platform === "PS1") return renderPs1Details(p, el, sel);
  if (sel.length === 0) {
    el.innerHTML =
      `<h2>${esc(c.name)}</h2><div class="path">${esc(c.describe)}</div>` +
      dl([
        [t("det.rootDirs"), p.summary.tree.filter((e) => e.dir).length],
        [t("det.rootFiles"), p.summary.tree.filter((e) => !e.dir).length],
        [t("det.used"), human(c.used)],
        [t("det.free"), human(c.free)],
        [t("det.file"), human(c.fileSize)],
      ]) +
      `<p class="hint">${esc(t("det.hint"))}</p>`;
    return;
  }
  if (sel.length > 1) {
    const total = sel.reduce((acc, e) => acc + e.size, 0);
    el.innerHTML = `<h2>${esc(t("det.multi", { n: sel.length }))}</h2>` + dl([[t("det.total"), human(total)]]) +
      `<p class="hint">${esc(t("det.multiHint"))}</p>`;
    return;
  }
  const e = sel[0];
  const rows = [];
  if (e.serial) {
    const game = gameName(e.serial);
    if (game) rows.push([t("det.game"), game]);
    else if (!gameDb) loadGameDb();
    rows.push([t("det.serial"), e.serial], [t("det.region"), e.region]);
  }
  rows.push([t("det.type"), t(e.dir ? (e.title ? "det.type.save" : "det.type.dir") : "det.type.file")]);
  rows.push([t("det.size"), e.dir ? t("det.onCard", { size: human(e.size) }) : t("det.bytes", { size: human(e.size), bytes: fmtInt(e.size) })]);
  if (e.dir) rows.push([t("det.files"), String(e.files)]);
  rows.push([t("det.created"), fmtDate(e.created)], [t("det.modified"), fmtDate(e.modified)]);
  if (e.attrs) rows.push([t("det.attrs"), e.attrs]);
  const view = ps2Icons.thumbR && hasPs2Icon(p, e) && ps2Icons.data.get(iconKey(e)) !== null;
  el.innerHTML =
    (view ? `<div class="ps2-slot" data-path="${esc(e.path)}" title="${esc(t("det.ps2.iconTip"))}"></div>` : "") +
    `<h2>${esc(e.title || e.name)}</h2><div class="path">${esc(e.path)}</div>` + dl(rows) +
    (e.protected ? `<div class="warnbox">${esc(t("det.protectedWarn"))}</div>` : "");
  if (view) mountPs2View(p, e);
}

// selected root-level folders that only contain files (= exportable saves); PS1: the selected saves not deleted
function selectedSaves(p) {
  const sel = [...p.selected].map((x) => p.byPath.get(x)).filter(Boolean);
  if (isPs1(p)) return sel.length && sel.every((e) => !e.deleted && !e.exploit) ? sel.map((e) => e.path) : [];
  if (!sel.length || !sel.every((e) => e.dir && e.flat && p.parentOf.get(e.path) === "/")) return [];
  return sel.map((e) => e.path);
}

const canCopy = (p) => state.dual && !!p.summary && !!panes[otherSlot(p.slot)].summary && p.selected.size > 0 &&
  !panes[otherSlot(p.slot)].summary.card.readOnly;
// PS1: selected deleted saves that can be brought back
const selectedRestorable = (p) => (isPs1(p) && !p.summary.card.readOnly
  ? [...p.selected].map((x) => p.byPath.get(x)).filter((e) => e && e.deleted && e.restorable).map((e) => e.path) : []);

function updateActions() {
  const p = P();
  const has = !!p.summary;
  const sel = p.selected.size;
  const ps1 = isPs1(p);
  const ro = has && p.summary.card.readOnly;
  const en = {
    open: true, new: true,
    save: has && p.summary.dirty, saveAs: has, undo: has && p.summary.canUndo,
    addFiles: has && !ps1, addFolder: has && !ps1, mkdir: has && !ps1,
    extract: has && !ps1, rename: has && !ps1 && sel === 1,
    delete: has && sel > 0 && !ro && (!ps1 || selectedSaves(p).length > 0), check: has,
    importSave: !ro, exportSave: has && selectedSaves(p).length > 0,
    dual: true, compare: canCompare(), copy: canCopy(p), sd: true, convert: has, split: has && !ro, resize: has && !ps1,
    restore: has && selectedRestorable(p).length > 0,
  };
  document.querySelectorAll("[data-act]").forEach((b) => {
    const k = b.dataset.act;
    if (k in en) b.disabled = state.busy || !en[k];
  });
}

// ---------------------------------------------------------------------------
// Selection and navigation

function select(p, path, { toggle = false, range = false } = {}) {
  if (range && p.anchor) {
    const paths = p.visible.map((e) => e.path);
    const a = paths.indexOf(p.anchor), b = paths.indexOf(path);
    if (a >= 0 && b >= 0) {
      if (!toggle) p.selected.clear();
      for (let i = Math.min(a, b); i <= Math.max(a, b); i++) p.selected.add(paths[i]);
    }
  } else if (toggle) {
    p.selected.has(path) ? p.selected.delete(path) : p.selected.add(path);
    p.anchor = path;
  } else {
    p.selected = new Set([path]);
    p.anchor = path;
  }
  p.focus = path;
  refreshSelection(p);
  p.tree.querySelector(`.row[data-path="${CSS.escape(path)}"]`)?.scrollIntoView({ block: "nearest" });
}

function refreshSelection(p) {
  renderTree(p);
  if (!state.dual && p.slot === state.active) renderDetails(p);
  updateActions();
}

function clearSelection(p) {
  p.selected.clear();
  refreshSelection(p);
}

function toggleExpand(p, path, open) {
  const e = p.byPath.get(path);
  if (!e || !e.dir) return;
  if (open === undefined) open = !p.expanded.has(path);
  open ? p.expanded.add(path) : p.expanded.delete(path);
  renderTree(p);
}

function targetDir(p) {
  // where to add: selected folder, the selected file's folder, or root
  if (p.selected.size !== 1) return "/";
  const e = p.byPath.get([...p.selected][0]);
  if (!e) return "/";
  return e.dir ? e.path : p.parentOf.get(e.path) || "/";
}

// ---------------------------------------------------------------------------
// Dialogs

const dialog = $("#dialog");
const dform = $("#dialogForm");

function openDialog(html, onSubmit) {
  return new Promise((resolve) => {
    dform.innerHTML = html;
    paintIcons(dform);
    const done = (v) => { dialog.close(); resolve(v); };
    dform.onsubmit = (ev) => {
      ev.preventDefault();
      const btn = ev.submitter?.value;
      if (btn === "cancel") return done(null);
      const res = onSubmit ? onSubmit(dform, btn) : btn;
      if (res === false) return; // validation failed
      done(res);
    };
    dialog.oncancel = (ev) => { ev.preventDefault(); done(null); };
    dialog.showModal();
    const first = dform.querySelector("input[type=text], select");
    (first || dform.querySelector("button[value='ok']"))?.focus();
    if (first && first.select) first.select();
  });
}

const actionsHtml = (okLabel, okClass = "primary") =>
  `<div class="actions"><button class="btn" value="cancel">${esc(t("dlg.cancel"))}</button>` +
  `<button class="btn ${okClass}" value="ok">${esc(okLabel)}</button></div>`;

function confirmDialog(title, msg, okLabel, danger = false) {
  return openDialog(
    `<h3>${esc(title)}</h3><div class="msg">${esc(msg)}</div>` + actionsHtml(okLabel, danger ? "danger" : "primary"),
    () => true,
  ).then((v) => v === true);
}

function alertDialog(title, msg) {
  return openDialog(
    `<h3>${esc(title)}</h3><div class="msg">${esc(msg)}</div><div class="actions"><button class="btn primary" value="ok">${esc(t("dlg.ok"))}</button></div>`,
    () => true,
  );
}

const NAME_RE = /^[\x20-\x7e]+$/;
function validName(name) {
  if (!name || name === "." || name === "..") return t("name.empty");
  if (!NAME_RE.test(name)) return t("name.ascii");
  if (name.length > 32) return t("name.long");
  if (/[\/\\?*:"<>|]/.test(name)) return t("name.chars");
  return "";
}

function promptName(title, label, value = "") {
  return openDialog(
    `<h3>${esc(title)}</h3><label>${esc(label)}<input type="text" name="v" value="${esc(value)}" maxlength="32" autocomplete="off" spellcheck="false"></label>` +
    `<div class="err" id="dErr"></div>` + actionsHtml(t("dlg.ok")),
    (f) => {
      const v = f.v.value.trim();
      const err = validName(v);
      if (err) { f.querySelector("#dErr").textContent = err; return false; }
      return v;
    },
  );
}

const PS1_TARGETS = ["gen2", "mcr", "srm", "gme", "vmp", "vgs"];
const PS1_EXT = { gen2: ".mcd", mcr: ".mcr", srm: ".srm", gme: ".gme", vmp: ".vmp", vgs: ".vgs" };
const withExt = (name, ext) => name.replace(/\.[^.]*$/, "") + ext;

function newCardDialog() {
  const pr = openDialog(
    `<h3>${esc(t("dlg.new.title"))}</h3>` +
    `<label>${esc(t("dlg.new.console"))}<select name="console"><option value="PS2">PS2</option><option value="PS1">PS1</option></select></label>` +
    `<label>${esc(t("dlg.new.name"))}<input type="text" name="name" value="Card1-1.mcd" autocomplete="off" spellcheck="false"></label>` +
    `<div data-for="PS2"><label>${esc(t("dlg.new.size"))}<select name="size">` +
    [1, 2, 4, 8, 16, 32, 64].map((m) => `<option value="${m}"${m === 8 ? " selected" : ""}>${m} MB${m === 8 ? " " + esc(t("dlg.new.default")) : ""}</option>`).join("") +
    `</select></label>` +
    `<label class="inline"><input type="checkbox" name="ecc"> ${t("dlg.new.ecc")}</label>` +
    `<div class="msg small">${t("dlg.new.note")}</div></div>` +
    `<div data-for="PS1" hidden><label>${esc(t("dlg.new.format"))}<select name="fmt">` +
    PS1_TARGETS.map((x) => `<option value="${x}">${esc(t(`dlg.convert.ps1.${x}`))}</option>`).join("") + `</select></label>` +
    `<div class="msg small">${esc(t("dlg.new.ps1note"))}</div></div>` +
    `<div class="err" id="dErr"></div>` + actionsHtml(t("dlg.new.create")),
    (f) => {
      let name = f.name.value.trim();
      if (!name) { f.querySelector("#dErr").textContent = t("dlg.new.noName"); return false; }
      const platform = f.console.value;
      if (platform === "PS1") {
        if (!/\.[a-z0-9]+$/i.test(name)) name += PS1_EXT[f.fmt.value];
        return { platform, name, size: 0, ecc: false };
      }
      if (!/\.[a-z0-9]+$/i.test(name)) name += f.ecc.checked ? ".ps2" : ".mcd";
      return { platform, name, size: +f.size.value, ecc: f.ecc.checked };
    },
  );
  const sync = () => {
    const ps1 = dform.console.value === "PS1";
    dform.querySelectorAll("[data-for]").forEach((d) => { d.hidden = d.dataset.for !== (ps1 ? "PS1" : "PS2"); });
    dform.name.value = withExt(dform.name.value || "Card1-1", ps1 ? PS1_EXT[dform.fmt.value] : dform.ecc.checked ? ".ps2" : ".mcd");
  };
  dform.console.addEventListener("change", sync);
  dform.fmt.addEventListener("change", sync);
  dform.ecc.addEventListener("change", sync);
  return pr;
}

function exportFormatDialog(n, ps1 = false) {
  const formats = ps1 ? ["mcs", "psv"] : ["psu", "max"];
  const key = ps1 ? "psmm-export-format-ps1" : "psmm-export-format";
  const saved = storage.get(key, formats[0]);
  const last = formats.includes(saved) ? saved : formats[0];
  const opt = (v) =>
    `<label><input type="radio" name="fmt" value="${v}"${v === last ? " checked" : ""}><b>${esc(t(`dlg.export.${v}`))}</b><span>${esc(t(`dlg.export.${v}Hint`))}</span></label>`;
  return openDialog(
    `<h3>${esc(t("dlg.export.title"))}</h3><div class="msg">${esc(t("dlg.export.count", { n }))}</div>` +
    `<div class="choice">${formats.map(opt).join("")}</div>` +
    actionsHtml(t("dlg.export.go")),
    (f) => {
      const v = f.fmt.value;
      storage.set(key, v);
      return v;
    },
  );
}

// ---------------------------------------------------------------------------
// Actions (all act on a pane; toolbar actions use the active pane)

async function guardUnsaved(p) {
  if (!p.summary?.dirty) return true;
  return confirmDialog(t("dlg.unsaved.title"), t("dlg.unsaved.msg"), t("dlg.discard"), true);
}

async function openCardFile(p, file, handle = null, sdPath = null) {
  if (!(await guardUnsaved(p))) return;
  await run("st.opening", { name: file.name }, async () => {
    const buf = await file.arrayBuffer();
    const r = ok(await rpc("open", [p.slot, file.name, buf], [buf]));
    resetPane(p);
    p.fileHandle = handle;
    p.sdPath = sdPath;
    state.active = p.slot;
    applySummary(p, r);
    status("st.opened", { name: file.name });
  });
}

let pickTarget = "A"; // pane that receives the file chosen in a file input

async function actOpen(p = P()) {
  if (window.showOpenFilePicker) {
    try {
      const [handle] = await window.showOpenFilePicker({
        types: [{ description: t("picker.desc"), accept: { "application/octet-stream": CARD_EXT } }],
      });
      return openCardFile(p, await handle.getFile(), handle);
    } catch (e) {
      if (e.name === "AbortError") return;
      // no permission / API unavailable: fall back to the file input
    }
  }
  pickTarget = p.slot;
  $("#pickCard").value = "";
  $("#pickCard").click();
}

async function actNew(p = P()) {
  if (!(await guardUnsaved(p))) return;
  const v = await newCardDialog();
  if (!v) return;
  await run("st.creating", null, async () => {
    const r = ok(await rpc("newCard", [p.slot, v.name, v.size, v.ecc, v.platform]));
    resetPane(p);
    state.active = p.slot;
    applySummary(p, r);
    toast(t("toast.created", { name: v.name }), "ok");
    status("st.created");
  });
}

async function actClose(p) {
  if (!p.summary) return;
  const name = p.summary.card.name;
  if (p.summary.dirty && !(await confirmDialog(t("dlg.close.title"), t("dlg.close.msg", { name }), t("dlg.close.go"), true))) return;
  await run("st.closed", { name }, async () => {
    ok(await rpc("closeCard", [p.slot]));
    resetPane(p);
    // in single view, fall back to the other card if it is open
    if (!state.dual && panes[otherSlot(p.slot)].summary) state.active = otherSlot(p.slot);
    render();
    status("st.closed", { name });
  });
}

async function writeHandle(handle, data) {
  const perm = await handle.requestPermission?.({ mode: "readwrite" });
  if (perm && perm !== "granted") throw new Error(t("toast.permission"));
  const w = await handle.createWritable();
  await w.write(data);
  await w.close();
}

async function actSave({ forceDownload = false } = {}, p = P()) {
  await run("st.saving", null, async () => {
    const r = ok(await rpc("cardBytes", [p.slot]));
    let how;
    if (p.fileHandle && !forceDownload) {
      try {
        await writeHandle(p.fileHandle, r.data);
        how = "original";
      } catch (e) {
        if (e.name === "AbortError") return;
        toast(t("toast.saveFallback", { error: e.message }), "error");
        download(r.name, r.data);
        how = "downloaded";
      }
    } else if (window.showSaveFilePicker && !forceDownload) {
      try {
        const handle = await window.showSaveFilePicker({ suggestedName: r.name });
        await writeHandle(handle, r.data);
        p.fileHandle = handle;
        how = "saved";
      } catch (e) {
        if (e.name === "AbortError") return;
        download(r.name, r.data);
        how = "downloaded";
      }
    } else {
      download(r.name, r.data);
      how = "downloaded";
    }
    // "Download copy" only counts as saving when there is no original file to write to
    if (!forceDownload || !p.fileHandle) {
      ok(await rpc("markSaved", [p.slot]));
      p.summary.dirty = false;
    }
    render();
    if (sd && p.sdPath && sd.root) await sdRefresh();
    toast(t(`toast.saved.${how}`, { name: r.name }), "ok");
    status(`toast.saved.${how}`, { name: r.name });
  });
}

async function actUndo(p = P()) {
  await run("st.undoing", null, async () => {
    applySummary(p, ok(await rpc("undo", [p.slot])));
    status("st.undone");
  });
}

// Runs an editing call; on a name conflict asks to replace and retries with overwrite=true.
async function withOverwrite(call) {
  let r = await call(false);
  if (!r.ok && r.kind === "exists") {
    const yes = await confirmDialog(t("dlg.replace.title"), t("dlg.replace.msg", { error: r.error }), t("dlg.replace"), true);
    if (!yes) return null;
    r = await call(true);
  }
  return ok(r);
}

// files: [{rel, data?: ArrayBuffer, dir?: true}]
async function addFiles(p, files, destDir) {
  if (!files.length) return;
  const plain = files.filter((f) => !f.dir);
  const what = plain.length === 1 ? plain[0].rel : t("what.files", { n: plain.length });
  await run("st.adding", { what }, async () => {
    const r = await withOverwrite((ow) => rpc("add", [p.slot, files, destDir, ow]));
    if (!r) { status("st.cancelled"); return; }
    applySummary(p, r);
    if (destDir !== "/") p.expanded.add(destDir);
    renderTree(p);
    toast(t("toast.added", { dir: destDir, what }), "ok");
    status("st.added");
  });
}

async function importSaves(p, files) {
  files = files.filter((f) => !f.dir);
  if (!files.length) return;
  await run("st.importing", null, async () => {
    const info = ok(await rpc("inspectSaves", [files, p.summary.card.platform])).saves;
    const good = info.filter((x) => x.ok);
    const bad = info.filter((x) => !x.ok);
    if (!good.length) {
      await alertDialog(t("dlg.import.title"), t("dlg.import.none") + "\n\n" + bad.map((b) => "• " + b.error).join("\n"));
      status("st.cancelled");
      return;
    }
    let staged = null; // null = import what inspectSaves staged
    if (bad.length) {
      const msg = t("dlg.import.bad") + "\n" + bad.map((b) => "• " + b.error).join("\n") + "\n\n" + t("dlg.import.rest", { n: good.length });
      if (!(await confirmDialog(t("dlg.import.title"), msg, t("dlg.import.go")))) { status("st.cancelled"); return; }
      const keep = new Set(good.map((g) => g.file));
      staged = files.filter((f) => keep.has(f.rel.split("/").pop()));
    }
    let first = true;
    const r = await withOverwrite((ow) => {
      const arg = first ? staged : null; // retry reuses what is staged
      first = false;
      return rpc("importSaves", [p.slot, arg, ow]);
    });
    if (!r) { status("st.cancelled"); return; }
    applySummary(p, r);
    const list = good.map((g) => `• ${g.title ? `${g.title} (${g.name})` : g.name}`).join("\n");
    toast(t("toast.imported", { slot: p.slot, list }), "ok");
    status("st.imported", { n: good.length });
  });
}

async function actExportSave(p = P()) {
  const paths = selectedSaves(p);
  if (!paths.length) { toast(t("toast.noSaves"), "error"); return; }
  const fmt = await exportFormatDialog(paths.length, isPs1(p));
  if (!fmt) return;
  await run("st.exporting", null, async () => {
    const r = ok(await rpc("exportSaves", [p.slot, paths, fmt]));
    download(r.name, r.data, r.kind === "zip" ? "application/zip" : "application/octet-stream");
    status("st.extracted", { name: r.name, size: human(r.size) });
  });
}

async function copyItems(srcSlot, paths, dstSlot, destDir = "/") {
  const dst = panes[dstSlot];
  if (!paths.length || !dst.summary) return;
  await run("st.copying", { slot: dstSlot }, async () => {
    const r = await withOverwrite((ow) => rpc("copy", [srcSlot, paths, dstSlot, destDir, ow]));
    if (!r) { status("st.cancelled"); return; }
    applySummary(dst, r);
    if (destDir !== "/") dst.expanded.add(destDir);
    renderTree(dst);
    toast(t("toast.copied", { n: paths.length, slot: dstSlot }), "ok");
    status("st.copied", { slot: dstSlot });
  });
}

async function filesFromInput(list) {
  const out = [];
  const dirs = new Set();
  for (const f of list) {
    const rel = f.webkitRelativePath || f.name;
    const parts = rel.split("/");
    for (let i = 1; i < parts.length; i++) dirs.add(parts.slice(0, i).join("/"));
    out.push({ rel, data: await f.arrayBuffer() });
  }
  return [...[...dirs].map((d) => ({ rel: d, dir: true })), ...out];
}

async function entriesFromDrop(dt) {
  // folders via webkitGetAsEntry
  const items = [...(dt.items || [])].map((it) => it.webkitGetAsEntry?.()).filter(Boolean);
  if (!items.length) return filesFromInput(dt.files);
  const out = [];
  const readAll = (reader) => new Promise((res, rej) => {
    const acc = [];
    const next = () => reader.readEntries((batch) => { if (!batch.length) return res(acc); acc.push(...batch); next(); }, rej);
    next();
  });
  const walk = async (entry, prefix) => {
    const rel = prefix ? `${prefix}/${entry.name}` : entry.name;
    if (entry.isFile) {
      const file = await new Promise((res, rej) => entry.file(res, rej));
      out.push({ rel, data: await file.arrayBuffer() });
    } else if (entry.isDirectory) {
      out.push({ rel, dir: true });
      for (const child of await readAll(entry.createReader())) await walk(child, rel);
    }
  };
  for (const it of items) await walk(it, "");
  return out;
}

async function actMkdir(p = P()) {
  const parent = targetDir(p);
  const name = await promptName(t("dlg.newFolder.title"), t("dlg.newFolder.label", { dir: parent }));
  if (!name) return;
  await run("st.mkdir", null, async () => {
    const path = (parent === "/" ? "" : parent) + "/" + name;
    applySummary(p, ok(await rpc("mkdir", [p.slot, path])));
    if (parent !== "/") p.expanded.add(parent);
    select(p, path);
    status("st.mkdirDone", { path });
  });
}

async function actRename(p = P()) {
  const path = [...p.selected][0];
  const e = p.byPath.get(path);
  if (!e) return;
  const name = await promptName(t("dlg.rename.title"), t("dlg.rename.label", { name: e.name }), e.name);
  if (!name || name === e.name) return;
  await run("st.renaming", null, async () => {
    applySummary(p, ok(await rpc("rename", [p.slot, path, name])));
    const parent = p.parentOf.get(path) || "/";
    select(p, (parent === "/" ? "" : parent) + "/" + name);
    status("st.renamed");
  });
}

async function actDelete(p = P()) {
  const items = [...p.selected].map((x) => p.byPath.get(x)).filter((e) => e && !e.deleted);
  if (!items.length) return;
  const prot = items.some((e) => e.protected);
  const names = items.slice(0, 8).map((e) => `• ${e.title ? `${e.title} (${e.name})` : e.name}`).join("\n") +
    (items.length > 8 ? "\n" + t("dlg.delete.more", { n: items.length - 8 }) : "");
  const msg = (items.length === 1 ? t("dlg.delete.one") : t("dlg.delete.many", { n: items.length })) + `\n\n${names}` +
    (prot ? "\n\n" + t("dlg.delete.protected") : "") + "\n\n" + t(isPs1(p) ? "dlg.delete.ps1" : "dlg.delete.undo");
  if (!(await confirmDialog(t("dlg.delete.title"), msg, t("dlg.delete"), true))) return;
  await run("st.deleting", null, async () => {
    applySummary(p, ok(await rpc("remove", [p.slot, items.map((e) => e.path)])));
    if (!isPs1(p)) p.selected.clear(); // PS1 saves stay (deleted) where they were
    render();
    status("st.deleted", { n: items.length });
  });
}

async function actRestore(p = P()) {
  const paths = selectedRestorable(p);
  if (!paths.length) return;
  await run("st.restoring", null, async () => {
    applySummary(p, ok(await rpc("restore", [p.slot, paths])));
    status("st.restored", { n: paths.length });
  });
}

async function actExtract(p = P()) {
  const paths = p.selected.size ? [...p.selected] : ["/"];
  await run("st.extracting", null, async () => {
    const r = ok(await rpc("export", [p.slot, paths]));
    download(r.name, r.data, r.kind === "zip" ? "application/zip" : "application/octet-stream");
    status("st.extracted", { name: r.name, size: human(r.size) });
  });
}

async function actCheck(p = P()) {
  await run("st.checking", null, async () => {
    const r = ok(await rpc("check", [p.slot]));
    if (r.healthy) {
      toast(t("toast.checkOk"), "ok");
      status("st.checkOk");
    } else {
      await alertDialog(t("dlg.check.title"), (r.messages || []).join("\n") || t("dlg.check.failed"));
      status("st.checkBad");
    }
  });
}

function actDual() {
  state.dual = !state.dual;
  if (!state.dual && !P().summary && panes[otherSlot(state.active)].summary) state.active = otherSlot(state.active);
  render();
}

function actCompare() {
  state.compare = !state.compare;
  render();
}

function actCopy(p = P()) {
  if (!canCopy(p)) return;
  copyItems(p.slot, [...p.selected], otherSlot(p.slot), "/");
}

const ACTIONS = {
  open: () => actOpen(), new: () => actNew(), save: () => actSave(), saveAs: () => actSave({ forceDownload: true }),
  undo: () => actUndo(),
  addFiles: () => { pickTarget = state.active; $("#pickFiles").value = ""; $("#pickFiles").click(); },
  addFolder: () => { pickTarget = state.active; $("#pickFolder").value = ""; $("#pickFolder").click(); },
  importSave: () => { pickTarget = state.active; $("#pickSaves").value = ""; $("#pickSaves").click(); },
  exportSave: () => actExportSave(),
  mkdir: () => actMkdir(), extract: () => actExtract(), rename: () => actRename(), delete: () => actDelete(),
  check: () => actCheck(), dual: actDual, compare: actCompare, copy: () => actCopy(), sd: () => actOpenSd(), restore: () => actRestore(),
  convert: () => actConvert(), split: () => actSplit(), resize: () => actResize(),
};

document.addEventListener("click", (ev) => {
  const b = ev.target.closest("[data-act]");
  if (b && !b.disabled && ACTIONS[b.dataset.act]) { hideMenu(); ACTIONS[b.dataset.act](); }
});

$("#pickCard").addEventListener("change", (ev) => { const f = ev.target.files[0]; if (f) openCardFile(panes[pickTarget], f); });
$("#pickFiles").addEventListener("change", async (ev) => {
  const p = panes[pickTarget];
  addFiles(p, await filesFromInput(ev.target.files), targetDir(p));
});
$("#pickFolder").addEventListener("change", async (ev) => {
  const p = panes[pickTarget];
  addFiles(p, await filesFromInput(ev.target.files), targetDir(p));
});
$("#pickSaves").addEventListener("change", async (ev) => importFiles(panes[pickTarget], await filesFromInput(ev.target.files)));

// ---------------------------------------------------------------------------
// Panes: clicks, tree mouse/keyboard

$("#panes").addEventListener("mousedown", (ev) => {
  const el = ev.target.closest(".pane");
  if (el) setActive(el.dataset.slot);
});
$("#panes").addEventListener("focusin", (ev) => {
  const el = ev.target.closest(".pane");
  if (el) setActive(el.dataset.slot);
});
$("#panes").addEventListener("click", (ev) => {
  const blk = ev.target.closest(".blockmap .blk[data-path]");
  if (blk) { const p = panes[blk.closest(".pane").dataset.slot]; select(p, blk.dataset.path, { toggle: ev.ctrlKey || ev.metaKey }); return; }
  const b = ev.target.closest("[data-pane-act]");
  if (!b || state.busy) return;
  const p = panes[b.closest(".pane").dataset.slot];
  const act = b.dataset.paneAct;
  if (act === "open") actOpen(p);
  else if (act === "new") actNew(p);
  else if (act === "close") actClose(p);
});

function bindTree(p) {
  const tree = p.tree;
  tree.addEventListener("click", (ev) => {
    const row = ev.target.closest(".row");
    if (!row) { clearSelection(p); return; }
    const path = row.dataset.path;
    if (ev.target.closest("[data-twisty]")) { toggleExpand(p, path); return; }
    select(p, path, { toggle: ev.ctrlKey || ev.metaKey, range: ev.shiftKey });
  });
  tree.addEventListener("dblclick", (ev) => {
    const row = ev.target.closest(".row");
    if (!row) return;
    const e = p.byPath.get(row.dataset.path);
    if (e?.ps1) { if (!e.deleted) actExportSave(p); }
    else if (e?.dir) toggleExpand(p, e.path);
    else if (e) actExtract(p);
  });
  tree.addEventListener("keydown", (ev) => {
    if (!p.summary) return;
    const paths = p.visible.map((e) => e.path);
    const i = p.focus ? paths.indexOf(p.focus) : -1;
    const e = p.focus ? p.byPath.get(p.focus) : null;
    const go = (j) => { if (paths[j]) select(p, paths[j], { range: ev.shiftKey }); };
    switch (ev.key) {
      case "ArrowDown": go(Math.min(paths.length - 1, i + 1)); break;
      case "ArrowUp": go(Math.max(0, i - 1)); break;
      case "Home": go(0); break;
      case "End": go(paths.length - 1); break;
      case "ArrowRight":
        if (e?.dir && !p.expanded.has(e.path)) toggleExpand(p, e.path, true);
        else go(i + 1);
        break;
      case "ArrowLeft":
        if (e?.dir && p.expanded.has(e.path)) toggleExpand(p, e.path, false);
        else if (e) { const parent = p.parentOf.get(e.path); if (parent && parent !== "/") select(p, parent); }
        break;
      case "Enter": if (e?.dir) toggleExpand(p, e.path); break;
      case "a": case "A":
        if (ev.ctrlKey || ev.metaKey) { p.selected = new Set(paths); refreshSelection(p); } else return;
        break;
      default: return;
    }
    ev.preventDefault();
  });
  tree.addEventListener("contextmenu", (ev) => showMenu(p, ev));

  // internal drag (copy to the other card)
  tree.addEventListener("dragstart", (ev) => {
    const row = ev.target.closest(".row");
    if (!row) return;
    const path = row.dataset.path;
    if (!p.selected.has(path)) {
      // update classes in place: rebuilding the tree here would remove the
      // dragged row from the DOM and the browser would cancel the drag
      p.selected = new Set([path]);
      p.anchor = p.focus = path;
      p.tree.querySelectorAll(".row").forEach((r) => {
        const on = r.dataset.path === path;
        r.classList.toggle("selected", on);
        r.classList.toggle("focused", on);
        r.setAttribute("aria-selected", String(on));
      });
      if (!state.dual && p.slot === state.active) renderDetails(p);
      updateActions();
    }
    internalDrag = { slot: p.slot, paths: [...p.selected] };
    ev.dataTransfer.effectAllowed = "copy";
    ev.dataTransfer.setData("application/x-psmm", JSON.stringify(internalDrag));
    p.tree.querySelectorAll(".row.selected").forEach((r) => r.classList.add("dragging"));
  });
  tree.addEventListener("dragend", () => {
    internalDrag = null;
    document.querySelectorAll(".row.dragging").forEach((r) => r.classList.remove("dragging"));
    highlight(null);
    overlay.hidden = true;
  });
}

$("#panes").addEventListener("click", (ev) => {
  const btn = ev.target.closest(".tree-head button");
  if (!btn) return;
  const k = btn.dataset.sort;
  state.sort = { key: k, desc: state.sort.key === k ? !state.sort.desc : false };
  render();
});

// global shortcuts
document.addEventListener("keydown", (ev) => {
  if (dialog.open) return;
  if (ev.target.closest?.("select, input")) return;
  const mod = ev.ctrlKey || ev.metaKey;
  const k = ev.key.toLowerCase();
  const fire = (act) => {
    const b = document.querySelector(`.toolbar [data-act="${act}"]`);
    if (b && !b.disabled) { ev.preventDefault(); ACTIONS[act](); }
  };
  if (mod && k === "o") fire("open");
  else if (mod && k === "s") fire("save");
  else if (mod && k === "z") fire("undo");
  else if (mod && k === "e") fire("extract");
  else if (mod && ev.shiftKey && k === "n") fire("mkdir");
  else if (ev.key === "/" && !mod && P().summary) { ev.preventDefault(); $(".filter", P().el).focus(); }
  else if (ev.key === "F2") fire("rename");
  else if (ev.key === "Delete") fire("delete");
  else if (ev.key === "Escape") {
    if (!menu.hidden) hideMenu();
    else if (P().selected.size) clearSelection(P());
  }
});

// ---------------------------------------------------------------------------
// Context menu

const menu = $("#menu");
function hideMenu() { menu.hidden = true; }

function showMenu(p, ev) {
  if (!p.summary) return;
  ev.preventDefault();
  setActive(p.slot);
  const row = ev.target.closest(".row");
  if (row && !p.selected.has(row.dataset.path)) select(p, row.dataset.path);
  if (!row) clearSelection(p);
  const sel = p.selected.size;
  const item = (act, icon, label, enabled = true, cls = "") =>
    `<button data-act="${act}" ${enabled && !state.busy ? "" : "disabled"} class="${cls}"><i data-icon="${icon}"></i>${esc(label)}</button>`;
  if (isPs1(p)) {
    const ro = p.summary.card.readOnly;
    let ps1Html = item("importSave", "import-save", t("menu.importSave"), !ro) + "<hr>";
    if (canCopy(p)) ps1Html += item("copy", "copy", t("menu.copyTo", { slot: otherSlot(p.slot) }));
    if (selectedSaves(p).length) ps1Html += item("exportSave", "export-save", t("menu.exportSave"));
    if (selectedRestorable(p).length) ps1Html += item("restore", "undo", t("menu.restore"));
    ps1Html += item("delete", "delete", t("menu.delete"), selectedSaves(p).length > 0 && !ro, "danger");
    menu.innerHTML = ps1Html;
    paintIcons(menu);
    menu.hidden = false;
    const r = menu.getBoundingClientRect();
    menu.style.left = Math.min(ev.clientX, window.innerWidth - r.width - 8) + "px";
    menu.style.top = Math.min(ev.clientY, window.innerHeight - r.height - 8) + "px";
    return;
  }
  let html =
    item("addFiles", "add-file", t("menu.addFiles", { dir: targetDir(p) })) +
    item("addFolder", "import-folder", t("menu.addFolder")) +
    item("mkdir", "add-folder", t("menu.mkdir")) +
    "<hr>";
  if (canCopy(p)) html += item("copy", "copy", t("menu.copyTo", { slot: otherSlot(p.slot) }));
  if (selectedSaves(p).length) html += item("exportSave", "export-save", t("menu.exportSave"));
  html +=
    item("extract", "extract", sel ? (sel > 1 ? t("menu.extractMany", { n: sel }) : t("menu.extract")) : t("menu.extractAll")) +
    item("rename", "rename", t("menu.rename"), sel === 1) +
    item("delete", "delete", t("menu.delete"), sel > 0, "danger");
  menu.innerHTML = html;
  paintIcons(menu);
  menu.hidden = false;
  const { innerWidth: w, innerHeight: h } = window;
  const r = menu.getBoundingClientRect();
  menu.style.left = Math.min(ev.clientX, w - r.width - 8) + "px";
  menu.style.top = Math.min(ev.clientY, h - r.height - 8) + "px";
}
document.addEventListener("click", (ev) => { if (!menu.contains(ev.target)) hideMenu(); });
window.addEventListener("blur", hideMenu);
window.addEventListener("resize", hideMenu);

// ---------------------------------------------------------------------------
// Drag and drop: files from the PC, and rows between the two cards

const overlay = $("#dropOverlay");
let dragDepth = 0;
let dropTargetRow = null;
let internalDrag = null; // {slot, paths} while dragging rows

// {pane, dir}: dir is the folder under the cursor ("/" over empty tree space), null outside the tree
function dropTarget(ev) {
  const el = ev.target.closest?.(".pane");
  const p = el ? panes[el.dataset.slot] : (!state.dual ? P() : null);
  if (!p) return { pane: null, dir: null };
  if (!p.summary) return { pane: p, dir: null };
  const row = ev.target.closest?.(".row");
  if (!row) return { pane: p, dir: ev.target.closest?.(".tree-wrap") ? "/" : null };
  const e = p.byPath.get(row.dataset.path);
  if (!e) return { pane: p, dir: "/" };
  return { pane: p, dir: e.dir ? e.path : p.parentOf.get(e.path) || "/" };
}

function highlight(p, path) {
  if (dropTargetRow) dropTargetRow.classList.remove("drop-target");
  dropTargetRow = null;
  if (p && path && path !== "/") {
    dropTargetRow = p.tree.querySelector(`.row[data-path="${CSS.escape(path)}"]`);
    dropTargetRow?.classList.add("drop-target");
  }
}

const isFileDrag = (ev) => [...(ev.dataTransfer?.types || [])].includes("Files");

document.addEventListener("dragenter", (ev) => {
  if (!isFileDrag(ev)) return;
  ev.preventDefault();
  dragDepth++;
  overlay.hidden = false;
});
document.addEventListener("dragover", (ev) => {
  if (internalDrag) {
    const { pane, dir } = dropTarget(ev);
    const okTarget = pane && pane.slot !== internalDrag.slot && pane.summary && dir;
    if (okTarget && (isPs1(pane) !== isPs1(panes[internalDrag.slot]) || pane.summary.card.readOnly)) {
      highlight(null);
      overlay.hidden = false;
      $("#dropText").textContent = pane.summary.card.readOnly ? t("toast.readOnly") : t("drop.noMix");
      return;
    }
    if (okTarget) {
      ev.preventDefault();
      ev.dataTransfer.dropEffect = "copy";
      highlight(pane, dir);
      overlay.hidden = false;
      $("#dropText").textContent = t("drop.copy", { slot: pane.slot, dir });
    } else {
      highlight(null);
      overlay.hidden = true;
    }
    return;
  }
  if (!isFileDrag(ev)) return;
  ev.preventDefault();
  const { pane, dir } = dropTarget(ev);
  highlight(pane, dir);
  $("#dropText").textContent =
    !pane || !pane.summary ? t("drop.open") : dir ? t("drop.add", { dir }) : t("drop.either");
});
document.addEventListener("dragleave", (ev) => {
  if (!isFileDrag(ev)) return;
  if (--dragDepth <= 0) { dragDepth = 0; overlay.hidden = true; highlight(null); }
});
document.addEventListener("drop", async (ev) => {
  if (internalDrag) {
    ev.preventDefault();
    const drag = internalDrag;
    internalDrag = null;
    overlay.hidden = true;
    highlight(null);
    const { pane, dir } = dropTarget(ev);
    if (pane && pane.slot !== drag.slot && pane.summary && dir && isPs1(pane) === isPs1(panes[drag.slot]) && !pane.summary.card.readOnly) {
      setActive(pane.slot);
      copyItems(drag.slot, drag.paths, pane.slot, dir);
    }
    return;
  }
  if (!isFileDrag(ev)) return;
  ev.preventDefault();
  dragDepth = 0; overlay.hidden = true;
  const { pane: target, dir } = dropTarget(ev);
  highlight(null);
  const p = target || P();
  const files = [...ev.dataTransfer.files];
  const items = [...(ev.dataTransfer.items || [])];
  const anyDir = items.some((it) => it.webkitGetAsEntry?.()?.isDirectory);
  const single = files.length === 1 ? files[0] : null;
  if (single && !anyDir && looksLikeCard(single) && (!p.summary || !dir)) {
    let handle = null;
    try { handle = await items[0].getAsFileSystemHandle?.(); } catch { /* unsupported */ }
    return openCardFile(p, single, handle && handle.kind === "file" ? handle : null);
  }
  if (!p.summary) { toast(t("toast.notCard"), "error"); return; }
  setActive(p.slot);
  if (isPs1(p)) {
    if (anyDir) { toast(t("toast.ps1NoFolders"), "error"); return; }
    if (p.summary.card.readOnly && !files.every(looksLikeCard)) { toast(t("toast.readOnly"), "error"); return; }
    return importFiles(p, await filesFromInput(files)); // PS1 cards only take saves (and whole cards)
  }
  if (!anyDir && files.length && files.every((f) => hasExt(f.name, SAVE_EXT) || looksLikeCard(f))) {
    return importFiles(p, await filesFromInput(files));
  }
  addFiles(p, await entriesFromDrop(ev.dataTransfer), dir || "/");
});

// ---------------------------------------------------------------------------
// Gen2 / SD2PSX SD card: the page reads and writes the SD (File System Access
// API on Chrome/Edge; read-only folder upload elsewhere), Python does the
// layout and INI logic.

const SD_CREATABLE = ["PS2", "PS1", "COH"]; // Conquest (SC2) cards use their own format
let sd = null; // {root, name, readOnly, fileMap, data, texts, expanded}

async function actOpenSd() {
  if (window.showDirectoryPicker) {
    let root;
    try {
      root = await window.showDirectoryPicker({ id: "psmm-sd", mode: "readwrite" });
    } catch (e) {
      if (e.name !== "AbortError") toast(t("toast.sdNoAccess", { error: e.message }), "error");
      return;
    }
    if (/^(memorycards|ps1|ps2|coh|sc2|\.sd2psx)$/i.test(root.name)) {
      toast(t("sd.pickedSub", { name: root.name }), "error");
      return;
    }
    sd = { root, name: root.name, readOnly: false, fileMap: null, data: null, texts: {}, expanded: null };
    await run("st.sdScanning", null, sdRefresh);
  } else {
    $("#pickSdDir").value = "";
    $("#pickSdDir").click();
  }
}

$("#pickSdDir").addEventListener("change", async (ev) => {
  const list = [...ev.target.files];
  if (!list.length) return;
  const name = list[0].webkitRelativePath.split("/")[0];
  const fileMap = new Map();
  for (const f of list) fileMap.set(f.webkitRelativePath.split("/").slice(1).join("/"), f);
  sd = { root: null, name, readOnly: true, fileMap, data: null, texts: {}, expanded: null };
  await run("st.sdScanning", null, sdRefresh);
});

async function sdScan() {
  const files = [];
  const texts = {};
  const add = async (path, file) => {
    files.push({ path, size: file.size });
    if (/\.ini$/i.test(path)) texts[path] = await file.text();
  };
  if (sd.root) {
    const walk = async (dir, prefix, depth) => {
      for await (const [name, h] of dir.entries()) {
        const path = `${prefix}/${name}`;
        if (h.kind === "file") await add(path, await h.getFile());
        else if (depth > 0) await walk(h, path, depth - 1);
      }
    };
    for (const [top, depth] of [["MemoryCards", 2], [".sd2psx", 0]]) {
      let dir;
      try { dir = await sd.root.getDirectoryHandle(top); } catch { continue; }
      await walk(dir, top, depth);
    }
  } else {
    for (const [path, file] of sd.fileMap) {
      if (/^(MemoryCards|\.sd2psx)\//i.test(path)) await add(path, file);
    }
  }
  return { files, texts };
}

// re-reads the SD (call inside run())
async function sdRefresh() {
  const { files, texts } = await sdScan();
  sd.data = ok(await rpc("sdLoad", [files, texts]));
  sd.texts = texts;
  if (sd.data.variants.some((v) => v.folders.some((f) => f.kind === "game"))) loadGameDb();
  if (!sd.expanded) {
    const keys = sd.data.variants.flatMap((v) => v.folders.map((f) => `${v.name}/${f.folder}`));
    sd.expanded = new Set(keys.length <= 12 ? keys : keys.filter((k) => k.endsWith("/BOOT")));
  }
  const n = sd.data.variants.reduce((a, v) => a + v.folders.reduce((b, f) => b + f.channels.length, 0), 0);
  status("st.sdLoaded", { name: sd.name, n });
  render();
}

async function sdHandle(path, create = false) {
  const parts = path.split("/");
  let dir = sd.root;
  for (const part of parts.slice(0, -1)) dir = await dir.getDirectoryHandle(part, { create });
  return dir.getFileHandle(parts[parts.length - 1], { create });
}

async function sdWrite(path, data) {
  await writeHandle(await sdHandle(path, true), data);
}

async function sdDeleteFile(path) {
  const parts = path.split("/");
  let dir = sd.root;
  for (const part of parts.slice(0, -1)) dir = await dir.getDirectoryHandle(part);
  await dir.removeEntry(parts[parts.length - 1]);
}

// ---------------------------------------------------------------------------
// Whole-SD backup: a .zip of MemoryCards/ and .sd2psx/, made in the browser.
// Files are compressed one at a time (cards are mostly empty and shrink a lot)
// and written straight to disk when the browser allows it, so even a large SD
// card needs little memory. ZIP64 kicks in past 4 GB.

const CRC_TABLE = (() => {
  const t = new Uint32Array(256);
  for (let n = 0; n < 256; n++) {
    let c = n;
    for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    t[n] = c >>> 0;
  }
  return t;
})();

function crc32(u8) {
  let c = 0xffffffff;
  for (let i = 0; i < u8.length; i++) c = CRC_TABLE[(c ^ u8[i]) & 0xff] ^ (c >>> 8);
  return (c ^ 0xffffffff) >>> 0;
}

async function deflateRaw(u8) {
  const stream = new Blob([u8]).stream().pipeThrough(new CompressionStream("deflate-raw"));
  return new Uint8Array(await new Response(stream).arrayBuffer());
}

// minimal streaming ZIP writer; out(chunk) receives each piece in order
function zipWriter(out) {
  const enc = new TextEncoder();
  const central = [];
  let offset = 0;
  const put = async (u8) => { await out(u8); offset += u8.length; };
  const dosTime = (ms) => {
    const d = new Date(ms || Date.now());
    const y = Math.max(1980, d.getFullYear());
    return {
      time: (d.getHours() << 11) | (d.getMinutes() << 5) | (d.getSeconds() >> 1),
      date: ((y - 1980) << 9) | ((d.getMonth() + 1) << 5) | d.getDate(),
    };
  };
  return {
    async add(name, data, mtime) {
      const raw = data;
      const crc = crc32(raw);
      let body = await deflateRaw(raw);
      let method = 8;
      if (body.length >= raw.length) { body = raw; method = 0; }
      const fname = enc.encode(name);
      const { time, date } = dosTime(mtime);
      const h = new DataView(new ArrayBuffer(30));
      h.setUint32(0, 0x04034b50, true); h.setUint16(4, 20, true); h.setUint16(6, 0x0800, true); // UTF-8 names
      h.setUint16(8, method, true); h.setUint16(10, time, true); h.setUint16(12, date, true);
      h.setUint32(14, crc, true); h.setUint32(18, body.length, true); h.setUint32(22, raw.length, true);
      h.setUint16(26, fname.length, true);
      central.push({ fname, method, time, date, crc, csize: body.length, size: raw.length, offset });
      await put(new Uint8Array(h.buffer)); await put(fname); await put(body);
    },
    async finish() {
      const start = offset;
      for (const e of central) {
        const big = e.offset >= 0xffffffff;
        const extra = big ? new DataView(new ArrayBuffer(12)) : null;
        if (big) { extra.setUint16(0, 1, true); extra.setUint16(2, 8, true); extra.setBigUint64(4, BigInt(e.offset), true); }
        const h = new DataView(new ArrayBuffer(46));
        h.setUint32(0, 0x02014b50, true); h.setUint16(4, 45, true); h.setUint16(6, big ? 45 : 20, true);
        h.setUint16(8, 0x0800, true); h.setUint16(10, e.method, true); h.setUint16(12, e.time, true); h.setUint16(14, e.date, true);
        h.setUint32(16, e.crc, true); h.setUint32(20, e.csize, true); h.setUint32(24, e.size, true);
        h.setUint16(28, e.fname.length, true); h.setUint16(30, big ? 12 : 0, true);
        h.setUint32(42, big ? 0xffffffff : e.offset, true);
        await put(new Uint8Array(h.buffer)); await put(e.fname);
        if (big) await put(new Uint8Array(extra.buffer));
      }
      const size = offset - start;
      const zip64 = start >= 0xffffffff || central.length >= 0xffff;
      if (zip64) {
        const r = new DataView(new ArrayBuffer(56));
        r.setUint32(0, 0x06064b50, true); r.setBigUint64(4, 44n, true); r.setUint16(12, 45, true); r.setUint16(14, 45, true);
        r.setBigUint64(24, BigInt(central.length), true); r.setBigUint64(32, BigInt(central.length), true);
        r.setBigUint64(40, BigInt(size), true); r.setBigUint64(48, BigInt(start), true);
        const l = new DataView(new ArrayBuffer(20)); // locator: where the record above starts
        l.setUint32(0, 0x07064b50, true); l.setBigUint64(8, BigInt(offset), true); l.setUint32(16, 1, true);
        await put(new Uint8Array(r.buffer));
        await put(new Uint8Array(l.buffer));
      }
      const e = new DataView(new ArrayBuffer(22));
      e.setUint32(0, 0x06054b50, true);
      e.setUint16(8, Math.min(central.length, 0xffff), true); e.setUint16(10, Math.min(central.length, 0xffff), true);
      e.setUint32(12, Math.min(size, 0xffffffff), true); e.setUint32(16, zip64 ? 0xffffffff : start, true);
      await put(new Uint8Array(e.buffer));
    },
  };
}

async function sdFile(path) {
  return sd.root ? (await sdHandle(path)).getFile() : sd.fileMap.get(path);
}

async function sdBackup() {
  const { files } = await sdScan();
  if (!files.length) { toast(t("sd.backup.empty"), "error"); return; }
  const total = files.reduce((a, f) => a + f.size, 0);
  const unsaved = SLOTS.filter((s) => panes[s].sdPath && panes[s].summary?.dirty);
  const ok1 = await openDialog(
    `<h3>${esc(t("sd.backup.title"))}</h3>` +
    `<div class="msg">${esc(t("sd.backup.msg", { n: files.length, size: human(total) }))}</div>` +
    (unsaved.length ? `<div class="warnbox">${esc(t("sd.backup.unsaved"))}</div>` : "") +
    `<div class="msg small">${esc(t("sd.backup.restore"))}</div>` + actionsHtml(t("sd.backup.go")),
    () => true,
  );
  if (!ok1) return;
  const stamp = new Date().toISOString().slice(0, 16).replace("T", "_").replace(":", "-");
  const name = `${sd.name.replace(/[^\w.-]+/g, "_") || "SD"}-backup-${stamp}.zip`;
  // straight to disk where possible; otherwise kept in memory (compressed) and downloaded
  let writable = null;
  if (window.showSaveFilePicker) {
    try {
      const h = await window.showSaveFilePicker({ suggestedName: name, types: [{ description: "ZIP", accept: { "application/zip": [".zip"] } }] });
      writable = await h.createWritable();
    } catch (e) {
      if (e.name === "AbortError") return;
      writable = null;
    }
  }
  const parts = [];
  await run("sd.backup.progress", { done: 0, n: files.length, pct: 0 }, async () => {
    const zip = zipWriter(async (u8) => (writable ? writable.write(u8) : parts.push(u8)));
    let done = 0, bytes = 0;
    try {
      for (const f of files) {
        const file = await sdFile(f.path);
        await zip.add(f.path, new Uint8Array(await file.arrayBuffer()), file.lastModified);
        done++; bytes += f.size;
        status("sd.backup.progress", { done, n: files.length, pct: Math.round((bytes / Math.max(1, total)) * 100) });
      }
      await zip.finish();
    } catch (e) {
      if (writable) await writable.abort().catch(() => {});
      throw e;
    }
    if (writable) await writable.close();
    else download(name, new Blob(parts, { type: "application/zip" }), "application/zip");
    status("sd.backup.done", { name, n: files.length });
    toast(t("sd.backup.done", { name, n: files.length }));
  });
}

// ---------------------------------------------------------------------------
// "All saves": every save on every card of the SD in one list. Each card is read
// once (only its directory) and remembered until it changes on the SD.

function sdChannels() {
  const out = [];
  for (const v of sd.data.variants) {
    for (const f of v.folders) {
      for (const c of f.channels) out.push({ variant: v.name, vlabel: v.label, folder: f.folder, flabel: f.label, kind: f.kind, number: c.number, chName: c.name, path: c.path });
    }
  }
  return out;
}

async function sdIndexSaves() {
  sd.index = sd.index || new Map(); // path -> {sig, platform, saves, error}
  const chans = sdChannels();
  let i = 0;
  for (const ch of chans) {
    i++;
    status("sd.all.reading", { i, n: chans.length });
    let file;
    try { file = await sdFile(ch.path); } catch { continue; }
    if (!file) continue;
    const sig = `${file.size}:${file.lastModified}`;
    if (sd.index.get(ch.path)?.sig === sig) continue;
    const buf = await file.arrayBuffer();
    const r = await rpc("sdIndexCard", [buf], [buf]);
    sd.index.set(ch.path, r.ok ? { sig, platform: r.platform, saves: r.saves } : { sig, saves: [], error: r.error });
  }
  for (const path of [...sd.index.keys()]) if (!chans.some((c) => c.path === path)) sd.index.delete(path);
  const rows = [];
  for (const ch of chans) {
    const ix = sd.index.get(ch.path);
    if (!ix) continue;
    for (const sv of ix.saves) rows.push({ ...sv, platform: ix.platform, ch });
  }
  // the same save folder on more than one card
  const count = new Map();
  for (const r of rows) { const k = `${r.platform}:${r.name}`; count.set(k, (count.get(k) || 0) + 1); }
  for (const r of rows) r.copies = count.get(`${r.platform}:${r.name}`);
  return { rows, cards: chans.length, failed: chans.filter((c) => sd.index.get(c.path)?.error).length };
}

async function sdAllSaves() {
  let data = null;
  await run("sd.all.reading", { i: 0, n: 0 }, async () => {
    await loadGameDb();
    data = await sdIndexSaves();
    status("sd.all.ready", { n: data.rows.length, cards: data.cards });
  });
  if (!data) return;
  const { rows } = data;
  const where = (ch) => `${ch.vlabel} · ${gameName(ch.folder) || ch.flabel} · ${t("sd.all.channel", { n: ch.number })}${ch.chName ? ` (${ch.chName})` : ""}`;
  for (const r of rows) {
    r.game = gameName(r.serial) || "";
    r.where = where(r.ch);
    r.hay = fold(`${r.name} ${r.title} ${r.serial || ""} ${(r.serial || "").replace("-", "")} ${r.game} ${r.where} ${r.ch.folder}`);
  }
  rows.sort((a, b) => (a.game || a.title || a.name).localeCompare(b.game || b.title || b.name) || a.where.localeCompare(b.where));
  const dups = rows.filter((r) => r.copies > 1).length;
  const list = (q, onlyDups) => {
    const words = fold(q).split(/\s+/).filter(Boolean);
    const shown = rows.filter((r) => (!onlyDups || r.copies > 1) && words.every((w) => r.hay.includes(w)));
    const body = shown.map((r) =>
      `<button type="submit" class="as-row" value="open:${rows.indexOf(r)}" title="${esc(t("sd.all.openTip"))}">` +
      `<span class="as-title"><b>${esc(r.title || r.name)}</b>` +
      `<small>${esc([r.game && r.game !== r.title ? r.game : "", r.serial || "", r.name].filter(Boolean).join(" · "))}</small></span>` +
      `<span class="as-where">${esc(r.where)}</span>` +
      `<span class="as-size">${esc(r.platform === "PS1" ? blocksLabel(Math.max(1, Math.round(r.size / 8192))) : human(r.size))}</span>` +
      (r.copies > 1 ? `<span class="tag" title="${esc(t("sd.all.dupTip", { n: r.copies }))}">${esc(t("sd.all.dup", { n: r.copies }))}</span>` : `<span></span>`) +
      `</button>`).join("");
    return { html: body || `<div class="tree-empty">${esc(t(words.length ? "filter.none" : "sd.all.none", { q: q.trim() }))}</div>`, n: shown.length };
  };
  const first = list("", false);
  const pr = openDialog(
    `<h3>${esc(t("sd.all.title"))}</h3>` +
    `<div class="msg small">${esc(t("sd.all.summary", { n: rows.length, cards: data.cards, dups }))}` +
    (data.failed ? ` ${esc(t("sd.all.failed", { n: data.failed }))}` : "") + `</div>` +
    `<div class="as-tools"><div class="tree-filter"><span class="filter-icon">${svg("search")}</span>` +
    `<input type="search" name="q" placeholder="${esc(t("filter.placeholder"))}" aria-label="${esc(t("filter.label"))}" autocomplete="off" spellcheck="false"></div>` +
    `<label class="inline"><input type="checkbox" name="dups"${dups ? "" : " disabled"}> ${esc(t("sd.all.onlyDups"))}</label></div>` +
    `<div class="as-count muted">${esc(t("sd.all.count", { n: first.n }))}</div>` +
    `<div class="as-list">${first.html}</div>` +
    `<div class="actions"><button class="btn" value="cancel">${esc(t("dlg.close"))}</button></div>`,
    (f, btn) => btn,
  );
  dialog.classList.add("wide");
  const refresh = () => {
    const r = list(dform.q.value, dform.dups.checked);
    dform.querySelector(".as-list").innerHTML = r.html;
    dform.querySelector(".as-count").textContent = t("sd.all.count", { n: r.n });
  };
  dform.q.addEventListener("input", refresh);
  dform.dups.addEventListener("change", refresh);
  dform.q.addEventListener("keydown", (ev) => { if (ev.key === "Enter") ev.preventDefault(); });
  dform.q.focus();
  const res = await pr;
  dialog.classList.remove("wide");
  if (!res || !String(res).startsWith("open:")) return;
  const r = rows[+String(res).slice(5)];
  await sdOpenChannel(r.ch.variant, r.ch.path);
  const p = panes[sdOpenSlot(r.ch.path) || state.active];
  if (!p?.summary) return;
  sd.expanded.add(`${r.ch.variant}/${r.ch.folder}`);
  renderSd();
  const e = p.summary.tree.find((x) => x.name === r.name && !x.deleted);
  if (e) select(p, e.path);
}

const sdOpenSlot = (path) => SLOTS.find((s) => panes[s].sdPath === path) || null;
const sdVariant = (name) => sd.data.variants.find((v) => v.name === name);
const sdFolder = (variant, folder) => sdVariant(variant)?.folders.find((f) => f.folder === folder);

function renderSd() {
  const bar = $("#sdbar");
  if (!sd) { bar.innerHTML = ""; return; }
  bar.classList.toggle("collapsed", state.sdCollapsed);
  if (state.sdCollapsed) {
    bar.innerHTML = `<button class="sd-rail" data-sd="collapse" title="${esc(t("sd.expand", { name: sd.name }))}" aria-label="${esc(t("sd.expand", { name: sd.name }))}">` +
      `<span class="sd-icon">${svg("sd")}</span><span class="twisty">${svg("chevron")}</span></button>`;
    return;
  }
  const ro = sd.readOnly;
  const dis = ro || state.busy ? "disabled" : "";
  let html =
    `<div class="sd-head"><span class="sd-icon">${svg("sd")}</span><span class="sd-name" title="${esc(sd.name)}">${esc(sd.name)}</span>` +
    `<button class="icon-btn small sd-fold" data-sd="collapse" title="${esc(t("sd.collapse"))}" aria-label="${esc(t("sd.collapse"))}">${svg("chevron")}</button>` +
    `<button class="icon-btn small" data-sd="close" title="${esc(t("sd.close"))}" aria-label="${esc(t("sd.close"))}">${svg("close")}</button></div>` +
    `<div class="sd-tools">` +
    `<button data-sd="settings" ${dis}><i data-icon="gear"></i>${esc(t("sd.settings"))}</button>` +
    `<button data-sd="g2f" ${dis}><i data-icon="link"></i>${esc(t("sd.g2f"))}</button>` +
    `<button data-sd="refresh" ${state.busy ? "disabled" : ""}><i data-icon="reload"></i>${esc(t("sd.refresh"))}</button>` +
    `<button data-sd="allsaves" ${state.busy || !sd.data ? "disabled" : ""}><i data-icon="list"></i>${esc(t("sd.allSaves"))}</button>` +
    `<button data-sd="backup" ${state.busy || !sd.data ? "disabled" : ""} title="${esc(t("sd.backup.tip"))}"><i data-icon="archive"></i>${esc(t("sd.backup"))}</button></div>`;
  if (ro) html += `<div class="sd-note">${esc(t("sd.readOnly"))}</div>`;
  const data = sd.data;
  if (!data) { bar.innerHTML = html; paintIcons(bar); return; }
  if (!data.rootOk) html += `<div class="sd-note">${esc(t("sd.noRoot"))}</div>`;
  const variants = [...data.variants];
  if (!variants.some((v) => v.name === "PS2")) variants.unshift({ name: "PS2", label: "PS2", platform: "PS2", folders: [], nextIndex: 1 });
  for (const v of variants) {
    const creatable = SD_CREATABLE.includes(v.name.toUpperCase());
    html += `<div class="sd-variant-head"><h3>${esc(v.label)}</h3>` +
      (creatable ? `<button data-sd="newcard" data-variant="${esc(v.name)}" ${dis}><i data-icon="plus"></i>${esc(t("sd.newCard"))}</button>` : "") +
      `</div>`;
    if (!v.folders.length) html += `<div class="sd-empty">${esc(t("sd.noCards"))}</div>`;
    for (const f of v.folders) {
      const key = `${v.name}/${f.folder}`;
      const open = sd.expanded.has(key);
      const canAdd = creatable && f.nextChannel && !ro;
      html += `<div class="sd-folder"><div class="sd-folder-head" data-sd="toggle" data-key="${esc(key)}">` +
        `<span class="twisty${open ? " open" : ""}">${svg("chevron")}</span>` +
        `<span class="kind${f.kind === "game" ? " game" : ""}" title="${esc(t(f.kind === "game" ? "sd.kindGame" : "sd.kindCard"))}">${svg(f.kind === "game" ? "save" : "memcard")}</span>` +
        `<span class="names"><span class="lbl" title="${esc(f.folder)}">${esc(f.label)}</span>` +
        (f.kind === "game" && gameName(f.folder) ? `<span class="gname" title="${esc(gameName(f.folder))}">${esc(gameName(f.folder))}</span>` : "") +
        `</span>` +
        `<span class="count">${f.channels.length}</span>` +
        `<button class="mini" data-sd="names" data-variant="${esc(v.name)}" data-folder="${esc(f.folder)}" title="${esc(t("sd.channelNames"))}" ${dis}>${svg("tag")}</button>` +
        `<button class="mini" data-sd="addch" data-variant="${esc(v.name)}" data-folder="${esc(f.folder)}" title="${esc(t("sd.addChannel"))}" ${canAdd && !state.busy ? "" : "disabled"}>${svg("plus")}</button>` +
        `</div>`;
      if (open) {
        for (const c of f.channels) {
          const slot = sdOpenSlot(c.path);
          html += `<div class="sd-ch" data-sd="open" data-variant="${esc(v.name)}" data-path="${esc(c.path)}" title="${esc(c.path)}">` +
            `<span class="num">${c.number}</span>` +
            `<span class="nm${c.name ? "" : " none"}">${esc(c.name || t("sd.noName"))}</span>` +
            (slot ? `<span class="open-in" title="${esc(t("sd.openedIn", { slot }))}">${slot}</span>` : "") +
            `<span class="sz">${human(c.size)}</span>` +
            (ro ? "" : `<button class="del" data-sd="del" data-path="${esc(c.path)}" title="${esc(t("sd.deleteChannel"))}">${svg("delete")}</button>`) +
            `</div>`;
        }
      }
      html += `</div>`;
    }
  }
  bar.innerHTML = html;
  paintIcons(bar);
}

$("#sdbar").addEventListener("click", (ev) => {
  const el = ev.target.closest("[data-sd]");
  if (!el || el.disabled || !sd) return;
  ev.stopPropagation();
  const act = el.dataset.sd;
  if (act === "collapse") {
    state.sdCollapsed = !state.sdCollapsed;
    storage.set("psmm-sd-collapsed", state.sdCollapsed ? "1" : "0");
    render();
    return;
  }
  if (act === "toggle") {
    const key = el.dataset.key;
    sd.expanded.has(key) ? sd.expanded.delete(key) : sd.expanded.add(key);
    renderSd();
    return;
  }
  if (state.busy) return;
  if (act === "close") sdClose();
  else if (act === "refresh") run("st.sdScanning", null, sdRefresh);
  else if (act === "open") sdOpenChannel(el.dataset.variant, el.dataset.path);
  else if (act === "del") sdDeleteChannel(el.dataset.path);
  else if (act === "newcard") sdNewCard(el.dataset.variant);
  else if (act === "addch") sdAddChannel(el.dataset.variant, el.dataset.folder);
  else if (act === "names") sdChannelNames(el.dataset.variant, el.dataset.folder);
  else if (act === "settings") sdSettings();
  else if (act === "g2f") sdGame2Folder();
  else if (act === "backup") sdBackup();
  else if (act === "allsaves") sdAllSaves();
});

function sdClose() {
  sd = null;
  for (const slot of SLOTS) panes[slot].sdPath = null; // cards stay open, now just as files
  render();
}

async function sdOpenChannel(variant, path) {
  const where = sdOpenSlot(path);
  if (where) { setActive(where); return; }
  const p = P();
  try {
    if (sd.root) {
      const handle = await sdHandle(path);
      await openCardFile(p, await handle.getFile(), handle, path);
    } else {
      await openCardFile(p, sd.fileMap.get(path), null, path);
    }
  } catch (e) {
    toast(t("toast.sdNoAccess", { error: e.message }), "error");
  }
  renderSd();
}

function sdSizeOptions(variant) {
  const v = sdVariant(variant);
  const existing = v?.folders.flatMap((f) => f.channels.map((c) => c.size)).find((x) => x) || 0;
  const def = variant.toUpperCase() === "PS2" ? sd.data.defaultSizeMB : Math.max(1, Math.round(existing / 1048576)) || 1;
  return { sizes: [1, 2, 4, 8, 16, 32, 64], def };
}

const GAME_ID_RE = /^[A-Z]{4}[-_ ]?\d{3}\.?\d{2}$/i;

async function sdNewCard(variant) {
  const v = sdVariant(variant) || { nextIndex: 1 };
  const { sizes, def } = sdSizeOptions(variant);
  const ps1 = variant.toUpperCase() === "PS1";
  const choice = await openDialog(
    `<h3>${esc(t("dlg.sdnew.title"))} · ${esc(variant)}</h3>` +
    `<div class="choice">` +
    `<label><input type="radio" name="kind" value="numbered" checked><b>${esc(t("dlg.sdnew.numbered"))}</b><span class="path-preview">MemoryCards/${esc(variant)}/Card${v.nextIndex}/Card${v.nextIndex}-1.mcd</span></label>` +
    `<label><input type="radio" name="kind" value="game"><b>${esc(t("dlg.sdnew.game"))}</b><span>${esc(t("dlg.sdnew.note"))}</span></label>` +
    `</div>` +
    `<label>${esc(t("dlg.sdnew.gameId"))}<input type="text" name="game" class="mono" placeholder="SLUS-20963" autocomplete="off" spellcheck="false"></label>` +
    (ps1 ? `<div class="msg small">${esc(t("dlg.sdnew.ps1note"))}</div>` :
      `<label>${esc(t("dlg.sdnew.size"))}<select name="size">` +
      sizes.map((m) => `<option value="${m}"${m === def ? " selected" : ""}>${m} MB</option>`).join("") + `</select></label>`) +
    `<div class="err" id="dErr"></div>` + actionsHtml(t("dlg.sdnew.create")),
    (f) => {
      const kind = f.kind.value;
      const game = f.game.value.trim();
      if (kind === "game" && !GAME_ID_RE.test(game)) {
        f.querySelector("#dErr").textContent = t("sd.badGameId");
        return false;
      }
      return { kind, game: kind === "game" ? game : "", size: ps1 ? 0 : +f.size.value };
    },
  );
  if (!choice) return;
  let createdPath = null;
  await run("st.creating", null, async () => {
    const plan = ok(await rpc("sdPlanCard", [variant, choice.game]));
    const blank = ok(await rpc("blankCard", [choice.size, ps1 ? "PS1" : "PS2"]));
    await sdWrite(plan.path, blank.data);
    sd.expanded.add(`${plan.variant}/${plan.folder}`);
    await sdRefresh();
    createdPath = plan.path;
    toast(t("toast.sdCreated", { path: plan.path }), "ok");
  });
  if (createdPath) await sdOpenChannel(variant, createdPath); // open the new card right away
}

async function sdAddChannel(variant, folder) {
  let plan;
  try { plan = ok(await rpc("sdPlanChannel", [variant, folder])); } catch (e) { toast(e.message, "error"); return; }
  const ps1 = variant.toUpperCase() === "PS1";
  const mb = plan.size ? Math.max(1, Math.round(plan.size / 1048576)) : sd.data.defaultSizeMB;
  const label = sdFolder(variant, folder)?.label || folder;
  const sizeText = ps1 ? "128 KB" : `${mb} MB`;
  if (!(await confirmDialog(t("dlg.sdch.title"), t("dlg.sdch.msg", { n: plan.channel, folder: label, size: sizeText, path: plan.path }), t("dlg.sdch.create")))) return;
  await run("st.creating", null, async () => {
    const blank = ok(await rpc("blankCard", [mb, ps1 ? "PS1" : "PS2"]));
    await sdWrite(plan.path, blank.data);
    await sdRefresh();
    toast(t("toast.sdCreated", { path: plan.path }), "ok");
  });
}

async function sdDeleteChannel(path) {
  const slot = sdOpenSlot(path);
  if (slot) { toast(t("toast.sdOpenElsewhere", { slot }), "error"); return; }
  if (!(await confirmDialog(t("dlg.sddel.title"), t("dlg.sddel.msg", { path }), t("dlg.delete"), true))) return;
  // the folder and channel number, to drop the channel's name from the INI too
  const folder = sd.data.variants.flatMap((v) => v.folders).find((f) => f.channels.some((c) => c.path === path));
  const channel = folder?.channels.find((c) => c.path === path);
  await run("st.deleting", null, async () => {
    await sdDeleteFile(path);
    if (folder?.ini && channel) {
      const r = ok(await rpc("sdRemoveChannelName", [folder.ini, channel.number]));
      if (r.path) await sdWrite(r.path, new TextEncoder().encode(r.text));
    }
    await sdRefresh();
    toast(t("toast.sdDeleted", { path }), "ok");
  });
}

async function sdWriteText(r) {
  await sdWrite(r.path, new TextEncoder().encode(r.text));
  await sdRefresh();
  toast(t("toast.sdWritten", { path: r.path }), "ok");
}

async function sdChannelNames(variant, folder) {
  const f = sdFolder(variant, folder);
  if (!f) return;
  // start from every name in the INI (also channels without a file), so none get lost
  const names = { ...f.names };
  const rows = [];
  for (let n = 1; n <= 8; n++) {
    rows.push(`<span>${esc(t("dlg.names.channel", { n }))}</span><input type="text" name="ch${n}" value="${esc(names[n] || "")}" maxlength="40" autocomplete="off">`);
  }
  const result = await openDialog(
    `<h3>${esc(t("dlg.names.title", { folder: f.label }))}</h3><div class="msg small">${esc(t("dlg.names.hint"))}</div>` +
    `<div class="names-grid">${rows.join("")}</div>` + actionsHtml(t("dlg.save")),
    (form) => {
      const out = {};
      for (let n = 1; n <= 8; n++) out[n] = form[`ch${n}`].value.trim();
      return out;
    },
  );
  if (!result) return;
  await run("st.saving", null, async () => {
    await sdWriteText(ok(await rpc("sdWriteChannelNames", [f.ini || f.iniPath, result])));
  });
}

async function sdSettings() {
  const info = sd.data.settings;
  const rows = info.settings.map((s, i) => {
    const opts = s.kind === "onoff" ? ["ON", "OFF"] : s.choices;
    return `<span>${esc(t(`set.${s.section}.${s.key}`))}${s.present ? "" : ` <small class="muted">${esc(t("dlg.settings.default"))}</small>`}</span>` +
      `<select name="s${i}">${opts.map((o) => `<option${o === s.value ? " selected" : ""}>${esc(o)}</option>`).join("")}</select>`;
  });
  const extra = info.extra.map((e) => `${e.section}.${e.key}`).join(", ");
  const values = await openDialog(
    `<h3>${esc(t("dlg.settings.title"))}</h3><div class="msg small">${esc(t("dlg.settings.hint"))}</div>` +
    `<div class="form-grid">${rows.join("")}</div>` +
    (extra ? `<div class="msg small">${esc(t("dlg.settings.extra", { list: extra }))}</div>` : "") +
    actionsHtml(t("dlg.save")),
    (form) => {
      const out = {};
      info.settings.forEach((s, i) => {
        const v = form[`s${i}`].value;
        if (s.present || v !== s.value) out[`${s.section}.${s.key}`] = v; // don't add untouched defaults
      });
      return out;
    },
  );
  if (!values) return;
  await run("st.saving", null, async () => {
    await sdWriteText(ok(await rpc("sdWriteSettings", [values])));
  });
}

async function sdGame2Folder() {
  await loadGameDb();
  const foldersOf = (platform) => [...new Set(sd.data.variants
    .filter((v) => (platform === "PS1" ? v.name.toUpperCase() === "PS1" : v.name.toUpperCase() !== "PS1"))
    .flatMap((v) => v.folders.map((f) => f.folder)))];
  // where game switching is off, these rules have no effect: say so
  const off = ["PS2", "PS1"].filter((c) =>
    sd.data.settings.settings.some((s) => s.section === c && s.key === "GameID" && s.value === "OFF"));
  const row = (r = { platform: "PS2", game: "", folder: "" }) =>
    `<div class="r"><select name="p">${["PS2", "PS1"].map((x) => `<option${x === r.platform ? " selected" : ""}>${x}</option>`).join("")}</select>` +
    `<div class="gcell"><input type="text" name="g" class="mono" value="${esc(r.game)}" placeholder="SLUS-20963" autocomplete="off">` +
    `<span class="gname">${esc(gameName(normalizeGameId(r.game)) || "")}</span></div>` +
    `<input type="text" name="f" value="${esc(r.folder)}" list="sdFolders${r.platform === "PS1" ? "PS1" : "PS2"}" placeholder="Card1" autocomplete="off">` +
    `<button type="button" class="rm" title="✕">×</button></div>`;
  const rows = sd.data.game2folder.length ? sd.data.game2folder : [undefined];
  const datalist = (id, list) => `<datalist id="${id}">${list.map((f) => `<option value="${esc(f)}">`).join("")}</datalist>`;
  const pr = openDialog(
    `<h3>${esc(t("dlg.g2f.title"))}</h3>` +
    `<div class="msg small">${esc(t("dlg.g2f.hint"))}</div>` +
    `<div class="msg small">${esc(t("dlg.g2f.example", { game: gameName("SLUS-20963") || t("dlg.g2f.exampleGame") }))}</div>` +
    (off.length ? `<div class="notebox">${esc(t("dlg.g2f.gameIdOff", { consoles: off.join(", ") }))}</div>` : "") +
    `<div class="rows-table" id="g2fRows"><div class="r h"><span>${esc(t("dlg.g2f.console"))}</span><span>${esc(t("dlg.g2f.gameId"))}</span><span>${esc(t("dlg.g2f.folder"))}</span><span></span></div>` +
    rows.map(row).join("") + `</div>` +
    datalist("sdFoldersPS2", foldersOf("PS2")) + datalist("sdFoldersPS1", foldersOf("PS1")) +
    `<div><button type="button" class="btn" id="g2fAdd">${esc(t("dlg.g2f.add"))}</button></div>` +
    `<div class="err" id="dErr"></div>` + actionsHtml(t("dlg.save")),
    (form) => {
      const out = [];
      for (const r of form.querySelectorAll("#g2fRows .r:not(.h)")) {
        const game = r.querySelector("[name=g]").value.trim();
        const folder = r.querySelector("[name=f]").value.trim();
        if (!game && !folder) continue;
        if (!GAME_ID_RE.test(game) || !folder) { form.querySelector("#dErr").textContent = t("sd.badGameId"); return false; }
        out.push({ platform: r.querySelector("[name=p]").value, game, folder });
      }
      return out;
    },
  );
  // dynamic rows (the form is in the DOM as soon as openDialog returns)
  const box = dform.querySelector("#g2fRows");
  dform.querySelector("#g2fAdd").onclick = () => box.insertAdjacentHTML("beforeend", row());
  box.onclick = (ev) => { if (ev.target.classList.contains("rm")) ev.target.closest(".r").remove(); };
  box.addEventListener("input", (ev) => {
    if (ev.target.name === "g") ev.target.nextElementSibling.textContent = gameName(normalizeGameId(ev.target.value)) || "";
  });
  box.addEventListener("change", (ev) => {
    if (ev.target.name === "p") ev.target.closest(".r").querySelector("[name=f]").setAttribute("list", `sdFolders${ev.target.value}`);
  });
  const result = await pr;
  if (!result) return;
  await run("st.saving", null, async () => {
    await sdWriteText(ok(await rpc("sdWriteGame2Folder", [result])));
  });
}

// ---------------------------------------------------------------------------
// Phase 4: whole cards (import / convert / split by game)

const isCardFile = (f) => isCardLike(f.rel, f.data.byteLength);

// "Import save": save files go through importSaves, card images through importCards
async function importFiles(p, files) {
  files = files.filter((f) => !f.dir);
  const cards = files.filter(isCardFile);
  const saves = files.filter((f) => !isCardFile(f));
  if (saves.length && !p.summary) toast(t("dlg.cards.mergeNone"), "error");
  if (saves.length && p.summary) await importSaves(p, saves);
  if (cards.length) await importCards(p, cards);
}

const canWriteSd = () => !!sd && !sd.readOnly && !!sd.data;

async function importCards(p, files) {
  let info = null;
  await run("st.reading", null, async () => { info = ok(await rpc("inspectCards", [files])).cards; });
  if (!info) return;
  const good = info.filter((c) => c.ok);
  const bad = info.filter((c) => !c.ok);
  if (!good.length) {
    await alertDialog(t("dlg.cards.title"), t("dlg.cards.none") + "\n\n" + bad.map((b) => `• ${b.file}: ${b.error}`).join("\n"));
    return;
  }
  const platforms = [...new Set(good.map((c) => c.platform))];
  const mixMerge = !!p.summary && platforms.some((x) => x !== p.summary.card.platform);
  const canMerge = !!p.summary && !mixMerge && !p.summary.card.readOnly;
  const canSd = canWriteSd();
  const def = canSd ? "sd" : canMerge ? "merge" : "zip";
  const items = good.map((c, i) => {
    const titles = c.entries.map((e) => e.title || e.name).slice(0, 4).join(" · ");
    return `<li><div class="t">${esc(c.file)}</div>` +
      `<div class="m">${esc(c.describe)} · ${esc(t("dlg.cards.saves", { n: c.entries.length }))}</div>` +
      (titles ? `<div class="titles">${esc(titles)}</div>` : "") +
      `<label>${esc(t("dlg.cards.game"))}<input type="text" name="g${i}" class="mono" value="${esc(c.game || "")}" placeholder="SLUS-20228" autocomplete="off" data-game-input>` +
      `<span class="gname">${esc(gameName(c.game) || "")}</span></label></li>`;
  }).join("");
  const opt = (v, title, hint, enabled) =>
    `<label><input type="radio" name="how" value="${v}"${v === def ? " checked" : ""}${enabled ? "" : " disabled"}><b>${esc(title)}</b><span>${esc(hint)}</span></label>`;
  await loadGameDb();
  const pr = openDialog(
    `<h3>${esc(t("dlg.cards.title"))}</h3><ul class="card-list">${items}</ul>` +
    (bad.length ? `<div class="msg small">${esc(t("dlg.cards.bad"))} ${esc(bad.map((b) => b.file).join(", "))}</div>` : "") +
    `<div class="choice">` +
    opt("merge", t("dlg.cards.merge", { slot: p.slot }), canMerge ? t("dlg.cards.mergeHint", { name: p.summary.card.name })
      : mixMerge ? t("dlg.cards.mixMerge", { platform: platforms.join("/") }) : p.summary?.card.readOnly ? t("toast.readOnly") : t("dlg.cards.mergeNone"), canMerge) +
    opt("sd", t("dlg.cards.sd"), canSd ? t("dlg.cards.sdHint") : t("dlg.cards.sdNone"), canSd) +
    opt("zip", t("dlg.cards.zip"), t("dlg.cards.zipHint"), true) +
    `</div><div class="err" id="dErr"></div>` + actionsHtml(t("dlg.cards.go")),
    (f) => {
      const how = f.how.value;
      const games = good.map((_, i) => f[`g${i}`].value.trim());
      if (how !== "merge" && games.some((g) => !GAME_ID_RE.test(g))) {
        f.querySelector("#dErr").textContent = t("dlg.cards.badId");
        return false;
      }
      return { how, games };
    },
  );
  // show the game title as the code is typed
  dform.querySelectorAll("[data-game-input]").forEach((input) => input.addEventListener("input", () => {
    input.nextElementSibling.textContent = gameName(normalizeGameId(input.value)) || "";
  }));
  const choice = await pr;
  if (!choice) return;
  const names = good.map((c) => c.file);
  if (choice.how === "merge") {
    await run("st.importing", null, async () => {
      const r = await withOverwrite((ow) => rpc("importCards", [p.slot, names, ow]));
      if (!r) { status("st.cancelled"); return; }
      applySummary(p, r);
      toast(t("toast.cardsMerged", { slot: p.slot, list: names.join(", ") }), "ok");
      status("st.added");
    });
  } else if (choice.how === "sd") {
    await run("st.importing", null, async () => {
      const done = [];
      for (let i = 0; i < good.length; i++) {
        const variant = good[i].platform === "PS1" ? "PS1" : "PS2";
        const plan = ok(await rpc("sdPlanImport", [choice.games[i], good[i].size, variant]));
        const card = ok(await rpc("prepareStagedCard", [good[i].file]));
        await sdWrite(plan.path, card.data);
        sd.expanded.add(`${variant}/${plan.folder}`);
        done.push(plan.path + (plan.existing ? " " + t("toast.newChannel", { n: plan.channel }) : ""));
      }
      await sdRefresh();
      toast(t("toast.cardsSd", { list: done.join("\n") }), "ok");
    });
  } else {
    await run("st.converting", null, async () => {
      const r = ok(await rpc("stagedCardsZip", [good.map((c, i) => ({ file: c.file, game: choice.games[i] })), "gen2"]));
      download(r.name, r.data, "application/zip");
      status("st.extracted", { name: r.name, size: human(r.size) });
    });
  }
}

const CONVERT_TARGETS = ["gen2", "opl", "pcsx2", "mcp2"];
// name OPL gives a game's virtual card: SLUS-20228 -> SLUS_202.28_0.bin
const oplVmcName = (game) => (game ? `${game.slice(0, 4)}_${game.slice(5, 8)}.${game.slice(8, 10)}_0.bin` : null);
const TARGET_EXT = { gen2: ".mcd", opl: ".bin", pcsx2: ".ps2", mcp2: ".mc2" };

async function actConvertPs1(p) {
  const c = p.summary.card;
  const current = c.container === "raw" ? (c.originId === "epsxe" ? "mcr" : c.originId === "retroarch" ? "srm" : "gen2") : c.container;
  const def = current === "gen2" ? "vmp" : "gen2";
  const opt = (v) =>
    `<label><input type="radio" name="fmt" value="${v}"${v === def ? " checked" : ""}><b>${esc(t(`dlg.convert.ps1.${v}`))}</b><span>${esc(t(`dlg.convert.ps1.${v}Hint`))}</span></label>`;
  const pr = openDialog(
    `<h3>${esc(t("dlg.convert.title"))}</h3>` +
    `<div class="choice">${PS1_TARGETS.map(opt).join("")}</div>` +
    `<div class="msg small">${esc(t("dlg.convert.ps1note"))}</div>` +
    `<label>${esc(t("dlg.convert.file"))}<input type="text" name="file" value="${esc(withExt(c.name, PS1_EXT[def]))}" autocomplete="off"></label>` +
    actionsHtml(t("dlg.convert.go")),
    (f) => ({ target: f.fmt.value, file: f.file.value.trim() || withExt(c.name, PS1_EXT[f.fmt.value]) }),
  );
  dform.querySelectorAll("input[name=fmt]").forEach((r) => r.addEventListener("change", () => {
    const input = dform.querySelector("input[name=file]");
    input.value = withExt(input.value || c.name, PS1_EXT[r.value]);
  }));
  const v = await pr;
  if (!v) return;
  await run("st.converting", null, async () => {
    const r = ok(await rpc("convertCard", [p.slot, v.target, 0]));
    download(v.file, r.data);
    toast(t("toast.converted", { name: v.file, size: human(r.size) }), "ok");
    status("st.extracted", { name: v.file, size: human(r.size) });
  });
}

async function actConvert(p = P()) {
  if (!p.summary) return;
  if (isPs1(p)) return actConvertPs1(p);
  const c = p.summary.card;
  const current = c.originId === "pcsx2" ? "pcsx2" : c.originId;
  const def = current === "gen2" ? "pcsx2" : "gen2";
  const stem = c.name.replace(/\.[^.]+$/, "");
  const fileFor = (target, current) =>
    target === "opl" && oplVmcName(c.game) ? oplVmcName(c.game) : current.replace(/\.[^.]*$/, "") + TARGET_EXT[target];
  const opt = (v) =>
    `<label><input type="radio" name="fmt" value="${v}"${v === def ? " checked" : ""}><b>${esc(t(`dlg.convert.${v}`))}</b><span>${esc(t(`dlg.convert.${v}Hint`))}</span></label>`;
  const pr = openDialog(
    `<h3>${esc(t("dlg.convert.title"))}</h3>` +
    `<div class="choice">${CONVERT_TARGETS.map(opt).join("")}</div>` +
    `<label>${esc(t("dlg.convert.size"))}<select name="size"><option value="0">${esc(t("dlg.convert.same", { n: c.sizeMB }))}</option>` +
    [1, 2, 4, 8, 16, 32, 64].filter((m) => m !== c.sizeMB).map((m) => `<option value="${m}">${m} MB</option>`).join("") + `</select></label>` +
    `<div class="msg small">${esc(t("dlg.convert.used", { used: human(c.used) }))}</div>` +
    `<label>${esc(t("dlg.convert.file"))}<input type="text" name="file" value="${esc(fileFor(def, c.name))}" autocomplete="off"></label>` +
    actionsHtml(t("dlg.convert.go")),
    (f) => ({ target: f.fmt.value, size: +f.size.value, file: f.file.value.trim() || stem + TARGET_EXT[f.fmt.value] }),
  );
  // keep the file extension in sync with the chosen format
  dform.querySelectorAll("input[name=fmt]").forEach((r) => r.addEventListener("change", () => {
    const input = dform.querySelector("input[name=file]");
    // OPL names its cards after the game (SLUS_202.28_0.bin); otherwise keep the name, change the extension
    input.value = fileFor(r.value, oplVmcName(c.game) && input.value === oplVmcName(c.game) ? stem + ".mcd" : input.value);
  }));
  const v = await pr;
  if (!v) return;
  await run("st.converting", null, async () => {
    const r = ok(await rpc("convertCard", [p.slot, v.target, v.size]));
    download(v.file, r.data);
    toast(t("toast.converted", { name: v.file, size: human(r.size) }), "ok");
    status("st.extracted", { name: v.file, size: human(r.size) });
  });
}

async function actSplit(p = P()) {
  if (!p.summary) return;
  let prev = null;
  await run("st.reading", null, async () => { prev = ok(await rpc("splitPreview", [p.slot])); });
  if (!prev) return;
  const ps1 = isPs1(p);
  if (!prev.games.length) { toast(t(ps1 ? "toast.noGamesPs1" : "toast.noGames"), "error"); return; }
  const canSd = canWriteSd();
  await loadGameDb();
  const list = prev.games.map((g) => `<li><div class="t">${esc(g.game)} <span class="split-game">${esc(gameName(g.game) || "")}</span></div><div class="titles">${esc(g.titles.join(" · "))}</div></li>`).join("");
  const opt = (v, title, hint, enabled, checked) =>
    `<label><input type="radio" name="dest" value="${v}"${checked ? " checked" : ""}${enabled ? "" : " disabled"}><b>${esc(title)}</b><span>${esc(hint)}</span></label>`;
  const v = await openDialog(
    `<h3>${esc(t("dlg.split.title"))}</h3><div class="msg small">${esc(t("dlg.split.games", { n: prev.games.length }))}</div>` +
    `<ul class="card-list">${list}</ul>` +
    (prev.others.length ? `<label class="inline"><input type="checkbox" name="others"> ${esc(t("dlg.split.others", { list: prev.others.join(", ") }))}</label>` : "") +
    (ps1 ? `<div class="msg small">${esc(t("dlg.split.ps1size"))}</div>` :
      `<label>${esc(t("dlg.split.size"))}<select name="size">${[1, 2, 4, 8, 16, 32, 64].map((m) => `<option value="${m}"${m === 8 ? " selected" : ""}>${m} MB</option>`).join("")}</select></label>`) +
    `<div class="choice">` +
    opt("sd", t("dlg.split.sd"), canSd ? t(ps1 ? "dlg.split.sdHintPs1" : "dlg.split.sdHint") : t("dlg.cards.sdNone"), canSd, canSd) +
    opt("zip", t("dlg.split.zip"), t(ps1 ? "dlg.split.zipHintPs1" : "dlg.split.zipHint"), true, !canSd) +
    (ps1 ? "" : opt("zip-opl", t("dlg.split.opl"), t("dlg.split.oplHint"), true, false)) +
    `</div>` + actionsHtml(t("dlg.split.go")),
    (f) => ({ dest: f.dest.value, size: ps1 ? 0 : +f.size.value, others: !!f.others?.checked }),
  );
  if (!v) return;
  await run("st.splitting", null, async () => {
    if (v.dest === "zip" || v.dest === "zip-opl") {
      const r = ok(await rpc("splitCard", [p.slot, v.size, v.others, v.dest]));
      download(r.name, r.data, "application/zip");
      status("st.extracted", { name: r.name, size: human(r.size) });
      return;
    }
    const r = ok(await rpc("splitCard", [p.slot, v.size, v.others, "files"]));
    const done = [];
    const variant = ps1 ? "PS1" : "PS2";
    for (const c of r.cards) {
      const plan = ok(await rpc("sdPlanImport", [c.game, ps1 ? PS1_SIZE : v.size * 1048576, variant]));
      const file = ok(await rpc("readFile", [c.path]));
      await sdWrite(plan.path, file.data);
      sd.expanded.add(`${variant}/${plan.folder}`);
      done.push(plan.path + (plan.existing ? " " + t("toast.newChannel", { n: plan.channel }) : ""));
    }
    await sdRefresh();
    toast(t("toast.cardsSd", { list: done.join("\n") }), "ok");
  });
}

// ---------------------------------------------------------------------------
// Game titles by code (from PCSX2's GameIndex), loaded once, on demand

let gameDb = null;
let gameDbLoading = null;

function loadGameDb() {
  if (gameDb) return Promise.resolve(gameDb);
  if (!gameDbLoading) {
    gameDbLoading = fetch(`gamedb.json?v=${BUILD}`)
      .then((r) => (r.ok ? r.json() : {}))
      .catch(() => ({}))
      .then((d) => { gameDb = d; render(); return d; });
  }
  return gameDbLoading;
}

const gameName = (code) => (gameDb && code ? gameDb[String(code).toUpperCase()] || null : null);

// "slus_202.28" / "SLUS20228" -> "SLUS-20228" (same rule as the Python core)
function normalizeGameId(text) {
  const m = /^([A-Z]{4})[-_ ]?(\d{3})\.?(\d{2})$/.exec(String(text).trim().toUpperCase());
  return m ? `${m[1]}-${m[2]}${m[3]}` : null;
}

// ---------------------------------------------------------------------------
// Resize the open card (undoable; Save writes it back, also to the SD card)

async function actResize(p = P()) {
  if (!p.summary) return;
  const c = p.summary.card;
  const sizes = [1, 2, 4, 8, 16, 32, 64];
  const fits = (m) => c.used < m * 1048576 * 0.97; // a little room for the file system itself
  const pr = openDialog(
    `<h3>${esc(t("dlg.resize.title"))}</h3>` +
    `<div class="msg">${esc(t("dlg.resize.current", { n: c.sizeMB, used: human(c.used) }))}</div>` +
    `<label>${esc(t("dlg.resize.size"))}<select name="size">` +
    sizes.filter((m) => m !== c.sizeMB).map((m) =>
      `<option value="${m}"${fits(m) ? "" : " disabled"}${m === (c.sizeMB < 8 ? 8 : Math.min(64, c.sizeMB * 2)) ? " selected" : ""}>${m} MB${fits(m) ? "" : " " + esc(t("dlg.resize.noFit"))}</option>`).join("") +
    `</select></label>` +
    `<div class="warnbox" id="sizeWarn" hidden></div>` +
    `<div class="msg small">${esc(t("dlg.resize.note"))}</div>` + actionsHtml(t("dlg.resize.go")),
    (f) => +f.size.value,
  );
  // larger than 8 MB: warn (more strongly for a boot card)
  const isBoot = /\/BOOT\//i.test(p.sdPath || "") || /^BootCard/i.test(c.name);
  const sel = dform.querySelector("select[name=size]");
  const warn = () => {
    const box = dform.querySelector("#sizeWarn");
    const big = +sel.value > 8;
    box.hidden = !big;
    box.textContent = big ? (isBoot ? t("dlg.resize.warnBoot") + " " : "") + t("dlg.resize.warnBig") : "";
  };
  sel.addEventListener("change", warn);
  warn();
  const v = await pr;
  if (!v) return;
  await run("st.resizing", null, async () => {
    applySummary(p, ok(await rpc("resizeCard", [p.slot, v])));
    toast(t("toast.resized", { n: v }), "ok");
    status("toast.resized", { n: v });
  });
}

// ---------------------------------------------------------------------------
// New versions: version.json is never cached; when it names another build,
// reload into it (automatically if nothing is open, otherwise on request).

let updateTo = null;

async function checkForUpdate() {
  if (BUILD.startsWith("__")) return; // not a built site (development)
  try {
    const r = await fetch(`version.json?t=${Date.now()}`, { cache: "no-store" });
    if (!r.ok) return;
    const { build } = await r.json();
    if (build && build !== BUILD) offerUpdate(build);
  } catch { /* offline: try again later */ }
}

function reloadInto(build) {
  // a new URL also skips a cached copy of the HTML itself
  location.replace(`${location.pathname}?v=${encodeURIComponent(build)}`);
}

function offerUpdate(build) {
  updateTo = build;
  const nothingOpen = !SLOTS.some((s) => panes[s].summary) && !sd;
  // reload automatically at most once per build: if a cache still serves the
  // old page after that, don't loop; just show the bar
  const tried = new URLSearchParams(location.search).get("v") === build || storage.get("psmm-update-tried") === build;
  if (nothingOpen && !state.busy && !dialog.open && !tried) {
    storage.set("psmm-update-tried", build);
    reloadInto(build);
    return;
  }
  $("#updateBar").hidden = false;
}

$("#updateBtn").addEventListener("click", async () => {
  if (!updateTo) return;
  const dirty = SLOTS.some((s) => panes[s].summary?.dirty);
  if (dirty && !(await confirmDialog(t("dlg.unsaved.title"), t("update.dirty"), t("update.reload"), true))) return;
  window.removeEventListener("beforeunload", warnUnsaved);
  reloadInto(updateTo);
});

document.addEventListener("visibilitychange", () => { if (!document.hidden) checkForUpdate(); });
setInterval(checkForUpdate, 10 * 60 * 1000);

// ---------------------------------------------------------------------------
// Theme

const THEMES = ["auto", "light", "dark"];
let theme = storage.get("psmm-theme", "auto");
if (!THEMES.includes(theme)) theme = "auto";
function applyTheme() {
  if (theme === "auto") document.documentElement.removeAttribute("data-theme");
  else document.documentElement.dataset.theme = theme;
  const btn = $("#themeBtn");
  btn.innerHTML = svg(theme === "auto" ? "auto" : theme === "light" ? "sun" : "moon");
  btn.title = t(`theme.${theme}`);
}
$("#themeBtn").addEventListener("click", () => {
  theme = THEMES[(THEMES.indexOf(theme) + 1) % THEMES.length];
  storage.set("psmm-theme", theme);
  applyTheme();
});

// ---------------------------------------------------------------------------
// Language

const langSel = $("#langSel");
langSel.innerHTML = Object.entries(LANGS).map(([k, v]) => `<option value="${k}">${esc(v)}</option>`).join("");

function applyLanguage() {
  translateDom();
  langSel.value = getLang();
  applyTheme();
  $("#status").textContent = t(statusMsg.key, statusMsg.params);
  if (engineError) engineFailed(engineError);
  else if (state.ready) $("#engineText").textContent = t("engine.ready", { version: state.python });
  else {
    $("#engineText").textContent = t(loadStep);
    $("#engine").title = t("load.cache");
    if (!state.busy && statusMsg.key === "st.loading") status("st.loading", { step: t(loadStep) });
  }
  render();
}

async function changeLanguage(lang) {
  setLang(lang, true);
  applyLanguage();
  if (!state.ready) return;
  await rpc("setLang", [getLang()]);
  if (state.busy) return;
  for (const slot of SLOTS) {
    const p = panes[slot];
    if (p.summary) applySummary(p, ok(await rpc("summary", [slot]))); // core texts (format, regions…)
  }
}
langSel.addEventListener("change", () => changeLanguage(langSel.value));

function warnUnsaved(ev) {
  if (SLOTS.some((s) => panes[s].summary?.dirty)) { ev.preventDefault(); ev.returnValue = ""; }
}
window.addEventListener("beforeunload", warnUnsaved);

// ---------------------------------------------------------------------------
// Start

for (const slot of SLOTS) panes[slot] = makePane(slot);
setLang(detectLang());
paintIcons();
status("st.loading", { step: t(loadStep) });
applyLanguage();
rpc("ready").then(async (info) => {
  await rpc("setLang", [getLang()]);
  state.ready = true;
  state.python = info.python;
  $("#engine").classList.add("ready");
  $("#engine").title = t("engine.title");
  $("#engineText").textContent = t("engine.ready", { version: info.python });
  if (!state.busy) status("st.readyOpen"); // an action started while loading sets its own status
  engineReadyOk();
  updateActions();
  checkForUpdate();
}).catch((e) => engineFailed(e.message));
