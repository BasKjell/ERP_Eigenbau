# PostgreSQL / pgvector administrieren

## Einsatz und Dienst

`demo-db` nutzt das fixierte pgvector-Image und ein persistentes Volume
`demo-db-data`. Die Datenbank ist nur im Compose-Netz erreichbar. Paperless
betreibt zusätzlich eine eigene PostgreSQL-Instanz; ERPNext verwendet
MariaDB. Fachliche Korrekturen erfolgen niemals direkt in diesen Datenbanken.

```bash
docker compose up -d demo-db
docker compose exec demo-db pg_isready -U platform -d platform_demo
docker compose logs --tail=150 demo-db
```

## Sicherheit und Betrieb

- Default-Passwörter vor geteilter Nutzung ersetzen und Secrets extern
  verwalten.
- Keine Host-Portfreigabe ohne Netzwerk- und TLS-Konzept.
- Rollen für Migration, Anwendung, Monitoring und Backup trennen.
- Erweiterungen und Schemaänderungen als versionierte Migration ausrollen.
- Langläufer, Verbindungen, Locks, Speicher und Autovacuum überwachen.

## Backup und Restore

Backup umfasst Schema, Daten, Rollen-/Grant-Konzept und verwendete Extensions.
Ein Volume-Snapshot allein ist ohne Konsistenz- und Restore-Test kein
ausreichender Nachweis. Wiederherstellung regelmäßig in einer getrennten
Umgebung testen und Anwendungsmigration sowie Stichproben ausführen.

pgvector-Indizes sind aus Primärdaten rekonstruierbar; Einbettungsmodell,
Dimension und Chunking-Version müssen zusammen mit den Daten dokumentiert
werden.

## DMS-Vektorindex

`knowledge_chunks` enthält ausschließlich abgeleitete OCR-Blöcke aus
Paperless, die Dokumentreferenz, klickbare Metadaten, Content-Hash und den
768-dimensionalen Vektor. Der Index wird reproduzierbar aufgebaut:

```bash
make dms-vector-index
docker compose exec demo-db psql -U platform -d platform_demo \
  -c "select count(distinct source_reference), count(*) from knowledge_chunks where source_system='Paperless-ngx';"
```

Paperless bleibt führend. Löschung, Rechteänderung oder Schutzklassifizierung
müssen eine Neuindizierung auslösen. Im Livebetrieb sind Sicherheitsbereiche
getrennt zu indizieren oder bei jeder Suche serverseitig mit der Identität des
Benutzers zu filtern.
