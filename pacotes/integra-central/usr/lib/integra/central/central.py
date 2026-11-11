#!/usr/bin/env python3
# =============================================================================
#  Central iNTEGRA — reúne os gerenciadores do sistema num só lugar.
#  Parte do iNTEGRA OS. Licença: GPL-3.0-or-later.
#
#  Uso:  integra-central                 abre a janela
#        integra-central --captura f.png [pagina]   (teste) salva a tela
# =============================================================================
import os
import re
import shutil
import socket
import subprocess
import sys
from pathlib import Path

from PyQt6.QtCore import QProcess, QProcessEnvironment, QSize, Qt, QThread, QTimer, QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices, QIcon
from PyQt6.QtWidgets import (
    QApplication, QFileDialog, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QMainWindow, QMessageBox, QProgressBar, QPushButton,
    QScrollArea, QSizePolicy, QStackedWidget, QVBoxLayout, QWidget,
)

VERSAO = "0.6.1"
PREFIXOS = Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local/share"))) / "integra" / "windows"

C = dict(fundo="#101E2F", painel="#0D1A2B", lateral="#0B1726", borda="#1F3650", texto="#E6EEF5",
         suave="#9FB3C8", destaque="#36B3EB", acao="#0077B6", acao2="#0089D1", selecao="#133A5C",
         ok="#3DD68C", alerta="#FFC24A", erro="#F06A6A")

ESTILO = f"""
QMainWindow, QWidget#raiz {{ background: {C['fundo']}; }}
QWidget {{ color: {C['texto']}; font-family: Inter, sans-serif; font-size: 10pt; }}
QWidget#lateral {{ background: {C['lateral']}; border-right: 1px solid {C['borda']}; }}
QListWidget {{ background: transparent; border: 0; outline: 0; }}
QListWidget::item {{ height: 34px; padding-left: 8px; border-radius: 6px; color: {C['texto']}; }}
QListWidget::item:selected {{ background: {C['selecao']}; color: #FFFFFF; }}
QListWidget::item:hover:!selected {{ background: #12243A; }}
QListWidget::item:disabled {{ color: {C['suave']}; padding-top: 10px; }}
QLineEdit {{ background: {C['painel']}; border: 1px solid {C['borda']}; border-radius: 8px; padding: 7px 10px; }}
QLabel#titulo {{ font-family: Sora, Inter, sans-serif; font-size: 20pt; font-weight: 600; color: #FFFFFF; }}
QLabel#subtitulo {{ color: {C['suave']}; }}
QLabel#secao {{ font-family: Sora, Inter, sans-serif; font-size: 13pt; font-weight: 600; color: #FFFFFF; }}
QFrame#cartao {{ background: {C['painel']}; border: 1px solid {C['borda']}; border-radius: 12px; }}
QPushButton {{ background: transparent; border: 1px solid #2E5170; border-radius: 8px; padding: 8px 16px; color: {C['texto']}; }}
QPushButton:hover {{ background: #16283D; }}
QPushButton#primario {{ background: {C['acao']}; border: 0; color: #FFFFFF; font-weight: 600; }}
QPushButton#primario:hover {{ background: {C['acao2']}; }}
QPushButton#perigo:hover {{ background: #3A1A22; border-color: {C['erro']}; }}
QProgressBar {{ background: #1B2F45; border: 0; border-radius: 4px; max-height: 8px; }}
QProgressBar::chunk {{ background: {C['destaque']}; border-radius: 4px; }}
QScrollArea {{ background: transparent; border: 0; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
"""


# --------------------------------------------------------------------------- utilidades
def rodar(cmd, timeout=30):
    """Executa um comando e devolve a saída (texto) ou None se falhar."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                           env={**os.environ, "LC_ALL": "C"})
        return r.stdout if r.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        return None


def tem(prog):
    return shutil.which(prog) is not None


def abrir(cmd, env=None):
    """Abre um programa externo sem prender a Central."""
    if not tem(cmd[0]):
        QMessageBox.warning(None, "Central iNTEGRA", f"O programa “{cmd[0]}” não está instalado.")
        return
    p = QProcess()
    p.setProgram(cmd[0])
    p.setArguments(cmd[1:])
    if env:
        e = QProcessEnvironment.systemEnvironment()
        for k, v in env.items():
            e.insert(k, v)
        p.setProcessEnvironment(e)
    p.startDetached()


def tamanho_legivel(n):
    for un in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or un == "TB":
            return f"{n:.0f} {un}" if un in ("B", "KB") else f"{n:.1f} {un}".replace(".", ",")
        n /= 1024


def tamanho_pasta(p):
    total = 0
    for raiz, _, arquivos in os.walk(p):
        for a in arquivos:
            try:
                total += os.lstat(os.path.join(raiz, a)).st_size
            except OSError:
                pass
    return total


def info_sistema():
    nome, versao = "iNTEGRA OS", ""
    try:
        for linha in open("/etc/os-release", encoding="utf-8"):
            if linha.startswith("NAME="):
                nome = linha.split("=", 1)[1].strip().strip('"')
            elif linha.startswith("VERSION="):
                versao = linha.split("=", 1)[1].strip().strip('"')
    except OSError:
        pass
    return f"{nome} {versao}".strip()


def sessao_de_teste():
    try:
        return "boot=casper" in Path("/proc/cmdline").read_text()
    except OSError:
        return False


def listas_de_pacotes_baixadas():
    return any(Path("/var/lib/apt/lists").glob("*_Packages*"))


def contar_atualizacoes():
    if not listas_de_pacotes_baixadas():
        return "sem-listas"
    saida = rodar(["apt-get", "-s", "-o", "Debug::NoLocking=1", "dist-upgrade"], timeout=60)
    if saida is None:
        return None
    return sum(1 for l in saida.splitlines() if l.startswith("Inst "))


def drivers_adicionais():
    if not tem("ubuntu-drivers"):
        return None
    saida = rodar(["ubuntu-drivers", "list"], timeout=60)
    if saida is None:
        return None
    return [l.split(",")[0].strip() for l in saida.splitlines() if l.strip() and not l.startswith(" ")]


def firewall_ativo():
    try:
        return "ENABLED=yes" in Path("/etc/ufw/ufw.conf").read_text()
    except OSError:
        return None


def ultimo_ponto():
    try:
        import datetime
        ts = int(Path("/var/lib/integra/ultimo-ponto").read_text().strip())
        return datetime.datetime.fromtimestamp(ts).strftime("%d/%m às %H:%M")
    except (OSError, ValueError):
        return None


def restauracao_automatica():
    return Path("/usr/lib/integra/ponto-de-restauracao").exists() and \
        not Path("/etc/integra/sem-ponto-de-restauracao").exists()


def restauracao_configurada():
    try:
        txt = Path("/etc/timeshift/timeshift.json").read_text()
        return bool(re.search(r'"backup_device_uuid"\s*:\s*"[^"]+"', txt))
    except OSError:
        return False


CLASSES = {
    "VGA compatible controller": "Placa de vídeo", "3D controller": "Placa de vídeo",
    "Display controller": "Placa de vídeo", "Network controller": "Wi-Fi",
    "Ethernet controller": "Rede cabeada", "Audio device": "Áudio",
    "Multimedia audio controller": "Áudio", "USB controller": "Controlador USB",
    "SATA controller": "Controlador de disco", "IDE interface": "Controlador de disco",
    "Non-Volatile memory controller": "Disco SSD (NVMe)", "Mass storage controller": "Controlador de disco",
    "SCSI storage controller": "Controlador de disco", "Unclassified device": "Outro dispositivo",
}
OCULTAR = ("bridge", "SMBus", "Signal processing", "RAM memory", "Serial bus", "System peripheral",
           "Communication controller", "PIC", "Performance counters", "Encryption controller")


def dispositivos_pci():
    saida = rodar(["lspci", "-vmmk"])
    if saida is None:
        return []
    itens = []
    for bloco in saida.strip().split("\n\n"):
        d = dict(l.split(":\t", 1) for l in bloco.splitlines() if ":\t" in l)
        classe = d.get("Class", "")
        if any(o.lower() in classe.lower() for o in OCULTAR):
            continue
        tipo = CLASSES.get(classe, "Outro dispositivo" if classe.startswith("Unassigned") else classe)
        itens.append(dict(tipo=tipo, nome=f"{d.get('Vendor', '')} {d.get('Device', '')}".strip(),
                          driver=d.get("Driver", "")))
    ordem = ["Placa de vídeo", "Wi-Fi", "Rede cabeada", "Áudio"]
    itens.sort(key=lambda i: (ordem.index(i["tipo"]) if i["tipo"] in ordem else 9, i["tipo"]))
    return itens


def dispositivos_usb():
    saida = rodar(["lsusb"])
    if saida is None:
        return []
    itens = []
    for l in saida.splitlines():
        m = re.match(r"Bus \d+ Device \d+: ID [0-9a-f]{4}:[0-9a-f]{4}\s*(.*)", l)
        if m and "root hub" not in m.group(1):
            itens.append(dict(tipo="USB", nome=m.group(1).strip() or "Dispositivo USB", driver="usb"))
    return itens


def versao_wine():
    saida = rodar(["wine", "--version"], timeout=20)
    return saida.strip() if saida else None


# --------------------------------------------------------------------------- tarefas em segundo plano
class Tarefa(QThread):
    pronto = pyqtSignal(object)

    def __init__(self, funcao, pai):
        super().__init__(pai)
        self.funcao = funcao

    def run(self):
        try:
            r = self.funcao()
        except Exception as e:  # nunca derrubar a janela por um status
            r = e
        self.pronto.emit(r)


# --------------------------------------------------------------------------- peças de interface
def rotulo(texto, nome=None, suave=False, quebra=False):
    l = QLabel(texto)
    if nome:
        l.setObjectName(nome)
    if suave:
        l.setStyleSheet(f"color: {C['suave']};")
    l.setWordWrap(quebra)
    return l


def cartao():
    f = QFrame()
    f.setObjectName("cartao")
    return f


def ponto(cor):
    p = QLabel()
    p.setFixedSize(10, 10)
    p.setStyleSheet(f"background: {cor}; border-radius: 5px;")
    return p


class CartaoStatus(QFrame):
    def __init__(self, titulo, botao=None, acao=None):
        super().__init__()
        self.setObjectName("cartao")
        v = QVBoxLayout(self)
        v.setContentsMargins(16, 14, 16, 14)
        v.setSpacing(8)
        v.addWidget(rotulo(titulo, suave=True))
        h = QHBoxLayout()
        h.setSpacing(8)
        self.ponto = ponto(C["suave"])
        self.texto = rotulo("Verificando…", quebra=True)
        self.texto.setStyleSheet("font-weight: 500;")
        h.addWidget(self.ponto, 0, Qt.AlignmentFlag.AlignTop)
        h.addWidget(self.texto, 1)
        v.addLayout(h)
        self.botao = None
        if botao:
            self.botao = QPushButton(botao)
            self.botao.clicked.connect(acao)
            self.botao.setVisible(False)
            v.addWidget(self.botao, 0, Qt.AlignmentFlag.AlignLeft)
        v.addStretch(1)

    def definir(self, texto, cor, mostrar_botao=False):
        self.texto.setText(texto)
        self.ponto.setStyleSheet(f"background: {cor}; border-radius: 5px;")
        if self.botao:
            self.botao.setVisible(mostrar_botao)


class Medidor(QWidget):
    def __init__(self, nome):
        super().__init__()
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(6)
        h = QHBoxLayout()
        h.addWidget(rotulo(nome))
        h.addStretch(1)
        self.valor = rotulo("—", suave=True)
        h.addWidget(self.valor)
        v.addLayout(h)
        self.barra = QProgressBar()
        self.barra.setTextVisible(False)
        self.barra.setRange(0, 1000)
        v.addWidget(self.barra)

    def definir(self, fracao, texto):
        self.barra.setValue(int(max(0.0, min(1.0, fracao)) * 1000))
        self.valor.setText(texto)


# --------------------------------------------------------------------------- páginas
class Pagina(QScrollArea):
    def __init__(self, titulo, subtitulo=""):
        super().__init__()
        self.setWidgetResizable(True)
        corpo = QWidget()
        self.layout_ = QVBoxLayout(corpo)
        self.layout_.setContentsMargins(32, 28, 32, 28)
        self.layout_.setSpacing(20)
        cab = QVBoxLayout()
        cab.setSpacing(4)
        cab.addWidget(rotulo(titulo, "titulo"))
        if subtitulo:
            self.sub = rotulo(subtitulo, "subtitulo", suave=True)
            cab.addWidget(self.sub)
        self.layout_.addLayout(cab)
        self.setWidget(corpo)

    def add(self, w, stretch=0):
        self.layout_.addWidget(w, stretch)

    def fim(self):
        self.layout_.addStretch(1)


class VisaoGeral(Pagina):
    def __init__(self, janela):
        super().__init__("Visão geral", f"{info_sistema()} · {socket.gethostname()}")
        self.janela = janela
        grade = QGridLayout()
        grade.setSpacing(14)
        self.c_atual = CartaoStatus("Atualizações", "Atualizar agora",
                                    lambda: abrir(["plasma-discover", "--mode", "update"]))
        self.c_drv = CartaoStatus("Dispositivos e drivers", "Ver drivers", lambda: janela.ir_para("dispositivos"))
        self.c_fw = CartaoStatus("Segurança", "Ativar firewall", lambda: abrir(["systemsettings", "kcm_firewall"]))
        self.c_rest = CartaoStatus("Pontos de restauração", "Configurar", lambda: abrir(["timeshift-launcher"]))
        for i, c in enumerate((self.c_atual, self.c_drv, self.c_fw, self.c_rest)):
            grade.addWidget(c, 0, i)
        w = QWidget()
        w.setLayout(grade)
        self.add(w)

        desemp = cartao()
        v = QVBoxLayout(desemp)
        v.setContentsMargins(20, 18, 20, 20)
        v.setSpacing(16)
        h = QHBoxLayout()
        h.addWidget(rotulo("Desempenho agora", "secao"))
        h.addStretch(1)
        b = QPushButton("Abrir Gerenciador de tarefas")
        b.clicked.connect(lambda: abrir(["plasma-systemmonitor"]))
        h.addWidget(b)
        v.addLayout(h)
        self.m_mem = Medidor("Memória")
        self.m_cpu = Medidor("Processador")
        self.m_disco = Medidor("Disco do sistema")
        for m in (self.m_mem, self.m_cpu, self.m_disco):
            v.addWidget(m)
        self.add(desemp)
        self.fim()

        self._cpu_ant = None
        self.atualizar_medidores()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.atualizar_medidores)
        self.timer.start(2000)

        fw = firewall_ativo()
        if fw:
            self.c_fw.definir("Firewall ativo", C["ok"])
        elif fw is False:
            self.c_fw.definir("Firewall desligado", C["alerta"], True)
        else:
            self.c_fw.definir("Firewall não instalado", C["suave"])
        ultimo = ultimo_ponto()
        if sessao_de_teste():
            self.c_rest.definir("Indisponíveis na sessão de teste", C["suave"])
        elif ultimo:
            self.c_rest.definir(f"Último ponto: {ultimo}", C["ok"])
        elif restauracao_automatica():
            self.c_rest.definir("Criados antes de cada atualização", C["ok"])
        elif restauracao_configurada():
            self.c_rest.definir("Configurados", C["ok"])
        else:
            self.c_rest.definir("Ainda não configurados", C["alerta"], True)
        janela.em_segundo_plano(contar_atualizacoes, self._atualizacoes)
        janela.em_segundo_plano(drivers_adicionais, self._drivers)

    def _atualizacoes(self, n):
        if n == "sem-listas":
            self.c_atual.definir("Ainda não verificadas", C["suave"], True)
        elif isinstance(n, int):
            if n == 0:
                self.c_atual.definir("Sistema em dia", C["ok"])
            else:
                self.c_atual.definir(f"{n} atualizaç{'ão disponível' if n == 1 else 'ões disponíveis'}", C["alerta"], True)
        else:
            self.c_atual.definir("Não foi possível verificar", C["suave"], True)

    def _drivers(self, lista):
        if isinstance(lista, list):
            if lista:
                self.c_drv.definir(f"{len(lista)} driver{'s' if len(lista) > 1 else ''} do fabricante disponíve{'is' if len(lista) > 1 else 'l'}", C["alerta"], True)
            else:
                self.c_drv.definir("Nenhum driver extra necessário", C["ok"])
        else:
            self.c_drv.definir("Verificação indisponível", C["suave"])

    def atualizar_medidores(self):
        try:
            mem = {}
            for l in open("/proc/meminfo"):
                k, v = l.split(":", 1)
                mem[k] = int(v.split()[0]) * 1024
            usado = mem["MemTotal"] - mem["MemAvailable"]
            self.m_mem.definir(usado / mem["MemTotal"],
                               f"{tamanho_legivel(usado)} de {tamanho_legivel(mem['MemTotal'])}")
        except (OSError, KeyError, ValueError):
            pass
        try:
            campos = [int(x) for x in open("/proc/stat").readline().split()[1:]]
            ocioso, total = campos[3] + campos[4], sum(campos)
            if self._cpu_ant:
                dt, di = total - self._cpu_ant[1], ocioso - self._cpu_ant[0]
                uso = 1 - di / dt if dt else 0
                self.m_cpu.definir(uso, f"{uso * 100:.0f}%")
            self._cpu_ant = (ocioso, total)
        except (OSError, ValueError, IndexError):
            pass
        if sessao_de_teste():
            self.m_disco.definir(0, "Sessão de teste: nada é gravado no disco")
            return
        try:
            d = shutil.disk_usage("/")
            self.m_disco.definir(d.used / d.total, f"{tamanho_legivel(d.free)} livres de {tamanho_legivel(d.total)}")
        except OSError:
            pass


class Dispositivos(Pagina):
    def __init__(self, janela):
        super().__init__("Dispositivos e drivers", "Peças do computador e o driver que cada uma está usando")
        self.janela = janela
        self.lista = cartao()
        self.v = QVBoxLayout(self.lista)
        self.v.setContentsMargins(20, 12, 20, 12)
        self.v.setSpacing(0)
        self.v.addWidget(rotulo("Lendo dispositivos…", suave=True))
        self.add(self.lista)
        self.add(rotulo("Drivers do fabricante", "secao"))
        self.extra = cartao()
        self.ve = QVBoxLayout(self.extra)
        self.ve.setContentsMargins(20, 14, 20, 14)
        self.ve.addWidget(rotulo("Procurando drivers do fabricante…", suave=True))
        self.add(self.extra)
        self.fim()
        janela.em_segundo_plano(lambda: dispositivos_pci() + dispositivos_usb(), self._mostrar)
        janela.em_segundo_plano(drivers_adicionais, self._extras)
        self.processo = None

    @staticmethod
    def _limpar(layout):
        while layout.count():
            w = layout.takeAt(0).widget()
            if w:
                w.deleteLater()

    def _linha(self, tipo, nome, status, cor, ultima=False):
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(0, 10, 0, 10)
        col = QVBoxLayout()
        col.setSpacing(2)
        col.addWidget(rotulo(tipo))
        n = rotulo(nome, suave=True)
        n.setStyleSheet(f"color: {C['suave']}; font-size: 9pt;")
        col.addWidget(n)
        h.addLayout(col, 1)
        s = rotulo(status)
        s.setStyleSheet(f"color: {cor};")
        h.addWidget(s)
        if not ultima:
            w.setStyleSheet(f"border-bottom: 1px solid #1B2F45;")
        return w

    def _mostrar(self, itens):
        self._limpar(self.v)
        if not isinstance(itens, list) or not itens:
            self.v.addWidget(rotulo("Não foi possível listar os dispositivos.", suave=True))
            return
        for i, d in enumerate(itens):
            if d["driver"] == "usb":
                status, cor = "Conectado", C["ok"]
            elif d["driver"]:
                status, cor = f"Funcionando ({d['driver']})", C["ok"]
            else:
                status, cor = "Sem driver", C["alerta"]
            self.v.addWidget(self._linha(d["tipo"], d["nome"], status, cor, i == len(itens) - 1))

    def _extras(self, lista):
        self._limpar(self.ve)
        if not isinstance(lista, list):
            self.ve.addWidget(rotulo("A verificação de drivers do fabricante não está disponível.", suave=True))
            return
        if not lista:
            self.ve.addWidget(rotulo("Nenhum driver do fabricante é necessário neste computador.", suave=True))
            return
        for pacote in lista:
            w = QWidget()
            h = QHBoxLayout(w)
            h.setContentsMargins(0, 6, 0, 6)
            h.addWidget(rotulo(pacote), 1)
            b = QPushButton("Instalar driver")
            b.setObjectName("primario")
            b.clicked.connect(lambda _=False, p=pacote, bt=b: self._instalar(p, bt))
            h.addWidget(b)
            self.ve.addWidget(w)

    def _instalar(self, pacote, botao):
        if QMessageBox.question(self, "Instalar driver",
                                f"Instalar o driver “{pacote}”?\n\nSerá pedida a senha de administrador. "
                                "Depois, reinicie o computador.") != QMessageBox.StandardButton.Yes:
            return
        botao.setEnabled(False)
        botao.setText("Instalando…")
        self.processo = QProcess(self)
        self.processo.finished.connect(lambda codigo, _s: self._instalado(codigo, botao))
        self.processo.start("pkexec", ["ubuntu-drivers", "install", pacote])

    def _instalado(self, codigo, botao):
        if codigo == 0:
            botao.setText("Instalado — reinicie")
            QMessageBox.information(self, "Driver instalado", "Driver instalado. Reinicie o computador para usá-lo.")
        else:
            botao.setEnabled(True)
            botao.setText("Tentar de novo")


class ProgramasWindows(Pagina):
    def __init__(self, janela):
        super().__init__("Programas do Windows", "Cada programa roda num ambiente separado, pela camada de compatibilidade")
        self.janela = janela
        topo = QHBoxLayout()
        self.versao = rotulo("Camada de compatibilidade: verificando…", suave=True)
        topo.addWidget(self.versao, 1)
        b = QPushButton("Instalar programa do Windows…")
        b.setObjectName("primario")
        b.clicked.connect(self.instalar)
        topo.addWidget(b)
        w = QWidget()
        w.setLayout(topo)
        self.add(w)
        self.caixa = QVBoxLayout()
        self.caixa.setSpacing(12)
        c = QWidget()
        c.setLayout(self.caixa)
        self.add(c)
        self.add(rotulo("Dica: dê dois cliques num arquivo .exe ou .msi para instalá-lo. "
                        "Jogos online com anti-cheat e instaladores de driver costumam não funcionar.",
                        suave=True, quebra=True))
        self.fim()
        janela.em_segundo_plano(versao_wine, lambda v: self.versao.setText(
            f"Camada de compatibilidade: {v}" if isinstance(v, str) else "Camada de compatibilidade não encontrada"))
        self.recarregar()

    def recarregar(self):
        Dispositivos._limpar(self.caixa)
        pastas = sorted((p for p in PREFIXOS.glob("*") if (p / "drive_c").is_dir()), key=lambda p: p.name.lower()) if PREFIXOS.is_dir() else []
        if not pastas:
            vazio = cartao()
            v = QVBoxLayout(vazio)
            v.setContentsMargins(20, 22, 20, 22)
            v.addWidget(rotulo("Nenhum programa do Windows instalado ainda.", suave=True))
            self.caixa.addWidget(vazio)
            return
        for p in pastas:
            self.caixa.addWidget(self._cartao_programa(p))

    def _cartao_programa(self, pasta):
        f = cartao()
        h = QHBoxLayout(f)
        h.setContentsMargins(20, 14, 16, 14)
        col = QVBoxLayout()
        col.setSpacing(2)
        col.addWidget(rotulo(pasta.name.replace("_", " ")))
        tam = rotulo("calculando tamanho…", suave=True)
        col.addWidget(tam)
        h.addLayout(col, 1)
        self.janela.em_segundo_plano(lambda: tamanho_pasta(pasta),
                                     lambda n: tam.setText(f"Ambiente próprio · {tamanho_legivel(n)}")
                                     if isinstance(n, int) else None)
        for texto, func, nome in (("Abrir pasta C:", lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(pasta / "drive_c"))), None),
                                  ("Configurar", lambda: abrir(["winecfg"], {"WINEPREFIX": str(pasta)}), None),
                                  ("Remover", lambda: self.remover(pasta), "perigo")):
            b = QPushButton(texto)
            if nome:
                b.setObjectName(nome)
            b.clicked.connect(func)
            h.addWidget(b)
        return f

    def instalar(self):
        arq, _ = QFileDialog.getOpenFileName(self, "Escolha o programa do Windows", str(Path.home() / "Downloads"),
                                             "Programas do Windows (*.exe *.msi *.EXE *.MSI)")
        if arq:
            abrir(["integra-windows", arq])

    def remover(self, pasta):
        if QMessageBox.question(self, "Remover programa",
                                f"Remover “{pasta.name}” e todos os arquivos dele?\nIsso não pode ser desfeito.") \
                != QMessageBox.StandardButton.Yes:
            return
        alvo = str(pasta)
        apps = Path.home() / ".local/share/applications/wine"
        if apps.is_dir():
            for d in apps.rglob("*.desktop"):
                try:
                    if alvo in d.read_text(errors="ignore"):
                        d.unlink()
                except OSError:
                    pass
        shutil.rmtree(pasta, ignore_errors=True)
        self.recarregar()


# --------------------------------------------------------------------------- janela
FERRAMENTAS = [
    ("Gerenciador de tarefas", "utilities-system-monitor", ["plasma-systemmonitor"]),
    ("Discos e armazenamento", "drive-harddisk", ["partitionmanager"]),
    ("Rede e internet", "network-wireless", ["systemsettings", "kcm_networkmanagement"]),
    ("Google Drive", "folder-gdrive", ["integra-google-drive"]),
    ("Impressoras e scanners", "printer", ["systemsettings", "kcm_printer_manager"]),
    ("Atualizações", "system-software-update", ["plasma-discover", "--mode", "update"]),
    ("Pontos de restauração", "timeshift", ["timeshift-launcher"]),
    ("Contas de usuário", "system-users", ["systemsettings", "kcm_users"]),
    ("Segurança e firewall", "security-high", ["systemsettings", "kcm_firewall"]),
    ("Energia e bateria", "battery-full", ["systemsettings", "kcm_powerdevilprofilesconfig"]),
    ("Telas e monitores", "preferences-desktop-display", ["systemsettings", "kcm_kscreen"]),
    ("Som", "audio-volume-high", ["systemsettings", "kcm_pulseaudio"]),
    ("Personalização", "preferences-desktop-theme-global", ["systemsettings", "kcm_lookandfeel"]),
    ("Sobre este computador", "help-about", ["kinfocenter"]),
]


class Janela(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Central iNTEGRA")
        self.setWindowIcon(QIcon.fromTheme("integra-logo"))
        self.resize(1180, 760)
        self.setMinimumSize(960, 620)
        self._tarefas = []

        raiz = QWidget()
        raiz.setObjectName("raiz")
        h = QHBoxLayout(raiz)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(0)

        lateral = QWidget()
        lateral.setObjectName("lateral")
        lateral.setFixedWidth(270)
        lv = QVBoxLayout(lateral)
        lv.setContentsMargins(12, 16, 12, 16)
        lv.setSpacing(10)
        self.busca = QLineEdit()
        self.busca.setPlaceholderText("Buscar configuração")
        self.busca.setAccessibleName("Buscar configuração")
        self.busca.textChanged.connect(self.filtrar)
        lv.addWidget(self.busca)
        self.menu = QListWidget()
        self.menu.setIconSize(QSize(18, 18))
        lv.addWidget(self.menu, 1)
        h.addWidget(lateral)

        self.pilha = QStackedWidget()
        h.addWidget(self.pilha, 1)
        self.setCentralWidget(raiz)

        self.paginas = {}
        for chave, titulo, icone, classe in (
                ("visao", "Visão geral", "go-home", VisaoGeral),
                ("dispositivos", "Dispositivos e drivers", "preferences-devices-tree", Dispositivos),
                ("windows", "Programas do Windows", "application-x-ms-dos-executable", ProgramasWindows)):
            pag = classe(self)
            self.paginas[chave] = self.pilha.addWidget(pag)
            it = QListWidgetItem(QIcon.fromTheme(icone), titulo)
            it.setData(Qt.ItemDataRole.UserRole, ("pagina", chave))
            self.menu.addItem(it)
        sep = QListWidgetItem("Ferramentas do sistema")
        sep.setFlags(Qt.ItemFlag.NoItemFlags)
        sep.setForeground(Qt.GlobalColor.gray)
        sep.setData(Qt.ItemDataRole.UserRole, ("secao", None))
        self.menu.addItem(sep)
        for titulo, icone, cmd in FERRAMENTAS:
            it = QListWidgetItem(QIcon.fromTheme(icone), titulo)
            it.setData(Qt.ItemDataRole.UserRole, ("externo", cmd))
            it.setToolTip("Abre em outra janela")
            self.menu.addItem(it)
        self.menu.setCurrentRow(0)
        self._linha_atual = 0
        self.menu.itemClicked.connect(self.clicar)

    def em_segundo_plano(self, funcao, ao_terminar):
        t = Tarefa(funcao, self)
        t.pronto.connect(ao_terminar)
        t.finished.connect(lambda: self._tarefas.remove(t) if t in self._tarefas else None)
        self._tarefas.append(t)
        t.start()

    def ir_para(self, chave):
        self.pilha.setCurrentIndex(self.paginas[chave])
        for i in range(self.menu.count()):
            if self.menu.item(i).data(Qt.ItemDataRole.UserRole) == ("pagina", chave):
                self.menu.setCurrentRow(i)
                self._linha_atual = i

    def clicar(self, item):
        tipo, valor = item.data(Qt.ItemDataRole.UserRole)
        if tipo == "pagina":
            self.ir_para(valor)
        elif tipo == "externo":
            abrir(valor)
            self.menu.setCurrentRow(self._linha_atual)

    def filtrar(self, texto):
        t = texto.strip().lower()
        for i in range(self.menu.count()):
            it = self.menu.item(i)
            tipo, _ = it.data(Qt.ItemDataRole.UserRole)
            it.setHidden(bool(t) and (tipo == "secao" or t not in it.text().lower()))


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Central iNTEGRA")
    app.setDesktopFileName("org.integra.central")
    app.setStyleSheet(ESTILO)
    janela = Janela()
    if "--captura" in sys.argv:
        i = sys.argv.index("--captura")
        destino = sys.argv[i + 1]
        pagina = sys.argv[i + 2] if len(sys.argv) > i + 2 else "visao"
        janela.ir_para(pagina)
        janela.show()
        QTimer.singleShot(int(os.environ.get("INTEGRA_ESPERA", "8000")),
                          lambda: (janela.grab().save(destino), app.quit()))
    else:
        janela.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
