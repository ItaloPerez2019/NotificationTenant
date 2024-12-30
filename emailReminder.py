import os
import json
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from datetime import datetime
from dotenv import load_dotenv

# Get the absolute path for the log file in the script's directory
script_dir = os.path.dirname(os.path.abspath(__file__))
log_file_path = os.path.join(script_dir, "email_reminder.log")

# Configure Logging
logging.basicConfig(
    level=logging.INFO,  # Change to DEBUG for more detailed logs during troubleshooting
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        # Append mode to preserve existing logs
        logging.FileHandler(log_file_path, mode='a'),
        logging.StreamHandler()  # Logs to the console
    ]
)

logging.info("Script started.")

# Load environment variables from .env file
load_dotenv()

# Retrieve SMTP server details from environment variables
SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = os.getenv("SMTP_PORT")
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

# Validate SMTP details
if not SMTP_SERVER or not SMTP_PORT or not EMAIL_ADDRESS or not EMAIL_PASSWORD:
    logging.error("One or more SMTP environment variables are missing.")
    exit(1)

try:
    SMTP_PORT = int(SMTP_PORT)
except ValueError:
    logging.error(f"Invalid SMTP_PORT value: {SMTP_PORT}")
    exit(1)

# Load TENANTS from tenants.json file
tenants_file_path = os.path.join(script_dir, "tenants.json")
try:
    with open(tenants_file_path, 'r') as file:
        TENANTS = json.load(file)
        if not isinstance(TENANTS, list):
            logging.error(
                "tenants.json should be a JSON array of tenant objects.")
            TENANTS = []
except FileNotFoundError:
    logging.error(f"tenants.json file not found at {tenants_file_path}.")
    TENANTS = []
except json.JSONDecodeError as e:
    logging.error(f"tenants.json is not a valid JSON file: {e}")
    TENANTS = []

# Initialize counters and lists for tracking
success_count = 0
failure_count = 0
failed_tenants = []


def send_email_reminder(tenant):
    """
    Sends a rent payment reminder email to a single tenant.
    """
    global success_count, failure_count, failed_tenants
    try:
        # Validate required tenant fields
        required_fields = ["email", "name",
                           "payment_amount", "payment_description"]
        for field in required_fields:
            if field not in tenant:
                logging.error(f"Missing '{field}' in tenant data: {tenant}")
                failure_count += 1
                failed_tenants.append({
                    "tenant": tenant.get("name", "Unknown"),
                    "email": tenant.get("email", "Unknown"),
                    "reason": f"Missing field: {field}"
                })
                return

        # Ensure payment_amount is a float
        try:
            payment_amount = float(tenant['payment_amount'])
        except ValueError:
            logging.error(f"Invalid payment_amount for tenant {
                          tenant.get('name', 'Unknown')}: {tenant['payment_amount']}")
            failure_count += 1
            failed_tenants.append({
                "tenant": tenant.get("name", "Unknown"),
                "email": tenant.get("email", "Unknown"),
                "reason": f"Invalid payment_amount: {tenant['payment_amount']}"
            })
            return

        subject = "Rent Payment Reminder"
        body = f"""Dear {tenant['name']},

This is a friendly reminder that your rent payment of ${payment_amount:.2f} is due soon.

Payment Details:
Property: {tenant.get('property_location', 'N/A')}
Description: {tenant['payment_description']}
Amount: ${payment_amount:.2f}


If payment is not received by the 5th day of the month, a 10% late fee will be imposed.
If you have any questions or need more information, please visit:
https://segundorentalservices.net/

Thank you!
Landlord"""

        # Create email message
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = EMAIL_ADDRESS
        msg["To"] = tenant["email"]

        # Send email
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.sendmail(EMAIL_ADDRESS, tenant["email"], msg.as_string())

        logging.info(f"Reminder email sent successfully to {
                     tenant['name']} ({tenant['email']}).")
        success_count += 1

    except smtplib.SMTPException as smtp_err:
        logging.error(f"SMTP error when sending email to {
                      tenant.get('email', 'Unknown')}: {smtp_err}")
        failure_count += 1
        failed_tenants.append({
            "tenant": tenant.get("name", "Unknown"),
            "email": tenant.get("email", "Unknown"),
            "reason": f"SMTP error: {smtp_err}"
        })
    except Exception as e:
        logging.error(f"Unexpected error when sending email to {
                      tenant.get('email', 'Unknown')}: {e}")
        failure_count += 1
        failed_tenants.append({
            "tenant": tenant.get("name", "Unknown"),
            "email": tenant.get("email", "Unknown"),
            "reason": f"Unexpected error: {e}"
        })


def send_alert_email():
    """
    Sends an alert email to the landlord summarizing the email sending results.
    """
    try:
        subject = "Rent Reminder Emails Sent - Summary"
        body = f"""Hello,

All rent reminder emails have been processed.

Summary:
- Total Tenants: {len(TENANTS)}
- Successfully Sent: {success_count}
- Failed to Send: {failure_count}

"""
        if failure_count > 0:
            body += "Failed Tenants:\n"
            for failed in failed_tenants:
                body += f"- {failed['tenant']
                             } ({failed['email']}): {failed['reason']}\n"

        body += """

Best regards,
Your Automated Email System
"""

        # Create email message
        msg = MIMEMultipart()
        msg["Subject"] = subject
        msg["From"] = EMAIL_ADDRESS
        msg["To"] = 'iperezmba@gmail.com'  # Updated recipient

        # Attach the body text
        msg.attach(MIMEText(body, "plain"))

        # Send alert email
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.sendmail(EMAIL_ADDRESS, 'iperezmba@gmail.com',
                            msg.as_string())  # Updated recipient

        logging.info("Alert email sent successfully to the landlord.")

    except smtplib.SMTPException as smtp_err:
        logging.error(f"SMTP error when sending alert email: {smtp_err}")
    except Exception as e:
        logging.error(f"Unexpected error when sending alert email: {e}")


def send_log_email():
    """
    Sends the log file as an attachment to the landlord.
    """
    try:
        subject = "Email Reminder Logs - Execution Summary"
        body = f"""Hello,

Please find attached the log file for the latest execution of the email reminder script.

Best regards,
Your Automated Email System
"""

        # Create a multipart message
        msg = MIMEMultipart()
        msg["Subject"] = subject
        msg["From"] = EMAIL_ADDRESS
        msg["To"] = 'iperezmba@gmail.com'  # Updated recipient

        # Attach the body text
        msg.attach(MIMEText(body, "plain"))

        # Attach the log file
        with open(log_file_path, "rb") as log_file:
            part = MIMEApplication(
                log_file.read(), Name=os.path.basename(log_file_path))
            # After the file is closed
            part['Content-Disposition'] = f'attachment; filename="{
                os.path.basename(log_file_path)}"'
            msg.attach(part)

        # Send log email
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.sendmail(EMAIL_ADDRESS, 'iperezmba@gmail.com',
                            msg.as_string())  # Updated recipient

        logging.info("Log email sent successfully to the landlord.")

    except FileNotFoundError:
        logging.error(f"Log file not found at {
                      log_file_path}. Cannot send log email.")
    except smtplib.SMTPException as smtp_err:
        logging.error(f"SMTP error when sending log email: {smtp_err}")
    except Exception as e:
        logging.error(f"Unexpected error when sending log email: {e}")


def send_emails_to_all_tenants():
    """
    Sends reminder emails to all tenants.
    """
    if not TENANTS:
        logging.warning("No tenants found to send emails.")
        return

    for tenant in TENANTS:
        send_email_reminder(tenant)


def check_and_send_email():
    """
    Executes the entire email sending process: reminders, alerts, and logs.
    """
    send_emails_to_all_tenants()
    send_alert_email()
    send_log_email()


if __name__ == "__main__":
    check_and_send_email()
    logging.info("Script execution completed.")
