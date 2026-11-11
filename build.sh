#!/usr/bin/env bash
# =============================================================================
#  iNTEGRA OS — construção da ISO de teste
#  Uso:   sudo ./build.sh                 (todas as etapas)
#         sudo ./build.sh base pacotes    (só as etapas indicadas)
#  Etapas: base pacotes marca limpeza imagem
#
#  Opções (variáveis de ambiente):
#    VERSAO=0.6-teste      versão impressa no sistema
#    WINE=ubuntu|winehq    ubuntu = Wine 10 do Ubuntu (padrão, testado)
#                          winehq = Wine 11 do repositório oficial WineHQ (experimental)
#    COMPRESSAO=15         nível zstd da imagem (menor = mais rápido, ISO maior)
#    INTEGRA_REPO_URL=...  endereço do repositório de atualizações do iNTEGRA
#                          (exige INTEGRA_CHAVE com a chave GPG que assina o repositório)
# =============================================================================
set -euo pipefail

AQUI="$(cd "$(dirname "$0")" && pwd)"
TRAB="${TRAB:-/srv/integra-build}"
RAIZ="$TRAB/chroot"
ISO="$TRAB/iso"
SAIDA="${SAIDA:-$TRAB/saida}"
VERSAO="${VERSAO:-0.6-teste}"
WINE="${WINE:-ubuntu}"
SERIE="resolute"                      # Ubuntu 26.04 LTS
ESPELHO="${ESPELHO:-http://archive.ubuntu.com/ubuntu}"
ETAPAS="${*:-base pacotes terceiros marca limpeza imagem}"
EXTRAS="$TRAB/extras"                  # cache dos programas de terceiros baixados

# Euro-Office (suíte de escritório europeia, AGPL-3.0, derivada do ONLYOFFICE).
# O pacote tem 330 MB e não cabe no repositório do iNTEGRA (GitHub Pages
# limita arquivos a 100 MB); vai direto na imagem.
EURO_OFFICE_VERSAO="9.3.6-0"
EURO_OFFICE_URL="https://github.com/Euro-Office/DesktopEditors/releases/download/v9.3.6/euro-office-euro-office_${EURO_OFFICE_VERSAO}_amd64.deb"
EURO_OFFICE_SHA256="f80599f40ac912810460188b9165688b08ac7bee33725ff65bb5ceb97c5acb81"

msg()  { printf '\n\033[1;36m==> %s\033[0m\n' "$*"; }
erro() { printf '\n\033[1;31m[erro] %s\033[0m\n' "$*" >&2; exit 1; }

[ "$(id -u)" -eq 0 ] || erro "rode como root (sudo ./build.sh)"
for f in debootstrap mksquashfs grub-mkrescue xorriso rsvg-convert dpkg-deb apt-ftparchive; do
  command -v "$f" >/dev/null || erro "falta a ferramenta '$f' (veja o README)"
done

# --- montagens do chroot ----------------------------------------------------
montar() {
  for d in dev dev/pts proc sys run; do mkdir -p "$RAIZ/$d"; done
  mountpoint -q "$RAIZ/dev"     || mount --bind /dev "$RAIZ/dev"
  mountpoint -q "$RAIZ/dev/pts" || mount --bind /dev/pts "$RAIZ/dev/pts"
  mountpoint -q "$RAIZ/proc"    || mount -t proc proc "$RAIZ/proc"
  mountpoint -q "$RAIZ/sys"     || mount -t sysfs sysfs "$RAIZ/sys"
  mountpoint -q "$RAIZ/run"     || mount -t tmpfs tmpfs "$RAIZ/run"
  # depois que o systemd-resolved entra na imagem, /etc/resolv.conf aponta
  # para /run; sem esta cópia o apt do chroot não resolve nomes numa reconstrução
  mkdir -p "$RAIZ/run/systemd/resolve"
  cp -L /etc/resolv.conf "$RAIZ/run/systemd/resolve/stub-resolv.conf"
}
desmontar() {
  for d in run sys proc dev/pts dev; do
    mountpoint -q "$RAIZ/$d" 2>/dev/null && umount -lf "$RAIZ/$d" || true
  done
}
trap desmontar EXIT

no_chroot() { chroot "$RAIZ" /usr/bin/env -i \
  HOME=/root PATH=/usr/sbin:/usr/bin:/sbin:/bin LANG=C.UTF-8 \
  DEBIAN_FRONTEND=noninteractive "$@"; }

# --- etapa 1: sistema base ---------------------------------------------------
etapa_base() {
  msg "Sistema base Ubuntu 26.04 ($SERIE)"
  if [ -x "$RAIZ/usr/bin/apt-get" ]; then echo "já existe, pulando"; return; fi
  mkdir -p "$RAIZ"
  debootstrap --arch=amd64 --variant=minbase "$SERIE" "$RAIZ" "$ESPELHO"
}

# --- etapa 2: pacotes --------------------------------------------------------
etapa_pacotes() {
  msg "Repositórios e pacotes"
  sed "s|@ESPELHO@|$ESPELHO|g; s|@SERIE@|$SERIE|g" "$AQUI/config/sources.list" > "$RAIZ/etc/apt/sources.list"
  install -Dm644 "$AQUI/config/sem-snap.pref" "$RAIZ/etc/apt/preferences.d/sem-snap.pref"
  echo integra > "$RAIZ/etc/hostname"
  # impede que serviços subam dentro do chroot
  printf '#!/bin/sh\nexit 101\n' > "$RAIZ/usr/sbin/policy-rc.d"; chmod +x "$RAIZ/usr/sbin/policy-rc.d"

  montar
  # Wine do Ubuntu precisa da arquitetura i386 para programas 32 bits.
  # O Wine 11 do WineHQ usa o novo modo WoW64 e dispensa o i386.
  [ "$WINE" = "ubuntu" ] && no_chroot dpkg --add-architecture i386
  no_chroot apt-get update
  no_chroot apt-get -y full-upgrade

  # idioma, teclado e fuso
  no_chroot apt-get -y install locales tzdata keyboard-configuration console-setup
  sed -i 's/^# *pt_BR.UTF-8/pt_BR.UTF-8/' "$RAIZ/etc/locale.gen"
  no_chroot locale-gen
  printf 'LANG=pt_BR.UTF-8\nLANGUAGE=pt_BR:pt:en\n' > "$RAIZ/etc/default/locale"
  ln -sf /usr/share/zoneinfo/America/Sao_Paulo "$RAIZ/etc/localtime"
  echo America/Sao_Paulo > "$RAIZ/etc/timezone"
  cat > "$RAIZ/etc/default/keyboard" <<'EOF'
XKBMODEL="abnt2"
XKBLAYOUT="br"
XKBVARIANT=""
XKBOPTIONS=""
BACKSPACE="guess"
EOF

  # lista principal (linhas com # são comentários)
  mapfile -t PACOTES < <(grep -vE '^\s*(#|$)' "$AQUI/config/pacotes.txt" | awk '{print $1}')
  if [ "$WINE" = "winehq" ]; then
    msg "Wine 11 do repositório WineHQ (experimental)"
    no_chroot apt-get -y install wget gpg ca-certificates
    mkdir -p "$RAIZ/etc/apt/keyrings"
    no_chroot sh -c 'wget -qO- https://dl.winehq.org/wine-builds/winehq.key | gpg --dearmor --yes -o /etc/apt/keyrings/winehq-archive.key'
    no_chroot wget -qNP /etc/apt/sources.list.d/ "https://dl.winehq.org/wine-builds/ubuntu/dists/$SERIE/winehq-$SERIE.sources"
    no_chroot apt-get update
    mapfile -t PACOTES < <(printf '%s\n' "${PACOTES[@]}" | grep -vxE 'wine|wine64|wine32:i386|fonts-wine')
    PACOTES+=(winehq-stable)
  fi
  no_chroot apt-get -y install "${PACOTES[@]}"
  desmontar
}

# --- etapa 2b: programas de terceiros instalados direto na imagem ------------
baixar_conferido() {   # url sha256 destino
  if [ -f "$3" ] && echo "$2  $3" | sha256sum -c --status; then return 0; fi
  curl -fL --retry 3 -o "$3.parcial" "$1"
  echo "$2  $3.parcial" | sha256sum -c --status || erro "soma SHA-256 não confere: $1"
  mv "$3.parcial" "$3"
}

etapa_terceiros() {
  msg "Programas de terceiros: Euro-Office"
  mkdir -p "$EXTRAS"
  local deb="$EXTRAS/$(basename "$EURO_OFFICE_URL")"
  baixar_conferido "$EURO_OFFICE_URL" "$EURO_OFFICE_SHA256" "$deb"
  montar
  mkdir -p "$RAIZ/etc/integra"; touch "$RAIZ/etc/integra/sem-ponto-de-restauracao"
  cp "$deb" "$RAIZ/tmp/euro-office.deb"
  # sem as recomendações: ttf-mscorefonts-installer baixa fontes da internet
  # e pede aceite de licença no meio da instalação
  no_chroot apt-get -y --no-install-recommends install /tmp/euro-office.deb
  rm -f "$RAIZ/tmp/euro-office.deb"
  rm -f "$RAIZ/etc/integra/sem-ponto-de-restauracao"
  desmontar
}

# --- etapa 3: marca iNTEGRA --------------------------------------------------
etapa_marca() {
  msg "Pacotes da camada iNTEGRA"
  "$AQUI/repo/gerar-pacotes.sh" "$VERSAO" "$SAIDA/pacotes"
  rm -f "$SAIDA"/pacotes/zapzap_*.deb
  "$AQUI/terceiros/zapzap/empacotar.sh" "$SAIDA/pacotes"
  "$AQUI/terceiros/logos/empacotar.sh" "$SAIDA/pacotes" "$EXTRAS"
  "$AQUI/repo/gerar-repositorio.sh" "$SAIDA/pacotes" "$SAIDA/repositorio"
  # restos da versão 0.1/0.2, quando os arquivos eram copiados sem pacote
  rm -f "$RAIZ/usr/local/bin/integra-windows" "$RAIZ/usr/local/bin/integra-central"

  montar
  # nada de ponto de restauração enquanto o sistema está sendo montado
  mkdir -p "$RAIZ/etc/integra"; touch "$RAIZ/etc/integra/sem-ponto-de-restauracao"
  mkdir -p "$RAIZ/tmp/integra-debs"; cp "$SAIDA"/pacotes/*.deb "$RAIZ/tmp/integra-debs/"
  no_chroot sh -c 'apt-get -y -o Dpkg::Options::=--force-confnew install --reinstall /tmp/integra-debs/*.deb'
  rm -rf "$RAIZ/tmp/integra-debs"

  # repositório do iNTEGRA para receber atualizações (quando houver endereço)
  if [ -n "${INTEGRA_REPO_URL:-}" ]; then
    [ -f "$SAIDA/repositorio/integra-archive.gpg" ] || erro "INTEGRA_REPO_URL exige repositório assinado (INTEGRA_CHAVE)"
    install -Dm644 "$SAIDA/repositorio/integra-archive.gpg" "$RAIZ/etc/apt/keyrings/integra-archive.gpg"
    cat > "$RAIZ/etc/apt/sources.list.d/integra.sources" <<FONTE
Types: deb
URIs: $INTEGRA_REPO_URL
Suites: $SERIE
Components: main
Signed-By: /etc/apt/keyrings/integra-archive.gpg
FONTE
  fi

  # arquivos de outros pacotes que o iNTEGRA substitui (casper, base-files, instalador)
  cp -a "$AQUI/marca/sistema/." "$RAIZ/"
  # /usr/lib/os-release vem no pacote integra-marca (desviado do base-files)
  cat > "$RAIZ/etc/lsb-release" <<LSB
DISTRIB_ID=iNTEGRA
DISTRIB_RELEASE=${VERSAO%%-*}
DISTRIB_CODENAME=$SERIE
DISTRIB_DESCRIPTION="iNTEGRA OS $VERSAO"
LSB
  no_chroot update-mime-database /usr/share/mime || true

  # instalador Calamares: marca iNTEGRA e btrfs por padrão (pontos de restauração instantâneos)
  C="$RAIZ/etc/calamares"
  if [ -f "$C/settings.conf" ]; then
    sed -i 's/^branding:.*/branding: integra/' "$C/settings.conf"
    sed -i 's/^defaultFileSystemType:.*/defaultFileSystemType: "btrfs"/; s/kubuntu_boot/integra_boot/; s/kubuntu_[0-9]*/integra_sistema/' \
      "$C/modules/partition.conf"
    sed -i 's/options: \[ defaults, noatime, autodefrag \]/options: [ defaults, noatime, compress=zstd:1 ]/' "$C/modules/mount.conf"
    # btrfs aparece primeiro na lista (o instalador mostra o primeiro item)
    sed -i 's/^availableFileSystemTypes:.*/availableFileSystemTypes: ["btrfs","ext4","xfs"]/' "$C/modules/partition.conf"
    # fuso horário padrão: Brasília (com internet, a localização automática ainda vale)
    sed -i 's/^zone: .*/zone: "Sao_Paulo"/' "$C/modules/locale.conf"
    # sem botões de doação e links do Kubuntu na tela de boas-vindas
    sed -i 's/^showDonateUrl:.*/showDonateUrl: false/; s/^showSupportUrl:.*/showSupportUrl: false/; s/^showKnownIssuesUrl:.*/showKnownIssuesUrl: false/; s/^showReleaseNotesUrl:.*/showReleaseNotesUrl: false/' "$C/modules/welcome.conf"
    # espelho do Ubuntu escolhido pelo país (com internet); o nome só aparece no comentário do arquivo
    [ -f "$C/modules/automirror.conf" ] && sed -i 's/^distribution:.*/distribution: iNTEGRA OS/' "$C/modules/automirror.conf"
    # sem a etapa "Customize" do Kubuntu (o modo mínimo removeria programas de que a Central depende)
    sed -i '/^  - pkgselect$/d; /^  - contextualprocess@pkgselect_action$/d; /^  - contextualprocess@pkgselect_snap_action$/d' "$C/settings.conf"
    # Remoção dos pacotes da sessão de teste. A lista sai do que está de fato
    # instalado na imagem: um nome ausente (kubuntu-installer-prompt) derrubou
    # a instalação inteira no teste da fase 4. Sem LibreOffice na imagem, os
    # pacotes de idioma dele também saem da lista (puxariam 200 MB da internet).
    remover=$(no_chroot dpkg-query -W -f='${db:Status-Abbrev} ${Package}\n' \
      | awk '$1=="ii" && $2 ~ /^(calamares|libcalamares|casper$|cifs-utils$|live-)/ {print "      - " $2}')
    {
      echo "---"
      echo "backend: apt"
      echo "update_db: true"
      echo "ignore_update_db_error: true"
      echo "operations:"
      echo "  - remove:"
      echo "$remover"
      echo "  - try_install:"
      echo "      - language-pack-\$LOCALE"
      echo "      - language-pack-gnome-\$LOCALE"
      echo "      - language-pack-kde-\$LOCALE"
      echo "      - hunspell-\$LOCALE"
    } > "$C/modules/packages.conf"
    # Passos finais do instalador do Kubuntu supõem arquivos que a ISO do
    # iNTEGRA não tem (cdrom.sources, /var/log/syslog) e falhavam no fim da
    # instalação (teste da fase 4). Versões que toleram a ausência:
    cat > "$C/modules/shellprocess_rmcdrom.conf" <<'RMCDROM'
---
dontChroot: true
timeout: 30
script:
    - "rm -f ${ROOT}/etc/apt/sources.list.d/cdrom.sources"
    - "if mountpoint -q ${ROOT}/cdrom; then umount ${ROOT}/cdrom; fi; rmdir ${ROOT}/cdrom 2>/dev/null; true"
RMCDROM
    cat > "$C/modules/shellprocess_logs.conf" <<'LOGS'
---
dontChroot: true
timeout: 30
script:
    - "mkdir -p ${ROOT}/var/log/installer"
    - "cp /root/.cache/calamares/session.log ${ROOT}/var/log/installer/debug 2>/dev/null; cp /var/log/casper.log ${ROOT}/var/log/installer/casper.log 2>/dev/null; chmod 600 ${ROOT}/var/log/installer/debug ${ROOT}/var/log/installer/casper.log 2>/dev/null; true"
    - "cp /cdrom/.disk/info ${ROOT}/var/log/installer/media-info 2>/dev/null; gzip --stdout ${ROOT}/var/lib/dpkg/status > ${ROOT}/var/log/installer/initial-status.gz; chmod 644 ${ROOT}/var/log/installer/media-info ${ROOT}/var/log/installer/initial-status.gz 2>/dev/null; true"
LOGS
    if ! grep -q '^btrfsSubvolumes' "$C/modules/mount.conf"; then
      cat >> "$C/modules/mount.conf" <<'SUBVOL'

# iNTEGRA: subvolumes no formato que o Timeshift usa (@ e @home)
btrfsSubvolumes:
    - mountPoint: /
      subvolume: /@
    - mountPoint: /home
      subvolume: /@home
    - mountPoint: /var/cache
      subvolume: /@cache
    - mountPoint: /var/log
      subvolume: /@log
SUBVOL
    fi
  fi

  # firewall ligado por padrão (bloqueia conexões de entrada, libera as de saída)
  if [ -f "$RAIZ/etc/ufw/ufw.conf" ]; then
    sed -i 's/^ENABLED=no/ENABLED=yes/' "$RAIZ/etc/ufw/ufw.conf"
    no_chroot systemctl enable ufw.service || true
  fi
  no_chroot update-initramfs -u -k all
  rm -f "$RAIZ/etc/integra/sem-ponto-de-restauracao"
  desmontar
}

# --- etapa 4: limpeza --------------------------------------------------------
etapa_limpeza() {
  msg "Limpeza"
  montar
  touch "$RAIZ/etc/integra/sem-ponto-de-restauracao"
  no_chroot apt-get -y autoremove --purge
  # pacotes removidos deixam configurações para trás (ex.: o autostart do
  # notificador do Discover); "purge" apaga esses restos
  mapfile -t RESTOS < <(no_chroot dpkg-query -W -f='${db:Status-Abbrev} ${Package}\n' | awk '$1=="rc" {print $2}')
  [ "${#RESTOS[@]}" -eq 0 ] || no_chroot dpkg --purge "${RESTOS[@]}"
  no_chroot apt-get clean
  rm -f "$RAIZ/etc/integra/sem-ponto-de-restauracao"
  desmontar
  rm -f "$RAIZ/usr/sbin/policy-rc.d"
  rm -rf "$RAIZ/tmp/"* "$RAIZ/var/lib/apt/lists/"* "$RAIZ/var/cache/apt/"*.bin
  : > "$RAIZ/etc/machine-id"
  rm -f "$RAIZ/var/lib/dbus/machine-id"
  find "$RAIZ/var/log" -type f -exec truncate -s 0 {} +
}

# --- etapa 5: imagem ISO -----------------------------------------------------
etapa_imagem() {
  msg "Gerando a ISO"
  rm -rf "$ISO"; mkdir -p "$ISO/casper" "$ISO/boot/grub" "$ISO/.disk" "$SAIDA"
  cp -L "$RAIZ/boot/vmlinuz"    "$ISO/casper/vmlinuz"
  cp -L "$RAIZ/boot/initrd.img" "$ISO/casper/initrd"
  chroot "$RAIZ" dpkg-query -W --showformat='${Package} ${Version}\n' > "$ISO/casper/filesystem.manifest"
  du -sx --block-size=1 "$RAIZ" | cut -f1 > "$ISO/casper/filesystem.size"
  mksquashfs "$RAIZ" "$ISO/casper/filesystem.squashfs" -noappend -comp zstd -Xcompression-level "${COMPRESSAO:-15}" \
    -wildcards -e 'proc/*' 'sys/*' 'dev/*' 'run/*' 'tmp/*' 'boot/*'
  echo "iNTEGRA OS $VERSAO \"$SERIE\" - amd64 ($(date +%Y%m%d))" > "$ISO/.disk/info"
  cp "$AQUI/config/grub.cfg" "$ISO/boot/grub/grub.cfg"
  grub-mkrescue -o "$SAIDA/iNTEGRA-OS-$VERSAO-amd64.iso" "$ISO" -- -volid "INTEGRA_OS"
  ( cd "$SAIDA" && sha256sum "iNTEGRA-OS-$VERSAO-amd64.iso" > "iNTEGRA-OS-$VERSAO-amd64.iso.sha256" )
  msg "Pronto: $SAIDA/iNTEGRA-OS-$VERSAO-amd64.iso"
  ls -lh "$SAIDA"
}

for e in $ETAPAS; do
  declare -F "etapa_$e" >/dev/null || erro "etapa desconhecida: $e"
  "etapa_$e"
done
