#!/usr/bin/env python3
"""Google Drive no iNTEGRA OS.

Conecta a conta Google pelo rclone e mostra o Drive como uma pasta comum,
"Google Drive", dentro da pasta pessoal. O Google não tem programa oficial
para Linux; o rclone é software livre e conversa com o Drive pela API
oficial. A pasta é montada por um serviço do systemd do próprio usuário.
"""
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote

from PyQt6.QtCore import QProcess, Qt, QTimer
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QApplication, QDialog, QHBoxLayout, QLabel, QMessageBox, QPushButton, QVBoxLayout,
)

REMOTO = "GoogleDrive"
PASTA = Path.home() / "Google Drive"
SERVICO = "integra-google-drive.service"
CONF = Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))) / "rclone" / "rclone.conf"
LUGARES = Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local/share"))) / "user-places.xbel"

C = dict(fundo="#101E2F", painel="#0D1A2B", borda="#1F3650", texto="#E6EEF5", suave="#9FB3C8",
         acao="#0077B6", acao2="#0089D1", ok="#3DD68C", alerta="#FFC24A", erro="#F06A6A")
ESTILO = f"""
QDialog {{ background: {C['fundo']}; }}
QWidget {{ color: {C['texto']}; font-family: Inter, sans-serif; font-size: 10pt; }}
QLabel#titulo {{ font-family: Sora, Inter, sans-serif; font-size: 17pt; font-weight: 600; color: #FFFFFF; }}
QLabel#suave {{ color: {C['suave']}; }}
QPushButton {{ background: transparent; border: 1px solid #2E5170; border-radius: 8px; padding: 8px 16px; }}
QPushButton:hover {{ background: #16283D; }}
QPushButton#primario {{ background: {C['acao']}; border: 0; color: #FFFFFF; font-weight: 600; }}
QPushButton#primario:hover {{ background: {C['acao2']}; }}
QPushButton#perigo:hover {{ background: #3A1A22; border-color: {C['erro']}; }}
"""


def conectado() -> bool:
    """A conta está conectada quando o rclone guardou o token do remoto."""
    try:
        texto = CONF.read_text(encoding="utf-8")
    except OSError:
        return False
    secao = re.search(rf"^\[{REMOTO}\]\s*$(.*?)(?=^\[|\Z)", texto, re.M | re.S)
    return bool(secao and re.search(r"^token\s*=", secao.group(1), re.M))


def montado() -> bool:
    return os.path.ismount(PASTA)


def systemctl(*args) -> bool:
    try:
        return subprocess.run(["systemctl", "--user", *args], capture_output=True, timeout=30).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def adicionar_aos_lugares():
    """Põe "Google Drive" no painel Locais do Dolphin (só se o arquivo já existir)."""
    if not LUGARES.is_file():
        return
    href = "file://" + quote(str(PASTA))
    texto = LUGARES.read_text(encoding="utf-8")
    if href in texto or "</xbel>" not in texto:
        return
    marcador = (
        f' <bookmark href="{href}">\n'
        "  <title>Google Drive</title>\n"
        "  <info>\n"
        '   <metadata owner="http://freedesktop.org">\n'
        '    <bookmark:icon name="folder-gdrive"/>\n'
        "   </metadata>\n"
        "  </info>\n"
        " </bookmark>\n"
    )
    LUGARES.write_text(texto.replace("</xbel>", marcador + "</xbel>", 1), encoding="utf-8")


def remover_dos_lugares():
    if not LUGARES.is_file():
        return
    href = re.escape("file://" + quote(str(PASTA)))
    texto = LUGARES.read_text(encoding="utf-8")
    novo = re.sub(rf' ?<bookmark href="{href}">.*?</bookmark>\n?', "", texto, flags=re.S)
    if novo != texto:
        LUGARES.write_text(novo, encoding="utf-8")


class Janela(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Google Drive")
        self.setWindowIcon(QIcon.fromTheme("folder-gdrive"))
        self.setMinimumWidth(520)
        self.processo: QProcess | None = None

        self.titulo = QLabel("Google Drive")
        self.titulo.setObjectName("titulo")
        self.texto = QLabel()
        self.texto.setWordWrap(True)
        self.texto.setTextFormat(Qt.TextFormat.RichText)
        self.estado = QLabel()
        self.estado.setObjectName("suave")
        self.estado.setWordWrap(True)

        self.b_principal = QPushButton()
        self.b_principal.setObjectName("primario")
        self.b_principal.clicked.connect(self.acao_principal)
        self.b_secundario = QPushButton()
        self.b_secundario.clicked.connect(self.acao_secundaria)
        self.b_fechar = QPushButton("Fechar")
        self.b_fechar.clicked.connect(self.close)

        botoes = QHBoxLayout()
        botoes.addWidget(self.b_secundario)
        botoes.addStretch(1)
        botoes.addWidget(self.b_fechar)
        botoes.addWidget(self.b_principal)

        v = QVBoxLayout(self)
        v.setContentsMargins(28, 24, 28, 22)
        v.setSpacing(14)
        v.addWidget(self.titulo)
        v.addWidget(self.texto)
        v.addWidget(self.estado)
        v.addStretch(1)
        v.addLayout(botoes)
        self.atualizar()

    # ------------------------------------------------------------------ telas
    def atualizar(self):
        if self.processo is not None:
            self.texto.setText(
                "O navegador abriu a página do Google. Entre na sua conta e autorize o "
                "acesso do <b>rclone</b>, o programa que liga o iNTEGRA ao seu Drive.<br><br>"
                "Quando o navegador disser que deu certo, volte para esta janela.")
            self.estado.setText("Aguardando a autorização…")
            self.b_principal.hide()
            self.b_secundario.setText("Cancelar")
            self.b_secundario.setObjectName("")
            self.b_secundario.show()
        elif conectado():
            self.texto.setText(
                f"Sua conta está conectada. Os arquivos aparecem na pasta "
                f"<b>{PASTA}</b>.<br><br>Eles continuam no Google; o que você abre fica "
                "guardado no computador (até 2 GB) para abrir mais rápido. Documentos, "
                "planilhas e apresentações do Google aparecem como .docx, .xlsx e .pptx.")
            if montado():
                self.estado.setText("Pasta ligada ao Drive.")
            else:
                self.estado.setText("A pasta ainda não está ligada. Confira a internet; o "
                                    "iNTEGRA tenta de novo sozinho a cada 30 segundos.")
            self.b_principal.setText("Abrir pasta")
            self.b_principal.show()
            self.b_secundario.setText("Desconectar")
            self.b_secundario.setObjectName("perigo")
            self.b_secundario.show()
        else:
            self.texto.setText(
                "Veja e edite os arquivos do seu Google Drive numa pasta comum, "
                f"<b>Google Drive</b>, dentro da sua pasta pessoal.<br><br>"
                "O Google não tem programa para Linux. A ligação é feita pelo "
                "<b>rclone</b>, um programa livre que usa o acesso oficial do Google. "
                "Precisa de internet.")
            self.estado.setText("")
            self.b_principal.setText("Conectar conta Google")
            self.b_principal.show()
            self.b_secundario.hide()
        self.b_secundario.style().unpolish(self.b_secundario)
        self.b_secundario.style().polish(self.b_secundario)

    # ------------------------------------------------------------------ ações
    def acao_principal(self):
        if conectado():
            subprocess.Popen(["xdg-open", str(PASTA)])
        else:
            self.conectar()

    def acao_secundaria(self):
        if self.processo is not None:
            self.processo.kill()
            return
        self.desconectar()

    def conectar(self):
        if not shutil.which("rclone"):
            QMessageBox.warning(self, "Google Drive", "O programa rclone não está instalado.")
            return
        self.processo = QProcess(self)
        self.processo.setProgram("rclone")
        # config_is_local: abre o navegador e recebe a resposta em 127.0.0.1:53682
        # config_change_team_drive=false: não pergunta por Drive compartilhado
        self.processo.setArguments([
            "config", "create", REMOTO, "drive", "scope=drive",
            "config_is_local=true", "config_change_team_drive=false",
        ])
        self.processo.finished.connect(self.conectou)
        self.processo.start()
        self.atualizar()

    def conectou(self, codigo, _status):
        self.processo = None
        if codigo == 0 and conectado():
            PASTA.mkdir(exist_ok=True)
            systemctl("daemon-reload")
            systemctl("enable", "--now", SERVICO)
            adicionar_aos_lugares()
            # a montagem leva alguns segundos; a tela se atualiza depois
            QTimer.singleShot(4000, self.atualizar)
        elif not conectado():
            # cancelado ou recusado: não deixa remoto pela metade
            subprocess.run(["rclone", "config", "delete", REMOTO], capture_output=True)
        self.atualizar()

    def desconectar(self):
        r = QMessageBox.question(
            self, "Desconectar o Google Drive",
            "A pasta “Google Drive” deixa de mostrar os seus arquivos. Nada é apagado "
            "no Google. Desconectar?")
        if r != QMessageBox.StandardButton.Yes:
            return
        systemctl("disable", "--now", SERVICO)
        subprocess.run(["rclone", "config", "delete", REMOTO], capture_output=True)
        remover_dos_lugares()
        try:
            PASTA.rmdir()      # só apaga se estiver vazia (desmontada)
        except OSError:
            pass
        self.atualizar()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Google Drive")
    app.setDesktopFileName("integra-google-drive")
    app.setStyleSheet(ESTILO)
    j = Janela()
    j.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
