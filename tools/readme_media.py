#!/usr/bin/env python3
# This file is part of PSMemoryManager.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Regenerates the README screenshots and GIF (docs/img/).

    python tools/build_site.py && python -m http.server -d _site 8765 &
    python tools/readme_media.py --url http://127.0.0.1:8765/ --sd DEMO_SD [--vmc A.bin B.bin]

DEMO_SD is the root of a Gen2 SD card folder to show (it is copied into the
browser's private storage; the folder itself is never modified). Needs
Playwright (pip install playwright) and ffmpeg for the GIF.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parent.parent / "docs" / "img"
VIEW = {"width": 1280, "height": 760}

MOUNT_SD = """async () => {
  const opfs = await navigator.storage.getDirectory();
  try { await opfs.removeEntry('SDCARD', { recursive: true }); } catch {}
  const root = await opfs.getDirectoryHandle('SDCARD', { create: true });
  for (const f of document.getElementById('sdIn').files) {
    const parts = f.webkitRelativePath.split('/').slice(1);
    let d = root;
    for (const x of parts.slice(0, -1)) d = await d.getDirectoryHandle(x, { create: true });
    const w = await (await d.getFileHandle(parts.at(-1), { create: true })).createWritable();
    await w.write(f); await w.close();
  }
  window.showDirectoryPicker = async () => root;
}"""


def open_page(browser, url, sd, scheme="light"):
    ctx = browser.new_context(viewport=VIEW, locale="en-US", color_scheme=scheme, device_scale_factor=1)
    pg = ctx.new_page()
    pg.goto(url)
    pg.wait_for_selector("#engine.ready", timeout=120000)
    pg.evaluate("""() => { const i = document.createElement('input'); i.type = 'file'; i.id = 'sdIn';
                           i.webkitdirectory = true; i.hidden = true; document.body.append(i); }""")
    pg.set_input_files("#sdIn", sd)
    pg.evaluate(MOUNT_SD)
    pg.click('.toolbar [data-act="sd"]')
    pg.wait_for_selector("#sdbar .sd-ch")
    pg.wait_for_function("[...document.querySelectorAll('#sdbar .gname')].some(e => e.textContent)")
    return pg


def quiet(pg):
    """No toasts or hover effects in the pictures."""
    pg.evaluate("document.querySelectorAll('.toast').forEach(t => t.remove())")
    pg.mouse.move(2, VIEW["height"] - 2)


def channel(path):
    return f'#sdbar .sd-ch[data-path="{path}"]'


def hero(browser, url, sd, scheme):
    pg = open_page(browser, url, sd, scheme)
    pg.click(channel("MemoryCards/PS2/BOOT/BootCard-1.mcd"))
    pg.wait_for_selector('.pane[data-slot="A"] .row[data-path="/OPL"]')
    pg.click('.pane[data-slot="A"] .row[data-path="/BAEXEC-SYSTEM"]')
    quiet(pg)
    pg.screenshot(path=OUT / f"hero-{scheme}.png")
    pg.context.close()


def dialogs(browser, url, sd, vmc):
    pg = open_page(browser, url, sd)
    pg.click(channel("MemoryCards/PS2/SLUS-20312/SLUS-20312-1.mcd"))
    pg.wait_for_selector('.pane[data-slot="A"] .row')
    pg.click('.pane[data-slot="A"] .row >> nth=0')
    if vmc:
        with pg.expect_file_chooser() as fc:
            pg.click('.toolbar [data-act="importSave"]')
        fc.value.set_files(vmc)
        pg.wait_for_selector("dialog[open] .card-list")
        pg.check("dialog input[value=sd]")
        quiet(pg)
        pg.screenshot(path=OUT / "import-opl.png")
        pg.click("dialog button[value=cancel]")
    pg.click('.toolbar [data-act="convert"]')
    pg.wait_for_selector("dialog[open]")
    pg.check("dialog input[value=pcsx2]")
    quiet(pg)
    pg.screenshot(path=OUT / "convert.png")
    pg.click("dialog button[value=cancel]")
    pg.click('#sdbar [data-sd="g2f"]')
    pg.wait_for_selector("dialog[open] #g2fRows")
    quiet(pg)
    pg.screenshot(path=OUT / "folder-per-game.png")
    pg.context.close()


def dual_gif(browser, url, sd):
    """Drag a save from one card to the other, captured frame by frame."""
    pg = open_page(browser, url, sd)
    pg.click('.toolbar [data-act="dual"]')
    pg.click(channel("MemoryCards/PS2/BOOT/BootCard-2.mcd"))
    pg.wait_for_selector('.pane[data-slot="A"] .row[data-path="/OPL"]')
    pg.click('.pane[data-slot="B"] .pane-empty')
    pg.click(channel("MemoryCards/PS2/Card1/Card1-2.mcd"))
    pg.wait_for_selector('.pane[data-slot="B"] .tree-empty')
    quiet(pg)
    frames = Path(tempfile.mkdtemp())
    n = 0

    def snap(repeat=1):
        nonlocal n
        for _ in range(repeat):
            pg.screenshot(path=frames / f"{n:03d}.png")
            n += 1

    # headless browsers draw neither the pointer nor the dragged item: fake both
    pg.evaluate("""() => {
      const c = document.createElement('div');
      c.id = 'fakeCursor';
      c.style.cssText = 'position:fixed;z-index:999;pointer-events:none;left:-50px;top:-50px;display:flex;align-items:flex-start;gap:4px';
      c.innerHTML = '<svg width="22" height="22" viewBox="0 0 24 24"><path d="M5 3l14 8-6 1.6L10 19z" fill="#111" stroke="#fff" stroke-width="1.5"/></svg>' +
        '<span id="fakeGhost" style="display:none;margin-top:14px;padding:3px 9px;border-radius:7px;background:#2f6fed;color:#fff;font:600 13px system-ui">OPL</span>';
      document.body.append(c);
      window.__cursor = (x, y, ghost) => { c.style.left = x + 'px'; c.style.top = y + 'px';
        document.getElementById('fakeGhost').style.display = ghost ? 'inline-block' : 'none'; };
    }""")
    cursor = lambda x, y, ghost=False: pg.evaluate("([x, y, g]) => window.__cursor(x, y, g)", [x, y, ghost])
    src = pg.locator('.pane[data-slot="A"] .row[data-path="/OPL"]').bounding_box()
    dst = pg.locator('.pane[data-slot="B"] .tree').bounding_box()
    sx, sy = src["x"] + 90, src["y"] + src["height"] / 2
    tx, ty = dst["x"] + dst["width"] / 2, dst["y"] + 120
    cursor(sx - 120, sy + 40)
    snap(3)
    for i in range(1, 6):  # move to the save
        cursor(sx - 120 + 120 * i / 5, sy + 40 - 40 * i / 5)
        snap()
    pg.mouse.move(sx, sy)
    pg.mouse.down()
    steps = 14
    for i in range(1, steps + 1):
        x, y = sx + (tx - sx) * i / steps, sy + (ty - sy) * i / steps
        pg.mouse.move(x, y)
        cursor(x, y, True)
        snap()
    snap(3)
    pg.mouse.up()
    cursor(tx, ty)
    pg.wait_for_selector('.pane[data-slot="B"] .row[data-path="/OPL"]')
    snap(4)
    pg.click('.pane[data-slot="B"] .row[data-path="/OPL"]')
    pg.mouse.move(2, VIEW["height"] - 2)
    cursor(tx, ty)
    snap(14)
    gif = OUT / "two-cards.gif"
    palette = frames / "palette.png"
    scale = "fps=7,scale=1000:-1:flags=lanczos"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-framerate", "7", "-i", frames / "%03d.png",
                    "-vf", f"{scale},palettegen=max_colors=128:stats_mode=diff", palette], check=True)
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-framerate", "7", "-i", frames / "%03d.png", "-i", palette,
                    "-lavfi", f"{scale} [x]; [x][1:v] paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle",
                    gif], check=True)
    shutil.rmtree(frames)
    pg.context.close()


def mobile(browser, url, sd):
    ctx = browser.new_context(viewport={"width": 390, "height": 760}, locale="en-US", color_scheme="dark",
                              device_scale_factor=2)
    pg = ctx.new_page()
    pg.goto(url)
    pg.wait_for_selector("#engine.ready", timeout=120000)
    pg.set_input_files("#pickCard", str(Path(sd) / "MemoryCards/PS2/BOOT/BootCard-1.mcd"))
    pg.wait_for_selector('.pane[data-slot="A"] .row')
    quiet(pg)
    pg.screenshot(path=OUT / "mobile.png")
    ctx.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True)
    ap.add_argument("--sd", required=True)
    ap.add_argument("--vmc", nargs="*", default=[])
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch()
        hero(b, a.url, a.sd, "light")
        hero(b, a.url, a.sd, "dark")
        dialogs(b, a.url, a.sd, a.vmc)
        dual_gif(b, a.url, a.sd)
        mobile(b, a.url, a.sd)
        b.close()
    for f in sorted(OUT.iterdir()):
        print(f"{f.name}: {f.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
