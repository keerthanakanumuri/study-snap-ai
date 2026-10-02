import smtplib
from email.mime.text import MIMEText
import streamlit as st


def send_email(to_address: str, subject: str, body: str) -> None:
    """
    Send a plain-text email via Gmail SMTP (SSL, port 465).

    Credentials are read from Streamlit secrets:
        GMAIL_ADDRESS       — the sending Gmail account
        GMAIL_APP_PASSWORD  — the 16-character App Password
                              (NOT the real account password)

    Raises an exception on failure so the caller can surface the error
    to the user.
    """
    gmail_address = st.secrets["GMAIL_ADDRESS"]
    gmail_app_password = st.secrets["GMAIL_APP_PASSWORD"]

    message = MIMEText(body, "plain", "utf-8")
    message["Subject"] = subject
    message["From"] = gmail_address
    message["To"] = to_address

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(gmail_address, gmail_app_password)
        server.send_message(message)
