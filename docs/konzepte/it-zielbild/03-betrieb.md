# 3 Plattform und Betrieb

Arbeitsentwurf zur internen Abstimmung · Stand 20.11.2026 · SSO über Keycloak ist festgelegt. Weitere Produktauswahl und Zeiträume sind offen.

Für den ersten internen Dienst empfiehlt sich eine Linux-VM mit Docker Compose, getrennten Umgebungen und automatisierter Auslieferung. Das ist ein überschaubarer Test für Backup, Patchen, Zuständigkeiten und Rückfall. Ein geschäftskritisches ERP darf diese Plattform erst übernehmen, wenn seine vereinbarten Wiederanlaufziele nachgewiesen sind.

## Entscheidung zwischen Compose und Kubernetes

| Prüffrage | Compose auf Linux-VMs | Kubernetes mit RKE2 |
|---|---|---|
| Ein Host fällt aus | Wiederanlauf auf Ersatz-VM, Hypervisor-HA oder zweiter vorbereiteter Instanz muss separat eingerichtet und gemessen werden. | Workloads können neu eingeplant werden, wenn Quorum, Kapazität, Netz und Speicher erreichbar sind. Datenbank und Anwendung brauchen ein geeignetes Ausfallkonzept. |
| Ein Update scheitert | Vorversion mit festem Image-Digest ausrollen. Datenbankschema und Daten separat zurückführen. | Rollendes Update setzt passende Replikate, Readiness und kompatible Migration voraus. Ein altes Image allein stellt Daten nicht wieder her. |
| Eine zweite Person übernimmt | Sie baut den Dienst aus Git und Backup auf einer leeren VM wieder auf. | Sie muss zusätzlich Cluster, Zertifikate, Netzwerk, Speicher und Control Plane wiederherstellen können. |
| Was kostet der Wechsel? | VM-, Automatisierungs-, Vertretungs- und Wiederanlaufkosten erfassen. | Zusätzlichen Betrieb, Schulung, Support und Clusterupgrades gegen tatsächlich vermiedene Ausfälle und Arbeit rechnen. |

RKE2 sieht für eine hochverfügbare Installation typischerweise eine ungerade Zahl von Serverknoten vor. Drei stimmberechtigte Knoten in zwei Brandabschnitten (2+1) überstehen den Verlust des Standorts mit der Mehrheit nicht. Soll jeder Standort ausfallen dürfen, braucht es ein dafür ausgelegtes Quorum und Speicherdesign oder einen separaten Wiederanlaufstandort mit getesteter Umschaltung. Die Anzahl der Apps ist kein ausreichender Auswahlmaßstab. [Q5, Q6]

## Umgebungen und Vertrauensgrenzen

Clients greifen per HTTPS auf Portal und Fachanwendungen zu. Partner nutzen nur veröffentlichte Dienste über einen gesonderten Eingang. Entwicklungs-, Test- und Produktivsysteme haben getrennte Identitäten, Secrets und Datenbestände. Modelle, Agenten und Sandboxes gehören in eine isolierte KI-Zone. Ausschließlich der Deploymentdienst überführt einen geprüften Kandidaten in die Produktion. GPU-Server oder ein gemeinsames Containerformat begründen keinen gemeinsamen Administrationszugang.

Administrationszugriffe laufen über einen kontrollierten Managementpfad mit MFA. Backupkonten sind von Produktivkonten getrennt. Für jeden Datenfluss werden Quelle, Ziel, Protokoll, Port, Richtung, Dienstidentität und Zweck hinterlegt. Backup, Monitoring und Zertifikatsausgabe erhalten nur die benötigten Verbindungen. Für ein Cluster muss die Durchsetzung der Netzregeln praktisch belegt werden.

## Plattformvertrag für neue Anwendungen

| Nr. | Voraussetzung für die Übernahme | Abnahmebeleg |
|---|---|---|
| 01 | Gepinntes Image aus kontrollierter Quelle, Signatur und zuordenbare SBOM | Auslieferungsdienst lehnt fremdes oder ungeprüftes Artefakt ab. |
| 02 | Minimale Prozessrechte und begrenzte Schreibpfade | Laufprofil geprüft. Begründete Produktausnahme ist dokumentiert. |
| 03 | Ressourcen und Kapazitätsgrenzen | Lastprobe mit repräsentativer Datenmenge. |
| 04 | Umgebungskonfiguration und Secrets getrennt vom Image | Rotation eines Test-Secrets ohne Neubau. |
| 05 | Keycloak-SSO mit MFA und Zuordnung der Benutzer zu lokalen Rollen | Anmeldung, Abmeldung, Rollenwechsel sowie Rechteentzug gemessen. |
| 06 | Abhängigkeiten zu Verzeichnisdiensten erfasst | Servicekonten und LDAP-Sonderfälle haben Eigentümer und Ablaufplan. |
| 07 | Eigener Datenzugang je Anwendung und Umgebung | Fremder Datenbestand ist mit dem Dienstkonto nicht lesbar. |
| 08 | Betriebszustand und Bereitschaft prüfbar | Neustart und defekte Abhängigkeit sind getrennt erkennbar. |
| 09 | Protokollierung mit Zweckbindung | Logprobe ohne Passwörter, Vollprompts und unnötige Personendaten. |
| 10 | Überwachung und Alarmempfänger | Ende-zu-Ende-Test erreicht eine zuständige Person. |
| 11 | Backup und Restore einschließlich Anhängen und Schlüsseln | Fachlicher Test nach isolierter Wiederherstellung. |
| 12 | Unterstützte Version, Patch- und Rückfallweg | Fehlgeschlagenes Update in Staging zurückgeführt. |
| 13 | Vollständiger Datenexport mit Beziehungen, Historie und Rechten | Stichprobe nach unabhängigem Wiederimport. |
| 14 | Lizenz, Bezugsweg und Wartung für Produkt und Erweiterungen | Eintrag im Komponentenkatalog. |
| 15 | Fachlicher Eigentümer, technischer Betreiber und Vertretung | Übergabe samt Notfallkontakt durchgeführt. |
| 16 | Schutzbedarf, Verfügbarkeit, Fristen und Sperren | Fachbereich und Betrieb bestätigen Ziele. Offene Risiken liegen beim Risikoeigner. |

## Sicherung, Aktualisierung und Personal

Als Diskussionswerte aus der Vorlage bleiben für ERP, DMS und Keycloak einschließlich AD-Anbindung maximal 15 Minuten Datenverlust (RPO) und vier Stunden bis zur fachlichen Wiederverfügbarkeit (RTO). Für Tickets und Wiki nennt die Vorlage 24 Stunden und einen Arbeitstag, für Test und Berichte 24 Stunden und drei Arbeitstage. Fachbereich und Betrieb bestätigen oder ändern diese Werte nach einer Auswirkungsanalyse. Gemessen wird bis zum nutzbaren Geschäftsprozess einschließlich Anmeldung, Daten, Anhängen und Schnittstellen.

Eine PostgreSQL-Zeitpunktwiederherstellung erfordert ein geeignetes Basisbackup und eine durchgängige WAL-Kette. Dokumentdateien, Metadatenbank, Schlüssel und Archivregeln sind gemeinsam auf einen konsistenten Stand zu bringen. Replikation, Objektsperre und Backup haben verschiedene Aufgaben. Vorgesehene Übung: quartalsweise ein Dienst, jährlich ein Wiederanlauf einschließlich Identität und Daten. Häufigkeit und Ergebnisse werden im Betrieb festgelegt.

Monatliche Wartungsfenster und regelmäßige Image-Neubauten sind Planwerte. Bei aktiv ausgenutzten Schwachstellen bewertet der Betrieb sofort Exposition, Gegenmaßnahmen und Dringlichkeit. Major-Upgrades durchlaufen Migration und Rückfallprobe. Der Service Owner plant Kapazität für Bereitschaft, Vertretung, Schulung und gegebenenfalls bezahlten Support. Die Größe des Business-Applications-Teams allein belegt keine verfügbare Plattformbereitschaft.

## Quellen und Referenzen

- [Q5] Docker · Compose in Produktion — <https://docs.docker.com/compose/how-tos/production/>
- [Q6] RKE2 · High Availability — <https://docs.rke2.io/install/ha>
