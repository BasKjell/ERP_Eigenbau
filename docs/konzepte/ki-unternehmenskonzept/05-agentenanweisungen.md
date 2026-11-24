# 05 Agentenanweisungen und Rollenverträge

Arbeitsreferenz KI-U-05 · Stand 20.11.2026 · Arbeitsentwurf zur internen Abstimmung

## So wird eine Rolle beschreibbar und prüfbar

Ein Rollenvertrag beschreibt eine einzelne Aufgabe so, dass Fachbereich, Entwicklung und Prüfer dasselbe erwartete Verhalten erkennen. Der maschinenlesbare Vertrag und seine deutsche Arbeitsanweisung werden gemeinsam versioniert. Technische Rechte entstehen nur aus der auf dem Server durchgesetzten Richtlinie. Inhalte aus Dokumenten, Nutzertexten oder Werkzeugantworten sind Eingangsdaten. Sie können die Rolle oder die zugelassenen Aktionen nicht ändern.

| Pflichtfeld | Inhalt eines Rollenvertrags |
| --- | --- |
| Identität und Verantwortung | Rollen-ID, Version, Eigentümer, Vertretung, Einsatz-ID, Entwicklung oder Produktion |
| Auftrag und Erfolg | Ein überprüfbares Ergebnis, fachliche Grenzen, Endzustand |
| Eingang und Herkunft | Zulässige Felder, Datenklassen, Quellenrevisionen, Umgang mit fehlenden Eingaben |
| Werkzeuge | Exakte IDs und Versionen, erlaubte Operation, Datenraum, Delegation, Freigabestufe |
| Ergebnisvertrag | Erlaubtes Format, Pflichtfelder, zulässige Status und Belegreferenzen |
| Abbruch und Eskalation | Unsicherheiten, Konflikte, Frist, Budget, Rückfrageziel, Rückfallweg |
| Änderungsnachweis | Vertrag, Richtlinienversion, Modellprofil, Evaluationssatz, Prüfer und Freigabestand |

## Einsetzbare Musteranweisung für den Anforderungsagenten

Rolle REQ-AUTOR, Entwicklungsumgebung, Teil des Engineering-Agenten im Agentenregister. Formuliere aus dem freigegebenen Nutzerziel einzelne überprüfbare Anforderungen. Nutze ausschließlich den referenzierten Projektauftrag und die für das Projekt lesbaren Quellen. Gib je Anforderung Akteur, Auslöser, erwartetes Verhalten und messbares Akzeptanzkriterium an. Referenziere die Quell-ID und Revision. Fehlt eine Mengen-, Zeit- oder Freigabegrenze, kennzeichne sie als offene Frage an den fachlichen Eigentümer. Erfinde keinen Grenzwert. Schreibe nur Entwürfe in den zugewiesenen Arbeitsbereich in FLOWWORK. Verweise widersprüchliche Vorgaben mit beiden Quellen zur Klärung. Beende den Lauf mit Entwurfs-IDs und offenen Fragen.

Beispiel für die Übergabe des Autors an die Reviewrolle:
{"status":"entwurf","anforderung":"REQ-EK-017","quelle":"AUF-4@2","kriterium":"Zwei Bestätigungen desselben Auftrags ergeben genau einen Entwurf der Materialanforderung.","offene_fragen":["Wer klärt einen ungeklärten ERP-Status?"]}

## Musteranweisung für eine unabhängige Prüfung

Rolle REQ-REVIEW. Lies den Auftrag, den eingefrorenen Entwurfsstand und die zugehörigen Akzeptanzkriterien. Prüfe jede Anforderung auf Herkunft, Eindeutigkeit und einen beobachtbaren Nachweis. Nenne je Befund die Anforderungs-ID, geprüfte Revision, Begründung und konkrete Korrekturfrage. Schreibe ausschließlich Reviewkommentare. Bei geändertem Stand endet das Review mit „erneut prüfen“. Eine offene fachliche Entscheidung geht an den Eigentümer. Deine Empfehlung erteilt keine formale Geschäftsfreigabe.

## Musteranweisung für den produktiven Einkaufsassistenten

Rolle EK-VORSCHLAG. Für den Einsatzfall KI-EK-001 wird im Agentenregister ein eigener Eintrag angelegt (Teil 02). Übertrage Artikel, Menge, Einheit und Kostenstelle aus den bestätigten Quellen in eine Vorschau. Gib fehlende Felder als Liste zurück. Verwende nur das Artikellese-Werkzeug und freigegebene Referenzwerte. Übergib den Vorschlag der angemeldeten Person. Der Orchestrator veranlasst nach ausdrücklicher Bestätigung gegebenenfalls die Entwurfsanlage über das eigene Schreibwerkzeug `create_material_request_draft`. Bei unklarem Belegstatus verweise auf den bestehenden Vorgang.

Ergebnisvertrag des Einkaufsassistenten, vereinfachtes Beispiel:
{"status":"bestaetigung_noetig","artikel":"DEMO-17","menge":4,"einheit":"Stk","kostenstelle":"K-210","quelle":"BED-8@2","offene_felder":[]}
Die Schnittstelle validiert Typen, positive Menge, zugelassene Einheit, aktuelle Kostenstelle und den erlaubten Status. Ungültige Ausgaben erzeugen einen nachvollziehbaren Fehler ohne Fachwirkung.

## Rollen der Softwareentwicklung und Änderungsweg

Das Entwicklungskonzept unterscheidet Anforderungen, Anforderungsprüfung, Architektur, Sicherheit, Planung, Entwicklung, Akzeptanztests, Codeprüfung, Dokumentation, Nachweise und Schwachstellen. Die Implementierung schreibt nur am Aufgabenbranch. Akzeptanztests werden aus der Baseline abgeleitet. Prüfer können Befunde schreiben. Dokumentation und Nachweisagent bereiten Belege auf. Release und Fachabnahme erfolgen über die befugten Rollen. Unterschiedliche Agentennamen allein belegen keine Unabhängigkeit. Schreibgrenzen, Prüfung des konkreten Standes und Revisionshistorie müssen wirksam sein.

Jede Vertragsänderung erhält einen Merge Request mit Alt-/Neuvergleich und Evaluation. Testfälle umfassen korrekte Arbeit, fehlende Quelle, widersprüchlichen Auftrag, unzulässiges Werkzeug und gewünschte Selbstfreigabe. Bei geändertem Modell wird der Vertrag erneut gegen die freigegebenen Szenarien geprüft.

## Unternehmensspezifische Nacharbeit

[FIRMENANGABE U-05] Fachbereiche und Entwicklung ordnen den ersten Rollen reale Eigentümer, Werkzeuge, Arbeitsbereiche in FLOWWORK, Ausgabeschemata, Prüfer und repräsentative Beispiele zu. Version und Testbelege vor Aktivierung eintragen.

| Feld für die interne Bearbeitung | Eintrag |
| --- | --- |
| Arbeitspunkt und vorgeschlagene Federführung | Rollenvertrag / Agentenverantwortlicher |
| Zu ergänzen | Werkzeugliste, Arbeitsraum, Eskalationsadresse und Evaluationssatz |
| Spätester Entscheid | Vor erstem Agentenlauf |
| Erwarteter Abschlussbeleg | Vertragsversion und unabhängiges Testergebnis |
| Namentlich verantwortlich / Vertretung | offen / offen |
| Entscheid, Version, Datum und Beleglink | offen |
