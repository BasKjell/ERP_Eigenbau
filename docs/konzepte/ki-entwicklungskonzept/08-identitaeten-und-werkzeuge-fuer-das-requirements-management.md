# 08 Identitäten und Werkzeuge für das Requirements Management

Das Requirements-Management-System führt Anforderungen, Versionen, Beziehungen und fachliche Entscheidungen. Ein lokaler MCP-Server übersetzt begrenzte Fachoperationen in die Produkt-API. Für Jama oder ein anderes RM-Tool werden Statusmodell, Rechte und Versionsverhalten zunächst mit einem Testprojekt nachgewiesen.

## Ein Auftrag hat drei Identitäten

Die Person meldet sich über AD und den Unternehmens-IdP an. Der Worker besitzt eine eigene Dienstidentität je Rolle. Der Adapter verwendet für das Zielsystem ein projekt- und rollengebundenes Konto. Der Laufdienst hält fest, welche Person oder welcher genehmigte technische Auftrag den Lauf auslöst. Die Person darf nicht über ein beliebiges Feld im Werkzeugaufruf ersetzt werden.

Keycloak kann AD lesend über LDAPS anbinden. Gruppen für PO, Tech Lead, Release, ISB und Key User werden getrennt von DMS-Datengruppen abgebildet. Personen nutzen MFA. Dienste verwenden getrennte Schlüssel und kurze Tokenlaufzeiten. Schlüssel, Zertifikate, Realm-Konfiguration und Ausfallverhalten werden vom Plattformbetrieb versioniert beziehungsweise im Tresor verwaltet.

## Fachmodell im RM

| Objekt | Pflichtinhalt | Zulässige Änderung |
| --- | --- | --- |
| Fachauftrag | Zweck, Zielgruppe, Quelle, Umfang, ausgeschlossene Funktionen, Eigentümer, Datenklasse und Erfolgsbeispiel. | PO bestätigt den Auftrag. Neue Zweckbestimmung erfordert neue Entscheidung. |
| Anforderung und Kriterium | Stabile ID und Version, Typ, Quelle, Muss/Soll, Begründung, Verantwortlicher, beobachtbares Ergebnis. | Agent 1 schreibt im Entwurf. Agent 2 kommentiert. Nach Fixierung entsteht eine neue Version. |
| Prüfung und Test | Gegenstand und Version, Befund, Prüfer, Test-ID, Kriterium, Soll. Ausführung zusätzlich mit Ist, Umgebung, Zeit und Bericht. | Testdefinition durch 7. Primärergebnis aus CI. Keine nachträgliche Änderung des historischen Laufs. |
| Baseline und Abnahme | Snapshot referenzierter Objektversionen. Abnahme enthält Person, Entscheidung, Kandidat, Digest und Begründung. | Workflow friert bei erfülltem G1 ein. Menschliche Freigaben entstehen ausschließlich in authentifizierter Oberfläche. |

## Zwei Arten von Baseline

Der technische Zustand „Arbeitsbaseline fixiert“ bezeichnet eine unveränderliche, zur Bearbeitung zugelassene Version. „Fachlich freigegeben“ setzt die explizite Entscheidung des PO voraus. Erlaubt das Produkt diese Trennung nicht, bleibt die explizite Baseline-Freigabe im RM bis zur Einführung eines belastbaren Ersatzes erforderlich.

## Vertrag des MCP Adapters

| Operation | Erlaubter Aufrufer | Bedingungen am Adapter und Zielsystem |
| --- | --- | --- |
| rm.search / get | Projektrollen mit sachlichem Bezug | Objekttyp, Projekt, Sichtbarkeit und zulässige Felder serverseitig begrenzen. Suchtreffer und Zähler folgen denselben Rechten. |
| rm.create_draft | 1 Anforderungen | Projekt, Fachauftrag, erlaubte Felder, Schema und Idempotenzschlüssel prüfen. Beispiel: A-17 / REQ-17 / Entwurf 1. |
| rm.update_draft | 1 Anforderungen | Nur eigener zuständiger Entwurf. expected_version ist Pflicht. Bei Konflikt aktuellen Stand zurückmelden und neu vergleichen. |
| rm.comment / ask_owner | 2 prüft, 1 fragt nach | Kommentar bindet ID und Version. Frage geht nur an berechtigte Fachverantwortliche. Keine allgemeinen Benachrichtigungsrechte. |
| rm.link_trace | 5 für Aufgabe, 7 für Testfall | Beziehungstyp und beide Endpunkte im selben zulässigen Projekt prüfen. Historische Baselines bleiben unverändert, spätere Links sind eigene versionierte Objekte. |
| rm.get_baseline | Rollen 1 bis 10 nach Zweck | Snapshot, Versionsliste, Status, Freigabetyp und Digest liefern. Filtern nach Projekt und tatsächlichem Auftrag. |

## Weitere Ziele

Git vergibt getrennte Zielkonten für Entwicklungs-, Test- und Dokumentationsbranches. CI bietet nur Berichtslesezugriff und für Rolle 7 einen festen Staging-Test. Der Paketspiegel erlaubt freigegebene Versionen. Die Sandbox führt Builds unter Ressourcenlimits aus. Ticket- und SBOM-Adapter begrenzen Zugriff auf Projekt und Release. Die Wissenssuche prüft die Rechtekette aus Teil 4. Die vollständige Rollenzuordnung für diese Schnittstellen steht in Teil 9.

## Fehler und Teilabbruch

Bei gleichzeitigen Änderungen gewinnt die bestätigte Objektversion. Ein unterbrochener Schreibaufruf wird mit demselben Schlüssel abgeglichen. Gleicher Schlüssel und abweichende Nutzlast erzeugen einen Konflikt. Fehlt im Zieltool eine idempotente Anlage, speichert der Adapter Schlüssel und Zuordnung dauerhaft und gleicht den eindeutigen Fremdschlüssel vor jedem erneuten Versuch ab. Ein unklarer Ausgang hält den Schritt zur Klärung an.

Vor Freigabe sind Backend-Version und Lizenz, API-Limits, Rollenmodell, Feldrechte, Historienexport, unveränderliche Snapshots und Recovery zu belegen. Fehlende Produktfunktionen werden als Lücke mit Eigentümer und technischem Ersatz dokumentiert. Eine Freigabemaske allein belegt keine wirksame Sperre auf API-Ebene.
