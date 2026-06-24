import os
import smtplib
from email.mime.text import MIMEText

EMAIL_USER = os.environ["EMAIL_USER"].strip()
EMAIL_PASS = os.environ["EMAIL_PASS"].strip()

EMAIL_TO = [
    x.strip()
    for x in os.environ["EMAIL_TO"].split(",")
]

msg = MIMEText("GitHub Email Test Success")

msg["Subject"] = "Assam Flood Alert Test"
msg["From"] = EMAIL_USER
msg["To"] = ", ".join(EMAIL_TO)

with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:

    server.login(
        EMAIL_USER,
        EMAIL_PASS
    )

    server.sendmail(
        EMAIL_USER,
        EMAIL_TO,
        msg.as_string()
    )

print("Email Sent Successfully")
