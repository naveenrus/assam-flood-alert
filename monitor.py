import smtplib
from email.mime.text import MIMEText

body = f"""
Flood Districts:
{chr(10).join(districts)}

Heavy Rainfall:

{chr(10).join([f"{s} : {r} mm" for s,r in heavy])}
"""

msg = MIMEText(body)

msg["Subject"] = "🚨 Assam Flood Alert"
msg["From"] = EMAIL_USER
msg["To"] = EMAIL_TO

with smtplib.SMTP_SSL("smtp.gmail.com",465) as server:

    server.login(
        EMAIL_USER,
        EMAIL_PASS
    )

    server.send_message(msg)