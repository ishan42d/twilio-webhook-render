from fastapi import FastAPI, Request, Form
from fastapi.responses import Response
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
from dotenv import load_dotenv
import os
import logging

# Load environment variables
load_dotenv()

ACCOUNT_SID = os.getenv("ACCOUNT_SID")
AUTH_TOKEN = os.getenv("AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP")  # Twilio Sandbox Number
REAL_EMPLOYEE_WHATSAPP_NUMBER = "whatsapp:+447766674459"  # Replace with actual employee's WhatsApp number

# Set up logging
logging.basicConfig(level=logging.INFO)

app = FastAPI()

# Track pending shift requests (key: employee number, value: shift info)
pending_requests = {}

# Track completed responses
completed_requests = {}

@app.post("/whatsapp-webhook")
async def whatsapp_reply(request: Request, From: str = Form(None), Body: str = Form(None)):
    """
    Handles incoming WhatsApp messages from Twilio.
    """
    global pending_requests, completed_requests

    if request.headers.get("content-type") == "application/json":
        data = await request.json()
        From = data.get("From", "")
        Body = data.get("Body", "")

    logging.info(f"Incoming message from {From}: {Body}")

    response = MessagingResponse()

    # Prevent further replies after Accept/Decline
    if From in completed_requests:
        response.message("❌ You’ve already responded to this request. No further action is needed.")
        return Response(content=str(response), media_type="application/xml")

    if "sick" in (Body or "").lower():
        logging.info("Employee reported sick. Notifying backup.")

        # Confirm to sick employee FIRST
        response.message("Got it! We will notify available employees for shift replacement.")
        twilio_response = Response(content=str(response), media_type="application/xml")

        # Notify employees AFTER returning response
        notify_real_employee()

        return twilio_response  # Ensures "Got it!" appears FIRST

    elif "accept" in (Body or "").lower():
        if From in pending_requests:
            logging.info(f"{From} accepted the shift.")
            response.message("✅ You have been assigned this shift successfully.")
            del pending_requests[From]  # Remove request
            completed_requests[From] = "accepted"  # Prevent further responses
        else:
            response.message("No pending shift request found for you.")

    elif "decline" in (Body or "").lower():
        if From in pending_requests:
            logging.info(f"{From} declined the shift.")
            response.message("❌ You have declined the shift request. Checking for the next available employee...")
            del pending_requests[From]  # Remove request
            completed_requests[From] = "declined"  # Prevent further responses
        else:
            response.message("No pending shift request found for you.")  # <-- Fixing this

    else:
        response.message("Thanks for your message. How can we assist you?")

    return Response(content=str(response), media_type="application/xml")

def notify_real_employee():
    """Send shift request message to an actual employee's WhatsApp number."""
    message_body = (
        "📢 Shift Alert: Can you backfill today's shift for Mr A? "
        "Reply 'Accept' to take the shift or 'Decline' if unavailable."
    )
    
    # Add the real employee to pending requests
    pending_requests[REAL_EMPLOYEE_WHATSAPP_NUMBER] = "Mr A's shift"

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
    except Exception as e:
        logging.error(f"Failed to send message to {to}: {str(e)}")
