import os
import json
import schedule
import smtplib
import time
from email.mime.text import MIMEText
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = os.getenv("SMTP_PORT") 
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

# Load TENANTS from the JSON stored in .env
TENANTS = json.loads(os.getenv("TENANTS_JSON", "[]"))

def send_email_reminder(tenant):
    try:
        subject = "Rent Payment Reminder"
        body = f"""Dear {tenant['name']},

This is a friendly reminder that your rent payment of ${tenant['payment_amount']:.2f} is due soon.

Payment Details:
Description: {tenant['payment_description']}
Amount: ${tenant['payment_amount']:.2f}

If you have any questions or need more information, please visit:
https://segundorentalservices.net/

Thank you!
Landlord"""

        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = EMAIL_ADDRESS
        msg["To"] = tenant["email"]

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.sendmail(EMAIL_ADDRESS, tenant["email"], msg.as_string())
        
        print(f"Reminder email sent successfully to {tenant['email']}.")
    except Exception as e:
        print(f"Error sending email to {tenant['email']}: {e}")

def send_emails_to_all_tenants():
    for tenant in TENANTS:
        send_email_reminder(tenant)

def check_and_send_email():
    current_time = datetime.now()
    if current_time.day == 1 and current_time.strftime("%H:%M") == "07:00":
        send_emails_to_all_tenants()


def schedule_monthly_tasks():
    schedule.every(1).minutes.do(check_and_send_email)
    print("Scheduled monthly reminders.")

    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    schedule_monthly_tasks()

