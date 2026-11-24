# V09 Protokollierung und Überwachung

Vorlagen-ID V09 · Vorlagenversion 1.0 · Stand 24.11.2026 · Entwurf zur internen Abstimmung

!!! note "Standardkopf"
    Jede ausgefüllte Systemdokumentation beginnt mit dem Standardkopf aus dem [Wegweiser](00-wegweiser.md#standardkopf-jeder-systemdokumentation).

## Zweck und Geltung

| Merkmal | Festlegung |
| --- | --- |
| Gilt für | Alle Systemtypen |
| Ausfüllen | IT-Betrieb; Sicherheitsereignisse mit dem Team, das die zentrale Protokollierung betreibt |
| Prüfen | ISB; bei personenbezogenen Protokolldaten Datenschutz |
| Zeitpunkt | Vor Inbetriebnahme; Aktualisierung bei neuen Protokollquellen oder Alarmen |
| Normbezug | OPS.1.1.5, DER.1; ISO/IEC 27001:2022 Anhang A 8.6, 8.15, 8.16, 8.17 |

## Schritt 1: Zeitbasis

| Feld | Eintrag |
| --- | --- |
| Zeitsynchronisation | {{siehe V02 Schritt 6}} |
| Zeitzone in Protokollen | {{Auswahl: UTC; lokale Zeit mit Zeitzonenangabe}} |

## Schritt 2: Protokollquellen

| Quelle | Inhalt | Format | Lokal gespeichert in | Weiterleitung | Aufbewahrung lokal / zentral | Personenbezogen |
| --- | --- | --- | --- | --- | --- | --- |
| {{Quelle}} | {{Inhalt}} | {{Format}} | {{Pfad}} | {{Ziel, Protokoll, verschlüsselt}} | {{Tage}} / {{Tage}} | {{ja/nein}} |

## Schritt 3: Mindestumfang sicherheitsrelevanter Ereignisse

| Ereignis | Erfasst | Quelle |
| --- | --- | --- |
| Erfolgreiche und fehlgeschlagene Anmeldungen (Betriebssystem, Anwendung, Datenbank) | {{ja/nein}} | {{Quelle}} |
| Nutzung privilegierter Rechte (zum Beispiel sudo, Ausführen als Administrator) | {{ja/nein}} | {{Quelle}} |
| Anlegen, Ändern und Löschen von Konten und Rechten | {{ja/nein}} | {{Quelle}} |
| Änderungen an Konfiguration und Software | {{ja/nein}} | {{Quelle}} |
| Start und Stopp von Diensten und Containern | {{ja/nein}} | {{Quelle}} |
| Ausfall oder Abschaltung von Sicherheitsfunktionen (Firewall, Virenschutz, Protokollierung) | {{ja/nein}} | {{Quelle}} |
| Löschen oder Verändern von Protokollen | {{ja/nein}} | {{Quelle}} |
| Zugriffe auf schutzbedürftige Daten, soweit vorgesehen | {{ja/nein}} | {{Quelle}} |

## Schritt 4: Schutz der Protokolle

| Feld | Eintrag |
| --- | --- |
| Zugriff auf Protokolle (lokal und zentral) | {{Rollen}} |
| Schutz vor Veränderung | {{zum Beispiel sofortige Weiterleitung, Speicher mit Schreibschutz}} |
| Löschung nach Fristablauf | {{Verfahren}} |
| Zweckbindung und Auswertung personenbezogener Protokolle | {{Regelung, zum Beispiel Betriebsvereinbarung}} |

## Schritt 5: Überwachung

| Prüfung | Schwellwert | Alarm an | Erwartete Reaktion |
| --- | --- | --- | --- |
| {{Prüfung}} | {{Schwellwert}} | {{Kanal, Empfänger}} | {{Reaktion bzw. Verweis auf V12}} |

[HINWEIS: Mindestens Erreichbarkeit des Dienstes, Ressourcen (CPU, Arbeitsspeicher, Speicherplatz), Ablauf von Zertifikaten, Erfolg der Datensicherung und Zustand der Protokollweiterleitung überwachen.]

## Schritt 6: Sicherheitsüberwachung

| Regel bzw. Anwendungsfall im SIEM | Auslöser | Schwere | Empfänger |
| --- | --- | --- | --- |
| {{Regel}} | {{Auslöser}} | {{Schwere}} | {{Empfänger}} |

## Schritt 7: Kapazität

| Ressource | Aktuell | Erwartetes Wachstum | Nächste Prüfung |
| --- | --- | --- | --- |
| {{Ressource}} | {{Wert}} | {{Wachstum je Monat}} | {{Datum}} |

## Ist-Stand erheben

| Zweck | Linux | Windows |
| --- | --- | --- |
| Lokale Protokolle und Belegung | `journalctl --disk-usage` | `wevtutil gl Security` |
| Weiterleitung | Konfiguration von rsyslog bzw. journald, Agent des SIEM | Konfiguration des Agenten bzw. der Ereignisweiterleitung |
| Audit-Regeln | `auditctl -l` | `auditpol /get /category:*` |
| Test einer Weiterleitung | Testmeldung mit `logger` und Prüfung im SIEM | Testereignis und Prüfung im SIEM |

## Prüfpunkte

- ☐ Alle Quellen aus Schritt 2 kommen in der zentralen Protokollierung an (mit Testmeldung geprüft).
- ☐ Der Mindestumfang aus Schritt 3 ist erfasst.
- ☐ Ein Testalarm aus Schritt 5 hat die Empfänger erreicht.
- ☐ Aufbewahrung und Löschung entsprechen [FIRMENANGABE V-09].
- ☐ Personenbezogene Protokolle sind mit Datenschutz und gegebenenfalls Betriebsrat abgestimmt.

## Unternehmensweite Festlegungen

[FIRMENANGABE V-09] ISB, IT-Betrieb und Datenschutz legen fest:

| Festlegung | Wert | Verantwortlich |
| --- | --- | --- |
| Zentrale Protokollierung bzw. SIEM und Anbindungsweg | offen | IT-Sicherheit |
| Aufbewahrungsfristen je Protokollart | offen | ISB, Datenschutz |
| Mindestumfang sicherheitsrelevanter Ereignisse | offen | ISB |
| Monitoring-System und Alarmkanäle | offen | IT-Betrieb |
| Regelung zur Auswertung personenbezogener Protokolle (zum Beispiel Betriebsvereinbarung) | offen | Datenschutz, Betriebsrat |

## Ausfüllbeispiel

??? example "Ausfüllbeispiel (fiktiv)"

    Zeitbasis: chrony mit ntp1 und ntp2; Protokolle in UTC.

    | Quelle | Inhalt | Format | Lokal | Weiterleitung | Aufbewahrung lokal / zentral | Personenbezogen |
    | --- | --- | --- | --- | --- | --- | --- |
    | journald | System, SSH, sudo, Docker, Container-Ausgaben | journal | /var/log/journal | rsyslog an log.flowcorp.example:6514, TLS | 14 / 90 Tage | ja |
    | auditd | Rechteänderungen, Zugriff auf /etc, Ausführung durch Administratoren | audit | /var/log/audit | SIEM-Agent | 14 / 180 Tage | ja |
    | nginx (Container proxy) | Zugriffe und Fehler | JSON | journald | wie journald | 14 / 90 Tage | ja (IP, Benutzer) |
    | Paperless-ngx | Anwendung, Anmeldungen | Text | journald | wie journald | 14 / 90 Tage | ja |
    | PostgreSQL | Verbindungen, DDL | Text | journald | wie journald | 14 / 90 Tage | ja |

    Mindestumfang: alle Ereignisse aus Schritt 3 erfasst; Anmeldungen der Anwendung zusätzlich im Keycloak-Ereignisprotokoll.

    Schutz: Zugriff lokal nur root und Gruppe adm; zentral Rollen SOC und Plattformbetrieb lesend; sofortige Weiterleitung; Auswertung nach Betriebsvereinbarung IT-Systeme 2025.

    | Prüfung | Schwellwert | Alarm an | Reaktion |
    | --- | --- | --- | --- |
    | HTTPS-Erreichbarkeit flowdoc.flowcorp.example | 3 Fehlschläge in 5 Minuten | Rufbereitschaft Plattform | V12 Störung „Weboberfläche nicht erreichbar“ |
    | Speicherplatz /srv/flowdoc | über 85 % | Team Plattformbetrieb | Erweitern oder bereinigen |
    | Zertifikatsablauf | weniger als 21 Tage | Team Plattformbetrieb | Erneuerung prüfen |
    | Datensicherung | kein Erfolg in 26 Stunden | Team Plattformbetrieb | V10 Schritt 7 |
    | Protokollweiterleitung | keine Meldung seit 30 Minuten | SOC | Weiterleitung prüfen |

    | Regel im SIEM | Auslöser | Schwere | Empfänger |
    | --- | --- | --- | --- |
    | Anmeldung Notfallkonto | Anmeldung breakglass auf dms01 | hoch | SOC, ISB |
    | Viele fehlgeschlagene SSH-Anmeldungen | mehr als 10 in 5 Minuten | mittel | SOC |
    | Änderung an sudo-Regeln | Schreibzugriff auf /etc/sudoers.d | mittel | SOC |

    Kapazität: Dokumente 120 GB, Wachstum etwa 6 GB je Monat; nächste Prüfung 01.05.2027.

    Prüfung am 19.11.2026: Testmeldung von dms01 im SIEM nach 4 Sekunden sichtbar; Testalarm Speicherplatz an Team Plattformbetrieb zugestellt.
