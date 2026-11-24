# V08 Datenbank

Vorlagen-ID V08 · Vorlagenversion 1.1 · Stand 24.11.2026 · Entwurf zur internen Abstimmung

!!! note "Standardkopf"
    Jede ausgefüllte Systemdokumentation beginnt mit dem Standardkopf aus dem [Wegweiser](00-wegweiser.md#standardkopf-jeder-systemdokumentation).

## Zweck und Geltung

| Merkmal | Festlegung |
| --- | --- |
| Gilt für | Teil A für jeden Datenbankserver und jeden Datenbankcluster (Systemtyp E) sowie für eine Datenbank, die nur zu einem System gehört. Teil B für jede Datenbank, die eine Anwendung nutzt. |
| Ausfüllen | Datenbankbetreuung bzw. IT-Betrieb |
| Prüfen | Zweite Person aus dem Betrieb; ISB bei hohem Schutzbedarf |
| Zeitpunkt | Bei Einrichtung; Aktualisierung bei neuer Datenbank, neuen Konten, Knotenwechsel oder Versionswechsel |
| Normbezug | Orientierung: APP.4.3, CON.1, CON.3; ISO/IEC 27001:2022 Anhang A 8.3, 8.5, 8.13, 8.14, 8.24 |

## Datenbankcluster: einmal dokumentieren, Datenbanken verweisen

Bei einem Datenbankcluster ist vieles für alle Datenbanken gleich: Produkt und Version, Knoten, Failover, Replikation, Administrations- und Sicherungskonten, Verschlüsselung, Protokollierung, Sicherung und Wartung. Das steht deshalb **einmal** in der Dokumentation des Clusters. Der Cluster ist ein eigenes System vom Typ E mit eigener System-ID und eigener vollständiger Systemdokumentation (V01 bis V04 und V08 bis V13 sowie V02 je Knoten bzw. V05 oder V06, wenn er auf einer Plattform läuft).

Jede Anwendung, die eine Datenbank auf dem Cluster nutzt, füllt in ihrer eigenen Systemdokumentation **nur Teil B** aus und verweist auf die Dokument-ID des Clusters. Teil B enthält nur, was für diese eine Datenbank gilt.

| Inhalt | Dokumentation des Clusters (Teil A) | Dokumentation der Anwendung (Teil B) |
| --- | --- | --- |
| Produkt, Version, Support | ● | Verweis |
| Knoten, Rollen, Failover, Quorum, Verbindungspunkt | ● | Verweis; nur der Verbindungsname, den die Anwendung nutzt |
| Replikation und Hochverfügbarkeit | ● | Verweis |
| Administrations-, Replikations-, Sicherungs- und Überwachungskonten | ● | – |
| Grundregeln für Zugriffe und Verschlüsselung | ● | nur die eigenen Zugriffsquellen |
| Sicherheitseinstellungen und Protokollierung | ● | nur Abweichungen |
| Sicherung des Clusters und Wiederherstellung auf einen Zeitpunkt | ● | eigene Anforderungen (RPO, RTO) und Wiederherstellung einer einzelnen Datenbank |
| Wartung, Updates, Umschalttests | ● | Wartungsfenster, die die Anwendung betreffen |
| Kapazität des Clusters | ● | eigene Größe und Wachstum |
| Datenbanken, Eigentümer, Anwendungskonten, Schutzbedarf | Übersicht aller Datenbanken | ● je eigene Datenbank |

Bei einem einzelnen Datenbankserver oder einer Datenbank, die nur zu einem System gehört (zum Beispiel ein Datenbank-Container im Compose-Projekt), stehen Teil A und Teil B in derselben Systemdokumentation.

[HINWEIS: Der höchste Schutzbedarf aller Datenbanken auf einem Cluster bestimmt den Schutzbedarf des Clusters (Maximumprinzip, V01). Eine neue Datenbank mit höherem Schutzbedarf ist deshalb eine wesentliche Änderung des Clusters.]

## Teil A: Datenbanksystem bzw. Cluster

### Schritt A1: Datenbanksystem

| Feld | Eintrag |
| --- | --- |
| Produkt und Version | {{Auswahl: PostgreSQL; MariaDB; anderes}} {{Version}} |
| Betriebsart | {{Auswahl: einzelner Server; Cluster; Container; Kubernetes-Operator; Dienst der Plattform}} |
| Support der Version bis | {{Datum}} |
| Ablage der Konfiguration | {{Git-Pfad}} |

### Schritt A2: Aufbau des Clusters

[HINWEIS: Entfällt bei einem einzelnen Server mit Begründung.]

| Knoten | System-ID bzw. Host | Standort bzw. Brandabschnitt | Rolle | Replikation |
| --- | --- | --- | --- | --- |
| {{Knoten}} | {{Host}} | {{Standort}} | {{Auswahl: Primär; Replikat; Zeuge (Witness)}} | {{Auswahl: synchron; asynchron; –}} |

| Feld | Eintrag |
| --- | --- |
| Cluster-Verfahren | {{zum Beispiel Patroni mit etcd, Galera, Operator CloudNativePG}} |
| Verbindungspunkt für Anwendungen | {{virtuelle Adresse, DNS-Name, Proxy wie HAProxy bzw. PgBouncer; Port in V03}} |
| Umschalten bei Ausfall (Failover) | {{automatisch/manuell, erwartete Dauer, wer entscheidet}} |
| Geplantes Umschalten (Switchover) | {{Verfahren, zuletzt geübt am}} |
| Schutz vor zwei Primärknoten (Split-Brain) | {{Quorum, Zeuge, Fencing}} |
| Lesezugriffe auf Replikate | {{erlaubt für welche Konten bzw. Zwecke}} |

### Schritt A3: Konten des Datenbanksystems

| Konto bzw. Rolle | Art | Rechte | Anmeldeverfahren | Ablage des Geheimnisses | Rotation |
| --- | --- | --- | --- | --- | --- |
| {{Name}} | {{Auswahl: Person; Replikation; Sicherung; Überwachung; Cluster-Verwaltung}} | {{Rechte}} | {{zum Beispiel SCRAM-SHA-256, Zertifikat}} | {{Pfad im Secret-Manager}} | {{Intervall}} |

[HINWEIS: Superuser-Rechte nur für persönliche Administrationskonten oder lokal auf dem Knoten bzw. im Container. Anwendungskonten stehen in Teil B.]

### Schritt A4: Grundregeln für Zugriffe

| Von (Quelle) | Datenbanken | Konten | Verfahren | Verschlüsselung |
| --- | --- | --- | --- | --- |
| {{Adresse, Netz oder Container}} | {{alle bzw. Muster}} | {{Konten}} | {{Verfahren}} | {{Auswahl: TLS Pflicht; TLS optional; keine}} |

[HINWEIS: Bei PostgreSQL entspricht diese Tabelle der Datei pg_hba.conf; bei MariaDB den Host-Angaben der Konten. Die Regeln für einzelne Anwendungen stehen in Teil B. Der Datenbank-Port ist in V03 eingetragen.]

### Schritt A5: Sicherheitseinstellungen

[HINWEIS: Beschreiben, wie das im System umgesetzt ist; Abweichungen mit Begründung. Typische Punkte: Verbindungen sind verschlüsselt, auch die Replikation zwischen den Knoten; Passwörter werden mit einem sicheren Verfahren gespeichert (bei PostgreSQL scram-sha-256); Datenträger bzw. Datenbankdateien sind verschlüsselt (siehe V02); Standarddatenbanken, Testdatenbanken und anonyme Konten sind entfernt; Anmeldungen, fehlgeschlagene Anmeldungen, Rechteänderungen und Strukturänderungen werden protokolliert (siehe V09); der Datenbank-Port ist nur für die Quellen aus A4 und Teil B erreichbar.]

{{Beschreibung}}

### Schritt A6: Sicherung und Wiederherstellung

| Feld | Eintrag |
| --- | --- |
| Verfahren | {{Auswahl: logische Sicherung (Dump); physische Sicherung; kontinuierliche Archivierung für Wiederherstellung auf einen Zeitpunkt}} |
| Gesichert von Knoten | {{Primär oder Replikat}} |
| Häufigkeit und Aufbewahrung | {{siehe V10}} |
| Wiederherstellung auf einen Zeitpunkt möglich | {{ja/nein, bis wie weit zurück}} |
| Wiederherstellung einer einzelnen Datenbank | {{Verfahren, zum Beispiel aus logischer Sicherung oder über eine Hilfsinstanz}} |

### Schritt A7: Wartung und Kapazität

| Tätigkeit | Häufigkeit | Automatisiert | Verantwortlich |
| --- | --- | --- | --- |
| {{zum Beispiel Kleinversion knotenweise aktualisieren, Hauptversion migrieren, Switchover üben, Statistiken und Bereinigung prüfen}} | {{Häufigkeit}} | {{ja/nein}} | {{Name}} |

| Feld | Eintrag |
| --- | --- |
| Speicher belegt und frei | {{GB}} |
| Verbindungen genutzt und erlaubt | {{Anzahl}} |
| Übersicht der Datenbanken auf dem Cluster | {{Liste oder Verweis auf Abfrage; je Datenbank die System-ID der nutzenden Anwendung}} |

## Teil B: Datenbanken

[HINWEIS: Liegt die Datenbank auf einem Cluster, hier zuerst die Dokument-ID des Clusters eintragen und nur ausfüllen, was für diese Datenbank gilt.]

| Feld | Eintrag |
| --- | --- |
| Datenbanksystem bzw. Cluster | {{Dokument-ID des Clusters oder „Teil A dieses Dokuments“}} |
| Verbindungsname der Anwendung | {{DNS-Name bzw. Adresse und Port}} |

### Schritt B1: Datenbanken

| Datenbank bzw. Schema | Zweck | Anwendung | Eigentümer-Rolle | Größe und Wachstum | Personenbezogen | Schutzbedarf |
| --- | --- | --- | --- | --- | --- | --- |
| {{Name}} | {{Zweck}} | {{System-ID}} | {{Rolle}} | {{GB, GB je Jahr}} | {{ja/nein}} | {{Stufe}} |

### Schritt B2: Konten der Anwendung

| Konto bzw. Rolle | Art | Rechte | Anmeldeverfahren | Ablage des Geheimnisses | Rotation |
| --- | --- | --- | --- | --- | --- |
| {{Name}} | {{Auswahl: Anwendung; Auswertung; Migration}} | {{Auswahl: Eigentümer; Lesen und Schreiben; nur Lesen}} | {{Verfahren}} | {{Pfad im Secret-Manager}} | {{Intervall}} |

[HINWEIS: Die Anwendung arbeitet nie als Superuser. Lesende Zugriffe für Auswertungen über eigene Rollen und möglichst über ein Replikat bzw. eine Berichtsdatenbank.]

### Schritt B3: Zugriffe auf diese Datenbank

| Von (Quelle) | Konto | Verfahren | Verschlüsselung |
| --- | --- | --- | --- |
| {{Adresse, Netz oder Container der Anwendung}} | {{Konto}} | {{Verfahren}} | {{Auswahl: TLS Pflicht; TLS optional; keine}} |

### Schritt B4: Abweichungen vom Standard des Clusters

| Abweichung | Begründung | Entschieden von |
| --- | --- | --- |
| {{zum Beispiel eigene Erweiterung, abweichende Parameter, eigene Protokollierung}} | {{Begründung}} | {{Name, Datum}} |

### Schritt B5: Sicherung und Wiederherstellung dieser Datenbank

| Feld | Eintrag |
| --- | --- |
| Anforderung der Anwendung (RPO, RTO) | {{aus V01 bzw. V10}} |
| Abgedeckt durch die Sicherung des Clusters | {{ja/nein; wenn nein: zusätzliches Verfahren}} |
| Wiederherstellung dieser Datenbank zuletzt geübt am | {{Datum, Verweis auf Protokoll}} |

## Ist-Stand erheben

| Zweck | PostgreSQL | MariaDB |
| --- | --- | --- |
| Version | `SELECT version();` | `SELECT VERSION();` |
| Rolle des Knotens | `SELECT pg_is_in_recovery();`, bei Patroni `patronictl list` | `SHOW STATUS LIKE 'wsrep_%';` bzw. `SHOW REPLICA STATUS;` |
| Replikation | `SELECT * FROM pg_stat_replication;` | `SHOW REPLICA STATUS;` |
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
| Ab wann Datenbanken auf einem gemeinsamen Cluster statt einzeln betrieben werden (zum Beispiel ab Schutzbedarf Verfügbarkeit hoch) | offen | IT-Leitung |
| Ob Datenbanken mit sehr hohem Schutzbedarf auf einem gemeinsamen Cluster liegen dürfen | offen | ISB |
| Pflicht zu verschlüsselten Verbindungen | offen | ISB |
| Mindestumfang der Datenbankprotokollierung | offen | ISB |
| Vorgabe für Wiederherstellung auf einen Zeitpunkt je Schutzbedarf | offen | IT-Betrieb |

## Ausfüllbeispiel

??? example "Ausfüllbeispiel (fiktiv)"

    **Variante 1: Datenbank gehört nur zu einem System (SYS-0042 FLOWDOC).** Teil A und Teil B stehen im selben Dokument.

    | Feld | Eintrag |
    | --- | --- |
    | Produkt und Version | PostgreSQL 17.6 |
    | Betriebsart | Container db im Compose-Projekt flowdoc |
    | Aufbau des Clusters | entfällt, einzelne Instanz; Verfügbarkeit normal, Wiederanlauf über Sicherung |
    | Support bis | PostgreSQL 17 laut Projekt bis November 2029 |
    | Konfiguration | apps/flowdoc/postgres/postgresql.conf und pg_hba.conf |

    | Konto | Art | Rechte | Anmeldeverfahren | Ablage | Rotation |
    | --- | --- | --- | --- | --- | --- |
    | postgres | Person (Administration) | Superuser | nur lokal im Container über Unix-Socket | – | – |
    | backup | Sicherung | Rolle pg_read_all_data | SCRAM-SHA-256, nur lokal | apps/flowdoc/db-backup | 12 Monate |
    | monitoring | Überwachung | Rolle pg_monitor | SCRAM-SHA-256 | apps/flowdoc/db-monitor | 12 Monate |
    | paperless | Anwendung (Teil B) | Eigentümer der Datenbank paperless | SCRAM-SHA-256 | apps/flowdoc/db | 12 Monate |

    | Von | Datenbank | Konto | Verfahren | Verschlüsselung |
    | --- | --- | --- | --- | --- |
    | Container webserver (Netz flowdoc_internal) | paperless | paperless | scram-sha-256 | TLS Pflicht |
    | lokal (Unix-Socket im Container) | alle | postgres, backup | peer bzw. scram-sha-256 | – |
    | alle anderen | – | – | reject | – |

    | Datenbank | Zweck | Anwendung | Eigentümer | Größe und Wachstum | Personenbezogen | Schutzbedarf |
    | --- | --- | --- | --- | --- | --- | --- |
    | paperless | Metadaten, Benutzer, Rechte | SYS-0042 | paperless | 3 GB, 1 GB je Jahr | ja | V hoch, I hoch, A normal |

    Sicherheitseinstellungen wie beschrieben gesetzt; Protokollierung mit log_connections, log_disconnections und log_statement=ddl. Sicherung: tägliche logische Sicherung um 01:00 mit pg_dump, zusätzlich WAL-Archivierung für die Wiederherstellung auf einen Zeitpunkt bis 7 Tage zurück; Einzelheiten in V10. Wartung: Kleinversion monatlich über Renovate und V11; Hauptversion nach Plan mit Test auf dms-test01.

    **Variante 2: Datenbankcluster (DBC-0001) und eine Anwendung darauf (SYS-0031 FLOWERP).**

    Dokument DBC-0001-V08, Teil A (einmal für den Cluster):

    | Knoten | Host | Standort | Rolle | Replikation |
    | --- | --- | --- | --- | --- |
    | pg01 | pg01.flowcorp.example | RZ Berlin, Brandabschnitt 1 | Primär | – |
    | pg02 | pg02.flowcorp.example | RZ Berlin, Brandabschnitt 2 | Replikat | synchron |
    | pg03 | pg03.flowcorp.example | RZ Hamburg | Replikat | asynchron |

    | Feld | Eintrag |
    | --- | --- |
    | Produkt und Version | PostgreSQL 17.6 auf Debian 13, Knoten nach V02 (DBC-0001-V02) |
    | Cluster-Verfahren | Patroni 4 mit etcd auf drei Knoten |
    | Verbindungspunkt für Anwendungen | pg.flowcorp.example:5432 über HAProxy, leitet immer zum Primärknoten; Lesezugriffe über pg-ro.flowcorp.example:5433 |
    | Failover | automatisch durch Patroni, etwa 30 Sekunden; Umschalten nach Hamburg nur manuell durch die Datenbankbetreuung |
    | Switchover | patronictl switchover, zuletzt geübt am 14.10.2026 |
    | Split-Brain-Schutz | Quorum über etcd (3 Knoten), Primär nur mit gültigem Leader-Lock |
    | Konten des Clusters | postgres (lokal), replicator (Replikation, Zertifikat), backup (pgBackRest), monitoring (pg_monitor), persönliche Admin-Konten über Gruppe AD-GG-DBA |
    | Grundregeln für Zugriffe | nur aus den Server-Zonen Anwendungen und Management, TLS Pflicht, scram-sha-256; alles andere reject |
    | Sicherung | pgBackRest: tägliche Vollsicherung vom Replikat pg02, WAL-Archivierung, Wiederherstellung auf einen Zeitpunkt bis 14 Tage; einzelne Datenbank über Hilfsinstanz; Einzelheiten in DBC-0001-V10 |
    | Wartung | Kleinversion monatlich knotenweise (erst Replikate, dann Switchover, dann alter Primärknoten); Switchover-Übung quartalsweise |
    | Datenbanken auf dem Cluster | erp (SYS-0031), reporting (SYS-0050), keycloak (SYS-0005) |

    Dokument SYS-0031-V08, nur Teil B (in der Dokumentation von FLOWERP):

    | Feld | Eintrag |
    | --- | --- |
    | Datenbanksystem bzw. Cluster | DBC-0001-V08 |
    | Verbindungsname der Anwendung | pg.flowcorp.example:5432, Lesezugriffe für Berichte pg-ro.flowcorp.example:5433 |

    | Datenbank | Zweck | Anwendung | Eigentümer | Größe und Wachstum | Personenbezogen | Schutzbedarf |
    | --- | --- | --- | --- | --- | --- | --- |
    | erp | Aufträge, Bestellungen, Buchungen | SYS-0031 | erp_owner | 120 GB, 25 GB je Jahr | ja | V hoch, I hoch, A hoch |

    | Konto | Art | Rechte | Anmeldeverfahren | Ablage | Rotation |
    | --- | --- | --- | --- | --- | --- |
    | erp_app | Anwendung | Lesen und Schreiben im Schema erp | SCRAM-SHA-256 | apps/flowerp/db | 12 Monate |
    | erp_report | Auswertung | nur Lesen, nur über pg-ro | SCRAM-SHA-256 | apps/flowerp/db-report | 12 Monate |

    | Von | Konto | Verfahren | Verschlüsselung |
    | --- | --- | --- | --- |
    | erp01, erp02 (Server-Zone Anwendungen) | erp_app | scram-sha-256 | TLS Pflicht |
    | bi01 (Server-Zone Auswertung) | erp_report | scram-sha-256 | TLS Pflicht |

    Abweichungen vom Cluster-Standard: Erweiterung pg_trgm für die Volltextsuche, genehmigt von der Datenbankbetreuung am 03.09.2026.

    Sicherung: RPO 15 Minuten und RTO 4 Stunden aus V01 sind durch die Cluster-Sicherung abgedeckt; Wiederherstellung der Datenbank erp über Hilfsinstanz zuletzt geübt am 21.10.2026 (Protokoll REST-2026-019).
