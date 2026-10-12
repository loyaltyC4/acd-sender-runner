# acd-sender-runner

Persistent outreach sender service (code only).

- Deploys as a long-running service: one sender pass every 2 hours, state on a mounted volume at /data
- 10-org AgentMail pool rotation, per-inbox daily caps, reply forwarding, 429 auto-parking
- Campaigns + state live on the deployment volume — never in this repo
- Env: AGENTMAIL_ORG1..10_KEY, OWNER_EMAIL, INBOX_DAILY_CAP, MAX_SENDS_PER_RUN, RUN_INTERVAL_SECONDS
