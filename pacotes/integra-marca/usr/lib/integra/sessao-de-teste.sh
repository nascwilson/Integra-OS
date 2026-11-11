#!/bin/sh
# Só na sessão de teste (pendrive): sem bloqueio de tela e sem apagar o monitor.
# No sistema instalado este script não faz nada.
grep -q "boot=casper" /proc/cmdline || exit 0
kwriteconfig6 --file kscreenlockerrc --group Daemon --key Autolock false
kwriteconfig6 --file kscreenlockerrc --group Daemon --key LockOnResume false
for perfil in AC Battery LowBattery; do
  kwriteconfig6 --file powerdevilrc --group "$perfil" --group Display --key TurnOffDisplayWhenIdle false
  kwriteconfig6 --file powerdevilrc --group "$perfil" --group Display --key DimDisplayWhenIdle false
  kwriteconfig6 --file powerdevilrc --group "$perfil" --group SuspendAndShutdown --key AutoSuspendAction 0
done
dbus-send --session --type=method_call --dest=org.freedesktop.ScreenSaver /ScreenSaver org.kde.screensaver.configure 2>/dev/null
dbus-send --session --type=method_call --dest=org.kde.Solid.PowerManagement /org/kde/Solid/PowerManagement org.kde.Solid.PowerManagement.reparseConfiguration 2>/dev/null
exit 0
