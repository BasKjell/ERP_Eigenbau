# 02 KI-Einsatz, Agentenregister und Freigaben

Arbeitsreferenz KI-U-02 · Stand 20.11.2026 · Arbeitsentwurf zur internen Abstimmung

## Vom Verbesserungsvorschlag zur Einsatzentscheidung

Jeder produktive Einsatz besitzt eine Use-Case-ID, einen fachlichen Eigentümer und ein Ablaufdatum zur Überprüfung. Das gilt auch für zugekaufte Anwendungen mit eingebauten KI-Funktionen. Der Fachbereich erfasst den Vorschlag als Ticket in FLOWTASK [FIRMENANGABE U-02]: Zweck, Personengruppen, Ein- und Ausgaben, Datenquellen, Empfänger, mögliche Fehlerfolgen, manuelle Alternative, gewünschte Stufe und erwarteter Nutzen. Das Plattformteam ergänzt Modell-, Werkzeug- und Prozessversion. Ändern sich Zweck, Daten, Modell oder Rechte, wird die Einsatzentscheidung erneut geprüft.

| Stufe | Was der Agent tun darf | Mensch und technische Grenze |
| --- | --- | --- |
| A0 Erklären | Berechtigte Informationen lesen, zusammenfassen und Quellen verlinken | Quellenverweis und Zugriffskontrolle. Die Person beurteilt das Ergebnis. |
| A1 Vorbereiten | Entwurf oder Entscheidungsvorlage im Arbeitsbereich vorbereiten | Der fachliche Vorgang bleibt unverändert. Die Person kann korrigieren oder verwerfen. |
| A2 Bestätigt ausführen | Eine ausdrücklich zugelassene Änderung nach Bestätigung ausführen | Person, konkrete Nutzdaten, Ziel, Frist und Version werden gemeinsam an die Bestätigung gebunden. |
| A3 Begrenzt automatisieren | Vorab genehmigte, umkehrbare Routine in einem festen Bereich ausführen | Mengengrenze, Abschaltung, Überwachung, Stichprobe, manuelle Ersatzbearbeitung und erneute Befristung. |
| A4 Menschliche Verantwortung | Keine Ausführung durch den Agenten; er darf nur nach A0 oder A1 zuarbeiten | Beziehung, Signatur, Haftung und Grundsatzentscheidungen bleiben beim Menschen. |

Die Stufen entsprechen dem Agentenregister der Referenzumgebung. Sie ordnen die Bedienung. Die rechtliche Einstufung und die Einstufung einer Softwareänderung nach Projektklasse und Kritikalität aus dem Konzept KI-Softwareentwicklung nach dem V-Modell werden in eigenen Feldern geführt. A0 kann hochsensible Informationen betreffen. A2 kann für einen ERP-Entwurf angemessen sein, obwohl die spätere Bestellung eine gesonderte Zeichnungsbefugnis erfordert.

## Das Agentenregister

Das Register ist die verbindliche Liste aller Agenten. Es liegt als versionierte Konfiguration im Git (Teil 06) und wird in FLOWMANAGE angezeigt. Ein Agent, der nicht im Register steht oder dessen Eintrag abgelaufen ist, bekommt kein Werkzeug.

| Pflichtfeld | Inhalt |
| --- | --- |
| Agent und Owner | ID, Name, fachlicher Owner mit Vertretung |
| Stufe | Freigegebene Stufe je Werkzeug, Ablaufdatum der Freigabe |
| Erlaubt | Konkrete Tätigkeiten und Werkzeuge, Datenklassen, Mengen- und Zeitgrenzen |
| Eskalation | Fälle, die in die Entscheidungs-Inbox gehen |
| Nachweis | Was je Lauf festgehalten wird |

Startbestand aus der Referenzumgebung (Vorschlag, Freigabe offen):

| Agent | Owner | Stufe | Erlaubt | Eskalation | Nachweis |
| --- | --- | --- | --- | --- | --- |
| AG-SUPPLIER Lieferanten-Agent | Leitung Einkauf | A2 | Risiken erkennen, Anfrage entwerfen, bestätigte Erinnerung senden | Terminabweichung, Vertragsfrage oder Preisänderung | Quelle, Werkzeugaufruf, Freigabe und Ergebnis |
| AG-ENGINEERING Engineering-Agent | Leitung Entwicklung | A1 | Code, Tests, Dokumentation und Nachverfolgung vorbereiten | Architektur, Security, Safety, Anforderung oder Release | Anforderung, Diff, Testergebnis und Review |
| AG-PLANNING Planungs-Agent | Leitung Operations | A2 | Szenarien rechnen und bestätigte Umplanung übertragen | Kundentermin, Überlast oder Materialkonflikt | Ausgangsdaten, Annahmen, Entscheidung und Wirkung |
| AG-QUALITY Qualitäts-Agent | Leitung Qualität | A1 | Prüfkontext sammeln und Entscheidung vorbereiten | Abweichung, Freigabe, Reklamation oder Safety-Bezug | Prüfplan, Messwert, Messmittel und Signatur |

Der Lieferanten-Agent sendet in der Stufe A2 eine Erinnerung an einen Lieferanten. Das ist externe Kommunikation; sie braucht vor dem Pilot eine eigene Prüfung von Empfängerkreis, Vorlage und Absenderidentität.

## Prüfweg und Entscheidungsrechte

Die Prozessverantwortliche beschreibt Schäden durch falsche Antwort, Offenlegung, Diskriminierung, unerlaubte Aktion und Betriebsstillstand. Eintritt und Auswirkung werden nach der vorhandenen ISMS-Methode bewertet. Die Datenverantwortliche prüft Zugang und Empfänger. ISB und Plattformbetrieb bewerten Schutzmaßnahmen und Restrisiko. Datenschutz und Recht prüfen Zweck, Rechtsgrundlage, Informationspflichten, gegebenenfalls eine Datenschutz-Folgenabschätzung (DSFA), die Rolle nach KI-Verordnung und einschlägige Verbote oder besondere Pflichten. Der Betriebsrat wird einbezogen, wenn Mitbestimmungsrechte berührt sind. Für Betroffene ist eine erreichbare Stelle für Widerspruch, Korrektur und menschliche Prüfung festzulegen. Automatische Personalentscheidungen, Leistungsprofile, sicherheitsbezogene Produktentscheidungen und verbindliche externe Zusagen sind aus dem ersten Rollout ausgenommen.

Status im Register: Idee, bewertet, Testbetrieb, befristet produktiv, pausiert, stillgelegt. Die Einsatzentscheidung nennt Geltungsbereich, freigegebene Stufe, Bedingungen und Ablaufdatum. Der technische Betrieb aktiviert ausschließlich diese Kombination. Für A3 entscheidet eine befugte Stelle erst nach dem Nachweis, dass auch bei Ausfall ein beherrschter Zustand eintritt. Eine höhere Stufe erfordert eine neue Entscheidung. Fehlende Nachweise oder ein unklarer Rechtsstatus lassen den Fall im Test mit zulässigen Daten.

## Nutzungsregel für Beschäftigte

Geschäftliche KI-Aufgaben werden nur über FLOWPORTAL und FLOWAI und im freigegebenen Datenraum erledigt. Vor der Übernahme in einen Geschäftsbeleg prüft die Person Inhalt, Quelle und Empfänger. Vertrauliche Inhalte, Zugangsdaten und personenbezogene Falldaten dürfen nur im ausdrücklich dafür freigegebenen Verfahren verarbeitet werden. Für Geheimnisse gilt der Tresorweg. Wer eine neue KI-Funktion braucht oder eine ungeplante Nutzung entdeckt, meldet das über FLOWTASK oder den Service Desk. Neue KI-Funktionen in Standardprodukten bleiben bis zur Prüfung des Datenflusses abgeschaltet. Diese Regel steht in Kurzform neben jeder Eingabe und ist Teil der Einführungsschulung.

## Musterentscheidung für den Einkauf

KI-EK-001, Materialanforderung aus geprüften Eingaben vorbereiten. Fachlicher Eigentümer ist die Rolle Einkaufsleitung. A1 bis zur Bestätigung, A2 ausschließlich für das Werkzeug `create_material_request_draft` im Testmandanten von FLOWERP. Zulässige Daten sind Artikel, Menge, Einheit und freigegebene Kostenstelle. Ausgeschlossen sind Freigabe der Materialanforderung, Bestellung, Versand, Buchung und Stammdatenänderung. Für die Freigabe sind Nachweise gegen Doppelanlage, Rechteüberschreitung und veraltete Bestätigung nötig. Nach Pilotende bewertet die Einkaufsleitung Zeitgewinn, Korrekturen und Störfälle. Status der Musterentscheidung: Entwurf.

## Unternehmensspezifische Nacharbeit

[FIRMENANGABE U-02] Geschäftsführung und Fachbereiche benennen Risikoeigner, Schwellen für Eskalation und Risikoannahme, ausgeschlossene und besonders sensible Prozesse, Vertretungen, Beschwerdestelle und Wiedervorlage. Sie bestätigen oder ändern den Startbestand des Agentenregisters und legen fest, ob das Einsatzregister in FLOWTASK oder einem anderen System geführt wird. Vor der Pilotauswahl freigeben. Arbeitsgrundlagen sind KI-Verordnung und DSGVO, Quellen in Teil 12.

| Feld für die interne Bearbeitung | Eintrag |
| --- | --- |
| Arbeitspunkt und vorgeschlagene Federführung | Freigabeordnung und Agentenregister / Prozessverantwortliche |
| Zu ergänzen | Zeichnungsbefugnisse, Schwellen, Vertretung, Ausschlussliste, Owner je Agent |
| Spätester Entscheid | Vor der Pilotauswahl |
| Erwarteter Abschlussbeleg | Unterzeichnete Einsatzentscheidung, Register-ID und freigegebener Registereintrag |
| Namentlich verantwortlich / Vertretung | offen / offen |
| Entscheid, Version, Datum und Beleglink | offen |
