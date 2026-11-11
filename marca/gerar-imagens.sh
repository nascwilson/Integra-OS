#!/usr/bin/env bash
# Gera as imagens PNG da marca a partir dos SVG (precisa de rsvg-convert).
set -euo pipefail
# Destino: a árvore do pacote integra-marca.
M="$(cd "$(dirname "$0")" && pwd)"
S="$M/svg"; R="${1:-$M/../pacotes/integra-marca}"

# papel de parede (pacote de papel de parede do Plasma)
P="$R/usr/share/wallpapers/iNTEGRA/contents/images"; mkdir -p "$P"
for t in 1920x1080 2560x1440 3840x2160; do
  rsvg-convert -w "${t%x*}" -h "${t#*x}" "$S/wallpaper.svg" -o "$P/$t.png"
done
rsvg-convert -w 400 -h 225 "$S/wallpaper.svg" -o "$R/usr/share/wallpapers/iNTEGRA/contents/screenshot.png"

# ícone do sistema (botão Iniciar, sobre o sistema)
mkdir -p "$R/usr/share/icons/hicolor/scalable/apps" "$R/usr/share/pixmaps"
cp "$S/logo.svg" "$R/usr/share/icons/hicolor/scalable/apps/integra-logo.svg"
for t in 16 22 32 48 64 128 256; do
  mkdir -p "$R/usr/share/icons/hicolor/${t}x${t}/apps"
  rsvg-convert -w $t -h $t "$S/logo.svg" -o "$R/usr/share/icons/hicolor/${t}x${t}/apps/integra-logo.png"
done
cp "$R/usr/share/icons/hicolor/256x256/apps/integra-logo.png" "$R/usr/share/pixmaps/integra-logo.png"

# tela de inicialização (Plymouth)
PL="$R/usr/share/plymouth/themes/integra"; mkdir -p "$PL"
rsvg-convert -h 150 "$S/logo-mark-white.svg" -o "$PL/logo.png"
rsvg-convert -w 240 -h 4 "$S/barra-fundo.svg" -o "$PL/barra-fundo.png"
rsvg-convert -w 240 -h 4 "$S/barra-cheia.svg" -o "$PL/barra-cheia.png"

# instalador (Calamares)
C="$R/etc/calamares/branding/integra"; mkdir -p "$C"
rsvg-convert -w 128 -h 128 "$S/logo.svg" -o "$C/logo.png"
rsvg-convert -w 320 -h 320 "$S/logo.svg" -o "$C/boas-vindas.png"
rsvg-convert -w 960 -h 540 "$S/wallpaper.svg" -o "$C/fundo.png"
echo "imagens geradas em $R"
