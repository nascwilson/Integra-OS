# iNTEGRA OS: sem aceleração gráfica (sem "render node"), como em máquinas virtuais
# sem 3D, usa a renderização por software mais leve em vez de travar a tela.
if ! ls /dev/dri/renderD* >/dev/null 2>&1; then
    export KWIN_COMPOSE=Q
    export QT_QUICK_BACKEND=software
fi
