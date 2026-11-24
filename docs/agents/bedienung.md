# Bedienungsanleitung: Agentenzentrale, Fachaufträge und FLOWDOC

**Stand:** 2026-11-22 · für Product Owner, Tech Lead, Key User, Release-Verantwortung und Plattformbetrieb

Diese Anleitung beschreibt Schritt für Schritt, wie du mit FLOWAGENTS (dem KI-Entwicklungsteam) und
FLOWDOC (der eigenen DMS-Oberfläche) arbeitest. Hintergrund und Regeln:
[FLOWAGENTS](index.md), [Sicherheitskonzept](sicherheitskonzept.md), [Betrieb](betrieb.md).

## 1. Starten und prüfen (einmal pro Arbeitstag)

| Schritt | Befehl / Ort | Erwartung |
|---|---|---|
| Plattform starten | `make sso-all` | Container laufen, Portal unter `http://localhost:8088` |
| Prüfimage (nur einmal) | `make agents-sandbox-image` | Image `flow-agents-sandbox:1` |
| Orchestrator starten | `make agents-up` | „FLOWAGENTS gestartet“ |
| Wissen für FLOWAI | `make mcp` | Wiki-, DMS- und ERP-Werkzeuge für Open WebUI |
| Gesamtprüfung | `make agents-smoke` | acht Zeilen „OK“ |
| Anforderungen abgleichen | `make requirements-sync` | Katalog liegt in FLOWWORK |

Ollama muss laufen (Ollama-App auf dem Mac). Die Modelle werden beim ersten Aufruf geladen; der erste
Schritt eines Laufs dauert deshalb länger.

## 2. Anmelden und Rollen

Anmeldung über FLOWID (Keycloak) im Portal. Was du entscheiden darfst, hängt an deinen Rollen:

| Du bist … | FLOWID-Rolle (AD-Gruppe) | Du entscheidest | Demo-Konto |
|---|---|---|---|
| Product Owner | `flow-po` (`AD-GG-FLOW-AGENTS-PO`) | Fachaufträge einreichen, G1 (Anforderungen fachlich freigeben), Rückfragen der Agenten | `po.demo` |
| Tech Lead | `flow-techlead` (`AD-GG-FLOW-AGENTS-TECHLEAD`) | G2/G3 bei kritischen Änderungen, Blockaden, Korrekturlimit, Laufbudget, Läufe pausieren/abbrechen | `techlead.demo` |
| Key User | `flow-keyuser` (`AD-GG-FLOW-AGENTS-KEYUSER`) | G4 Fachabnahme in der Vorschau | `keyuser.demo` |
| Release | `flow-release` (`AD-GG-FLOW-AGENTS-RELEASE`) | G5 Produktionsfreigabe | `release.demo` |
| Informationssicherheit | `flow-isb` (`AD-GG-FLOW-AGENTS-ISB`) | Sicherheitsrückfragen der Agenten, Audit einsehen; keine Gate-Freigabe | `isb.demo` |
| Geschäftsführung | `flow-gf` (`AD-GG-FLOW-AGENTS-GF`) | Grundsatzfragen des Geschäftsführungs-Agenten | `gf.demo` |

`admin.demo` hat alle Freigaberollen zusätzlich zum Plattform-Vollzugriff – für Einzelvorführungen.
Die Plattform-Administration (`platform-admin`) enthält die Freigaberollen **nicht**: Betrieb und
fachliche Freigabe sind getrennt. Alle Demo-Konten nutzen das Demo-Passwort aus
`scripts/generate_iam_demo.py`.

**Freigabeprozess vorführen:** In getrennten Browserfenstern (oder privaten Fenstern) als
`po.demo` einen Fachauftrag einreichen und G1 freigeben, als `techlead.demo` G2/G3 und Blockaden
entscheiden, als `keyuser.demo` die Vorschau abnehmen (G4) und als `release.demo` G5 freigeben.
Jede andere Person erhält bei fremden Entscheidungen „Keine Befugnis“.

## 3. Die Agentenzentrale lesen

Auf der Startseite (kompakt) und unter **`/agents`** (vollständig):

- **Kennzahlen:** Agenten im Register, wer gerade arbeitet, offene Aufträge, *Warten auf dich*,
  Rückläufe.
- **Zusammenarbeit live:** Kreise = Agenten (Nummer 01–11, GF = Geschäftsführungs-Agent),
  Rauten = Gates G1–G5, unten die Menschen. Ein leuchtender Ring heißt „arbeitet“, gelb heißt
  „wartet auf einen Menschen“. Linien: türkis Übergabe, rot Rücklauf nach Prüfbefund, gelb Frage an
  einen Menschen, lime Entscheidung, blau Schreibzugriff in FLOWWORK. Klick auf einen Knoten zeigt
  Auftrag, Stufe, Werkzeuge und letzte Aktion.
- **Live-Protokoll:** jedes Ereignis mit Uhrzeit.
- **Aufträge:** Fortschritt, aktueller Schritt, wartende Rolle, übernommener Branch. Klick öffnet
  die Laufdetails (Verlauf, Entscheidungen, alle Ergebnisse inkl. Diff und Nachweise).
- **Rechte der Agenten** (Seite *Agenten*): Matrix, welcher Agent über welche technische Rolle
  welche Werkzeuge hat, welches Modell er nutzt (und ob komplexe Aufträge an Codex/Claude gehen),
  welche Datenklassen er verarbeiten darf und welche menschliche Rolle sein Ergebnis freigibt –
  mit der zugehörigen Keycloak-Rolle. Klick auf einen Agenten zeigt die Einzelheiten: wer jedes
  Werkzeug prüft (FLOWWORK RM-Adapter, Orchestrator-Sandbox), was er liest, seine Grenzen und was er
  nie darf.

### Meine Sicht und Alle

Oben rechts in der Agentenzentrale wechselt man zwischen zwei Ansichten (die Wahl bleibt im Browser
gespeichert):

| Ansicht | Zeigt |
|---|---|
| **Meine Sicht** | nur Aufträge, an denen du beteiligt bist (selbst beauftragt, selbst entschieden oder sie warten auf eine deiner Entscheidungsrollen); auf der Karte sind nur die Agenten dieser Aufträge, deine Entscheidungsrollen und die betroffenen Gates hervorgehoben |
| **Alle** | alle Aufträge, Entscheidungen und Agenten; Aufträge mit deiner Beteiligung tragen den Hinweis „du bist beteiligt“ |

Die Liste **„Wo es gerade hängt“** nennt je offenem Auftrag, bei wem er liegt: bei einem **Agenten**
(mit Zustand, z. B. „arbeitet“), bei einer **Person** in einer Entscheidungsrolle (mit „du“, wenn du sie
hast), oder **blockiert**/**pausiert** mit Grund, jeweils mit „seit …“. Ein Klick öffnet den Auftrag.

### Konfiguration eines Agenten ansehen und ändern

In der Vollansicht `/agents` steht unten das **Agentenregister**: je Agent eine Karte mit technischer
Rolle, Ersteller oder Prüfer, Stufe, Status, Verantwortlichen, **Aufgaben** (die Schritte im Ablauf und
was dabei entsteht, z. B. „Akzeptanztests aus der Baseline ableiten – erstellt akzeptanztests“), wer
prüft und freigibt, Modell und Ausführung, Werkzeuge, lesbare Ergebnisse, Datenklassen, Grenzen,
Eskalation und Freigabedatum. Geänderte Agenten tragen den Hinweis „… Felder geändert“.

Von dort, oder auf der Karte über einen Agenten, öffnet **Konfiguration und Prompt ansehen** bzw.
**Konfiguration ändern** das Konfigurationsfenster. Das Fenster zeigt alles, was
den Agenten ausmacht: Ausführung (lokal über FLOWGATE, OpenCode, Codex/Claude), Modell und Modellfamilie,
Status, Stufe, Verantwortliche, Auftrag, Werkzeuge, lesbare Ergebnisse, Datenklassen, Grenzen, die
vollständige Rollenanweisung (Prompt) und das Änderungsprotokoll.

- **Alle Angemeldeten** sehen die Konfiguration, die Felder sind gesperrt.
- **Administratoren** (`platform-admin`, z. B. `admin.demo`) ändern Felder und speichern mit Begründung.
  Der Orchestrator prüft die Änderung wie das Agentenregister: Prüfer bleiben unabhängig vom Ersteller
  (andere Modellfamilie), Testagenten lesen keine Implementierung, nur bekannte Werkzeuge ohne Freigabe-,
  Merge-, Lösch- oder Deployrechte, nur bekannte Datenklassen, Stufe höchstens A3. Ungültiges wird mit
  Grund abgelehnt.
- Geänderte Felder tragen das Zeichen *geändert* (der Registerwert steht im Tooltip). **↺ Register**
  setzt ein Feld auf den Wert aus `agents/registry.yaml` bzw. der Prompt-Datei zurück.
- Jede Änderung ändert den **Registerstand**. Offene Aufträge halten dann mit „Agentenregister oder
  Ablauf wurden geändert“ an, bis ein Mensch sie auf den neuen Stand umstellt.
- Gespeichert wird als Übersteuerung in der Orchestrator-Datenbank (`agent_settings`, Protokoll in
  `agent_settings_log`), nicht in der YAML-Datei. Soll eine Änderung dauerhaft ins Repository, trägt man
  sie in `agents/registry.yaml` ein und setzt das Feld danach zurück.

## 4. Einen Fachauftrag erteilen

1. **＋ Fachauftrag starten**.
2. **Titel** und **Zweck**: Welche Arbeit soll leichter werden?
3. **Nutzergruppe** und **gewünschtes Verhalten** so konkret wie möglich.
4. **Erfolgsbeispiel**: ein beobachtbares Beispiel („Bei Beta und Alpha erscheint Alpha zuerst“).
   Daraus werden Akzeptanzkriterien.
5. **Ausgeschlossen**: was sich nicht ändern darf (z. B. Rechte, Status).
6. **Änderungsklasse**:
   - *Standardänderung* – Text, Sortierung, Anzeige ohne neue Daten; du entscheidest nur G4 und G5.
   - *Neue Funktion* – neues Verhalten; zusätzlich G1.
   - *Hoher Schutzbedarf* – Rechte, Löschung, Migration, Export; alle Gates.
7. **Änderungsbereich** (nur diese Dateien darf der Entwicklungs-Agent ändern):

| Bereich | Inhalt |
|---|---|
| `dms-doku` | Benutzerhilfe zu Dokumenten |
| `dms-ui` | FLOWDOC-Oberfläche (`dms.js`, `dms.css`) |
| `dms-backend` | Paperless-Anbindung (`dms.py`) mit Tests |
| `dms-komplett` | Oberfläche, Backend, Tests und Hilfe zusammen |
| `portal-hilfe` | Portal- und Agentenhilfe |

8. **Auftrag einreichen.** Zuerst bewertet der Geschäftsführungs-Agent den Auftrag (Nutzen, Aufwand,
   Abläufe, Risiko). Hat er erhebliche Bedenken, fragt er dich.

**Tipp:** Kleine, klar abgegrenzte Aufträge gelingen mit lokalen Modellen deutlich besser als große.
Lieber drei Aufträge hintereinander als einen „baue alles um“.

## 5. Entscheiden

Entscheidungen erscheinen unter **Deine Entscheidungen**. Jede Karte nennt Frage, Lauf und – bei
G3–G5 – den Digest, an den deine Entscheidung gebunden ist.

| Entscheidung | Annehmen bedeutet | Ablehnen bedeutet |
|---|---|---|
| **Rückfrage** eines Agenten | Deine Antwort (Kommentarfeld) fließt in den nächsten Versuch ein | Lauf wird abgebrochen |
| **G1 Anforderungen** | Arbeitsbaseline ist fachlich freigegeben | Begründung geht als Befund an den Anforderungs-Agenten |
| **G2/G3** | Architektur bzw. Integrationsstand bestätigt | zurück an Architektur bzw. Entwicklung |
| **G4 Fachabnahme** | Kandidat ist fachlich richtig; er wird als Branch übernommen | Begründung geht an die Entwicklung, neuer Kandidat folgt |
| **G5 Produktion** | Freigabe wird protokolliert; ausgerollt wird manuell | Lauf endet als „abgelehnt“ |
| **Eskalation** (Bedenken der Geschäftsführung) | trotzdem fortfahren | Lauf abbrechen |
| **Korrekturlimit / Blockade** | weitere Runde bzw. denselben Schritt erneut versuchen | Lauf abbrechen |
| **Laufbudget erschöpft** | 20 weitere Modellaufrufe freigeben | Lauf abbrechen |

**Ablehnungen immer konkret begründen** („Punkt 3 ist falsch: …, bitte so formulieren: …“). Die
Begründung ist das Einzige, was der Agent von deiner Prüfung erfährt.

## 6. Fachabnahme in der Vorschau (G4)

1. In der G4-Karte **Kandidat in der Vorschau prüfen ↗** öffnen (`http://localhost:8098/dms`).
   Die Vorschau läuft im Demo-Modus mit Testdaten; der Code ist genau der geprüfte Kandidat.
2. Das Erfolgsbeispiel aus dem Auftrag nachspielen. Bei Hilfetexten: Stimmt jede Aussage mit der
   Oberfläche überein? Lokale Modelle erfinden gern Verhalten.
3. In den **Laufdetails** (Klick auf den Auftrag) unter *implementierung* den Diff ansehen.
4. **Annehmen** oder mit Begründung **Ablehnen**. Nach der Entscheidung stoppt die Vorschau.

## 7. Ergebnis übernehmen

Nach angenommener Fachabnahme liegt der Stand als Branch im Repository:

```bash
git branch --list 'agent/*'
git log -1 agent/A-001-…          # Commit mit Auftrag, Lauf, Abnahme und Digest
git diff main...agent/A-001-…     # Änderung ansehen
```

Prüfen, bei Bedarf nacharbeiten und **selbst mergen**. Danach G5 entscheiden. Mit
`adoption.push: true` in `services/agent_orchestrator/config/orchestrator.yaml` wird der Branch
zusätzlich gepusht (öffentliches Repository beachten).

## 8. Wenn etwas hängt

| Anzeige | Ursache | Was tun |
|---|---|---|
| „Orchestrator meldet sich nicht“ | Dienst läuft nicht | `make agents-up`, dann `make agents-smoke` |
| „FLOWGATE nicht erreichbar“ | Gateway oder Ollama aus | Ollama-App starten, `make ai-gateway` |
| „Ergebnisvertrag verletzt“ zweimal | Modell liefert unvollständige Antwort | Tech Lead: *Annehmen* = erneut versuchen |
| „Korrekturlimit erreicht“ | Prüfer und Ersteller einigen sich nicht | Befunde in den Laufdetails lesen; weitere Runde oder abbrechen und Auftrag präziser neu stellen |
| „Agentenregister geändert“ | Register oder Rollenanweisungen geändert | Tech Lead stellt den Lauf bewusst um oder bricht ab |
| Agent „pausiert“ | Stopp-Schalter aktiv | in `/agents` → Agent anklicken → fortsetzen (Plattformbetrieb) |
| Vorschau fehlt | Plattform-Image fehlt oder Port 8098 belegt | `docker ps`, Fehlertext in der G4-Karte |

Laufenden Zustand im Terminal: `make agents-status`; Log: `make agents-logs`.

## 9. FLOWDOC bedienen

FLOWDOC ist die eigene Dokumentenoberfläche unter **`/dms`** (Details: [FLOWDOC](../user-guides/flowdoc.md)):

- **Suchen** im Volltext oben, **filtern** links nach Status, Dokumenttyp, Projekt/Bereich,
  Korrespondent, **sortieren** über das Auswahlfeld *Sortierung* (Titel A–Z/Z–A, Datum, Typ, …).
- **Dokument anklicken:** Vorschau, Metadaten, Notizen, erkannter Text, Download.
- **Status:** *Zur Prüfung geben* → *Freigeben* oder *Zurückweisen*; ob du darfst, entscheidet
  Paperless.
- **↑ Dokument ablegen:** Datei ziehen, optional Typ und Projekt, neue Dokumente starten als Entwurf.
- FLOWDOC zeigt nur, was du in Paperless lesen darfst – auch Titel und Trefferzahlen.

## 10. FLOWAI fragen

In FLOWAI (Open WebUI, `http://localhost:3001`) ist diese Anleitung als Unternehmenswissen
hinterlegt (Werkzeug „Unternehmenswissen“). Beispiele:

- „Wie erteile ich einen Fachauftrag an die Agenten?“
- „Was bedeutet G4 und was passiert nach der Annahme?“
- „Welche Sicherheitsregeln gelten für die Agenten?“
- „Was tue ich bei ‚Korrekturlimit erreicht‘?“

## 11. FLOWAI mit Zugriff auf das Repository

Im Chat (Open WebUI, `http://localhost:3001`) unter **＋ → Werkzeuge** „Entwicklung & Repository“
einschalten (zusätzlich gern „Unternehmenswissen“). Am besten mit `qwen3-coder:30b`.

**Fragen stellen** – FLOWAI liest Code, Doku, Agentenregister und Anforderungen (nur lesend, ohne
`.env` und Geheimnisse) und nennt Pfad und Zeilen:

- „Welche Dateitypen erlaubt der FLOWDOC-Upload und wo ist das definiert?“
- „Warum hängt Auftrag A-002?“ (Werkzeug `agent_status`)
- „Wie prüft der RM-Adapter die Agenten-Tokens?“

**Änderung anstoßen** – FLOWAI ändert nie selbst etwas. Es legt mit `propose_fachauftrag` einen
**Vorschlag** an und nennt den Link:

1. Im Chat beschreiben, was sich ändern soll („Ich möchte .stl-Dateien hochladen können …“).
   FLOWAI klärt Erfolgsbeispiel und Änderungsbereich.
2. Der Vorschlag erscheint in FLOWPORTAL unter **Zu prüfen** („Vorschlag aus FLOWAI“).
3. **Prüfen und einreichen** öffnet das ausgefüllte Fachauftragsformular; du ergänzt es und reichst
   es mit deiner FLOWID-Anmeldung ein – oder **verwirfst** ihn.
4. Danach läuft der Auftrag wie jeder andere durch die Agenten und deine Gates.

