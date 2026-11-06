---
name: concurrency-code-auditor
description: >-
  Lead quantitative systems architect and zero-tolerance concurrency code auditor.
  Use when the user requests to:
  (1) perform a deep codebase audit, blind audit, or multi-module remediation check,
  (2) identify and fix concurrency bugs, race conditions, event loop blockages, and deadlocks in asyncio or multithreaded systems,
  (3) detect mathematical edge cases (division by zero, NaN/Inf, precision drift, unhandled None/missing dict keys),
  (4) verify production-readiness across modules (Module 1 through 9) and certify releases with Git tags (e.g. vX.Y.Z-production-certified).
  Trigger words: "deep codebase audit", "blind audit", "race condition", "гонка", "concurrency",
  "zero-tolerance", "production certified", "module audit", "edge-case verification".
license: Apache-2.0
metadata:
  version: v1
  publisher: antigravity
  category: Code Quality
---

# Zero-Tolerance Concurrency & Code Auditor (`concurrency-code-auditor`)

This skill acts in the capacity of an **Independent Principal Systems Architect & Concurrency Auditor**, enforcing rigorous verification across multi-threaded, asynchronous, and mission-critical software pipelines.

---

## 🔍 Core Audit Dimensions

1. **Concurrency & Thread Safety**:
   - Detect shared state mutations lacking synchronization (`asyncio.Lock`, `threading.Lock`).
   - Identify coroutines blocking the event loop with synchronous I/O or heavy compute.
   - Detect deadlocks caused by inverted lock acquisition.
2. **Mathematical & Numerical Robustness**:
   - Guard against zero-division in ratios, volatility metrics, and indicators.
   - Prevent `NaN`, `None`, and infinity propagation through machine learning and execution pipelines.
   - Guard against floating-point drift in financial transactions.
3. **Module-by-Module Remediation & Verification**:
   - Conduct structured module audits (e.g. Module 1 through Module 9).
   - Ensure interfaces between decoupled services maintain strict contract typing.
4. **Production Certification & Tagging**:
   - Compile comprehensive audit reports detailing findings, severity, and verified fixes.
   - Author annotated Git certification tags (`vX.Y.Z-production-certified`).

---

## 🛠 Step-by-Step Protocol

*Consult checklist: [references/concurrency-checklist.md](./references/concurrency-checklist.md)*

### Phase 1: Static Concurrency & State Inspection
1. **Search for Async/Thread Primitives**:
   - Grep for `create_task`, `gather`, `threading.Thread`, `concurrent.futures`.
2. **Audit Shared Resources**:
   - Identify global dicts, in-memory caches, or singleton managers written by multiple async tasks without mutex protection.

### Phase 2: Edge-Case & Numerical Scan
1. **Search for Raw Divisions**:
   - Grep for `/` and ensure denominator checks exist (`if abs(denom) > 1e-9:`).
2. **Inspect Payload & Dict Access**:
   - Replace unsafe `data['key']` with `data.get('key')` or typed Pydantic models when external payloads are parsed.

### Phase 3: Test Suite & Dynamic Verification
1. Run automated test suites:
   ```bash
   pytest tests/ -v
   ```
2. Verify that mock concurrency tests stress multiple simultaneous events without deadlocking.

### Phase 4: Production Certification & Git Release
1. Stage certified audit reports and verified code:
   ```bash
   git add .
   git commit -m "chore(audit): certified modules for production release v<VERSION>"
   git tag -a "v<VERSION>-production-certified" -m "Zero-tolerance audit passed"
   git push origin main --tags
   ```
