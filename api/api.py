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

# Track completed responses (key: employee number, value: response)
completed_requests = {}

# Track which employee reported sick (key: sick employee number, value: True)
sick_employees = {}

@app.post("/whatsapp-webhook")
async def whatsapp_reply(request: Request, From: str = Form(None), Body: str = Form(None)):
    """
    Handles incoming WhatsApp messages from Twilio.
    """
    global pending_requests, completed_requests, sick_employees
    
    # Extract message data from request
    if request.headers.get("content-type") == "application/json":
        data = await request.json()
        From = data.get("From", "")
        Body = data.get("Body", "")
    
    # Ensure From and Body are lowercase strings
    From = str(From).strip()
    Body = str(Body or "").lower().strip()
    
    logging.info(f"Incoming message from {From}: {Body}")
    response = MessagingResponse()
    
    # Check if this person has already responded to a request
    if From in completed_requests:
        response.message("❌ You've already responded to this request. No further action is needed.")
        return Response(content=str(response), media_type="application/xml")
    
    # Handle sick employee message
    if "sick" in Body:
        logging.info(f"Employee {From} reported sick. Notifying backup.")
        
        # Mark this employee as sick
        sick_employees[From] = True
        
        # Confirm to sick employee
        response.message("Got it! We will notify available employees for shift replacement.")
        twilio_response = Response(content=str(response), media_type="application/xml")
        
        # Notify backup employee
        notify_real_employee(From)
        
        return twilio_response
    
    # Handle accept message
    elif "accept" in Body:
        if From in pending_requests:
            logging.info(f"{From} accepted the shift for {pending_requests[From]}.")
            response.message("✅ You have been assigned this shift successfully.")
            
            # Mark this request as completed with "accepted" status
            completed_requests[From] = "accepted"
            del pending_requests[From]  # Remove from pending
        else:
            response.message("No pending shift request found for you.")
    
    # Handle decline message
   else: "decline" in Body:
        if From in pending_requests:
            logging.info(f"{From} declined the shift for {pending_requests[From]}.")
            response.message("❌ You have declined the shift request. Checking for the next available employee...")
            
            # Mark this request as completed with "declined" status
            completed_requests[From] = "declined"
            del pending_requests[From]  # Remove from pending
            
            # Could add logic here to notify next employee
        else:
            response.message("No pending shift request found for you.")
    
    return Response(content=str(response), media_type="application/xml")

def notify_real_employee(sick_employee_number):
    """Send shift request message to an actual employee's WhatsApp number."""
    # Extract employee name or use a placeholder
    employee_name = "Mr A"  # You could extract a real name if available
    
    message_body = (
        f"📢 Shift Alert: Can you backfill today's shift for {employee_name}? "
        "Reply 'Accept' to take the shift or 'Decline' if unavailable."
    )
    
    # Add the real employee to pending requests with reference to sick employee
    pending_requests[REAL_EMPLOYEE_WHATSAPP_NUMBER] = sick_employee_number
    
    # Send the message
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
