#!/usr/bin/env bash
# Abre a ISO numa máquina virtual QEMU (em Linux).
#   Uso: ./testar-qemu.sh [caminho/da.iso]
# Precisa de: sudo apt install qemu-system-x86 ovmf
set -euo pipefail
ISO="${1:-/srv/integra-build/saida/iNTEGRA-OS-0.2-teste-amd64.iso}"
[ -f "$ISO" ] || { echo "ISO não encontrada: $ISO"; exit 1; }

ACEL="-accel tcg"
[ -w /dev/kvm ] && ACEL="-accel kvm -cpu host"

exec qemu-system-x86_64 $ACEL -m 4096 -smp 2 \
  -bios /usr/share/ovmf/OVMF.fd \
  -device virtio-vga -display gtk \
  -device qemu-xhci -device usb-tablet \
  -audiodev pa,id=som -device intel-hda -device hda-duplex,audiodev=som \
  -nic user,model=virtio-net-pci \
  -cdrom "$ISO" -boot d
