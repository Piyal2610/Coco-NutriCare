import smtplib
from email.message import EmailMessage
from flask import current_app


def send_email(to, subject, body):
    config = current_app.config
    if not config.get("MAIL_USERNAME") or not config.get("MAIL_PASSWORD"):
        current_app.logger.warning("Mail is not configured. Email to %s:\n%s", to, body)
        return False

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = config["MAIL_USERNAME"]
    message["To"] = to
    message.set_content(body)

    try:
        with smtplib.SMTP(config["MAIL_SERVER"], config["MAIL_PORT"]) as server:
            server.starttls()
            server.login(config["MAIL_USERNAME"], config["MAIL_PASSWORD"])
            server.send_message(message)
        return True
    except (smtplib.SMTPException, OSError) as error:
        current_app.logger.error("Failed to send email to %s: %s", to, error)
        return False