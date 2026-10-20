#!/usr/bin/env python3
"""Aged Care Direct outreach sender v1 — Railway/Actions cron entrypoint.

Pool: 10 AgentMail orgs (30 inboxes). Campaigns: per-ICP lead files in
CAMPAIGNS_DIR with 3-email reply-gated sequences (day 0 / day 3 / day 7).
Warmup: INBOX_DAILY_CAP per inbox per day (start 3, raise to 5 in week 2).
Ramp-aware: orgs created Oct 8 (lifted) and Oct 11 (week caps until Oct 18);
429s park an org with lift-time parsing.

Env:
  AGENTMAIL_ORG1_KEY .. AGENTMAIL_ORG10_KEY
  OWNER_EMAIL (reply forward target), STATE_DIR=/data, CAMPAIGNS_DIR
  INBOX_DAILY_CAP (default 3), MAX_SENDS_PER_RUN (default 40), DRY_RUN=1
"""
import html, json, os, random, re, sys, time, urllib.request, urllib.error
from datetime import datetime, timezone, date

def clean(s):
    return html.unescape(s or "").strip() if s else s

API = "https://api.agentmail.to/v0"
STATE_DIR = os.environ.get("STATE_DIR", os.path.dirname(os.path.abspath(__file__)))
CAMPAIGNS_DIR = os.environ.get("CAMPAIGNS_DIR", os.path.join(STATE_DIR, "campaigns"))
os.makedirs(STATE_DIR, exist_ok=True)
DRY_RUN = os.environ.get("DRY_RUN", "0") == "1"
OWNER_EMAIL = os.environ.get("OWNER_EMAIL", "slyvesterchiko1@gmail.com")
INBOX_DAILY_CAP = int(os.environ.get("INBOX_DAILY_CAP", "3"))
MAX_SENDS = int(os.environ.get("MAX_SENDS_PER_RUN", "40"))
ORG_ENVS = [f"AGENTMAIL_ORG{i}_KEY" for i in range(1, 11)] + [f"AGENTMAIL_TW{i}_KEY" for i in range(1, 5)]
TW_MAX_STEP = int(os.environ.get("TW_MAX_STEP", "1"))
# Owner-approved 2026-10-20: TenderWin inboxes (warmed since Oct 7) send up to 8/day; ACD stays on INBOX_DAILY_CAP (3).
TW_INBOX_DAILY_CAP = int(os.environ.get("TW_INBOX_DAILY_CAP", "8"))

def cap_for(org_env):
    return TW_INBOX_DAILY_CAP if org_env.startswith("AGENTMAIL_TW") else INBOX_DAILY_CAP  # TenderWin: step 1 only until the owner raises it

def pool_ok(campaign, org_env):
    """TenderWin mail goes out only from the TenderWin orgs; every other campaign never uses them."""
    is_tw_org = org_env.startswith("AGENTMAIL_TW")
    return is_tw_org == campaign.startswith("tenderwin")

def load_json(path, default):
    try: return json.load(open(path))
    except Exception: return default

def save_json(path, data):
    json.dump(data, open(path, "w"), indent=1)

def now_iso(): return datetime.now(timezone.utc).isoformat()

def api(key, path, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        f"{API}{path}", data=data, method="POST" if data else "GET",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        return e.code, {"error": e.read().decode()[:400]}
    except Exception as e:
        return 0, {"error": str(e)[:200]}

def parse_lift_time(err_text):
    m = re.search(r"lifts at (\d{4}-\d{2}-\d{2}T[\d:.]+Z)", err_text)
    return m.group(1) if m else None

# ---- per-ICP sequences (armageddon copy, Jev-validated pattern:
# recipient-specific hook, capacity framing, reply-gated CTA, no links in email 1) ----

def _first(lead):
    n = html.unescape(lead.get("contact_name") or "")
    return (n.split()[0].capitalize() if n.split() else "there")


def clean_lead(lead):
    return {k: (html.unescape(v) if isinstance(v, str) else v) for k, v in (lead or {}).items()}

def seq_ndis_coordinators(lead, step):
    f, biz = _first(lead), (clean_lead(lead).get("company") or "your team")
    if step == 1:
        return (f"equipment quotes for {biz} participants",
f"""Hi {f},

You coordinate support for a mixed caseload, and equipment requests land on your desk mid-week when participants need them sorted fast.

We dispatch mobility and daily-living equipment Australia-wide from Melbourne: rollators, shower chairs, commodes, hoists, beds. Quotes go out the same day you send the request, invoices come addressed to the participant or plan manager so the claim clears first time, and there is no account to set up.

If it would help to have a supplier on file who quotes same-day, reply with any current equipment need, even one item, and you will have pricing before you log off today.

P.S. If this is not useful, reply "remove" and you will not hear from me again.

Regards,
Sylvester
Aged Care Direct""")
    if step == 2:
        return (f"equipment invoices that clear first time ({biz})",
f"""Hi {f},

A follow-up with something useful: the most common equipment-claim hiccup we see from coordinators is the invoice name. Plan managers bounce it, the coordinator re-raises it, the participant waits another week.

We invoice in exactly the name the claim needs, participant or plan manager, first time. Same-day quotes, Australia-wide delivery from Melbourne, no account setup.

Reply with any current equipment need and pricing is back today. If you would rather just have our price list on file, reply "price list" and I will send it across.

P.S. If this is not useful, reply "remove" and you will not hear from me again.

Regards,
Sylvester
Aged Care Direct""")
    return (f"last one from me ({biz})",
f"""Hi {f},

Last note from me. If an equipment request ever lands on your desk with a participant waiting, we quote same day and deliver Australia-wide from Melbourne, invoices in the participant or plan-manager name.

Reply with a need and pricing comes back today. If now is not the time, reply "remove" and you will not hear from us again.

Regards,
Sylvester
Aged Care Direct""")

def seq_hcp_providers(lead, step):
    f, biz = _first(lead), (clean_lead(lead).get("company") or "your team")
    if step == 1:
        return (f"same-day equipment quotes for {biz} clients",
f"""Hi {f},

Your care managers arrange home equipment for clients on packages, and the wait between request and quote is where jobs stall.

We send quotes the same day for bathroom safety, commodes, walking aids, and bedroom furniture, deliver Australia-wide from Melbourne, and invoice in the client or case-manager name so the package claim is clean. No account setup, no minimum order.

If you want a supplier who turns quotes around the same day, reply with any current client equipment need and you will have pricing today.

P.S. If this is not useful, reply "remove" and you will not hear from me again.

Regards,
Sylvester
Aged Care Direct""")
    if step == 2:
        return (f"backup supplier for {biz} client jobs",
f"""Hi {f},

One useful thing: most providers we talk to keep one backup equipment supplier on file, for the day the main one is slow or out of stock. That is the slot we would like with {biz}.

Same-day quotes, Australia-wide delivery from Melbourne, invoices in the client or case-manager name for clean package claims, no minimums.

Reply with any current client need, or reply "price list" and I will send our current pricing across for the items your managers order most.

P.S. If this is not useful, reply "remove" and you will not hear from me again.

Regards,
Sylvester
Aged Care Direct""")
    return (f"last one for now ({biz})",
f"""Hi {f},

Last note. Whenever a client job needs bathroom, mobility, or bedroom equipment and the quote is dragging, we turn it around the same day, delivered Australia-wide from Melbourne.

Reply with a need for pricing today, or "remove" and that is the last you will hear from us.

Regards,
Sylvester
Aged Care Direct""")

def seq_plan_managers(lead, step):
    f, biz = _first(lead), (clean_lead(lead).get("company") or "your team")
    if step == 1:
        return (f"same-day quotes for {biz} participants",
f"""Hi {f},

Plan managers wear the cost of slow suppliers: a claim stalls when the invoice does not match the participant or plan-manager name, and the coordinator comes back to you to fix it.

We quote equipment the same day, invoice correctly for plan-managed claims, and deliver Australia-wide from Melbourne: mobility, bathroom safety, commodes, hoists, beds. No account needed.

If faster, cleaner equipment claims would help your participants, reply with any current need and you will have the quote today.

P.S. If this is not useful, reply "remove" and you will not hear from me again.

Regards,
Sylvester
Aged Care Direct""")
    if step == 2:
        return (f"fewer bounced equipment claims for {biz}",
f"""Hi {f},

The concrete version: when a coordinator sources equipment badly, the invoice arrives in the wrong name, your team queries it, and the participant waits. Multiply by every equipment request and it is real admin time.

Our invoices come out in the participant or plan-manager name, first time, so claims clear without the email trail. Same-day quotes, Australia-wide delivery from Melbourne.

Reply "price list" for the current pricing, or with any participant need and the quote is back today.

P.S. If this is not useful, reply "remove" and you will not hear from me again.

Regards,
Sylvester
Aged Care Direct""")
    return (f"closing the loop ({biz})",
f"""Hi {f},

Final note. If it would help to point coordinators at a supplier whose invoices clear first time, we are that: same-day quotes, correct invoice names, Australia-wide delivery from Melbourne.

Reply with a need, or "remove" and we go quiet.

Regards,
Sylvester
Aged Care Direct""")

def seq_support_agencies(lead, step):
    f, biz = _first(lead), (clean_lead(lead).get("company") or "your team")
    if step == 1:
        return (f"equipment quotes for {biz} client homes",
f"""Hi {f},

Support workers see the moment a client home needs a shower chair or a rail, but agencies then wait on a supplier quote before anyone can act.

We quote same-day on daily-living and mobility equipment, deliver Australia-wide from Melbourne, and invoice in the participant name so claims are clean. No account setup, no minimum.

Reply with any current client need, one item or ten, and the quote is back today.

P.S. If this is not useful, reply "remove" and you will not hear from me again.

Regards,
Sylvester
Aged Care Direct""")
    if step == 2:
        return (f"a shower chair by Friday, not next month ({biz})",
f"""Hi {f},

The practical version: when a client home suddenly needs a commode, rail, or shower chair this week, a same-day quote is the difference between sorted Friday and sorted next month.

We quote the day you ask, deliver Australia-wide from Melbourne, invoice in the participant name. No account, no minimums.

Reply "price list" and I will send current pricing across, or send any live need and the quote is back today.

P.S. If this is not useful, reply "remove" and you will not hear from me again.

Regards,
Sylvester
Aged Care Direct""")
    return (f"last note ({biz})",
f"""Hi {f},

Last one. Same-day quotes on any daily-living or mobility equipment, Australia-wide from Melbourne, invoices that clear.

Reply with a need, or "remove" and that is the end of it.

Regards,
Sylvester
Aged Care Direct""")

def seq_disability_providers(lead, step):
    f, biz = _first(lead), (clean_lead(lead).get("company") or "your team")
    if step == 1:
        return (f"same-day equipment quotes for {biz} participants",
f"""Hi {f},

Your teams arrange equipment for participants across housing and community programs, and suppliers who take days to quote slow the whole schedule.

We quote the same day on mobility, bathroom safety, commodes, hoists, and bedroom furniture, dispatch Australia-wide from Melbourne, and invoice in the participant or plan-manager name. No account, no minimums.

Reply with any current equipment need and you will have pricing before end of day.

P.S. If this is not useful, reply "remove" and you will not hear from me again.

Regards,
Sylvester
Aged Care Direct""")
    if step == 2:
        return (f"for the next SIL or respite fit-out ({biz})",
f"""Hi {f},

Where we get used most: SIL and respite fit-outs and participant home setups, beds, hoists, bathroom safety, bedroom furniture, where the schedule waits on supplier quotes.

We quote same-day, deliver Australia-wide from Melbourne, invoice in the participant or plan-manager name. No account, no minimums.

Reply "price list" for current pricing, or with any live need and the quote is back today.

P.S. If this is not useful, reply "remove" and you will not hear from me again.

Regards,
Sylvester
Aged Care Direct""")
    return (f"final note ({biz})",
f"""Hi {f},

Final one. Whenever equipment is the thing holding up a participant setup, we quote the same day and deliver Australia-wide from Melbourne.

Reply with a need, or "remove" and we stop here.

Regards,
Sylvester
Aged Care Direct""")

from tenderwin_seq import seq_tenderwin_winners

SEQUENCES = {
    "tenderwin_winners": seq_tenderwin_winners,
    "ndis_coordinators": seq_ndis_coordinators,
    "hcp_providers": seq_hcp_providers,
    "plan_managers": seq_plan_managers,
    "support_agencies": seq_support_agencies,
    "disability_providers": seq_disability_providers,
}
STEP_DELAYS = {1: 0, 2: 3, 3: 7}  # days after step 1

def main():
    print(f"[{now_iso()}] ACD sender v1 start (cap {INBOX_DAILY_CAP}/inbox/day, TenderWin {TW_INBOX_DAILY_CAP}, max {MAX_SENDS}/run)")
    # discover inboxes per org
    inboxes_by_org, org_ok = {}, []
    for org_env in ORG_ENVS:
        key = os.environ.get(org_env)
        if not key: continue
        code, data = api(key, "/inboxes")
        if code == 200 and data.get("inboxes"):
            inboxes_by_org[org_env] = [i["email"] for i in data["inboxes"] if i.get("email")]
            org_ok.append(org_env)
    pool_size = sum(len(v) for v in inboxes_by_org.values())
    print(f"pool: {pool_size} inboxes across {len(org_ok)} orgs")
    if not pool_size:
        print("no inboxes available, exiting"); return

    # reply scan + forward + engagement detection
    sent_map = load_json(os.path.join(STATE_DIR, "sent_emails.json"), {})
    engaged = load_json(os.path.join(STATE_DIR, "engaged.json"), {})
    fwd_state = load_json(os.path.join(STATE_DIR, "forwarded_ids.json"), {})
    leads_by_email = {}
    for cname in SEQUENCES:
        for l in load_json(os.path.join(CAMPAIGNS_DIR, f"{cname}.json"), []):
            e = (l.get("email") or "").lower()
            if e: leads_by_email[e] = l
    for org_env, inboxes in inboxes_by_org.items():
        key = os.environ.get(org_env)
        for inbox in inboxes:
            code, data = api(key, f"/inboxes/{inbox}/messages")
            if code != 200: continue
            for msg in (data.get("messages") or []):
                mid = msg.get("id") or msg.get("message_id")
                if not mid or fwd_state.get(mid): continue
                sender = msg.get("from") or {}
                sender = sender.get("email", "") if isinstance(sender, dict) else str(sender)
                if "agentmail" in sender or "agedcaredirect" in sender:
                    fwd_state[mid] = 1; continue
                fwd_state[mid] = 1
                fc, _ = api(key, f"/inboxes/{inbox}/messages/{mid}/forward", {"to": [OWNER_EMAIL]})
                if fc == 200:
                    print(f"FWD {inbox} {mid} -> {OWNER_EMAIL}")
                    if sender.lower() in leads_by_email:
                        engaged[sender.lower()] = now_iso()
                        print(f"ENGAGED {sender} (sequence stops)")
    save_json(os.path.join(STATE_DIR, "forwarded_ids.json"), fwd_state)
    save_json(os.path.join(STATE_DIR, "engaged.json"), engaged)

    # state
    st = load_json(os.path.join(STATE_DIR, "inbox_state.json"), {})
    blocks = load_json(os.path.join(STATE_DIR, "org_blocks.json"), {})
    today = date.today().isoformat()
    today_counts = st.get(today) or {}
    now = datetime.now(timezone.utc)
    for org, until in list(blocks.items()):
        try:
            t = until.replace("Z", "+00:00")
            t = re.sub(r"\.(\d{1,6})\+00:00", lambda m: "." + m.group(1).ljust(6, "0") + "+00:00", t)
            if datetime.fromisoformat(t) <= now:
                print(f"org block lifted: {org}"); del blocks[org]
        except Exception:
            pass  # keep block on parse failure — safer than silently unblocking
    save_json(os.path.join(STATE_DIR, "org_blocks.json"), blocks)

    # build the send plan: due sequence steps for leads not engaged
    plan = []
    for cname, seqfn in SEQUENCES.items():
        leads = load_json(os.path.join(CAMPAIGNS_DIR, f"{cname}.json"), [])
        for l in leads:
            e = (l.get("email") or "").lower()
            if not e or e in engaged: continue
            rec = sent_map.get(e)
            if not rec:
                plan.append((cname, l, 1))
            else:
                step = rec.get("step", 1)
                if step >= 3: continue
                if cname.startswith("tenderwin") and step + 1 > TW_MAX_STEP: continue
                days = (now - datetime.fromisoformat(rec["sent_at"])).days
                if days >= STEP_DELAYS[step + 1]:
                    plan.append((cname, l, step + 1))
    random.shuffle(plan)
    plan.sort(key=lambda x: 0 if x[0].startswith("tenderwin") else 1)  # TenderWin has its own inboxes and few leads: never let the ACD backlog crowd it out
    print(f"due sends: {len(plan)} (engaged/replied: {len(engaged)}, already sent: {len(sent_map)})")

    avail = [(oe, ib) for oe, ibs in inboxes_by_org.items() if oe not in blocks
             for ib in ibs if today_counts.get(ib, 0) < cap_for(oe)]
    if not avail:
        print("all inboxes at daily cap or orgs blocked, exiting"); return
    plan = plan[:MAX_SENDS]
    print(f"planned {len(plan)} sends this run")

    log = open(os.path.join(STATE_DIR, "sent_log.jsonl"), "a")
    n, parked, ai = 0, set(), -1
    for i, (cname, lead, step) in enumerate(plan):
        # recompute available (org, inbox) pairs fresh each iteration
        avail = [(oe, ib) for oe, ibs in inboxes_by_org.items() if oe not in blocks and oe not in parked and pool_ok(cname, oe)
                 for ib in ibs if today_counts.get(ib, 0) < cap_for(oe)]
        if not avail: continue
        ai = (ai + 1) % len(avail)
        org_env, inbox = avail[ai]
        key = os.environ.get(org_env)
        res = SEQUENCES[cname]({**lead, "_from": inbox}, step)
        subj, body = res[0], res[1]
        body_html = res[2] if len(res) > 2 else None
        to = (lead.get("email") or "").strip().lower()
        if DRY_RUN:
            print(f"DRY {inbox} -> {to} ({cname} step{step}) :: {subj}"); continue
        code, resp = api(key, f"/inboxes/{inbox}/messages/send",
                         {"to": [to], "subject": subj, "text": body, **({"html": body_html} if body_html else {})})
        if code == 200:
            sent_map[to] = {"campaign": cname, "step": step, "inbox": inbox, "sent_at": now_iso()}
            today_counts[inbox] = today_counts.get(inbox, 0) + 1
            log.write(json.dumps({"ts": now_iso(), "inbox": inbox, "to": to, "campaign": cname,
                                  "step": step, "company": lead.get("company"), "subject": subj}) + "\n")
            log.flush(); n += 1
            arm = ""
            if cname.startswith("tenderwin"):
                from tenderwin_seq import variant_for
                arm = f" v{variant_for(lead)}"
                sent_map[to]["variant"] = arm.strip()
            print(f"OK {inbox} -> {to} ({cname} step{step}{arm})")
        else:
            print(f"ERR {code} {inbox} -> {to} :: {resp}")
            if code == 429:
                err = resp.get("error", "") if isinstance(resp, dict) else str(resp)
                lift = parse_lift_time(err)
                blocks[org_env] = lift or (now.replace(microsecond=0).isoformat() + "Z")
                save_json(os.path.join(STATE_DIR, "org_blocks.json"), blocks)
                parked.add(org_env)
                print(f"parking org {org_env} until {blocks[org_env]}")
        save_json(os.path.join(STATE_DIR, "sent_emails.json"), sent_map)
        st[today] = today_counts
        save_json(os.path.join(STATE_DIR, "inbox_state.json"), st)
        if n < len(plan) - 1:
            time.sleep(random.uniform(4, 9))
    log.close()
    print(f"done: {n} sent this run, {len(sent_map)} leads touched total, parked: {sorted(parked)}")

if __name__ == "__main__":
    main()
