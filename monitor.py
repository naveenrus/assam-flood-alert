import os
import smtplib
from email.mime.text import MIMEText

EMAIL_USER = os.environ["EMAIL_USER"]
EMAIL_PASS = os.environ["EMAIL_PASS"]
EMAIL_TO = os.environ["EMAIL_TO"]

msg = MIMEText("GitHub Actions email test successful!")

msg["Subject"] = "Assam Flood Alert Test"
msg["From"] = EMAIL_USER
msg["To"] = EMAIL_TO

with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
    server.login(EMAIL_USER, EMAIL_PASS)
    server.send_message(msg)

print("Email Sent Successfully")
