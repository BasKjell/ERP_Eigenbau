# TM-100 – Lastenheft Gerätesoftware

**Projekt:** TM-100 (Testprodukt, Domäne Produktsoftware, Kritikalität K2) · **Status:** Entwurf · Demo-Inhalt

Das TM-100 ist ein fiktives Handmessgerät für Temperatur und Feuchte. Dieses Lastenheft ist der
Ausgangspunkt für Arbeitspaket AP-1 im Projekt TM-100.

| ID | Anforderung | Prüfkriterium |
|---|---|---|
| TM-R1 | Das Gerät misst Temperatur von −20 °C bis +85 °C. | Messung an drei Referenzpunkten innerhalb des Bereichs |
| TM-R2 | Die Messabweichung beträgt höchstens ±0,3 K. | Vergleich mit kalibriertem Referenzsensor |
| TM-R3 | Ein Servicetechniker kann die Kalibrierwerte über die Serviceschnittstelle lesen und schreiben. | Lesen und Schreiben mit Servicekennung, ohne Kennung abgewiesen |
| TM-R4 | Jede Kalibrierung wird mit Zeitpunkt und Seriennummer protokolliert. | Protokolleintrag nach jeder Kalibrierung vorhanden |

Offene Punkte: Akkulaufzeit, Anzeige im Display.
