# This file is part of PSMemoryManager.
# SPDX-License-Identifier: GPL-3.0-or-later
import json
from pathlib import Path

import pytest

from psmm.core import sdcard as sd

FILES = [
    {"path": ".sd2psx/settings.ini", "size": 100},
    {"path": "MemoryCards/PS2/BOOT/BootCard-1.mcd", "size": 8388608},
    {"path": "MemoryCards/PS2/BOOT/BootCard-2.mcd", "size": 8388608},
    {"path": "MemoryCards/PS2/BOOT/BootCard.ini", "size": 30},
    {"path": "MemoryCards/PS2/Card1/Card1-1.mcd", "size": 8388608},
    {"path": "MemoryCards/PS2/Card3/Card3-2.mcd", "size": 8388608},
    {"path": "MemoryCards/PS2/Card3/Card3.bin", "size": 1024},
    {"path": "MemoryCards/PS2/SLUS-20963/SLUS-20963-1.mcd", "size": 67108864},
    {"path": "MemoryCards/PS1/Card1/Card1-1.mcd", "size": 131072},
    {"path": "MemoryCards/COH/BOOT/BootCard-1.mcd", "size": 1048576},
    {"path": "README.txt", "size": 5},
]
TEXTS = {
    ".sd2psx/settings.ini": "[General]\nMode=PS2\n[PS2]\nCardSize=16\nVariant=RETAIL\nCustomThing=42\n",
    "MemoryCards/PS2/BOOT/BootCard.ini": "[ChannelName]\n1=FMCB\r\n2=FunTuna\n\n",
}


def test_layout():
    lay = sd.parse_listing(FILES, TEXTS)
    assert [v.name for v in lay.variants] == ["PS2", "PS1", "COH"]
    ps2 = lay.variant("PS2")
    assert [f.label for f in ps2.folders] == ["BOOT", "Card 1", "Card 3", "SLUS-20963"]
    boot = ps2.find("BOOT")
    assert [(c.number, c.name) for c in boot.channels] == [(1, "FMCB"), (2, "FunTuna")]
    assert boot.names == {1: "FMCB", 2: "FunTuna"}
    lay2 = sd.parse_listing([FILES[1]] + [FILES[3]], TEXTS)  # INI names channel 2, but only channel 1 exists
    assert lay2.variant("PS2").find("BOOT").names[2] == "FunTuna"
    assert sd.layout_to_dict(lay2)["variants"][0]["folders"][0]["names"] == {"1": "FMCB", "2": "FunTuna"}
    assert boot.next_channel() == 3
    assert ps2.next_card_index() == 2  # Card1 and Card3 exist
    assert ps2.find("Card3").others == ["MemoryCards/PS2/Card3/Card3.bin"]
    assert ps2.find("Card3").next_channel() == 1
    assert lay.root_ok and lay.has_settings and not lay.has_game2folder
    d = sd.layout_to_dict(lay)
    json.dumps(d)  # serializable
    assert d["variants"][0]["folders"][0]["iniPath"] == "MemoryCards/PS2/BOOT/BootCard.ini"


def test_plans():
    lay = sd.parse_listing(FILES, TEXTS)
    assert sd.plan_new_card(lay, "PS2")["path"] == "MemoryCards/PS2/Card2/Card2-1.mcd"
    assert sd.plan_new_card(lay, "PS2", "sles_525.41")["path"] == "MemoryCards/PS2/SLES-52541/SLES-52541-1.mcd"
    with pytest.raises(FileExistsError):
        sd.plan_new_card(lay, "PS2", "SLUS20963")
    with pytest.raises(ValueError):
        sd.plan_new_card(lay, "PS2", "not a game")
    assert sd.plan_new_channel(lay, "PS2", "BOOT")["path"] == "MemoryCards/PS2/BOOT/BootCard-3.mcd"
    assert sd.plan_new_card(lay, "PS2")["path"].startswith("MemoryCards/PS2/Card2/")
    assert sd.plan_new_card(sd.parse_listing([], {}), "PS2")["path"] == "MemoryCards/PS2/Card1/Card1-1.mcd"


def test_settings_roundtrip_keeps_unknown_keys():
    text = TEXTS[".sd2psx/settings.ini"]
    info = sd.read_settings(text)
    values = {f"{s['section']}.{s['key']}": s["value"] for s in info["settings"]}
    assert values["PS2.CardSize"] == "16" and values["PS2.Autoboot"] == "ON"  # default
    assert info["extra"] == [{"section": "PS2", "key": "CustomThing", "value": "42"}]
    out = sd.write_settings(text, {"PS2.CardSize": "8", "PS1.GameID": "off", "General.FlippedScreen": "ON"})
    ini = sd.IniFile(out)
    assert ini.get("PS2", "CardSize") == "8" and ini.get("PS2", "CustomThing") == "42"
    assert ini.get("PS1", "GameID") == "OFF" and ini.get("General", "FlippedScreen") == "ON"
    assert out.endswith("\n\n")
    with pytest.raises(ValueError):
        sd.write_settings(text, {"PS2.CardSize": "7"})
    assert sd.default_card_size_mb(text) == 16


def test_remove_channel_name():
    text = "[ChannelName]\n1=FMCB\n2=FunTuna\n[Settings]\nMaxChannels=8\n"
    out = sd.remove_channel_name(text, 2)
    ini = sd.IniFile(out)
    assert ini.items("ChannelName") == [("1", "FMCB")] and ini.get("Settings", "MaxChannels") == "8"
    assert sd.remove_channel_name(text, 5) is None  # no name -> nothing to write
    assert sd.remove_channel_name("", 1) is None


def test_channel_names_and_game2folder():
    out = sd.write_channel_names("[Settings]\nMaxChannels=8\n[ChannelName]\n1=Old\n", {1: "New", 3: "Third", 4: " "})
    ini = sd.IniFile(out)
    assert ini.items("ChannelName") == [("1", "New"), ("3", "Third")]
    assert ini.get("Settings", "MaxChannels") == "8"
    g = sd.write_game2folder("", [{"platform": "PS2", "game": "slus_209.63", "folder": "Card2"},
                                  {"platform": "PS1", "game": "SCUS-94163", "folder": "FF7"}])
    assert sd.read_game2folder(g) == [{"platform": "PS1", "game": "SCUS-94163", "folder": "FF7"},
                                      {"platform": "PS2", "game": "SLUS-20963", "folder": "Card2"}]
    with pytest.raises(ValueError):
        sd.write_game2folder("", [{"platform": "PS2", "game": "SLUS-20963", "folder": "../x"}])


def test_web_api_sd(tmp_path, monkeypatch):
    from psmm import web_api as w

    monkeypatch.setattr(w, "WORK", tmp_path)
    monkeypatch.setattr(w, "EXPORT", tmp_path / "out.bin")
    r = json.loads(w.sd_load(json.dumps(FILES), json.dumps(TEXTS)))
    assert r["ok"] and r["defaultSizeMB"] == 16 and r["variants"][0]["name"] == "PS2"
    assert json.loads(w.sd_plan_card("PS2"))["folder"] == "Card2"
    assert json.loads(w.sd_plan_card("PS1"))["kind"] == "card"
    assert json.loads(w.sd_plan_card("PS2", "xyz"))["kind"] == "card"
    assert json.loads(w.sd_plan_channel("PS2", "SLUS-20963"))["channel"] == 2
    r = json.loads(w.blank_card(1))
    assert r["ok"] and Path(r["path"]).stat().st_size == 1024 * 1024
    r = json.loads(w.sd_write_settings(json.dumps({"PS2.CardSize": "8"})))
    assert "CardSize=8" in r["text"] and r["path"] == ".sd2psx/settings.ini"
    r = json.loads(w.sd_write_channel_names("MemoryCards/PS2/BOOT/BootCard.ini", json.dumps({"1": "A", "2": "B"})))
    assert r["text"].startswith("[ChannelName]\n1=A\n2=B")


SAMPLES = Path.home() / "psxmemcard_novo"


@pytest.mark.skipif(not SAMPLES.is_dir(), reason="Gen2 sample folder not available")
def test_real_sd_sample_read_only():
    files, texts = sd.scan_local(SAMPLES)
    lay = sd.parse_listing(files, texts)
    boot = lay.variant("PS2").find("BOOT")
    assert len(boot.channels) == 6 and boot.channels[0].name
