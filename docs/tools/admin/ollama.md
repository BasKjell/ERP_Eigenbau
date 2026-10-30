# Ollama und AI-Assistent administrieren

## Start und Modell

```bash
docker compose --profile ai up -d ollama
docker compose exec ollama ollama pull qwen3:4b
docker compose exec ollama ollama list
```

Anschließend in `.env` `AI_MODE=ollama`, interne Basis-URL und den exakt
installierten Modellnamen setzen und `platform-api` neu starten. Ohne
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
