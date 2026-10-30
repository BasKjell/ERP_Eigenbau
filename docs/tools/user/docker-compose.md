# Lokalen Demo-Stack bedienen

Docker Compose startet die Demo reproduzierbar. Diese Anleitung richtet sich
an Präsentatoren und Testanwender; Administration und Datenlöschung bleiben
bei der Betriebsrolle.

## Demo starten und beenden

```bash
cp .env.example .env   # nur beim ersten Start
make demo
docker compose ps
make stop
```

Danach sind Portal unter `http://localhost:8088` und Wiki unter
`http://localhost:8001` erreichbar. Für den erweiterten Fachtest startet die
Betriebsrolle `make full` mit ERPNext und Paperless.

## Vor einer Prozessdemo

1. `docker compose ps` auf laufende bzw. gesunde Kerndienste prüfen.
2. Portal und Wiki in getrennten Tabs öffnen.
3. Mit **Demo zurücksetzen** einen definierten Ausgangszustand herstellen.
4. Nach der Demo `make stop` verwenden; dieser Befehl erhält Datenvolumes.

Keine Volumes löschen und keine Containerdaten manuell verändern. Bei einem
Fehler Dienstname, Uhrzeit und sichtbare Meldung an den Administrator geben.
