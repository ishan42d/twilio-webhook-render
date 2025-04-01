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
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP")
EMPLOYEE_WHATSAPP_NUMBER = "whatsapp:+447766674459"  # Your actual WhatsApp number

# Set up logging
logging.basicConfig(level=logging.INFO)

app = FastAPI()

# Dictionary to track pending shift requests
pending_requests = {}

@app.post("/whatsapp-webhook")
async def whatsapp_reply(request: Request, From: str = Form(None), Body: str = Form(None)):
    """
    Handles incoming WhatsApp messages from Twilio.
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
        
        # Store the request
        pending_requests[From] = True
        notify_employee(From)  # Notify replacement candidate

    elif "accept" in (Body or "").lower():
        if From in pending_requests:
            logging.info(f"{From} accepted the shift.")
            response.message("✅ You have been assigned this shift successfully.")
            del pending_requests[From]  # Remove request after acceptance
        else:
            logging.info(f"{From} tried to accept a shift, but no pending request found.")
            response.message("No pending shift request found for you.")

    elif "decline" in (Body or "").lower():
        if From in pending_requests:
            logging.info(f"{From} declined the shift.")
            response.message("❌ You have declined the shift request. Checking for the next available employee...")
            del pending_requests[From]  # Remove request
        else:
            logging.info(f"{From} tried to decline a shift, but no pending request found.")
            response.message("No pending shift request found for you.")

    else:
        response.message("Thanks for your message. How can we assist you?")

    # Ensure Twilio receives the correct Content-Type
    twilio_response = Response(content=str(response), media_type="application/xml")
    return twilio_response

def notify_employee(sick_employee):
    """Send shift request message to the employee's WhatsApp number."""
    message_body = (
        f"📢 Shift Alert: Can you backfill today's shift for {sick_employee}? Reply 'Accept' to take the shift or 'Decline' if unavailable."
    )
    send_whatsapp_message(EMPLOYEE_WHATSAPP_NUMBER, message_body)

def send_whatsapp_message(to, message_body):
    """Function to send a WhatsApp message via Twilio."""
    try:
        client = Client(ACCOUNT_SID, AUTH_TOKEN)
        msg = client.messages.create(
            from_=TWILIO_WHATSAPP_NUMBER,
            body=message_body,
            to=to
        )
        logging.info(f"Message sent to {to}: {msg.sid}")
    except Exception as e:
        logging.error(f"Failed to send message to {to}: {str(e)}")
