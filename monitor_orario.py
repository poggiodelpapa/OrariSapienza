import requests
import os
import re
import difflib
import smtplib
from email.mime.text import MIMEText
from bs4 import BeautifulSoup

URL = "https://corsidilaurea.uniroma1.it/it/course/33501/attendance/timetable"
CONTENT_FILE = "last_content.txt"


def get_page_text():
    resp = requests.get(URL, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    # Rimuove script/stili, non interessano al confronto testuale
    for tag in soup(["script", "style"]):
        tag.decompose()

    text = soup.get_text(separator="\n")
    # Comprime righe vuote multiple e spazi superflui, per un diff leggibile
    lines = [line.strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    return "\n".join(lines)


def send_email(subject, body):
    gmail_user = os.environ["GMAIL_ADDRESS"]
    gmail_pass = os.environ["GMAIL_APP_PASSWORD"]
    to_email = os.environ.get("TO_EMAIL", gmail_user)

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = gmail_user
    msg["To"] = to_email

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(gmail_user, gmail_pass)
        server.send_message(msg)


def build_diff(old_text, new_text):
    old_lines = old_text.splitlines()
    new_lines = new_text.splitlines()
    diff = difflib.unified_diff(
        old_lines, new_lines, fromfile="prima", tofile="ora", lineterm=""
    )
    # Tiene solo le righe di aggiunta/rimozione, non l'intestazione del diff
    changes = [
        line for line in diff
        if (line.startswith("+") or line.startswith("-"))
        and not line.startswith("+++")
        and not line.startswith("---")
    ]
    return "\n".join(changes) if changes else "(nessuna riga di testo distinguibile, ma il contenuto e' cambiato)"


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
        diff_text = build_diff(old_text, current_text)
        body = (
            f"La pagina e' cambiata:\n{URL}\n\n"
            "Cosa e' cambiato (righe rimosse con -, aggiunte con +):\n\n"
            f"{diff_text}\n"
        )
        send_email(
            "Aggiornamento pagina orario - Ingegneria Informatica e Automatica",
            body,
        )
        with open(CONTENT_FILE, "w", encoding="utf-8") as f:
            f.write(current_text)
        print("Cambiamento rilevato: email con diff inviata.")
    else:
        print("Nessun cambiamento rilevato.")


if __name__ == "__main__":
    main()
