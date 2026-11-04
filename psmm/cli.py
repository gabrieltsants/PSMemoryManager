# This file is part of PSMemoryManager.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Command line: ``psmm [--lang en|pt] <card> <command> ...``"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .core.card import CardError, Entry, MemoryCard
from .core.formats import FormatError
from .core.i18n import detect_system_language, set_language, t


def human(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if abs(n) < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return str(n)


def _fmt_entry(e: Entry, indent: str = "") -> str:
    date = e.modified.strftime("%Y-%m-%d %H:%M") if e.modified else "-"
    name = e.name + ("/" if e.is_dir else "")
    extra = f"  {e.title}" if e.title else ""
    attrs = f"  [{e.attributes()}]" if e.attributes() else ""
    return f"{indent}{human(e.size):>10}  {date}  {name}{extra}{attrs}"


def _field(label_key: str, value: str) -> None:
    print(f"{t(label_key):<12} {value}")


def cmd_info(card: MemoryCard, a) -> int:
    i = card.info()
    f = i.format
    _field("cli.file", str(i.path))
    _field("cli.format", f.describe())
    _field("cli.size_label", f"{f.file_size} bytes")
    _field("cli.geometry", t("cli.geometry_value", page=f.page_size, ppc=f.pages_per_cluster,
                             ppb=f.pages_per_block, clusters=f.clusters_per_card))
    _field("cli.version", f"{f.version}  flags 0x{f.card_flags:02X}")
    _field("cli.space", t("cli.space_value", used=human(i.used_bytes), free=human(i.free_bytes),
                          total=human(i.total_bytes)))
    if f.size_mismatch:
        print(t("cli.size_mismatch"))
    return 0


def _print_tree(entries: list[Entry], indent: str = "") -> None:
    for e in entries:
        print(_fmt_entry(e, indent))
        if e.is_dir and e.children:
            _print_tree(e.children, indent + "    ")


def cmd_ls(card: MemoryCard, a) -> int:
    if a.recursive:
        _print_tree([card.stat(a.path)] if a.path not in ("/", "") else card.tree())
    else:
        for e in card.list_dir(a.path):
            print(_fmt_entry(e))
    print("\n" + t("cli.free", free=human(card.free_bytes())))
    return 0


def cmd_extract(card: MemoryCard, a) -> int:
    for out in card.extract_many(a.paths, a.output, overwrite=a.overwrite):
        print(out)
    return 0


def _report(card: MemoryCard, changes: list[str]) -> None:
    if changes:
        print("\n".join(changes))
    if card.last_backup:
        print(t("cli.backup", path=card.last_backup))


def cmd_add(card: MemoryCard, a) -> int:
    with card.edit() as ed:
        for src in a.files:
            ed.add_local(src, a.directory, overwrite=a.overwrite)
        changes = list(ed.changes)
    _report(card, changes)
    return 0


def cmd_mkdir(card: MemoryCard, a) -> int:
    with card.edit() as ed:
        for p in a.paths:
            ed.mkdir(p)
        changes = list(ed.changes)
    _report(card, changes)
    return 0


def cmd_rm(card: MemoryCard, a) -> int:
    for p in a.paths:
        if card.is_dir(p) and not a.recursive and card.list_dir(p):
            print(t("cli.not_empty", path=p), file=sys.stderr)
            return 1
    with card.edit() as ed:
        for p in a.paths:
            ed.remove(p)
        changes = list(ed.changes)
    _report(card, changes)
    return 0


def cmd_rename(card: MemoryCard, a) -> int:
    with card.edit() as ed:
        ed.rename(a.path, a.new_name)
        changes = list(ed.changes)
    _report(card, changes)
    return 0


def cmd_resize(card: MemoryCard, a) -> int:
    """Resizes the card file in place (with a backup, like every change)."""
    import os
    from .core import backup, convert

    if a.size == card.format.nominal_mb:
        raise CardError("conv.same_size", size=a.size)
    tmp = card.path.with_name(f".{card.path.name}.resize")
    convert.convert(card, tmp, ecc=card.format.layout.value == "ecc", size_mb=a.size)
    if card.make_backups:
        print(t("cli.backup", path=backup.make_backup(card.path)))
    card.close()
    os.replace(tmp, card.path)
    card.reload()
    print(f"{card.path}: {card.format.describe()}")
    return 0


def cmd_merge(card: MemoryCard, a) -> int:
    with card.edit() as ed:
        for src_path in a.sources:
            with MemoryCard(src_path, make_backups=False) as src:
                ed.copy_from(src, ["/"], "/", overwrite=a.overwrite)
        changes = list(ed.changes)
    _report(card, changes)
    return 0


def cmd_check(card: MemoryCard, a) -> int:
    ok, msgs = card.check()
    for m in msgs:
        print(m)
    print(t("cli.check_ok") if ok else t("cli.check_bad"))
    return 0 if ok else 1


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="psmm", description=t("cli.description"))
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    p.add_argument("--lang", choices=["en", "pt"], help=t("cli.lang"))
    p.add_argument("--no-backup", action="store_true", help=t("cli.no_backup"))
    p.add_argument("card", help=t("cli.card"))
    sub = p.add_subparsers(dest="cmd", required=True, metavar=t("cli.command"))

    s = sub.add_parser("info", help=t("cli.info"))
    s.set_defaults(fn=cmd_info)

    s = sub.add_parser("ls", help=t("cli.ls"))
    s.add_argument("path", nargs="?", default="/")
    s.add_argument("-r", "--recursive", action="store_true")
    s.set_defaults(fn=cmd_ls)

    s = sub.add_parser("extract", help=t("cli.extract"))
    s.add_argument("paths", nargs="+")
    s.add_argument("-o", "--output", default=".", help=t("cli.output"))
    s.add_argument("-f", "--overwrite", action="store_true")
    s.set_defaults(fn=cmd_extract)

    s = sub.add_parser("add", help=t("cli.add"))
    s.add_argument("files", nargs="+")
    s.add_argument("-d", "--directory", default="/", help=t("cli.directory"))
    s.add_argument("-f", "--overwrite", action="store_true")
    s.set_defaults(fn=cmd_add)

    s = sub.add_parser("mkdir", help=t("cli.mkdir"))
    s.add_argument("paths", nargs="+")
    s.set_defaults(fn=cmd_mkdir)

    s = sub.add_parser("rm", help=t("cli.rm"))
    s.add_argument("paths", nargs="+")
    s.add_argument("-r", "--recursive", action="store_true", help=t("cli.recursive_rm"))
    s.set_defaults(fn=cmd_rm)

    s = sub.add_parser("rename", help=t("cli.rename"))
    s.add_argument("path")
    s.add_argument("new_name")
    s.set_defaults(fn=cmd_rename)

    s = sub.add_parser("resize", help=t("cli.resize"))
    s.add_argument("size", type=int, help=t("cli.size"))
    s.set_defaults(fn=cmd_resize)

    s = sub.add_parser("merge", help=t("cli.merge"))
    s.add_argument("sources", nargs="+")
    s.add_argument("-f", "--overwrite", action="store_true")
    s.set_defaults(fn=cmd_merge)

    s = sub.add_parser("check", help=t("cli.check"))
    s.set_defaults(fn=cmd_check)
    return p


def new_card_main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="psmm new", description=t("cli.new"))
    p.add_argument("path")
    p.add_argument("-s", "--size", type=int, default=8, help=t("cli.size"))
    p.add_argument("--ecc", action="store_true", help=t("cli.ecc"))
    a = p.parse_args(argv)
    card = MemoryCard.create(a.path, a.size, ecc=a.ecc)
    print(f"{a.path}: {card.format.describe()}")
    card.close()
    return 0


def sd_main(argv: list[str]) -> int:
    """Read-only overview of a Gen2/SD2PSX SD card folder."""
    from .core import gamedb, sdcard

    p = argparse.ArgumentParser(prog="psmm sd", description=t("cli.sd"))
    p.add_argument("root", help=t("cli.sd_root"))
    a = p.parse_args(argv)
    files, texts = sdcard.scan_local(a.root)
    layout = sdcard.parse_listing(files, texts)
    if not layout.root_ok:
        print(t("cli.sd_not_root"), file=sys.stderr)
        return 1
    for v in layout.variants:
        print(f"{v.label}")
        for f in v.folders:
            game = gamedb.title(f.folder) if f.kind == "game" else None
            print(f"  {f.label}" + (f"  ({game})" if game else ""))
            for c in f.channels:
                name = f"  {c.name}" if c.name else ""
                print(f"    {c.number}: {human(c.size):>8}{name}")
    settings = sdcard.read_settings(texts.get(sdcard.SETTINGS_FILE, ""))
    print()
    for s in settings["settings"]:
        print(f"{s['section']}.{s['key']}={s['value']}" + ("" if s["present"] else " (default)"))
    for row in sdcard.read_game2folder(texts.get(sdcard.GAME2FOLDER_FILE, "")):
        print(f"Game2Folder {row['platform']}: {row['game']} -> {row['folder']}")
    return 0


def convert_main(argv: list[str]) -> int:
    from .core import convert

    p = argparse.ArgumentParser(prog="psmm convert", description=t("cli.convert"))
    p.add_argument("source")
    p.add_argument("dest", help=t("cli.convert_dest"))
    p.add_argument("-s", "--size", type=int, default=0, help=t("cli.convert_size"))
    g = p.add_mutually_exclusive_group()
    g.add_argument("--ecc", dest="ecc", action="store_true", default=None, help=t("cli.ecc"))
    g.add_argument("--no-ecc", dest="ecc", action="store_false")
    a = p.parse_args(argv)
    ecc = a.ecc if a.ecc is not None else convert.TARGETS[convert.target_for_extension(a.dest)][1]
    with MemoryCard(a.source, make_backups=False) as src:
        out = convert.convert(src, a.dest, ecc=ecc, size_mb=a.size or None)
    with MemoryCard(out, make_backups=False) as c:
        print(f"{out}: {c.format.describe()}")
    return 0


def split_main(argv: list[str]) -> int:
    """One card per game, written with the SD card layout under ``out``."""
    import shutil
    import tempfile

    from .core import convert, sdcard

    p = argparse.ArgumentParser(prog="psmm split", description=t("cli.split"))
    p.add_argument("source")
    p.add_argument("out", help=t("cli.split_out"))
    p.add_argument("-s", "--size", type=int, default=8, help=t("cli.size"))
    p.add_argument("--with-others", action="store_true", help=t("cli.split_others"))
    a = p.parse_args(argv)
    with MemoryCard(a.source, make_backups=False) as src, tempfile.TemporaryDirectory() as tmp:
        cards = convert.split_by_game(src, tmp, size_mb=a.size, include_others=a.with_others)
        for c in cards:
            files, texts = sdcard.scan_local(a.out)
            layout = sdcard.parse_listing(files, texts)
            v = layout.variant("PS2")
            folder = v.find(c["game"]) if v else None
            plan = (sdcard.plan_new_channel(layout, "PS2", folder.folder) if folder
                    else sdcard.plan_new_card(layout, "PS2", c["game"]))
            dest = Path(a.out) / plan["path"]
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(c["path"], dest)
            print(f"{dest}: {', '.join(c['titles'])}")
    return 0


def _pop_lang(argv: list[str]) -> str | None:
    """Reads --lang before building the parser (help text depends on it)."""
    for i, arg in enumerate(argv):
        if arg == "--lang" and i + 1 < len(argv):
            return argv[i + 1]
        if arg.startswith("--lang="):
            return arg.split("=", 1)[1]
    return None


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    argv = list(sys.argv[1:] if argv is None else argv)
    set_language(_pop_lang(argv) or detect_system_language())
    try:
        if argv and argv[0] == "new":
            return new_card_main(argv[1:])
        if argv and argv[0] == "sd":
            return sd_main(argv[1:])
        if argv and argv[0] == "convert":
            return convert_main(argv[1:])
        if argv and argv[0] == "split":
            return split_main(argv[1:])
        a = build_parser().parse_args(argv)
        with MemoryCard(a.card, make_backups=not a.no_backup) as card:
            return a.fn(card, a)
    except (CardError, FormatError) as e:
        print(t("cli.error", error=e), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
