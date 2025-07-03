# backend/email_service.py
import yagmail
import os
import logging
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

EMAIL_USERNAME = os.getenv("EMAIL_USERNAME")
EMAIL_APP_PASSWORD = os.getenv("EMAIL_APP_PASSWORD")

def send_confirmation_email(recipient_email: str, subject: str, body: str):
    """Sends an email using Yagmail."""
    if not EMAIL_USERNAME or not EMAIL_APP_PASSWORD:
        logger.warning("Email credentials not set. Cannot send email.")
        return False

    try:
        yag = yagmail.SMTP({EMAIL_USERNAME: "Smart Doctor Assistant"}, EMAIL_APP_PASSWORD)
        yag.send(
            to=recipient_email,
            subject=subject,
            contents=body
        )
        logger.info(f"Confirmation email sent to {recipient_email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {recipient_email}: {e}")
        return False

if __name__ == "__main__":
    # Ensure EMAIL_USERNAME and EMAIL_APP_PASSWORD are set in your .env for independent testing
    test_recipient = "test@example.com" # Replace with a real email for testing
    test_subject = "Test Subject from Smart Doctor Assistant"
    test_body = "Hello from Smart Doctor Assistant! This is a test email."

    if send_confirmation_email(test_recipient, test_subject, test_body):
        logger.info("Test email initiated.")
    else:
        logger.warning("Failed to initiate test email. Check logs for details.")