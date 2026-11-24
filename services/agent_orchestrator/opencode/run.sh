#!/bin/sh
# Einstieg des OpenCode-Workers: Prompt von stdin als Datei ablegen und einmalig ausführen.
# Konfiguration (nur FLOWGATE, keine Werkzeuge) kommt aus OPENCODE_CONFIG_CONTENT.
# Die Nachricht steht vor -f, weil -f beliebig viele Dateien aufnimmt.
set -eu
umask 077
cat > /work/auftrag.md
exec opencode run --pure --format json -m "flowgate/${FLOW_MODEL}" \
  "Bearbeite den Auftrag in der angehängten Datei auftrag.md. Antworte ausschließlich im dort verlangten Format, ohne Einleitung und ohne Werkzeuge." \
  -f /work/auftrag.md
