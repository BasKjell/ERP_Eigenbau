# V08 Datenbank

Vorlagen-ID V08 · Vorlagenversion 1.1 · Stand 24.11.2026 · Entwurf zur internen Abstimmung

!!! note "Standardkopf"
    Jede ausgefüllte Systemdokumentation beginnt mit dem Standardkopf aus dem [Wegweiser](00-wegweiser.md#standardkopf-jeder-systemdokumentation).

## Zweck und Geltung

| Merkmal | Festlegung |
| --- | --- |
| Gilt für | Datenbankserver (Systemtyp E) und jedes System, zu dem eine eigene Datenbank gehört |
| Ausfüllen | Datenbankbetreuung bzw. IT-Betrieb |
| Prüfen | Zweite Person aus dem Betrieb; ISB bei hohem Schutzbedarf |
| Zeitpunkt | Bei Einrichtung; Aktualisierung bei neuer Datenbank, neuen Konten oder Versionswechsel |
| Normbezug | APP.4.3, CON.1, CON.3; ISO/IEC 27001:2022 Anhang A 8.3, 8.5, 8.13, 8.24 |

## Schritt 1: Datenbanksystem

| Feld | Eintrag |
| --- | --- |
| Produkt und Version | {{Auswahl: PostgreSQL; MariaDB; anderes}} {{Version}} |
| Betriebsart | {{Auswahl: eigener Server; Container; Kubernetes-Operator; Dienst der Plattform}} |
| Hochverfügbarkeit bzw. Replikation | {{keine / Verfahren}} |
| Support der Version bis | {{Datum}} |
| Ablage der Konfiguration | {{Git-Pfad}} |

## Schritt 2: Datenbanken

| Datenbank bzw. Schema | Zweck | Anwendung | Eigentümer-Rolle | Größe | Personenbezogen | Schutzbedarf |
| --- | --- | --- | --- | --- | --- | --- |
| {{Name}} | {{Zweck}} | {{System-ID}} | {{Rolle}} | {{GB}} | {{ja/nein}} | {{Stufe}} |

## Schritt 3: Datenbankkonten und Rollen

| Konto bzw. Rolle | Art | Rechte | Anmeldeverfahren | Ablage des Geheimnisses | Rotation |
| --- | --- | --- | --- | --- | --- |
| {{Name}} | {{Auswahl: Person; Anwendung; Replikation; Sicherung; Überwachung; Auswertung}} | {{Auswahl: Eigentümer; Lesen und Schreiben; nur Lesen; Superuser}} | {{zum Beispiel SCRAM-SHA-256, Zertifikat}} | {{Pfad im Secret-Manager}} | {{Intervall}} |

[HINWEIS: Die Anwendung arbeitet nie als Superuser. Superuser-Rechte nur für persönliche Administrationskonten oder lokal im Container. Lesende Zugriffe für Auswertungen über eigene Rollen und möglichst über eine Kopie bzw. Berichtsdatenbank.]

## Schritt 4: Zugriffssteuerung

| Von (Quelle) | Datenbank | Konto | Verfahren | Verschlüsselung |
| --- | --- | --- | --- | --- |
| {{Adresse, Netz oder Container}} | {{Datenbank}} | {{Konto}} | {{Verfahren}} | {{Auswahl: TLS Pflicht; TLS optional; keine}} |

[HINWEIS: Bei PostgreSQL entspricht diese Tabelle der Datei pg_hba.conf; bei MariaDB den Host-Angaben der Konten. Der Datenbank-Port ist in V03 eingetragen.]

## Schritt 5: Sicherheitseinstellungen

[HINWEIS: Beschreiben, wie das im System umgesetzt bzw. erledigt ist; Abweichungen mit Begründung. Typische Punkte: Verbindungen sind verschlüsselt; unverschlüsselte Verbindungen nur innerhalb eines abgeschotteten Netzes mit Begründung; Passwörter werden mit einem sicheren Verfahren gespeichert (bei PostgreSQL scram-sha-256); Datenträger bzw. Datenbankdateien sind verschlüsselt (siehe V02); Standarddatenbanken, Testdatenbanken und anonyme Konten sind entfernt; Anmeldungen, fehlgeschlagene Anmeldungen, Rechteänderungen und Strukturänderungen werden protokolliert (siehe V09); Der Datenbank-Port ist nur für die Quellen aus Schritt 4 erreichbar.]

{{Beschreibung}}

## Schritt 6: Sicherung und Wiederherstellung

| Feld | Eintrag |
| --- | --- |
| Verfahren | {{Auswahl: logische Sicherung (Dump); physische Sicherung; kontinuierliche Archivierung für Wiederherstellung auf einen Zeitpunkt}} |
| Häufigkeit und Aufbewahrung | {{siehe V10}} |
| Wiederherstellung auf einen Zeitpunkt möglich | {{ja/nein, bis wie weit zurück}} |

## Schritt 7: Wartung

| Tätigkeit | Häufigkeit | Automatisiert | Verantwortlich |
| --- | --- | --- | --- |
| {{zum Beispiel Kleinversion aktualisieren, Hauptversion migrieren, Statistiken und Bereinigung prüfen}} | {{Häufigkeit}} | {{ja/nein}} | {{Name}} |

## Ist-Stand erheben

| Zweck | PostgreSQL | MariaDB |
| --- | --- | --- |
| Version | `SELECT version();` | `SELECT VERSION();` |
| Datenbanken | `\l` in psql | `SHOW DATABASES;` |
| Konten und Rollen | `\du` in psql | `SELECT user, host FROM mysql.user;` |
| Rechte eines Kontos | `\dp` bzw. `\z` in psql | `SHOW GRANTS FOR '<konto>'@'<host>';` |
| Zugriffsregeln | `SELECT * FROM pg_hba_file_rules;` | Host-Angaben der Konten |
| Verschlüsselung und Passwortverfahren | `SHOW ssl;`, `SHOW password_encryption;` | `SHOW VARIABLES LIKE 'require_secure_transport';` |

## Unternehmensweite Festlegungen

[FIRMENANGABE V-08] Datenbankbetreuung und ISB legen fest:

| Festlegung | Wert | Verantwortlich |
| --- | --- | --- |
| Zugelassene Datenbanksysteme (zum Beispiel PostgreSQL als Standard) | offen | Architektur-Runde |
| Pflicht zu verschlüsselten Verbindungen | offen | ISB |
| Mindestumfang der Datenbankprotokollierung | offen | ISB |
| Vorgabe für Wiederherstellung auf einen Zeitpunkt je Schutzbedarf | offen | IT-Betrieb |

## Ausfüllbeispiel

??? example "Ausfüllbeispiel (fiktiv)"

    | Feld | Eintrag |
    | --- | --- |
    | Produkt und Version | PostgreSQL 17.6 |
    | Betriebsart | Container db im Compose-Projekt flowdoc |
    | Hochverfügbarkeit | keine; Verfügbarkeit normal, Wiederanlauf über Sicherung |
    | Support bis | PostgreSQL 17 laut Projekt bis November 2029 |
    | Konfiguration | apps/flowdoc/postgres/postgresql.conf und pg_hba.conf |

    | Datenbank | Zweck | Anwendung | Eigentümer | Größe | Personenbezogen | Schutzbedarf |
    | --- | --- | --- | --- | --- | --- | --- |
    | paperless | Metadaten, Benutzer, Rechte | SYS-0042 | paperless | 3 GB | ja | V hoch, I hoch, A normal |

    | Konto | Art | Rechte | Anmeldeverfahren | Ablage | Rotation |
    | --- | --- | --- | --- | --- | --- |
    | postgres | Superuser | Superuser | nur lokal im Container über Unix-Socket | – | – |
    | paperless | Anwendung | Eigentümer der Datenbank paperless | SCRAM-SHA-256 | apps/flowdoc/db | 12 Monate |
    | backup | Sicherung | Rolle pg_read_all_data | SCRAM-SHA-256, nur lokal | apps/flowdoc/db-backup | 12 Monate |
    | monitoring | Überwachung | Rolle pg_monitor | SCRAM-SHA-256 | apps/flowdoc/db-monitor | 12 Monate |

    | Von | Datenbank | Konto | Verfahren | Verschlüsselung |
    | --- | --- | --- | --- | --- |
    | Container webserver (Netz flowdoc_internal) | paperless | paperless | scram-sha-256 | TLS Pflicht |
    | lokal (Unix-Socket im Container) | alle | postgres, backup | peer bzw. scram-sha-256 | – |
    | alle anderen | – | – | reject | – |

    Sicherheitseinstellungen wie beschrieben gesetzt; Protokollierung mit log_connections, log_disconnections und log_statement=ddl.

    Sicherung: tägliche logische Sicherung um 01:00 mit pg_dump, zusätzlich WAL-Archivierung für die Wiederherstellung auf einen Zeitpunkt bis 7 Tage zurück; Einzelheiten in V10.

    Wartung: Kleinversion monatlich über Renovate und V11; Hauptversion nach Plan mit Test auf dms-test01.
