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

app = FastAPI()

# Dictionary to track pending shift requests
pending_requests = {}

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

    response = MessagingResponse()

    if "sick" in (Body or "").lower():
        response.message("Got it! We will notify available employees for shift replacement.")
        notify_employee()  # Send backfill request to your actual WhatsApp number

    elif "accept" in (Body or "").lower():
        if From in pending_requests:
            response.message("✅ You have been assigned this shift successfully.")
            del pending_requests[From]  # Remove request after acceptance
        else:
            response.message("No pending shift request found for you.")

    elif "decline" in (Body or "").lower():
        if From in pending_requests:
            response.message("❌ You have declined the shift request. Checking for next available employee...")
            del pending_requests[From]  # Remove request
        else:
            response.message("No pending shift request found for you.")

    else:
        response.message("Thanks for your message. How can we assist you?")

    # Return response with the correct content type for Twilio
    return Response(content=str(response), media_type="application/xml")


def notify_employee():
    """Send shift request message to the employee's actual WhatsApp number."""
    message_body = (
        "📢 *Shift Alert!*\n"
        "Can you cover today's shift for Mr. A?\n\n"
        "✅ *Reply 'Accept'* to confirm.\n"
        "❌ *Reply 'Decline'* if you're unavailable."
    )
    
    send_whatsapp_message(EMPLOYEE_WHATSAPP_NUMBER, message_body)


def send_whatsapp_message(to, body):
    """Function to send a WhatsApp message via Twilio."""
    try:
        client = Client(ACCOUNT_SID, AUTH_TOKEN)
        msg = client.messages.create(
            from_=TWILIO_WHATSAPP_NUMBER,
            body=body,
            to=to
        )
        logging.info(f"Message sent to {to}: {msg.sid}")
    except Exception as e:
        logging.error(f"Failed to send message to {to}: {str(e)}")
