# V11 Patch-, Änderungs- und Schwachstellenmanagement

Vorlagen-ID V11 · Vorlagenversion 1.1 · Stand 24.11.2026 · Entwurf zur internen Abstimmung

!!! note "Standardkopf"
    Jede ausgefüllte Systemdokumentation beginnt mit dem Standardkopf aus dem [Wegweiser](00-wegweiser.md#standardkopf-jeder-systemdokumentation).

## Zweck und Geltung

| Merkmal | Festlegung |
| --- | --- |
| Gilt für | Alle Systemtypen |
| Ausfüllen | IT-Betrieb |
| Prüfen | Change-Verantwortliche und ISB |
| Zeitpunkt | Vor Inbetriebnahme; Befundliste laufend; Überprüfung im festgelegten Intervall |
| Normbezug | OPS.1.1.3, OPS.1.1.6; ISO/IEC 27001:2022 Anhang A 8.8, 8.9, 8.19, 8.32 |

## Schritt 1: Komponenten und Update-Wege

| Komponente | Update-Quelle | Information über Sicherheitslücken | Verfahren | Verantwortlich | Support bis |
| --- | --- | --- | --- | --- | --- |
| {{Auswahl: Betriebssystem; Pakete; Container-Images; Anwendung; Datenbank; Firmware bzw. Plattform}} | {{Quelle}} | {{zum Beispiel Sicherheitsmitteilungen des Herstellers, Abonnement}} | {{Auswahl: automatisch; manuell im Wartungsfenster; Neubau des Images}} | {{Name}} | {{Datum}} |

## Schritt 2: Patchfristen

[HINWEIS: Fristen nach [FIRMENANGABE V-11]. Die Werte in der Tabelle sind Vorschläge.]

| Schwere | Frist bis zur Installation | Ausnahme genehmigt durch |
| --- | --- | --- |
| Aktiv ausgenutzt | sofort, spätestens nach {{Stunden}} | ISB |
| Kritisch | 7 Tage | ISB |
| Hoch | 30 Tage | IT-Leitung |
| Mittel und niedrig | nächster regulärer Zyklus | IT-Betrieb |

## Schritt 3: Wartungsfenster

| Feld | Eintrag |
| --- | --- |
| Reguläres Wartungsfenster | {{Wochentag, Uhrzeit}} |
| Ankündigung an Nutzer | {{Vorlauf, Kanal}} |
| Neustart-Regel | {{zum Beispiel automatisch im Wartungsfenster bei Kernel-Updates}} |

## Schritt 4: Änderungsverfahren

| Feld | Eintrag |
| --- | --- |
| Change-Prozess bzw. Werkzeug | [FIRMENANGABE V-11] |
| Vorab genehmigte Standard-Changes | {{zum Beispiel Sicherheitsupdates von Paketen, Kleinversionen von Images}} |
| Test vor Produktion | {{Testsystem, Verfahren}} |
| Rücknahme | {{Snapshot, vorheriges Image, Rücknahme laut V05 bzw. V06}} |
| Dokumentationspflicht | Betroffene Vorlagen werden im selben Change aktualisiert. |

## Schritt 5: Schwachstellenscan

| Feld | Eintrag |
| --- | --- |
| Werkzeug | {{Werkzeug}} |
| Art | {{Auswahl: mit Anmeldung; ohne Anmeldung; Image-Scan; Webscan}} |
| Intervall | {{Intervall}} |
| Letzter Scan | {{Datum, Bericht}} |

Offene Befunde:

| Befund (CVE bzw. Bezeichnung) | Schwere | Gefunden am | Frist | Maßnahme | Status | Ausnahme bis, genehmigt von |
| --- | --- | --- | --- | --- | --- | --- |
| {{Befund}} | {{Schwere}} | {{Datum}} | {{Datum}} | {{Maßnahme}} | {{Status}} | {{Datum, Name}} |

## Schritt 6: Supportende

| Komponente | Supportende | Geplante Maßnahme | Termin |
| --- | --- | --- | --- |
| {{Komponente}} | {{Datum}} | {{Maßnahme}} | {{Datum}} |

## Ist-Stand erheben

| Zweck | Befehl |
| --- | --- |
| Ausstehende Updates Debian bzw. Ubuntu | `apt list --upgradable` |
| Ausstehende Updates RHEL | `dnf check-update` |
| Ausstehende Updates SLES | `zypper list-patches` |
| Installierte Windows-Updates | `Get-HotFix` |
| Veraltete Container-Images | Image-Scan bzw. Abgleich mit der Registry (siehe V05) |

## Unternehmensweite Festlegungen

[FIRMENANGABE V-11] IT-Betrieb und ISB legen fest:

| Festlegung | Wert | Verantwortlich |
| --- | --- | --- |
| Patchfristen je Schwere | offen | ISB |
| Reguläre Wartungsfenster | offen | IT-Betrieb |
| Change-Prozess, Werkzeug und Standard-Changes | offen | IT-Leitung |
| Schwachstellenscanner und Intervalle | offen | IT-Sicherheit |
| Genehmigung von Ausnahmen | offen | ISB |

## Ausfüllbeispiel

??? example "Ausfüllbeispiel (fiktiv)"

    | Komponente | Quelle | Information | Verfahren | Verantwortlich | Support bis |
    | --- | --- | --- | --- | --- | --- |
    | Debian 13 | interner Spiegel | Debian Security Advisories | Sicherheitsupdates automatisch täglich (unattended-upgrades), Neustart im Wartungsfenster | Plattformbetrieb | regulär voraussichtlich 2028, danach LTS |
    | Docker Engine | interner Spiegel | Sicherheitsmitteilungen des Projekts | manuell im Wartungsfenster | Plattformbetrieb | laufende Version |
    | Images paperless-ngx, postgres, valkey, nginx | interne Registry | Image-Scan täglich, Projektmitteilungen | Renovate-Merge-Request, Test, Ausrollen | Plattformbetrieb | je Version |
    | PostgreSQL 17 | Image | Projektmitteilungen | Kleinversion monatlich, Hauptversion geplant | Plattformbetrieb | November 2029 |

    Patchfristen: Vorschlagswerte übernommen, aktiv ausgenutzt spätestens nach 24 Stunden.

    Wartungsfenster: dienstags 19:00 bis 21:00; Ankündigung zwei Arbeitstage vorher im Portal; Neustart bei Kernel-Updates automatisch im Fenster.

    Änderungsverfahren: Change im Ticketsystem; Standard-Changes für Paket-Sicherheitsupdates und Kleinversionen der Images; Test auf dms-test01; Rücknahme über Snapshot der VM bzw. vorherigen Commit der Compose-Datei.

    Schwachstellenscan: Scanner mit Anmeldung wöchentlich, Image-Scan täglich, Webscan monatlich; letzter Scan 19.11.2026, Bericht SCAN-2026-0711.

    | Befund | Schwere | Gefunden am | Frist | Maßnahme | Status | Ausnahme |
    | --- | --- | --- | --- | --- | --- | --- |
    | CVE in Bildbibliothek des Images webserver | hoch | 19.11.2026 | 19.12.2026 | Update mit nächster Paperless-Version | offen | Ausnahme bis 31.12.2026, ISB |

    Supportende: keine Komponente innerhalb der nächsten zwölf Monate.
