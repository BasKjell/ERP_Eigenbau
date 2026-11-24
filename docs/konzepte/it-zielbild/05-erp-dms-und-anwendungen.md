# 5 ERP, DMS und weitere Anwendungen

Arbeitsentwurf zur internen Abstimmung · Stand 20.11.2026 · SSO über Keycloak ist festgelegt. Weitere Produktauswahl und Zeiträume sind offen.

Vor einem Austausch werden drei Wege mit denselben Geschäftsvorfällen bewertet: Bestand in den Produktstandard zurückführen, ein geeignetes Produkt übernehmen oder fehlende Fachlogik gezielt entwickeln. Ein besser passender Standardprozess kann den Zusatzbetrieb einer zweiten Datenbank rechtfertigen. Sämtliche Produktentscheidungen in diesem Teil sind offen.

## ERP für einen Fertigungsbetrieb

| Option | Was für sie spricht | Was im PoC belegt werden muss |
|---|---|---|
| Infor COM standardisieren | Vorhandene Daten, Betriebserfahrung und bekannte Fertigungsprozesse. | Unterstützter Zielstand, Rückbau von Anpassungen, Kosten und Aufwand pro verbleibender Lücke. Weiterbetrieb, Update und Exit schriftlich bewerten. |
| Odoo Community mit gezielt ausgewählten Modulen | Python, PostgreSQL und ein modularer Ansatz. Community, zusätzliche OCA-Module und kommerzielle Funktionen getrennt betrachten. [Q1] | Konkrete Edition und Modulversion, Lizenz, deutsche Finanzprozesse, Upgradekosten und vertragliche Wartung nachweisen. |
| ERPNext | Offenes ERP im Frappe-Umfeld. Das offizielle Deployment beschreibt MariaDB für ERPNext. PostgreSQL-Unterstützung im Framework ist kein ERPNext-Betriebsnachweis. [Q2] | Fertigungstiefe, Versionskompatibilität deutscher Zusatzmodule, DATEV-Import beim Empfänger und MariaDB-Restore prüfen. |

Fünf verbindliche Vergleichsszenarien als Vorschlag für den Fachbereich:

1. Vom Angebot über Kundenauftrag und Lieferung zur Ausgangsrechnung einschließlich Storno. Belegkette und Deckungsbeitrag mit Referenzfall vergleichen.
2. Von der Bestellung über Teillieferung und abweichende Eingangsrechnung zur Freigabe. Menge, Preisabweichung und offene Verpflichtungen abstimmen.
3. PLM gibt eine neue Stücklistenrevision frei. Einen bestehenden und einen neuen Fertigungsauftrag verarbeiten. Der alte Auftrag muss seinen gültigen Stand behalten. Rückverfolgbarkeit von Serien-/Chargennummern prüfen, soweit fachlich gefordert.
4. Lagerbewegung und Inventurdifferenz buchen, eine Fehlbuchung korrigieren. Bestände, Bewertung und Historie mit Sollzahlen abgleichen.
5. Monatsabschluss mit Testmandant durchführen. Offene Posten, Summen und Salden abstimmen, DATEV-Export beim vorgesehenen Empfänger importieren und eine strukturierte E-Rechnung vollständig nachvollziehen.

Für alle Anbieter gelten dieselben pseudonymisierten oder synthetischen Testdaten und erwarteten Ergebnisse. Je Szenario dokumentiert der Prozesseigner „Standard“, „Konfiguration“, „Erweiterung“ oder „Lücke“, Kosten, Beleg und Akzeptanz. Vor Migration festlegen, welche Historie mitzieht und wie der prüfbare Zugriff auf den Rest erhalten bleibt. Umschaltfenster, Deltaübernahme, Stichtagsabgleich, Rückfall und Verantwortliche vorher proben.

## DMS und Archiv

| Variante | Geeigneter Versuch | Ausschlaggebende Grenze |
|---|---|---|
| Bestehendes ECM oder etabliertes Produkt erweitern | Dokumenttyp, Metadaten, Rollen und zweistufige Freigabe konfigurieren. | Übernimmt das System Revisionen, ACLs, Fristen und Historie vollständig? Export und Anbieterwechsel praktisch erproben. |
| Paperless-ngx als Abteilungslösung | Erfassung, OCR, vorhandene Workflows und Objektberechtigungen mit realistischem Fall prüfen. Diese Funktionen sind dokumentiert. [Q11] | Ein komplexer Freigabe- oder Archivprozess braucht einen eigenen Funktionsnachweis. |
| Eigene Fachoberfläche auf bewährtem Speicher-/Archivdienst | Einen betriebsrelevanten Sonderworkflow über APIs umsetzen. KI-Agenten können Implementierung und Tests übernehmen. | Entwicklungsteam trägt Wartung, Migration und Sicherheit. Aufbau eines eigenen Archivkerns separat kalkulieren und freigeben. |

Erster Migrationsversuch: Eine freigegebene und eine gesperrte Dokumentversion samt Metadaten, Berechtigungsvererbung, Prüfsumme und Aufbewahrungssperre übernehmen. In einem getrennten Wiederanlauf prüfen, ob Original, Verknüpfungen und effektive Rechte übereinstimmen. Ein Rechteverlust, eine zusätzliche Sichtbarkeit oder eine verlorene Löschsperre blockiert die Umschaltung. Revisionssicherheit umfasst den gesamten organisatorischen und technischen Ablauf.

Object Lock schützt konfigurierte Objektversionen unter definierten Bedingungen. Metadaten, Schlüssel, lesbarer Export, Indizes, Aufbewahrungsbeginn, Fristverlängerung und Sperre wegen offener Verfahren brauchen eigenen Schutz. Vor einer Löschung prüft das DMS Frist, Sperren, Berechtigung und Nachweis. Eine PDF/A-Ableitung bleibt zusätzlich zum benötigten Eingangsoriginal erhalten. Für ersetzendes Scannen kann die BSI TR-03138 die Verfahrensgestaltung unterstützen. [Q9, Q12–Q15]

## Rechnungen und Aufbewahrung in Deutschland

Für betroffene inländische B2B-Umsätze sind Empfang und Ausstellung getrennt zu prüfen. Der Empfang strukturierter Rechnungen ist seit 2025 einzuplanen. Für die Ausstellung gelten Übergangsregeln, insbesondere bis Ende 2026, für bestimmte Aussteller bis 800.000 Euro Vorjahresgesamtumsatz auch 2027 sowie gesonderte EDI-Regeln. Ausnahmen und Sonderfälle, etwa Kleinbetragsrechnungen oder steuerbefreite Umsätze, ordnet die Finanzfunktion mit der Steuerberatung zu. Bei hybriden Rechnungen ist der strukturierte Teil aufzubewahren. Zusätzliche steuerrelevante Informationen in Darstellung oder Anlagen müssen ebenfalls erhalten bleiben. Im Pilot XRechnung und ein einschlägiges ZUGFeRD-Profil mit Originaldatei, fachlicher Validierung und Abruf testen. [Q12, Q13]

§ 147 AO unterscheidet unter anderem zehn Jahre für Bücher bzw. Jahresabschlüsse, acht für Buchungsbelege und sechs für bestimmte Geschäftsbriefe. Fristbeginn, Sonderregeln und offene Verfahren sind je Dokumenttyp zu hinterlegen. Die Finanzfunktion zeichnet diese Zuordnung ab. Ein Speicherprodukt allein belegt weder GoBD-Einhaltung noch eine allgemeine Abnahme durch Wirtschaftsprüfer. [Q13, Q14]

## Priorität der übrigen Systeme

- Ticket, Wiki und Projekte: Den vorgesehenen Easy-Redmine-/Easy8-Weg zuerst mit dem Produktionsprozess und der MS-Project-Schnittstelle prüfen. Zammad, XWiki oder OpenProject sind Alternativen bei belegter Lücke. OpenProject dokumentiert PostgreSQL als unterstützte Datenbank. [Q3]
- PLM, CRM, MES und Produktion: PLM-Freigabestand und ERP-Fertigungssicht trennen. CRM im ERP gegen Vertriebsanforderungen testen. Für MES/MEU Offlinebetrieb, Scanner, Etikettendruck und Maschinenanschlüsse mit realen Geräten im Testbetrieb prüfen.
- Business Intelligence: Bestehende SQL-Server-, SSRS- oder Power-BI-Berichte mit fachlich freigegebenen Kennzahlen inventarisieren. Superset gegen eine Berichtsdatenbank pilotieren und Referenzsummen abgleichen.
- Personal und Lohn: Fachsoftware oder Dienstleister für die Abrechnung beibehalten, sofern die Fachprüfung dies bestätigt. Zeit- und Stammdatenschnittstellen sowie Zugriff auf Personaldaten separat freigeben.
- Zusammenarbeit und kleine Fachanwendungen: Nextcloud/Collabora oder openDesk bei konkretem Bedarf pilotieren. Kleine, gut abgegrenzte Access- oder Formularprozesse eignen sich als erste Python-Eigenentwicklung.

## Quellen und Referenzen

- [Q1] Odoo · Source install und PostgreSQL — <https://www.odoo.com/documentation/19.0/administration/on_premise/source.html>
- [Q2] Frappe · ERPNext Deployment und Datenbankvoraussetzung — <https://github.com/frappe/helm/blob/main/erpnext/README.md>
- [Q3] OpenProject · System Requirements — <https://www.openproject.org/docs/installation-and-operations/system-requirements/>
- [Q9] Ceph · Bucket Operations, einschließlich Object Lock — <https://docs.ceph.com/en/latest/radosgw/s3/bucketops/>
- [Q11] Paperless-ngx · Workflows und Objektberechtigungen — <https://docs.paperless-ngx.com/usage/>
- [Q12] BMF · E-Rechnung FAQ. UStG §§ 14 und 27 — <https://www.bundesfinanzministerium.de/Content/DE/FAQ/e-rechnung.html> — <https://www.gesetze-im-internet.de/ustg_1980/__14.html> — <https://www.gesetze-im-internet.de/ustg_1980/__27.html>
- [Q13] BMF · GoBD, Änderung vom 14. Juli 2025 — <https://www.bundesfinanzministerium.de/Content/DE/Downloads/BMF_Schreiben/Weitere_Steuerthemen/Abgabenordnung/2025-07-14-GoBD-2-aenderung.pdf?__blob=publicationFile>
- [Q14] Abgabenordnung · § 147, Ordnungsvorschriften für die Aufbewahrung — <https://www.gesetze-im-internet.de/ao_1977/__147.html>
- [Q15] BSI · TR-03138 Ersetzendes Scannen — <https://www.bsi.bund.de/SharedDocs/Downloads/DE/BSI/Publikationen/TechnischeRichtlinien/TR03138/TR-03138_V1_5.pdf?__blob=publicationFile>
