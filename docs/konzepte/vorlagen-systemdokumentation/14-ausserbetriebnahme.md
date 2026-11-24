# V14 Außerbetriebnahme

Vorlagen-ID V14 · Vorlagenversion 1.0 · Stand 24.11.2026 · Entwurf zur internen Abstimmung

!!! note "Standardkopf"
    Jede ausgefüllte Systemdokumentation beginnt mit dem Standardkopf aus dem [Wegweiser](00-wegweiser.md#standardkopf-jeder-systemdokumentation).

## Zweck und Geltung

| Merkmal | Festlegung |
| --- | --- |
| Gilt für | Alle Systemtypen bei Stilllegung, auch bei Ersatz durch ein Nachfolgesystem |
| Ausfüllen | IT-Betrieb mit der systemverantwortlichen Person |
| Prüfen und freigeben | Systemverantwortliche Person, ISB, bei personenbezogenen Daten Datenschutz |
| Zeitpunkt | Planung vor dem Abschalttermin; Abschluss nach Löschung und Bereinigung |
| Normbezug | CON.6, OPS.1.2.2, ORP.4; ISO/IEC 27001:2022 Anhang A 5.11, 5.33, 7.14, 8.10 |

## Schritt 1: Entscheidung und Termine

| Feld | Eintrag |
| --- | --- |
| Grund der Stilllegung | {{Grund}} |
| Nachfolgesystem | {{System-ID oder „keines“}} |
| Entscheidung durch, am | {{Name}}, {{Datum}} |
| Letzter Nutzungstag | {{Datum}} |
| Abschalttermin | {{Datum}} |
| Change-Nr. | {{Change-Nr.}} |

## Schritt 2: Daten übernehmen, aufbewahren oder löschen

| Datenart (aus V01) | Entscheidung | Ziel bzw. Verfahren | Aufbewahrung bis | Verantwortlich |
| --- | --- | --- | --- | --- |
| {{Datenart}} | {{Auswahl: migrieren; archivieren; löschen}} | {{Ziel oder Löschverfahren}} | {{Datum}} | {{Name}} |

[HINWEIS: Aufbewahrungspflichten (zum Beispiel steuerliche Fristen) gehen der Löschung vor. Laufende Aufbewahrungssperren mit der zuständigen Stelle klären.]

## Schritt 3: Datenträger und Speicher löschen

| Datenträger bzw. Speicher | Verfahren | Nachweis | Durchgeführt von, am |
| --- | --- | --- | --- |
| {{Datenträger, Volume, Bucket}} | {{Auswahl: kryptografisches Löschen (Schlüssel vernichten); Überschreiben; Löschen durch Plattform; physische Vernichtung nach DIN 66399}} | {{Protokoll bzw. Zertifikat}} | {{Name, Datum}} |

## Schritt 4: Bestehende Sicherungen

| Sicherung | Verbleib | Löschung bzw. Ablauf |
| --- | --- | --- |
| {{Sicherung aus V10}} | {{bis Fristablauf aufbewahren / sofort löschen}} | {{Datum, Nachweis}} |

## Schritt 5: Zugänge und Verbindungen entfernen

- ☐ Persönliche Administrationskonten und Rollen entfernt (V04).
- ☐ Service-User, API-Schlüssel und Tokens gesperrt bzw. gelöscht; Einträge im Secret-Manager gelöscht (V04).
- ☐ Clients bzw. Anwendungsregistrierungen im Identitätsdienst entfernt.
- ☐ Zertifikate widerrufen (V03).
- ☐ Firewall-Freigaben zurückgenommen, mit Change-Nummer (V03).
- ☐ DNS-Einträge entfernt (V03).
- ☐ Schnittstellen bei den Partnersystemen abgemeldet (V07).

## Schritt 6: Betrieb bereinigen

- ☐ Überwachung und Alarme entfernt (V09); vorhandene Protokolle bleiben bis Fristablauf.
- ☐ Sicherungsjobs beendet (V10).
- ☐ Patch- und Scan-Zuordnung entfernt (V11).
- ☐ Lizenzen und Verträge gekündigt.
- ☐ Inventar bzw. CMDB auf „stillgelegt“ gesetzt; Grundschutz-Modellierung des Informationsverbunds aktualisiert.
- ☐ Eintrag im Verzeichnis der Verarbeitungstätigkeiten angepasst.

## Schritt 7: Hardware

| Gerät | Verbleib | Nachweis |
| --- | --- | --- |
| {{Gerät, Seriennummer oder „nur virtuell“}} | {{Auswahl: Wiederverwendung nach Löschung; Rückgabe; Entsorgung}} | {{Nachweis}} |

## Schritt 8: Abschluss

| Rolle | Name | Bestätigung | Datum |
| --- | --- | --- | --- |
| IT-Betrieb | {{Name}} | Alle Schritte erledigt | {{Datum}} |
| Systemverantwortliche Person | {{Name}} | Daten wie festgelegt behandelt | {{Datum}} |
| ISB | {{Name}} | Abnahme | {{Datum}} |

Die Systemdokumentation wird auf „außer Kraft“ gesetzt und nach [FIRMENANGABE V-14] aufbewahrt.

## Unternehmensweite Festlegungen

[FIRMENANGABE V-14] ISB und Datenschutz legen fest:

| Festlegung | Wert | Verantwortlich |
| --- | --- | --- |
| Löschverfahren je Schutzbedarf und Datenträgerart | offen | ISB |
| Dienstleister für Datenträgervernichtung und Nachweisform | offen | IT-Betrieb |
| Aufbewahrung der Systemdokumentation nach Stilllegung | offen | ISB |
| Löschkonzept des Unternehmens (zum Beispiel nach DIN 66398) | offen | Datenschutz |

## Ausfüllbeispiel

??? example "Ausfüllbeispiel (fiktiv)"

    Fiktiver Fall: SYS-0042 wird im Jahr 2031 durch ein neues DMS ersetzt.

    | Feld | Eintrag |
    | --- | --- |
    | Grund | Ablösung durch DMS-Nachfolger SYS-0120 |
    | Nachfolgesystem | SYS-0120 |
    | Entscheidung | Julia Neumann, 15.01.2031 |
    | Letzter Nutzungstag | 30.06.2031 |
    | Abschalttermin | 15.07.2031 |
    | Change-Nr. | CHG-2031-0402 |

    | Datenart | Entscheidung | Ziel bzw. Verfahren | Aufbewahrung bis | Verantwortlich |
    | --- | --- | --- | --- | --- |
    | Verträge | migrieren | SYS-0120, Prüfung mit Anzahl und Prüfsummen | laut Vertrag | Julia Neumann |
    | Arbeitsanweisungen | migrieren, nur gültige Fassungen | SYS-0120 | – | Fachbereiche |
    | Arbeitskopien von Eingangsrechnungen | löschen | Original liegt im Archiv | – | Julia Neumann |

    | Speicher | Verfahren | Nachweis | Durchgeführt |
    | --- | --- | --- | --- |
    | Datenträger der VM dms01 | kryptografisches Löschen: LUKS-Schlüssel vernichtet, danach Volume der Plattform gelöscht | Löschprotokoll LP-2031-033 | Mara Klein, 16.07.2031 |

    Sicherungen: laufen nach 12 Monaten ab; letzte Löschung am 15.07.2032, Nachweis durch Bericht des Sicherungssystems.

    Zugänge und Betrieb: alle Prüfpunkte erledigt am 16. und 17.07.2031, Firewall-Rücknahme unter CHG-2031-0403.

    Hardware: nur virtuell, keine Geräte.

    Abschluss: bestätigt durch IT-Betrieb, Systemverantwortliche Person und ISB am 18.07.2031; Dokumentation „außer Kraft“, Aufbewahrung zehn Jahre.
