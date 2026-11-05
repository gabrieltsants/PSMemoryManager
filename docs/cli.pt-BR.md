# Linha de comando

[English](cli.md) · [Português (Brasil)](cli.pt-BR.md) · [Voltar ao README](../README.pt-BR.md)

O PSMemoryManager também roda no terminal, no Windows e no Linux (no macOS deve funcionar também). Tem os mesmos recursos da página web e é prático para scripts e para vários cartões de uma vez.

## 1. Instale o Python

É preciso o **Python 3.10 ou mais novo**.

- **Windows:** baixe em [python.org](https://www.python.org/downloads/). No instalador, marque **“Add python.exe to PATH”**.
- **Linux:** o Python normalmente já vem instalado. Confira com `python3 --version`.

## 2. Baixe o PSMemoryManager

Clone o repositório:

```bash
git clone https://github.com/gabrieltsants/PSMemoryManager.git
```

ou, na [página do GitHub](https://github.com/gabrieltsants/PSMemoryManager), clique em **Code → Download ZIP** e extraia.

## 3. Instale

Abra um terminal na pasta `PSMemoryManager` e rode:

```bash
pip install .
```

No Windows, se o `pip` não for encontrado, use `py -m pip install .`. Em algumas distribuições Linux pode ser preciso criar um ambiente virtual antes:

```bash
python3 -m venv ~/.psmm && . ~/.psmm/bin/activate
pip install .
```

## 4. Confira se funciona

```bash
psmm --help
```

Se o comando `psmm` não for encontrado, `python -m psmm --help` (Windows: `py -m psmm --help`) faz o mesmo.

## Como usar

Os comandos têm este formato:

```bash
psmm <arquivo do cartão> <comando> [opções]
```

As mensagens seguem o idioma do sistema. Use `--lang pt` ou `--lang en` para escolher. Todo comando aceita `-h` para a ajuda dele, por exemplo `psmm Card1-1.mcd export -h`.

**Backups:** todo comando que altera um cartão guarda antes uma cópia dele em:

- Linux: `~/.local/share/PSMemoryManager/backups`
- Windows: `%LOCALAPPDATA%\PSMemoryManager\backups`

Use `--no-backup` para não fazer a cópia.

### Cartões de PS2

| O quê | Comando |
|---|---|
| Formato e espaço livre | `psmm Card1-1.mcd info` |
| Listar o conteúdo (`-r`: dentro das pastas também) | `psmm Card1-1.mcd ls -r` |
| Copiar saves ou arquivos para o PC | `psmm Card1-1.mcd extract BASLUS-20963 -o saves/` |
| Adicionar arquivos ou pastas do PC | `psmm Card1-1.mcd add MeuSave/ -d /` |
| Criar uma pasta | `psmm Card1-1.mcd mkdir /NOVAPASTA` |
| Apagar (`-r`: pastas com conteúdo) | `psmm Card1-1.mcd rm -r BASLUS-20963` |
| Renomear | `psmm Card1-1.mcd rename /ANTIGO NOVO` |
| Copiar tudo de outros cartões para este | `psmm Card1-1.mcd merge SLUS_202.28_0.bin outro.ps2` |
| Mudar o tamanho (MB) | `psmm Card1-1.mcd resize 16` |
| Verificar erros | `psmm Card1-1.mcd check` |
| Criar um cartão novo | `psmm new Novo.mcd --size 8` (`--ecc` para o PCSX2) |

### Cartões de PS1

O formato é reconhecido pelo conteúdo (`.mcd`, `.mcr`, `.gme`, `.vmp`…). Os saves são escolhidos pelo número do bloco (como o `ls` mostra) ou pelo nome.

| O quê | Comando |
|---|---|
| Formato e blocos livres | `psmm card.mcr info` |
| Listar os saves, inclusive os apagados | `psmm card.mcr ls` |
| Importar saves (`.mcs`, `.psv`, `.psx`, crus) ou todos os saves de outros cartões | `psmm card.mcr import save.mcs outro.gme` |
| Exportar saves (todos, se nenhum for indicado) | `psmm card.mcr export 3 -o saves/` |
| Exportar para o PS3 (`.psv` assinado) | `psmm card.mcr export 3 -o saves/ --format psv` |
| Apagar um save (dá para restaurar depois) | `psmm card.mcr rm BASLUS-00067DRAX00` |
| Restaurar um save apagado | `psmm card.mcr restore 1` |
| Verificar erros | `psmm card.mcr check` |
| Criar um cartão novo (a extensão define o formato) | `psmm new Card1-1.mcd --ps1` |

### Converter

A extensão do arquivo novo define o formato.

```bash
psmm convert SLUS_202.28_0.bin sh2.ps2       # PS2: OPL -> PCSX2
psmm convert card.ps2 card.mcd --size 16     # PS2: PCSX2 -> Gen2, 16 MB
psmm convert card.gme SCEVMC0.VMP            # PS1: DexDrive -> PSP/Vita
psmm convert SCEVMC0.VMP card.mcr            # PS1: PSP/Vita -> emuladores
```

PS2: `.mcd`, `.bin` e `.mc2` são gravados sem ECC, `.ps2` com ECC (`--ecc`/`--no-ecc` mudam isso). PS1: `.mcd`, `.mcr`, `.srm`, `.gme`, `.vmp` e `.vgs`.

### Cartão SD do PSxMemCard Gen2 / SD2PSX

```bash
psmm sd /media/SDCARD                        # lista cartões, canais e configurações (só leitura)
psmm split todos.mcd /media/SDCARD           # um cartão por jogo, no formato do cartão SD
```

O `split` cria `MemoryCards/PS2/<jogo>/<jogo>-1.mcd` (ou `MemoryCards/PS1/…` para cartões de PS1). Se o jogo já tiver pasta, o cartão vira um canal novo nela. `--with-others` copia também as pastas que não são de jogos para todos os cartões, e `-s` define o tamanho dos cartões de PS2 novos.
