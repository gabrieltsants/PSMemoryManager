// This file is part of PSMemoryManager.
// SPDX-License-Identifier: GPL-3.0-or-later
//
// Web Worker: loads Pyodide + mymc++ + the psmm core and serves requests from
// the page. Everything runs locally in the browser; no file leaves the PC.

const PYODIDE_VERSION = "0.27.2";
// tools/build_site.py --offline sets this to true: the local app ships Pyodide
// next to the page, so it works without internet
const PYODIDE_LOCAL = false;
const PYODIDE_URL = PYODIDE_LOCAL
  ? new URL("pyodide/", self.location.href).href
  : `https://cdn.jsdelivr.net/pyodide/v${PYODIDE_VERSION}/full/`;
const BUILD = "__BUILD__"; // filled in by tools/build_site.py

importScripts(PYODIDE_URL + "pyodide.js");

let py = null;
let api = null;

function progress(step) {
  self.postMessage({ type: "progress", step });
}

async function boot() {
  progress("load.pyodide");
  py = await loadPyodide({ indexURL: PYODIDE_URL });

  progress("load.mymc");
  const manifest = await (await fetch(`py/manifest.json?v=${BUILD}`, { cache: "no-cache" })).json();
  const wheel = await (await fetch(`${manifest.wheel}?v=${BUILD}`)).arrayBuffer();
  py.unpackArchive(wheel, "wheel");

  progress("load.core");
  for (const rel of manifest.files) {
    const src = await (await fetch(`py/${rel}?v=${BUILD}`, { cache: "no-cache" })).text();
    const dest = "/home/pyodide/" + rel;
    py.FS.mkdirTree(dest.slice(0, dest.lastIndexOf("/")));
    py.FS.writeFile(dest, src);
  }
  py.runPython("import sys; sys.path.insert(0, '/home/pyodide')");
  api = py.pyimport("psmm.web_api");
  py.FS.mkdirTree("/psmm");
  return { version: manifest.version, python: py.runPython("import sys; sys.version.split()[0]") };
}

const ready = boot();

function call(fn, ...args) {
  return JSON.parse(api[fn](...args));
}

// files: [{rel, data?: ArrayBuffer, dir?: true}] -> written under the staging folder
function stage(files) {
  const root = api.staging_dir();
  for (const f of files) {
    const dest = root + "/" + f.rel;
    py.FS.mkdirTree(dest.slice(0, dest.lastIndexOf("/")));
    if (f.dir) py.FS.mkdirTree(dest);
    else py.FS.writeFile(dest, new Uint8Array(f.data));
  }
}

// reads a file produced by Python and hands it to the page without copying again
function takeFile(r, remove = false) {
  if (!r.ok) return r;
  const data = py.FS.readFile(r.path); // Uint8Array (a copy)
  if (remove) py.FS.unlink(r.path);
  return { ...r, data: data.buffer, transfer: [data.buffer] };
}

const handlers = {
  ready: async () => ready,
  setLang: async (lang) => call("set_language", lang),

  open: async (slot, name, buffer) => {
    py.FS.writeFile("/psmm/incoming.bin", new Uint8Array(buffer));
    return call("open_card", slot, name);
  },
  newCard: async (slot, name, sizeMB, ecc, platform) => call("new_card", slot, name, sizeMB, ecc, platform || "PS2"),
  closeCard: async (slot) => call("close_card", slot),
  summary: async (slot) => call("summary", slot),
  icons: async (slot, paths) => call("icons", slot, JSON.stringify(paths)),

  add: async (slot, files, destDir, overwrite) => {
    stage(files);
    return call("add_staged", slot, destDir, !!overwrite);
  },
  mkdir: async (slot, path) => call("mkdir", slot, path),
  remove: async (slot, paths) => call("remove", slot, JSON.stringify(paths)),
  rename: async (slot, path, newName) => call("rename", slot, path, newName),
  restore: async (slot, paths) => call("restore", slot, JSON.stringify(paths)),
  copy: async (src, paths, dst, destDir, overwrite) =>
    call("copy_items", src, JSON.stringify(paths), dst, destDir, !!overwrite),
  check: async (slot) => call("check", slot),
  undo: async (slot) => call("undo", slot),
  markSaved: async (slot) => call("mark_saved", slot),

  inspectSaves: async (files, platform) => {
    stage(files);
    return call("inspect_staged_saves", platform || "PS2");
  },
  // files == null: reuse what is already staged (after inspectSaves)
  importSaves: async (slot, files, overwrite) => {
    if (files) stage(files);
    return call("import_staged_saves", slot, !!overwrite);
  },
  exportSaves: async (slot, paths, fmt) => takeFile(call("export_saves", slot, JSON.stringify(paths), fmt), true),
  export: async (slot, paths) => takeFile(call("export", slot, JSON.stringify(paths)), true),
  cardBytes: async (slot) => takeFile(call("card_file", slot)),

  // Gen2 SD card: the page does the file access, Python the layout/INI logic
  sdLoad: async (files, texts) => call("sd_load", JSON.stringify(files), JSON.stringify(texts)),
  // one card of the SD, for the "All saves" view (the file is removed after reading)
  sdIndexCard: async (buffer) => {
    py.FS.writeFile("/psmm/index.bin", new Uint8Array(buffer));
    return call("sd_index_card");
  },
  sdWriteSettings: async (values) => call("sd_write_settings", JSON.stringify(values)),
  sdWriteChannelNames: async (iniPath, names) => call("sd_write_channel_names", iniPath, JSON.stringify(names)),
  sdRemoveChannelName: async (iniPath, channel) => call("sd_remove_channel_name", iniPath, channel),
  sdWriteGame2Folder: async (rows) => call("sd_write_game2folder", JSON.stringify(rows)),
  sdPlanCard: async (variant, gameId) => call("sd_plan_card", variant, gameId || ""),
  sdPlanChannel: async (variant, folder) => call("sd_plan_channel", variant, folder),
  blankCard: async (sizeMB, platform) => takeFile(call("blank_card", sizeMB, false, platform || "PS2"), true),

  // whole cards: import (OPL VMCs...), convert, split by game
  inspectCards: async (files) => {
    stage(files);
    return call("inspect_staged_cards");
  },
  importCards: async (slot, names, overwrite) => call("import_staged_cards", slot, JSON.stringify(names), !!overwrite),
  prepareStagedCard: async (name) => takeFile(call("prepare_staged_card", name), true),
  stagedCardsZip: async (items, layout) => takeFile(call("staged_cards_zip", JSON.stringify(items), layout || "gen2"), true),
  sdPlanImport: async (game, size, variant) => call("sd_plan_import", game, size, variant || "PS2"),
  convertCard: async (slot, target, sizeMB) => takeFile(call("convert_card", slot, target, sizeMB), true),
  splitPreview: async (slot) => call("split_preview", slot),
  resizeCard: async (slot, sizeMB) => call("resize_card", slot, sizeMB),
  splitCard: async (slot, sizeMB, withOthers, mode) => {
    const r = call("split_card", slot, sizeMB, !!withOthers, mode);
    return mode.startsWith("zip") ? takeFile(r, true) : r;
  },
  readFile: async (path) => takeFile({ ok: true, path }, true),
};

self.onmessage = async (ev) => {
  const { id, op, args } = ev.data;
  try {
    if (op !== "ready") await ready;
    const result = await handlers[op](...(args || []));
    const transfer = (result && result.transfer) || [];
    if (result && result.transfer) delete result.transfer;
    self.postMessage({ type: "reply", id, ok: true, result }, transfer);
  } catch (err) {
    self.postMessage({ type: "reply", id, ok: false, error: String((err && err.message) || err) });
  }
};
