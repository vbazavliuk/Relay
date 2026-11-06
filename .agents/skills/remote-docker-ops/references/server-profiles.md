# Remote Server Profiles & Stacks Reference

This reference documents the default target hosts, stack directories, and standard operational commands for remote Docker administration.

---

## 🖥 Server Profiles

### 1. Production Server (Tailscale / Remote)
- **Host / User**: `valentin@100.103.31.103`
- **Access Protocol**: SSH (`ssh valentin@100.103.31.103`)
- **Stacks Base Directory**: `/opt/stacks/`
- **Primary Stacks**:
  - `/opt/stacks/option/`: Autonomous options trading autopilot, paper trading, sentinels, market feeds.
  - `/opt/stacks/bots/`: Telegram notification and management bots.

### 2. Local LAN Server (Direct Local Network)
- **Host / User**: `valentin@192.168.1.110`
- **Access Protocol**: SSH (`ssh valentin@192.168.1.110`)
- **Use Case**: Direct local network fallback when Tailscale is disabled or for high-throughput LAN transfers.

---

## 🛡 High-Priority Safety Guardrails

> [!CAUTION]
> **Production Protection Rules**:
> 1. **NEVER run `docker compose down -v`**: Removing volumes wipes persistent trading state, SQLite DBs, and logs.
> 2. **NEVER run destructive prune commands** (`docker system prune -a --volumes`) without explicit confirmation.
> 3. **Non-destructive EOD checks only**: When running End-of-Day (EOD) audits, use strictly read-only commands (`cat`, `tail`, `grep`, `docker logs`).
> 4. **Always combine build + up + log check in a single sequence** so that if a build fails, existing containers are not left stopped.

---

## ⚡ Canonical One-Liner Commands

### 1. Atomic Rebuild & Live Logs
```bash
ssh valentin@100.103.31.103 "cd /opt/stacks/option && docker compose build --no-cache <SERVICE_NAME> && docker compose up -d <SERVICE_NAME> && docker compose ps <SERVICE_NAME> && docker compose logs --tail=50 <SERVICE_NAME>"
```

### 2. Read-Only EOD Forensic Inspection
```bash
ssh valentin@100.103.31.103 "cd /opt/stacks/option && docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.RunningFor}}' && docker compose logs --since 8h <SERVICE_NAME> | grep -E '(TRADE|FILL|ORDER|ERROR|CRITICAL|PnL)' | tail -n 100"
```

### 3. Resource & Health Snapshot
```bash
ssh valentin@100.103.31.103 "uptime && df -h /opt/stacks && docker stats --no-stream --format 'table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}'"
```
