# This file is part of PSMemoryManager.
# SPDX-License-Identifier: GPL-3.0-or-later
import hashlib
import json
import os
import zipfile
import io
from pathlib import Path

import pytest

from psmm.core import formats
from psmm.core.card import CardError, ExistsError, MemoryCard, NoSpaceError, parse_game_id
from psmm.core.formats import Layout

SAMPLES = Path(os.environ.get("PSMM_SAMPLES", Path.home() / "psxmemcard_novo"))


@pytest.fixture(autouse=True)
def data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("PSMM_DATA_DIR", str(tmp_path / "data"))


@pytest.fixture
def raw_card(tmp_path):
    c = MemoryCard.create(tmp_path / "Card1-1.mcd", 8, ecc=False)
    yield c
    c.close()


@pytest.mark.parametrize("ecc,size", [(False, 8 * 2**20), (True, 8 * 2**20 // 512 * 528)])
def test_create_and_detect(tmp_path, ecc, size):
    c = MemoryCard.create(tmp_path / "x.ps2", 8, ecc=ecc)
    assert c.format.file_size == size
    assert c.format.layout is (Layout.ECC if ecc else Layout.RAW)
    assert c.format.nominal_mb == 8
    assert c.check()[0]
    c.close()


def test_detect_rejects_garbage(tmp_path):
    p = tmp_path / "junk.bin"
    p.write_bytes(b"hello" * 1000)
    with pytest.raises(formats.FormatError):
        formats.detect(p)


def test_add_extract_roundtrip(raw_card, tmp_path):
    src = tmp_path / "src" / "BASLUS-20963SAVE"
    src.mkdir(parents=True)
    payload = os.urandom(50_000)
    (src / "data.bin").write_bytes(payload)
    with raw_card.edit() as ed:
        ed.add_local(src, "/")
    assert raw_card.check()[0]
    assert raw_card.read_file("/BASLUS-20963SAVE/data.bin") == payload
    e = raw_card.list_dir("/")[0]
    assert e.game_id.serial == "SLUS-20963" and e.game_id.region == "US"
    out = tmp_path / "out"
    raw_card.extract("/BASLUS-20963SAVE", out)
    assert (out / "BASLUS-20963SAVE" / "data.bin").read_bytes() == payload
    with pytest.raises(ExistsError):
        raw_card.extract("/BASLUS-20963SAVE", out)
    z = zipfile.ZipFile(io.BytesIO(raw_card.export_zip(["/BASLUS-20963SAVE"])))
    assert z.read("BASLUS-20963SAVE/data.bin") == payload


def test_failed_edit_leaves_original_untouched(raw_card):
    before = hashlib.sha256(raw_card.path.read_bytes()).digest()
    with pytest.raises(RuntimeError):
        with raw_card.edit() as ed:
            ed.mkdir("/A")
            raise RuntimeError("boom")
    assert hashlib.sha256(raw_card.path.read_bytes()).digest() == before
    assert not list(raw_card.path.parent.glob("*.psmm-tmp"))


def test_backup_created(raw_card):
    with raw_card.edit() as ed:
        ed.mkdir("/A")
    assert raw_card.last_backup and raw_card.last_backup.exists()


def test_no_space(raw_card):
    with pytest.raises(NoSpaceError):
        with raw_card.edit() as ed:
            ed.write_file("/BIG", b"x" * (9 * 2**20))


@pytest.mark.parametrize("name", ["ação", "x" * 33, "a?b"])
def test_invalid_names(raw_card, name):
    with pytest.raises(CardError):
        with raw_card.edit() as ed:
            ed.mkdir("/" + name)


def test_rename_and_remove(raw_card):
    with raw_card.edit() as ed:
        ed.mkdir("/A")
        ed.write_file("/A/f", b"1")
        ed.rename("/A", "B")
    assert [e.name for e in raw_card.list_dir("/")] == ["B"]
    with raw_card.edit() as ed:
        ed.remove("/B")
    assert raw_card.list_dir("/") == []
    assert raw_card.check()[0]


def test_parse_game_id():
    assert parse_game_id("BESLES-52541") .serial == "SLES-52541"
    assert parse_game_id("BISLPM-65530x").region == "JP"
    assert parse_game_id("APPS") is None


def _web(tmp_path, monkeypatch):
    from psmm import web_api as w

    monkeypatch.setattr(w, "WORK", tmp_path)
    monkeypatch.setattr(w, "STAGING", tmp_path / "staging")
    monkeypatch.setattr(w, "INCOMING", tmp_path / "in.bin")
    monkeypatch.setattr(w, "EXPORT", tmp_path / "out.bin")
    monkeypatch.setattr(w, "_slots", {s: w._Slot() for s in w.SLOTS})
    return w


def test_web_api(tmp_path, monkeypatch):
    w = _web(tmp_path, monkeypatch)
    r = json.loads(w.new_card("A", "t.mcd", 8, False))
    assert r["ok"] and r["dirty"] and r["slot"] == "A"
    st = Path(w.staging_dir())
    (st / "S").mkdir()
    (st / "S" / "f").write_bytes(b"abc")
    r = json.loads(w.add_staged("A", "/"))
    assert r["ok"] and r["canUndo"]
    assert json.loads(w.add_staged("A", "/"))["kind"] == "exists"
    r = json.loads(w.export("A", json.dumps(["/S/f"])))
    assert r["kind"] == "file" and Path(r["path"]).read_bytes() == b"abc"
    r = json.loads(w.undo("A"))
    assert r["ok"] and r["tree"] == []
    assert json.loads(w.summary("B"))["kind"] == "card"  # slot B empty


def test_web_api_saves_and_copy(tmp_path, monkeypatch):
    w = _web(tmp_path, monkeypatch)
    json.loads(w.new_card("A", "a.mcd", 8, False))
    json.loads(w.new_card("B", "b.mcd", 8, True))
    st = Path(w.staging_dir())
    save = st / "BASLUS-20963GAME"
    save.mkdir()
    (save / "icon.sys").write_bytes(b"PS2D" + b"\0" * 960)
    (save / "data").write_bytes(os.urandom(3000))
    assert json.loads(w.add_staged("A", "/"))["ok"]
    for fmt in ("psu", "max"):
        r = json.loads(w.export_saves("A", json.dumps(["/BASLUS-20963GAME"]), fmt))
        assert r["ok"] and r["name"] == f"BASLUS-20963GAME.{fmt}"
        exported = Path(r["path"]).read_bytes()
        st = Path(w.staging_dir())
        (st / r["name"]).write_bytes(exported)
        info = json.loads(w.inspect_staged_saves())["saves"][0]
        assert info["ok"] and info["name"] == "BASLUS-20963GAME" and info["files"] == 2
        r = json.loads(w.import_staged_saves("B", fmt == "max"))  # 2nd time: overwrite
        assert r["ok"], r
    # copying A -> B conflicts, then overwrites
    assert json.loads(w.copy_items("A", json.dumps(["/BASLUS-20963GAME"]), "B"))["kind"] == "exists"
    r = json.loads(w.copy_items("A", json.dumps(["/BASLUS-20963GAME"]), "B", "/", True))
    assert r["ok"] and [e["name"] for e in r["tree"]] == ["BASLUS-20963GAME"]
    assert json.loads(w.copy_items("A", json.dumps(["/x"]), "A"))["kind"] == "card"
    assert json.loads(w.check("B"))["healthy"]
    # garbage is reported per file, not as a crash
    st = Path(w.staging_dir())
    (st / "bad.psu").write_bytes(b"nope" * 100)
    assert json.loads(w.inspect_staged_saves())["saves"][0]["ok"] is False


def test_save_roundtrip_keeps_metadata(raw_card, tmp_path):
    from psmm.core import saves

    src = tmp_path / "S"
    src.mkdir()
    (src / "a").write_bytes(os.urandom(2000))
    with raw_card.edit() as ed:
        ed.add_local(src)
    sf = raw_card.export_save("/S")
    data = saves.dump(sf, "psu")
    sf2, fmt = saves.load(data, "S.psu")
    assert fmt == "psu"
    other = MemoryCard.create(tmp_path / "o.mcd", 8)
    with other.edit() as ed:
        ed.import_save(sf2, name="S2")
    a, b = raw_card.stat("/S"), other.stat("/S2")
    assert (a.modified, a.created, a.mode) == (b.modified, b.created, b.mode)
    assert other.read_file("/S2/a") == raw_card.read_file("/S/a")
    other.close()


@pytest.mark.skipif(not SAMPLES.is_dir(), reason="Gen2 sample folder not available")
def test_gen2_samples_read_only():
    cards = [p for p in SAMPLES.glob("MemoryCards/*/*/*.mcd") if "/PS1/" not in p.as_posix()]
    assert cards
    for p in cards:
        before = p.stat().st_mtime_ns
        with MemoryCard(p) as c:
            assert c.format.layout is Layout.RAW
            assert c.check()[0]
            c.tree()
        assert p.stat().st_mtime_ns == before


def test_i18n_messages(raw_card):
    from psmm.core import i18n

    assert i18n.normalize("pt-BR") == "pt" and i18n.normalize("pt_PT.UTF-8") == "pt"
    assert i18n.normalize("es-ES") == "en" and i18n.normalize(None) == "en"
    # every key has both languages
    for key, entry in i18n.MESSAGES.items():
        assert set(entry) == set(i18n.LANGUAGES), key
    try:
        with pytest.raises(CardError) as exc:
            with raw_card.edit() as ed:
                ed.mkdir("/ação")
        i18n.set_language("en")
        assert "ASCII" in str(exc.value) and "accents" in str(exc.value)
        i18n.set_language("pt")
        assert "acentos" in str(exc.value)
        assert "sem ECC" in raw_card.format.describe()
        i18n.set_language("en")
        assert "no ECC" in raw_card.format.describe()
    finally:
        i18n.set_language("en")


def _orig_vs_fast(path):
    """Free space and check() from plain mymc++ vs our fast versions."""
    import contextlib, io as _io
    from mymcplusplus import ps2mc as orig
    from psmm.core.card import _PS2MC
    from psmm.core.formats import detect

    layout = detect(path).layout
    out = []
    for make in (lambda f: orig.ps2mc(f, ignore_ecc=layout is Layout.RAW), lambda f: _PS2MC(f, layout)):
        with open(path, "rb") as f:
            mc = make(f)
            if layout is Layout.RAW:  # plain mymc++ guesses the layout; force it like we do
                mc.spare_size, mc.raw_page_size = 0, mc.page_size
            buf = _io.StringIO()
            with contextlib.redirect_stdout(buf):
                ok = mc.check()
            out.append((mc.get_free_space(), ok, buf.getvalue()))
            mc.close()
    return out


def _corrupt(card_path, how):
    from mymcplusplus import ps2mc as orig

    with open(card_path, "r+b") as f:
        mc = orig.ps2mc(f, ignore_ecc=True)
        mc.spare_size, mc.raw_page_size = 0, mc.page_size
        if how == "lost":
            mc.set_fat(500, orig.PS2MC_FAT_CHAIN_END)  # allocated but unreferenced
        elif how == "cross":
            d = mc.dir_open("/S")
            ents = [e for e in d][2:]
            d.close()
            a, b = ents[0][4], ents[1][4]
            mc.set_fat(a, b | orig.PS2MC_FAT_ALLOCATED_BIT)  # file a's chain runs into file b
        mc.flush()
        mc.close()


@pytest.mark.parametrize("how", [None, "lost", "cross"])
@pytest.mark.parametrize("size", [8, 64])
def test_fast_fat_matches_mymc(tmp_path, how, size):
    c = MemoryCard.create(tmp_path / "x.mcd", size)
    with c.edit() as ed:
        ed.mkdir("/S")
        ed.write_file("/S/a", os.urandom(5000))
        ed.write_file("/S/b", os.urandom(9000))
    c.close()
    if how:
        _corrupt(tmp_path / "x.mcd", how)
    (free_o, ok_o, msg_o), (free_f, ok_f, msg_f) = _orig_vs_fast(tmp_path / "x.mcd")
    assert (free_f, ok_f, msg_f) == (free_o, ok_o, msg_o)
    assert ok_f is (how is None)


@pytest.mark.skipif(not SAMPLES.is_dir(), reason="Gen2 sample folder not available")
def test_fast_fat_matches_mymc_on_samples():
    for p in SAMPLES.glob("MemoryCards/*/*/*.mcd"):
        if "/PS1/" in p.as_posix():
            continue
        orig, fast = _orig_vs_fast(p)
        assert fast == orig, p
