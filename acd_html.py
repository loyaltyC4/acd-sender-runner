"""Aged Care Direct: branded HTML for step 2 of every ACD sequence.

Step 1 stays plain text (best deliverability for a cold first touch). Step 2 is the 'value drop': the same copy, set in
a clean, high-end layout with the brand teal, a trust strip and one clear button. Single column, 600px, inline CSS,
table layout and system fonts so it renders in Gmail, Outlook and Apple Mail without images.
"""
import html as _h, re, urllib.parse

TEAL, SAGE, INK, MUTED, RED = "#0d424b", "#eef2e6", "#14232a", "#5b6b70", "#c0392b"
FONT = "-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif"
SERIF = "Georgia,'Times New Roman',serif"


def _paras(text):
    out, sign = [], []
    blocks = [b.strip() for b in re.split(r"\n\s*\n", text.strip()) if b.strip()]
    for b in blocks:
        if b.lower().startswith("p.s."):
            continue                      # the opt-out is repeated in the footer
        if b.startswith(("Regards", "Thanks")):
            sign = b.split("\n"); continue
        out.append(b)
    return out, sign


def render(subject, text, lead):
    paras, sign = _paras(text)
    inbox = (lead.get("_from") or "").strip() or "hello@agedcaredirect.com.au"
    co = _h.unescape(lead.get("company") or "")
    mailto = f"mailto:{inbox}?subject={urllib.parse.quote('Re: ' + subject)}&body={urllib.parse.quote('Hi, here is what we need a quote for: ')}"
    body = ""
    for i, p in enumerate(paras):
        p_html = _h.escape(p).replace("\n", "<br>")
        if i == 0:
            body += f'<p style="margin:0 0 18px;font:400 17px/1.55 {SERIF};color:{INK};">{p_html}</p>'
        else:
            body += f'<p style="margin:0 0 16px;font:400 15px/1.65 {FONT};color:{INK};">{p_html}</p>'
    sig = "<br>".join(_h.escape(s) for s in sign) if sign else "Sylvester<br>Aged Care Direct"
    trust = "".join(
        f'<td width="33%" valign="top" style="padding:0 6px;font:600 11.5px/1.4 {FONT};color:{TEAL};text-align:center;">{a}<br>'
        f'<span style="font-weight:400;color:{MUTED};">{b}</span></td>'
        for a, b in (("Same-day quotes", "The day you ask"), ("Clean claims", "Invoiced in the right name"), ("Australia-wide", "Dispatched from Melbourne")))
    return f'''<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light only"><title>{_h.escape(subject)}</title></head>
<body style="margin:0;padding:0;background:{SAGE};">
<div style="display:none;max-height:0;overflow:hidden;">Same-day quotes on mobility and daily-living equipment, dispatched from Melbourne.</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{SAGE};"><tr><td align="center" style="padding:28px 12px 36px;">
<table role="presentation" width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;">
<tr><td style="background:{TEAL};border-radius:18px 18px 0 0;padding:26px 34px;">
  <div style="font:600 11px/1 {FONT};letter-spacing:.18em;text-transform:uppercase;color:#9fc3c9;">Equipment supplier</div>
  <div style="margin-top:8px;font:700 24px/1.1 {SERIF};color:#ffffff;">Aged Care Direct</div></td></tr>
<tr><td style="background:#ffffff;padding:32px 34px 6px;">{body}
  <table role="presentation" cellpadding="0" cellspacing="0" style="margin:22px 0 8px;"><tr><td style="background:{TEAL};border-radius:999px;">
    <a href="{mailto}" style="display:inline-block;padding:14px 26px;font:700 14px/1 {FONT};color:#ffffff;text-decoration:none;">Reply for a same-day quote</a></td></tr></table>
  <p style="margin:22px 0 0;font:400 15px/1.6 {FONT};color:{INK};">{sig}</p></td></tr>
<tr><td style="background:#ffffff;padding:22px 28px 26px;border-top:1px solid #e6ebe0;"><table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>{trust}</tr></table></td></tr>
<tr><td style="background:#ffffff;border-radius:0 0 18px 18px;padding:0 34px 26px;font:400 11.5px/1.6 {FONT};color:{MUTED};">
  Sent to {_h.escape(co) if co else 'your published business address'} by Aged Care Direct, Melbourne, Australia. Not relevant? Reply "remove" and we will not email you again.</td></tr>
</table></td></tr></table></body></html>'''
