# V03 Netz, Ports und Firewall

Vorlagen-ID V03 · Vorlagenversion 1.0 · Stand 24.11.2026 · Entwurf zur internen Abstimmung

!!! note "Standardkopf"
    Jede ausgefüllte Systemdokumentation beginnt mit dem Standardkopf aus dem [Wegweiser](00-wegweiser.md#standardkopf-jeder-systemdokumentation).

## Zweck und Geltung

| Merkmal | Festlegung |
| --- | --- |
| Gilt für | Alle Systemtypen. Bei Typ D nur die Ports, Freigaben und Zertifikate der Anwendung; Knoten und Cluster stehen in der Plattformdokumentation. |
| Ausfüllen | IT-Betrieb; Firewall-Freigaben gemeinsam mit dem Netzwerkteam |
| Prüfen | Netzwerkteam und ISB |
| Zeitpunkt | Anträge vor der Installation; Ist-Stand nach der Installation; Aktualisierung bei jeder Port- oder Regeländerung |
| Normbezug | NET.1.1, NET.1.2, NET.3.2, CON.1; ISO/IEC 27001:2022 Anhang A 8.20, 8.21, 8.22, 8.24 |

## Schritt 1: Netzanbindung

| Schnittstelle | IP-Adresse und Präfix | VLAN | Netzzone | Gateway | Zweck |
| --- | --- | --- | --- | --- | --- |
| {{Schnittstelle}} | {{IP/Präfix}} | {{VLAN}} | {{Zone nach [FIRMENANGABE V-03]}} | {{Gateway}} | {{Auswahl: Anwendung; Management; Sicherung; Speicher}} |

DNS-Einträge:

| Name | Typ | Ziel |
| --- | --- | --- |
| {{Name}} | {{Auswahl: A; AAAA; CNAME; PTR}} | {{Ziel}} |

## Schritt 2: Offene Ports

[HINWEIS: Jeden Port eintragen, auf dem das System lauscht, auch wenn er nur lokal erreichbar ist. Dienste nur an die Adresse binden, über die sie gebraucht werden. Administrationsdienste nur aus der Management-Zone erreichbar machen.]

| Port/Protokoll | Gebunden an | Dienst bzw. Prozess | Zweck | Erreichbar aus | Verschlüsselung | Authentisierung | Begründung |
| --- | --- | --- | --- | --- | --- | --- | --- |
| {{Port/tcp oder udp}} | {{Adresse}} | {{Prozess}} | {{Zweck}} | {{Zone bzw. Quelle}} | {{Auswahl: TLS 1.3; TLS 1.2; SSH; keine}} | {{Verfahren}} | {{Begründung}} |

## Schritt 3: Host-Firewall

| Feld | Eintrag |
| --- | --- |
| Produkt | {{Auswahl: nftables; firewalld; ufw; Windows Defender Firewall}} |
| Standardregel eingehend | {{Auswahl: sperren; erlauben}} |
| Standardregel ausgehend | {{Auswahl: sperren; erlauben}} |
| Ablage der Regeln | {{Git-Pfad oder Konfigurationsmanagement}} |

| Richtung | Quelle | Ziel-Port/Protokoll | Aktion | Zweck |
| --- | --- | --- | --- | --- |
| {{Auswahl: eingehend; ausgehend}} | {{Quelle}} | {{Port/Protokoll}} | {{Auswahl: erlauben; sperren}} | {{Zweck}} |

## Schritt 4: Freigaben an der Netzwerk-Firewall

[HINWEIS: Jede Freigabe hat eine Antrags- bzw. Change-Nummer. Vorübergehende Freigaben werden befristet.]

| Change-Nr. | Quelle | Ziel | Port/Protokoll | Richtung | Zweck | Befristet bis | Genehmigt von |
| --- | --- | --- | --- | --- | --- | --- | --- |
| {{Change-Nr.}} | {{Zone oder Adresse}} | {{Zone oder Adresse}} | {{Port/Protokoll}} | {{Auswahl: eingehend; ausgehend}} | {{Zweck}} | {{Datum oder „unbefristet“}} | {{Name}} |

## Schritt 5: Ausgehende Verbindungen

[HINWEIS: Ausgehend gilt nach [FIRMENANGABE V-03] grundsätzlich „nur was nötig ist“. Hier alle Ziele eintragen, die das System erreichen muss: Updates, Registry, Zeit, Protokollierung, Sicherung, Anmeldung, externe Schnittstellen.]

| Ziel | Port/Protokoll | Zweck | Über Proxy | Freigabe (Change-Nr.) |
| --- | --- | --- | --- | --- |
| {{Ziel}} | {{Port/Protokoll}} | {{Zweck}} | {{ja/nein}} | {{Change-Nr.}} |

## Schritt 6: Zertifikate und TLS

| Zertifikat (Name bzw. SAN) | Aussteller | Gültig bis | Automatische Erneuerung | Ablage privater Schlüssel | Überwachung des Ablaufs |
| --- | --- | --- | --- | --- | --- |
| {{Name}} | {{Auswahl: interne CA; ACME; öffentliche CA}} | {{Datum}} | {{ja/nein, Verfahren}} | {{Verweis, niemals der Schlüssel}} | {{ja, siehe V09}} |

| Feld | Eintrag |
| --- | --- |
| Mindestens zugelassene TLS-Version | [FIRMENANGABE V-03] {{Version}} [HINWEIS: Orientierung bietet die BSI TR-02102-2] |
| Unverschlüsselte Dienste und Begründung | {{Liste oder „keine“}} |

## Schritt 7: Vorgeschaltete Komponenten

| Komponente | Funktion | Konfiguration bzw. Regel-ID |
| --- | --- | --- |
| {{Auswahl: Reverse Proxy; Load Balancer; Web Application Firewall; VPN}} | {{Funktion}} | {{Verweis}} |

## Schritt 8: Ist-Stand erheben und prüfen

| Zweck | Linux | Windows |
| --- | --- | --- |
| Adressen und Routen | `ip -br addr`, `ip route` | `Get-NetIPAddress`, `Get-NetRoute` |
| Lauschende Ports mit Prozess | `ss -tulpn` | `Get-NetTCPConnection -State Listen`, `Get-NetUDPEndpoint` |
| Host-Firewall | `nft list ruleset` bzw. `firewall-cmd --list-all-zones` | `Get-NetFirewallRule -Enabled True` |
| Zertifikat eines Dienstes | `openssl s_client -connect <host>:443 -servername <host>` | gleich, mit installiertem OpenSSL |

Zusätzlich prüft das Netzwerkteam von außen mit einem Portscan aus der Clientzone und aus der Management-Zone, ob genau die Ports aus Schritt 2 erreichbar sind. Portscans nur mit Freigabe nach [FIRMENANGABE V-03].

## Prüfpunkte

- ☐ Jeder lauschende Port aus der Erhebung steht in Schritt 2, keiner ist ohne Begründung.
- ☐ Administrationsdienste sind nicht aus der Clientzone erreichbar.
- ☐ Das Ergebnis des Portscans stimmt mit Schritt 2 überein.
- ☐ Jede Netzwerk-Freigabe hat eine Change-Nummer; vorübergehende sind befristet.
- ☐ Ausgehende Verbindungen sind auf die Ziele aus Schritt 5 beschränkt.
- ☐ Alle Zertifikate werden auf Ablauf überwacht.

## Unternehmensweite Festlegungen

[FIRMENANGABE V-03] Netzwerkteam und ISB legen fest:

| Festlegung | Wert | Verantwortlich |
| --- | --- | --- |
| Netzzonenmodell mit erlaubten Verbindungen zwischen Zonen | offen | Netzwerkteam |
| Antragsweg für Firewall-Freigaben und Höchstdauer befristeter Freigaben | offen | Netzwerkteam |
| Regel für ausgehende Verbindungen (Standard sperren, Proxy-Pflicht) | offen | ISB |
| Mindest-TLS-Version und zugelassene Verfahren | offen | ISB |
| Interne Zertifizierungsstelle bzw. ACME-Dienst | offen | IT-Betrieb |
| Freigabe von Portscans und Schwachstellenscans | offen | ISB |

## Ausfüllbeispiel

??? example "Ausfüllbeispiel (fiktiv)"

    | Schnittstelle | IP-Adresse | VLAN | Netzzone | Gateway | Zweck |
    | --- | --- | --- | --- | --- | --- |
    | ens192 | 10.20.120.15/24 | 120 | Server-Zone Anwendungen | 10.20.120.1 | Anwendung |
    | ens224 | 10.20.10.15/24 | 10 | Management-Zone | – | Management |

    DNS: dms01.flowcorp.example A 10.20.120.15; flowdoc.flowcorp.example CNAME dms01.flowcorp.example; PTR für beide Adressen.

    | Port/Protokoll | Gebunden an | Dienst | Zweck | Erreichbar aus | Verschlüsselung | Authentisierung | Begründung |
    | --- | --- | --- | --- | --- | --- | --- | --- |
    | 443/tcp | 10.20.120.15 | nginx (Container) | Weboberfläche und API | Clientzone, Server-Zone ERP | TLS 1.3, TLS 1.2 | OIDC über Keycloak | Zugriff der Beschäftigten und des ERP |
    | 80/tcp | 10.20.120.15 | nginx (Container) | Weiterleitung auf 443 | Clientzone | keine | keine | Nur Umleitung, keine Inhalte |
    | 22/tcp | 10.20.10.15 | sshd | Administration | Jump-Host jump01 | SSH | Schlüssel, MFA am Jump-Host | Betrieb |
    | 9100/tcp | 10.20.10.15 | node_exporter | Metriken | Monitoring-Server mon01 | keine | keine | Nur aus Management-Zone; enthält keine Inhaltsdaten |
    | 8000/tcp | Docker-Netz flowdoc_internal | Paperless-ngx | Anwendung hinter nginx | nur nginx-Container | keine (internes Netz) | – | Nicht veröffentlicht |
    | 5432/tcp | Docker-Netz flowdoc_internal | PostgreSQL | Datenbank | nur Paperless-Container | TLS | SCRAM-SHA-256 | Nicht veröffentlicht |
    | 6379/tcp | Docker-Netz flowdoc_internal | Valkey | Nachrichtenpuffer | nur Paperless-Container | keine | Passwort | Nicht veröffentlicht |

    Host-Firewall: nftables, eingehend sperren, ausgehend sperren; Regeln in Git unter infra/hosts/dms01/nftables.conf. Weil Docker veröffentlichte Ports an eigenen Regeln vorbei freigibt, sind Ports nur an 10.20.120.15 gebunden und zusätzlich in der Kette DOCKER-USER beschränkt.

    | Change-Nr. | Quelle | Ziel | Port | Richtung | Zweck | Befristet bis | Genehmigt von |
    | --- | --- | --- | --- | --- | --- | --- | --- |
    | CHG-2026-1187 | Clientzone | 10.20.120.15 | 443/tcp, 80/tcp | eingehend | Weboberfläche | unbefristet | Netzwerkteam, T. Wolf |
    | CHG-2026-1187 | Server-Zone ERP | 10.20.120.15 | 443/tcp | eingehend | ERP-Verweise | unbefristet | Netzwerkteam, T. Wolf |
    | CHG-2026-1192 | Migrationsserver mig01 | 10.20.120.15 | 443/tcp | eingehend | Übernahme des Altbestands | 30.11.2026 | Netzwerkteam, T. Wolf |

    | Ziel | Port | Zweck | Über Proxy | Freigabe |
    | --- | --- | --- | --- | --- |
    | repo.flowcorp.example | 443/tcp | Paketquellen | nein (intern) | Standardregel |
    | registry.flowcorp.example | 443/tcp | Container-Images | nein (intern) | Standardregel |
    | ntp1, ntp2.flowcorp.example | 123/udp | Zeit | nein | Standardregel |
    | log.flowcorp.example | 6514/tcp | Protokolle per Syslog über TLS | nein | Standardregel |
    | backup-s3.flowcorp.example | 443/tcp | Datensicherung | nein | CHG-2026-1188 |
    | sso.flowcorp.example | 443/tcp | Anmeldung OIDC | nein | Standardregel |
    | mail.flowcorp.example | 993/tcp | Belegabruf per IMAPS | nein | CHG-2026-1189 |

    | Zertifikat | Aussteller | Gültig bis | Erneuerung | Ablage Schlüssel | Überwachung |
    | --- | --- | --- | --- | --- | --- |
    | flowdoc.flowcorp.example | interne CA über ACME | 18.02.2027 | automatisch alle 60 Tage | Docker-Volume flowdoc_certs, Zugriff nur nginx | ja, Warnung 21 Tage vor Ablauf |

    Mindest-TLS-Version 1.2; unverschlüsselt nur Port 80 als Umleitung und node_exporter in der Management-Zone.

    Portscan am 19.11.2026 aus Clientzone: offen 80, 443; aus Management-Zone: offen 22, 9100. Stimmt mit der Tabelle überein.
