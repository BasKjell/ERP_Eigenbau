# Datenzugriff und Datenfehler

PostgreSQL/pgvector ist ein interner Plattformdienst. Benutzer greifen nicht
direkt per SQL zu, sondern ausschließlich über Portal und freigegebene APIs.
MariaDB und Redis hinter ERPNext/Paperless sind ebenfalls nicht direkt zu
bedienen.

## Wenn Daten falsch oder unvollständig wirken

1. Seite neu laden und Belegreferenz prüfen.
2. Führendes System bestimmen: ERPNext für Belege, Paperless für Dokumente,
   Portal für den Demo-Zustand.
3. Keine Ersatzbuchung anlegen, bevor eine verzögerte Verarbeitung
   ausgeschlossen ist.
4. Erwartungswert, Ist-Wert, Referenz, Uhrzeit und letzten Arbeitsschritt
   dokumentieren.
5. Korrektur über den fachlichen Storno-/Änderungsprozess anfordern.

Direkte SQL-Korrekturen umgehen Berechtigungen, Audit und Geschäftsregeln und
sind für Benutzer verboten.
