# Agent Execution Rules & Hosting Environment

> **CRITICAL DIRECTIVE**:
> **DO NOT RUN LOCALLY ON MACOS. THIS STACK IS HOSTED ON REMOTE LINUX:**
> `valentin@192.168.1.110` in `/opt/stacks/relay/`

## Deployment & Execution Rules

1. **Remote-Only Docker Execution**:
   - Docker containers and services must NEVER be built, spun up (`docker compose up`), or restarted on the local macOS environment.
   - All stack lifecycles must be operated directly on the remote Linux host (`valentin@192.168.1.110`):
     ```bash
     ssh valentin@192.168.1.110 "cd /opt/stacks/relay && docker compose <command>"
     ```

2. **File Synchronization**:
   - Code changes, configurations, or updates developed locally must be synchronized to the remote stack destination path (`/opt/stacks/relay/`) using `rsync` or `scp`.
   - Never commit sensitive secrets (`.env`) or local runtime databases/cache files to Git.

3. **Remote Commands Quick Reference**:
   - Check status:
     ```bash
     ssh valentin@192.168.1.110 "cd /opt/stacks/relay && docker compose ps"
     ```
   - Check real-time logs:
     ```bash
     ssh valentin@192.168.1.110 "cd /opt/stacks/relay && docker compose logs -f --tail=100"
     ```
   - Restart daemon:
     ```bash
     ssh valentin@192.168.1.110 "cd /opt/stacks/relay && docker compose restart"
     ```
   - Rebuild and redeploy remote stack:
     ```bash
     ssh valentin@192.168.1.110 "cd /opt/stacks/relay && docker compose build && docker compose up -d"
     ```
