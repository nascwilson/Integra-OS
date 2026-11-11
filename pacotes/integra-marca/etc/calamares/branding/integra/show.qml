import QtQuick
import calamares.slideshow 1.0

Presentation {
    id: apresentacao

    // fundo escuro em toda a área (sem a moldura branca em volta dos slides)
    Rectangle { anchors.fill: parent; color: "#08131F"; z: -1 }

    function proximo() { apresentacao.goToNextSlide(); }

    Timer {
        interval: 9000
        running: apresentacao.activatedInCalamares
        repeat: true
        onTriggered: proximo()
    }

    Slide {
        Rectangle { anchors.fill: parent; color: "#08131F" }
        Image { id: logo1; source: "logo.png"; width: 96; height: 96; anchors.horizontalCenter: parent.horizontalCenter; anchors.top: parent.top; anchors.topMargin: 48 }
        Text { anchors.top: logo1.bottom; anchors.topMargin: 24; anchors.horizontalCenter: parent.horizontalCenter; color: "#FFFFFF"; font.pixelSize: 26; text: "Bem-vindo ao iNTEGRA OS" }
        Text { anchors.bottom: parent.bottom; anchors.bottomMargin: 48; anchors.horizontalCenter: parent.horizontalCenter; color: "#C9D6E3"; font.pixelSize: 16; text: "Leve por dentro. Bonito por fora." }
    }

    Slide {
        Rectangle { anchors.fill: parent; color: "#08131F" }
        Text { anchors.centerIn: parent; width: parent.width * 0.8; horizontalAlignment: Text.AlignHCenter; wrapMode: Text.WordWrap; color: "#E6EEF5"; font.pixelSize: 20
               text: "Programas do Windows com dois cliques.\nCada programa .exe ou .msi roda num ambiente separado." }
    }

    Slide {
        Rectangle { anchors.fill: parent; color: "#08131F" }
        Text { anchors.centerIn: parent; width: parent.width * 0.8; horizontalAlignment: Text.AlignHCenter; wrapMode: Text.WordWrap; color: "#E6EEF5"; font.pixelSize: 20
               text: "Atualizações automáticas com ponto de restauração.\nSe algo der errado, o sistema volta ao estado anterior." }
    }

    Slide {
        Rectangle { anchors.fill: parent; color: "#08131F" }
        Text { anchors.centerIn: parent; width: parent.width * 0.8; horizontalAlignment: Text.AlignHCenter; wrapMode: Text.WordWrap; color: "#E6EEF5"; font.pixelSize: 20
               text: "Drivers, discos, rede, impressoras e tarefas:\ntudo nas Configurações do sistema." }
    }

    function onActivate() { apresentacao.currentSlide = 0; }
    function onLeave() { }
}
