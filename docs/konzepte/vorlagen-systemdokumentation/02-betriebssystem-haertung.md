# V02 Grundinstallation und Härtung des Betriebssystems

Vorlagen-ID V02 · Vorlagenversion 1.1 · Stand 24.11.2026 · Entwurf zur internen Abstimmung

!!! note "Standardkopf"
    Jede ausgefüllte Systemdokumentation beginnt mit dem Standardkopf aus dem [Wegweiser](00-wegweiser.md#standardkopf-jeder-systemdokumentation).

## Zweck und Geltung

| Merkmal | Festlegung |
| --- | --- |
| Gilt für | Jeden eigenen Server und jede eigene VM (Systemtypen A, B, C, E, F). Bei Typ D steht das Betriebssystem in der Plattformdokumentation. |
| Ausfüllen | Installierende Person im IT-Betrieb, während der Installation |
| Prüfen | Zweite Person aus dem Betrieb; Stichprobe durch ISB |
| Zeitpunkt | Bei Installation; Aktualisierung bei Änderung von Paketen, Diensten oder Härtung |
| Normbezug | SYS.1.1, SYS.1.3 bzw. passender Windows-Server-Baustein SYS.1.2.x, SYS.1.5 (bei VM), OPS.1.1.4, CON.1; ISO/IEC 27001:2022 Anhang A 8.5, 8.7, 8.9, 8.17, 8.19, 8.24 |

## Schritt 1: Basisdaten

| Feld | Eintrag |
| --- | --- |
| Hostname und FQDN | {{FQDN}} |
| Betriebssystem, Version, Kernel bzw. Build | {{Betriebssystem}} |
| Installationsquelle und geprüfte Prüfsumme bzw. Signatur | {{Quelle}} [HINWEIS: zum Beispiel freigegebenes VM-Template mit Name und Version oder ISO-Abbild mit SHA-256] |
| Plattform | {{Auswahl: physisch; VM}}: {{Hypervisor bzw. Plattform-ID}} |
| CPU, Arbeitsspeicher, Datenträger | {{Ausstattung}} |
| Installiert von, am | {{Name}}, {{Datum}} |
| Herstellersupport der Betriebssystemversion bis | {{Datum}} |

## Schritt 2: Speicher und Partitionen

| Einhängepunkt bzw. Laufwerk | Größe | Dateisystem | Verschlüsselt | Mount-Optionen | Zweck |
| --- | --- | --- | --- | --- | --- |
| {{Pfad}} | {{GB}} | {{Dateisystem}} | {{ja/nein}} | {{Optionen}} | {{Zweck}} |

[HINWEIS: Daten von Anwendungen, Protokollen und temporären Dateien möglichst auf eigenen Partitionen, damit ein volles Dateisystem nicht das ganze System stoppt. Für /tmp und Datenpartitionen nach Möglichkeit nodev, nosuid und noexec.]

## Schritt 3: Paketquellen und installierte Software

Paketquellen:

| Quelle | Adresse bzw. Spiegel | Signatur geprüft | Zweck |
| --- | --- | --- | --- |
| {{Name}} | {{URL}} | {{ja/nein}} | {{Zweck}} |

Zusätzlich installierte Software (alles, was über die Minimalinstallation hinausgeht):

| Software bzw. Paket | Version | Quelle | Zweck | Lizenz | Verantwortlich |
| --- | --- | --- | --- | --- | --- |
| {{Paket}} | {{Version}} | {{Quelle}} | {{Zweck}} | {{Lizenz}} | {{Name}} |

[HINWEIS: Die vollständige Paketliste wird als Anlage aus dem System erzeugt (Schritt 10). Die Tabelle enthält nur bewusst installierte Software. Grundsatz Minimalinstallation: keine Compiler, Entwicklungswerkzeuge oder grafischen Oberflächen auf Produktivservern ohne Begründung.]

## Schritt 4: Dienste

Laufende und beim Start aktivierte Dienste:

| Dienst | Startart | Zweck | Lauscht auf Port (siehe V03) | Begründung |
| --- | --- | --- | --- | --- |
| {{Dienst}} | {{Auswahl: automatisch; manuell; per Timer}} | {{Zweck}} | {{Port oder „keiner“}} | {{Begründung}} |

Bewusst deaktivierte oder entfernte Dienste: {{Liste}}

## Schritt 5: Härtung

| Feld | Eintrag |
| --- | --- |
| Verwendete Härtungsvorgabe | [FIRMENANGABE V-02] {{Name und Version der Vorgabe}} |
| Prüfwerkzeug und Ergebnis | {{Werkzeug, Datum, Ergebnis}} [HINWEIS: zum Beispiel OpenSCAP-Bericht oder CIS-Prüfbericht als Anlage] |

Abweichungen von der Härtungsvorgabe:

| Regel | Abweichung | Begründung | Risiko akzeptiert von |
| --- | --- | --- | --- |
| {{Regel-ID}} | {{Abweichung}} | {{Begründung}} | {{Name, Datum}} |

Härtung unter Linux:

[HINWEIS: Beschreiben, wie das im System umgesetzt bzw. erledigt ist; Abweichungen mit Begründung. Typische Punkte: Anmeldung als root über SSH ist abgeschaltet; SSH-Anmeldung nur mit Schlüssel oder Zertifikat; Passwortanmeldung ist abgeschaltet; Administrative Rechte nur über sudo mit persönlichen Konten; sudo wird protokolliert; SELinux oder AppArmor ist aktiv und erzwingend; Host-Firewall ist aktiv, eingehend standardmäßig gesperrt (Regeln in V03); auditd bzw. gleichwertige Protokollierung ist aktiv (siehe V09); Kernelparameter nach Härtungsvorgabe gesetzt; Nicht benötigte Dienste und Pakete sind entfernt.]

{{Beschreibung}}

Härtung unter Windows Server:

[HINWEIS: Beschreiben, wie das im System umgesetzt bzw. erledigt ist; Abweichungen mit Begründung. Typische Punkte: Installation als Server Core, wo die Anwendung das zulässt; SMBv1 ist deaktiviert; Remotedesktop nur über Jump-Host bzw. Gateway und mit Authentifizierung auf Netzwerkebene; Lokales Administratorkennwort wird über Windows LAPS verwaltet; Windows-Firewall ist in allen Profilen aktiv; Erweiterte Überwachungsrichtlinie ist nach Vorgabe gesetzt (siehe V09).]

{{Beschreibung}}

## Schritt 6: Zeit, Namensauflösung und Basisdienste

| Dienst | Konfiguration |
| --- | --- |
| Zeitsynchronisation | {{Zeitserver}} |
| DNS-Resolver | {{Resolver}} |
| Proxy für ausgehende Verbindungen | {{Proxy oder „keiner“}} |
| Mail-Relay für Systemmeldungen | {{Relay oder „keiner“}} |

## Schritt 7: Schutz vor Schadprogrammen

| Feld | Eintrag |
| --- | --- |
| Produkt (Virenschutz bzw. EDR) | {{Produkt, Version}} |
| Zentrale Verwaltung | {{Konsole}} |
| Ausnahmen | {{Pfade oder Prozesse mit Begründung}} |
| Begründung, falls kein Produkt eingesetzt wird | {{Begründung}} [HINWEIS: bei Linux-Servern zulässig, wenn die Risikobetrachtung das trägt und Härtung, Protokollierung und Integritätsprüfung gleichwertig schützen] |

## Schritt 8: Verschlüsselung der Datenträger

| Feld | Eintrag |
| --- | --- |
| Verfahren | {{Auswahl: LUKS; BitLocker; Verschlüsselung durch Plattform; keine}} |
| Entsperrung beim Start | {{Auswahl: TPM; Netzwerk-Entsperrung; manuell}} |
| Ablage des Wiederherstellungsschlüssels | {{Verweis auf Secret-Manager oder Tresor, niemals der Schlüssel selbst}} |

## Schritt 9: Fernadministration

| Feld | Eintrag |
| --- | --- |
| Zugangsweg | {{Auswahl: SSH über Jump-Host; RDP über Gateway; Konsole der Plattform}} |
| Mehrfaktor-Anmeldung | {{Verfahren}} |
| Erlaubte Quellnetze | {{Netze}} (siehe V03) |

## Schritt 10: Ist-Stand erheben

| Zweck | Linux | Windows |
| --- | --- | --- |
| Betriebssystem und Version | `cat /etc/os-release`, `uname -r` | `Get-ComputerInfo` |
| Installierte Pakete | `dpkg-query -W` bzw. `rpm -qa` | `Get-Package` |
| Laufende Dienste | `systemctl list-units --type=service --state=running` | `Get-Service` mit Filter auf laufende Dienste |
| Beim Start aktivierte Dienste | `systemctl list-unit-files --state=enabled` | `Get-Service` mit Filter auf Starttyp automatisch |
| Partitionen und Verschlüsselung | `lsblk -f`, `findmnt` | `Get-Volume`, `manage-bde -status` |
| SSH-Konfiguration | `sshd -T` | – |
| Zeitsynchronisation | `timedatectl`, `chronyc tracking` | `w32tm /query /status` |

Die Ausgaben werden mit Datum als Anlage „{{System-ID}}-V02-Anlage-{{Datum}}“ abgelegt.

## Unternehmensweite Festlegungen

[FIRMENANGABE V-02] IT-Betrieb und ISB legen fest:

| Festlegung | Wert | Verantwortlich |
| --- | --- | --- |
| Härtungsvorgabe je Betriebssystem (zum Beispiel CIS Benchmark Level 1 oder eigene Basis) | offen | ISB |
| Zugelassene Betriebssysteme und freigegebene Templates bzw. Abbilder | offen | IT-Betrieb |
| Zugelassene Paketquellen und interne Spiegel | offen | IT-Betrieb |
| Vorgabe für Virenschutz bzw. EDR je Betriebssystem | offen | ISB |
| Pflicht zur Datenträgerverschlüsselung je Schutzbedarf | offen | ISB |

## Ausfüllbeispiel

??? example "Ausfüllbeispiel (fiktiv)"

    | Feld | Eintrag |
    | --- | --- |
    | Hostname und FQDN | dms01, dms01.flowcorp.example |
    | Betriebssystem | Debian 13, Kernel 6.12 |
    | Installationsquelle | VM-Template „debian13-base“ Version 2026.10, freigegeben unter CHG-2026-0951 |
    | Plattform | VM auf VIRT-01 (PLT-0003) |
    | Ausstattung | 4 vCPU, 16 GB RAM, 40 GB System, 500 GB Daten |
    | Installiert von, am | Mara Klein, 10.11.2026 |
    | Herstellersupport bis | Debian 13 regulär bis voraussichtlich 2028, LTS danach; Prüfung in V11 |

    | Einhängepunkt | Größe | Dateisystem | Verschlüsselt | Mount-Optionen | Zweck |
    | --- | --- | --- | --- | --- | --- |
    | / | 20 GB | ext4 | ja (LUKS) | Standard | System |
    | /var/log | 10 GB | ext4 | ja | nodev, nosuid, noexec | Protokolle |
    | /tmp | 2 GB | tmpfs | – | nodev, nosuid, noexec | Temporär |
    | /srv/flowdoc | 500 GB | ext4 | ja | nodev, nosuid | Docker-Volumes und Dokumente |

    | Quelle | Adresse | Signatur geprüft | Zweck |
    | --- | --- | --- | --- |
    | Debian (Spiegel) | repo.flowcorp.example/debian | ja | Betriebssystem |
    | Docker CE (Spiegel) | repo.flowcorp.example/docker | ja | Container-Laufzeit |

    | Software | Version | Quelle | Zweck | Lizenz | Verantwortlich |
    | --- | --- | --- | --- | --- | --- |
    | docker-ce, docker-compose-plugin | laut Paketliste | Docker CE | Container-Laufzeit | Apache-2.0 | Plattformbetrieb |
    | prometheus-node-exporter | laut Paketliste | Debian | Monitoring | Apache-2.0 | Plattformbetrieb |
    | restic | laut Paketliste | Debian | Datensicherung | BSD-2-Clause | Plattformbetrieb |
    | EDR-Agent | laut Herstellerkonsole | Hersteller | Schutz vor Schadprogrammen | kommerziell | IT-Sicherheit |

    | Dienst | Startart | Zweck | Port | Begründung |
    | --- | --- | --- | --- | --- |
    | ssh | automatisch | Administration | 22/tcp | nur Management-Netz |
    | docker | automatisch | Container-Laufzeit | keiner direkt | Anwendung |
    | prometheus-node-exporter | automatisch | Metriken | 9100/tcp | nur Monitoring-Server |
    | auditd, rsyslog, chrony | automatisch | Protokollierung, Zeit | keiner | Pflicht |

    Deaktiviert: avahi-daemon, cups, rpcbind (nicht installiert).

    Härtungsvorgabe: CIS Debian Linux Benchmark Level 1 Server in der Fassung der Firmenvorgabe; OpenSCAP-Bericht vom 11.11.2026, 3 Abweichungen. Beispiel einer Abweichung: Regel „separate Partition /var/tmp“ nicht umgesetzt, Begründung „über tmpfs-Bindung gelöst“, akzeptiert von Mara Klein am 11.11.2026.

    Zeit: ntp1.flowcorp.example, ntp2.flowcorp.example. DNS: 10.20.10.53, 10.20.10.54. Proxy: proxy.flowcorp.example:3128. Mail-Relay: smtp-relay.flowcorp.example.

    Verschlüsselung: LUKS, Entsperrung über Netzwerk-Entsperrung (Tang/Clevis), Wiederherstellungsschlüssel im Secret-Manager unter „infra/luks/dms01“.

    Fernadministration: SSH nur über jump01.flowcorp.example mit Schlüssel und MFA am Jump-Host; Quellnetz Management-Zone.
