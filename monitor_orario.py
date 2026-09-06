import html
import os
import smtplib
import difflib
import requests
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from bs4 import BeautifulSoup

URL = "https://corsidilaurea.uniroma1.it/it/course/33501/attendance/timetable"
CONTENT_FILE = "last_content.txt"
SENDER_NAME = "\U0001F5D3\uFE0F"  # 🗓️


def get_page_text():
    resp = requests.get(URL, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    for tag in soup(["script", "style"]):
        tag.decompose()

    text = soup.get_text(separator="\n")
    lines = [line.strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    return "\n".join(lines)


def build_diff_lines(old_text, new_text):
    old_lines = old_text.splitlines()
    new_lines = new_text.splitlines()
    diff = difflib.unified_diff(
        old_lines, new_lines, fromfile="prima", tofile="ora", lineterm=""
    )
    changes = [
        line for line in diff
        if (line.startswith("+") or line.startswith("-"))
        and not line.startswith("+++")
        and not line.startswith("---")
    ]
    return changes


def render_diff_html(changes):
    if not changes:
        return '<p style="color:#6b7280;font-style:italic;">Contenuto cambiato, ma nessuna riga di testo distinguibile.</p>'

    rows = []
    for line in changes:
        sign = line[0]
        text = html.escape(line[1:].strip())
        if sign == "+":
            rows.append(
                f'<div style="padding:6px 10px;background:#ecfdf5;border-left:3px solid #10b981;'
                f'color:#065f46;font-family:ui-monospace,Menlo,Consolas,monospace;font-size:13px;'
                f'border-radius:4px;margin-bottom:4px;">+ {text}</div>'
            )
        else:
            rows.append(
                f'<div style="padding:6px 10px;background:#fef2f2;border-left:3px solid #ef4444;'
                f'color:#991b1b;font-family:ui-monospace,Menlo,Consolas,monospace;font-size:13px;'
                f'border-radius:4px;margin-bottom:4px;text-decoration:line-through;text-decoration-color:#f3a8a8;">'
                f'- {text}</div>'
            )
    return "".join(rows)


def render_diff_text(changes):
    if not changes:
        return "(nessuna riga di testo distinguibile, ma il contenuto e' cambiato)"
    return "\n".join(changes)


def send_email(subject, diff_changes):
    gmail_user = os.environ["GMAIL_ADDRESS"]
    gmail_pass = os.environ["GMAIL_APP_PASSWORD"]
    to_email = os.environ.get("TO_EMAIL", gmail_user)

    diff_html = render_diff_html(diff_changes)
    diff_text = render_diff_text(diff_changes)

    text_body = (
        f"La pagina e' cambiata:\n{URL}\n\n"
        "Cosa e' cambiato (righe rimosse con -, aggiunte con +):\n\n"
        f"{diff_text}\n"
    )

    html_body = f"""\
<html>
  <body style="margin:0;padding:0;background:#f4f4f5;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="padding:32px 16px;">
      <tr>
        <td align="center">
          <table role="presentation" width="480" cellpadding="0" cellspacing="0"
                 style="background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,0.08);">
            <tr>
              <td style="padding:24px 28px 8px 28px;">
                <span style="font-size:22px;">\U0001F5D3\uFE0F</span>
                <span style="font-size:17px;font-weight:600;color:#111827;margin-left:8px;">
                  Orario aggiornato
                </span>
              </td>
            </tr>
            <tr>
              <td style="padding:0 28px 4px 28px;">
                <p style="font-size:14px;color:#6b7280;margin:0 0 16px 0;">
                  Ingegneria Informatica e Automatica &middot;
                  <a href="{URL}" style="color:#2563eb;text-decoration:none;">apri la pagina</a>
                </p>
              </td>
            </tr>
            <tr>
              <td style="padding:0 28px 24px 28px;">
                {diff_html}
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>
"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = formataddr((SENDER_NAME, gmail_user))
    msg["To"] = to_email
    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(gmail_user, gmail_pass)
        server.send_message(msg)


def main():
    current_text = get_page_text()

    old_text = None
    if os.path.exists(CONTENT_FILE):
        with open(CONTENT_FILE, encoding="utf-8") as f:
            old_text = f.read()

    if old_text is None:
        with open(CONTENT_FILE, "w", encoding="utf-8") as f:
            f.write(current_text)
        print("Prima esecuzione: contenuto di riferimento salvato, nessuna email inviata.")
        return

    if current_text != old_text:
        changes = build_diff_lines(old_text, current_text)
        send_email(
            "Aggiornamento pagina orario - Ingegneria Informatica e Automatica",
            changes,
        )
        with open(CONTENT_FILE, "w", encoding="utf-8") as f:
            f.write(current_text)
        print("Cambiamento rilevato: email con diff inviata.")
    else:
        print("Nessun cambiamento rilevato.")


if __name__ == "__main__":
    main()
