"""
Diagnostic script to test the SMTP email settings for The Alignment Puzzle.

Usage:
    python test_email.py

It reads SMTP_* settings from your .env file, tries to connect and log in,
and sends one test email so you can confirm everything works BEFORE touching
the live Render server.

Nothing here changes the website. It is safe to run and safe to delete.
"""

import os
import smtplib
import ssl
from email.mime.text import MIMEText
from pathlib import Path

from dotenv import load_dotenv

# Load the same .env the website uses
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.hostnet.nl")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "info@alignmentpuzzle.com")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
FROM_EMAIL = "info@alignmentpuzzle.com"

# Where to send the test message. Change this if you like.
TEST_RECIPIENT = os.getenv("TEST_RECIPIENT", "info@alignmentpuzzle.com")


def main():
    print("=" * 60)
    print(" Alignment Puzzle - SMTP test")
    print("=" * 60)
    print(f"  SMTP_HOST     : {SMTP_HOST}")
    print(f"  SMTP_PORT     : {SMTP_PORT}")
    print(f"  SMTP_USER     : {SMTP_USER}")
    print(f"  SMTP_PASSWORD : {'(set, ' + str(len(SMTP_PASSWORD)) + ' chars)' if SMTP_PASSWORD else '*** NOT SET ***'}")
    print(f"  Sending test  : {FROM_EMAIL} -> {TEST_RECIPIENT}")
    print("-" * 60)

    if not SMTP_PASSWORD:
        print("STOP: SMTP_PASSWORD is empty. Add it to your .env file first:")
        print("      SMTP_PASSWORD=your_mailbox_password")
        return

    msg = MIMEText(
        "This is a test email from test_email.py.\n\n"
        "If you are reading this, the SMTP settings work correctly.",
        "plain",
        "utf-8",
    )
    msg["From"] = f"The Alignment Puzzle <{FROM_EMAIL}>"
    msg["To"] = TEST_RECIPIENT
    msg["Subject"] = "Alignment Puzzle SMTP test"

    try:
        print(f"Connecting to {SMTP_HOST}:{SMTP_PORT} ...")
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20) as server:
            server.set_debuglevel(1)  # print the raw SMTP conversation
            print("Starting TLS ...")
            # Match the website exactly: plain STARTTLS, same as backend/email_service.py.
            server.starttls()
            print("Logging in ...")
            server.login(SMTP_USER, SMTP_PASSWORD)
            print("Sending message ...")
            server.send_message(msg)
        print("-" * 60)
        print(f"SUCCESS: test email sent to {TEST_RECIPIENT}.")
        print("Check that inbox (and the spam folder).")
    except smtplib.SMTPAuthenticationError as e:
        print("-" * 60)
        print("LOGIN FAILED: the username or password was rejected.")
        print(f"  Server said: {e}")
        print("  -> Double-check the mailbox password in Hostnet webmail.")
    except Exception as e:
        print("-" * 60)
        print(f"FAILED: {type(e).__name__}: {e}")
        print("  -> If this is a timeout/connection error, the host or port")
        print("     may be wrong. Hostnet also supports SSL on port 465.")


if __name__ == "__main__":
    main()
