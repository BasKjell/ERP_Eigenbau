# 09 Konfigurationsmanagement, Rückverfolgbarkeit und Nachweise

Arbeitsreferenz SE-09 · Stand 24.11.2026 · Arbeitsentwurf zur internen Abstimmung

Das V-Modell funktioniert nur, wenn jede Prüfung eindeutig auf ihre Vorgabe und auf einen konkreten Stand verweist. Dieser Teil regelt Versionen, Verknüpfungen und Nachweise über alle Ebenen.

## Konfigurationselemente

| Element | Führendes System | Kennung |
| --- | --- | --- |
| Projektauftrag, Projekthandbuch, Projektstrukturplan, Arbeitspakete | Projektmanagement-Werkzeug bzw. DMS | Projekt-ID, AP-Nummer, Version |
| Anforderungen aller Ebenen, Baselines | Anforderungsmanagement | Anforderungs-ID, Version, Baseline-ID |
| Architektur, Entwurf, Entscheidungen | Git (Architektur-Repository) bzw. Anforderungsmanagement | Pfad, Commit |
| Code, Konfiguration, Tests | Git | Commit, Tag |
| Build-Artefakte, Firmware-Images, Container | Registry bzw. Artefaktspeicher | Digest, Signatur |
| Werkzeugkette | Git bzw. Registry | Versionen von Compiler, Bibliotheken, Modellen, Prompts, Gateway-Regeln |
| Testberichte, Reviews, Abnahmen | Testsysteme, Git, Anforderungsmanagement | Lauf-ID, Review-ID, Abnahme-ID |
| Release-Manifest | Nachweisspeicher | Manifest-ID, Signatur |
| Hardware-Revision und Variante (Produkte) | PLM bzw. ERP | Sachnummer, Revision |

## Verknüpfungen über das V

| Von | Nach | Art |
| --- | --- | --- |
| Arbeitspaket | Anforderungen und Architekturelemente | „liefert“ |
| Nutzeranforderung | Systemanforderung | „verfeinert“ |
| Systemanforderung | Systemelement und Software-Anforderung | „zugeordnet“, „verfeinert“ |
| Software-Anforderung | Komponente, Code | „umgesetzt in“ |
| Jede Vorgabe | Test auf derselben Ebene rechts | „geprüft durch“ |
| Test | Testlauf mit Ergebnis | „ausgeführt in“ |
| Release | alle obigen Stände | „enthält“ |

Agent 5 legt Verknüpfungen zu Aufgaben an, Agent 7 und 12 zu Tests. Die CI prüft, dass jede Änderung eine Aufgabe und eine Anforderung referenziert. Agent 10 meldet Vorgaben ohne Prüfung und Prüfungen ohne Vorgabe.

## Baselines und Änderungssteuerung

- An jedem Entscheidungspunkt wird der betroffene Stand als Baseline eingefroren.
- Änderungen an eingefrorenen Ständen laufen über einen Änderungsantrag mit Auswirkungsanalyse über das V (welche Ebenen, Tests und Dokumente betroffen sind). Agent 5 erstellt die Auswirkungsanalyse als Entwurf.
- Bei Projektklasse L entscheidet ein Änderungsgremium; bei S und M die Projektleitung bzw. der Product Owner.
- Probleme aus Tests und Feld werden als Problemmeldung erfasst, bewertet und über Änderungen behoben.

## Nachweise je Entscheidungspunkt

| Entscheidungspunkt | Mindestnachweis |
| --- | --- |
| EP0, EP1 | Projektauftrag, Einstufung, Projekthandbuch, Projektstrukturplan, Pläne, Beschluss |
| EP2 | Anforderungs-Baseline, Prüfkommentare, Freigabe |
| EP3, EP4 | Architektur-Baseline, Bedrohungsmodell, Entscheidungen, Teststrategie, Freigabe |
| EP5 | Commits, Reviews am exakten Stand, Modul- und Integrationstestberichte, CI-Bericht |
| EP6 | Verifikationsberichte je Anforderung, Bewertung offener Befunde, SBOM, Werkzeugkette |
| EP7 | Abnahme mit Person, Zeitpunkt, Digest bzw. Software- und Hardwarestand |
| EP8 | Signiertes Release-Manifest, Freigabe, Rückfallplan |
| EP9 | Abschlussbericht, Übergabe, Erfahrungen |

## Release-Manifest

Der Manifest-Dienst erstellt je Release ein signiertes Manifest mit: Baselines aller Ebenen, Commits, Artefakt-Digests, SBOM, Testläufen je Ebene, Reviews, Abnahme, Werkzeugkette (einschließlich Modellen und Prompts), offenen Befunden mit Bewertung und Ausnahmen mit Frist. Agent 10 bereitet die Übersicht vor; der Dienst prüft jeden Beleg selbst. Fehlt ein Pflichtbeleg, ist das Release gesperrt.

## Aufbewahrung

Nachweise werden nach den Fristen des Domänenprofils aufbewahrt (Teil 07), mindestens so lange, wie das Release im Einsatz ist bzw. unterstützt wird. Es muss möglich bleiben, einen ausgelieferten Stand Jahre später vollständig zu rekonstruieren.

## Unternehmensspezifische Nacharbeit

[FIRMENANGABE E-09] Konfigurationsmanagement und Qualität legen Kennungen, Verknüpfungsarten, Baseline-Regeln, das Änderungsgremium, den Nachweisspeicher und die Aufbewahrungsfristen je Profil fest.

| Feld für die interne Bearbeitung | Eintrag |
| --- | --- |
| Arbeitspunkt und vorgeschlagene Federführung | Konfigurationsmanagementplan / Konfigurationsmanagement mit Qualität |
| Zu ergänzen | Kennungen, Verknüpfungen, Baselines, Gremium, Nachweisspeicher, Fristen |
| Spätester Entscheid | Vor EP2 des ersten Pilotprojekts |
| Erwarteter Abschlussbeleg | Freigegebener KM-Plan und Muster eines Release-Manifests |
| Namentlich verantwortlich / Vertretung | offen / offen |
| Entscheid, Version, Datum und Beleglink | offen |
