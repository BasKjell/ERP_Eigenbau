# 06 GitLab, Repository-Struktur und Releaseverfahren

Arbeitsreferenz KI-U-06 · Stand 20.11.2026 · Arbeitsentwurf zur internen Abstimmung

## Empfohlene Struktur für die interne Instanz

| Gruppen- und Projektpfad (Beispiel) | Zuständiger Inhalt und Schutz |
| --- | --- |
| business-apps/flowportal, business-apps/flowwork, business-apps/platform-api | Produktcode, Tests, Dokumentation und Betriebsreferenzen je Produkt, eigene Maintainer |
| ai-platform/agents | agents/&lt;rolle>/instruction.md, contract.yaml, output.schema.json und eval/ für bereinigte Testfälle; register.yaml als Agentenregister |
| ai-platform/policies | Versionierte Werkzeugfreigaben, Schutzgrenzen und Freigabestufen, gesonderte Änderungskontrolle |
| integration/mcp-erp, integration/mcp-dms, integration/mcp-wiki | Schnittstellenverträge, Adapter und Vertragstests je MCP-Server |
| operations/deploy | Deklarative Umgebungskonfiguration und signierte Verweise auf freigegebene Releases |
| assurance/evidence-schemas | Belegformate und Prüfregeln. Sensible Testbelege im geschützten Nachweisspeicher. |

Git führt überprüfbare Quellstände. Große Modellgewichte, fertige Images und Pakete liegen in der internen Registry, Geheimnisse im Tresor. Produktionsdaten gelangen nicht in Repositories, Laufprotokolle oder Test-Fixtures. Neue Projekte übernehmen ein geschütztes Projektmuster mit Berechtigungsmatrix, CI-Definition, Verantwortlichen, Wiederherstellungshinweis und Archivierungsregel. Wie in der Referenzumgebung gilt: Eine Änderung ist erst fertig, wenn die betroffenen Prozess-, Benutzer-, Admin- und Schnittstellenseiten im selben Merge Request aktualisiert sind.

## Vom Ticket zum ausgelieferten Stand

1. Das Ticket in FLOWTASK verweist auf Use Case und Baseline in FLOWWORK. Der Entwickler oder Agent erhält ein zeitlich und projektbezogen begrenztes Schreibrecht am Aufgabenbranch. Änderungen an Richtlinien, Runnern und Deployment sind separat geschützt.
2. Der Merge Request beschreibt Anforderungs-ID, Akzeptanztests, Risikoklasse, Rückfall und betroffene Rollen. Ein unabhängiger Prüfer beurteilt den tatsächlichen Stand. Änderungen nach dem Review verwerfen die alte Zustimmung nach dem vorgesehenen Regelwerk.
3. Die CI prüft Build, Funktions- und Berechtigungstests, Abhängigkeiten, Lizenzen sowie Herkunft. Läufe mit ungeprüften Branchinhalten bekommen keine Produktionsgeheimnisse. Runner für Entwicklung und Auslieferung sind getrennt. Freigaben und Scan-Ausnahmen besitzen benannte Eigentümer und Fristen.
4. Nach Integration wird der endgültige Kandidat gebaut und getestet. Das Manifest enthält Quell-SHA, Baseline, Pipeline-ID, Artefakt-Digest, SBOM, Rollenvertrag, Modell und Richtlinie. Abnahme und produktive Auslieferung referenzieren dasselbe Manifest. Verschiebt sich die Basis oder ändert sich ein Artefakt, werden die betroffenen Prüfungen wiederholt.
5. Der Deploymentdienst prüft Berechtigung, Integrität und Freigabe. Er übernimmt dasselbe Artefakt aus Staging. Der Dienst vermerkt Zielumgebung, Zeit und Ergebnis. Nach einem gestaffelten Rollout geben Funktionsprobe und Betriebsmetriken den nächsten Schritt frei.

## Plattformgrenzen und Rücknahme

GitLab führt Code Owners für Premium und Ultimate. Für verpflichtende Code-Owner-Freigaben müssen Lizenzstufe, Branchschutz, Direkt-Push-Rechte und tatsächliche Durchsetzung zusammenpassen. Der Plattformowner testet einen unberechtigten Direkt-Push, ein Eigenreview und einen geänderten Kandidaten auf Ablehnung. Wenn die Edition die geforderte Regel nicht erzwingt, wird vor produktiver Nutzung ein technisch unabhängiges Release-Gate mit geprüftem Identitäts- und Kandidatenbezug nachgewiesen oder eine geeignete Edition ausgewählt. Eine CODEOWNERS-Datei allein erbringt den Nachweis nicht.
Quelle: GitLab, Code Owners — <https://docs.gitlab.com/user/project/codeowners/>

Rollback umfasst die vorherige Kombination aus Code, Prompt, Modell und Richtlinie. Datenbankmigrationen müssen rückwärtsverträglich sein oder einen getesteten Wiederherstellungs- und Abgleichplan haben. Bereits geschriebene ERP-Belege bleiben Fachvorgänge. Eine technische Rücknahme löst ihre fachliche Korrektur über den Eigentümer aus. Beim Notfallrelease werden Umfang, Befugnis, Befristung und nachträglicher unabhängiger Review dokumentiert.

## Unternehmensspezifische Nacharbeit

[FIRMENANGABE U-06] Releaseleitung trägt GitLab-Edition, den Umzug des Repositorys der Referenzumgebung und seiner CI in die interne GitLab-Instanz, reale Gruppen, Runnergrenzen, Prüfervertretung, geschützte Zweige, Signaturschlüsselverwaltung und genehmigten Notfallpfad ein. Vor Pilotübergabe einen exemplarischen Release inklusive Rücknahme belegen.

| Feld für die interne Bearbeitung | Eintrag |
| --- | --- |
| Arbeitspunkt und vorgeschlagene Federführung | Releasepfad / Releaseleitung |
| Zu ergänzen | Edition, Schutzregeln, Runner und Prüfervertretung |
| Spätester Entscheid | Vor produktiv nutzbarem Release |
| Erwarteter Abschlussbeleg | Blockierter unzulässiger Release und geprüfter korrekter Kandidat |
| Namentlich verantwortlich / Vertretung | offen / offen |
| Entscheid, Version, Datum und Beleglink | offen |
