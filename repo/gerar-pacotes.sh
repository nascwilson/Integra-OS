#!/usr/bin/env bash
# =============================================================================
#  Gera os pacotes .deb da camada iNTEGRA a partir de pacotes/<nome>/.
#  Uso: ./repo/gerar-pacotes.sh [versão] [pasta de saída]
#  Ex.: ./repo/gerar-pacotes.sh 0.6.1-teste /srv/integra-build/saida/pacotes
# =============================================================================
set -euo pipefail
AQUI="$(cd "$(dirname "$0")/.." && pwd)"
VERSAO="${1:-0.6.1-teste}"
SAIDA="${2:-$AQUI/saida/pacotes}"
VERSAO_DEB="${VERSAO//-/\~}"          # 0.6.1-teste -> 0.5~teste (vem antes da 0.5 final)
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

command -v dpkg-deb >/dev/null || { echo "falta dpkg-deb"; exit 1; }
"$AQUI/marca/gerar-imagens.sh" "$AQUI/pacotes/integra-marca" >/dev/null
mkdir -p "$SAIDA"
rm -f "$SAIDA"/integra-*.deb

for dir in "$AQUI"/pacotes/*/; do
  nome="$(basename "$dir")"
  raiz="$TMP/$nome"
  cp -a "$dir" "$raiz"
  find "$raiz" -name __pycache__ -prune -exec rm -rf {} +
  # versão nos arquivos de controle e na marca do instalador
  sed -i "s/@VERSAO@/$VERSAO_DEB/g" "$raiz/DEBIAN/control"
  for f in etc/calamares/branding/integra/branding.desc usr/lib/os-release; do
    if [ -f "$raiz/$f" ]; then sed -i "s/@VERSAO@/$VERSAO/g; s/@VERSAO_ID@/${VERSAO%%-*}/g" "$raiz/$f"; fi
  done
  # todo arquivo em /etc é de configuração (o dpkg preserva mudanças do usuário)
  if [ -d "$raiz/etc" ]; then
    (cd "$raiz" && find etc -type f | sort | sed 's|^|/|') > "$raiz/DEBIAN/conffiles"
  fi
  # permissões
  find "$raiz" -type d -exec chmod 0755 {} +
  find "$raiz" -type f -not -path '*/DEBIAN/*' -exec chmod 0644 {} +
  ( cd "$raiz"
    for x in usr/bin/* usr/lib/integra/*.sh usr/lib/integra/ponto-de-restauracao usr/lib/integra/logos/oudedetai \
             usr/lib/integra/aviso-de-atualizacoes usr/lib/integra/sessao-de-teste-apparmor etc/profile.d/*.sh \
             DEBIAN/preinst DEBIAN/postinst DEBIAN/prerm DEBIAN/postrm usr/bin/euro-office-euro-office; do
      [ -f "$x" ] && chmod 0755 "$x"
    done
    true )
  dpkg-deb --root-owner-group -Zxz --build "$raiz" "$SAIDA/${nome}_${VERSAO_DEB}_all.deb" >/dev/null
  echo "  $(basename "$SAIDA/${nome}_${VERSAO_DEB}_all.deb")"
done
