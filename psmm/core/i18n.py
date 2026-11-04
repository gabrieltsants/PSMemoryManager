# This file is part of PSMemoryManager.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Translations for messages produced by the core (English is the default).

Errors carry a message key plus parameters and are rendered only when
converted to text, so changing the language later also changes how pending
errors and summaries are shown.
"""

from __future__ import annotations

import locale
import os

LANGUAGES = ("en", "pt")
DEFAULT = "en"
_lang = DEFAULT

MESSAGES: dict[str, dict[str, str]] = {
    # --- formats -------------------------------------------------------
    "fmt.folder_unsupported": {
        "en": "PCSX2 folder memory cards are not supported yet.",
        "pt": "Memory cards em pasta do PCSX2 ainda não são suportados.",
    },
    "fmt.read_failed": {
        "en": "Could not read the file: {error}",
        "pt": "Não foi possível ler o arquivo: {error}",
    },
    "fmt.bad_superblock": {
        "en": "Invalid PS2 superblock (impossible geometry).",
        "pt": "Superblock de PS2 inválido (geometria impossível).",
    },
    "fmt.truncated": {
        "en": "Truncated file: {size} bytes, expected {raw} (no ECC) or {ecc} (with ECC).",
        "pt": "Arquivo truncado: {size} bytes, esperado {raw} (sem ECC) ou {ecc} (com ECC).",
    },
    "fmt.blank": {"en": "Empty/unformatted image.", "pt": "Imagem vazia/não formatada."},
    "fmt.unknown": {
        "en": "Not a recognized PS2 memory card image.",
        "pt": "Não é uma imagem de memory card de PS2 reconhecida.",
    },
    "fmt.ps1_unsupported": {
        "en": "PS1 memory cards are not supported yet.",
        "pt": "Cartões de PS1 ainda não são suportados nesta versão.",
    },
    "fmt.describe_ps2": {"en": "PS2 · {mb} MB · {ecc} · {origin}", "pt": "PS2 · {mb} MB · {ecc} · {origin}"},
    "fmt.describe_ps1": {"en": "PS1 · 128 KB", "pt": "PS1 · 128 KB"},
    "ecc.yes": {"en": "with ECC", "pt": "com ECC"},
    "ecc.no": {"en": "no ECC", "pt": "sem ECC"},
    "origin.gen2": {"en": "PSxMemCard Gen2 / SD2PSX", "pt": "PSxMemCard Gen2 / SD2PSX"},
    "origin.opl": {"en": "OPL VMC", "pt": "OPL VMC"},
    "origin.pcsx2": {"en": "PCSX2", "pt": "PCSX2"},
    "origin.mcp2": {"en": "MemCard PRO2", "pt": "MemCard PRO2"},
    "origin.unknown": {"en": "Unknown", "pt": "Desconhecido"},
    # --- regions / attributes -----------------------------------------
    "region.US": {"en": "America", "pt": "América"},
    "region.EU": {"en": "Europe", "pt": "Europa"},
    "region.JP": {"en": "Japan", "pt": "Japão"},
    "region.KR": {"en": "Korea", "pt": "Coreia"},
    "region.CN": {"en": "China", "pt": "China"},
    "attr.protected": {"en": "protected", "pt": "protegido"},
    "attr.hidden": {"en": "hidden", "pt": "oculto"},
    "attr.ps1": {"en": "PS1", "pt": "PS1"},
    "attr.pocketstation": {"en": "PocketStation", "pt": "PocketStation"},
    # --- names ------------------------------------------------------------
    "name.empty": {"en": "Empty or invalid name.", "pt": "Nome vazio ou inválido."},
    "name.ascii": {
        "en": "“{name}”: memory cards only accept ASCII names (no accents).",
        "pt": "“{name}”: o memory card só aceita nomes ASCII (sem acentos).",
    },
    "name.too_long": {
        "en": "“{name}”: name longer than {max} characters.",
        "pt": "“{name}”: nome com mais de {max} caracteres.",
    },
    "name.bad_chars": {
        "en": "“{name}”: contains characters that are not allowed.",
        "pt": "“{name}”: contém caracteres não permitidos.",
    },
    # --- card errors ------------------------------------------------------
    "err.path_not_found": {"en": "Path not found: {path}", "pt": "Caminho não encontrado: {path}"},
    "err.file_not_found": {"en": "File not found: {path}", "pt": "Arquivo não encontrado: {path}"},
    "err.dir_not_found": {"en": "Folder not found: {path}", "pt": "Pasta não encontrada: {path}"},
    "err.corrupt": {"en": "Corrupted card: {error}", "pt": "Cartão corrompido: {error}"},
    "err.io": {"en": "I/O error: {error}", "pt": "Erro de E/S: {error}"},
    "err.root_entry": {"en": "The root has no entry of its own.", "pt": "A raiz não tem entrada própria."},
    "err.not_found": {"en": "Not found: {path}", "pt": "Não encontrado: {path}"},
    "err.exists": {"en": "Already exists: {path}", "pt": "Já existe: {path}"},
    "err.exists_dest": {"en": "Already exists at destination:\n{items}", "pt": "Já existe no destino:\n{items}"},
    "err.exists_dir": {
        "en": "A folder with that name already exists: {path}",
        "pt": "Já existe uma pasta com esse nome: {path}",
    },
    "err.exists_file": {
        "en": "A file with that name already exists: {path}",
        "pt": "Já existe um arquivo com esse nome: {path}",
    },
    "err.dest_missing": {
        "en": "Destination folder does not exist: {path}",
        "pt": "Pasta de destino não existe: {path}",
    },
    "err.no_space": {
        "en": "Not enough space: needs {need} KB, {free} KB free.",
        "pt": "Espaço insuficiente: precisa de {need} KB, livre {free} KB.",
    },
    "err.not_file_or_dir": {"en": "Not a file or folder: {path}", "pt": "Não é arquivo nem pasta: {path}"},
    "err.delete_root": {"en": "The root cannot be deleted.", "pt": "Não é possível apagar a raiz."},
    "err.workcopy": {
        "en": "Could not create the working copy: {error}",
        "pt": "Não foi possível criar a cópia de trabalho: {error}",
    },
    "err.verify_failed": {
        "en": "Verification failed after the change; the original card was not modified.\n{details}",
        "pt": "A verificação falhou depois da alteração; o cartão original não foi modificado.\n{details}",
    },
    "err.size_changed": {
        "en": "Card size changed during the edit; aborted.",
        "pt": "Tamanho do cartão mudou durante a edição; abortado.",
    },
    "err.bad_size": {
        "en": "Size must be 1, 2, 4, 8, 16, 32, 64 or 128 MB.",
        "pt": "Tamanho deve ser 1, 2, 4, 8, 16, 32, 64 ou 128 MB.",
    },
    "err.check_exception": {"en": "check error: {error}", "pt": "erro na verificação: {error}"},
    "err.no_card": {"en": "No card is open.", "pt": "Nenhum cartão aberto."},
    "err.nothing_to_add": {"en": "Nothing to add.", "pt": "Nada para adicionar."},
    "err.nothing_to_undo": {"en": "Nothing to undo.", "pt": "Nada para desfazer."},
    "err.nothing_selected": {"en": "Nothing selected.", "pt": "Nada selecionado."},
    # --- saves ------------------------------------------------------------
    "save.unknown": {
        "en": "{name}: not a recognized save file (.psu, .max, .cbs, .sps, .xps, .psv).",
        "pt": "{name}: não é um arquivo de save reconhecido (.psu, .max, .cbs, .sps, .xps, .psv).",
    },
    "save.corrupt": {"en": "{name}: damaged save file ({error}).", "pt": "{name}: arquivo de save danificado ({error})."},
    "save.bad_format": {"en": "Unsupported export format: {format}", "pt": "Formato de exportação não suportado: {format}"},
    "save.export_failed": {
        "en": "Could not export {name} as .{format}: {error}",
        "pt": "Não foi possível exportar {name} como .{format}: {error}",
    },
    "save.not_a_folder": {"en": "Not a save folder: {path}", "pt": "Não é uma pasta de save: {path}"},
    "save.has_subfolders": {
        "en": "{path} contains subfolders and cannot be exported as a save.",
        "pt": "{path} tem subpastas e não pode ser exportada como save.",
    },
    "err.same_card": {"en": "Source and destination are the same card.", "pt": "Origem e destino são o mesmo cartão."},
    "err.bad_slot": {"en": "Invalid card slot: {slot}", "pt": "Posição de cartão inválida: {slot}"},
    # --- SD card ------------------------------------------------------------
    "sd.bad_setting": {"en": "Invalid setting: {error}", "pt": "Configuração inválida: {error}"},
    "sd.bad_name": {"en": "Invalid channel name: {error}", "pt": "Nome de canal inválido: {error}"},
    "sd.bad_folder": {"en": "Invalid folder: {error}", "pt": "Pasta inválida: {error}"},
    "sd.bad_game_id": {
        "en": "“{game}” does not look like a game ID (e.g. SLUS-20963).",
        "pt": "“{game}” não parece um código de jogo (ex.: SLUS-20963).",
    },
    "sd.folder_exists": {"en": "The folder {folder} already exists.", "pt": "A pasta {folder} já existe."},
    "sd.no_channels": {
        "en": "This card already uses all {max} channels.",
        "pt": "Este cartão já usa os {max} canais.",
    },
    "sd.variant_unsupported": {
        "en": "Creating cards in {variant} is not supported yet.",
        "pt": "Criar cartões em {variant} ainda não é suportado.",
    },
    # --- conversion ---------------------------------------------------------
    "conv.page_size": {
        "en": "Cards with {size}-byte pages cannot be converted.",
        "pt": "Cartões com páginas de {size} bytes não podem ser convertidos.",
    },
    "conv.no_fit": {
        "en": "The content ({used} KB) does not fit in a {size} MB card.",
        "pt": "O conteúdo ({used} KB) não cabe num cartão de {size} MB.",
    },
    "conv.no_games": {
        "en": "No game saves (folders like BASLUS-20228...) on this card.",
        "pt": "Nenhum save de jogo (pastas como BASLUS-20228...) neste cartão.",
    },
    "conv.game_no_fit": {
        "en": "The saves of {game} do not fit in a {size} MB card: {error}",
        "pt": "Os saves de {game} não cabem num cartão de {size} MB: {error}",
    },
    "conv.same_size": {"en": "The card is already {size} MB.", "pt": "O cartão já tem {size} MB."},
    "conv.no_game_id": {
        "en": "{name}: enter the game code (e.g. SLUS-20228).",
        "pt": "{name}: informe o código do jogo (ex.: SLUS-20228).",
    },
    # --- change log -------------------------------------------------------
    "change.mkdir": {"en": "folder created: {path}", "pt": "pasta criada: {path}"},
    "change.write": {"en": "file written: {path}", "pt": "arquivo gravado: {path}"},
    "change.remove": {"en": "removed: {path}", "pt": "removido: {path}"},
    "change.import": {"en": "save imported: {path}", "pt": "save importado: {path}"},
    "change.rename": {"en": "renamed: {path} → {name}", "pt": "renomeado: {path} → {name}"},
    # --- command line -----------------------------------------------------
    "cli.description": {
        "en": "PS2 memory card manager (PSxMemCard Gen2, OPL, PCSX2, MemCard PRO2).",
        "pt": "Gerenciador de memory cards de PS2 (PSxMemCard Gen2, OPL, PCSX2, MemCard PRO2).",
    },
    "cli.no_backup": {"en": "do not back up before changing", "pt": "não fazer backup antes de alterar"},
    "cli.lang": {"en": "interface language (en, pt)", "pt": "idioma da interface (en, pt)"},
    "cli.card": {
        "en": "memory card file (.mcd, .bin, .vmc, .ps2, .mc2)",
        "pt": "arquivo do memory card (.mcd, .bin, .vmc, .ps2, .mc2)",
    },
    "cli.command": {"en": "command", "pt": "comando"},
    "cli.info": {"en": "card format and space", "pt": "formato e espaço do cartão"},
    "cli.ls": {"en": "list contents", "pt": "listar conteúdo"},
    "cli.extract": {"en": "extract files/folders to the PC", "pt": "extrair arquivos/pastas para o PC"},
    "cli.output": {"en": "destination folder (default: current)", "pt": "pasta de destino (padrão: atual)"},
    "cli.add": {"en": "add files/folders from the PC", "pt": "adicionar arquivos/pastas do PC"},
    "cli.directory": {"en": "destination folder on the card", "pt": "pasta de destino no cartão"},
    "cli.mkdir": {"en": "create folder", "pt": "criar pasta"},
    "cli.rm": {"en": "delete files/folders", "pt": "apagar arquivos/pastas"},
    "cli.recursive_rm": {"en": "delete non-empty folders", "pt": "apagar pastas com conteúdo"},
    "cli.rename": {"en": "rename file/folder", "pt": "renomear arquivo/pasta"},
    "cli.check": {"en": "check integrity", "pt": "verificar integridade"},
    "cli.new": {"en": "Create a formatted PS2 card.", "pt": "Criar cartão de PS2 formatado."},
    "cli.size": {"en": "MB (1-128, default 8)", "pt": "MB (1-128, padrão 8)"},
    "cli.ecc": {"en": "with ECC (PCSX2 format)", "pt": "com ECC (formato PCSX2)"},
    "cli.file": {"en": "File:", "pt": "Arquivo:"},
    "cli.format": {"en": "Format:", "pt": "Formato:"},
    "cli.size_label": {"en": "Size:", "pt": "Tamanho:"},
    "cli.geometry": {"en": "Geometry:", "pt": "Geometria:"},
    "cli.geometry_value": {
        "en": "page {page} B, {ppc} pages/cluster, {ppb} pages/block, {clusters} clusters",
        "pt": "página {page} B, {ppc} pág/cluster, {ppb} pág/bloco, {clusters} clusters",
    },
    "cli.version": {"en": "Version:", "pt": "Versão:"},
    "cli.space": {"en": "Space:", "pt": "Espaço:"},
    "cli.space_value": {
        "en": "{used} used, {free} free of {total}",
        "pt": "{used} usados, {free} livres de {total}",
    },
    "cli.size_mismatch": {
        "en": "WARNING: the file size does not match the header.",
        "pt": "AVISO: o tamanho do arquivo não bate com o cabeçalho.",
    },
    "cli.free": {"en": "{free} free", "pt": "{free} livres"},
    "cli.not_empty": {"en": "{path}: folder not empty (use -r)", "pt": "{path}: pasta não vazia (use -r)"},
    "cli.backup": {"en": "backup: {path}", "pt": "backup: {path}"},
    "cli.check_ok": {"en": "No errors found.", "pt": "Nenhum erro encontrado."},
    "cli.check_bad": {"en": "Problems were found.", "pt": "Foram encontrados problemas."},
    "cli.sd": {"en": "Show the cards on a PSxMemCard Gen2 / SD2PSX SD card (read-only).",
               "pt": "Mostrar os cartões de um SD do PSxMemCard Gen2 / SD2PSX (só leitura)."},
    "cli.sd_root": {"en": "root folder of the SD card", "pt": "pasta raiz do cartão SD"},
    "cli.sd_not_root": {"en": "No MemoryCards/ or .sd2psx/ folder found here.",
                        "pt": "Nenhuma pasta MemoryCards/ ou .sd2psx/ encontrada aqui."},
    "cli.resize": {"en": "change the card size in place (MB)", "pt": "mudar o tamanho do cartão no próprio arquivo (MB)"},
    "cli.merge": {"en": "copy everything from other cards into this one", "pt": "copiar tudo de outros cartões para este"},
    "cli.convert": {"en": "Convert a card to another format (with/without ECC) and/or size.",
                    "pt": "Converter um cartão para outro formato (com/sem ECC) e/ou tamanho."},
    "cli.convert_dest": {"en": "output file; the extension picks the format (.mcd .bin .mc2 = no ECC, .ps2 = ECC)",
                         "pt": "arquivo de saída; a extensão define o formato (.mcd .bin .mc2 = sem ECC, .ps2 = com ECC)"},
    "cli.convert_size": {"en": "new size in MB (default: same)", "pt": "novo tamanho em MB (padrão: o mesmo)"},
    "cli.split": {"en": "Create one card per game, laid out like a Gen2 SD card.",
                  "pt": "Criar um cartão por jogo, organizado como um SD do Gen2."},
    "cli.split_out": {"en": "SD card root (or any folder)", "pt": "raiz do cartão SD (ou qualquer pasta)"},
    "cli.split_others": {"en": "also copy non-game folders into every card",
                         "pt": "copiar também as pastas que não são de jogo para cada cartão"},
    "cli.error": {"en": "error: {error}", "pt": "erro: {error}"},
}


def normalize(lang: str | None) -> str:
    """'pt-BR', 'pt_PT.UTF-8' -> 'pt'; anything unsupported -> 'en'."""
    if not lang:
        return DEFAULT
    code = lang.replace("_", "-").split("-")[0].split(".")[0].lower()
    return code if code in LANGUAGES else DEFAULT


def set_language(lang: str | None) -> str:
    global _lang
    _lang = normalize(lang)
    return _lang


def get_language() -> str:
    return _lang


def detect_system_language() -> str:
    """Language from the environment (Linux/macOS) or the OS locale (Windows)."""
    for var in ("PSMM_LANG", "LC_ALL", "LC_MESSAGES", "LANG", "LANGUAGE"):
        val = os.environ.get(var)
        if val and val not in ("C", "POSIX", "C.UTF-8"):
            return normalize(val.split(":")[0])
    try:
        loc = locale.getlocale()[0]
    except (ValueError, TypeError):
        loc = None
    if loc and loc.lower().startswith("portuguese"):  # Windows: "Portuguese_Brazil"
        return "pt"
    return normalize(loc)


def t(key: str, **params) -> str:
    entry = MESSAGES.get(key)
    if entry is None:
        return key.format(**params) if params else key
    text = entry.get(_lang) or entry[DEFAULT]
    return text.format(**params) if params else text


class LocalizedError(Exception):
    """Exception whose text is the message ``key`` rendered in the current language."""

    def __init__(self, key: str, **params):
        super().__init__(key)
        self.key = key
        self.params = params

    def __str__(self) -> str:
        return t(self.key, **self.params)
