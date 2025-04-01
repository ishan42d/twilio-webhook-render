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

app = FastAPI()
logging.basicConfig(level=logging.INFO)

# Dictionary to track pending shift requests
pending_requests = {}

@app.post("/whatsapp-webhook")
async def whatsapp_reply(
    request: Request,
    From: str = Form(...),  # Ensure Twilio properly extracts 'From'
    Body: str = Form(...)
):
    """
    Twilio WhatsApp Webhook to handle incoming messages.
    """
    global pending_requests
    logging.info(f"Incoming message from {From}: {Body}")
    
    response = MessagingResponse()
    
    if "sick" in Body.lower():
        response.message("Got it! We will notify available employees for shift replacement.")
        notify_available_employees()
    
    elif "accept" in Body.lower():
        if From in pending_requests:
            response.message("You have been assigned this shift successfully.")
            del pending_requests[From]  # Remove request after acceptance
        else:
            response.message("No pending shift request found for you.")
    
    elif "decline" in Body.lower():
        if From in pending_requests:
            response.message("You have declined the shift. We will forward this to the next available employee. Thank you!")
            del pending_requests[From]  # Remove request and forward to next employee
            notify_next_employee()
        else:
            response.message("No pending shift request found for you.")
    
    else:
        response.message("Thanks for your message. How can we assist you?")
    
    return str(response)


def notify_available_employees():
    """Send shift request message to available employees."""
    available_employees = ["+1234567890", "+0987654321"]  # Example numbers (E.164 format)
    message = "Can you please backfill the shift today for Mr. A as he is off sick today? Reply with 'Accept' or 'Decline'."
    
    for employee in available_employees:
        formatted_number = format_phone_number(employee)
        if formatted_number:
            pending_requests[formatted_number] = True  # Track pending request
            send_whatsapp_message(formatted_number, message)


def notify_next_employee():
    """Forward the shift request to the next available employee."""
    available_employees = ["+447766674459"]  # Replace with real numbers
    if available_employees:
        next_employee = format_phone_number(available_employees[0])  # Pick the first available employee
        if next_employee:
            pending_requests[next_employee] = True
            send_whatsapp_message(next_employee, "Can you please backfill the shift today for Mr. A? Reply with 'Accept' or 'Decline'.")


def send_whatsapp_message(to, message):
    """Function to send a WhatsApp message via Twilio."""
    try:
        client = Client(ACCOUNT_SID, AUTH_TOKEN)
        
        # Ensure 'to' number is formatted correctly
        formatted_to = f"whatsapp:{to}" if not to.startswith("whatsapp:") else to
        logging.info(f"Sending WhatsApp message to: {formatted_to}")
        
        message = client.messages.create(
            from_=TWILIO_WHATSAPP_NUMBER,  # Ensure this is formatted correctly
            body=message,
            to=formatted_to
        )
        logging.info(f"Message sent successfully: {message.sid}")
    except Exception as e:
        logging.error(f"Failed to send message to {to}: {str(e)}")


def format_phone_number(phone_number):
    """Ensure phone numbers are in E.164 format."""
    if phone_number.startswith("+"):
        return phone_number  # Already in correct format
    logging.error(f"Invalid phone number format: {phone_number}")
    return None
