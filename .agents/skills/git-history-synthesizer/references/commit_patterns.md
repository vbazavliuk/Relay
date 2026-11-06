# Realistic Commit Patterns & Behavioral Heuristics

This reference catalog provides natural, authentic commit messages and development patterns to ensure synthesized git histories look completely genuine.

---

## 🇩🇪 German Commit Patterns (Standard for German Universities)

German students typically use lower-case or capitalized short phrases, occasionally mixing colloquial German and light tech-English.

### 1. Setup & Scaffolding (Day 1)
* `init repo`
* `initial commit`
* `gitignore hinzugefuegt`
* `ordnerstruktur angelegt`
* `readme angefangen`
* `todo liste erstellt` *(Temporary scratch file)*
* `basisdateien hinzugefuegt`

### 2. Early Drafts & Architecture (Day 2)
* `erste skizze fuer klassenmodell`
* `diagramm entwurf angefangen`
* `basisklassen angelegt`
* `attribute und methoden ergaenzt`
* `zwischenstand usecases`
* `notizen zu raumbuchung ergaenzt` *(Temporary scratch file)*
* `package aufteilung ueberlegt`

### 3. Human Flaws & Student Mistakes (Days 2–3)
* `wip diagramm`
* `typo im klassennamen`
* `kompilierungsfehler in main.tex`
* `layout kaputt 6 seiten`
* `seitenumbruch zerschossen`
* `vergessenes import ergaenzt`
* `pfad zu diagrammen war falsch`
* `farben im usecase passen noch nicht ganz`

### 4. Repairs & Bugfixes (Days 3–4)
* `layout gefixt, jetzt wieder 5 seiten`
* `seitenumbruch korrigiert`
* `syntaxfehler in tikz behoben`
* `nullpointer bei teilnehmerpruefung verhindert`
* `todo liste aktualisiert`
* `ueberfluessige leerzeilen entfernt`

### 5. Tutor & Peer Review Feedback Integration (Days 3–4)
* `feedback vom tutor eingearbeitet`
* `tutor hinweis: rollen als vererbungshierarchie statt strings umgesetzt`
* `tutor feedback: vorbelegungsrecht als boolean methode ergaenzt`
* `peer review anmerkungen: diagramm farben und unnoetige notizen entfernt`
* `notiz fuer vorbelegungsrecht hinzugefuegt (tipp von kollege)`
* `ruecksprache mit tutor: teilnehmer als abstrakte klasse definiert`

### 6. Cleanup & Scratch Removal (Days 4–5)
* `todo.txt entfernt, alles erledigt`
* `temporaere notizen aufgeraeumt`
* `diagrammfarben einheitlich gemacht`
* `code formatiert und kommentare bereinigt`
* `gitignore fuer latex hilfsdateien angepasst`

### 7. Final Polish & Submission (Day 5)
* `matrikelnummer und deckblatt eingetragen`
* `doku kapitel 2 fertiggestellt`
* `letzter feinschliff vor abgabe`
* `abgabe fertig`
* `main.pdf kompiliert`

---

## 🇬🇧 English Commit Patterns (International Codebases)

### 1. Setup & Scaffolding
* `chore: initial project setup`
* `feat: add project skeleton and directory structure`
* `chore: add .gitignore for build artifacts`
* `docs: add initial README with project overview`
* `chore: add draft task list (TODO.md)`

### 2. Implementation & Drafts
* `feat: scaffold core domain entities`
* `wip: initial draft of data models`
* `feat: implement user role hierarchy`
* `refactor: extract abstract base class`
* `feat: add booking conflict validation`

### 3. Human Mistakes & Quick Fixes
* `fix: typo in method signature`
* `fix: broken layout overflow in report`
* `fix: missing dependency import`
* `wip: debugging compilation warning`
* `fix: resolve page count constraint`

### 4. Review & Feedback Integration
* `refactor: incorporate tutor feedback on inheritance structure`
* `fix: apply code review suggestions for encapsulation`
* `refactor: replace string role with polymorphic hierarchy per tutor suggestion`
* `docs: clarify time complexity analysis based on feedback`

### 5. Cleanup & Delivery
* `chore: remove temporary notes and scratch files`
* `docs: finalize submission report and diagrams`
* `build: generate final release artifact`
* `release: final submission build`

---

## ⏱ Temporal Heuristics for Realistic Intervals

To make git history look 100% human:
1. **Never use fixed intervals**: Avoid exactly 5, 10, or 15 minute gaps. Human commits have variance:
   - Quick successive commits (debugging typos/layout): **3 to 12 minutes**.
   - Feature development bursts: **25 to 65 minutes**.
   - Lunch / Break gaps: **1.5 to 3.5 hours**.
   - Day transitions: **14 to 22 hours**.
2. **Realistic Time Windows**:
   - University students typically commit between **13:30 and 18:30** or **20:00 and 23:45**.
   - Avoid commits during typical sleeping hours (03:00 to 07:30) unless intentionally simulating a last-night deadline crunch.
3. **Clustering**:
   - Most commits cluster into 2–3 active work sessions per day.
