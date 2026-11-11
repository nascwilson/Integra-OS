#!/usr/bin/env python3
# =============================================================================
#  Instalador iNTEGRA — instala ou executa um programa do Windows (.exe/.msi)
#  num ambiente próprio do Wine, depois de mostrar um aviso de compatibilidade.
#
#  O aviso é uma estimativa feita neste computador, sem internet: lê o
#  cabeçalho do arquivo e procura sinais conhecidos (instalador de driver,
#  anti-cheat de jogos, .NET, 32/64 bits, assinatura digital).
#
#  Uso: integra-windows arquivo.exe|arquivo.msi
#       integra-windows --analisar arquivo      (só imprime a análise)
#       integra-windows --captura f.png arquivo (teste: salva a janela)
# =============================================================================
import os
import re
import sys
from pathlib import Path

PREFIXOS = Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local/share"))) / "integra" / "windows"
LER_INICIO = 8 * 1024 * 1024
LER_FIM = 2 * 1024 * 1024

ANTICHEAT = [b"EasyAntiCheat", b"BattlEye", b"BEService", b"vgk.sys", b"Riot Vanguard", b"XIGNCODE",
             b"nProtect", b"GameGuard", b"FACEIT", b"PunkBuster", b"mhyprot"]
DRIVER = [b"DIFxAPI", b"DriverPackageInstall", b"UpdateDriverForPlugAndPlayDevices",
          b"SetupDiCallClassInstaller", b"pnputil", b"DrvInst", b"dpinst"]
INSTALADORES = [(b"Inno Setup", "Instalador Inno Setup"), (b"Nullsoft", "Instalador NSIS"),
                (b"InstallShield", "Instalador InstallShield"), (b"Advanced Installer", "Advanced Installer"),
                (b"InstallAware", "Instalador InstallAware"), (b"Squirrel", "Instalador Squirrel"),
                (b"7-Zip", "Arquivo autoextraível 7-Zip"), (b"WinRAR SFX", "Arquivo autoextraível WinRAR"),
                (b"WixBundle", "Instalador WiX")]


def _u16(b, o):
    return int.from_bytes(b[o:o + 2], "little")


def _u32(b, o):
    return int.from_bytes(b[o:o + 4], "little")


def analisar(caminho):
    """Devolve um dicionário com nivel (boa/incerta/baixa/nao), rótulo, cor e detalhes."""
    p = Path(caminho)
    r = dict(arquivo=p.name, tipo="Arquivo desconhecido", arquitetura="—", assinatura="—",
             motivos=[], nivel="incerta")
    try:
        tam = p.stat().st_size
        with open(p, "rb") as f:
            inicio = f.read(LER_INICIO)
            fim = b""
            if tam > LER_INICIO:
                f.seek(max(LER_INICIO, tam - LER_FIM))
                fim = f.read(LER_FIM)
    except OSError as e:
        r.update(nivel="nao", motivos=[f"Não foi possível ler o arquivo ({e.strerror})."])
        return r
    texto = inicio + fim
    utf16 = lambda s: s.decode("ascii").encode("utf-16-le")

    def contem(lista):
        return [s.decode() for s in lista if s in texto or utf16(s) in texto]

    # --- formato -------------------------------------------------------------
    if inicio[:8] == b"\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1":
        r["tipo"] = "Pacote de instalação do Windows (.msi)"
        r["arquitetura"] = "64 bits" if b"x64" in texto or utf16(b"x64") in texto else "32 ou 64 bits"
        r["nivel"] = "boa"
    elif inicio[:2] == b"MZ" and len(inicio) > 0x40:
        pe = _u32(inicio, 0x3C)
        assinatura = inicio[pe:pe + 4]
        if assinatura == b"PE\0\0":
            maquina = _u16(inicio, pe + 4)
            opc = pe + 24
            magico = _u16(inicio, opc)
            subsistema = _u16(inicio, opc + 68)
            dirs = opc + (112 if magico == 0x20B else 96)
            cert = _u32(inicio, dirs + 4 * 8 + 4)      # diretório 4: certificado
            clr = _u32(inicio, dirs + 14 * 8 + 4)      # diretório 14: .NET
            r["arquitetura"] = {0x14C: "32 bits", 0x8664: "64 bits", 0xAA64: "ARM64",
                                0x1C4: "ARM 32 bits"}.get(maquina, f"desconhecida ({maquina:#x})")
            r["tipo"] = "Programa de linha de comando" if subsistema == 3 else "Programa do Windows"
            r["assinatura"] = "Assinado digitalmente" if cert else "Sem assinatura digital"
            r["nivel"] = "boa"
            for marca, nome in INSTALADORES:
                if marca in texto:
                    r["tipo"] = nome
                    break
            if maquina in (0xAA64, 0x1C4):
                r["nivel"] = "nao"
                r["motivos"].append("Feito para processadores ARM; este computador usa Intel/AMD.")
            if clr:
                r["nivel"] = "incerta" if r["nivel"] == "boa" else r["nivel"]
                r["motivos"].append("Programa .NET: costuma funcionar, mas alguns precisam de componentes extras.")
        elif inicio[pe:pe + 2] == b"NE":
            r["tipo"] = "Programa antigo do Windows (16 bits)"
            r["arquitetura"] = "16 bits"
            r["nivel"] = "incerta"
            r["motivos"].append("Programas de 16 bits funcionam só em parte.")
        else:
            r["tipo"] = "Programa do DOS"
            r["nivel"] = "baixa"
            r["motivos"].append("Programas do DOS rodam melhor no DOSBox.")
    else:
        r["nivel"] = "nao"
        r["motivos"].append("Não parece um programa do Windows (.exe) nem um pacote .msi.")
        return r

    # --- sinais de problema --------------------------------------------------
    ac = contem(ANTICHEAT)
    if ac:
        r["nivel"] = "baixa"
        r["motivos"].append(f"Usa anti-cheat de jogos online ({', '.join(ac[:2])}), que quase nunca funciona fora do Windows.")
    drv = contem(DRIVER)
    if drv or re.search(r"driver", p.name, re.I):
        r["nivel"] = "baixa"
        r["motivos"].append("Parece instalar um driver de hardware. Drivers do Windows não funcionam aqui; "
                            "veja Central iNTEGRA › Dispositivos e drivers.")
    if r["assinatura"] == "Sem assinatura digital":
        r["motivos"].append("Sem assinatura digital: instale só se confiar em quem forneceu o arquivo.")
    if r["tipo"].startswith(("Instalador", "Arquivo autoextraível", "Advanced")) and r["nivel"] == "boa":
        r["motivos"].append("Instaladores compactados escondem parte do conteúdo; a estimativa é parcial.")
    return r


ROTULOS = {"boa": ("Boa", "#0E3A2A", "#7FE0B4"), "incerta": ("Incerta", "#3A3014", "#FFD27A"),
           "baixa": ("Baixa", "#3A1A22", "#F5A0A0"), "nao": ("Não compatível", "#3A1A22", "#F5A0A0")}


def nome_ambiente(arquivo):
    base = Path(arquivo).stem
    return re.sub(r"[^A-Za-z0-9._-]", "_", base) or "programa"


# =============================================================================
#  Janela
# =============================================================================
def janela(arquivo, captura=None):
    from PyQt6.QtCore import QProcess, QProcessEnvironment, Qt, QTimer
    from PyQt6.QtGui import QIcon
    from PyQt6.QtWidgets import (QApplication, QDialog, QFrame, QHBoxLayout, QLabel, QProgressBar,
                                 QPushButton, QVBoxLayout, QWidget)

    app = QApplication(sys.argv)
    app.setApplicationName("Instalador iNTEGRA")
    app.setDesktopFileName("integra-windows")
    app.setStyleSheet("""
        QDialog { background: #12233A; }
        QWidget { color: #E6EEF5; font-family: Inter, sans-serif; font-size: 10pt; }
        QLabel#titulo { font-family: Sora, Inter, sans-serif; font-size: 15pt; font-weight: 600; color: #FFFFFF; }
        QFrame#caixa { background: #0D1A2B; border: 1px solid #1F3650; border-radius: 10px; }
        QPushButton { background: transparent; border: 1px solid #2E5170; border-radius: 8px; padding: 9px 18px; }
        QPushButton:hover { background: #16283D; }
        QPushButton#primario { background: #0077B6; border: 0; color: white; font-weight: 600; }
        QPushButton#primario:hover { background: #0089D1; }
        QProgressBar { background: #1B2F45; border: 0; border-radius: 4px; max-height: 8px; }
        QProgressBar::chunk { background: #36B3EB; border-radius: 4px; }
    """)
    a = analisar(arquivo)
    rotulo, fundo_chip, cor_chip = ROTULOS[a["nivel"]]
    ambiente = PREFIXOS / nome_ambiente(arquivo)

    d = QDialog()
    d.setWindowTitle("Instalador iNTEGRA")
    d.setWindowIcon(QIcon.fromTheme("integra-logo"))
    d.setMinimumWidth(560)
    v = QVBoxLayout(d)
    v.setContentsMargins(26, 24, 26, 22)
    v.setSpacing(16)

    topo = QHBoxLayout()
    topo.setSpacing(16)
    icone = QLabel()
    icone.setPixmap(QIcon.fromTheme("application-x-ms-dos-executable").pixmap(56, 56))
    icone.setFixedSize(60, 60)
    topo.addWidget(icone, 0, Qt.AlignmentFlag.AlignTop)
    col = QVBoxLayout()
    col.setSpacing(6)
    t = QLabel("Instalar programa do Windows")
    t.setObjectName("titulo")
    col.addWidget(t)
    exp = QLabel(f"<b>{a['arquivo']}</b> será aberto pela camada de compatibilidade, "
                 "num ambiente separado dos outros programas.")
    exp.setWordWrap(True)
    exp.setStyleSheet("color: #C9D6E3;")
    col.addWidget(exp)
    topo.addLayout(col, 1)
    v.addLayout(topo)

    caixa = QFrame()
    caixa.setObjectName("caixa")
    cv = QVBoxLayout(caixa)
    cv.setContentsMargins(16, 14, 16, 14)
    cv.setSpacing(10)

    def linha(nome, valor_widget):
        h = QHBoxLayout()
        n = QLabel(nome)
        n.setStyleSheet("color: #9FB3C8;")
        h.addWidget(n)
        h.addStretch(1)
        h.addWidget(valor_widget)
        cv.addLayout(h)

    chip = QLabel(rotulo)
    chip.setStyleSheet(f"background: {fundo_chip}; color: {cor_chip}; border-radius: 10px; "
                       "padding: 3px 12px; font-weight: 600;")
    linha("Compatibilidade estimada", chip)
    linha("Tipo", QLabel(a["tipo"]))
    linha("Arquitetura", QLabel(a["arquitetura"]))
    linha("Assinatura", QLabel(a["assinatura"]))
    v.addWidget(caixa)

    for m in a["motivos"]:
        lm = QLabel("•  " + m)
        lm.setWordWrap(True)
        lm.setStyleSheet("color: #C9D6E3;")
        v.addWidget(lm)
    nota = QLabel("Estimativa feita neste computador, sem internet. Só a instalação confirma se o programa funciona.")
    nota.setWordWrap(True)
    nota.setStyleSheet("color: #8EA3B8; font-size: 9pt;")
    v.addWidget(nota)

    progresso = QProgressBar()
    progresso.setRange(0, 0)
    progresso.setVisible(False)
    v.addWidget(progresso)

    botoes = QHBoxLayout()
    botoes.addStretch(1)
    cancelar = QPushButton("Cancelar")
    instalar = QPushButton("Instalar mesmo assim" if a["nivel"] in ("baixa",) else "Instalar")
    instalar.setObjectName("primario")
    instalar.setEnabled(a["nivel"] != "nao")
    instalar.setDefault(a["nivel"] != "nao")
    botoes.addWidget(cancelar)
    botoes.addWidget(instalar)
    v.addLayout(botoes)
    cancelar.clicked.connect(d.reject)

    env = QProcessEnvironment.systemEnvironment()
    env.insert("WINEPREFIX", str(ambiente))
    env.insert("WINEDEBUG", "-all")
    proc = QProcess(d)
    proc.setProcessEnvironment(env)

    estado = {"executar": False}

    def abrir_programa():
        # o programa é aberto depois que a janela fecha, neste mesmo processo
        # (assim ele não é encerrado junto com o instalador)
        estado["executar"] = True
        d.accept()

    def comecar():
        instalar.setEnabled(False)
        cancelar.setEnabled(False)
        instalar.setText("Preparando o ambiente…")
        progresso.setVisible(True)
        PREFIXOS.mkdir(parents=True, exist_ok=True)
        proc.finished.connect(lambda *_: abrir_programa())
        proc.start("wine", ["wineboot", "--init"])

    instalar.clicked.connect(comecar)
    d.show()
    if captura:
        QTimer.singleShot(1500, lambda: (d.grab().save(captura), app.quit()))
    codigo = app.exec()
    if estado["executar"]:
        executar_direto(arquivo)
    return codigo


def executar_direto(arquivo):
    """Programa que já tem ambiente: abre direto, sem perguntar de novo."""
    env = dict(os.environ, WINEPREFIX=str(PREFIXOS / nome_ambiente(arquivo)), WINEDEBUG="-all")
    args = ["wine", "msiexec", "/i", arquivo] if arquivo.lower().endswith(".msi") else ["wine", arquivo]
    os.execvpe("wine", args, env)


def main():
    args = sys.argv[1:]
    if not args:
        print("uso: integra-windows arquivo.exe|arquivo.msi")
        return 2
    if args[0] == "--analisar":
        for a in args[1:]:
            r = analisar(a)
            print(f"{r['arquivo']}: {ROTULOS[r['nivel']][0]} | {r['tipo']} | {r['arquitetura']} | {r['assinatura']}")
            for m in r["motivos"]:
                print("   -", m)
        return 0
    if args[0] == "--captura":
        return janela(os.path.abspath(args[2]), captura=args[1])
    arquivo = os.path.abspath(args[0])
    if (PREFIXOS / nome_ambiente(arquivo) / "drive_c").is_dir():
        executar_direto(arquivo)
    return janela(arquivo)


if __name__ == "__main__":
    sys.exit(main())
