# 09 Regeln für Gateway und lokale Modellserver

Dieser Teil spezifiziert das erwartete Verhalten. Die frühere YAML-Skizze mit unverschlüsselten Backend-Adressen, nicht nachgewiesenen Produktfeldern und vollständigen Werkzeugargumenten im Log wird durch prüfbare Regeln ersetzt. Der Plattformbetrieb erstellt die ausführbare Konfiguration für die tatsächlich installierte Version und validiert sie gegen deren Schema.

## Reihenfolge der Autorisierung

1. Das Gateway prüft für jede Modell- und Werkzeugroute TLS, zugelassenen Aussteller, Signatur mit erlaubtem Algorithmus, Zielressource, Gültigkeit und autorisierte Dienstidentität. Ein geschütztes Register bindet Identität, Rolle, Projekt, Lauf und freigegebenes Modell. Unbekannte Rollen, fehlende Bindungen und mehrdeutige Zuordnungen führen zur Ablehnung.

2. Das Gateway akzeptiert nur ausdrücklich erlaubte Kombinationen aus Rolle, Ziel und Operation. Es prüft auch direkte Aufrufe von Werkzeugen, die in einer Liste verborgen sind. Der Worker kann weder Modellpfad noch Backend-Adresse auswählen. Werkzeugbeschreibungen sind versioniert. Neue Werkzeuge bleiben bis zum geprüften Change gesperrt.

3. Zum Adapter gilt mTLS mit festgelegter Dienstidentität und vertrauenswürdiger CA. Bei getrennten OAuth-Ressourcen wird ein neues, für den jeweiligen Adapter bestimmtes Token verwendet. Für die Produkt-API ruft der Adapter ein eigenes begrenztes Credential ab. Delegierte Aufträge binden die auslösende Person nachvollziehbar an den Lauf. Die Bedeutung von sub, azp und gegebenenfalls act ist gegen das konkrete Tokenprofil zu prüfen.

4. Adapter und Zielsystem kontrollieren Objekt, Projekt, Version, Pfad, Status und Empfängerkreis. Der Entwicklungsagent schreibt nur auf den ihm zugewiesenen Branch. Für einen Retry gelten dieselben Bedingungen wie für den ersten Aufruf. Der Server prüft den aktuellen Zustand erneut.

## Modellbetrieb und Protokolle

Builder, Prüfer und optional ein kleines Dokumentationsmodell laufen intern. Die Zuordnung ist versioniert und an die Evaluation gebunden. Eingabedaten, Gewichte, Modellserver-Image, Prompt- und Policy-Versionen sind nachvollziehbar. Modellentscheidungen werden durch tatsächliche Tests und unabhängige Primärbelege ergänzt.

Logs enthalten standardmäßig Ereignis-ID, Zeit, Lauf, Dienstrolle, soweit erforderlich die pseudonyme Personenreferenz, Ressourcen-ID, Policy-Version, Entscheidung und Fehlercode. Keine Vollprompts, Antworten, Suchtexte, ungefilterten Argumente oder Zugangsdaten in Standardlogs. Ein begründeter Diagnosemitschnitt erfordert einen begrenzten Umfang, Berechtigung, Redigierung und Löschfrist. Integritätsschutz und Löschkonzept sind aufeinander abzustimmen.

## Erlaubte Werkzeuge je Rolle

Die logischen Namen dienen der Zuordnung auf die lokalen Produkte. Jede Operation ist zusätzlich auf Objekt, Projekt und Zielsystemkonto begrenzt. Allgemeine Freigabe-, Merge-, Lösch-, Administrations- und Deploymentwerkzeuge gehören zu keiner Agentenrolle.

| Rolle | Werkzeuge im zulässigen Umfang | Modellprofil |
| --- | --- | --- |
| 1 Anforderungen | RM lesen, Entwurf anlegen und ändern, Frage an Eigentümer, erlaubte Wissenssuche. | Builder |
| 2 Anforderungsprüfung | RM lesen und kommentieren, Dokumentation und zugehörige Testbelege lesen, Prüfbefund schreiben. | Prüfer |
| 3 Architektur | RM und erlaubtes Fachwissen lesen, Architekturbranch schreiben, Review anfordern. | Builder |
| 4 Sicherheit | RM, Architektur, Diff und begrenzte CI-Scanberichte lesen, Befund kommentieren. | Prüfer |
| 5 Planung | Baseline lesen, Tickets suchen und anlegen, zulässige Aufgabenbeziehung anfügen. | Assistenz |
| 6 Entwicklung | Aufgabe und Baseline lesen, Featurebranch schreiben, Sandbox-Build und Paketlookup, Entwicklungs-CI lesen. | Builder |
| 7 Akzeptanztests | Baseline und Schnittstellen lesen, Testbranch schreiben, Testbeziehung anfügen, festen Stagingjob starten und bereinigten Testbericht lesen. | Prüfer |
| 8 Codeprüfung | Änderung und Baseline lesen, Abdeckungs- und Scanberichte lesen, versioniertes Review abgeben. | Prüfer |
| 9 Dokumentation | Baseline, Architektur, freigegebene Testbelege und Konfigurationsreferenzen lesen, Dokumentationsbranch schreiben. | Assistenz |
| 10 Nachweise | Projektbezogene Evidenzmetadaten von RM, Git, CI, Ticket- und SBOM-System lesen. Zusammenstellung als Laufresultat zurückgeben. | Assistenz |
| 11 Schwachstellen | Interne Meldungen und SBOM lesen, betroffene Komponenten und vorhandene Tickets suchen, Ticket erstellen. | Assistenz |

## Versionen und Betriebsgrenzen

Im Release der Plattform werden Produktversion, Konfigurationsschema, Richtlinien-Hash, Vertrauenskette und Testergebnisse gemeinsam erfasst. Budgets gelten je Lauf über alle Replikate hinweg. Nach Erschöpfung hält der Orchestrator an. Der Betreiber prüft Schlüsselrotation, Sperrlisten, Queue-Wiederanlauf und das Verhalten bei ausgefallener Protokollierung. Pflichtaktionen mit fehlender Nachweiskette bleiben gesperrt.

- MCP · Autorisierung für die HTTP-Transportspezifikation vom 25.11.2025 — <https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization>
- IETF · RFC 8693 OAuth 2.0 Token Exchange — <https://www.rfc-editor.org/rfc/rfc8693>
- Keycloak · Grenzen und Konfiguration des Token Exchange — <https://www.keycloak.org/securing-apps/token-exchange>
