import os
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL")

# Send the test email to yourself
TO_EMAIL = SMTP_USER

def test_smtp():
    print("--- SMTP Connection Test ---")
    if not SMTP_USER or not SMTP_PASSWORD or "your_" in SMTP_USER:
        print(" Error: Please put your actual Gmail address and App Password in the .env file first.")
        return

    msg = EmailMessage()
    msg.set_content("If you are reading this, your Gmail SMTP configuration is working perfectly for the Outage Dashboard!")
    msg["Subject"] = " Test Email from Outage Backend"
    msg["From"] = SMTP_FROM_EMAIL
    msg["To"] = TO_EMAIL

    print(f"Connecting to {SMTP_HOST}:{SMTP_PORT}...")
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            print("Logging in...")
            server.login(SMTP_USER, SMTP_PASSWORD)
            print("Sending message...")
            server.send_message(msg)
            print(f"\n SUCCESS! A test email was just sent to {TO_EMAIL}.")
            print("You can now safely run your backend server and the Dashboard will use this email!")
    except Exception as e:
        print(f"\n FAILED to send email.")
        print(f"Error details: {e}")
        print("\nPlease double check that you generated an 'App Password' correctly and that your email address is spelled right.")

if __name__ == "__main__":
    test_smtp()
