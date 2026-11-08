# This file is part of PSMemoryManager.
# SPDX-License-Identifier: GPL-3.0-or-later
import hashlib
import io
import json
import os
import zipfile
from pathlib import Path

import pytest
from mymcplusplus import ps2mc_ecc as ref

from psmm.core import convert as cv
from psmm.core import ecc
from psmm.core.card import CardError, MemoryCard, NoSpaceError
from psmm.core.formats import Layout


@pytest.fixture(autouse=True)
def data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("PSMM_DATA_DIR", str(tmp_path / "data"))


def _md5(p):
    return hashlib.md5(Path(p).read_bytes()).hexdigest()


def _flat(card):
    return sorted(
        (e.path, e.mode, 0 if e.is_dir else e.size, e.created, e.modified)
        for top in card.tree() for e in [top] + _all_children(top)
    )


def _all_children(e):
    out = []
    for c in e.children:
        out += [c] + _all_children(c)
    return out


def test_fast_ecc_matches_mymc():
    import random

    random.seed(7)
    chunks = [b"\0" * 128, b"\xff" * 128] + [bytes([i]) * 128 for i in range(256)]
    chunks += [os.urandom(128) for _ in range(3000)]
    chunks += [bytes(random.choice([0, 1, 128, 255]) for _ in range(128)) for _ in range(500)]
    for c in chunks:
        assert ecc.ecc_calculate(c) == ref._ecc_calculate(c)
    raw = os.urandom(512 * 64)
    assert ecc.strip_ecc(ecc.add_ecc(raw)) == raw


@pytest.fixture
def game_card(tmp_path):
    """8 MB card with two games (one with a nested folder) and a system folder."""
    c = MemoryCard.create(tmp_path / "src.mcd", 8)
    for d in ("BASLUS-20228GAME1", "BASLUS-20228GAME2", "BESLES-52541X", "BADATA-SYSTEM"):
        src = tmp_path / "in" / d
        src.mkdir(parents=True)
        (src / "data").write_bytes(os.urandom(4000))
        with c.edit() as ed:
            ed.add_local(src)
    with c.edit() as ed:
        ed.mkdir("/BESLES-52541X/sub")
        ed.write_file("/BESLES-52541X/sub/deep", b"deep")
    yield c
    c.close()


def test_convert_ecc_roundtrip_is_identical(game_card, tmp_path):
    out = cv.convert(game_card, tmp_path / "x.ps2", ecc=True)
    with MemoryCard(out) as e:
        assert e.format.layout is Layout.ECC and e.format.file_size == 8650752
        assert e.check()[0] and _flat(e) == _flat(game_card)
        back = cv.convert(e, tmp_path / "back.mcd", ecc=False)
    assert _md5(back) == _md5(game_card.path)


@pytest.mark.parametrize("size", [16, 64, 4])
def test_convert_resize_keeps_everything(game_card, tmp_path, size):
    out = cv.convert(game_card, tmp_path / f"r{size}.mcd", ecc=False, size_mb=size)
    with MemoryCard(out) as r:
        assert r.format.nominal_mb == size and r.check()[0]
        assert _flat(r) == _flat(game_card)
        assert r.read_file("/BESLES-52541X/sub/deep") == b"deep"


def test_convert_too_small(game_card, tmp_path):
    with game_card.edit() as ed:
        ed.write_file("/big", os.urandom(1_500_000))
    with pytest.raises(NoSpaceError):
        cv.convert(game_card, tmp_path / "tiny.mcd", ecc=False, size_mb=1)
    assert not (tmp_path / "tiny.mcd").exists()


def test_opl_vmc_name():
    assert cv.opl_vmc_name("SLUS-20228") == "SLUS_202.28_0.bin"
    assert cv.opl_vmc_name("sles_525.41", 1) == "SLES_525.41_1.bin"
    # the name OPL gives a VMC maps back to the same game
    assert cv.game_id_from_text(cv.opl_vmc_name("SCUS-97113")) == "SCUS-97113"


def test_game_ids(game_card):
    assert cv.game_id_from_text("SLUS_202.28_0.bin") == "SLUS-20228"
    assert cv.game_id_from_text("SLES-52541-1.mcd") == "SLES-52541"
    assert cv.game_id_from_text("Mcd001.ps2") is None
    assert cv.guess_game_id(game_card) == "SLUS-20228"  # two saves vs one
    assert cv.guess_game_id(game_card, "SCUS_971.13_0.bin") == "SCUS-97113"
    groups, others = cv.group_by_game(game_card)
    assert [g.game for g in groups] == ["SLES-52541", "SLUS-20228"]
    assert others == ["/BADATA-SYSTEM"]


def test_split(game_card, tmp_path):
    cards = cv.split_by_game(game_card, tmp_path / "out")
    assert [(c["game"], c["saves"]) for c in cards] == [("SLES-52541", 1), ("SLUS-20228", 2)]
    with MemoryCard(tmp_path / "out" / "SLES-52541.mcd") as c:
        assert [e.name for e in c.list_dir("/")] == ["BESLES-52541X"]
        assert c.read_file("/BESLES-52541X/sub/deep") == b"deep"
    cards = cv.split_by_game(game_card, tmp_path / "out2", include_others=True)
    with MemoryCard(cards[0]["path"]) as c:
        assert "BADATA-SYSTEM" in [e.name for e in c.list_dir("/")]


def _web(tmp_path, monkeypatch):
    from psmm import web_api as w

    monkeypatch.setattr(w, "WORK", tmp_path / "work")
    monkeypatch.setattr(w, "STAGING", tmp_path / "work" / "staging")
    monkeypatch.setattr(w, "EXPORT", tmp_path / "work" / "out.bin")
    monkeypatch.setattr(w, "INCOMING", tmp_path / "work" / "in.bin")
    monkeypatch.setattr(w, "_slots", {s: w._Slot() for s in w.SLOTS})
    (tmp_path / "work").mkdir()
    return w


def test_web_card_import_flow(game_card, tmp_path, monkeypatch):
    w = _web(tmp_path, monkeypatch)
    pcsx2 = cv.convert(game_card, tmp_path / "SLUS_202.28_0.ps2", ecc=True)
    st = Path(w.staging_dir())
    (st / "SLUS_202.28_0.ps2").write_bytes(pcsx2.read_bytes())
    (st / "junk.bin").write_bytes(b"x" * 1000)
    info = json.loads(w.inspect_staged_cards())["cards"]
    good = next(c for c in info if c["ok"])
    assert good["game"] == "SLUS-20228" and good["ecc"] and {"SLUS-20228", "SLES-52541"} <= set(good["games"])
    assert not next(c for c in info if c["file"] == "junk.bin")["ok"]
    # merge into an open card
    json.loads(w.new_card("A", "a.mcd", 8, False))
    r = json.loads(w.import_staged_cards("A", json.dumps(["SLUS_202.28_0.ps2"])))
    assert r["ok"] and len(r["tree"]) == 4
    assert json.loads(w.import_staged_cards("A", json.dumps(["SLUS_202.28_0.ps2"])))["kind"] == "exists"
    # prepared for the SD: no ECC anymore
    r = json.loads(w.prepare_staged_card("SLUS_202.28_0.ps2"))
    assert r["ok"] and Path(r["path"]).stat().st_size == 8 * 1024 * 1024
    # SD plan: new game folder, then next channel in the same batch
    json.loads(w.sd_load(json.dumps([]), json.dumps({})))
    p1 = json.loads(w.sd_plan_import("slus_202.28", 8388608))
    p2 = json.loads(w.sd_plan_import("SLUS-20228", 8388608))
    assert (p1["path"], p1["existing"]) == ("MemoryCards/PS2/SLUS-20228/SLUS-20228-1.mcd", False)
    assert (p2["path"], p2["existing"]) == ("MemoryCards/PS2/SLUS-20228/SLUS-20228-2.mcd", True)
    # download as SD layout
    r = json.loads(w.staged_cards_zip(json.dumps([{"file": "SLUS_202.28_0.ps2", "game": "SLUS-20228"}] * 2)))
    names = zipfile.ZipFile(io.BytesIO(Path(r["path"]).read_bytes())).namelist()
    assert names == ["MemoryCards/PS2/SLUS-20228/SLUS-20228-1.mcd", "MemoryCards/PS2/SLUS-20228/SLUS-20228-2.mcd"]
    assert json.loads(w.staged_cards_zip(json.dumps([{"file": "SLUS_202.28_0.ps2", "game": ""}])))["ok"] is False
    # OPL layout: VMC/<CODE_123.45>_N.bin
    r = json.loads(w.staged_cards_zip(json.dumps([{"file": "SLUS_202.28_0.ps2", "game": "SLUS-20228"}] * 2), "opl"))
    assert r["name"] == "OPL-VMC.zip"
    assert zipfile.ZipFile(io.BytesIO(Path(r["path"]).read_bytes())).namelist() == [
        "VMC/SLUS_202.28_0.bin", "VMC/SLUS_202.28_1.bin"]


def test_web_convert_and_split(game_card, tmp_path, monkeypatch):
    w = _web(tmp_path, monkeypatch)
    Path(w.INCOMING).write_bytes(game_card.path.read_bytes())
    assert json.loads(w.open_card("A", "src.mcd"))["ok"]
    r = json.loads(w.convert_card("A", "pcsx2", 0))
    assert r["name"] == "src.ps2" and r["size"] == 8650752
    r = json.loads(w.convert_card("A", "gen2", 16))
    assert r["name"] == "src.mcd" and r["size"] == 16 * 1024 * 1024
    prev = json.loads(w.split_preview("A"))
    assert [g["game"] for g in prev["games"]] == ["SLES-52541", "SLUS-20228"] and prev["others"] == ["BADATA-SYSTEM"]
    r = json.loads(w.split_card("A", 8, False, "files"))
    assert [c["game"] for c in r["cards"]] == ["SLES-52541", "SLUS-20228"]
    r = json.loads(w.split_card("A", 8, True, "zip"))
    assert zipfile.ZipFile(io.BytesIO(Path(r["path"]).read_bytes())).namelist() == [
        "MemoryCards/PS2/SLES-52541/SLES-52541-1.mcd", "MemoryCards/PS2/SLUS-20228/SLUS-20228-1.mcd"]
    r = json.loads(w.split_card("A", 8, False, "zip-opl"))
    assert zipfile.ZipFile(io.BytesIO(Path(r["path"]).read_bytes())).namelist() == [
        "VMC/SLES_525.41_0.bin", "VMC/SLUS_202.28_0.bin"]
    assert json.loads(w.summary("A"))["card"]["game"] == "SLUS-20228"


def test_gamedb():
    from psmm.core import gamedb

    assert gamedb.title("SLUS-20228") == "Silent Hill 2"
    assert gamedb.title("slus-20312") == "Final Fantasy X"
    assert gamedb.title("XXXX-00000") is None and gamedb.title(None) is None


def test_web_resize_too_small(game_card, tmp_path, monkeypatch):
    w = _web(tmp_path, monkeypatch)
    with game_card.edit() as ed:
        ed.write_file("/big", os.urandom(1_500_000))
    Path(w.INCOMING).write_bytes(game_card.path.read_bytes())
    json.loads(w.open_card("A", "src.mcd"))
    r = json.loads(w.resize_card("A", 1))
    assert r["kind"] == "nospace"
    assert json.loads(w.summary("A"))["card"]["sizeMB"] == 8  # untouched


def test_web_resize_is_undoable(game_card, tmp_path, monkeypatch):
    w = _web(tmp_path, monkeypatch)
    Path(w.INCOMING).write_bytes(game_card.path.read_bytes())
    json.loads(w.open_card("A", "src.mcd"))
    r = json.loads(w.resize_card("A", 16))
    assert r["ok"] and r["card"]["sizeMB"] == 16 and r["dirty"] and r["canUndo"]
    assert len(r["tree"]) == 4
    assert json.loads(w.resize_card("A", 16))["kind"] == "card"  # same size
    r = json.loads(w.resize_card("A", 1))  # the content is small: it fits
    assert r["ok"] and r["card"]["sizeMB"] == 1 and len(r["tree"]) == 4
    assert json.loads(w.undo("A"))["card"]["sizeMB"] == 16
    r = json.loads(w.undo("A"))
    assert r["card"]["sizeMB"] == 8 and len(r["tree"]) == 4
