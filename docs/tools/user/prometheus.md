# Prometheus-Metriken richtig einordnen

Prometheus sammelt technische Zeitreihen. Endanwender arbeiten normalerweise
über [Grafana](grafana.md); die Prometheus-Oberfläche ist eine Diagnosehilfe
für berechtigte Supportrollen.

## Bezug zum Unternehmensprozess

Metriken zeigen, ob Portal und Schnittstellen technisch funktionieren. Sie
zeigen nicht, ob ein Auftrag kaufmännisch, qualitativ oder rechtlich korrekt
freigegeben ist.

Bei einer Störung:

1. betroffene Prozessaktion, Beleg und Uhrzeit notieren,
2. in Grafana Verfügbarkeit und Fehlerquote prüfen,
3. fachlichen Status im führenden System sichern,
4. keine Prozessaktion wiederholen, solange unklar ist, ob sie bereits
   verbucht wurde,
5. Support mit Uhrzeit, Benutzeraktion und Referenz informieren.

Direkte PromQL-Abfragen und Änderungen an Alarmregeln gehören zur
Administration.
