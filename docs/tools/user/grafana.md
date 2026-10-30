# Grafana-Dashboards nutzen

Grafana stellt technische Betriebsdaten und später freigegebene
Prozesskennzahlen dar. Es ersetzt weder ERPNext-Belege noch Qualitätsnachweise.

## Dashboard lesen

1. `http://localhost:3000` öffnen und mit persönlichem Konto anmelden.
2. Dashboard und Zeitraum prüfen; für einen aktuellen Vorfall einen kurzen,
   für Trends einen längeren Zeitraum wählen.
3. Filter wie Umgebung, Service oder Auftrag setzen.
4. Bei einem Ausschlag den Zeitpunkt markieren und mit Prozessereignissen in
   ERPNext bzw. Portal vergleichen.
5. Alarmstatus bestätigen und den hinterlegten Runbook-Link verwenden.

| Sicht | Prozessnutzen | Nächster Schritt bei Abweichung |
|---|---|---|
| API-Verfügbarkeit | Portal und Integrationen erreichbar? | Betriebsadmin informieren |
| Antwortzeit/Fehler | Bedien- oder Schnittstellenproblem? | Zeitpunkt und Aktion melden |
| Prozessdurchlauf | Stau zwischen Stufen? | Beleg im führenden System prüfen |
| Qualitätsquote | Häufung von Nacharbeit? | QS-Auswertung starten |

Ein grünes Dashboard ist keine fachliche Freigabe. Für Auftrag, Qualität,
Lieferung und Rechnung zählen die Belege im führenden System.
