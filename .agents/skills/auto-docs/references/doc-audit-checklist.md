# Documentation Audit & Reconciliation Checklist

When a repository already contains documentation (`README.md`, `docs/`, docstrings, wiki), use this checklist to systematically verify and reconcile the documentation against the actual codebase.

---

## 🔍 Audit Steps

### 1. File & Directory Reference Verification
- [ ] Check every file path, directory link, and script mentioned in the docs.
- [ ] Do all referenced files actually exist in the repository?
- [ ] Have any files been renamed, moved, or deleted? Update links and descriptions accordingly.
- [ ] Are new core modules or directories missing from the project structure section?

### 2. Dependency & Version Synchronization
- [ ] Check `pyproject.toml`, `package.json`, `go.mod`, `Cargo.toml`, or `requirements.txt`.
- [ ] Is the recommended runtime version (e.g., Python 3.10 vs 3.12, Node 18 vs 22) up-to-date with reality?
- [ ] Are documented setup/install commands using outdated tooling (e.g. `setup.py install` instead of `pip install -e .` or `uv`)?
- [ ] Are all required system dependencies (e.g., `ffmpeg`, `libpq-dev`, `docker`) explicitly stated?

### 3. CLI Commands & Scripts Validation
- [ ] Inspect every code block containing terminal commands.
- [ ] Check CLI arguments and flags against the parser in code (e.g. `argparse`, `click`, `commander`, `cobra`).
- [ ] Are default parameter values listed in docs matching the actual defaults in code?
- [ ] Are deprecated or removed flags still documented? Remove them.
- [ ] Are newly added CLI options missing from the command reference?

### 4. Configuration & Environment Variables Audit
- [ ] Search the codebase for `os.environ`, `process.env`, `getenv`, `viper`, or config loader logic.
- [ ] Reconcile every found environment variable against the README / docs config table.
- [ ] Ensure `.env.example` exists and matches the configuration table with sane placeholder values.
- [ ] Ensure NO production passwords, secret keys, or live credentials are leaked in docs or `.env.example`.

### 5. API Endpoints & Interfaces Audit
- [ ] Compare documented endpoints with actual router/controller definitions.
- [ ] Verify HTTP methods (`GET`, `POST`, `PUT`, `DELETE`), URL paths, and URL params.
- [ ] Verify request payload JSON schema and required fields against route validators (e.g. Pydantic, Zod).
- [ ] Check response status codes and sample responses.

### 6. Architecture & Data Flow Alignment
- [ ] Is there an existing architecture diagram? If not, create one.
- [ ] If an architecture diagram exists, does it reflect recent additions (e.g., new microservices, caching layers, message queues)?
- [ ] Update obsolete component relationships using modern Mermaid diagrams.

### 7. Markdown Formatting & Quality Check
- [ ] Ensure valid GitHub Flavored Markdown (GFM).
- [ ] Fix unrendered tables, broken blockquotes, unescaped special characters in Mermaid code.
- [ ] Ensure code blocks have explicit language identifiers (` ```python `, ` ```bash `, ` ```typescript `).
- [ ] Remove dead external links and fix broken internal relative anchors.
