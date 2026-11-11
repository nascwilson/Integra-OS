# iNTEGRA OS — construção da ISO de teste (versão 0.5)

Estes scripts montam uma imagem ISO do iNTEGRA OS sobre o Ubuntu 26.04 LTS:
KDE Plasma 6 com o tema iNTEGRA, Central iNTEGRA, janelas no estilo Windows,
Wine para programas do Windows com aviso de compatibilidade, pontos de
restauração automáticos e o instalador Calamares.

Desde a versão 0.3, a camada iNTEGRA vem em pacotes `.deb` (pasta `pacotes/`),
que podem ser publicados num repositório próprio para enviar atualizações.
A versão 0.4 é a primeira instalada no disco pelo instalador, do começo ao fim.
A versão 0.5 traz programas de uso diário: Euro-Office, WhatsApp (ZapZap),
Google Drive e o instalador do Logos Bible.

É uma versão de **teste**. Use em máquina virtual ou num computador de testes.

## O que você precisa

- Um computador (ou máquina virtual) com **Ubuntu 24.04 ou 26.04**, 64 bits.
- Uns **40 GB livres** em disco e conexão com a internet (o build baixa cerca de 2 GB).
- Acesso de administrador (`sudo`).

Instale as ferramentas uma vez:

```bash
sudo apt update
sudo apt install debootstrap squashfs-tools xorriso grub-pc-bin grub-efi-amd64-bin \
                 grub-common mtools dosfstools librsvg2-bin zstd dpkg-dev apt-utils \
                 git curl gettext
```

No Ubuntu 24.04, o `debootstrap` ainda não conhece o 26.04. Resolva com:

```bash
sudo ln -sf gutsy /usr/share/debootstrap/scripts/resolute
```

## Como gerar a ISO

```bash
git clone https://github.com/nascwilson/Integra-OS.git
cd Integra-OS
sudo ./build.sh
```

Leva de 30 a 60 minutos, conforme o computador e a internet.
A ISO fica em `/srv/integra-build/saida/iNTEGRA-OS-0.5-teste-amd64.iso` (3,7 GB; a 0.4 tinha 3,1 GB).

Dá para rodar só algumas etapas, na ordem: `base`, `pacotes`, `terceiros`, `marca`, `limpeza`, `imagem`.
Exemplo, depois de mudar só o visual:

```bash
sudo ./build.sh marca limpeza imagem
```

### Wine 11 (experimental)

Por padrão a ISO usa o Wine 10 do Ubuntu, que foi o testado. Para usar o Wine 11 do repositório oficial do WineHQ:

```bash
sudo WINE=winehq ./build.sh
```

Faça isso num build novo (apague `/srv/integra-build/chroot` antes). Esta opção ainda não foi testada.

## Como testar

**VirtualBox:** crie uma máquina "Ubuntu (64-bit)" com 4 GB de RAM, 2 processadores e 30 GB de disco.
Em Tela, marque "Habilitar aceleração 3D" e use 128 MB de vídeo. Aponte o drive óptico para a ISO e ligue.
Sem aceleração 3D o sistema também abre: ele detecta a falta de aceleração e passa a desenhar a tela por software (`/etc/profile.d/integra-graficos.sh`), mais devagar.

**QEMU (Linux):** `./testar-qemu.sh` abre a ISO numa janela, com KVM quando disponível.

**Pendrive (computador real):** grave a ISO com o balenaEtcher ou o Ventoy.
Esta versão de teste não tem assinatura para Secure Boot: desligue o Secure Boot na BIOS para testar.

Na sessão de teste, o usuário é `integra`, sem senha.

## O que tem nesta versão

| Pacote | O que faz |
|---|---|
| `integra-marca` | Tela de inicialização, cores, papel de parede, barra de tarefas, janelas no estilo Windows, ajustes de desempenho, marca do instalador, identificação do sistema, rede cabeada gerenciada, atualizações sem perguntas sobre arquivos de configuração |
| `integra-central` | Central iNTEGRA (visão geral, dispositivos e drivers, programas do Windows, atalhos para os gerenciadores) e o aviso de atualizações |
| `integra-windows` | Abre `.exe` e `.msi` com dois cliques, mostra o aviso de compatibilidade e cria um ambiente separado para cada programa |
| `integra-restauracao` | Cria um ponto de restauração (Timeshift) antes de cada instalação ou atualização de pacotes |
| `integra-euro-office` | Abre o Euro-Office pela XWayland e em português (o próprio Euro-Office vem do pacote oficial do projeto) |
| `integra-google-drive` | Assistente "Google Drive": conecta a conta e mostra o Drive como pasta |
| `integra-logos` | Atalho "Logos Bible", que instala o Logos no primeiro uso (Ou Dedetai) |
| `zapzap` | ZapZap, cliente do WhatsApp Web, empacotado pelo iNTEGRA com o Qt do Ubuntu |
| `integra-desktop` | Metapacote que instala todos os acima |

Fora dos pacotes, o `build.sh` ainda ajusta arquivos de outros pacotes (`marca/sistema/` e a configuração do instalador): textos de login, sessão de teste, ícone do instalador, firewall ligado por padrão e o instalador com btrfs, fuso de Brasília e lista de remoção gerada a partir da própria imagem.

A identificação do sistema (`/usr/lib/os-release`) passou para o pacote `integra-marca` na versão 0.4. O arquivo do Ubuntu é desviado (`dpkg-divert`), e uma atualização do `base-files` não troca mais o nome do sistema.

As imagens PNG são geradas a partir dos SVG em `marca/svg/` pelo script `marca/gerar-imagens.sh`.

## Programas incluídos (versão 0.5)

Nenhum destes quatro tem versão oficial para Linux feita pelo fabricante. Cada um entrou pelo caminho que existe hoje:

| Programa | Como entrou | O que precisa saber |
|---|---|---|
| **Euro-Office** 9.3.6 | Pacote oficial do projeto (GitHub `Euro-Office/DesktopEditors`), instalado na imagem pela etapa `terceiros` do build | Suíte de escritório europeia (textos, planilhas, apresentações, PDF), derivada do ONLYOFFICE, licença AGPL-3.0. Abre em português (arquivo `~/.config/euro-office/DesktopEditors.conf`) e pela XWayland: na sessão Wayland, sem aceleração 3D, a janela ficou vazia no teste. Ocupa 1,5 GB instalado. Ainda não recebe atualizações pelo sistema (ver limites). |
| **ZapZap** 7.5.1 (WhatsApp) | Empacotado pelo iNTEGRA (`terceiros/zapzap/empacotar.sh`) a partir da tag 7.5.1, usando o PyQt6 e o Qt WebEngine do Ubuntu | Janela própria para o WhatsApp Web, com bandeja e notificações. Projeto independente (GPL-3.0); não é programa oficial do WhatsApp. Na primeira vez, leia o código QR com o celular. Vem com um perfil do AppArmor (`/etc/apparmor.d/zapzap`); sem ele, o Ubuntu 26.04 fecha o programa na hora. |
| **Google Drive** | Assistente do iNTEGRA (`integra-google-drive`) com o rclone do Ubuntu | Menu Iniciar › Google Drive, ou Central › Google Drive. "Conectar conta Google" abre o navegador; depois os arquivos aparecem na pasta `~/Google Drive`. Documentos do Google aparecem como .docx/.xlsx/.pptx. Cache local de até 2 GB. |
| **Logos Bible** | Atalho do iNTEGRA (`integra-logos`) com o Ou Dedetai 4.0.0-beta.15 (MIT, comunidade FaithLife-Community) | O Logos não vem na ISO: é pago, fechado e exige conta Faithlife. Na primeira vez, o atalho baixa o Logos e um Wine próprio (alguns GB) e instala na pasta do usuário. Funciona por esforço da comunidade; uma atualização do Logos pode quebrar até a comunidade corrigir. O painel do Ou Dedetai é em inglês. |

Para o Logos, as dependências do sistema (cabextract, 7zip, FUSE e outras) já vêm na ISO. O serviço `winbind` vem desligado para não ocupar memória; o Wine só usa o programa `ntlm_auth` dele.

## Aviso de compatibilidade (.exe e .msi)

Ao abrir um programa do Windows pela primeira vez, a janela "Instalar programa do Windows" mostra uma **estimativa** feita no próprio computador, sem internet: tipo de instalador, 32 ou 64 bits, assinatura digital, programa .NET, sinais de anti-cheat de jogos online e de instalador de driver. A nota vai de "Boa" a "Não compatível". Para ver a análise no terminal:

```bash
integra-windows --analisar arquivo.exe
```

## Aviso de atualizações

O notificador do Discover ficava o tempo todo na memória: cerca de 156 MB, mais 44 MB do `packagekitd` que ele mantinha acordado (medido na fase 4). Na versão 0.4 ele saiu da imagem.

No lugar, um timer do systemd chama `/usr/lib/integra/aviso-de-atualizacoes` 5 minutos depois do login e a cada 6 horas. O script confere a lista de pacotes, mostra um aviso com os botões "Atualizar agora" e "Ver na Central" e termina. Não repete o mesmo aviso no mesmo dia. As listas continuam sendo baixadas pelo próprio sistema, e as atualizações de segurança continuam sendo instaladas sozinhas.

Se o aviso sumir antes do clique, as atualizações continuam listadas na Central e no Discover.

Para desligar numa conta: `systemctl --user disable --now integra-aviso-de-atualizacoes.timer`.

## Pontos de restauração automáticos

Antes de cada instalação ou atualização de pacotes (pelo Discover ou pelo `apt`), o iNTEGRA cria um ponto de restauração com o Timeshift:

- Na primeira vez, configura o Timeshift sozinho, no mesmo disco do sistema.
- O instalador agora formata em **btrfs** por padrão. Assim cada ponto leva segundos e ocupa pouco espaço. Em ext4 o primeiro ponto copia o sistema inteiro e só é feito se houver espaço livre.
- No máximo um ponto por hora; guarda os 3 mais recentes (ajuste em `/etc/integra/restauracao.conf`).
- Nunca impede a atualização: se algo falhar, só registra em `/var/log/integra-restauracao.log`.
- Para desligar: `sudo touch /etc/integra/sem-ponto-de-restauracao`.

Para voltar a um ponto, abra Central iNTEGRA › Pontos de restauração (Timeshift), escolha o ponto e clique em Restaurar. Depois reinicie. A pasta pessoal (`/home`) não é afetada.

No terminal, o mesmo processo:

```bash
sudo timeshift --list
sudo timeshift --restore --snapshot '2026-11-09_18-23-16' --skip-grub --yes
sudo reboot
```

Antes de restaurar, o Timeshift guarda o estado atual como mais um ponto ("Before restoring..."). Dá para desfazer a restauração.

## Repositório de atualizações

O `build.sh` gera os pacotes e um repositório APT em `/srv/integra-build/saida/repositorio`. Para publicar:

1. Crie uma chave para assinar: `gpg --quick-gen-key "Projeto iNTEGRA <seu-email>" rsa4096 sign 5y`
2. Gere o repositório assinado: `INTEGRA_CHAVE=<ID da chave> ./repo/gerar-repositorio.sh`
3. Publique a pasta `saida/repositorio` num servidor web estático (o GitHub Pages serve).
4. Gere a ISO apontando para ele: `sudo INTEGRA_CHAVE=<ID> INTEGRA_REPO_URL=https://seu-endereco ./build.sh`

A partir daí, cada nova versão dos pacotes chega aos computadores pelo Discover, como qualquer atualização.

Código-fonte: https://github.com/nascwilson/Integra-OS. Endereço previsto para os pacotes: o mesmo repositório, com o GitHub Pages servindo a pasta do repositório APT. O Euro-Office fica de fora (330 MB; o GitHub não aceita arquivos acima de 100 MB num repositório).

## Limites conhecidos desta versão

- O Wine padrão é o 10.0 do Ubuntu. O Wine 11 (`WINE=winehq`) ainda não foi testado.
- Sem assinatura para Secure Boot.
- A Central iNTEGRA usa cores escuras fixas; ainda não acompanha um tema claro.
- O tema de janelas usa o motor Aurorae do KDE, um pouco mais pesado que o padrão Breeze.
- O aviso de compatibilidade é uma estimativa local. Ainda não consulta bancos de dados de compatibilidade na internet.
- O repositório de atualizações ainda não tem endereço público.
- Os botões do aviso de atualizações ("Atualizar agora", "Ver na Central") não foram testados com clique: na máquina virtual, sem aceleração 3D, o Plasma não desenhou as janelas flutuantes de aviso. O aviso chegou ao histórico de notificações.
- Instalação com disco criptografado ainda não testada.
- No resumo do instalador aparecem duas frases com "1" no lugar do valor ("Configure timezone para 1"). É erro de tradução do próprio Calamares; a configuração gravada sai certa.
- O instalador escolhe o modelo de teclado "Generic 105-key PC" em vez do ABNT2. As letras e acentos funcionam; falta conferir a tecla de ponto do teclado numérico.
- O menu de boot do sistema instalado mostra "iNTEGRA GNU/Linux" e "Advanced options" em inglês. O texto de ajuda do menu da ISO também continua em inglês.
- A sessão de teste (pendrive) ainda apaga a tela depois de uns 20 minutos parada, mesmo com a economia de energia desligada. Mexer o mouse traz a tela de volta. A causa não foi achada.
- Sem o comando `ping` na imagem.
- Euro-Office: o pacote tem 330 MB e não cabe no repositório do iNTEGRA no GitHub Pages (limite de 100 MB por arquivo). Por enquanto, atualizar exige baixar o `.deb` novo do projeto. O projeto ainda é jovem e há uma disputa de licença com o ONLYOFFICE.
- WhatsApp e Google Drive dependem de serviços que a máquina virtual de teste não alcança (sem acesso a `web.whatsapp.com` e `accounts.google.com`). O login nos dois não foi testado.
- Logos: só o painel do instalador foi testado. A instalação do Logos em si precisa de conta Faithlife e de vários GB de download.
- Euro-Office: a página inicial abriu em português, mas o editor de texto não terminou de carregar em 35 minutos na máquina virtual sem aceleração. Falta testar num computador real ou no VirtualBox antes de confiar nele.
- ZapZap: na primeira vez, abre o site do projeto no navegador e mostra um pedido de doação. É do próprio ZapZap.

## Resultado do teste da versão 0.5 (10/11/2026)

Sessão de teste da ISO 0.5 em QEMU sem aceleração, 4 GB de RAM.

- **Euro-Office:** abriu em português, já fixado na barra de tarefas. A primeira abertura levou uns 8 minutos na máquina virtual, quase todos montando o cache de fontes. Pela sessão Wayland a janela ficou vazia; pela XWayland desenhou normalmente, por isso o atalho agora abre pela XWayland. O editor de documento não terminou de carregar em 35 minutos.
- **ZapZap (WhatsApp):** fechava na hora ("credentials.cc: Permissão negada"). O Ubuntu 26.04 bloqueia "user namespaces" para programas sem perfil do AppArmor, e o Chromium embutido precisa disso. Com o perfil novo, abriu em português, passou pela configuração inicial e chegou à página do WhatsApp Web, que não carrega na rede da máquina de teste.
- **Falkon (navegador padrão desde a 0.1):** fechava na hora na sessão de teste pelo mesmo motivo. No pendrive, o Ubuntu não carrega os perfis do AppArmor, e ninguém tinha aberto o navegador nos testes anteriores. Um serviço novo carrega só os perfis dos programas com Chromium embutido na sessão de teste. Depois disso, o Falkon abriu. No sistema instalado, os perfis já carregavam normalmente.
- **Google Drive:** o assistente abriu e, ao clicar em "Conectar conta Google", iniciou o rclone esperando a autorização. A montagem foi testada com uma conta de mentira do próprio rclone: a pasta `~/Google Drive` montou, aceitou gravação e desmontou ao parar o serviço.
- **Logos:** o painel do Ou Dedetai abriu e perguntou qual versão do Logos instalar. A lista depende da internet, que a máquina de teste não tem para esse endereço.
- **Memória:** área de trabalho parada, 0,87 GB (sessão de teste, máquina com 4 GB). Com Euro-Office e ZapZap abertos, 1,46 GB.

Telas em `docs/telas-v0.5/`.

## Resultado do teste da versão 0.4 (9/11/2026)

Mesmo ambiente dos testes anteriores (QEMU sem aceleração, 3 GB de RAM, `-cpu Nehalem`, disco de 30 GB). Desta vez o sistema foi instalado no disco pelo instalador, do começo ao fim, três vezes.

**Primeira instalação, com a ISO 0.3.** O instalador parou na etapa de pacotes: a lista de remoção do Kubuntu pedia `kubuntu-installer-prompt`, que não existe na imagem. O carregador de inicialização já estava gravado, então o sistema iniciou e deu para testar o resto:

- Disco em btrfs com os subvolumes `@`, `@home`, `@cache` e `@log`. Firewall ativo.
- Ponto de restauração de verdade: ao remover pacotes com o `apt`, o gancho configurou o Timeshift sozinho em modo btrfs e criou o ponto em menos de 1 segundo (o gancho inteiro levou uns 7). Um segundo `apt` dentro da mesma hora não criou outro, como previsto.
- Restauração: o Timeshift voltou o sistema ao ponto e, depois de reiniciar, os pacotes removidos estavam de volta. A pasta pessoal não mudou. O Timeshift guardou o estado anterior como mais um ponto, então a restauração pode ser desfeita.
- Atualização pelo Discover (8 pacotes): o gancho também rodou, e o ponto foi criado antes da instalação.
- Memória com a área de trabalho parada: 0,99 GB pelo `free`, 0,97 GB somando o uso real de cada processo. Só o notificador do Discover ocupava 156 MB, mais 44 MB do `packagekitd`.

Problemas achados nessa rodada: pastas pessoais em inglês; fuso padrão de Nova York; botão "Doar" e etapa "Customize" do Kubuntu no instalador; o btrfs aparecia na prévia, mas a lista de sistemas de arquivos mostrava ext4; a limpeza final removia o `cryptsetup`; a rede cabeada ficava sem gerenciamento na sessão de teste; depois de uma restauração, a Central não sabia a data do último ponto.

**Segunda instalação, com a ISO 0.4.** Todos os problemas acima corrigidos. (A data do último ponto foi corrigida no script, mas a restauração não foi repetida para conferir.) A instalação passou da etapa de pacotes e parou duas etapas depois: o passo final do Kubuntu tenta apagar `cdrom.sources`, que a ISO do iNTEGRA não tem. O passo seguinte também falharia, porque procura `/var/log/syslog`. Os dois foram reescritos para tolerar a falta dos arquivos. No sistema instalado:

- Pastas pessoais em português, inclusive "Área de trabalho".
- Nenhum pacote da sessão de teste sobrou. `cryptsetup` mantido.
- Identificação "iNTEGRA OS 0.4-teste", protegida por desvio do dpkg.
- Rede cabeada conectada. Fontes do apt no formato novo (`ubuntu.sources`).
- Aviso de atualizações ativo para o usuário e nenhum notificador residente.
- Memória com a área de trabalho parada: **0,81 GB pelo `free`, 0,80 GB somando os processos** (0,17 GB a menos que a 0.3).

No teste do aviso de atualizações, o `notify-send` recusou os botões ("Actions are not supported by this notifications server"), embora o Plasma anuncie suporte a eles. O aviso passou a falar direto com o Plasma pelo D-Bus (`gdbus`). A lógica foi testada com sinais simulados (clique em cada botão, aviso fechado, avisos de outros programas no meio). O aviso real apareceu no histórico de notificações com o logo do iNTEGRA.

**Terceira instalação, com a ISO 0.4 final:** o instalador foi do começo ao fim sem erro e terminou na tela "Tudo pronto". Levou 58 minutos na máquina virtual sem aceleração; num computador real deve ser bem menos. No sistema instalado, os registros da instalação ficaram em `/var/log/installer/`, e o aviso de atualizações rodou de verdade: com duas atualizações simuladas, o aviso foi entregue ao Plasma, o script esperou, viu o aviso fechar e terminou sem deixar processo para trás.

Telas em `docs/telas-v0.4/` (as que começam com `v03-` são da primeira rodada).

## Resultado do teste da versão 0.3 (9/11/2026)

Mesmo ambiente (QEMU sem aceleração, 3 GB de RAM, `-cpu Nehalem`):

- Os cinco pacotes `integra-*` instalaram sem erro na imagem, e o `apt` reconheceu o repositório gerado (`apt-cache policy integra-desktop`).
- Ao abrir um `.exe`, a janela nova mostrou a estimativa ("Boa", 64 bits, sem assinatura). Depois de "Instalar", preparou o ambiente e o programa abriu. Teste com o Bloco de Notas do próprio Wine.
- A análise reconheceu os casos de teste: programa 32 e 64 bits, sinal de anti-cheat (nota "Baixa"), instalador de driver ("Baixa"), `.msi` e arquivo que não é programa ("Não compatível").
- O gancho de pontos de restauração foi testado com um Timeshift simulado: configura sozinho, respeita o intervalo de uma hora e guarda os 3 mais recentes. Na sessão de teste ele não faz nada, como esperado.
- Corrigido durante o teste: programas abertos pelo instalador eram encerrados quando a janela fechava, e os comandos `integra-windows`/`integra-central` saíam dos pacotes sem permissão de execução.
- Telas em `docs/telas-v0.3/`.

## Resultado do teste da versão 0.2 (9/11/2026)

Mesmo ambiente do teste anterior (QEMU sem aceleração, 3 GB de RAM, `-cpu Nehalem`):

- A Central iNTEGRA abriu pela barra de tarefas e mostrou o status real: firewall ativo, nenhum driver extra necessário, atualizações ainda não verificadas (a sessão de teste não traz a lista de pacotes) e pontos de restauração não configurados.
- Janelas da Central, do Dolphin e dos demais programas com os botões traço, quadrado e X.
- Memória em uso com a Central aberta: cerca de 0,93 GB.
- A sessão de teste ficou 12 minutos parada sem bloquear nem apagar a tela.
- As pastas pessoais da sessão de teste aparecem com nomes em inglês (Desktop, Documents). No sistema instalado em português isso não deve ocorrer, mas falta confirmar.
- Telas em `docs/telas-v0.2/`.

## Resultado do primeiro teste, versão 0.1 (9/11/2026)

Testado em QEMU sem aceleração (emulação pura), 3 GB de RAM, 2 processadores:

- Tela de inicialização, bloqueio de tela, área de trabalho, menu Iniciar e "Sobre este sistema" funcionaram com a marca iNTEGRA, em português.
- Memória em uso com a área de trabalho parada: entre 0,8 e 0,9 GB (comando `free`, sessão ao vivo, renderização por software).
- Ao abrir um `.exe`, apareceu o aviso "Instalar programa do Windows", o Wine criou o ambiente separado e o programa abriu em português. O teste usou o Bloco de Notas que vem com o próprio Wine; programas comerciais ainda precisam ser testados.
- Com o modelo de processador `-cpu max` do QEMU, o Wine travou por um erro da emulação. Com `-cpu Nehalem` funcionou. Em computador real isso não deve acontecer, mas vale confirmar.
- Problemas achados e já corrigidos: tela preta em máquina virtual sem aceleração 3D, ícone "Instalar Kubuntu" na área de trabalho e acentos no menu de boot.
- Ainda não testado: o instalador Calamares do começo ao fim e o boot em computador real.
- A sessão de teste bloqueava a tela após 5 minutos parada. Corrigido na versão 0.2.
