# FLOWDOC – Dokumente in der eigenen Oberfläche

**Stand:** 2026-11-22 · implementiert und getestet · erreichbar unter `/dms` im FLOWPORTAL

FLOWDOC ist die eigene Dokumentenoberfläche der Plattform. Ablage, Texterkennung, Versionen und
Zugriffsrechte bleiben in Paperless-ngx; FLOWDOC fragt Paperless **im Namen der angemeldeten
Person**. Was du nicht lesen darfst, erscheint nirgends – weder in der Liste noch als Titel,
Trefferzahl oder Vorschau (siehe [Dokumente: Rechte und Freigabe](dms.md)).

## Finden

1. In FLOWPORTAL **Dokumente finden (FLOWDOC)** oder im App-Launcher **FLOWDOC** öffnen.
2. Im Suchfeld oben suchst du im Volltext (Titel, erkannter Text, Kommission, Artikel, Seriennummer).
3. Links filterst du nach **Status** (Entwurf, In Prüfung, Freigegeben), **Dokumenttyp**,
   **Projekt/Bereich** und **Korrespondent**. Aktive Filter erscheinen als Chips über der Liste und
   lassen sich mit ✕ entfernen.
4. Mit **Sortierung** ordnest du die Liste nach Titel A–Z oder Z–A, Datum, Dokumenttyp, Korrespondent
   oder Ablagezeitpunkt. Sortierung und Filter wirken zusammen: „Freigegeben“ + „Titel A–Z“ zeigt nur
   freigegebene Dokumente, alphabetisch.

Die Adresse der Seite enthält Suche, Filter und das geöffnete Dokument; du kannst sie als Lesezeichen
speichern oder an Kolleginnen schicken – sie sehen nur, was ihre eigenen Rechte erlauben.

## Ansehen und bearbeiten

- Ein Klick öffnet rechts die **Vorschau** mit Metadaten, Projekt/Bereich, Feldern, Notizen und
  einem Auszug des erkannten Texts.
- **Statusworkflow:** *Zur Prüfung geben* (aus Entwurf), *Freigeben* oder *Zurückweisen* (aus In
  Prüfung). Ob du das darfst, entscheidet Paperless anhand deiner Rolle (z. B. `DMS-Freigeber`).
- **Notizen** halten Prüfhinweise am Dokument fest.
- **Herunterladen** liefert die Originaldatei.

## Ablegen

1. **↑ Dokument ablegen** (oben rechts oder Schnellstart im Portal).
2. Datei hineinziehen oder auswählen (PDF, Bild, Office; höchstens 25 MB).
3. Optional Titel, Dokumenttyp und Projekt/Bereich wählen; sonst ordnet FLOWDOC nach den
   Ablageregeln automatisch zu.
4. Nach der Verarbeitung öffnet sich das neue Dokument als **Entwurf**.

## Hinweise für den Betrieb

- Die Kopfzeile links zeigt den Zugriffsmodus: „im Namen von …“ (angemeldet) oder
  „technisches Konto (Demo)“ (lokaler Demo-Modus ohne Anmeldung).
- Paperless-ngx bleibt für Administration und Ablageregeln unter „FLOWDOC Admin“ erreichbar.
- Paperless-ngx ist kein revisionssicheres Archiv; Aufbewahrung und GoBD werden gesondert gelöst
  (ADR-007, KI-U-03).
