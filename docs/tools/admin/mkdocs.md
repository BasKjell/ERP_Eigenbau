# MkDocs-Wiki administrieren

## Lokaler Betrieb

```bash
docker compose up -d docs
docker compose logs --tail=100 docs
docker run --rm -v "$PWD:/docs" squidfunk/mkdocs-material:9.8.0 build --strict
```

Der Dienst rendert `mkdocs.yml` und `docs/` read-only. Navigation, Theme,
Plugins und Version sind im Repository fixiert.

## Informationsarchitektur

- **Prozesse** beschreiben Zweck, Rollen, Kontrollpunkte und Nachweise.
- **Werkzeuge > Benutzer** erklären die Bedienung im Prozesskontext.
- **Werkzeuge > Administration** erklären Betrieb, Sicherheit und Restore.
- **Schnittstellen** dokumentieren Datenverantwortung und Verträge.
- **Architektur** hält Zielbild und Entscheidungen fest.

Links müssen relativ, Überschriften eindeutig und Beispiele als Demodaten
erkennbar sein. Eine Werkzeugänderung erfordert immer die Prüfung aller vier
Sichten.

## Freigabe und Veröffentlichung

Änderungen laufen wie Code über Review und CI. `make validate` muss ohne
Warnung bauen; zusätzlich Stichprobe für Navigation, Suche, Tabellen,
Mermaid-Diagramme und mobile Darstellung durchführen. Für produktive
Veröffentlichung Version, Eigentümer, Reviewdatum und Zugriffsschutz ergänzen.
