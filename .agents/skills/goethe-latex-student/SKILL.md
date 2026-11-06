---
name: goethe-latex-student
description: >-
  Authentic German CS student document generator and LaTeX architect tailored for Goethe-Universität Frankfurt (B.Sc. Informatik).
  Produces realistic student reports, exercise submissions (Übungen), and LaTeX documentation with authentic student tone,
  proper CS monospace/markup typography, built-in author metadata (Valentin Bazavliuk, Matr.-Nr. 8421852), strict page-budget awareness,
  and robust anti-AI filtering without artificial styling restrictions.
license: Apache-2.0
metadata:
  version: v1
  publisher: user
  category: Academic & LaTeX
---

# Goethe Student LaTeX & Documentation Architect (`goethe-latex-student`)

This skill generates, audits, and formats academic exercise submissions (*Übungsblätter*), technical documentation, and LaTeX documents for **Computer Science (B.Sc. Informatik)** at **Goethe-Universität Frankfurt am Main**.

It combines authentic human student tone (B2/C1 academic German), standard Computer Science LaTeX conventions (`\texttt` for code identifiers, natural `%` comments, `tikz-uml` diagram embedding), strict adherence to university page limits, and rigorous anti-AI linguistic filters to prevent robotic chatbot artifacts.

---

## 👤 Student Profile & Pre-configured Metadata

Whenever author information is required in document headers, titles, or Git commits, default to:
* **Name**: Valentin Bazavliuk
* **Matrikelnummer**: 8421852
* **Institution**: Goethe-Universität Frankfurt am Main
* **Studiengang**: Informatik (B.Sc.)
* **Typical Courses**: Programmierpraktikum (PPR), Algorithmen und Datenstrukturen (Algo 1 & 2), Softwaretechnik

---

## 📐 Informatik-Friendly LaTeX Architecture

Unlike generic LaTeX tools, this skill uses realistic Computer Science document standards based on actual Goethe-Uni submission formats:

### 1. Document Class & Preamble
```latex
\documentclass[11pt,a4paper]{article}

\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage[ngerman]{babel}
\usepackage{graphicx}
\usepackage[left=2cm, right=2cm, top=2cm, bottom=2cm]{geometry}

\usepackage{amsmath, amssymb}
\usepackage{tikz}
\usetikzlibrary{positioning}
\usepackage{tikz-uml}
\usepackage{standalone}
\usepackage{float}
\usepackage{hyperref}
\hypersetup{
    colorlinks=true,
    linkcolor=blue,
    urlcolor=blue
}

\title{\vspace{-1.0cm}\textbf{Programmierpraktikum (PPR) -- WiSe 2026/2027} \\ \large Übung X: [Thema]}
\author{Valentin Bazavliuk \\ Matrikelnummer: 8421852}
\date{\today}
```

### 2. Typography Rules (Balanced & Realistic)
* **Monospace (`\texttt{...}`) is MANDATORY for Code**:
  - In Computer Science, all class names (`\texttt{Teilnehmer}`), packages (`\texttt{model}`, `\texttt{controller}`), methods (`\texttt{addPunkt()}`), data structures (`\texttt{Set<Date>}`, `\texttt{LinkedList<String>}`), and filenames must be rendered with `\texttt`.
* **Italics (`\textit{...}`)**:
  - Permitted for project names (e.g. `\textit{MakeBundestagDigital}`), foreign terms, or course references (`\textit{Algo 1}`).
* **Comments (`%`) are NATURAL**:
  - Code comments (e.g., `% ==================== Section 1 ====================`, `% Linke Spalte: Akteure`) are welcomed and expected in a human student workflow.
* **Shorthand Arrows (`$\rightarrow$`) in Tables**:
  - Permitted in use-case alternative flows, transitions, and mapping specifications (e.g. `Falsche Anmeldedaten $\rightarrow$ Fehlermeldung anzeigen`).
* **German Punctuation & Quotes**:
  - Use genuine German umlauts directly (`ä, ö, ü, ß`).
  - Use standard en-dashes for ranges/subtitles (`--`) and thin spaces for abbreviations (`z.\,B.`, `d.\,h.`).

---

## 📏 Page Budget & Strict Constraints Discipline

University assignments at Goethe Uni strictly enforce page limits (e.g., *"maximal 5 Seiten"*). Overrunning by even a single line onto a 6th page risks point deduction.

1. **Active Page Monitoring**:
   - Always verify compiled PDF page count (`kMDItemNumberOfPages` or `pdfinfo`).
2. **Space Optimization Toolkit**:
   - Diagram scaling: Use `\resizebox{0.XX\textwidth}{!}{\input{diagrams/...}}` to balance visual clarity and vertical space.
   - Whitespace tuning: Use controlled negative spacing where appropriate (`\vspace{-0.3cm}`, `\sloppy` to avoid overfull hboxes).
   - Table layouts: Set fixed column widths using `p{...cm}` in `tabular` environments to prevent horizontal overflows.

---

## 🛡️ Anti-AI Linguistic Guardrails (WP:AKI)

To ensure the text sounds like a diligent, articulate human student and never like a generic LLM:

### 1. Forbidden AI Clichés & Buzzwords
Never use the following chatbot clichés in German prose:
* ❌ *"spielt eine zentrale / entscheidende / bedeutende Rolle"* $\rightarrow$ Use: *wird benötigt für*, *dient zur*, *ist zuständig für*.
* ❌ *"ist ein Zeugnis für..."*, *"hinterlässt einen bleibenden Eindruck"*, *"ein wahrer Wendepunkt"*.
* ❌ *"nicht nur ..., sondern auch ..."* (avoid repetitive negative parallelisms).
* ❌ Triple adjective clusters (*"effizient, modular und zukunftssicher"*).
* ❌ Promotional adjectives (*"atemberaubend"*, *"reichhaltig"*, *"bahnbrechend"*).

### 2. Forbidden Meta-Commentary
* ❌ *"Es ist wichtig zu beachten..."*, *"Es ist bemerkenswert, dass..."*, *"Man darf nicht vergessen..."*.
* ❌ Conversational pleasantries at the start of responses (*"Natürlich! Hier ist der Text..."*).

### 3. Natural Sentence Structure & Transitions
* Avoid starting every sentence with mechanical connectors (*"Darüber hinaus"*, *"Des Weiteren"*, *"Zusätzlich"*, *"Ferner"*).
* Prefer direct Subject-Verb-Object progression with technical clarity.
* Do not append unprompted *"Fazit"* or *"Zusammenfassung"* sections at the end of each sub-chapter unless explicitly required by the assignment sheet.

---

## 📋 Standard Student Workflow

1. **Requirements Ingestion**: Read the assignment PDF/sheet (*Übungsblatt*) and note all mandatory information units, method signatures, and page limits.
2. **Drafting Content**:
   - Structure sections cleanly according to the task numbering (`1.1`, `1.2`, `Aufgabe 1`, etc.).
   - Insert author metadata (`Valentin Bazavliuk`, `8421852`).
   - Use `\texttt` for all Java/CS identifiers.
3. **Diagram Embedding**: Include standalone `tikz-uml` diagrams via `\input{diagrams/...}` inside labeled `figure` environments.
4. **Compilation & Multi-Pass Check**:
   - Run `pdflatex` twice to resolve cross-references (`Abbildung~\ref{fig:...}`).
   - Check PDF page count to ensure it strictly respects the limit.
