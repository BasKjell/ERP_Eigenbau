# FLOWAGENTS – Agentenplattform

**Stand:** 2026-11-22 · implementiert und getestet · Betriebsfreigabe durch Bas offen

FLOWAGENTS entwickelt Fachsoftware in getrennten Rollen. Ein Fachbereich beschreibt im
FLOWPORTAL, welche Arbeit leichter werden soll; Agenten leiten Anforderungen ab, prüfen sie,
entwerfen Architektur, planen, testen, entwickeln, dokumentieren und stellen Nachweise zusammen.
Menschen entscheiden an festen Punkten. Grundlage:
[KI-Softwareentwicklung nach dem V-Modell](../konzepte/ki-softwareentwicklung/00-hauptdokument.md),
technische Einzelheiten im [KI-Entwicklungskonzept (Teil 01–10)](../konzepte/ki-entwicklungskonzept/index.md),
sowie das [Unternehmenskonzept KI-U-00 bis KI-U-12](../konzepte/ki-unternehmenskonzept/00-hauptdokument.md).

## Wo man was sieht

| Ort | Inhalt |
|---|---|
| FLOWPORTAL Startseite | Agentenzentrale: wer gerade arbeitet, Live-Karte der Zusammenarbeit, Entscheidungs-Inbox, offene Aufträge |
| `/agents` | Vollansicht mit Agentenregister, Laufdetails (Verlauf, Ergebnisse, Diff, Nachweise), Stopp-Schalter, FLOWWORK-Audit |
| FLOWWORK `/work` | Anforderungen (Agenten-Entwürfe und Plattformkatalog), Baselines, Testfälle, Nachverfolgung |

Die Karte zeigt **Übergaben** (türkis), **Rückläufe** nach Prüfbefund (rot), **Fragen an Menschen**
(gelb), **Entscheidungen** (lime) und **Werkzeugaufrufe in FLOWWORK** (blau). Neue Ereignisse
laufen als Impuls über die Kante.

## Die Rollen

| Nr. | Agent | Art | Stufe | Modellprofil | Wird geprüft von |
|---|---|---|---|---|---|
| 12 | Geschäftsführungs-Agent (AG-MGMT-01) | Prüfung | A0 | leitung (gemma) | Mensch bei Bedenken |
| 1 | Anforderungs-Agent (AG-ENG-01) | Erstellung | A1 | builder (qwen) | 2 |
| 2 | Anforderungsprüfung (AG-ENG-02) | Prüfung | A0 | pruefer (gemma) | – |
| 3 | Architektur (AG-ENG-03) | Erstellung | A1 | builder (qwen) | 4 |
| 4 | Sicherheit (AG-ENG-04) | Prüfung | A0 | pruefer (gemma) | – |
| 5 | Planung (AG-ENG-05) | Erstellung | A1 | assistenz (qwen) | – |
| 6 | Entwicklung (AG-ENG-06) | Erstellung | A1 | coder (qwen) | 8 |
| 7 | Akzeptanztests (AG-ENG-07) | Erstellung | A1 | pruefer (gemma) | – (kein Zugriff auf Code) |
| 8 | Codeprüfung (AG-ENG-08) | Prüfung | A0 | pruefer (gemma) | – |
| 9 | Dokumentation (AG-ENG-09) | Erstellung | A1 | assistenz (qwen) | 2 |
| 10 | Nachweise (AG-ENG-10) | Erstellung | A1 | assistenz (qwen) | Orchestrator prüft selbst |
| 11 | Schwachstellen (AG-ENG-11) | Erstellung | A1 | assistenz (qwen) | Status „Idee“, nicht aktiv |

Der **Geschäftsführungs-Agent** bewertet jeden Auftrag zu Beginn und das Ergebnis vor der
Fachabnahme: Nutzen, Aufwand für Beschäftigte, Passung zu den Abläufen, Risiken. Er berät nur;
bei erheblichen Bedenken entscheidet ein Mensch.

## Ablauf und Gates

```mermaid
flowchart LR
  A[Fachauftrag] --> GF1[Geschäftsführungs-Agent]
  GF1 --> R1[Anforderungen] --> R2[Anforderungsprüfung]
  R2 -- Befund --> R1
  R2 --> G1{G1 Baseline}
  G1 --> AR[Architektur] --> SE[Sicherheit]
  SE -- Befund --> AR
  SE --> G2{G2 Architektur} --> PL[Planung] --> AT[Akzeptanztests] --> DEV[Entwicklung]
  DEV --> CI[Integrationsprüfung offline] --> CR[Codeprüfung]
  CI -- rot --> DEV
  CR -- Befund --> DEV
  CR --> G3{G3 Integration} --> DOC[Dokumentation] --> EV[Nachweise] --> GF2[Geschäftsführungs-Agent]
  GF2 --> G4{G4 Fachabnahme} --> G5{G5 Produktion}
```

| Klasse | Menschliche Entscheidung |
|---|---|
| Standardänderung | G4 Fachabnahme, G5 Produktion (G1–G3 automatisch, protokolliert) |
| Neue Funktion | zusätzlich G1 durch den Product Owner |
| Hoher Schutzbedarf / neuer Dienst | G1 bis G5 |

Nach zwei erfolglosen Korrekturrunden entscheidet der Tech Lead. Ein neuer Änderungsstand macht
Codeprüfung, Integrationsprüfung und Abnahme ungültig (Digest-Bindung). Der Orchestrator prüft das
Nachweispaket selbst; eine Lücke sperrt G4/G5.

## Entscheidungsrollen (vorläufige FLOWID-Zuordnung)

| Rolle | FLOWID-Rollen | Beispiel-Testperson |
|---|---|---|
| Product Owner | `requirements-user`, `work-admin` | Clara Schröder (demo11) |
| Tech Lead | `work-admin`, `it-user` | Maja Roth (demo49) |
| Key User (Fachabnahme) | `requirements-user`, `work-user` | Tobias Neumann (demo12) |
| Release-Verantwortung | `it-user` | Christian Beck (demo50) |
| Geschäftsführung | `management-user` | Anna Schneider (demo01) |

Eigene Realm-Rollen (`flow-po`, `flow-techlead`, `flow-release`, `flow-isb`) sind vor dem Pilot
anzulegen [FIRMENANGABE U-07]. Im lokalen Demo-Modus ohne Anmeldung darf `platform-admin`
entscheiden; das ist im Portal sichtbar.

## Einen Auftrag starten

1. In FLOWPORTAL **＋ Fachauftrag starten** wählen.
2. Zweck, Nutzergruppe, gewünschtes Verhalten und ein Erfolgsbeispiel beschreiben.
3. Änderungsklasse, Datenklasse und den **freigegebenen Änderungsbereich** wählen. Nur Dateien
   dieses Bereichs darf der Entwicklungs-Agent ändern; die Bereiche stehen in
   `services/agent_orchestrator/config/orchestrator.yaml` (Erweiterung ist Klasse K).
4. Den Lauf auf der Karte verfolgen; Entscheidungen erscheinen in „Deine Entscheidungen“.

Weiter: [Betrieb](betrieb.md) · [Sicherheit und Nachweise](sicherheit.md)
