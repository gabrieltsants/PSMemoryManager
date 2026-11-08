# This file is part of PSMemoryManager.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Real PS2 files (tests/data/ps2, from mymc++'s test data): a card made by a
console and one save in every format the import accepts."""
import gzip
import hashlib
from pathlib import Path

import pytest

from psmm.core import convert as cv
from psmm.core import saves
from psmm.core.card import MemoryCard
from psmm.core.formats import Layout

DATA = Path(__file__).parent / "data" / "ps2"
SAVE = "BESCES-50501REZ"  # Rez (Europe)


@pytest.fixture(autouse=True)
def data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("PSMM_DATA_DIR", str(tmp_path / "data"))


@pytest.fixture
def real_card(tmp_path):
    """mc01.ps2: 8 MB with ECC, the Rez save and the console's system folder."""
    p = tmp_path / "mc01.ps2"
    p.write_bytes(gzip.decompress((DATA / "mc01.ps2.gz").read_bytes()))
    return p


def _files(card: MemoryCard, folder: str) -> dict[str, bytes]:
    return {e.name: card.read_file(e.path) for e in card.stat(folder).children}


def _md5(p) -> str:
    return hashlib.md5(Path(p).read_bytes()).hexdigest()


def test_real_card(real_card):
    with MemoryCard(real_card, make_backups=False) as c:
        assert c.format.layout is Layout.ECC and c.format.nominal_mb == 8
        assert c.check()[0]
        names = {e.name: e.title for e in c.tree()}
        assert names == {"BEDATA-SYSTEM": "Your System Configuration", SAVE: "Rez"}
        assert cv.guess_game_id(c, real_card.name) == "SCES-50501"
        icon = c.icon("/" + SAVE)
        assert icon is not None and icon.data[:4] == b"\x00\x00\x01\x00"


def test_real_card_as_opl_vmc(real_card, tmp_path):
    """Console card -> OPL VMC (raw, named like OPL does) -> ECC -> raw again."""
    with MemoryCard(real_card, make_backups=False) as src:
        want = {e.name: _files(src, e.path) for e in src.tree()}
        vmc = cv.convert(src, tmp_path / "SCES_505.01_0.bin", ecc=False)
    with MemoryCard(vmc, make_backups=False) as v:
        assert v.format.layout is Layout.RAW and v.check()[0]
        assert cv.guess_game_id(v, vmc.name) == cv.game_id_from_text(vmc.name) == "SCES-50501"
        assert {e.name: _files(v, e.path) for e in v.tree()} == want
        ecc = cv.convert(v, tmp_path / "back.ps2", ecc=True)
    with MemoryCard(ecc, make_backups=False) as e:
        back = cv.convert(e, tmp_path / "back.bin", ecc=False)
    assert _md5(back) == _md5(vmc)


@pytest.mark.parametrize("ext", ["cbs", "max", "psu", "sps", "xps"])
def test_real_save_formats(real_card, tmp_path, ext):
    """Every format of the same save imports to exactly the files on the card."""
    with MemoryCard(real_card, make_backups=False) as src:
        want = _files(src, "/" + SAVE)
    sf, _fmt = saves.load((DATA / f"{SAVE}.{ext}").read_bytes(), f"{SAVE}.{ext}")
    with MemoryCard.create(tmp_path / "x.mcd", 8, ecc=False) as c:
        with c.edit() as ed:
            assert ed.import_save(sf) == "/" + SAVE
        assert _files(c, "/" + SAVE) == want
        assert c.check()[0]


def test_real_ps3_psv(real_card, tmp_path):
    """A PS3 export of the same game (later progress): same files and icon, other data."""
    with MemoryCard(real_card, make_backups=False) as src:
        want = _files(src, "/" + SAVE)
    sf, fmt = saves.load((DATA / "BESCES-5050152455A.PSV").read_bytes(), "BESCES-5050152455A.PSV")
    assert fmt == "psv"
    with MemoryCard.create(tmp_path / "x.mcd", 8, ecc=False) as c:
        with c.edit() as ed:
            ed.import_save(sf)
        got = _files(c, "/" + SAVE)
    assert set(got) == set(want)
    assert got["icon.sys"] == want["icon.sys"] and got["rez.ico"] == want["rez.ico"]


@pytest.mark.parametrize("fmt", sorted(saves.EXPORT_FORMATS))
def test_real_export_round_trip(real_card, tmp_path, fmt):
    """Export the card's save and import it into another card: nothing changes."""
    with MemoryCard(real_card, make_backups=False) as src:
        want = _files(src, "/" + SAVE)
        blob = saves.dump(src.export_save("/" + SAVE), fmt)
    sf, _ = saves.load(blob, "x" + saves.EXPORT_FORMATS[fmt][0])
    with MemoryCard.create(tmp_path / "x.mcd", 8, ecc=False) as c:
        with c.edit() as ed:
            ed.import_save(sf)
        assert _files(c, "/" + SAVE) == want
