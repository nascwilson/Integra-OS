#!/usr/bin/env bash
# =============================================================================
#  Pacote integra-logos: atalho "Logos Bible" que instala e abre o Logos Bible
#  Software (Faithlife) pelo Ou Dedetai, instalador livre (MIT) mantido pela
#  comunidade FaithLife-Community.
#
#  O Logos em si NÃO vai na ISO: é um programa pago e fechado, e cada pessoa
#  entra com a própria conta Faithlife. Na primeira vez, o Ou Dedetai baixa o
#  Logos e um Wine próprio (precisa de internet) e instala tudo na pasta do
#  usuário.
#
#  Uso: ./terceiros/logos/empacotar.sh <pasta-de-saída> [pasta-de-cache]
# =============================================================================
set -euo pipefail

VERSAO_OD="4.0.0-beta.15"
SHA256_OD="56662ded54e6564cca2c24fa3bdce2e60e7fce542bd419718107153382f0db88"
COMMIT_OD="232dceca20fdb5511f3b39624c71e55356326fdf"   # tag v4.0.0-beta.15
REVISAO="1integra1"
SAIDA="${1:?informe a pasta de saída}"
CACHE="${2:-${TMPDIR:-/tmp}/integra-cache}"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$CACHE"

BIN="$CACHE/oudedetai-$VERSAO_OD"
if [ ! -f "$BIN" ] || ! echo "$SHA256_OD  $BIN" | sha256sum -c --status; then
  curl -fsSL -o "$BIN" \
    "https://github.com/FaithLife-Community/LogosLinuxInstaller/releases/download/v$VERSAO_OD/oudedetai"
fi
echo "$SHA256_OD  $BIN" | sha256sum -c --status || { echo "ERRO: soma do oudedetai não confere" >&2; exit 1; }

git -c advice.detachedHead=false clone -q --depth 1 --branch "v$VERSAO_OD" \
  https://github.com/FaithLife-Community/LogosLinuxInstaller "$TMP/fonte"
[ "$(git -C "$TMP/fonte" rev-parse HEAD)" = "$COMMIT_OD" ] || {
  echo "ERRO: a tag v$VERSAO_OD não aponta mais para o commit conferido" >&2; exit 1; }

R="$TMP/raiz"
mkdir -p "$R/DEBIAN" "$R/usr/bin" "$R/usr/lib/integra/logos" "$R/usr/share/applications" \
         "$R/usr/share/icons/hicolor/128x128/apps" "$R/usr/share/doc/integra-logos"

install -m 0755 "$BIN" "$R/usr/lib/integra/logos/oudedetai"
install -m 0644 "$TMP/fonte/ou_dedetai/img/Logos-128-icon.png" \
  "$R/usr/share/icons/hicolor/128x128/apps/integra-logos.png"

cat > "$R/usr/bin/integra-logos" <<'EOF'
#!/bin/sh
# Abre o painel do Ou Dedetai (instalar, abrir, atualizar e remover o Logos).
# -K: as dependências do sistema já vêm na ISO; o Ou Dedetai não reconhece o
# iNTEGRA como Ubuntu e pediria pacotes com nomes antigos.
export DIALOG=tk
exec /usr/lib/integra/logos/oudedetai -K "$@"
EOF
chmod 0755 "$R/usr/bin/integra-logos"

cat > "$R/usr/share/applications/integra-logos.desktop" <<'EOF'
[Desktop Entry]
Type=Application
Name=Logos Bible
GenericName=Estudo bíblico
Comment=Instala e abre o Logos Bible Software (precisa de conta Faithlife e de internet na primeira vez)
Exec=integra-logos
Icon=integra-logos
Categories=Education;Office;
Keywords=Logos;Bíblia;Faithlife;Verbum;estudo;
Terminal=false
EOF

{
  cat "$TMP/fonte/LICENSE"
  cat <<EOF

-----
Ou Dedetai $VERSAO_OD (https://github.com/FaithLife-Community/LogosLinuxInstaller,
commit $COMMIT_OD), distribuído sem alterações pelo projeto iNTEGRA OS.
O Logos Bible Software é produto da Faithlife e não acompanha este pacote.
EOF
} > "$R/usr/share/doc/integra-logos/copyright"

cat > "$R/usr/share/doc/integra-logos/LEIA-ME" <<'EOF'
Logos Bible no iNTEGRA OS
=========================

1. Abra "Logos Bible" no menu Iniciar.
2. Clique em Install (Instalar), aceite os termos da Faithlife e aguarde.
   O download é grande: o Logos e um Wine próprio, alguns gigabytes.
3. Entre com a sua conta Faithlife/Logos.

Interface em português: dentro do Logos, abra as configurações do programa
(Program Settings) e procure a opção de idioma (Language). Se Português
(Brasil) estiver na lista, escolha e reinicie o Logos. Isto não foi testado
pelo projeto iNTEGRA.

Problemas: o painel do Ou Dedetai tem a opção "Get Support", que junta os
registros para enviar à comunidade FaithLife-Community.
EOF

cat > "$R/DEBIAN/control" <<EOF
Package: integra-logos
Version: ${VERSAO_OD//-/\~}-${REVISAO}
Architecture: amd64
Maintainer: Projeto iNTEGRA <integra@localhost>
Section: misc
Priority: optional
Depends: binutils, wget, winbind, 7zip, cabextract, xdg-utils, mesa-utils, libfuse2t64, libfuse3-4, fuse3
Homepage: https://github.com/FaithLife-Community/LogosLinuxInstaller
Description: Logos Bible pelo Ou Dedetai (instalação no primeiro uso)
 Atalho "Logos Bible" que abre o Ou Dedetai, instalador livre da comunidade
 FaithLife-Community. O Logos Bible Software é baixado da Faithlife na
 primeira vez e exige conta própria.
EOF
cat > "$R/DEBIAN/postinst" <<'EOF'
#!/bin/sh
set -e
if [ "$1" = "configure" ]; then
    command -v update-desktop-database >/dev/null && update-desktop-database -q /usr/share/applications || true
    command -v gtk-update-icon-cache >/dev/null && gtk-update-icon-cache -qf /usr/share/icons/hicolor || true
    # O winbind entra só pelo programa ntlm_auth, que o Wine usa. O serviço
    # residente fica desligado para não gastar memória de quem não usa.
    # Só na primeira instalação: quem religar o serviço não é contrariado
    # numa atualização deste pacote.
    if [ -z "$2" ] && [ -e /usr/lib/systemd/system/winbind.service ]; then
        systemctl disable winbind.service >/dev/null 2>&1 || true
        systemctl stop winbind.service >/dev/null 2>&1 || true
    fi
fi
exit 0
EOF
chmod 0755 "$R/DEBIAN/postinst"

mkdir -p "$SAIDA"
NOME="integra-logos_${VERSAO_OD//-/\~}-${REVISAO}_amd64.deb"
dpkg-deb --root-owner-group -Zxz --build "$R" "$SAIDA/$NOME" >/dev/null
echo "  $NOME"
