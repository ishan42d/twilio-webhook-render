from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import Response
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
from dotenv import load_dotenv
import os
import logging
import time  # Add time module for delay

# Load environment variables
load_dotenv()

ACCOUNT_SID = os.getenv("ACCOUNT_SID")
AUTH_TOKEN = os.getenv("AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP")  # Twilio Sandbox Number
REAL_EMPLOYEE_WHATSAPP_NUMBER = "whatsapp:+44XXXXXXX"  # Employee's WhatsApp number

# Set up logging
logging.basicConfig(level=logging.INFO)

app = FastAPI()

# Track pending shift requests (key: employee number, value: shift status)
pending_requests = {}

def normalize_number(phone_number):
    """Normalize phone numbers to ensure consistency in dictionary keys."""
    if not phone_number:
        return None  # Handle missing phone numbers
    return phone_number.strip().lower()

@app.post("/whatsapp-webhook")
async def whatsapp_reply(request: Request, From: str = Form(None), Body: str = Form(None)):
    """
    Handles incoming WhatsApp messages from Twilio.
    """
    global pending_requests

    try:
        request_data = await request.form()  # Extract form data
        logging.info(f"Received WhatsApp request: {dict(request_data)}")
    except Exception as e:
        logging.error(f"Error parsing request: {str(e)}")
        raise HTTPException(status_code=400, detail="Invalid request format")

    if not From:
        logging.error("Missing 'From' field in request.")
        return Response(content="<Response><Message>Error: Missing sender information.</Message></Response>", media_type="application/xml")

    From = normalize_number(From)
    Body = Body.strip().lower() if Body else ""

    logging.info(f"Incoming message from {From}: {Body}")

    response = MessagingResponse()

    if "sick" in Body:
        logging.info("Employee reported sick. Notifying backup.")

        # Store the shift as pending
        pending_requests[normalize_number(REAL_EMPLOYEE_WHATSAPP_NUMBER)] = "pending"

        # Send immediate "Got it" response
        response.message("Got it! We will notify available employees for shift replacement.")
        twilio_response = Response(content=str(response), media_type="application/xml")

        # Introduce a slight delay to ensure "Got it!" appears first
        time.sleep(2)

        # Send shift request message after "Got it!"
        send_whatsapp_message(REAL_EMPLOYEE_WHATSAPP_NUMBER, 
            "\U0001F4E2 Shift Alert: Can you backfill today's shift for Mr A? "
            "Reply 'Accept' to take the shift or 'Decline' if unavailable."
        )

        return twilio_response

    elif "accept" in Body:
        if pending_requests.get(From) == "pending":
            response.message("✅ You have been assigned this shift successfully.")
            pending_requests[From] = "accepted"
        else:
            response.message("❌ You’ve already responded to this request. No further action is needed.")

    elif "decline" in Body:
        if pending_requests.get(From) == "pending":
            response.message("❌ You have declined the shift request. Checking for the next available employee...")
            pending_requests[From] = "declined"
        else:
            response.message("❌ You’ve already responded to this request. No further action is needed.")

    else:
        if pending_requests.get(From) in ["accepted", "declined"]:
            response.message("❌ You’ve already responded to this request. No further action is needed.")
        else:
            response.message("Thanks for your message. How can we assist you?")

    return Response(content=str(response), media_type="application/xml")

def send_whatsapp_message(to, message_body):
    """Function to send a WhatsApp message via Twilio."""
    try:
        client = Client(ACCOUNT_SID, AUTH_TOKEN)
        client.messages.create(
            from_=TWILIO_WHATSAPP_NUMBER,
            body=message_body,
            to=to
        )
        logging.info(f"✅ Message sent to {to}: {message_body}")
    except Exception as e:
        logging.error(f"❌ Failed to send message to {to}: {str(e)}")
