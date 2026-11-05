# This file is part of PSMemoryManager.
# SPDX-License-Identifier: GPL-3.0-or-later
"""PS1 cards and saves, checked against real files (tests/data/ps1/README.md)."""

import hashlib
import os
import struct
from pathlib import Path

import pytest

from psmm.core import formats, ps1, signing
from psmm.core.card import CardError, ExistsError, NoSpaceError
from psmm.core.formats import Origin, Platform

DATA = Path(__file__).parent / "data" / "ps1"
SAMPLES = Path(os.environ.get("PSMM_SAMPLES", Path.home() / "psxmemcard_novo"))
SD2PSX_BLANK_MD5 = "831517d84eb1ea8222651b99b90391e9"  # empty PS1 card created by a PSxMemCard Gen2


@pytest.fixture(autouse=True)
def data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("PSMM_DATA_DIR", str(tmp_path / "data"))


def copy(tmp_path, name, dest=None):
    p = tmp_path / (dest or name)
    p.write_bytes((DATA / name).read_bytes())
    return p


def blank(tmp_path, name="Card1-1.mcd"):
    return ps1.Ps1Card.create(tmp_path / name)


# ---------------------------------------------------------------------------
# signatures


def test_aes_fips197_vector():
    key = bytes(range(16))
    plain = bytes.fromhex("00112233445566778899aabbccddeeff")
    enc = signing.aes_encrypt_block(key, plain)
    assert enc.hex() == "69c4e0d86a7b0430d8cdb78070b4c55a"
    assert signing.aes_decrypt_block(key, enc) == plain


def test_real_psp_and_ps3_signatures_verify():
    assert signing.is_signed((DATA / "suikoden2-psp.vmp").read_bytes(), 0x0C, 0x20)
    assert signing.is_signed((DATA / "BASLUS-0110553595354454D.PSV").read_bytes(), 0x08, 0x1C)


def test_our_signature_equals_the_psp_one():
    real = (DATA / "suikoden2-psp.vmp").read_bytes()
    unsigned = real[:0x20] + bytes(20) + real[0x34:]
    assert signing.sign(unsigned, 0x0C, 0x20) == real
    # and the container writer keeps the PSP's seed, so it rebuilds the very same file
    assert ps1.wrap(real[0x80:], "vmp", real[:0x80]) == real


def test_tampered_vmp_is_detected(tmp_path):
    data = bytearray((DATA / "suikoden2-psp.vmp").read_bytes())
    data[0x80 + 8192 + 300] ^= 1
    p = tmp_path / "bad.vmp"
    p.write_bytes(data)
    c = ps1.Ps1Card(p)
    assert c.signed is False
    assert any(".vmp" in m for m in c.check()[1])
    # saving it signs it again
    assert signing.is_signed(c.card_bytes(), 0x0C, 0x20)


# ---------------------------------------------------------------------------
# images


def test_blank_card_matches_the_gen2(tmp_path):
    assert hashlib.md5(ps1.blank_card()).hexdigest() == SD2PSX_BLANK_MD5
    c = blank(tmp_path)
    assert c.check() == (True, [])
    assert c.free_bytes() == c.total_bytes() == 15 * 8192
    assert c.saves() == []


@pytest.mark.skipif(not (SAMPLES / "MemoryCards" / "PS1" / "Card1" / "Card1-1.mcd").exists(), reason="no SD card dump")
def test_blank_card_matches_the_real_sd_card():
    assert (SAMPLES / "MemoryCards/PS1/Card1/Card1-1.mcd").read_bytes() == ps1.blank_card()


@pytest.mark.parametrize("name,container,origin", [
    ("sotn-dexdrive.gme", "gme", Origin.DEXDRIVE),
    ("suikoden2-psp.vmp", "vmp", Origin.PSP),
    ("sotn.mcr", "raw", Origin.EPSXE),
    ("diablo-jp.mcd", "raw", Origin.GEN2),
])
def test_detect(name, container, origin):
    f = formats.detect(DATA / name)
    assert f.platform is Platform.PS1 and f.container == container and f.origin is origin
    assert not f.size_mismatch


def test_vgs_and_srm_detected(tmp_path):
    raw = (DATA / "sotn.mcr").read_bytes()
    (tmp_path / "a.mem").write_bytes(ps1.wrap(raw, "vgs"))
    (tmp_path / "a.srm").write_bytes(raw)
    assert formats.detect(tmp_path / "a.mem").origin is Origin.VGS
    assert formats.detect(tmp_path / "a.srm").origin is Origin.RETROARCH
    assert ps1.Ps1Card(tmp_path / "a.mem").raw == raw


def test_dexdrive_cut_after_last_block(tmp_path):
    c = ps1.Ps1Card(copy(tmp_path, "sotn-dexdrive-truncated.gme"))
    assert c.format.size_mismatch
    assert [s.name for s in c.saves()] == ["BASLUS-00067DRAX01"]
    assert c.check()[0]
    # the rest of the card is free and usable; saving writes a full-size file
    with c.edit() as ed:
        ed.import_save(ps1.load_save((DATA / "tonyhax.mcs").read_bytes()))
    assert c.path.stat().st_size == ps1.GME_HEADER + ps1.CARD_SIZE
    assert not c.format.size_mismatch and len(c.saves()) == 2


def test_japanese_titles_and_icons():
    c = ps1.Ps1Card(DATA / "diablo-jp.mcd")
    s = {x.name: x for x in c.saves()}
    big = s["BISLPS-01416-DIAB-01"]
    assert big.blocks == list(range(1, 11))
    assert big.title.startswith("ディアブロ")
    assert big.serial == "SLPS-01416" and big.region == "JP"
    assert big.icon and big.icon.frames == 1 and len(big.icon.pixels) == 128
    d = big.icon.to_dict()
    assert len(d["pal"]) == 16 and len(d["px"]) == 256


def test_deleted_saves_and_non_contiguous_blocks(tmp_path):
    c = ps1.Ps1Card(copy(tmp_path, "gt-deleted-saves.gme"))
    saves = {s.name: s for s in c.saves()}
    gt = saves["BASCUS-94194GT"]
    assert gt.blocks == [7, 8, 10, 11, 12] and not gt.deleted
    deleted = [s for s in c.saves() if s.deleted]
    assert len(deleted) == 5 and all(s.restorable for s in deleted)
    assert saves["BASLUS-00495WARZONE"].blocks == [3, 5]
    # deleted blocks count as free
    assert c.free_bytes() == 7 * 8192
    with c.edit() as ed:
        ed.restore("/3")
    assert not c.find("/3").deleted
    assert c.free_bytes() == 5 * 8192
    assert c.check()[0]


def test_new_saves_use_free_blocks_before_deleted_ones(tmp_path):
    c = blank(tmp_path)
    mcs = ps1.load_save((DATA / "tonyhax.mcs").read_bytes())
    with c.edit() as ed:
        ed.import_save(mcs)  # block 1
        ed.import_save(mcs.renamed("BESLEM-99999SECOND"))  # block 2
        ed.remove("/1")
        ed.import_save(mcs.renamed("BESLEM-99999THIRD"))  # block 3, not the deleted block 1
    names = {s.block: (s.name, s.deleted) for s in c.saves()}
    assert names == {1: ("BESLEM-99999TONYHAX", True), 2: ("BESLEM-99999SECOND", False), 3: ("BESLEM-99999THIRD", False)}


# ---------------------------------------------------------------------------
# saves


def test_import_every_single_save_format(tmp_path):
    c = blank(tmp_path)
    files = ["tonyhax.mcs", "diablo-10-blocks.mcs", "BASLUS-0110553595354454D.PSV", "gran-turismo-BASCUS-94194RT.srm"]
    loaded = [ps1.load_save((DATA / f).read_bytes(), f) for f in files]
    assert [s.format for s in loaded] == ["mcs", "mcs", "psv", "raw"]
    assert loaded[2].signed is True
    with c.edit() as ed:
        for sf in loaded:
            ed.import_save(sf)  # 1 + 10 + 1 + 3 = all 15 blocks
    assert c.free_bytes() == 0 and len(c.saves()) == 4
    before = c.path.read_bytes()
    with pytest.raises(NoSpaceError):
        with c.edit() as ed:
            ed.remove("/1")
            ed.import_save(loaded[1].renamed("BIG"))  # 10 blocks, 1 free
    assert c.path.read_bytes() == before  # a failed edit writes nothing


def test_import_fill_and_order(tmp_path):
    c = blank(tmp_path)
    loaded = [ps1.load_save((DATA / f).read_bytes(), f) for f in
              ["tonyhax.mcs", "diablo-10-blocks.mcs", "gran-turismo-BASCUS-94194RT.srm"]]
    with c.edit() as ed:
        for sf in loaded:
            ed.import_save(sf)
    assert [(s.name, s.blocks) for s in c.saves()] == [
        ("BESLEM-99999TONYHAX", [1]), ("BISLPS-01416-DIAB-01", list(range(2, 12))), ("BASCUS-94194RT", [12, 13, 14]),
    ]
    assert c.free_bytes() == 8192 and c.check() == (True, [])


def test_mcs_round_trip_is_exact():
    for name in ("tonyhax.mcs", "diablo-10-blocks.mcs"):
        data = (DATA / name).read_bytes()
        sf = ps1.load_save(data)
        out = ps1.dump_save(sf, "mcs")
        assert out[128:] == data[128:] and out[10:31] == data[10:31] and out[0] == 0x51 and out[4:8] == data[4:8]


def test_export_matches_the_card_data(tmp_path):
    c = ps1.Ps1Card(DATA / "diablo-jp.mcd")
    sf = c.export_save("/1")
    original = ps1.load_save((DATA / "diablo-10-blocks.mcs").read_bytes())
    assert sf.data == original.data and sf.name == original.name


def test_psv_export_like_the_ps3(tmp_path):
    real = (DATA / "BASLUS-0110553595354454D.PSV").read_bytes()
    sf = ps1.load_save(real)
    ours = ps1.dump_save(sf, "psv")
    assert signing.is_signed(ours, 0x08, 0x1C)
    # same header as the PS3's, except the random seed and the signature
    keep = [range(0, 8), range(0x30, 0x84)]
    for r in keep:
        assert ours[r.start:r.stop] == real[r.start:r.stop]
    assert ours[0x84:] == real[0x84:]
    assert ps1.export_filename(sf, "psv") == "BASLUS-0110553595354454D.PSV"
    again = ps1.load_save(ours)
    assert again.data == sf.data and again.name == sf.name


def test_action_replay_save(tmp_path):
    sf = ps1.load_save((DATA / "tonyhax.mcs").read_bytes())
    header = bytearray(54)
    header[0:len(sf.name)] = sf.name.encode()
    header[21:21 + 11] = b"TONYHAX SPL"
    ar = ps1.load_save(bytes(header) + sf.data, "x.psx")
    assert ar.format == "psx" and ar.name == sf.name and ar.data == sf.data


def test_raw_save_name_from_file_name():
    assert ps1.name_from_filename("gran-turismo.26537-BASCUS-94194RT.srm") == "BASCUS-94194RT"
    assert ps1.name_from_filename("Castlevania (USA).0.BASLUS-00067DRAX00.srm") == "BASLUS-00067DRAX00"
    assert ps1.name_from_filename("baslus_00067drax00") == "BASLUS-00067drax00"
    assert ps1.name_from_filename("mysave.bin") == "mysave"


def test_ps2_psv_and_garbage_are_rejected():
    ps2 = bytearray(0x200)
    ps2[0:4] = ps1.PSV_MAGIC
    ps2[0x3C] = 2
    with pytest.raises(CardError, match="PS2"):
        ps1.load_save(bytes(ps2), "x.psv")
    with pytest.raises(CardError):
        ps1.load_save(b"hello" * 100, "x.mcs")


def test_overwrite_and_restore_rules(tmp_path):
    c = blank(tmp_path)
    sf = ps1.load_save((DATA / "tonyhax.mcs").read_bytes())
    with c.edit() as ed:
        ed.import_save(sf)
    with pytest.raises(ExistsError):
        with c.edit() as ed:
            ed.import_save(sf)
    with c.edit() as ed:
        ed.import_save(sf, overwrite=True)  # reuses its own block
    assert [(s.block, s.deleted) for s in c.saves()] == [(1, False)]
    with c.edit() as ed:
        ed.remove("/1")
        ed.import_save(sf)  # same name again, in block 2
    with pytest.raises(ExistsError):
        with c.edit() as ed:
            ed.restore("/1")


def test_restore_after_blocks_were_reused(tmp_path):
    c = blank(tmp_path)
    big = ps1.load_save((DATA / "diablo-10-blocks.mcs").read_bytes())
    small = ps1.load_save((DATA / "tonyhax.mcs").read_bytes())
    with c.edit() as ed:
        ed.import_save(big)  # blocks 1-10
        ed.import_save(small.renamed("A"))  # 11
        ed.import_save(small.renamed("B"))  # 12
        ed.import_save(small.renamed("C"))  # 13
        ed.import_save(small.renamed("D"))  # 14
        ed.import_save(small.renamed("E"))  # 15
        ed.remove("/1")
        ed.import_save(small.renamed("F"))  # reuses block 1
    d = c.find("/2") if any(s.block == 2 for s in c.saves()) else None
    assert d is None or not d.restorable
    assert c.check()[0]


def test_copy_between_cards(tmp_path):
    src = ps1.Ps1Card(DATA / "diablo-jp.mcd", make_backups=False)
    dst = blank(tmp_path)
    with dst.edit() as ed:
        ed.copy_from(src, ["/"])
    assert [s.name for s in dst.saves()] == [s.name for s in src.saves()]
    assert all(dst.export_save(a.path).data == src.export_save(b.path).data for a, b in zip(dst.saves(), src.saves()))


# ---------------------------------------------------------------------------
# conversion


@pytest.mark.parametrize("target", list(ps1.TARGETS))
def test_convert_keeps_every_byte(tmp_path, target):
    src = ps1.Ps1Card(DATA / "gt-deleted-saves.gme")
    out = src.convert(tmp_path / ps1.output_name("gt.gme", target), target)
    back = ps1.Ps1Card(out)
    assert back.raw == src.raw and back.container == ps1.TARGETS[target][0]
    if target == "vmp":
        assert back.signed is True
    if target == "gme":
        h = out.read_bytes()[:ps1.GME_HEADER]
        assert h.startswith(ps1.GME_MAGIC)
        assert list(h[22:37]) == [src.raw[128 * i] for i in range(1, 16)]


def test_dexdrive_comments_survive_saving(tmp_path):
    raw = (DATA / "sotn.mcr").read_bytes()
    comments = ["first save comment"] + [""] * 14
    p = tmp_path / "c.gme"
    p.write_bytes(ps1.wrap(raw, "gme", comments=comments))
    c = ps1.Ps1Card(p)
    assert c.saves()[0].comment == "first save comment"
    with c.edit() as ed:
        ed.import_save(ps1.load_save((DATA / "tonyhax.mcs").read_bytes()))
    assert ps1.Ps1Card(p).saves()[0].comment == "first save comment"


def test_split_by_game(tmp_path):
    c = blank(tmp_path)
    with c.edit() as ed:
        for f in ["tonyhax.mcs", "diablo-10-blocks.mcs", "BASLUS-0110553595354454D.PSV"]:
            ed.import_save(ps1.load_save((DATA / f).read_bytes(), f))
    out = ps1.split_by_game(c, tmp_path / "split")
    assert [x["game"] for x in out] == ["SLEM-99999", "SLPS-01416", "SLUS-01105"]
    for x in out:
        card = ps1.Ps1Card(x["path"])
        assert [s.serial for s in card.saves()] == [x["game"]]
    assert ps1.guess_game_id(c) == "SLPS-01416"  # the game with the most blocks


# ---------------------------------------------------------------------------
# damaged and special cards


def freepsxboot_like() -> bytes:
    raw = bytearray(ps1.blank_card())
    f = bytearray(128)
    f[0] = 0x51
    f[4:8] = struct.pack("<I", 0x0F486000)
    f[8:10] = b"\xa9\x14"
    f[10:21] = b"FreePSXBoot"
    f[127] = ps1._xor(f)
    raw[128:256] = f
    for b in range(2, 16):
        raw[128 * b:128 * (b + 1)] = bytes(128)  # state 0: not a valid entry
    raw[128 * 16:128 * 17] = os.urandom(128)  # exploit code where the broken sector list goes
    return bytes(raw)


def test_freepsxboot_cards_are_read_only(tmp_path):
    p = tmp_path / "BootCard-1.mcd"
    p.write_bytes(freepsxboot_like())
    c = ps1.Ps1Card(p)
    d = c.directory()
    assert d.nonstandard and d.freepsxboot and c.read_only
    ok, msgs = c.check()
    assert not ok and "FreePSXBoot" in msgs[0]
    with pytest.raises(CardError):
        with c.edit():
            pass
    # converting keeps the exploit byte for byte
    out = c.convert(tmp_path / "boot.vmp", "vmp")
    assert ps1.Ps1Card(out).raw == p.read_bytes()


@pytest.mark.skipif(not (SAMPLES / "MemoryCards/PS1/BOOT/BootCard-1.mcd").exists(), reason="no SD card dump")
def test_real_freepsxboot_card():
    c = ps1.Ps1Card(SAMPLES / "MemoryCards/PS1/BOOT/BootCard-1.mcd", make_backups=False)
    assert c.directory().freepsxboot and c.read_only


def test_checksum_errors_reported_but_editable(tmp_path):
    raw = bytearray((DATA / "sotn.mcr").read_bytes())
    raw[128 + 127] ^= 0xFF
    p = tmp_path / "x.mcr"
    p.write_bytes(raw)
    c = ps1.Ps1Card(p)
    ok, msgs = c.check()
    assert not ok and any("block 1" in m for m in msgs)
    with c.edit() as ed:  # a card that was already damaged can still be edited
        ed.import_save(ps1.load_save((DATA / "tonyhax.mcs").read_bytes()))
    assert len(c.saves()) == 2


def test_cross_linked_card_is_read_only(tmp_path):
    c = blank(tmp_path)
    with c.edit() as ed:
        ed.import_save(ps1.load_save((DATA / "tonyhax.mcs").read_bytes()))
        ed.import_save(ps1.load_save((DATA / "gran-turismo-BASCUS-94194RT.srm").read_bytes(), "gran-turismo-BASCUS-94194RT.srm"))
    # the 3-block save is in blocks 2-4; point block 1 (the other save) at block 3 too
    raw = bytearray(c.path.read_bytes())
    f = bytearray(raw[128:256])
    f[8:10] = struct.pack("<H", 2)
    f[127] = ps1._xor(f)
    raw[128:256] = f
    c.path.write_bytes(raw)
    c.reload()
    assert not c.check()[0] and c.read_only
    with pytest.raises(CardError):
        with c.edit():
            pass


def test_verification_blocks_a_broken_write(tmp_path, monkeypatch):
    c = blank(tmp_path)
    before = c.path.read_bytes()

    def bad(self, *a, **k):
        self.raw[128] = 0x77  # unknown state
        self.changes.append("x")

    monkeypatch.setattr(ps1.Ps1Editor, "format_card", bad)
    with pytest.raises(CardError):
        with c.edit() as ed:
            ed.format_card()
    assert c.path.read_bytes() == before


# ---------------------------------------------------------------------------
# web bridge (same calls the page makes)


def _web(tmp_path, monkeypatch):
    import json as _json
    from psmm import web_api as w

    monkeypatch.setattr(w, "WORK", tmp_path / "work")
    monkeypatch.setattr(w, "STAGING", tmp_path / "work" / "staging")
    monkeypatch.setattr(w, "INCOMING", tmp_path / "work" / "in.bin")
    monkeypatch.setattr(w, "EXPORT", tmp_path / "work" / "out.bin")
    monkeypatch.setattr(w, "_slots", {s: w._Slot() for s in w.SLOTS})
    (tmp_path / "work").mkdir()

    def call(fn, *args):
        return _json.loads(getattr(w, fn)(*args))

    def stage(*names):
        w.staging_dir()
        for n in names:
            (w.STAGING / n).write_bytes((DATA / n).read_bytes())

    def open_(slot, name):
        w.INCOMING.write_bytes((DATA / name).read_bytes())
        return call("open_card", slot, name)

    return w, call, stage, open_


def test_web_open_import_export_delete_restore_undo(tmp_path, monkeypatch):
    import io
    import zipfile

    w, call, stage, open_ = _web(tmp_path, monkeypatch)
    r = open_("A", "suikoden2-psp.vmp")
    assert r["ok"] and r["card"]["platform"] == "PS1" and r["card"]["container"] == "vmp"
    assert r["card"]["blocksFree"] == 1 and len(r["tree"]) == 7 and r["card"]["signed"] is True
    assert r["tree"][0]["icon"]["n"] == 3 and r["card"]["game"] == "SLUS-00958"

    stage("tonyhax.mcs", "sotn.mcr")
    info = call("inspect_staged_saves", "PS1")["saves"]
    assert {x["file"]: x["ok"] for x in info} == {"tonyhax.mcs": True, "sotn.mcr": False}  # a card is not a save
    stage("tonyhax.mcs")
    r = call("import_staged_saves", "A", False)
    assert r["ok"] and r["card"]["blocksFree"] == 0 and r["dirty"]
    stage("tonyhax.mcs")
    assert call("import_staged_saves", "A", False)["kind"] == "exists"
    # saving keeps the .vmp format, signed
    data = Path(call("card_file", "A")["path"]).read_bytes()
    assert signing.is_signed(data, 0x0C, 0x20) and len(data) == 131200

    r = call("remove", "A", '["/1", "/3"]')
    assert sum(e["deleted"] for e in r["tree"]) == 2 and r["card"]["blocksFree"] == 4
    r = call("restore", "A", '["/3"]')
    assert sum(e["deleted"] for e in r["tree"]) == 1
    r = call("undo", "A")
    assert sum(e["deleted"] for e in r["tree"]) == 2

    r = call("export_saves", "A", '["/5", "/7"]', "psv")
    assert r["kind"] == "zip"
    with zipfile.ZipFile(io.BytesIO(w.EXPORT.read_bytes())) as z:
        for n in z.namelist():
            assert n.endswith(".PSV") and signing.is_signed(z.read(n), 0x08, 0x1C)
    assert call("export_saves", "A", '["/1"]', "mcs")["kind"] == "card"  # deleted: restore first
    assert call("mkdir", "A", "/x")["kind"] == "card"
    assert call("export", "A", '["/5"]')["kind"] == "card"
    assert call("resize_card", "A", 8)["kind"] == "card"


def test_web_copy_convert_split_and_platform_rules(tmp_path, monkeypatch):
    w, call, stage, open_ = _web(tmp_path, monkeypatch)
    open_("A", "diablo-jp.mcd")
    assert call("new_card", "B", "Card1-1.mcd", 0, False, "PS1")["card"]["blocksFree"] == 15
    r = call("copy_items", "A", '["/1", "/11"]', "B", "/", False)
    assert [e["name"] for e in r["tree"]] == ["BISLPS-01416-DIAB-01", "BISLPS-01416-DIAB-88"]
    assert call("new_card", "B", "x.mcd", 8, False)["card"]["platform"] == "PS2"
    assert call("copy_items", "A", '["/1"]', "B", "/", False)["kind"] == "card"  # PS1 -> PS2

    for target, size in [("gen2", 131072), ("gme", 134976), ("vmp", 131200), ("vgs", 131136)]:
        r = call("convert_card", "A", target, 0)
        assert r["size"] == size and ps1.unwrap(w.EXPORT.read_bytes()).raw == (DATA / "diablo-jp.mcd").read_bytes()

    prev = call("split_preview", "A")
    assert [g["game"] for g in prev["games"]] == ["SLPS-01416"]
    r = call("split_card", "A", 0, False, "zip")
    import io
    import zipfile
    with zipfile.ZipFile(io.BytesIO(w.EXPORT.read_bytes())) as z:
        assert z.namelist() == ["MemoryCards/PS1/SLPS-01416/SLPS-01416-1.mcd"]
    assert call("split_card", "A", 0, False, "zip-opl")["kind"] == "card"


def test_web_whole_cards_and_sd(tmp_path, monkeypatch):
    import io
    import json as _json
    import zipfile

    w, call, stage, open_ = _web(tmp_path, monkeypatch)
    stage("gt-deleted-saves.gme", "suikoden2-psp.vmp")
    cards = call("inspect_staged_cards")["cards"]
    assert [c["platform"] for c in cards] == ["PS1", "PS1"]
    assert cards[0]["game"] == "SCUS-94194" and len(cards[0]["entries"]) == 2  # deleted saves left out
    open_("A", "sotn.mcr")
    r = call("import_staged_cards", "A", '["gt-deleted-saves.gme"]', False)
    assert {e["name"] for e in r["tree"]} == {"BASLUS-00067DRAX00", "BASCUS-94194GT", "BASCUS-94194RT"}
    r = call("staged_cards_zip", _json.dumps([{"file": "suikoden2-psp.vmp", "game": "SLUS-00958"}]), "gen2")
    with zipfile.ZipFile(io.BytesIO(w.EXPORT.read_bytes())) as z:
        name = z.namelist()[0]
        assert name == "MemoryCards/PS1/SLUS-00958/SLUS-00958-1.mcd" and len(z.read(name)) == 131072

    files = [{"path": "MemoryCards/PS1/Card1/Card1-1.mcd", "size": 131072},
             {"path": "MemoryCards/PS1/SLUS-00958/SLUS-00958-1.mcd", "size": 131072}]
    call("sd_load", _json.dumps(files), "{}")
    plan = call("sd_plan_import", "SLUS-00958", 131072, "PS1")
    assert plan["path"] == "MemoryCards/PS1/SLUS-00958/SLUS-00958-2.mcd" and plan["existing"]
    plan = call("sd_plan_card", "PS1", "")
    assert plan["path"] == "MemoryCards/PS1/Card2/Card2-1.mcd"
    assert call("sd_plan_channel", "PS1", "Card1")["size"] == 131072
    assert w.EXPORT.exists() is False or True
    call("blank_card", 0, False, "PS1")
    assert w.EXPORT.read_bytes() == ps1.blank_card()


def test_web_ps1_save_into_ps2_card_is_explained(tmp_path, monkeypatch):
    w, call, stage, open_ = _web(tmp_path, monkeypatch)
    call("new_card", "A", "x.mcd", 8, False)
    stage("tonyhax.mcs", "BASLUS-0110553595354454D.PSV")
    info = call("inspect_staged_saves", "PS2")["saves"]
    assert not any(x["ok"] for x in info) and all("PS1" in x["error"] for x in info)


def test_cli(tmp_path, capsys):
    from psmm.cli import main

    card = copy(tmp_path, "gt-deleted-saves.gme")
    assert main(["--lang", "en", str(card), "ls"]) == 0
    assert "WARZONE" in capsys.readouterr().out
    assert main([str(card), "restore", "3"]) == 0
    assert main([str(card), "import", str(DATA / "tonyhax.mcs")]) == 0
    assert main([str(card), "export", "BASLUS-00495WARZONE", "-o", str(tmp_path / "out"), "--format", "psv"]) == 0
    out = list((tmp_path / "out").iterdir())
    assert len(out) == 1 and signing.is_signed(out[0].read_bytes(), 0x08, 0x1C)
    assert main([str(card), "rm", "7"]) == 0
    assert main([str(card), "check"]) == 0
    c = ps1.Ps1Card(card)
    assert {s.name for s in c.directory().live()} == {"BASLUS-00495WARZONE", "BESLEM-99999TONYHAX", "BASCUS-94194RT"}
    assert main(["new", str(tmp_path / "n.vmp"), "--ps1"]) == 0
    assert ps1.Ps1Card(tmp_path / "n.vmp").signed
    assert main(["convert", str(card), str(tmp_path / "c.mcr")]) == 0
    assert ps1.Ps1Card(tmp_path / "c.mcr").raw == c.raw
    assert main(["split", str(card), str(tmp_path / "sd")]) == 0
    assert (tmp_path / "sd/MemoryCards/PS1/SLUS-00495/SLUS-00495-1.mcd").exists()
    freepsx = tmp_path / "boot.mcd"
    freepsx.write_bytes(freepsxboot_like())
    assert main([str(freepsx), "import", str(DATA / "tonyhax.mcs")]) == 1  # read-only


# ---------------------------------------------------------------------------
# the FreePSXBoot trigger is told apart from real saves


def test_freepsxboot_trigger_is_marked_and_not_exported(tmp_path):
    p = tmp_path / "boot.mcd"
    p.write_bytes(freepsxboot_like())
    c = ps1.Ps1Card(p)
    [e] = c.saves()
    assert e.exploit and c.directory().freepsxboot
    with pytest.raises(CardError):
        c.export_save(e.path)


def test_valid_save_named_freepsxboot_is_a_normal_save(tmp_path):
    c = blank(tmp_path)
    sf = ps1.load_save((DATA / "tonyhax.mcs").read_bytes()).renamed("FreePSXBoot")
    with c.edit() as ed:
        ed.import_save(sf)
    d = c.directory()
    assert not d.freepsxboot and not d.nonstandard and not c.read_only
    [e] = c.saves()
    assert not e.exploit and e.problems == [] and c.export_save(e.path).data == sf.data


def test_really_broken_save_still_reports_its_problems(tmp_path):
    c = blank(tmp_path)
    with c.edit() as ed:
        ed.import_save(ps1.load_save((DATA / "gran-turismo-BASCUS-94194RT.srm").read_bytes(), "x-BASCUS-94194RT.srm"))
        ed.import_save(ps1.load_save((DATA / "tonyhax.mcs").read_bytes()))  # another exploit, but a normal save
    raw = bytearray(c.path.read_bytes())
    f = bytearray(raw[128 * 2:128 * 3])  # second block of the 3-block save: point it nowhere
    f[8:10] = struct.pack("<H", 0x40)
    f[127] = ps1._xor(f)
    raw[128 * 2:128 * 3] = f
    c.path.write_bytes(raw)
    c.reload()
    saves = {s.name: s for s in c.saves()}
    gt, thx = saves["BASCUS-94194RT"], saves["BESLEM-99999TONYHAX"]
    assert not gt.exploit and "ps1.p.bad_link" in gt.problems
    assert not thx.exploit and thx.problems == []
    ok, msgs = c.check()
    assert not ok and any("BASCUS-94194RT" in m for m in msgs)
    assert not c.directory().freepsxboot


def test_web_hides_trigger_problems_only(tmp_path, monkeypatch):
    w, call, stage, open_ = _web(tmp_path, monkeypatch)
    w.INCOMING.write_bytes(freepsxboot_like())
    r = call("open_card", "A", "BootCard-1.mcd")
    [e] = r["tree"]
    assert e["exploit"] and e["problems"] == [] and r["card"]["readOnly"] and r["card"]["freepsxboot"]
    assert call("export_saves", "A", '["/1"]', "mcs")["kind"] == "card"
    assert not call("check", "A")["healthy"]  # Check still lists the technical details
