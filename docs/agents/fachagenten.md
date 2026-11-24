# Fachagenten

**Stand:** 2026-11-24 · Code: `flowagents/fachagenten.py`, Agentenzentrale `/agents`

Fachagenten erledigen Fachaufgaben außerhalb des Entwicklungsablaufs nach dem V-Modell, zum Beispiel
**Lieferantenmails im Einkauf beantworten**. Administratoren legen sie in der Agentenzentrale an, auf
Wunsch mit einem Entwurf der lokalen KI, und weisen sie AD-Gruppen oder einzelnen Personen zu.

## Grundsätze

| Regel | Umsetzung |
|---|---|
| Nur lokale Modelle | Aufruf über FLOWGATE mit eigenem Schlüssel `fachagenten` (nur `flow-assist`, `flow-builder`, `flow-reviewer`, `flow-coder`); kein Codex/Claude, kein Internet |
| Nur Entwürfe (Stufe A1) | Der Agent versendet, bucht und genehmigt nichts. Jede Antwort ist ein Entwurf, den ein Mensch bearbeitet und **freigibt** oder **verwirft** |
| Keine Werkzeuge | Der Agent bekommt nur den Eingang (z. B. die E-Mail) und Hintergrunddaten, die die Plattform mitgibt |
| Hintergrunddaten nur für Berechtigte | Die Plattform liest Datenquellen (Einkauf, Qualität, Kundenauftrag) nur, wenn die **anfragende Person** selbst eine passende Rolle hat (z. B. `procurement-user`) |
| Anlegen nur durch Administratoren | `platform-admin`; Knopf **⚙ Fachagenten verwalten** sehen nur Administratoren |
| Nutzen nur durch Zugewiesene | AD-Gruppen (Realm-Rollen wie `procurement-user` aus `AD-GG-FLOW-PROCUREMENT-USER`) und/oder Benutzernamen |
| Nachvollziehbar | Anlegen, Ändern, Freigeben und Verwerfen stehen im Protokoll; Modellnutzung im Token-Dashboard (Rolle `fachagenten`) |

## Einen Fachagenten anlegen (Administrator)

1. In `/agents` oben **⚙ Fachagenten verwalten** wählen.
2. Unter „Mit lokaler KI entwerfen“ den Agenten in Worten beschreiben, zum Beispiel:
   *„Ein Agent, der Mails von Lieferanten an den Einkauf beantwortet: Lieferverzug, Preisanpassungen und
   Rückfragen zu Prüfzeugnissen. Er nutzt die Einkaufsdaten und sagt nie Termine oder Preise zu, die nicht in
   den Bestellungen stehen.“*
3. **Mit lokaler KI entwerfen**: Das lokale Modell schlägt Name, Zweck, Vorlage, Datenquellen, Datenklasse,
   Rollenanweisung und AD-Gruppen vor. In der Vorführung brauchte `qwen3:8b` dafür 11 Sekunden.
4. Vorschlag prüfen, anpassen, **AD-Gruppen** ankreuzen und/oder **Personen** (Benutzernamen) eintragen.
5. **Fachagent anlegen**. Der Orchestrator prüft die Definition: Vorlage, lokales Modellprofil, Datenquellen,
   Datenklasse und mindestens eine Zuweisung. Pausieren und Ändern gehen über denselben Dialog.

| Vorlage | Eingang | Ergebnis |
|---|---|---|
| E-Mails beantworten | Absender, Betreff, Text | Kategorie, Zusammenfassung, Antwort (Betreff und Text), Rückfragen vor dem Versand, Risiko |
| Text zusammenfassen und Aufgaben ableiten | Titel, Text | Zusammenfassung, Aufgaben, offene Fragen |
| Fachassistent | Frage | Antwort, genutzte Daten, nächste Schritte |

## Einen Fachagenten nutzen

Zugewiesene Personen sehen in der Agentenzentrale **Meine Fachagenten**:

1. **Aufgabe geben**, Eingang ausfüllen (für die Vorführung: **Beispielmail einfügen**) und **An den Agenten
   geben**.
2. Der Status wechselt von „wartet auf das Modell“ über „Agent arbeitet“ zu **„Entwurf bereit – bitte
   prüfen“**.
3. Antwort lesen, bei Bedarf bearbeiten, die **Rückfragen vor dem Versand** klären, dann **Freigeben** oder
   **Verwerfen**.
4. Freigegebene Antworten lassen sich kopieren. Ein Postfach ist noch nicht angebunden; der Versand erfolgt
   bis dahin über das eigene Mailprogramm.

Beispiel aus der Vorführung: Auf die Mail „Rückfrage Prüfzeugnis Gehäuse“ lieferte der Einkaufs-Mail-Agent
in 7 Sekunden einen höflichen Zwischenbescheid, sagte nichts zu und nannte als Rückfrage vor dem Versand,
ob ein Prüfzeugnis 3.1 oder 2.2 benötigt wird.

## Zielbild: n8n oder Dify

Für den Unternehmensbetrieb sollen Fachagenten mit fertigen Anbindungen arbeiten (Postfach, ERP, DMS),
statt jede Anbindung selbst zu bauen. Kandidaten sind **n8n** und **Dify**
([Orchestrierung: Eigenbau und fertige Werkzeuge](plattformstrategie.md)). Unverändert bleiben dabei:
Modelle nur über FLOWGATE, Anmeldung über Keycloak mit AD-Gruppen, nur Entwürfe mit menschlicher Freigabe
und Nachweise im gemeinsamen Nachweisspeicher. Der Einkaufs-Mail-Agent dient als Referenzfall für den
Vergleich (FLOWAGENTS, n8n, Dify).

## Grenzen und nächste Schritte

- Kein automatischer Posteingang und kein Versand; dafür braucht es eine Postfach-Anbindung (IMAP/Graph) mit
  eigenem Dienstkonto. Das ist eine Änderung der Klasse K.
- Hintergrunddaten kommen derzeit aus dem Demo-Datensatz der Plattform (Bestellungen, Liefertreue,
  Zahlungsbedingungen, Wareneingang, Kundenauftrag), höchstens 25 Einträge je Liste.
- Fachagenten stehen nicht im versionierten Agentenregister; sie liegen in der Orchestrator-Datenbank
  (`business_agents`, `business_jobs`).
