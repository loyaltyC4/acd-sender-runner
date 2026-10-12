#!/usr/bin/env python3
"""Railway entrypoint for the ACD sender service.

Persistent service (no cron): wakes every RUN_INTERVAL_SECONDS (default 2h),
runs one sender pass, sleeps. State on the mounted volume at /data.

Env vars (Railway service variables):
  AGENTMAIL_ORG1..10_KEY   — the 10 AgentMail org keys
  CAMPAIGNS_JSON_URL       — optional signed URL to refresh campaigns
  OWNER_EMAIL              — reply-forward target
  INBOX_DAILY_CAP          — per-inbox daily cap (3 during warmup)
  MAX_SENDS_PER_RUN        — per-run cap (45)
  RUN_INTERVAL_SECONDS     — 7200
"""
import json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import send  # the sender engine (send.py in this repo)

INTERVAL = int(os.environ.get("RUN_INTERVAL_SECONDS", "7200"))
STATE_DIR = os.environ.get("STATE_DIR", "/data")

def _fetch(url, token):
    import urllib.request
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.raw+json",
        "X-GitHub-Api-Version": "2022-11-28"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read().decode()

def seed_state():
    os.makedirs(os.path.join(STATE_DIR, "campaigns"), exist_ok=True)
    repo = os.environ.get("SEED_REPO")  # owner/repo of the private state repo
    token = os.environ.get("SEED_GITHUB_TOKEN")
    if not (repo and token):
        print("[entry] no SEED_REPO/SEED_GITHUB_TOKEN — skipping seed", flush=True)
        return
    base = f"https://api.github.com/repos/{repo}/contents"
    # campaigns
    for fname in ["ndis_coordinators.json", "hcp_providers.json", "plan_managers.json",
                  "support_agencies.json", "disability_providers.json"]:
        path = os.path.join(STATE_DIR, "campaigns", fname)
        if os.path.exists(path) and os.path.getsize(path) > 100:
            continue
        try:
            content = _fetch(f"{base}/campaigns/{fname}", token)
            with open(path, "w") as fh:
                fh.write(content)
            print(f"[entry] seeded campaigns/{fname} ({len(content)} bytes)", flush=True)
        except Exception as e:
            print(f"[entry] campaigns/{fname} seed failed: {e}", flush=True)
    # state files
    for fname in ["sent_emails.json", "inbox_state.json", "engaged.json",
                  "org_blocks.json", "sent_log.jsonl", "forwarded_ids.json"]:
        path = os.path.join(STATE_DIR, fname)
        if os.path.exists(path) and os.path.getsize(path) > 2:
            continue  # never overwrite live state
        try:
            content = _fetch(f"{base}/{fname}", token)
            with open(path, "w") as fh:
                fh.write(content)
            print(f"[entry] seeded {fname} ({len(content)} bytes)", flush=True)
        except Exception as e:
            print(f"[entry] {fname} seed failed (may not exist yet): {e}", flush=True)

if __name__ == "__main__":
    seed_state()
    while True:
        try:
            send.main()
        except SystemExit:
            pass
        except Exception as e:
            print(f"[entry] sender error: {e}", flush=True)
        print(f"[entry] sleeping {INTERVAL}s", flush=True)
        time.sleep(INTERVAL)
