# V05 Container: Images und Docker/Compose

Vorlagen-ID V05 · Vorlagenversion 1.1 · Stand 24.11.2026 · Entwurf zur internen Abstimmung

!!! note "Standardkopf"
    Jede ausgefüllte Systemdokumentation beginnt mit dem Standardkopf aus dem [Wegweiser](00-wegweiser.md#standardkopf-jeder-systemdokumentation).

## Zweck und Geltung

| Merkmal | Festlegung |
| --- | --- |
| Gilt für | Teil A bei jedem System mit Containern (Systemtypen C, D, F). Teil B bei Betrieb auf einem Docker-Host (Typ C und Docker-Host als Plattform Typ F). |
| Ausfüllen | IT-Betrieb bzw. Plattformteam |
| Prüfen | Zweite Person aus dem Betrieb; ISB bei Ausnahmen |
| Zeitpunkt | Bei Einrichtung; Aktualisierung bei jedem neuen Image und jeder Änderung an Compose-Dateien |
| Normbezug | SYS.1.6, APP.6, OPS.1.1.3; ISO/IEC 27001:2022 Anhang A 8.8, 8.9, 8.19, 8.22 |

## Teil A: Images

### Schritt A1: Verwendete Images

| Dienst | Image (Registry/Repository:Tag) | Digest | Basis-Image | Herkunft | Lizenz | Signatur geprüft | SBOM | Letzter Scan | Verantwortlich |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| {{Dienst}} | {{Image}} | {{sha256:…}} | {{Basis}} | {{Auswahl: Hersteller; selbst gebaut (Pfad zum Dockerfile im Git)}} | {{Lizenz}} | {{ja/nein}} | {{Ablage}} | {{Datum, offene kritische und hohe Befunde}} | {{Name}} |

### Schritt A2: Regeln für Images

[HINWEIS: Beschreiben, wie das im System umgesetzt bzw. erledigt ist; Abweichungen mit Begründung. Typische Punkte: Images kommen nur aus der freigegebenen internen Registry [FIRMENANGABE V-05]; Images werden über den Digest referenziert, nicht über veränderliche Tags wie „latest“; Container laufen nicht als root, außer mit dokumentierter Begründung; Images enthalten keine Geheimnisse, Schlüssel oder Zugangsdaten; Images werden nach Vorgabe neu gebaut bzw. aktualisiert, auch ohne eigene Codeänderung (siehe V11); Für jedes Image liegt eine SBOM vor.]

{{Beschreibung}}

### Schritt A3: Offene Befunde und Ausnahmen

| Image | Befund (CVE) | Schwere | Begründung bzw. Gegenmaßnahme | Ausnahme bis | Genehmigt von |
| --- | --- | --- | --- | --- | --- |
| {{Image}} | {{CVE}} | {{Schwere}} | {{Begründung}} | {{Datum}} | {{Name}} |

## Teil B: Docker-Host und Compose

### Schritt B1: Container-Laufzeit

| Feld | Eintrag |
| --- | --- |
| Laufzeit und Version | {{zum Beispiel Docker Engine, Version}} |
| Betriebsart | {{Auswahl: rootful; rootless}} |
| Ablage der daemon.json | {{Git-Pfad}} |
| Wichtige Einstellungen | {{zum Beispiel Log-Treiber, live-restore, no-new-privileges, icc, userns-remap}} |
| Zugriff auf den Docker-Socket | {{wer, über welchen Weg}} [HINWEIS: Zugriff auf den Socket entspricht root-Rechten; siehe V04 Schritt 6] |

### Schritt B2: Compose-Projekte

| Projekt | Compose-Datei (Git-Pfad, Commit) | Umgebungsdatei ohne Geheimnisse | Start beim Booten | Verantwortlich |
| --- | --- | --- | --- | --- |
| {{Projekt}} | {{Pfad@Commit}} | {{Pfad}} | {{Auswahl: systemd-Unit; restart-Regel}} | {{Name}} |

### Schritt B3: Sicherheitseinstellungen je Container

| Dienst | Benutzer (UID) | Nur-Lese-Dateisystem | Capabilities | privileged | no-new-privileges | Grenzen CPU/RAM/PIDs | Healthcheck | Neustart-Regel |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| {{Dienst}} | {{UID}} | {{ja/nein}} | {{zum Beispiel drop ALL, add …}} | {{muss „nein“ sein oder begründet}} | {{ja/nein}} | {{Werte}} | {{ja/nein}} | {{Regel}} |

### Schritt B4: Netze und veröffentlichte Ports

| Docker-Netz | Treiber | Intern (ohne Außenverbindung) | Verbundene Dienste |
| --- | --- | --- | --- |
| {{Netz}} | {{Treiber}} | {{ja/nein}} | {{Dienste}} |

Veröffentlichte Ports stehen in V03 Schritt 2. [HINWEIS: Docker gibt veröffentlichte Ports über eigene Paketfilterregeln frei, an Regeln von ufw oder firewalld vorbei. Ports deshalb nur an die benötigte Adresse binden, zum Beispiel 127.0.0.1 oder die Anwendungsadresse, und bei Bedarf in der Kette DOCKER-USER beschränken.]

### Schritt B5: Volumes und Daten

| Volume bzw. Bind-Mount | Pfad auf dem Host | Inhalt | Gesichert (siehe V10) | Rechte |
| --- | --- | --- | --- | --- |
| {{Volume}} | {{Pfad}} | {{Inhalt}} | {{ja/nein, Verfahren}} | {{Eigentümer, Modus}} |

### Schritt B6: Geheimnisse

| Geheimnis | Übergabe an den Container | Ablage |
| --- | --- | --- |
| {{Bezeichnung}} | {{Auswahl: Compose-Secret als Datei; Umgebungsvariable aus Datei außerhalb von Git; Agent des Secret-Managers}} | {{Pfad im Secret-Manager}} |

### Schritt B7: Aktualisierung und Rücknahme

| Feld | Eintrag |
| --- | --- |
| Wie neue Image-Versionen erkannt werden | {{zum Beispiel automatischer Merge Request durch Renovate}} |
| Test vor Produktion | {{Umgebung, Verfahren}} |
| Ausrollen | {{Befehle bzw. Pipeline}} |
| Rücknahme | {{Verfahren, zum Beispiel vorheriger Digest aus Git}} |

## Ist-Stand erheben

| Zweck | Befehl |
| --- | --- |
| Version und Einstellungen der Laufzeit | `docker version`, `docker info` |
| Wirksame Compose-Konfiguration | `docker compose config` |
| Images mit Digest | `docker image ls --digests`, `docker compose images` |
| Sicherheitseinstellungen eines Containers | `docker inspect <container>` (Felder Config.User, HostConfig.Privileged, HostConfig.CapAdd, HostConfig.CapDrop, HostConfig.ReadonlyRootfs, HostConfig.SecurityOpt) |
| Schwachstellenscan und SBOM | zum Beispiel `trivy image <image>`, `syft <image>` |

## Unternehmensweite Festlegungen

[FIRMENANGABE V-05] Plattformteam und ISB legen fest:

| Festlegung | Wert | Verantwortlich |
| --- | --- | --- |
| Freigegebene Registry und Regeln für die Übernahme externer Images | offen | Plattformteam |
| Scan-Werkzeug und Schwellen (zum Beispiel keine offenen kritischen Befunde) | offen | ISB |
| Signaturpflicht und SBOM-Format | offen | Plattformteam |
| Freigegebene Basis-Images | offen | Plattformteam |
| Intervall für Neubau bzw. Aktualisierung von Images | offen | Plattformteam |
| Rootless-Betrieb Pflicht oder empfohlen | offen | ISB |

## Ausfüllbeispiel

??? example "Ausfüllbeispiel (fiktiv)"

    | Dienst | Image | Digest | Basis | Herkunft | Lizenz | Signatur | SBOM | Letzter Scan | Verantwortlich |
    | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
    | webserver | registry.flowcorp.example/mirror/paperless-ngx:2.18.4 | sha256:3f9a… (vollständig in Anlage) | Debian slim | Projekt paperless-ngx, gespiegelt | GPL-3.0 | ja | sbom/flowdoc/webserver.json | 19.11.2026, 0 kritisch, 2 hoch | Plattformbetrieb |
    | db | registry.flowcorp.example/mirror/postgres:17.6 | sha256:91c2… | Debian slim | offizielles Image, gespiegelt | PostgreSQL | ja | sbom/flowdoc/db.json | 19.11.2026, 0 kritisch, 0 hoch | Plattformbetrieb |
    | broker | registry.flowcorp.example/mirror/valkey:8.1 | sha256:4b07… | Debian slim | offizielles Image, gespiegelt | BSD-3-Clause | ja | sbom/flowdoc/broker.json | 19.11.2026, 0 kritisch, 0 hoch | Plattformbetrieb |
    | proxy | registry.flowcorp.example/mirror/nginx-unprivileged:1.28 | sha256:c1d8… | Debian slim | offizielles Image, gespiegelt | BSD-2-Clause | ja | sbom/flowdoc/proxy.json | 19.11.2026, 0 kritisch, 1 hoch | Plattformbetrieb |

    Offener Befund (Beispiel): webserver, CVE in einer Bildbibliothek, hoch; Funktion wird nicht genutzt, Upload-Typen begrenzt; Ausnahme bis 31.12.2026, genehmigt vom ISB.

    Laufzeit: Docker Engine 28 (Community) rootful; daemon.json in Git unter infra/hosts/dms01/daemon.json mit log-driver journald, live-restore true, no-new-privileges true, icc false. Socket nur für root; Zugriff über sudo-Regeln aus V04.

    Compose-Projekt: flowdoc, Datei apps/flowdoc/compose.yaml@a41c9e2, Umgebungsdatei /etc/flowdoc/flowdoc.env (ohne Geheimnisse), Start über systemd-Unit flowdoc.service.

    | Dienst | Benutzer | Nur-Lese | Capabilities | privileged | no-new-privileges | Grenzen | Healthcheck | Neustart |
    | --- | --- | --- | --- | --- | --- | --- | --- | --- |
    | webserver | Start als root, danach Wechsel auf 1000 (USERMAP_UID) | nein (schreibt Anwendungsdaten) | drop ALL, add CHOWN, SETUID, SETGID; begründet durch den Benutzerwechsel beim Start | nein | ja | 2 CPU, 4 GB, 512 PIDs | ja | unless-stopped |
    | db | Start als root, danach Wechsel auf 999 | nein | drop ALL, add CHOWN, SETUID, SETGID, DAC_OVERRIDE, FOWNER; begründet durch den Benutzerwechsel beim Start | nein | ja | 2 CPU, 4 GB | ja | unless-stopped |
    | broker | 999 (in Compose gesetzt) | ja | drop ALL | nein | ja | 0,5 CPU, 512 MB | ja | unless-stopped |
    | proxy | 101 | ja (tmpfs für Cache) | drop ALL | nein | ja | 1 CPU, 256 MB | ja | unless-stopped |

    Netze: flowdoc_internal (bridge, intern: ja) mit webserver, db, broker; flowdoc_edge (bridge, intern: nein) mit proxy und webserver. Veröffentlicht nur proxy: 10.20.120.15:80 auf Container-Port 8080 und 10.20.120.15:443 auf 8443.

    | Volume | Pfad | Inhalt | Gesichert | Rechte |
    | --- | --- | --- | --- | --- |
    | flowdoc_data | /srv/flowdoc/data | Suchindex, Anwendungsdaten | ja, restic täglich | 1000:1000, 0750 |
    | flowdoc_media | /srv/flowdoc/media | Originale und archivierte PDFs | ja, restic täglich | 1000:1000, 0750 |
    | flowdoc_pgdata | /srv/flowdoc/pgdata | Datenbankdateien | über Datenbanksicherung (V08, V10) | 999:999, 0700 |
    | flowdoc_certs | /srv/flowdoc/certs | TLS-Zertifikat und Schlüssel | nein, wird neu ausgestellt | 101:101, 0700 |

    Geheimnisse: Datenbankpasswort, Valkey-Passwort, OIDC-Client-Secret und IMAP-Passwort als Compose-Secrets aus /run/flowdoc-secrets, befüllt beim Start durch den Agenten des Secret-Managers.

    Aktualisierung: Renovate erstellt Merge Requests; Test auf dms-test01; Ausrollen im Wartungsfenster mit `docker compose pull` und `docker compose up -d`; Rücknahme über den vorherigen Commit der Compose-Datei.
