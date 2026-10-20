"""TenderWin (AU) outreach sequences for the shared AgentMail sender.

Lead fields (campaigns/tenderwin_winners.json): email, contact_name, company, trade, state,
award_buyer, award_month, live_tenders:[{title,buyer,closes,url}], live_count.

Design (from the cold-email skill + the BidCheck premium template):
- Step 1: plain text. Recipient-specific hook (a real public contract award), one clear ask, no links.
  Plain text keeps deliverability high on warming inboxes.
- Step 2 (day 3): the premium HTML 'live tenders for your trade' card, with links. Value first, reply-gated.
- Step 3 (day 7): short break-up, plain text.
Compliance (Spam Act 2003): identifies the sender and business, relevant to the recipient's role, working opt-out
in every step. Only send to addresses that are publicly published for business use.
"""
import html as _h, re, json, time, datetime as _dt
import urllib.request

TRADE_RX = {"cleaning": r"clean|janitor|hygiene|laundry", "construction": r"construct|build|civil|refurb|maintenance|repair|electrical|plumb|roof|paint|fenc|landscap",
            "ICT": r"software|\bict\b|cyber|cloud|digital|licen[cs]e|it support|network|web|telecom", "security": r"security|guard|surveillance|cctv",
            "catering": r"cater|food|meal|kitchen", "professional services": r"consult|advis|review|audit|training|research|legal|recruit|project manage|evaluation",
            "supplies": r"suppl|equipment|vehicle|furniture|uniform|stationery|print|medical|goods|purchase"}
_CACHE = {"t": 0, "rows": []}

def _all_tenders():
    """Live AU tenders from TenderWin's own public API, cached for an hour so a sender pass makes one request."""
    if time.time() - _CACHE["t"] < 3600 and _CACHE["rows"]:
        return _CACHE["rows"]
    try:
        req = urllib.request.Request("https://tenderwin.com.au/api/tenders?limit=1000", headers={"User-Agent": "tenderwin-outreach/1.0"})
        rows = json.load(urllib.request.urlopen(req, timeout=30)).get("tenders", [])
        _CACHE.update(t=time.time(), rows=rows)
    except Exception:
        pass
    return _CACHE["rows"]

def live_for(trade, n=3):
    """(total_open, [top n soonest-closing, at least 4 days out]) for a trade bucket."""
    rx = re.compile(TRADE_RX.get(trade or "", r"$^"), re.I)
    cut = (_dt.date.today() + _dt.timedelta(days=4)).isoformat()
    rows = [r for r in _all_tenders() if (r.get("closes") or "") >= cut and rx.search(r.get("title") or "")]
    rows.sort(key=lambda r: r["closes"])
    out = []
    for r in rows[:n]:
        d = _dt.date.fromisoformat(r["closes"][:10]).strftime("%-d %b")
        out.append({"title": (r.get("title") or "")[:80].rstrip(" ,-"), "buyer": r.get("buyer", ""), "closes": d, "state": r.get("province", ""),
                    "url": f"https://tenderwin.com.au/tender/{r['ocid']}?utm_source=cold_email&utm_medium=email&utm_campaign=tw_oct26"})
    return len(rows), out

def _first(lead):
    n = _h.unescape(lead.get("contact_name") or "").split()
    return n[0].capitalize() if n else ((lead.get("company") or "").strip() + " team" if lead.get("company") else "there")

def _sign(lead):
    local = (lead.get("_from") or "").split("@")[0]
    first = re.split(r"[._\-0-9]", local)[0].lower()
    if not first or first == "tenderwin":          # role inboxes such as tenderwin-bids / tenderwin-quotes
        return "The TenderWin team\ntenderwin.com.au"
    return f"{first.capitalize()}\nTenderWin | tenderwin.com.au"
OPT = 'P.S. Not relevant? Reply "remove" and you will not hear from me again.'

def _hook(lead):
    b, m = lead.get("award_buyer"), lead.get("award_month")
    if b and m:
        return f"I saw {lead.get('company') or 'your business'} was awarded work by {b} ({m}) on the public AusTender record. Well done."
    return f"I came across {lead.get('company') or 'your business'} while looking at who is winning {lead.get('trade') or 'government'} work in {lead.get('state') or 'Australia'}."

def variant_for(lead):
    """Stable A/B arm per address: the same lead always gets the same arm."""
    import hashlib
    return "A" if int(hashlib.sha1((lead.get("email") or "").lower().encode()).hexdigest()[:8], 16) % 2 == 0 else "B"


def _award_line(lead):
    b, m = lead.get("award_buyer"), lead.get("award_month")
    co = lead.get("company") or "your business"
    if b and m:
        return f"Saw {co} won work from {b} ({m}) on AusTender. Nice."
    return f"Came across {co} while looking at who wins {lead.get('trade') or 'government'} work in Australia."


def step1(lead):
    """A = proof (three live tenders, reply-gated check). B = short question + free daily alerts. Both plain text, one ask."""
    f, trade, co = _first(lead), lead.get("trade") or "your trade", lead.get("company") or "your business"
    total, tenders = live_for(lead.get("trade"))
    if variant_for(lead) == "B" or not tenders:
        n = f"{total} {trade} tenders are open" if total else f"{trade} tenders open every week"
        body = (f"{_award_line(lead)}\n\nQuick question: who on your team watches for the next one?\n\n"
                f"Right now {n} across AusTender and the state portals. TenderWin emails the ones that fit your ABN "
                f"each morning, free.\n\nWant me to switch it on for {co}? Reply \"yes\" and I'll set it up.")
        return (f"{co} + government work", f"Hi {f},\n\n{body}\n\n{OPT}\n\n{_sign(lead)}", None)
    lines = "\n".join(f"- {x['title'][:70]} ({x['buyer'].split(' - ')[0][:35]}{', ' + x['state'] if x['state'] else ''}), closes {x['closes']}\n  {x['url']}" for x in tenders)
    body = (f"{_award_line(lead)}\n\n{total} {trade} tenders are open right now. These close soonest:\n\n{lines}\n\n"
            f"Want me to check these three against {co}{chr(39) if co.endswith('s') else chr(39) + 's'} ABN, GST and insurance? Reply \"yes\".")
    return (f"{trade} tenders closing soon", f"Hi {f},\n\n{body}\n\n{OPT}\n\n{_sign(lead)}", None)

def _row(t):
    return (f'<tr><td style="padding:14px 0;border-bottom:1px solid #EBECEE;">'
            f'<a href="{_h.escape(t.get("url","https://tenderwin.com.au/search"))}" style="font-size:15px;font-weight:700;color:#0A1F5C;text-decoration:none;">{_h.escape(t.get("title","")[:90])}</a>'
            f'<div style="font-size:12.5px;color:#5B6475;margin-top:3px;">{_h.escape(t.get("buyer",""))} &middot; closes {_h.escape(str(t.get("closes","")))}</div></td></tr>')

def step2(lead):
    f, trade = _first(lead), lead.get("trade") or "your trade"
    total, live5 = live_for(lead.get("trade"), 5)
    tenders = (lead.get("live_tenders") or live5)[:5]
    n = lead.get("live_count") or total or len(tenders)
    rows = "".join(_row(t) for t in tenders)
    subj = f"{n} open {trade} tenders matched to {lead.get('company') or 'you'}"
    text = (f"Hi {f},\n\nAs promised, open {trade} tenders right now:\n\n" +
            "\n".join(f"- {t.get('title','')} ({t.get('buyer','')}, closes {t.get('closes','')}) {t.get('url','')}" for t in tenders) +
            f"\n\nSearch is free at tenderwin.com.au. Reply with your ABN state and I will tell you which you qualify for.\n\n{OPT}\n\n{_sign(lead)}")
    page = f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="light only"></head>
<body style="margin:0;padding:0;background:#F4F5F7;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;color:#0B0F14;">
<div style="display:none;max-height:0;overflow:hidden;">{n} live {trade} tenders, matched to your ABN. Free to search.</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#F4F5F7;"><tr><td align="center" style="padding:32px 12px 40px;">
<table role="presentation" width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;">
<tr><td style="padding-bottom:20px;font-size:16px;font-weight:800;letter-spacing:-0.02em;color:#0A1F5C;">Tender<span style="color:#E0A800;">Win</span></td></tr>
<tr><td style="background:#0A1F5C;border-radius:18px 18px 0 0;padding:28px 32px;">
<div style="font-size:11px;letter-spacing:.16em;text-transform:uppercase;color:#9DB0E8;">{_h.escape((lead.get('state') or 'Australia').upper())} &middot; {_h.escape(trade.upper())}</div>
<h1 style="margin:10px 0 0;font-size:26px;line-height:1.15;letter-spacing:-0.03em;color:#fff;">{n} open {_h.escape(trade)} tenders, checked against your business.</h1></td></tr>
<tr><td style="background:#fff;padding:22px 32px 6px;">
<p style="margin:0 0 6px;font-size:15px;line-height:1.6;color:#333A44;">Hi {_h.escape(f)}, as promised. These are live on AusTender and state portals today.</p>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0">{rows}</table></td></tr>
<tr><td style="background:#fff;padding:18px 32px 30px;border-radius:0 0 18px 18px;">
<a href="https://tenderwin.com.au/search" style="display:inline-block;background:#0A1F5C;color:#fff;text-decoration:none;font-weight:700;font-size:14px;padding:13px 22px;border-radius:999px;">See all {n} tenders, free</a>
<p style="margin:16px 0 0;font-size:13px;line-height:1.5;color:#5B6475;">Reply with your state and ABN status and I will tell you which of these you qualify for.</p></td></tr>
<tr><td style="padding:18px 8px 0;font-size:12px;line-height:1.5;color:#7B8593;">Sent by {_h.escape(_sign(lead).splitlines()[0])} at TenderWin (tenderwin.com.au). Not relevant? Reply "remove" and you will not hear from us again.</td></tr>
</table></td></tr></table></body></html>"""
    return subj, text, page

def step3(lead):
    f, trade = _first(lead), lead.get("trade") or "your trade"
    return (f"last one ({lead.get('company') or 'your team'})",
f"""Hi {f},

Last note. If winning more {trade} work is on the list, TenderWin's search is free and shows what you qualify for before you spend time on a bid.

Reply "send" and I will email this week's matches, or "remove" and that is the end of it.

{_sign(lead)}""", None)

def seq_tenderwin_winners(lead, step):
    return {1: step1, 2: step2, 3: step3}[step](lead)
