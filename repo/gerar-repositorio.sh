#!/usr/bin/env bash
# =============================================================================
#  Monta o repositório APT do iNTEGRA a partir dos .deb gerados.
#
#  Uso: ./repo/gerar-repositorio.sh [pasta dos .deb] [pasta do repositório]
#  Assinatura (recomendada): defina INTEGRA_CHAVE com o ID da chave GPG.
#    gpg --quick-gen-key "Projeto iNTEGRA <seu-email>" rsa4096 sign 5y
#    INTEGRA_CHAVE=<ID> ./repo/gerar-repositorio.sh
#
#  O resultado pode ser publicado em qualquer servidor web estático
#  (GitHub Pages, por exemplo). Nos computadores, o arquivo
#  /etc/apt/sources.list.d/integra.sources aponta para esse endereço.
# =============================================================================
set -euo pipefail
AQUI="$(cd "$(dirname "$0")/.." && pwd)"
DEBS="${1:-$AQUI/saida/pacotes}"
REPO="${2:-$AQUI/saida/repositorio}"
SERIE="resolute"

command -v apt-ftparchive >/dev/null || { echo "falta apt-ftparchive (sudo apt install apt-utils)"; exit 1; }
ls "$DEBS"/*.deb >/dev/null 2>&1 || { echo "nenhum .deb em $DEBS (rode repo/gerar-pacotes.sh)"; exit 1; }

rm -rf "$REPO"
mkdir -p "$REPO/pool/main" "$REPO/dists/$SERIE/main/binary-amd64" "$REPO/dists/$SERIE/main/binary-all"
rm -f "$REPO"/pool/main/*.deb
cp "$DEBS"/*.deb "$REPO/pool/main/"
cd "$REPO"
for arq in amd64 all; do
  apt-ftparchive packages pool/main > "dists/$SERIE/main/binary-$arq/Packages"
  gzip -9kf "dists/$SERIE/main/binary-$arq/Packages"
done
apt-ftparchive \
  -o APT::FTPArchive::Release::Origin="iNTEGRA" \
  -o APT::FTPArchive::Release::Label="iNTEGRA OS" \
  -o APT::FTPArchive::Release::Suite="$SERIE" \
  -o APT::FTPArchive::Release::Codename="$SERIE" \
  -o APT::FTPArchive::Release::Architectures="amd64 all" \
  -o APT::FTPArchive::Release::Components="main" \
  release "dists/$SERIE" > "dists/$SERIE/Release"

if [ -n "${INTEGRA_CHAVE:-}" ]; then
  gpg --batch --yes -u "$INTEGRA_CHAVE" --clearsign -o "dists/$SERIE/InRelease" "dists/$SERIE/Release"
  gpg --batch --yes -u "$INTEGRA_CHAVE" -abs -o "dists/$SERIE/Release.gpg" "dists/$SERIE/Release"
  gpg --export "$INTEGRA_CHAVE" > integra-archive.gpg
  echo "Repositório assinado com a chave $INTEGRA_CHAVE."
else
  echo "AVISO: repositório sem assinatura. Só use assim para testes locais ([trusted=yes])."
fi
echo "Repositório pronto em $REPO"
