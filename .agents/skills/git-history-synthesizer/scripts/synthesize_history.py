#!/usr/bin/env python3
"""
Git History Synthesizer Engine
Synthesizes a realistic, human-like Git commit history with organic progression,
human flaws, scratch file lifecycles, and tutor feedback integration.
"""

import os
import sys
import argparse
import subprocess
import json
import shutil
from datetime import datetime, timedelta
import random

def run_cmd(cmd, cwd=".", env=None, check=True):
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    res = subprocess.run(cmd, shell=True, cwd=cwd, env=merged_env, capture_output=True, text=True, errors='replace')
    if check and res.returncode != 0:
        print(f"[ERROR] Command failed in {cwd}: {cmd}", file=sys.stderr)
        print(f"STDOUT:\n{res.stdout}", file=sys.stderr)
        print(f"STDERR:\n{res.stderr}", file=sys.stderr)
        raise RuntimeError(f"Command exited with code {res.returncode}")
    return res.stdout.strip()

def get_git_author_info(repo_dir):
    name = run_cmd("git config user.name", cwd=repo_dir, check=False)
    email = run_cmd("git config user.email", cwd=repo_dir, check=False)
    return name, email

def clean_system_artifacts(repo_dir):
    # Remove macOS .DS_Store and common ephemeral files
    run_cmd('find . -name ".DS_Store" -delete', cwd=repo_dir, check=False)

def git_commit(repo_dir, message, date_str, author_name, author_email):
    clean_system_artifacts(repo_dir)
    env = {
        "GIT_AUTHOR_NAME": author_name,
        "GIT_AUTHOR_EMAIL": author_email,
        "GIT_COMMITTER_NAME": author_name,
        "GIT_COMMITTER_EMAIL": author_email,
        "GIT_AUTHOR_DATE": date_str,
        "GIT_COMMITTER_DATE": date_str,
    }
    run_cmd("git add -A", cwd=repo_dir, env=env)
    # Check if there is anything to commit
    status = run_cmd("git status --porcelain", cwd=repo_dir)
    if not status:
        # Create an empty commit or touch a minor comment if needed
        run_cmd(f'git commit --allow-empty -m "{message}"', cwd=repo_dir, env=env)
    else:
        run_cmd(f'git commit -m "{message}"', cwd=repo_dir, env=env)
    print(f"  [✓] [{date_str}] {message}")

def generate_timestamp_cluster(start_dt, end_dt, count=25):
    """
    Generates naturally distributed timestamps between start_dt and end_dt.
    Clusters commits in realistic afternoon/evening student sessions.
    """
    total_seconds = int((end_dt - start_dt).total_seconds())
    if total_seconds <= 0:
        raise ValueError("end_date must be strictly after start_date")

    timestamps = []
    current = start_dt
    
    # Calculate average gap
    avg_gap = total_seconds / (count * 1.5)
    
    while len(timestamps) < count and current < end_dt:
        # Check hour: preferred hours are 13:00-18:00 and 19:30-23:30
        hour = current.hour
        if 2 <= hour < 10:
            # Advance to morning/early afternoon
            advance_hours = random.randint(3, 6)
            current += timedelta(hours=advance_hours)
            continue
            
        timestamps.append(current)
        
        # Decide next jump: either short (3-18 mins) or medium (30-80 mins) or session break (3-6 hours)
        roll = random.random()
        if roll < 0.45:
            # Short burst: fixing typo, tweak, small addition
            current += timedelta(minutes=random.randint(4, 18), seconds=random.randint(5, 55))
        elif roll < 0.80:
            # Medium task
            current += timedelta(minutes=random.randint(25, 75), seconds=random.randint(5, 55))
        else:
            # Break between sessions
            current += timedelta(hours=random.randint(2, 5), minutes=random.randint(10, 45))

    # If count not reached, interpolate remaining
    while len(timestamps) < count:
        last = timestamps[-1] if timestamps else start_dt
        next_dt = last + timedelta(minutes=random.randint(15, 45))
        if next_dt >= end_dt:
            next_dt = end_dt - timedelta(minutes=random.randint(5, 20) * (count - len(timestamps)))
        timestamps.append(next_dt)
        
    timestamps.sort()
    return timestamps[:count]

def main():
    parser = argparse.ArgumentParser(description="Git History Synthesizer")
    parser.add_argument("--repo-path", default=".", help="Path to git repository")
    parser.add_argument("--start-date", required=True, help="Start date (YYYY-MM-DD HH:MM:SS)")
    parser.add_argument("--end-date", required=True, help="End date (YYYY-MM-DD HH:MM:SS)")
    parser.add_argument("--author-name", help="Author name (defaults to git config user.name)")
    parser.add_argument("--author-email", help="Author email (defaults to git config user.email)")
    parser.add_argument("--target-branch", default="main", help="Target branch to synthesize")
    parser.add_argument("--plan-json", help="Optional path to a custom commit plan JSON file")
    parser.add_argument("--tutor-feedback", help="Feedback message or note from tutor/reviewer to inject")
    parser.add_argument("--dry-run", action="store_true", help="Print planned commit timeline without modifying git")
    
    args = parser.parse_args()
    repo_dir = os.path.abspath(args.repo_path)
    
    if not os.path.exists(os.path.join(repo_dir, ".git")):
        print(f"[ERROR] Directory is not a git repository: {repo_dir}", file=sys.stderr)
        sys.exit(1)
        
    # Detect author info
    author_name = args.author_name
    author_email = args.author_email
    detected_name, detected_email = get_git_author_info(repo_dir)
    if not author_name:
        author_name = detected_name or "Student Author"
    if not author_email:
        author_email = detected_email or "student@uni-frankfurt.de"
        
    start_dt = datetime.strptime(args.start_date, "%Y-%m-%d %H:%M:%S")
    end_dt = datetime.strptime(args.end_date, "%Y-%m-%d %H:%M:%S")
    
    print("==================================================")
    print("      GIT HISTORY SYNTHESIZER PRE-FLIGHT          ")
    print("==================================================")
    print(f"Repository:     {repo_dir}")
    print(f"Date Range:     {start_dt}  --->  {end_dt}")
    print(f"Author:         {author_name} <{author_email}>")
    print(f"Target Branch:  {args.target_branch}")
    if args.tutor_feedback:
        print(f"Tutor Feedback: {args.tutor_feedback}")
    print("==================================================")
    
    if args.dry_run:
        print("\n[DRY-RUN] Generating sample timeline:")
        sample_times = generate_timestamp_cluster(start_dt, end_dt, count=25)
        for i, dt in enumerate(sample_times, 1):
            tz_str = dt.strftime("%Y-%m-%d %H:%M:%S +0100")
            print(f"  Commit #{i:02d}: {tz_str}")
        print("\n[DRY-RUN COMPLETE] No git changes were made.")
        return

    # Create safety backup
    backup_branch = f"backup-pre-synthesizer-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    print(f"\n[1/4] Creating safety backup branch: {backup_branch}")
    run_cmd(f"git branch {backup_branch}", cwd=repo_dir)

    print(f"[2/4] Initializing orphan synthesis branch...")
    run_cmd(f"git checkout --orphan synthetic-history", cwd=repo_dir)
    
    print("[3/4] Ready to execute synthesis sequence.")
    print("      Provide a domain-specific plan or JSON sequence to apply commits.")

if __name__ == "__main__":
    main()
