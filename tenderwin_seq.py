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
import html as _h

def _first(lead):
    n = _h.unescape(lead.get("contact_name") or "").split()
    return n[0].capitalize() if n else "there"

SIGN = "Sylvester\nTenderWin | tenderwin.com.au"
OPT = 'P.S. Not relevant? Reply "remove" and you will not hear from me again.'

def _hook(lead):
    b, m = lead.get("award_buyer"), lead.get("award_month")
    if b and m:
        return f"I saw {lead.get('company') or 'your business'} was awarded work by {b} ({m}) on the public AusTender record. Well done."
    return f"I came across {lead.get('company') or 'your business'} while looking at who is winning {lead.get('trade') or 'government'} work in {lead.get('state') or 'Australia'}."

def step1(lead):
    f, trade = _first(lead), lead.get("trade") or "your trade"
    n = lead.get("live_count")
    live = f"{n} {trade} tenders are open right now across federal and state portals" if n else f"there are {trade} tenders open right now across federal and state portals"
    return (f"{trade} tenders closing soon ({lead.get('company') or 'your team'})",
f"""Hi {f},

{_hook(lead)}

Most small suppliers find out about work like that after it closes. TenderWin pulls AusTender and the state portals into one search and matches each tender to your ABN, GST status and insurance, so {live}, and you can see which you actually qualify for.

If it would help, reply "send" and I will email you this week's open {trade} tenders matched to your business. No signup.

{OPT}

{SIGN}""", None)

def _row(t):
    return (f'<tr><td style="padding:14px 0;border-bottom:1px solid #EBECEE;">'
            f'<a href="{_h.escape(t.get("url","https://tenderwin.com.au/search"))}" style="font-size:15px;font-weight:700;color:#0A1F5C;text-decoration:none;">{_h.escape(t.get("title","")[:90])}</a>'
            f'<div style="font-size:12.5px;color:#5B6475;margin-top:3px;">{_h.escape(t.get("buyer",""))} &middot; closes {_h.escape(str(t.get("closes","")))}</div></td></tr>')

def step2(lead):
    f, trade = _first(lead), lead.get("trade") or "your trade"
    tenders = (lead.get("live_tenders") or [])[:5]
    n = lead.get("live_count") or len(tenders)
    rows = "".join(_row(t) for t in tenders)
    subj = f"{n} open {trade} tenders matched to {lead.get('company') or 'you'}"
    text = (f"Hi {f},\n\nAs promised, open {trade} tenders right now:\n\n" +
            "\n".join(f"- {t.get('title','')} ({t.get('buyer','')}, closes {t.get('closes','')}) {t.get('url','')}" for t in tenders) +
            f"\n\nSearch is free at tenderwin.com.au. Reply with your ABN state and I will tell you which you qualify for.\n\n{OPT}\n\n{SIGN}")
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
<tr><td style="padding:18px 8px 0;font-size:12px;line-height:1.5;color:#7B8593;">Sent by Sylvester at TenderWin (tenderwin.com.au). Not relevant? Reply "remove" and you will not hear from us again.</td></tr>
</table></td></tr></table></body></html>"""
    return subj, text, page

def step3(lead):
    f, trade = _first(lead), lead.get("trade") or "your trade"
    return (f"last one ({lead.get('company') or 'your team'})",
f"""Hi {f},

Last note. If winning more {trade} work is on the list, TenderWin's search is free and shows what you qualify for before you spend time on a bid.

Reply "send" and I will email this week's matches, or "remove" and that is the end of it.

{SIGN}""", None)

def seq_tenderwin_winners(lead, step):
    return {1: step1, 2: step2, 3: step3}[step](lead)
