# Konzepte und Vorlagen

Dieser Bereich enthält die Konzepte und Vorlagen, auf denen die Referenzumgebung und ihr späterer Ausbau beruhen. Alle Dokumente sind Arbeitsentwürfe zur internen Abstimmung. Stellen, an denen Unternehmenswissen fehlt, sind mit `[FIRMENANGABE …]` markiert. Beispiele und Namen sind fiktiv.

## Übersicht

| Reihe | Inhalt | Fassung |
| --- | --- | --- |
| [KI-Softwareentwicklung nach dem V-Modell](ki-softwareentwicklung/00-hauptdokument.md) | Wie Software mit KI-Agenten entwickelt wird, für IT, Engineering und Produkte: Projektplanung mit Arbeitspaketen, V-Modell mit Zuschnitt, Rollen und Agenten 0 bis 12, Domänenprofile und Normen | 24.11.2026, verallgemeinert das KI-Entwicklungskonzept |
| [KI-Unternehmenskonzept](ki-unternehmenskonzept/00-hauptdokument.md) | Wohin das Unternehmen mit KI will (Arbeitsplatz 2028) und wie der KI-Einsatz in den Fachprozessen geregelt ist: Portal, Freigaben, Agentenregister, Rechte, Schnittstellen, Qualität, ISMS | 20.11.2026, abgestimmt auf diese Referenzumgebung |
| [IT-Zielbild Business Applications](it-zielbild/index.md) | Plattform, Technologie-Standards, Portal und Integration, ERP und DMS, Weg aus der Microsoft-Abhängigkeit, Fahrplan | Revision vom 20.11.2026 |
| [KI-Entwicklungskonzept](ki-entwicklungskonzept/index.md) | Ursprüngliches Konzept am Beispiel eines DMS; die technischen Teile 08 bis 10 (Identitäten und MCP-Werkzeuge, Gateway-Regeln, Abnahmetests 01 bis 36) gelten weiter | Revision vom 20.11.2026 |
| [Vorlagen Systemdokumentation](vorlagen-systemdokumentation/00-wegweiser.md) | Baukasten aus 14 Vorlagen für eine einheitliche Grunddokumentation jedes Systems (IT-Grundschutz, ISO 27001), ohne Prüflisten und Tests je Anforderung; die Zuordnung zu Anforderungen führt der ISB im eigenen System. Mit Ausfüllbeispiel je Vorlage | 24.11.2026 |

## Wie die Dokumente zusammenhängen

- Das **KI-Unternehmenskonzept** regelt den Einsatz von KI in den Fachbereichen.
- Das Konzept **KI-Softwareentwicklung nach dem V-Modell** regelt, wie die dafür nötige Software entsteht. Es ersetzt den Prozessteil des KI-Entwicklungskonzepts und verweist für technische Einzelheiten darauf.
- Das **IT-Zielbild** gibt Plattform und Technologie-Standards für IT-Anwendungen vor.
- Die **Vorlagen Systemdokumentation** gelten für jedes System, das in Betrieb geht, auch für die Plattform dieser Referenzumgebung.

## Bekannte Abweichungen zwischen den Fassungen

Vom IT-Zielbild und vom KI-Entwicklungskonzept gibt es jeweils eine Word-Fassung und eine überarbeitete Textfassung (Revision). Hier ist die Revision eingestellt. Die Tabelle „offene Abstimmungen“ im Hauptdokument des KI-Unternehmenskonzepts gibt die Positionen der Word-Fassung des IT-Zielbilds wieder, etwa „Kubernetes mit Docker Compose als Plan B“. Die Revision sieht dagegen Docker Compose als Pilot und Kubernetes bei nachgewiesenem Bedarf vor. Welche Fassung verbindlich ist, legt die Programmleitung fest (Firmenangabe U-12).

## Pflege

Die Seiten wurden am 24.11.2026 aus den Textpaketen übernommen. Vorschlag: Ab jetzt wird diese Fassung im Git gepflegt (Dokumentation im Git nach ADR-004); Textpakete für die Word-Vorlagen werden bei Bedarf daraus neu erzeugt.

!!! warning "Zugriff"
    Im Prozess-Wiki sieht jede angemeldete Person diese Seiten, und der Wiki-MCP-Server macht sie für FLOWAI durchsuchbar. Vor einem Produktivbetrieb ist zu prüfen, ob Teile davon (zum Beispiel Sicherheitsarchitektur und Abnahmetests) einem engeren Leserkreis vorbehalten bleiben müssen.
