// Layout padrão do iNTEGRA OS: barra de tarefas embaixo, no estilo Windows.
var painel = new Panel;
painel.location = "bottom";
painel.height = 2 * Math.ceil(gridUnit * 2.6 / 2);
painel.floating = false;

// Botão Iniciar com o logo iNTEGRA
var iniciar = painel.addWidget("org.kde.plasma.kickoff");
iniciar.currentConfigGroup = ["General"];
iniciar.writeConfig("icon", "integra-logo");

// Programas fixados (só ícones)
var tarefas = painel.addWidget("org.kde.plasma.icontasks");
tarefas.currentConfigGroup = ["General"];
tarefas.writeConfig("launchers", [
    "applications:org.kde.dolphin.desktop",
    "applications:org.kde.falkon.desktop",
    "applications:euro-office-euro-office.desktop",
    "applications:com.rtosta.zapzap.desktop",
    "applications:org.integra.central.desktop",
    "applications:org.kde.discover.desktop",
    "applications:org.kde.konsole.desktop"
]);

painel.addWidget("org.kde.plasma.marginsseparator");
painel.addWidget("org.kde.plasma.systemtray");
painel.addWidget("org.kde.plasma.digitalclock");
painel.addWidget("org.kde.plasma.showdesktop");

// Papel de parede iNTEGRA em todas as telas
var telas = desktopsForActivity(currentActivity());
for (var i = 0; i < telas.length; i++) {
    telas[i].wallpaperPlugin = "org.kde.image";
    telas[i].currentConfigGroup = ["Wallpaper", "org.kde.image", "General"];
    telas[i].writeConfig("Image", "file:///usr/share/wallpapers/iNTEGRA/");
}
