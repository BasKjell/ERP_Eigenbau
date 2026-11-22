# Bewertung der Agenten und Modelle

Bewertet werden bestandene Abnahmekriterien, gefundene Fehler und der Gesamtaufwand einschließlich
Nacharbeit (AGENTS.md §3, KI-EK Teil 05 „Wirksamkeit messen“). Übereinstimmung mehrerer Modelle ist
kein empirischer Nachweis. Fehler, die später gefunden werden, werden beim verursachenden Eintrag
nachgetragen.

## Entwicklung der Plattform

| Thema | Agent / Modell | Abnahmekriterien | Fehler gefunden (durch wen) | Nacharbeit | Bemerkung |
|---|---|---|---|---|---|
| FLOWAGENTS, Agentenzentrale, FLOWDOC (2026-11-22) | Claude Code / claude-opus-5-5 | Tests grün; Codex-Review offen | Selbst im Live-Lauf gefunden: Pull-Modell nötig (Container erreicht Host-Loopback nicht), PID-Datei bezeichnete die Subshell, Prüfer sahen erledigte Gate-Entscheidungen, Feed-Animation | 6 Korrekturcommits | Klasse K; unabhängiges Review durch Codex ausstehend |

## Lokale Rollenmodelle im Live-Lauf A-001 (2026-11-22, neue Funktion, Bereich DMS-Benutzerhilfe)

| Rolle | Modell (Profil) | Beobachtung | Folge |
|---|---|---|---|
| Geschäftsführung | gemma3:12b (leitung) | Bewertung inhaltlich passend; erster Versuch ohne Pflichtfelder der Bewertung | Vertragswiederholung; Pflichtfelder jetzt im Auftrag (`a02ef98`) |
| Anforderungen | qwen3:8b (builder) | Prüfbare Kriterien erst nach menschlicher G1-Ablehnung; meldete Überarbeitung als „nacharbeit“ | Vertrag lehnt „nacharbeit“ für Ersteller ab (`d975da5`) |
| Anforderungsprüfung | gemma3:12b (pruefer) | Ließ „leicht verständlich“ als Kriterium durch; wiederholte später einen bereits behobenen Befund, weil die G1-Begründung im Kontext stand | Kontext auf eigene Rückfragen begrenzt (`e3ad000`); G1 bleibt bei neuen Funktionen menschlich |
| Architektur, Sicherheit, Planung, Akzeptanztests | qwen3:8b / gemma3:12b | jeweils ein ungültiger erster Versuch (fehlende Pflichtfelder), zweiter gültig | Pflichtfelder im Auftrag |
| Entwicklung | qwen3-coder:30b (coder) | erster Versuch ohne Dateiinhalt | Pflichtfelder im Auftrag |

Folgerung: Die lokalen Prüfer sind nachgiebig und anfällig für Kontextwiederholung. Vor einem
Pilot braucht jede Rolle einen Evaluationssatz mit Referenzfällen (korrekte Arbeit, fehlende Quelle,
widersprüchlicher Auftrag, unzulässiges Werkzeug, gewünschte Selbstfreigabe; KI-U-05) und eine
Schwelle, unter der ein Modellwechsel gesperrt bleibt (KI-EK Test 34).
