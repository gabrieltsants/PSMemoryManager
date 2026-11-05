# Detalhes técnicos

[English](formats.md) · [Português (Brasil)](formats.pt-BR.md) · [Voltar ao README](../README.pt-BR.md)

## Memory cards de PS2

| Origem | Extensão | ECC | Tamanho (cartão de 8 MB) |
|---|---|---|---|
| PSxMemCard Gen2 / SD2PSX | `.mcd` | não | 8.388.608 bytes |
| OPL (VMC) | `.bin` / `.vmc` | não | 8.388.608 bytes |
| MemCard PRO2 | `.mc2` | não | 8.388.608 bytes |
| PCSX2, dumps de cartões reais | `.ps2` | sim | 8.650.752 bytes |

- O **ECC** (correção de erros) acrescenta 16 bytes a cada página de 512 bytes. Se a imagem tem ECC é detectado pelo cabeçalho e pelo tamanho, não pela extensão. Um arquivo cujo tamanho não bate com o cabeçalho abre mesmo assim, marcado como "tamanho inesperado".
- Abre cartões de 1 a 128 MB. Cartões novos e redimensionamento vão de 1 a 64 MB.
- Conversões no mesmo tamanho são idênticas bit a bit (só o ECC é acrescentado ou retirado). Ao redimensionar, um cartão novo é formatado e tudo é copiado, mantendo datas e atributos.
- Toda alteração é feita numa cópia, que é verificada (checagem do sistema de arquivos) antes de substituir o original. Se o cartão não tinha erros, uma alteração que criaria um erro é recusada.
- Nomes de arquivos e pastas no cartão são ASCII, com até 32 caracteres.

### Arquivos de save de PS2

| Formato | Importa | Exporta |
|---|---|---|
| uLaunchELF / wLaunchELF / EMS (`.psu`) | sim | sim (recomendado: mantém datas e atributos) |
| Action Replay MAX (`.max`) | sim | sim (sem datas; a compressão é lenta em saves grandes) |
| CodeBreaker (`.cbs`) | sim | não |
| SharkPort / X-Port (`.sps`, `.xps`) | sim | não |
| PS3 (`.psv`) | sim | não (o mymc++ não grava esse formato) |

Pastas de save têm nomes como `BASLUS-20963…`: `B` + letra da região (`A` América, `E` Europa, `I` Japão, `K` Coreia, `C` China) + código do jogo. Saves copiados para a raiz de outro cartão mantêm datas e atributos, inclusive a marca de "protegido" do FreeMcBoot.

### Ícones dos saves de PS2

O `icon.sys` de cada save aponta o arquivo do ícone (`.ico`/`.icn`): um modelo 3D pequeno com uma textura de 128×128 (crua ou comprimida em RLE) e, em alguns jogos, uma animação que mistura várias formas. O `icon.sys` também define as cores do fundo e as três luzes. A página lê os ícones depois de mostrar o cartão e desenha com WebGL: uma miniatura parada na lista e o modelo animado no painel de detalhes (arraste para girar). Saves sem `icon.sys`, ou com o arquivo do ícone faltando ou quebrado, ficam com o símbolo genérico de save. Navegadores sem WebGL acelerado por hardware também ficam com o símbolo genérico, porque desenhar os modelos por software travaria a página.

## Memory cards de PS1

Um cartão de PS1 tem 128 KB: 16 blocos de 8 KB. O bloco 0 é o diretório; os blocos 1–15 guardam saves, e um save ocupa um ou mais blocos (nem sempre vizinhos). O primeiro bloco de cada save tem o título (em Shift-JIS, então títulos em japonês aparecem certos) e um ícone de 16×16 com 1 a 3 quadros de animação.

| Origem | Extensão | Tamanho |
|---|---|---|
| PSxMemCard Gen2 / SD2PSX, MemCard PRO, DuckStation | `.mcd` (cru) | 131.072 bytes |
| ePSXe, Mednafen e outros emuladores | `.mcr` (cru) | 131.072 bytes |
| RetroArch (Beetle PSX, PCSX ReARMed) | `.srm` (cru) | 131.072 bytes |
| Outras imagens cruas | `.mc`, `.ps`, `.psm`, `.ddf`, `.mci`, `.vm1`, `.bin` | 131.072 bytes |
| DexDrive | `.gme` | 134.976 bytes (cabeçalho de 3.904 bytes; muitas vezes cortado após o último bloco usado) |
| PSP / PS Vita (PS1 Classics) | `.vmp` | 131.200 bytes (cabeçalho assinado de 128 bytes) |
| Connectix Virtual Game Station | `.vgs` / `.mem` | 131.136 bytes (cabeçalho de 64 bytes) |

- O formato é detectado pelo conteúdo. Um arquivo do DexDrive com o cabeçalho danificado também é reconhecido.
- Converter entre esses formatos mantém os 128 KB do cartão idênticos, byte a byte; só muda o invólucro. Os comentários do DexDrive são mantidos enquanto o cartão continua `.gme`.
- **Apagar** funciona como no console: os blocos do save só são marcados como apagados. Até outro save reutilizá-los, o save pode ser restaurado. Saves novos usam primeiro os blocos livres e depois os apagados.
- **Assinaturas:** arquivos `.vmp` (PSP/Vita) e `.psv` (PS3) têm uma assinatura (HMAC-SHA1 com uma chave derivada por AES-128 de uma semente no cabeçalho). Os consoles recusam arquivos com a assinatura errada. O PSMemoryManager assina todo `.vmp` e `.psv` que grava, e a assinatura foi conferida com arquivos gerados por um PSP e um PS3 reais.
- **Cartões fora do padrão** abrem só para leitura: cartões do FreePSXBoot (o diretório é quebrado de propósito para o exploit funcionar) e cartões com blocos que pertencem a dois saves ou com estados desconhecidos. Converter ainda mantém cada byte. Problemas menores (checksums errados, blocos em uso sem save, tamanho que não confere) aparecem em **Verificar**, mas não impedem a edição.
- Cartões de PS1 novos são idênticos, byte a byte, aos cartões vazios que o PSxMemCard Gen2 cria.

### Arquivos de save de PS1

| Formato | Importa | Exporta |
|---|---|---|
| MemcardRex / PSXGameEdit (`.mcs`, `.ps1`) | sim | sim (recomendado) |
| PS3 (`.psv`) | sim | sim (assinado) |
| Action Replay / GameShark / Xploder / Smart Link (`.psx`, `.mcx`, `.pda`, `.mcb`) | sim | não |
| Save cru (só os blocos, qualquer extensão) | sim | não |

Nomes de save são como `BASLUS-00067DRAX00`: `BA`/`BE`/`BI` (América/Europa/Japão) + código do jogo + um identificador escolhido pelo jogo. Um save cru não tem nome dentro, então ele vem do nome do arquivo. Arquivos `.psv` exportados recebem o nome que o PS3 espera (`BASLUS-00067` + o resto do nome em hexadecimal).

## Cartão SD do PSxMemCard Gen2 / SD2PSX

```
.sd2psx/settings.ini                     configurações do aparelho
.sd2psx/Game2Folder.ini                  opcional: código do jogo -> pasta
MemoryCards/PS2/BOOT/BootCard-1.mcd      cartão de boot (arquivos com o prefixo "BootCard")
MemoryCards/PS2/BOOT/BootCard.ini        nomes dos canais
MemoryCards/PS2/Card1/Card1-1.mcd        cartão 1, canal 1
MemoryCards/PS2/SLUS-20963/SLUS-20963-1.mcd   cartão de um código de jogo
MemoryCards/PS1/...                      cartões de PS1 (mesmo esquema)
MemoryCards/COH/... , MemoryCards/SC2/...     arcade / SoulCalibur II Conquest
```

- Cada pasta tem até 8 canais. Os nomes dos canais ficam em `<pasta>.ini` (`BootCard.ini` no BOOT), na seção `[ChannelName]`.
- Com a troca por jogo (**GameID**) ligada, o aparelho abre a pasta com o código do jogo quando ele começa. O `Game2Folder.ini` pode mandar um jogo para outra pasta.
- Quando o PSMemoryManager edita um arquivo INI, mantém a ordem, os comentários e as chaves desconhecidas.
- Dá para criar cartões de PS2, PS1 e arcade (COH). Cartões de Conquest do SoulCalibur II usam formato próprio e só aparecem na lista.
- Gravar no cartão SD exige a File System Access API (Chrome, Edge). Outros navegadores abrem só para leitura.

## Títulos dos jogos

Pastas e saves de jogos de PS2 mostram o título do jogo, do GameIndex do PCSX2 (cerca de 12.700 jogos, carregado só quando necessário). Ele só cobre jogos de PS2: saves de PS1 mostram o título que o próprio jogo gravou no save.

## Limitações conhecidas

- Saves `.psv` de PS2 podem ser importados, mas não exportados.
- A exportação `.max` não mantém as datas dos arquivos, e a compressão roda em Python: um save comum leva alguns segundos, uma pasta de vários MB pode levar minutos. Prefira `.psu`.
- Saves de PS1 não podem ser renomeados: o nome contém o código que o jogo procura.
- Memory cards em pasta do PCSX2 não são suportados.

## Créditos

- [mymc++](https://github.com/Adubbz/mymcplusplus) (GPLv3), de Florian Märkl e outros, baseado no mymc de Ross Ridge: sistema de arquivos e formatos de save do PS2.
- Os formatos de PS1 seguem as especificações de PSX do nocash e o [MemcardRex](https://github.com/ShendoXT/memcardrex) (GPLv3). A assinatura de `.vmp`/`.psv` segue o [vita-mcr2vmp](https://github.com/dots-tb/vita-mcr2vmp) (GPLv3).
- Os títulos dos jogos vêm do [GameIndex.yaml do PCSX2](https://github.com/PCSX2/pcsx2/blob/master/bin/resources/GameIndex.yaml) (GPLv3; os créditos dos dados são de sonyindex, serialstation, psxdatacenter e redump). Só o código e o título são mantidos, em `psmm/data/gamedb.json`.
- Os arquivos de teste de PS1 vêm do [save-file-converter](https://github.com/euan-forrester/save-file-converter) e do [psx_mc_cli](https://github.com/G4Vi/psx_mc_cli) (veja `tests/data/ps1/README.md`).
- Inspirado no [mcd_viewer](https://github.com/gamebitfunx/mcdviewer), feito para o PSxMemCard Gen2.
