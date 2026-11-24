# IT-Zielbild für Business Applications

Arbeitsentwurf zur internen Abstimmung · Stand 20.11.2026 · SSO über Keycloak ist festgelegt. Weitere Produktauswahl und Zeiträume sind offen.

## Inhalt

1 Zielbild und Leitprinzipien
2 Technologie und Lizenzregeln
3 Plattform und Betrieb
4 Portal, Anmeldung und Integration
5 ERP, DMS und weitere Anwendungen
6 Microsoft-Abhängigkeiten schrittweise abbauen
7 Fahrplan, Kosten, Risiken und Entscheidungen

## Wesentliche Korrekturen gegenüber den sieben Word-Vorlagen

| Aussage der Ausgangsfassung | Ergebnis der Revision | Folge für die Entscheidung |
|---|---|---|
| Die KI-Suche setzt PostgreSQL voraus. | Das KI-Konzept verlangt aktuelle Dokumentrechte vor der Ausgabe. Mehrere Indextechnologien kommen dafür infrage. | PostgreSQL als relationalen Standard vorschlagen. Den Suchdienst am Rechteentzug testen. |
| Kubernetes wird ab einer gewissen App-Anzahl erforderlich. | Quorum, Datenspeicher, Personal und gemessener Wiederanlauf entscheiden. | Compose und RKE2 am selben Dienst vergleichen. |
| GitLab Premium sei wegen jedes Merges nötig. | Der KI-Prozess fordert einen menschlichen Code-Owner für kritische Änderungen. GitLab ordnet seine Code-Owners-Funktion Premium/Ultimate zu. [Q4] | Edition oder alternative Durchsetzung gegen konkrete Umgehungspfade prüfen. |
| DMS-Eigenentwicklung und ERP-Ablösung sind gesetzt. | DMS ist im KI-Konzept ein Anwendungsbeispiel. Bestand, Standardsoftware und Ergänzung sind echte Alternativen. | Archivkern und ERP-Auswahl separat anhand derselben Geschäftsfälle entscheiden. |
| SSO oder AD-Entzug wirken unmittelbar in allen Anwendungen. | Lokale Sitzungen, Objekt-ACLs und Caches können länger wirksam sein. | Entzug bei laufender Sitzung, Suche und Portalaufgabe mit Zeitmessung prüfen. |
| Die Plattform erfüllt Normanforderungen zentral. | Maßnahmen können gemeinsam betrieben werden. Anwendbarkeit und Wirksamkeit sind für den Informationsverbund und die Anwendung nachzuweisen. | Anforderungen und Belege mit ISMS und Fachverantwortlichen zuordnen. |
