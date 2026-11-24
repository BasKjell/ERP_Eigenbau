# V04 Konten, Service-User und Berechtigungen

Vorlagen-ID V04 · Vorlagenversion 1.0 · Stand 24.11.2026 · Entwurf zur internen Abstimmung

!!! note "Standardkopf"
    Jede ausgefüllte Systemdokumentation beginnt mit dem Standardkopf aus dem [Wegweiser](00-wegweiser.md#standardkopf-jeder-systemdokumentation).

## Zweck und Geltung

| Merkmal | Festlegung |
| --- | --- |
| Gilt für | Alle Systemtypen. Konten von Betriebssystem, Anwendung, Datenbank, Container und Plattform werden hier zusammengeführt; Details zu Datenbankkonten stehen zusätzlich in V08. |
| Ausfüllen | IT-Betrieb; Rollen der Anwendung gemeinsam mit der systemverantwortlichen Person |
| Prüfen | Identitätsmanagement und ISB |
| Zeitpunkt | Konten vor der Installation beantragen; Ist-Stand nach der Installation; Aktualisierung bei jeder Konto- oder Rechteänderung |
| Normbezug | ORP.4, OPS.1.1.2, OPS.1.2.5; ISO/IEC 27001:2022 Anhang A 5.15, 5.16, 5.17, 5.18, 8.2, 8.5, 8.18 |

[HINWEIS: In diesem Dokument stehen niemals Passwörter, private Schlüssel oder Tokens. Eingetragen wird nur der Ablageort im Secret-Manager.]

## Schritt 1: Anmeldeverfahren

| Ebene | Verfahren | Mehrfaktor | Lokale Anmeldung zulässig |
| --- | --- | --- | --- |
| Betriebssystem | {{Auswahl: lokale Konten; Verzeichnisdienst (AD/LDAP); zentrale Schlüssel bzw. Zertifikate}} | {{Verfahren}} | {{ja/nein, Begründung}} |
| Anwendung | {{Auswahl: OIDC über Keycloak; SAML; LDAP; lokale Konten}} | {{Verfahren}} | {{ja/nein, Begründung}} |
| Datenbank | {{Verfahren}} (siehe V08) | – | – |

## Schritt 2: Persönliche Administrationskonten

[HINWEIS: Keine gemeinsam genutzten Administrationskonten. Administrationskonten sind getrennt vom persönlichen Alltagskonto.]

| Konto | Person bzw. Rolle | Rechte | Mehrfaktor | Genehmigung (Ticket) | Gültig bis |
| --- | --- | --- | --- | --- | --- |
| {{Konto}} | {{Name}} | {{Rechte}} | {{ja/nein}} | {{Ticket}} | {{Datum oder „Rezertifizierung“}} |

## Schritt 3: Service-User und technische Konten

| Konto | Ort | Zweck | Rechte | Interaktive Anmeldung | Authentisierung | Ablage des Geheimnisses | Rotation | Verantwortlich |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| {{Konto}} | {{Auswahl: Betriebssystem; Verzeichnisdienst; Anwendung; Datenbank; Keycloak-Client; Plattform}} | {{Zweck}} | {{Rechte, so gering wie möglich}} | {{gesperrt / erlaubt mit Begründung}} | {{Auswahl: Passwort; Schlüssel; Zertifikat; Token}} | {{Pfad im Secret-Manager}} | {{Intervall, letzte Rotation}} | {{Name}} |

## Schritt 4: Rollen und Gruppen

| Rolle im System | Rechte | Herkunft | Mitglieder verwaltet von |
| --- | --- | --- | --- |
| {{Rolle}} | {{Rechte}} | {{zum Beispiel AD-Gruppe → Keycloak-Rolle}} | {{Stelle}} |

## Schritt 5: Notfallkonto

| Feld | Eintrag |
| --- | --- |
| Konto | {{Konto}} |
| Aufbewahrung der Zugangsdaten | {{Auswahl: Secret-Manager mit Vier-Augen-Freigabe; versiegelter Umschlag im Tresor}} |
| Nutzung wird alarmiert | {{ja/nein, Alarmweg}} |
| Letzter Test | {{Datum, Ergebnis}} |

## Schritt 6: Privilegierte Rechte im Detail

| Mechanismus | Regel bzw. Mitglied | Begründung |
| --- | --- | --- |
| {{Auswahl: sudo-Regel; lokale Administratorengruppe; Gruppe „docker“; Datenbank-Superuser; Cluster-Administration}} | {{Regel oder Konto}} | {{Begründung}} |

[HINWEIS: Mitglieder der Gruppe „docker“ haben faktisch root-Rechte auf dem Host. Diese Gruppe gehört hierher und bleibt möglichst leer.]

## Schritt 7: Fernwartung und Zugänge für Dienstleister

| Dienstleister | Zugangsweg | Freischaltung | Protokollierung bzw. Aufzeichnung | Vertrag (inkl. Auftragsverarbeitung) | Ansprechperson |
| --- | --- | --- | --- | --- | --- |
| {{Firma oder „keiner“}} | {{Weg}} | {{Auswahl: dauerhaft; nur auf Anforderung}} | {{Verfahren}} | {{Vertragsnummer}} | {{Name}} |

## Schritt 8: API-Schlüssel und Tokens

| Bezeichnung | Zweck | Berechtigungsumfang | Gültig bis | Ablage | Verantwortlich |
| --- | --- | --- | --- | --- | --- |
| {{Bezeichnung}} | {{Zweck}} | {{Scopes bzw. Rechte}} | {{Datum}} | {{Pfad im Secret-Manager}} | {{Name}} |

## Schritt 9: Rezertifizierung

| Feld | Eintrag |
| --- | --- |
| Intervall | [FIRMENANGABE V-04] |
| Letzte Rezertifizierung | {{Datum, durchgeführt von}} |
| Ergebnis | {{entzogene Konten bzw. Rechte}} |

## Schritt 10: Ist-Stand erheben

| Zweck | Linux | Windows |
| --- | --- | --- |
| Lokale Konten | `getent passwd` | `Get-LocalUser` |
| Administrative Gruppen | `getent group sudo docker` bzw. passende Gruppen | `Get-LocalGroupMember -SID S-1-5-32-544` |
| sudo-Regeln | `/etc/sudoers` und `/etc/sudoers.d/` | – |
| Rechte eines Kontos | `sudo -l -U <konto>` | `whoami /priv` als betroffenes Konto |
| Letzte Anmeldungen | `lastlog`, `last` | Sicherheitsprotokoll, Ereignis 4624 |

## Prüfpunkte

- ☐ Jedes Konto aus der Erhebung steht in Schritt 2, 3 oder 5.
- ☐ Es gibt keine gemeinsam genutzten persönlichen Konten.
- ☐ Service-User können sich nicht interaktiv anmelden, wo das technisch möglich ist.
- ☐ Kein Geheimnis steht in diesem Dokument, in Git oder in Konfigurationsdateien im Klartext.
- ☐ Standardkonten und Standardpasswörter von Betriebssystem, Anwendung und Datenbank sind entfernt bzw. geändert.
- ☐ Das Notfallkonto ist getestet und seine Nutzung wird alarmiert.

## Unternehmensweite Festlegungen

[FIRMENANGABE V-04] Identitätsmanagement und ISB legen fest:

| Festlegung | Wert | Verantwortlich |
| --- | --- | --- |
| Namenskonvention (zum Beispiel adm- für Administrations-, svc- für Service-Konten) | offen | Identitätsmanagement |
| Passwort-, Schlüssel- und Token-Richtlinie, Rotationsintervalle | offen | ISB |
| Zugelassener Secret-Manager und Pfadstruktur | offen | IT-Betrieb |
| Mehrfaktor-Pflicht je Zugangsart | offen | ISB |
| Rezertifizierungsintervall je Schutzbedarf | offen | ISB |
| Verfahren für Notfallkonten | offen | ISB |

## Ausfüllbeispiel

??? example "Ausfüllbeispiel (fiktiv)"

    | Ebene | Verfahren | Mehrfaktor | Lokale Anmeldung |
    | --- | --- | --- | --- |
    | Betriebssystem | Persönliche Konten aus dem Verzeichnisdienst, SSH-Zertifikate | MFA am Jump-Host | nur Notfallkonto |
    | Anwendung | OIDC über Keycloak, Client „flowdoc“ | ja, Keycloak | nein; lokales Admin-Konto nach Einrichtung gesperrt |
    | Datenbank | SCRAM-SHA-256, siehe V08 | – | – |

    | Konto | Person | Rechte | Mehrfaktor | Genehmigung | Gültig bis |
    | --- | --- | --- | --- | --- | --- |
    | adm-mklein | Mara Klein | sudo ohne Einschränkung | ja | REQ-2026-3310 | Rezertifizierung |
    | adm-twolf | Tim Wolf | sudo für Docker-Compose-Befehle im Projekt flowdoc | ja | REQ-2026-3311 | Rezertifizierung |

    | Konto | Ort | Zweck | Rechte | Interaktiv | Authentisierung | Ablage | Rotation | Verantwortlich |
    | --- | --- | --- | --- | --- | --- | --- | --- | --- |
    | svc-backup | Betriebssystem | Datensicherung mit restic | Lesen /srv/flowdoc, Ausführen pg_dump im Container über sudo-Regel | gesperrt (nologin) | Schlüssel für Sicherungsziel | infra/backup/dms01 | 12 Monate, zuletzt 10.11.2026 | Plattformbetrieb |
    | paperless | Datenbank | Anwendung | Eigentümer der Datenbank paperless | – | Passwort | apps/flowdoc/db | 12 Monate | Plattformbetrieb |
    | flowdoc | Keycloak-Client | OIDC-Anmeldung | nur Anmeldung | – | Client-Secret | apps/flowdoc/oidc | 12 Monate | Identitätsmanagement |
    | svc-paperless-imap | Mailserver | Abruf Postfach rechnungen@ | Lesen und Verschieben im Postfach | gesperrt | Passwort | apps/flowdoc/imap | 12 Monate | Plattformbetrieb |

    | Rolle | Rechte | Herkunft | Mitglieder verwaltet von |
    | --- | --- | --- | --- |
    | flowdoc-admin | Verwaltung von Tags, Typen, Benutzern | AD-Gruppe GG-APP-FLOWDOC-ADMIN → Keycloak-Rolle | Systemverantwortliche Person |
    | flowdoc-buchhaltung | Lesen und Bearbeiten der Belegtypen Rechnung, Gutschrift | AD-Gruppe GG-APP-FLOWDOC-FIBU | Leitung Rechnungswesen |
    | flowdoc-lesen | Lesen freigegebener Arbeitsanweisungen | AD-Gruppe GG-APP-FLOWDOC-LESEN | Fachbereiche |

    Notfallkonto: lokales Konto „breakglass“ auf dms01, Zugangsdaten im Secret-Manager mit Vier-Augen-Freigabe, Anmeldung löst Alarm im SIEM aus, Test am 14.11.2026 erfolgreich.

    Privilegierte Rechte: Gruppe „docker“ ist leer; Docker-Befehle nur über sudo-Regel für adm-twolf und adm-mklein. Kein weiterer Datenbank-Superuser außer dem Standard-Superuser, der nur lokal im Container nutzbar ist.

    Fernwartung: keine Dienstleister.

    Tokens: API-Token „erp-verweis“ für FLOWERP, nur Lesen von Dokumenten mit Tag „Beleg“, gültig bis 30.11.2027, Ablage apps/flowerp/flowdoc-token.

    Rezertifizierung: halbjährlich wegen Schutzbedarf hoch; erste Prüfung im Mai 2027.
