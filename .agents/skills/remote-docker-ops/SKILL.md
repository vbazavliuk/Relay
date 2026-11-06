---
name: remote-docker-ops
description: >-
  Specialized remote Docker stack and server forensic engineer for production infrastructure.
  Pre-configured for servers valentin@100.103.31.103 (Tailscale) and valentin@192.168.1.110 (LAN) under /opt/stacks/.
  Use when the user requests to:
  (1) perform read-only forensic inspection, trade timeline audits, or EOD container checks on the production server,
  (2) build, rebuild, deploy, or update docker-compose stacks atomically (e.g. trading_sentinel, autopilot_paper_trading),
  (3) inspect live or historical container logs, resource utilization (CPU, memory, disk), or crashed daemon forensics,
  (4) sync stack files, environment templates, or run remote diagnostics via SSH.
  Trigger words: "docker compose", "сервер", "деплой", "логи контейнера", "100.103.31.103", "192.168.1.110",
  "/opt/stacks", "autopilot_paper_trading", "trading_sentinel", "EOD verification", "remote inspection".
license: Apache-2.0
metadata:
  version: v1
  publisher: antigravity
  category: DevOps
---

# Remote Docker & Server Forensic Operations (`remote-docker-ops`)

This skill standardizes safe, atomic, and forensic operations for remote Docker stacks running on production hosts (`valentin@100.103.31.103` / `valentin@192.168.1.110`) in `/opt/stacks/`.

---

## 🧭 Host Context & Routing

*Reference: [references/server-profiles.md](./references/server-profiles.md)*

- **Default Remote Host**: `valentin@100.103.31.103` (Tailscale VPN)
- **Local LAN Host**: `valentin@192.168.1.110` (Direct local Wi-Fi / Ethernet fallback)
- **Primary Stack Directory**: `/opt/stacks/` (typically `/opt/stacks/option/` or `/opt/stacks/bots/`)
- **Key Services**: `autopilot_paper_trading`, `trading_sentinel`, `option_autopilot`

---

## 🛡 Operating Rules & Guardrails

> [!CAUTION]
> **Safety Invariants**:
> 1. **Zero Data Loss**: NEVER execute `docker compose down -v` or `docker volume rm`.
> 2. **Atomic Execution**: Always link build, start, and verification in one command string so that failure at build step never leaves a running container killed or missing.
> 3. **Non-Destructive Audits**: For requests labeled `Audit`, `Forensic Inspection`, or `EOD Verification`, run **strictly read-only** commands (`docker ps`, `docker logs`, `grep`, `cat`). Never restart or modify containers unless explicitly instructed.
> 4. **SSH Timeout & Error Handling**: Include standard SSH options (`-o ConnectTimeout=5 -o BatchMode=yes`) to fail fast if connection hangs.

---

## Workflows

### 1. Read-Only Forensic Audit / EOD Verification

Use this when the user asks for a trade audit, EOD inspection, or status check:

1. **Verify Connectivity & Running State**:
   ```bash
   ssh -o ConnectTimeout=5 valentin@100.103.31.103 "docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'"
   ```
2. **Inspect Container Logs for Trades, Errors, and Warnings**:
   ```bash
   ssh valentin@100.103.31.103 "cd /opt/stacks/option && docker compose logs --tail=200 <SERVICE_NAME>"
   ```
3. **Filter Specific Time Windows or Regex**:
   ```bash
   ssh valentin@100.103.31.103 "cd /opt/stacks/option && docker compose logs --since 8h <SERVICE_NAME> | grep -E '(TRADE|FILL|ORDER|ERROR|PnL|Peak)' | tail -n 100"
   ```
4. **Format Structured Forensic Output**:
   Present the user with:
   - Container uptime and health status.
   - Chronological summary of executed actions / orders.
   - Any unhandled exceptions or error warnings.

---

### 2. Atomic Build, Deploy & Verify

Use this when code has been updated and containers need a clean rebuild without downtime surprises:

1. **Chain Build + Up + Check in a Single Invocable Command**:
   ```bash
   ssh valentin@100.103.31.103 "cd /opt/stacks/option && docker compose build --no-cache <SERVICE_NAME> && docker compose up -d <SERVICE_NAME> && docker compose ps <SERVICE_NAME> && docker compose logs --tail=40 <SERVICE_NAME>"
   ```
2. **Verify Process State**:
   Check that container status is `Up` and not restarting (`Restarting (1) ...`).

---

### 3. Server Resource & Disk Health Diagnostic

Use when checking system health, memory exhaustion, or storage limits:

```bash
ssh valentin@100.103.31.103 "uptime && df -h / /opt/stacks && free -h && docker stats --no-stream --format 'table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.PIDs}}'"
```

---

### 4. File Sync (Local ➔ Remote)

When pushing updated configuration files or scripts to `/opt/stacks/`:

```bash
rsync -avz --progress <LOCAL_PATH> valentin@100.103.31.103:/opt/stacks/<STACK_NAME>/
```
