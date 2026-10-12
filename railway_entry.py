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
import os, time, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import send  # the sender engine (send.py in this repo)

INTERVAL = int(os.environ.get("RUN_INTERVAL_SECONDS", "7200"))

if __name__ == "__main__":
    while True:
        try:
            send.main()
        except SystemExit:
            pass
        except Exception as e:
            print(f"[entry] sender error: {e}", flush=True)
        print(f"[entry] sleeping {INTERVAL}s", flush=True)
        time.sleep(INTERVAL)
