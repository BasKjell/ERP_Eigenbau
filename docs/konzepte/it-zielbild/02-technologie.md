# 2 Technologie und Lizenzregeln

Arbeitsentwurf zur internen Abstimmung · Stand 20.11.2026 · SSO über Keycloak ist festgelegt. Weitere Produktauswahl und Zeiträume sind offen.

Für Eigenentwicklungen stellt die IT eine gepflegte Projektvorlage bereit. Standardsoftware bleibt auf dem vom Hersteller oder der Community unterstützten Stack. Diese Trennung vermeidet zum Beispiel, dass ein geeignetes Ticketsystem allein wegen seines Ruby-Backends durch eine Eigenentwicklung ersetzt wird.

## Entwicklungsvorlage

| Gegenstand | Standardvorschlag | Nachweis im Projekt |
|---|---|---|
| Backend | Unterstützte Python-Version mit ausreichendem Pflegefenster. Django für Datenmodell, Migration, Administration und Webanwendung. FastAPI für schlanke APIs oder Adapter, wenn der Zusatznutzen benannt ist. | Versionsmatrix von Python, Framework und DB-Treiber. Updateprobe in CI. |
| Oberfläche | TypeScript und React für komplexe Bedienoberflächen. Vite erzeugt statische Dateien. Für dieses Muster läuft Node.js in der Build-Pipeline. Fertigprodukte oder serverseitiges Rendering können Node.js im Betrieb benötigen. | Bedienprobe mit Fachbereich, Tastatur, Fokus, Kontrast, Fehlermeldungen und gängigen Bildschirmgrößen. Barrierefreiheit am produktiven Ablauf prüfen. |
| Schnittstelle | Versionierte OpenAPI-Beschreibung, stabiler Fehlervertrag, generierter Client bei Bedarf. | Vertragstest zwischen mindestens einem Anbieter und Verbraucher. |
| Berechtigungen | OIDC über Keycloak für Eigenentwicklungen. Unterstützt eine Standardanwendung ausschließlich SAML 2.0 für SSO, wird sie als SAML-Client in Keycloak angebunden. Anwendungen prüfen Mandant, Rolle, Aktion und Objekt serverseitig. | Positiv- und Negativtest, einschließlich Entzug während einer Sitzung. |
| Werkzeuge | uv und Lockfile, Ruff, Typprüfung mit mypy, pytest. Vitest und Playwright für Frontend und Nutzerabläufe. Abhängigkeiten aus internem Spiegel. | Reproduzierbarer Build, SBOM, Scanbericht, Release-Digest. |
| Hintergrundarbeit | Einfache periodische Aufgaben als geplante Jobs. Bei dauerhafter Queue etwa Celery mit RabbitMQ. | Sicherer Retry und messbarer Rückstau. Derselbe Auftrag darf keine zweite Buchung erzeugen. |

## Technologieauswahl für den Betrieb

| Bereich | Einstieg | Ausbau bei belegtem Bedarf |
|---|---|---|
| Betrieb und Lieferung | Unterstütztes Linux, Compose, Git, kontrollierte Registry, automatisierte Auslieferung | RKE2, Argo CD oder Flux, Helm, Admission-Regeln und Network Policies. Clusterpflege vorab finanzieren. |
| Eingang, Zertifikate, Secrets | Vorhandenen Reverse Proxy, interne PKI und geeigneten Tresor verwenden. Ablauf und Rotation überwachen. | Traefik oder Envoy Gateway, cert-manager und OpenBao als Kandidaten. Der Community-Controller ingress-nginx hat sein Wartungsende erreicht. [Q7] |
| Datenbank und Suche | PostgreSQL, Volltext und optional pgvector. MariaDB für Produkte mit entsprechender Voraussetzung. | OpenSearch oder Qdrant nach Suchqualität, Rechteprüfung, Ausfallverhalten und Betrieb bewerten. |
| Speicher und Archiv | Vorhandenes SAN und unterstützter Objektspeicher. Speicherklassen und Archivfristen getrennt planen. | Ceph RGW als Kandidat nach Test von Versionierung, Object Lock, Restore und Personalbedarf. Das öffentliche MinIO-Repository ist archiviert. Installierte Variante und Support einzeln prüfen. [Q8, Q9] |
| Beobachtung und Sicherung | Bestehendes Monitoring wie Checkmk einbinden. Zentraler Ereignisspeicher, Schlüsselverwaltung, anwendungskonsistente Backups. | Prometheus, Grafana, Loki oder vorhandenes SIEM nur für konkrete Lücken ergänzen. Bei Kubernetes Cluster- und Datenbanksicherung getrennt planen. |
| Integration und Analyse | Python-Adapter, versionierte Verträge, eigene Berichtsdatenbank | RabbitMQ für entkoppelte Ereignisse, Superset als BI-Kandidat. Bestehende SSRS- oder Power-BI-Berichte nach fachlicher Gleichwertigkeit ablösen. |
| Code und CI | Bestehende Git-Plattform samt installierter Edition prüfen | GitLab mit benötigter Edition oder Forgejo nach lokalem Nachweis der Rechte und Integrationssperren. |

## Lizenzen und unabhängige Freigaben

Für Kernprodukt, Module, Images, Konnektoren und gegebenenfalls Modellgewichte getrennt dokumentieren: konkrete Version, Lizenz, Änderungen, Einsatzform, Empfängerkreis, Support und Export. Bei GPL/AGPL, Weitergabe an Dritte oder Zugriff weiterer Rechtseinheiten prüft die zuständige Stelle die Pflichten am tatsächlichen Lizenztext. Ein kostenloser Download belegt keine Open-Source-Lizenz. Source-available-Werkzeuge wie n8n nur einsetzen, wenn Nutzungsrechte und Ausnahme zur Beschaffungspolitik geklärt sind. [Q10]

GitLab dokumentiert Code Owners und verpflichtende Code-Owner-Freigaben für Premium und Ultimate. Im revidierten KI-Konzept ist eine menschliche Code-Owner-Prüfung für kritische Änderungen vorgesehen. Für Standardänderungen gelten ein unabhängiges Review und die genehmigten CI-Regeln. Im PoC müssen Direkt-Push, geänderte Prüflogik, veraltete Freigabe und Freigabe durch den Ersteller gesperrt sein. Für Forgejo oder einen separaten Integrationsdienst muss die gleiche Wirkung im konkreten Aufbau gezeigt werden. Eine veränderbare CI-Datei im Arbeitsbranch genügt hierfür nicht. [Q4]

Der Architekturverantwortliche führt den Technologiekatalog mit den Zuständen vorgeschlagen, im Pilot, freigegeben und auslaufend. Halbjährlich und bei Wartungsende überprüft er Verantwortung, Bezugsquelle, Patchweg, Support, lizenzierte Funktionen und Exit-Test.

## Quellen und Referenzen

- [Q4] GitLab · Code Owners und geschützte Branches — <https://docs.gitlab.com/user/project/codeowners/> — <https://docs.gitlab.com/user/project/repository/branches/protected/>
- [Q7] Kubernetes · Wartungsende des Community-Controllers ingress-nginx — <https://kubernetes.io/blog/2026/01/29/ingress-nginx-statement/>
- [Q8] MinIO · Archivstatus des öffentlichen Repositorys — <https://github.com/minio/minio>
- [Q9] Ceph · Bucket Operations, einschließlich Object Lock — <https://docs.ceph.com/en/latest/radosgw/s3/bucketops/>
- [Q10] GNU · Lizenz-FAQ zur AGPL. n8n · Produktdokumentation und Lizenzmodell — <https://www.gnu.org/licenses/gpl-faq.html> — <https://github.com/n8n-io/n8n/blob/master/LICENSE.md>
