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
EMPLOYEE_WHATSAPP_NUMBER = "whatsapp:+447766674459"  # Replace with actual employee's WhatsApp number

# Set up logging
logging.basicConfig(level=logging.INFO)

app = FastAPI()

@app.post("/whatsapp-webhook")
async def whatsapp_reply(request: Request, From: str = Form(None), Body: str = Form(None)):
    """
    Handles incoming WhatsApp messages and sends notifications for shift replacement.
    """
    if request.headers.get("content-type") == "application/json":
        data = await request.json()
        From = data.get("From", "")
        Body = data.get("Body", "").strip().lower()

    logging.info(f"Incoming message from {From}: {Body}")

    response = MessagingResponse()

    if "sick" in Body:
        logging.info("Employee reported sick. Notifying backup.")

        # Confirm to sick employee FIRST
        response.message("Got it! We will notify available employees for shift replacement.")
        twilio_response = Response(content=str(response), media_type="application/xml")

        # Notify available employees AFTER returning response
        notify_employees()

        return twilio_response  # Ensures "Got it!" appears first

    return Response(content=str(response), media_type="application/xml")

def notify_employees():
    """Send shift request message to all available employees."""
    message_body = (
        "📢 Shift Alert: Can you backfill today's shift for Mr A?"
    )
    send_whatsapp_message(EMPLOYEE_WHATSAPP_NUMBER, message_body)

def send_whatsapp_message(to, message_body):
    """Function to send a WhatsApp message via Twilio."""
    try:
        client = Client(ACCOUNT_SID, AUTH_TOKEN)
        client.messages.create(
            from_=TWILIO_WHATSAPP_NUMBER,
            body=message_body,
            to=to
        )
        logging.info(f"Shift request sent to {to}")
    except Exception as e:
        logging.error(f"Failed to send message to {to}: {str(e)}")
