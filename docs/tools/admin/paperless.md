# Paperless-ngx administrieren

## Komponenten und Start

Das Profil `full` umfasst `paperless-webserver`, PostgreSQL, Redis-Broker und
einen einmaligen Seed-Import. Die Weboberfläche liegt auf
`${PAPERLESS_PORT:-8010}`.

```bash
docker compose --profile full up -d paperless-webserver paperless-seed
curl --fail http://localhost:8010/api/health/
docker compose logs --tail=200 paperless-webserver paperless-seed
```

Die fünf Repository-Beispiel-PDFs werden über das Volume
`paperless-seed-state` nur einmal in den Consume-Ordner gelegt. Falls ein alter
Stack bereits Duplikate enthält, zeigt `scripts/dedupe_paperless_demo.py`
zunächst ausschließlich eine Vorschau; `--confirm` löscht nur weitere Kopien
der fünf bekannten Demodateien und behält jeweils das älteste Dokument.

```bash
docker compose --profile full run --rm --no-deps \
  -v "$PWD/scripts/dedupe_paperless_demo.py:/dedupe.py:ro" \
  dms-mcp python /dedupe.py
# nach Prüfung denselben Aufruf mit: python /dedupe.py --confirm
```

## Konfiguration

- `PAPERLESS_SECRET_KEY` und Admin-Passwort vor geteiltem Betrieb ändern.
- OCR-Sprache ist `deu+eng`; Erkennungsqualität mit realen Dokumenten testen.
- Dokumenttypen, Tags, Korrespondenten und benutzerdefinierte Felder für
  Artikel, Revision, Auftrag, Work Order, Charge und Seriennummer definieren.
- Rollen trennen: Import, Metadatenpflege, Freigabe, Lesen und Administration.
- API-Token für Portalintegration auf notwendige Operationen begrenzen.

## Backup und Wiederherstellung

Konsistent zu sichern sind `paperless-db-data`, `paperless-data`,
`paperless-media` und bei Bedarf `paperless-export`. Der Consume-Ordner ist
eine Eingangsqueue, kein Archiv. Wiederherstellung mit Stichproben für OCR,
Originaldatei, Metadaten, Berechtigungen und stabile Dokument-ID prüfen.

## Dokumentenlenkung

Paperless bietet Ablage und Suche; ein belastbarer Freigabe-/Revisionsprozess
muss durch Rollen, Custom Fields und Workflowregeln ergänzt und validiert
werden. Löschung und Massenänderungen sind zu protokollieren. Vor Updates
Export, Datenbanksicherung, Migrationstest und API-Smoke-Test durchführen.
