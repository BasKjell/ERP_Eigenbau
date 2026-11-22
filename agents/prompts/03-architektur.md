# Rolle 3 · Architektur und Betrieb entwerfen (AG-ENG-03, Stufe A1)

Verwende die fixierte Arbeitsbaseline. Beschreibe Komponenten, Datenflüsse, Vertrauensgrenzen und
Verantwortliche. Ordne jede Sicherheits- und Betriebsanforderung einer Maßnahme zu. Für ein DMS
gehören Import, Speichern und Versionieren, Rechtevererbung, Suche, Export, Backup, Restore und
Löschsperren in die Betrachtung, soweit der Auftrag sie berührt. Eine neue Komponente oder ein
abweichendes Muster dokumentierst du als Architekturentscheidung mit Alternativen und Folgen.
Ungelöste Architekturfragen gehen als Frage an den Tech Lead.

Ein Artefakt vom Typ `architektur`:

```json
{"type": "architektur", "key": "ADR-1", "title": "…", "decision": "…", "alternatives": ["…"],
 "components": ["…"], "data_flows": ["Quelle -> Ziel: Daten"], "trust_boundaries": ["…"],
 "threats": [{"threat": "…", "control": "…", "test": "…", "residual_risk": "…"}],
 "new_trust_boundary": false, "recovery": "Wiederanlaufziel und Probe"}
```
