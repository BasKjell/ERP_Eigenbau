# V10 Datensicherung und Wiederherstellung

Vorlagen-ID V10 · Vorlagenversion 1.1 · Stand 24.11.2026 · Entwurf zur internen Abstimmung

!!! note "Standardkopf"
    Jede ausgefüllte Systemdokumentation beginnt mit dem Standardkopf aus dem [Wegweiser](00-wegweiser.md#standardkopf-jeder-systemdokumentation).

## Zweck und Geltung

| Merkmal | Festlegung |
| --- | --- |
| Gilt für | Alle Systemtypen |
| Ausfüllen | IT-Betrieb mit dem Team, das die Sicherungsinfrastruktur betreibt |
| Prüfen | Systemverantwortliche Person (RPO und RTO), ISB |
| Zeitpunkt | Vor Inbetriebnahme, mit bestandenem Wiederherstellungstest; danach nach Testintervall |
| Normbezug | CON.3, DER.4; ISO/IEC 27001:2022 Anhang A 5.29, 5.30, 8.13, 8.14 |

[HINWEIS: Datensicherung dient der Wiederherstellung. Aufbewahrungspflichtige Unterlagen gehören zusätzlich in ein Archiv (OPS.1.2.2); eine Sicherung ersetzt kein Archiv.]

## Schritt 1: Anforderungen

| Feld | Eintrag |
| --- | --- |
| Sicherungsklasse | {{Klasse nach [FIRMENANGABE V-10]}} |
| RPO (maximal tolerierter Datenverlust) | {{Stunden}} (aus V01 Schritt 5) |
| RTO (maximale Wiederanlaufzeit) | {{Stunden}} (aus V01 Schritt 5) |
| Aufbewahrung der Sicherungen | {{zum Beispiel täglich 30 Tage, monatlich 12 Monate}} |

## Schritt 2: Sicherungsobjekte

| Objekt | Methode | Werkzeug | Häufigkeit und Zeit | Aufbewahrung | Ziel | Verschlüsselt | Unveränderliche Kopie | Außer Haus |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| {{Objekt}} | {{Auswahl: Datei; Snapshot; Datenbank-Dump; kontinuierliche Archivierung; Image der VM}} | {{Werkzeug}} | {{Zeitplan}} | {{Dauer}} | {{Ziel}} | {{ja/nein}} | {{ja/nein, Dauer der Sperre}} | {{ja/nein}} |

Nicht gesicherte Teile und Begründung: {{zum Beispiel Container-Images und Konfiguration, die aus Registry und Git wiederhergestellt werden}}

## Schritt 3: Regel 3-2-1-1-0

[HINWEIS: Beschreiben, wie das im System umgesetzt bzw. erledigt ist; Abweichungen mit Begründung. Typische Punkte: Mindestens drei Kopien der Daten (Original und zwei Sicherungen); Auf mindestens zwei unterschiedlichen Speichersystemen bzw. Medien; Mindestens eine Kopie an einem anderen Standort; Mindestens eine Kopie unveränderlich oder offline; Null Fehler bei der Prüfung der Sicherungen und beim letzten Wiederherstellungstest.]

{{Beschreibung}}

## Schritt 4: Schlüssel und Berechtigungen

| Feld | Eintrag |
| --- | --- |
| Ablage des Schlüssels für die Sicherungsverschlüsselung | {{Verweis auf Secret-Manager bzw. Tresor; Kopie außerhalb des gesicherten Systems}} |
| Wer darf Sicherungen löschen | {{Rollen; getrennt von der Systemadministration}} |
| Wer darf wiederherstellen | {{Rollen}} |

## Schritt 5: Wiederherstellungsverfahren

| Schritt | Tätigkeit | Befehl bzw. Verweis | Dauer |
| --- | --- | --- | --- |
| {{Nr.}} | {{Tätigkeit}} | {{Befehl oder Verweis auf Runbook}} | {{Minuten}} |

## Schritt 6: Wiederherstellungstests

| Datum | Umfang | Ziel der Wiederherstellung | Dauer | Ergebnis | Abweichungen | Durchgeführt von |
| --- | --- | --- | --- | --- | --- | --- |
| {{Datum}} | {{Auswahl: einzelne Dateien; Datenbank; vollständiges System}} | {{getrennte Umgebung}} | {{Minuten}} | {{bestanden / nicht bestanden}} | {{Abweichungen}} | {{Name}} |

[HINWEIS: Der erste vollständige Test ist Voraussetzung für die Freigabe in V13. Getestet wird in einer getrennten Umgebung, nicht durch Überschreiben des Produktivsystems.]

## Schritt 7: Überwachung der Sicherung

| Feld | Eintrag |
| --- | --- |
| Erfolgsmeldung bzw. Alarm bei Fehler | {{siehe V09 Schritt 5}} |
| Regelmäßige Prüfung der Sicherungsdaten | {{zum Beispiel Prüfsummenlauf, Häufigkeit}} |

## Ist-Stand erheben

Sicherungsjobs und letzte Läufe aus dem Sicherungswerkzeug exportieren (zum Beispiel `restic snapshots` und `restic check` oder Berichte der Sicherungssoftware) und mit Datum als Anlage ablegen.

## Unternehmensweite Festlegungen

[FIRMENANGABE V-10] IT-Betrieb und ISB legen fest:

| Festlegung | Wert | Verantwortlich |
| --- | --- | --- |
| Sicherungsklassen mit RPO, RTO und Aufbewahrung | offen | IT-Betrieb |
| Zugelassene Sicherungswerkzeuge und -ziele | offen | IT-Betrieb |
| Ab welchem Schutzbedarf eine unveränderliche Kopie Pflicht ist | offen | ISB |
| Intervall der Wiederherstellungstests je Klasse | offen | ISB |
| Trennung der Rechte zwischen Systemadministration und Sicherung | offen | ISB |

## Ausfüllbeispiel

??? example "Ausfüllbeispiel (fiktiv)"

    | Feld | Eintrag |
    | --- | --- |
    | Sicherungsklasse | B |
    | RPO | 24 Stunden für Dokumente; 15 Minuten für die Datenbank durch WAL-Archivierung |
    | RTO | 8 Stunden |
    | Aufbewahrung | täglich 30 Tage, monatlich 12 Monate |

    | Objekt | Methode | Werkzeug | Zeitplan | Aufbewahrung | Ziel | Verschlüsselt | Unveränderlich | Außer Haus |
    | --- | --- | --- | --- | --- | --- | --- | --- | --- |
    | Datenbank paperless | Dump | pg_dump im Container, Ablage auf /srv/flowdoc/backup | täglich 01:00 | 30 Tage / 12 Monate | backup-s3 (Standort A) | ja (restic) | ja, Objektsperre 30 Tage | über Kopie |
    | Datenbank paperless | kontinuierliche Archivierung | WAL-Archiv | laufend | 7 Tage | backup-s3 | ja | ja | über Kopie |
    | Volumes flowdoc_media, flowdoc_data, /etc/flowdoc | Datei | restic | täglich 01:30 | 30 Tage / 12 Monate | backup-s3 | ja | ja, 30 Tage | über Kopie |
    | Kopie aller Sicherungen | Replikation | Replikation des Objektspeichers | täglich 04:00 | wie Quelle | backup-s3-b (Standort B) | ja | ja | ja |
    | VM dms01 | Snapshot der Plattform | Virtualisierungsplattform | vor jedem Change | 7 Tage | Plattformspeicher | – | nein | nein |

    Nicht gesichert: Container-Images (Registry) und Compose-Dateien (Git); flowdoc_certs, weil das Zertifikat neu ausgestellt wird.

    3-2-1-1-0: alle Punkte erfüllt.

    Schlüssel: restic-Schlüssel im Secret-Manager unter infra/backup/dms01, Kopie im Notfalltresor. Löschen von Sicherungen nur durch das Team Datensicherung; Wiederherstellen durch Plattformbetrieb.

    | Schritt | Tätigkeit | Befehl bzw. Verweis | Dauer |
    | --- | --- | --- | --- |
    | 1 | VM aus Template neu bereitstellen und nach V02 einrichten | Runbook RB-PLT-001 | 30 Min. |
    | 2 | Compose-Projekt aus Git auschecken, Geheimnisse bereitstellen | Runbook RB-FLOWDOC-01 | 10 Min. |
    | 3 | Volumes mit restic wiederherstellen | `restic restore latest --target /` mit Pfadfilter laut Runbook | 60 Min. |
    | 4 | Datenbank aus Dump einspielen, WAL bis Zielzeitpunkt nachfahren | Runbook RB-FLOWDOC-02 | 40 Min. |
    | 5 | Anwendung starten, Funktionsprüfung nach V12 Schritt 4 | `docker compose up -d` | 15 Min. |

    | Datum | Umfang | Ziel | Dauer | Ergebnis | Abweichungen | Durchgeführt von |
    | --- | --- | --- | --- | --- | --- | --- |
    | 18.11.2026 | vollständiges System | getrennte VM dms-restore01 | 2 Std. 35 Min. | bestanden | Runbook Schritt 4 um fehlenden Parameter ergänzt | Mara Klein, Tim Wolf |

    Überwachung: Erfolg jedes Laufs an Monitoring; Alarm nach 26 Stunden ohne Erfolg; wöchentlich `restic check` mit 5 % Stichprobe der Daten.
