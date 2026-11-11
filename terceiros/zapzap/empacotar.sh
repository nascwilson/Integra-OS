#!/usr/bin/env bash
# =============================================================================
#  Empacota o ZapZap (cliente do WhatsApp Web para Linux, GPL-3.0) como .deb
#  que usa o PyQt6 e o Qt WebEngine do próprio Ubuntu. Nada de Flatpak/Snap:
#  o programa divide as bibliotecas com o resto do sistema.
#
#  Uso: ./terceiros/zapzap/empacotar.sh <pasta-de-saída>
#  Precisa de: git, msgfmt (pacote gettext), dpkg-deb
# =============================================================================
set -euo pipefail

VERSAO_ZAPZAP="7.5.1"
COMMIT="ec5159f884882d90490513740225bf1f9acb485a"   # tag 7.5.1, conferido na fase 5
REVISAO="1integra1"
SAIDA="${1:?informe a pasta de saída}"

AQUI="$(cd "$(dirname "$0")" && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

git -c advice.detachedHead=false clone -q --depth 1 --branch "$VERSAO_ZAPZAP" https://github.com/rafatosta/zapzap "$TMP/fonte"
[ "$(git -C "$TMP/fonte" rev-parse HEAD)" = "$COMMIT" ] || {
  echo "ERRO: a tag $VERSAO_ZAPZAP não aponta mais para o commit conferido" >&2; exit 1; }

R="$TMP/raiz"
PY="$R/usr/lib/python3/dist-packages"
mkdir -p "$PY" "$R/usr/bin" "$R/usr/share/applications" \
         "$R/usr/share/icons/hicolor/scalable/apps" "$R/usr/share/metainfo" \
         "$R/usr/share/doc/zapzap" "$R/DEBIAN"

cp -a "$TMP/fonte/zapzap" "$PY/"
find "$PY" -name __pycache__ -prune -exec rm -rf {} +

# traduções: o ZapZap procura <pacote>/po/<idioma>/LC_MESSAGES/zapzap.mo
for po in "$TMP/fonte"/po/*.po; do
  idioma="$(basename "$po" .po)"
  mkdir -p "$PY/zapzap/po/$idioma/LC_MESSAGES"
  msgfmt -o "$PY/zapzap/po/$idioma/LC_MESSAGES/zapzap.mo" "$po"
done

cat > "$R/usr/bin/zapzap" <<'EOF'
#!/bin/sh
exec python3 -m zapzap "$@"
EOF

# Atalho com "WhatsApp" no nome, para quem procura no menu. O ZapZap não é
# um programa oficial do WhatsApp; o nome ZapZap continua visível.
sed -e 's/^Name=ZapZap$/Name=ZapZap (WhatsApp)/' \
    -e 's/^Keywords=.*/Keywords=WhatsApp;Zap;Chat;Mensagens;ZapZap;/' \
    "$TMP/fonte/share/applications/com.rtosta.zapzap.desktop" \
    > "$R/usr/share/applications/com.rtosta.zapzap.desktop"
grep -q '^Name\[pt_BR\]=' "$R/usr/share/applications/com.rtosta.zapzap.desktop" || \
  sed -i '/^Name=/a Name[pt_BR]=ZapZap (WhatsApp)' "$R/usr/share/applications/com.rtosta.zapzap.desktop"

cp "$TMP/fonte/share/icons/com.rtosta.zapzap.svg" "$R/usr/share/icons/hicolor/scalable/apps/"
cp "$TMP/fonte/share/metainfo/com.rtosta.zapzap.appdata.xml" "$R/usr/share/metainfo/"
cp "$TMP/fonte/LICENSE" "$R/usr/share/doc/zapzap/copyright"
cat >> "$R/usr/share/doc/zapzap/copyright" <<EOF

-----
Empacotado pelo projeto iNTEGRA OS a partir de
https://github.com/rafatosta/zapzap (tag $VERSAO_ZAPZAP, commit $COMMIT).
O ZapZap é um projeto independente; não é um produto do WhatsApp nem da Meta.
EOF

# Perfil do AppArmor: o Ubuntu 24.04+ bloqueia "user namespaces" para
# programas sem perfil, e o Chromium do Qt WebEngine fecha na hora
# ("credentials.cc: Permissão negada"), visto no teste da fase 5. O perfil
# só libera esse recurso; o resto continua como sem perfil.
mkdir -p "$R/etc/apparmor.d"
cat > "$R/etc/apparmor.d/zapzap" <<'EOF'
# ZapZap (iNTEGRA OS): libera user namespaces para o sandbox do Chromium.
abi <abi/4.0>,
include <tunables/global>

profile zapzap /usr/bin/zapzap flags=(unconfined) {
  userns,

  # Ajustes locais. Veja local/README.
  include if exists <local/zapzap>
}
EOF
echo "/etc/apparmor.d/zapzap" > "$R/DEBIAN/conffiles"

cat > "$R/DEBIAN/control" <<EOF
Package: zapzap
Version: ${VERSAO_ZAPZAP}-${REVISAO}
Architecture: all
Maintainer: Projeto iNTEGRA <integra@localhost>
Section: net
Priority: optional
Depends: python3, python3-pyqt6, python3-pyqt6.qtwebengine, python3-pyqt6.qtwebchannel
Homepage: https://github.com/rafatosta/zapzap
Description: ZapZap: cliente do WhatsApp Web para Linux
 Janela própria para o WhatsApp Web, com ícone na bandeja, notificações e
 várias contas. Projeto independente (GPL-3.0); não é um programa oficial
 do WhatsApp.
EOF
cat > "$R/DEBIAN/postinst" <<'EOF'
#!/bin/sh
set -e
if [ "$1" = "configure" ]; then
    command -v update-desktop-database >/dev/null && update-desktop-database -q /usr/share/applications || true
    command -v gtk-update-icon-cache >/dev/null && gtk-update-icon-cache -qf /usr/share/icons/hicolor || true
    # carrega o perfil já, sem esperar o próximo boot (fora de chroot)
    if command -v apparmor_parser >/dev/null && [ -d /sys/kernel/security/apparmor ] \
       && ! systemd-detect-virt --chroot >/dev/null 2>&1; then
        apparmor_parser -r -T -W /etc/apparmor.d/zapzap || true
    fi
fi
exit 0
EOF
cat > "$R/DEBIAN/postrm" <<'EOF'
#!/bin/sh
set -e
if [ "$1" = "purge" ]; then
    rm -f /etc/apparmor.d/zapzap
fi
exit 0
EOF

find "$R" -type d -exec chmod 0755 {} +
find "$R" -type f -exec chmod 0644 {} +
chmod 0755 "$R/usr/bin/zapzap" "$R/DEBIAN/postinst" "$R/DEBIAN/postrm"

mkdir -p "$SAIDA"
dpkg-deb --root-owner-group -Zxz --build "$R" "$SAIDA/zapzap_${VERSAO_ZAPZAP}-${REVISAO}_all.deb" >/dev/null
echo "  zapzap_${VERSAO_ZAPZAP}-${REVISAO}_all.deb"
