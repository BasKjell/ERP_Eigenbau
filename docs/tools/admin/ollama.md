# Ollama und AI-Assistent administrieren

## Start und Modell

```bash
ollama list
ollama pull qwen3:8b        # nur wenn nicht vorhanden
curl http://127.0.0.1:11434/api/version
```

Für das auf dem Mac laufende Ollama in `.env` `AI_MODE=ollama`,
`OLLAMA_BASE_URL=http://host.docker.internal:11434` und den exakt installierten
Modellnamen setzen. Danach `platform-api` neu starten. Für den optionalen
Compose-Ollama-Dienst lautet die interne URL `http://ollama:11434`. Ohne
erreichbares Modell bleibt der deterministische Modus die sichere Basis.

## Sicherheitsmodell

- Das Modell erhält nur minimierte Daten aus freigegebenen Werkzeugen.
- Keine direkten Datenbank-Credentials und kein unkontrollierter Shellzugriff.
- Schreibaktionen brauchen Rollenprüfung, explizite Bestätigung und Audit.
- Quellenreferenzen werden unabhängig von der Formulierung erzeugt.
- Prompt-Injection aus Dokumenten wird als nicht vertrauenswürdiger Inhalt
  behandelt.

## Betrieb und Abnahme

Modellname, Digest, Promptversion und Tool-Schema versionieren. CPU/GPU,
Speicher, Antwortzeit und Fehler beobachten. Ein Modellwechsel erfordert einen
festen Testsatz für Status, fehlende Quellen, Sperren, Berechtigungen und
Halluzinationsfälle. Fachliche Freigaben bleiben auch bei bestandenem Test
außerhalb des Modells.

Das Volume `ollama-data` kann groß sein; Modelle sind reproduzierbar ladbar,
die freigegebene Digest-Liste und Konfiguration müssen jedoch gesichert sein.
