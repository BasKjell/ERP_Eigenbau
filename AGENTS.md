# AGENTS.md – verbindliche Arbeitsregeln für ERP_Eigenbau

Gilt für alle Agenten (Claude Code, Codex, lokale Rollen über FLOWAGENTS) und für Menschen, die an
diesem Repository arbeiten. Grundlage sind das Konzept KI-Softwareentwicklung nach dem V-Modell (löst
das KI-Entwicklungskonzept vom 2026-11-20 ab), das Unternehmenskonzept KI-U-00 bis KI-U-12 und die
Arbeitsweise aus `Trading_Ai`. Bei Widerspruch
gelten diese Datei, `agents/registry.yaml`, `agents/workflow.yaml` und ausdrückliche Entscheidungen
von Bas. Konflikte werden dokumentiert und geklärt, nicht stillschweigend interpretiert.

Status dieser Regeln: **Arbeitsentwurf**, gilt ab sofort für alle Änderungen. Die erste
Betriebsfreigabe der Agentenplattform erteilt Bas nach dem unabhängigen Review (siehe §6).

## 0. Erster Schritt jeder Sitzung

1. Diese Datei, `docs/agents/index.md` und die letzte Übergabe in `docs/handoffs/` lesen.
2. `git status`, `git log`, offene Branches und offene Pull Requests prüfen.
3. Offene Review-Befunde zu eigenen Änderungen haben Vorrang vor neuen Aufgaben.
4. Modell und Denkstufe prüfen: Standard „medium“; höher bei Rechten, Identitäten, Freigaben,
   Datenhaltung, Löschung, Migration oder unklaren Anforderungen. Ein Wechsel wird nie behauptet,
   sondern in der Übergabe empfohlen.

## 1. Anforderungen zuerst (FLOWWORK = Jama-Nachbau)

- Jede fachliche Änderung beginnt mit einer Anforderung mit stabiler ID, Version, Quelle und
  mindestens einem beobachtbaren Akzeptanzkriterium.
- Führendes Register ist **FLOWWORK**. Die versionierte Quelle für Plattformanforderungen liegt in
  `requirements/catalog.yaml` und wird mit `make requirements-sync` idempotent nach FLOWWORK
  übertragen. Tests nennen die Anforderungs-ID im Docstring (`REQ-…`); `make requirements-check`
  prüft die Rückverfolgbarkeit.
- Fehlende Fachentscheidungen werden als offene Frage erfasst, nie erfunden (Fristen, Rechte,
  Löschregeln, Grenzwerte).

## 2. Rollentrennung und Unabhängigkeit

- Für jedes Artefakt sind Ersteller und Prüfer getrennt. Prüfer gehören zu einer anderen
  Modellfamilie (Register: `model_profiles.*.family`). Unterschiedliche Agentennamen allein
  belegen keine Unabhängigkeit.
- Wer eine Änderung erstellt hat, prüft oder integriert sie nicht selbst.
  Bei Claude Code als Autor reviewt Codex oder Bas; bei Codex als Autor reviewt Claude Code oder Bas.
- Der **Geschäftsführungs-Agent** (AG-MGMT-01) bewertet Auftrag und Ergebnis aus
  Unternehmenssicht (Nutzen, Aufwand für Beschäftigte, Abläufe, Risiko). Er berät, er gibt nichts frei.
- Kein Agent besitzt Freigabe-, Merge-, Lösch-, Administrations- oder Deploymentwerkzeuge.
  Freigaben entstehen nur durch befugte Menschen in FLOWPORTAL.

## 3. Risikoklassen und Gates

| Klasse | Beispiele | Menschliche Entscheidung |
|---|---|---|
| **Standardänderung** | Sortierung, Texte, Hilfe, Anzeige ohne neue Datenquelle | G4 Fachabnahme, G5 Produktion |
| **Neue Funktion** | neuer Dokumenttyp, neuer Workflow, neue Ansicht mit neuer Datenquelle | zusätzlich G1 (Product Owner) |
| **Kritisch (K)** | Identität, Rechte, Rechtevererbung, Tokens, Datenhaltung, Migration, Löschung, Export, Agentenrechte, Register/Ablauf, CI, diese Regeln | G1, G2, G3, G4, G5 und unabhängiges Review durch Codex oder Bas vor dem Merge |

- Im Zweifel und bei gemischten Änderungen gilt **kritisch**.
- Eine Prüfempfehlung gilt nur für den genannten Commit bzw. Digest. Ein neuer inhaltlicher Commit
  entwertet sie (Ausnahme: reiner Merge von `main` ohne Konflikt, mit Merge-Diff-Prüfung).
- Nach zwei erfolglosen Korrekturrunden: keine weiteren spekulativen Änderungen, Übergabe mit
  Reproduktion und Befunden an den Tech Lead bzw. ein stärkeres Modell.

## 4. Arbeiten

- Eigener Branch je Aufgabe (`claude/…`, `codex/…`); nie mehrere Agenten im selben Checkout.
- Kleine, fachlich zusammenhängende Commits mit Präfix `feat|fix|test|docs|refactor|chore|style`
  und Zeile `Agent: <art> / <modell>`. Kein Force-Push, keine Historienänderung, nie eigene PRs mergen.
- Vor jedem Commit die betroffenen Prüfungen ausführen und nur tatsächlich ausgeführte Ergebnisse
  berichten: `make test` (Plattform), `make agents-test` (Orchestrator), `make validate`.
- Jede ausführbare Änderung mit Test, jede Fehlerbehebung mit Regressionstest. Erwartete
  Testergebnisse nie anpassen, nur damit fehlerhafter Code besteht.
- Dokumentationsaussagen kennzeichnen: **geplant / implementiert / getestet / integriert / blockiert**.
- Geheimnisse nur in `.env` (Vorlage `.env.example`), nie in Git, Logs, Übergaben oder Commits.
  Demo-Geheimnisse tragen `change-before-network-use` und sind vor jeder Netzwerknutzung zu ersetzen.
- Übergabe `docs/handoffs/<thema>.md` laufend pflegen, spätestens vor jeder Pause.

## 5. Sicherheit (BSI IT-Grundschutz / ISO 27001 orientiert)

- Das Quellsystem entscheidet über Objektrechte (Paperless, ERPNext, FLOWWORK). Eigene Oberflächen
  fragen im Namen der angemeldeten Person; technische Konten nur im lokalen Demo-Modus und sichtbar
  gekennzeichnet.
- Agenten erhalten nur Werkzeuge laut Register und nur kurzlebige, rollen- und laufgebundene Tokens;
  der RM-Adapter prüft jede Operation serverseitig erneut.
- Entwicklungsagenten schreiben nur in freigegebene Änderungsbereiche einer Sandbox; Prüfungen laufen
  ohne Netzwerk und ohne Zugangsdaten. Kein Zugriff auf produktive Systeme.
- Protokolle enthalten keine Vollprompts, Modellantworten, Suchtexte oder Zugangsdaten.
- Externe Modelle, Cloud-Fallbacks, kostenpflichtige Dienste und die Codex/Claude-Abo-Worker bleiben
  gesperrt, bis Bas sie ausdrücklich freigibt (`container.execution_enabled`).
- Kontrollzuordnung und offene Nachweise: [docs/agents/sicherheit.md](docs/agents/sicherheit.md).

## 6. Integration und Freigabe

1. Klasse kritisch: unabhängiges Review (Codex oder Bas) für genau den Head, danach ausdrückliche
   Freigabe von Bas. Den Merge führt Bas aus.
2. Übrige Klassen: Review durch einen Agenten einer anderen Modellfamilie mit dokumentierter
   Klassenprüfung; Integration durch einen vom Autor getrennten Agenten oder Bas.
3. Integration in `main` ist keine Produktionsfreigabe. G5 entscheidet die Release-Verantwortung
   außerhalb des Agentennetzes.

## 7. Nützliche Befehle

```bash
make agents-up          # FLOWAGENTS-Orchestrator starten (Host-Dienst)
make agents-status      # Läufe, Entscheidungen, Agentenzustand
make agents-test        # Register, Orchestrator und Vertrauensgrenzen prüfen
make test               # Plattform-API (Lint + Tests im Container)
make requirements-sync  # requirements/catalog.yaml nach FLOWWORK übertragen
make requirements-check # Rückverfolgbarkeit Anforderung -> Test prüfen
```
