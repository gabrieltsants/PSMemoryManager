# PSMemoryManager

[English](README.md) · [Português (Brasil)](README.pt-BR.md)

Um **gerenciador de memory cards de PlayStation 2 e PlayStation 1 que roda no navegador**. Abra um cartão, veja o que está ocupando espaço, transfira saves entre cartões, faça backup deles ou organize os cartões de um cartão SD do PSxMemCard Gen2 / SD2PSX.

**[Abrir o PSMemoryManager](https://gabrieltsants.github.io/PSMemoryManager/)** — sem instalação.

Prefere um programa no computador? **[Baixe o aplicativo local](https://github.com/gabrieltsants/PSMemoryManager/releases/latest)** (Linux; Windows em breve): o mesmo PSMemoryManager em um arquivo só, sem instalar nada e sem precisar de internet.

> Seus arquivos nunca saem do computador: tudo é processado no navegador. Nada é enviado a um servidor.

> **Antes de editar:** faça backup dos memory cards e de todo o cartão SD. O PSMemoryManager é fornecido como está e seu uso é por sua conta e risco. O projeto e seus colaboradores não se responsabilizam por saves perdidos ou corrompidos, cartões danificados ou qualquer outra perda ou dano decorrente do uso.

![PSMemoryManager exibindo um cartão SD Gen2, seus memory cards e os saves de um cartão aberto](docs/img/hero-light.png)

## O que dá para fazer

- **Ver o que tem no cartão:** cada save com o nome do jogo, ícone, tamanho e região, e quanto espaço sobra. Os saves de PS2 mostram os ícones 3D, animados como no console. Digite na caixa de busca para achar um save pelo nome, título ou código do jogo.
- **Transferir saves:** abra dois cartões lado a lado e arraste os saves de um para o outro.
- **Fazer backup e restaurar saves:** exporte saves para arquivos e importe-os de novo, no mesmo cartão ou em outro.
- **Fazer uma limpeza:** apague saves, pastas e arquivos. Toda alteração pode ser desfeita até você salvar. Nos cartões de PS1, um save apagado pode até ser restaurado depois, como no console.
- **Redimensionar cartões existentes:** aumente ou diminua um cartão de PS2 (de 1 a 64 MB) sem perder nada. Cada save mantém as datas e os atributos, e funciona também nos cartões do cartão SD.
- **Converter cartões** entre aparelhos e emuladores, juntar cartões ou separar um cartão em um cartão por jogo.
- **Gerenciar o cartão SD do PSxMemCard Gen2 / SD2PSX:** veja todos os cartões e canais, abra e salve direto no SD, crie novos, dê nome aos canais e altere as configurações do aparelho. **Todos os saves** lista os saves de todos os cartões num lugar só (e mostra os que estão em mais de um cartão), e **Backup** guarda o cartão SD inteiro em um arquivo .zip.
- **Verificar um cartão** em busca de erros.

![Um cartão de PS2 com os ícones 3D dos saves na lista e o ícone do Silent Hill 2 girando no painel de detalhes](docs/img/ps2-icons.gif)

![Cópia de um save entre dois memory cards](docs/img/two-cards.gif)

Funciona em computadores e celulares, nos temas claro e escuro, em português ou inglês (segue o idioma do navegador; dá para trocar na barra superior).

<p align="center">
  <img src="docs/img/import-opl.png" width="49%" alt="Importação de memory cards virtuais do OPL para um cartão SD Gen2" />
  <img src="docs/img/convert.png" width="49%" alt="Conversão de um memory card para o formato do PCSX2" />
</p>
<p align="center">
  <img src="docs/img/folder-per-game.png" width="49%" alt="Associação de uma pasta de memory card a um jogo no SD Gen2" />
  <img src="docs/img/mobile.png" width="25%" alt="PSMemoryManager aberto em um celular" />
</p>

## Compatível com

**Memory cards de PS2**
- PSxMemCard Gen2 / SD2PSX
- Memory cards virtuais do OPL (VMC)
- PCSX2
- MemCard PRO2

**Memory cards de PS1**
- PSxMemCard Gen2 / SD2PSX e MemCard PRO
- DexDrive
- PSP e PS Vita (PS1 Classics)
- Emuladores: DuckStation, ePSXe, Mednafen, RetroArch e outros

**Arquivos de save**
- PS2: uLaunchELF/wLaunchELF (`.psu`), Action Replay MAX (`.max`), CodeBreaker, SharkPort/X-Port e PS3 (`.psv`)
- PS1: MemcardRex/PSXGameEdit (`.mcs`), PS3 (`.psv`), Action Replay/GameShark/Xploder e saves crus

É só abrir ou arrastar o arquivo: o PSMemoryManager reconhece o formato sozinho. A lista completa de tipos de arquivo está nos [detalhes técnicos](docs/formats.pt-BR.md).

## Como usar

1. [Abra o PSMemoryManager](https://gabrieltsants.github.io/PSMemoryManager/) e espere carregar (na primeira visita são baixados uns 10 MB; nas próximas é instantâneo).
2. Clique em **Abrir** e escolha o arquivo do memory card, ou arraste-o para a página.
3. Selecione saves para ver os detalhes. Use a barra de ferramentas ou o botão direito do mouse para as ações.
4. Clique em **Salvar** quando terminar. Nada muda no seu arquivo até você salvar.

**Usando o cartão SD do PSxMemCard Gen2 / SD2PSX:** coloque o cartão SD no computador, clique em **Cartão SD** e escolha a pasta raiz do cartão (a que tem a pasta `MemoryCards`). Clique num cartão da lista à esquerda para abri-lo; **Salvar** grava direto no cartão SD.

### Aplicativo local (sem internet)

1. [Baixe o aplicativo local](https://github.com/gabrieltsants/PSMemoryManager/releases/latest) do seu computador: `linux-x86_64` para a maioria dos PCs, `linux-arm64` para Raspberry Pi ou outra placa ARM.
2. Extraia e dê dois cliques em **PSMemoryManager** (ou rode `./PSMemoryManager` no terminal). O navegador abre com o aplicativo, igualzinho ao site.
3. Quando terminar, é só fechar a aba do navegador: o aplicativo fecha sozinho logo depois.

Ele roda só no seu computador: nenhum outro aparelho da rede consegue acessá-lo. Uma versão para Windows vem em breve.

### Bom saber

- **Use Chrome ou Edge** para salvar direto no arquivo original ou no cartão SD. Firefox e Safari também funcionam, mas salvam baixando uma cópia e abrem o cartão SD só para leitura.
- **Mantenha cartões de PS2 com 8 MB**, a menos que saiba que precisa de mais: cartões maiores não são reconhecidos por todos os jogos, pelo menu do console nem pelo FreeMcBoot.
- Pastas com um cadeado são **protegidas** (FreeMcBoot, PS2BBL). Apagá-las pode impedir o console de iniciar pelo cartão.
- Cartões do **FreePSXBoot** abrem só para leitura, para continuarem funcionando.
- Arquivos `.vmp` (PSP/Vita) e `.psv` (PS3) são assinados ao salvar ou exportar, para os consoles aceitarem.

Atalhos: `/` buscar · `Ctrl+O` abrir · `Ctrl+S` salvar · `Ctrl+Z` desfazer · `Ctrl+E` extrair · `Ctrl+Shift+N` nova pasta · `F2` renomear · `Del` apagar · `Esc` limpar seleção.

## Mais

- **[Linha de comando](docs/cli.pt-BR.md):** use o PSMemoryManager pelo terminal, passo a passo (Windows e Linux).
- **[Detalhes técnicos](docs/formats.pt-BR.md):** formatos e tamanhos de arquivo, ECC, blocos do PS1, a estrutura do cartão SD do Gen2 e as limitações conhecidas.
- **[Desenvolvimento](docs/development.md)** (em inglês): rodar localmente, testes, organização do projeto e como o site é publicado.

## Créditos e licença

GPLv3. Usa o [mymc++](https://github.com/Adubbz/mymcplusplus), de Florian Märkl e outros, baseado no mymc de Ross Ridge (também GPLv3). O suporte a PS1 segue o [MemcardRex](https://github.com/ShendoXT/memcardrex) e o [vita-mcr2vmp](https://github.com/dots-tb/vita-mcr2vmp) (GPLv3). Os títulos dos jogos vêm do [GameIndex.yaml do PCSX2](https://github.com/PCSX2/pcsx2/blob/master/bin/resources/GameIndex.yaml) (GPLv3). O aplicativo local inclui o [Pyodide](https://pyodide.org) (MPL-2.0). Inspirado no [mcd_viewer](https://github.com/gamebitfunx/mcdviewer), feito para o PSxMemCard Gen2. Os créditos completos estão nos [detalhes técnicos](docs/formats.pt-BR.md#créditos).
