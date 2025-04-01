from fastapi import FastAPI, Request, Form
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
from dotenv import load_dotenv
import os
import logging

# Load environment variables
load_dotenv()

ACCOUNT_SID = os.getenv("ACCOUNT_SID")
AUTH_TOKEN = os.getenv("AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP")
EMPLOYEE_WHATSAPP_NUMBER = "whatsapp:+447766674459"  # Your actual WhatsApp number

app = FastAPI()

# Dictionary to track pending shift requests
pending_requests = {}

# Configure logging
logging.basicConfig(level=logging.INFO)

@app.post("/whatsapp-webhook")
async def whatsapp_reply(request: Request, From: str = Form(None), Body: str = Form(None)):
    """
    Twilio WhatsApp Webhook to handle incoming messages.
    """
    global pending_requests

    if request.headers.get("content-type") == "application/json":
        data = await request.json()
        From = data.get("From", "")
        Body = data.get("Body", "")

    logging.info(f"Incoming message from {From}: {Body}")
    response = MessagingResponse()

    if "sick" in (Body or "").lower():
        logging.info("Employee reported sick. Notifying backup.")
        response.message("Got it! We will notify available employees for shift replacement.")
        notify_employee()
    
    elif "accept" in (Body or "").lower():
        logging.info(f"Received 'Accept' from {From}. Checking pending requests.")

        if From in pending_requests:
            response.message("✅ You have been assigned this shift successfully.")
            del pending_requests[From]  # Remove request after acceptance
        else:
            response.message("❌ No pending shift request found for you. Are you responding to a valid shift request?")
    
    elif "decline" in (Body or "").lower():
        if From in pending_requests:
            response.message("❌ You have declined the shift request. Checking for next available employee...")
            del pending_requests[From]  # Remove request
        else:
            response.message("No pending shift request found for you.")
    
    else:
        response.message("Thanks for your message. How can we assist you?")

    return str(response)  # Ensures TwiML response with correct Content-Type


def notify_employee():
    """Send shift request message to your actual WhatsApp number and track it."""
    global pending_requests  # Ensure we're updating the global dictionary

    message = "📢 Shift Alert: Can you backfill today's shift for Mr. A? Reply with 'Accept' or 'Decline'."
    
    # Store the pending request for your WhatsApp number
    pending_requests[EMPLOYEE_WHATSAPP_NUMBER] = True  

    # Send the message to the correct employee number
    send_whatsapp_message(EMPLOYEE_WHATSAPP_NUMBER, message)


def send_whatsapp_message(to, message):
    """Function to send a WhatsApp message via Twilio."""
    try:
        client = Client(ACCOUNT_SID, AUTH_TOKEN)
        msg = client.messages.create(
            from_=TWILIO_WHATSAPP_NUMBER,
            body=message,
            to=to  # Ensure correct recipient
        )
        logging.info(f"Message sent to {to}: {msg.sid}")
    except Exception as e:
        logging.error(f"Failed to send message to {to}: {str(e)}")
