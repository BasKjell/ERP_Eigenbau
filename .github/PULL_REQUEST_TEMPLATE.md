## Auftrag
Fachauftrag / Thema: … · Agent: `<art> / <modell> / <denkstufe>`

## Problem und geändertes Verhalten

## Anforderungen (FLOWWORK)
- Anforderungs-IDs (`REQ-…`) und Version, Baseline, Testfall-IDs: …
- `make requirements-check`: …

## Entscheidungen (ADR-Verweise)

## Tests und Ergebnisse
- `make test`: …
- `make agents-test`: …
- `make validate`: …
- nicht ausgeführt / übersprungen: …

## Einschränkungen und offene Nachweise

## Review
Risikoklasse (AGENTS.md §3): **Standard** / **Neue Funktion** / **Kritisch (K)** – Begründung: …
- [ ] K (Identität, Rechte, Tokens, Datenhaltung, Migration, Löschung, Export, Agentenrechte, Register/Ablauf, CI, normative Regeln) → unabhängiges Review (Codex oder Bas) vor dem Merge, Merge durch Bas
- [ ] Prüfer gehört zu einer anderen Modellfamilie als der Autor
- [ ] Freigabe nennt den geprüften Head-SHA und Zielbranch; nach neuen Commits erneut prüfen
- [ ] Übergabe in `docs/handoffs/` aktualisiert
- [ ] Alle Befunde beantwortet (behoben in `<SHA>` / begründet abgelehnt)
