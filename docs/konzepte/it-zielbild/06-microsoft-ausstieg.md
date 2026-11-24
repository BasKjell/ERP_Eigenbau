# 6 Microsoft-Abhängigkeiten schrittweise abbauen

Arbeitsentwurf zur internen Abstimmung · Stand 20.11.2026 · SSO über Keycloak ist festgelegt. Weitere Produktauswahl und Zeiträume sind offen.

Ein Geschäftsvorgang ist erst entkoppelt, wenn die zuständige Person ihn auf der Zielumgebung vollständig bearbeiten kann. Eine Browseranwendung kann weiterhin von AD, SQL Server, Excel-VBA, Office-Vorlagen oder einem Windows-Druckertreiber abhängen. Die Inventur erfasst daher komplette Arbeitsabläufe einschließlich Zulieferern, Kunden und Fachgeräten.

## Fünf Etappen

| Etappe | Arbeit und Verantwortung | Nachweis für die Ablösung |
|---|---|---|
| 1 · Server und Daten | IT-Betrieb bevorzugt Linux für neue Dienste. Windows- und SQL-Server einzeln nach Herstellerfreigabe, Reporting und Wartungsende bewerten. | Restore und fachlicher Wiederanlauf unter Linux. Für verbleibende Instanzen gibt es Kosten, Eigentümer und nächste Entscheidung. |
| 2 · Business Applications | Fachbereiche priorisieren Access-Dateien, VBA, Office-Add-ins, Outlook-Regeln, MS-Project-Abhängigkeiten und Desktopprogramme. Zuerst einen überschaubaren Prozess migrieren. | Ein vollständiger Geschäftsvorgang einschließlich Ausgabe, Unterschrift oder Drucker funktioniert im Pilot. |
| 3 · Identität | IAM-Team bindet geeignete Anwendungen über OIDC oder SAML an Keycloak an. Es inventarisiert getrennt LDAP, Kerberos, GPOs, PKI, Dateirechte, SID-Bezüge und Dienstkonten. | Bei Wechsel von Rolle oder Verzeichnis bleiben fachliche Rechte korrekt. Entzug wirkt innerhalb der vereinbarten Frist. |
| 4 · Zusammenarbeit | Dateien, Office, Chat und Mail getrennt bewerten. Freigegebene Unternehmensvorlagen, Änderungsverfolgung, Seriendruck, Kalenderdelegation, Mobilgeräte und externe Einladungen mit Pilotgruppe testen. | Fachbereiche und konkrete externe Partner können Testfälle bearbeiten. Datenexport, Aufbewahrung und Rückfall sind erprobt. |
| 5 · Arbeitsplätze | Linux für geeignete Nutzerprofile pilotieren. Windows für CAD, Maschinen, proprietäre Treiber oder Vertragsvorgaben als begründete Ausnahme führen. | Verschlüsselung, Updates, Fernhilfe, Geräteverwaltung und Peripherie im Tagesbetrieb nachgewiesen. |

Die Architekturregel „keine neuen vermeidbaren Microsoft-Abhängigkeiten“ wird nach interner Entscheidung in die Beschaffung aufgenommen. Für jede Ausnahme werden fachlicher Zwang, Mehrkosten, Alternativen, Laufzeit und verantwortliche Person dokumentiert. Bestehende Vorhaben wie BI oder MS-Project-Anbindung werden anhand desselben Maßstabs bewertet. Linux und PostgreSQL können produktiv genutzt werden, während AD und Windows-Clients weiterbestehen.

## Was bei der Ablösung des AD zu prüfen ist

Keycloak entkoppelt die Anwendungsanmeldung vom Verzeichnis. Beim späteren Austausch des AD sind Benutzerzuordnung und Gruppenabbildung in Keycloak sowie der Zugriff auf bereits zugeordnete Objekte im Fachsystem zu testen. Eine Ablösung der Windows-Domäne umfasst zusätzlich Gerätebeitritt, Gruppenrichtlinien, Namensauflösung, Zertifikate, Netzlaufwerke und technische Konten. Zuerst die Anwendungen entkoppeln und die verbleibenden Bindungen testen. AD weiterbetreiben, einen kompatiblen Verzeichnisdienst prüfen oder eine Linux-orientierte Verwaltung einführen sind unterschiedliche Optionen. Eine Testdomäne samt deaktivierter Person und wiederhergestelltem Backup macht den Aufwand sichtbar.

## Praxisprobe am Arbeitsplatz

Eine Pilotperson öffnet eine externe Office-Datei, bearbeitet sie mit Änderungsverfolgung, verwendet die echte Unternehmensvorlage, exportiert PDF, übergibt das Ergebnis an einen Kunden und nimmt an dessen Besprechung teil. Im Lager umfasst die Probe Scanner, Etiketten und Druckpfad. Fehler und Zeitaufwand werden mit der vorhandenen Lösung verglichen. Ein zentral bereitgestelltes Windows-Programm kann als Übergang dienen. Lizenzen und Betriebsaufwand dafür gehören in die Kalkulation.

Schleswig-Holsteins Projekt Linux+1 und openDesk liefern Vergleichsansätze für Arbeitsplätze und Zusammenarbeit. Eigene Fristen und Einsparungen werden aus den getesteten Nutzerprofilen abgeleitet. Ablaufende Verträge dürfen erst nach Abnahme, gesichertem Altdatenzugriff und vereinbartem Rückfall gekündigt werden. [Q16]

## Quellen und Referenzen

- [Q16] Land Schleswig-Holstein · Linux+1. ZenDiS · openDesk — <https://www.schleswig-holstein.de/DE/landesregierung/themen/digitalisierung/linux-plus1/Projekt/projekt_node.html> — <https://www.opendesk.eu/de>
