# Dokumente finden, bearbeiten und freigeben

## Was nach der Anmeldung sichtbar ist

Die Dokumentliste ist kein gemeinsamer, ungeschützter Ablageordner. Sichtbar
ist nur die Schnittmenge aus:

- der Funktionsrolle `DMS-Leser`, `DMS-Bearbeiter`, `DMS-Pruefer` oder
  `DMS-Freigeber` und
- einer Zugriffsgruppe für Eingang, Bereich oder konkretes Projekt.

Beispiel: Ein Benutzer mit `DMS-Leser` und
`DMS-Projekt-KOM-2027-4711-Lesen` darf die Dokumente der Kommission lesen, aber
nicht ändern. Ein Leser eines anderen Projekts sieht sie nicht.

Personalunterlagen sind zusätzlich isoliert. Bewerberakten benötigen
`DMS-Bereich-HR-Recruiting`, Entgeltabrechnungen
`DMS-Bereich-HR-Payroll`. Projektleser und allgemeine DMS-Leser erhalten diese
Objektfreigabe nicht. Zugriff auf beide Bereiche allein wegen einer
HR-Zugehörigkeit ist nicht vorgesehen.

## Dokument sicher finden

1. In der Suche Projekt-/Kommissionsnummer, Artikel oder Seriennummer eingeben.
2. Ergebnis öffnen und Dokumenttyp sowie Titel prüfen.
3. Projekt, Artikel, Revision, Gültigkeit und Status vergleichen.
4. Nur `Status/Freigegeben` verwenden.
5. Im ERP/MES kontrollieren, dass die stabile Dokument-ID auf genau diesen
   Stand verweist.

## Neuen Entwurf anlegen

1. PDF hochladen.
2. Automatisch gesetzten Status **Entwurf** prüfen.
3. Dokumenttyp, Titel und `Projekt / Kommission` pflegen.
4. Artikel, Revision, ERP-Auftrag, Fertigungsauftrag oder Charge ergänzen.
5. Projekt-Tag und Ablagepfad kontrollieren.
6. Inhalt und OCR vollständig kontrollieren.
7. `Status/In Prüfung` hinzufügen.

Ist das Projekt nicht erkannt, bleibt das Dokument nur für `DMS-Eingang` und
die Administration sichtbar. Die Dokumentenlenkung klassifiziert es; der
Benutzer darf die Rechte nicht manuell erweitern.

## Dokumentlieferung planen

Sobald feststeht, dass ein Projekt ein Dokument liefern muss, legt der
Dokumentenverantwortliche einen kontrollierten Entwurf an. Dadurch ist der
Bedarf bereits im Lieferdashboard sichtbar, obwohl der Inhalt noch nicht final
freigegeben ist.

Pflichtangaben für die Terminplanung:

| Feld | Wer pflegt es? | Beispiel |
|---|---|---|
| Projekt / Kommission | Projektassistenz oder Dokumentenlenkung | `KOM-2027-4711` |
| Dokumentlieferobjekt | Projektleitung | Abnahmeunterlagen |
| Meilenstein | Projektleitung | Kundenabnahme |
| Dokumentverantwortung | Projektleitung | Qualität |
| Baseline-Version und -Termin | Projektsteuerung nach Planfreigabe | `BL-01`, 15.11.2026 |
| Liefertermin | Projektleitung nach Vertrag/Terminplan | 18.11.2026 |
| Forecast-Termin | Dokumentverantwortlicher | 22.11.2026 |
| Lieferempfänger | Projektleitung | Kunde oder Prüfstelle |
| Vertragsdokument | Projektleitung | ja/nein |
| Fortschritt (%) | Dokumentverantwortlicher | 40 |
| Terminnotiz | Dokumentverantwortlicher | ausstehende Freigabe |
| Tatsächliches Lieferdatum | Dokumentenlenkung nach Versand/Nachweis | 19.11.2026 |

Baseline und Baseline-Termin werden nicht stillschweigend überschrieben. Eine
genehmigte neue Baseline erhält eine neue Versionskennung; die Änderung wird im
Projektänderungsprotokoll begründet. Ein schlechter Forecast ändert weder
Baseline noch Liefertermin, sondern macht die Gefährdung transparent.

Zum Kontrollieren das
[Grafana-Dashboard](http://localhost:3000/d/dms-document-deliveries/dms-e28093-dokumentenlieferplan)
öffnen, Projekt wählen und die Zeile über den Dokumenttitel wieder in
Paperless öffnen.

## Vier-Augen-Freigabe durchführen

### Bearbeiter

Der Bearbeiter stellt Vollständigkeit, richtige Revision und Metadaten sicher
und fügt **In Prüfung** hinzu. Danach verliert seine Projektgruppe das
Änderungsrecht.

### Prüfer

Der Prüfer kontrolliert Inhalt und Verwendbarkeit. Bei Erfolg ergänzt er
**Zur Freigabe**, bei Mangel **Abgelehnt** plus Begründung. Nach **Zur
Freigabe** kann die Prüfgruppe das Dokument nicht mehr ändern.

### Freigeber

Der Freigeber prüft Entscheidung, Verantwortlichkeit und Gültigkeit, pflegt
`Freigegeben durch` sowie `Freigabedatum` und ergänzt **Freigegeben**. Alternativ
setzt er **Abgelehnt** mit Begründung. Eine Abkürzung direkt von Entwurf oder
Prüfung zu Freigegeben wird vom Schutzworkflow entfernt.

## Neue Revision

Eine neue Revision ist ein neues Dokument und überschreibt den freigegebenen
Stand nicht. Sie startet wieder als Entwurf und durchläuft alle Stufen. Nach
Freigabe der neuen Revision setzt der Freigeber den ersetzten Stand auf
**Obsolet**. Laufende Aufträge behalten ihre eingefrorene Referenz, sofern der
Änderungsprozess keine dokumentierte Umstellung erlaubt.

## Projektvorlagen

Für Kundenkommissionen, interne Fertigung und Entwicklung sind Vorlagen
vorhanden. Die DMS-Administration erzeugt daraus Projekt-Tag, Ablagepfad,
Zugriffsgruppen und Workflows. Anwender melden dafür mindestens Vorlagentyp,
Projektcode, Name, zuständige Bearbeiter, Prüfer, Freigeber und optionale
Dateinamensmuster.

## Abnahmetest für Berechtigungen

Vor Freigabe eines neuen Projekts testen vier getrennte Konten:

1. Projektleser sieht das Dokument, kann es aber nicht ändern.
2. Bearbeiter kann den Entwurf ändern und einreichen, danach nicht mehr.
3. Prüfer kann prüfen und auf **Zur Freigabe** setzen, aber nicht final
   freigeben.
4. Freigeber kann final entscheiden.
5. Ein Benutzer aus einem Fremdprojekt findet das Dokument weder in Suche noch
   API.

Fehlschlägt einer dieser Tests, darf der Projektraum nicht produktiv verwendet
werden.

Für Personalbereiche kommen zwei negative Tests hinzu: Ein Recruiting-Benutzer
darf keine Entgeltabrechnung finden, ein Payroll-Benutzer keine
Bewerberunterlage. DMS-Administration wird als privilegierter Notzugriff
separat protokolliert.
