# Reusable Goethe-Uni CS LaTeX Templates

This reference contains tested LaTeX patterns and text templates drawn directly from successful submissions in Computer Science at Goethe University Frankfurt.

---

## 1. Use-Case Specification Table Pattern
Clean 2-column tabular specification fitting exactly on standard A4 with 2cm margins:

```latex
\noindent
\begin{tabular}{|p{3.8cm}|p{12.2cm}|}
\hline
\textbf{Use-Case [ID]} & \textbf{[Name des Anwendungsfalls]} \\ \hline
\textbf{Akteure} & [Akteur 1, Akteur 2] \\ \hline
\textbf{Vorbedingung} & [Bedingung vor Ausführung, z.\,B. Benutzer ist angemeldet.] \\ \hline
\textbf{Ergebnis (Erfolg)} & [Zustand nach erfolgreicher Durchführung.] \\ \hline
\textbf{Beschreibung} & 1. [Schritt 1] 2. [Schritt 2] 3. [Schritt 3] \\ \hline
\textbf{Alternativen / Fehler} & [Ausnahmezustand] $\rightarrow$ [Fehlermeldung anzeigen / Abbruch]. \\ \hline
\end{tabular}
\vspace{0.3cm}
```

---

## 2. Diagram Embedding (Standalone TikZ-UML)
Proper embedding ensuring scalable vector rendering, centered alignment, and cross-reference labels:

```latex
\begin{figure}[H]
    \centering
    \resizebox{0.92\textwidth}{!}{\input{diagrams/Klassen_Diagramm.tex}}
    \caption{Klassendiagramm des Systems mit Rollenhierarchie und Beziehungen.}
    \label{fig:class}
\end{figure}
```

*Note: Always compile `main.tex` twice with `pdflatex` to resolve `\ref{fig:class}` without displaying `??`.*

---

## 3. Justification Formulas (Anti-AI Student Phrasing)

### A. Architectural Pattern (MVC)
> „Die Applikation ist nach dem Model-View-Controller-Muster (MVC) gegliedert, um eine saubere Trennung der Zuständigkeiten (*Separation of Concerns*) zu gewährleisten: Datenhaltende Klassen liegen im Paket \texttt{model}, Prozess- und Validierungslogik in \texttt{controller} und die grafische Oberfläche in \texttt{view}. Änderungen an der Benutzeroberfläche haben somit keine Rückwirkungen auf die Geschäftslogik.“

### B. Abstract Classes vs. Interfaces
> „Die Basisklasse \texttt{Teilnehmer} ist als abstrakte Klasse modelliert. Da im System jede Person eine konkrete Funktion einnimmt, soll keine direkte Instanziierung von \texttt{Teilnehmer} möglich sein. Gemeinsame Zustandsattribute (\texttt{id}, \texttt{name}, \texttt{email}) und Berechtigungsmethoden werden in der Oberklasse gebündelt und an die spezialisierten Klassen vererbt.“

### C. Data Structure Justifications (Algo 1 Reference)
> * **\texttt{Set<Typ>}:** „Für die Speicherung von Teilnehmern und Zugangstagen wird ein \texttt{Set} verwendet. In diesen Kontexten ist die Reihenfolge der Elemente irrelevant, jedoch müssen Duplikate zwingend verhindert werden.“
> * **\texttt{LinkedList<Typ>}:** „Für Tagesordnungspunkte wird eine \texttt{LinkedList} eingesetzt, da Sitzungspunkte in einer festen chronologischen Reihenfolge abgearbeitet werden und neue Punkte flexibel eingefügt werden müssen.“

### D. Relationships (Composition vs. Aggregation)
> * **Komposition:** „Zwischen \texttt{Veranstaltung} und \texttt{Tagesordnung} besteht eine strikte Komposition (1:1), da eine Tagesordnung existentiell an ihre Veranstaltung gebunden ist und bei deren Löschung mitgelöscht wird.“
> * **Aggregation:** „Zwischen \texttt{Veranstaltung} und \texttt{Teilnehmer} liegt eine Aggregation vor, da Personen auch nach Absage eines Termins als eigenständige Entitäten im System erhalten bleiben.“

---

## 4. Effort Estimation Table Pattern (Aufwandsschätzung)

```latex
\noindent
\begin{tabular}{|p{5.0cm}|p{8.5cm}|r|}
\hline
\textbf{Phase / Teilaufgabe} & \textbf{Inhaltliche Schwerpunkte} & \textbf{Stunden} \\ \hline
1. Planung \& UML-Spezifikation & Anforderungsanalyse, Datenmodellierung, Git-Setup & 15 h \\ \hline
2. Datenmodell (\texttt{model}) & Entitätsklassen, Rollenhierarchie, Kapselung & 35 h \\ \hline
3. Geschäftslogik (\texttt{controller}) & Konfliktprüfung, Berechtigungsvalidierung & 35 h \\ \hline
4. Persistenz \& Schnittstellen & Datenhaltung, Serialisierung, Fehlerbehandlung & 25 h \\ \hline
5. Benutzeroberfläche (\texttt{view}) & Dialoge, Termindarstellung, Ereignisverarbeitung & 30 h \\ \hline
6. Testen \& Dokumentation & Unit-Tests, Code-Reviews, Abschlussdokumentation & 20 h \\ \hline
\textbf{Gesamtaufwand} & \textbf{Vollständige Produktreife} & \textbf{160 h} \\ \hline
\end{tabular}
```
