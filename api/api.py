from fastapi import FastAPI, Request, Form
from fastapi.responses import Response
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
from dotenv import load_dotenv
import os
import logging
import time

# Load environment variables
load_dotenv()

ACCOUNT_SID = os.getenv("ACCOUNT_SID")
AUTH_TOKEN = os.getenv("AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP")  # Twilio Sandbox Number
REAL_EMPLOYEE_WHATSAPP_NUMBER = "whatsapp:+447766674459"  # Employee's WhatsApp number

# Set up logging
logging.basicConfig(level=logging.INFO)

app = FastAPI()

# Track pending shift requests (key: employee number, value: shift status)
pending_requests = {}

def normalize_number(phone_number):
    """Normalize phone numbers to ensure consistency in dictionary keys."""
    return phone_number.strip().lower()

@app.post("/whatsapp-webhook")
async def whatsapp_reply(request: Request, From: str = Form(None), Body: str = Form(None)):
    """
    Handles incoming WhatsApp messages from Twilio.
    """
    global pending_requests

    # Log the raw request data to understand what is being received
    raw_data = await request.json()
    logging.info(f"Raw incoming request: {raw_data}")

    # Handle JSON content if it comes from Twilio webhook
    if request.headers.get("content-type") == "application/json":
        From = raw_data.get("From", "")
        Body = raw_data.get("Body", "")

    # Check if 'From' is valid, return error if missing
    if not From:
        logging.error("Error: 'From' is None or empty")
        return Response(content="Invalid request", status_code=400)

    # Normalize the phone number to ensure consistency
    From = normalize_number(From)
    logging.info(f"Incoming message from {From}: {Body}")

    response = MessagingResponse()
    body_lower = (Body or "").strip().lower()

    # Case 1: Employee reports sick and the shift needs to be filled
    if "sick" in body_lower:
        logging.info("Employee reported sick. Notifying backup.")
        pending_requests[normalize_number(REAL_EMPLOYEE_WHATSAPP_NUMBER)] = "pending"
        response.message("Got it! We will notify available employees for shift replacement.")
        twilio_response = Response(content=str(response), media_type="application/xml")
        time.sleep(2)  # 2-second delay
        notify_real_employee()
        return twilio_response

    # Case 2: Employee accepts the shift
    elif "accept" in body_lower:
        if pending_requests.get(From) == "pending":
            response.message("✅ You have been assigned this shift successfully.")
            pending_requests[From] = "accepted"
        else:
            response.message("❌ You’ve already responded to this request. No further action is needed.")

    # Case 3: Employee declines the shift
    elif "decline" in body_lower:
        if pending_requests.get(From) == "pending":
            response.message("❌ You have declined the shift request. Checking for the next available employee...")
            pending_requests[From] = "declined"
        else:
            response.message("❌ You’ve already responded to this request. No further action is needed.")

    # Default case: Handle other queries
    else:
        response.message("Thanks for your message. How can we assist you?")

    return Response(content=str(response), media_type="application/xml")

def notify_real_employee():
    """Send shift request message to an actual employee's WhatsApp number."""
    message_body = (
        "\U0001F4E2 Shift Alert: Can you backfill today's shift for Mr A? "
        "Reply 'Accept' to take the shift or 'Decline' if unavailable."
    )
    send_whatsapp_message(REAL_EMPLOYEE_WHATSAPP_NUMBER, message_body)

def send_whatsapp_message(to, message_body):
    """Function to send a WhatsApp message via Twilio."""
    try:
        client = Client(ACCOUNT_SID, AUTH_TOKEN)
        client.messages.create(
            from_=TWILIO_WHATSAPP_NUMBER,
            body=message_body,
            to=to
        )
        logging.info(f"Message sent to {to}: {message_body}")
    except Exception as e:
        logging.error(f"Failed to send message to {to}: {str(e)}")
