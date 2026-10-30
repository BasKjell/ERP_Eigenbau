# Lokalen AI-Assistenten sicher nutzen

Der Assistent beantwortet Statusfragen aus freigegebenen ERP-, MES- und
DMS-Werkzeugen. Im Standardmodus sind Antworten deterministisch; mit dem
`ai`-Profil kann ein lokales Ollama-Modell formulieren. Fachliche Quellen und
Freigaberegeln bleiben gleich.

## Statusfrage bearbeiten

1. Im Portal **AI Copilot** öffnen.
2. Eine konkrete Frage mit Auftrags-, Work-Order- oder Seriennummer stellen.
3. Antwort auf Status, Terminrisiko und offene Aktion prüfen.
4. Jeden Quellenchip öffnen bzw. die Referenz im führenden System prüfen.
5. Entscheidungen oder Freigaben ausschließlich im Fachsystem durchführen.

## Geeignete Fragen

- „Wie ist der Status von Auftrag 4711?“
- „Welche Aufträge sind gerade in Produktion?“
- „Welche Bestellungen sind verspätet?“
- „Warum ist SN-10004 gesperrt?“
- „Welche Dokumentrevision gilt für WO-2027-0042?“
- „Was fehlt vor der Lieferung?“

Der Assistent darf keine Qualitätsfreigabe, Buchung oder Benutzerberechtigung
eigenständig erteilen. Fehlt eine Quelle oder widerspricht die Antwort dem
Fachsystem, gilt das Fachsystem; Antwort und Referenz werden als Fehlerfall an
den Administrator gemeldet.

Unter der Antwort zeigen `Tool`-Chips, welche Lesefunktion verwendet wurde;
die weiteren Chips nennen die Fachreferenzen. Ein lokales Sprachmodell
formuliert die Antwort, bestimmt aber nicht selbst die Quellen.
