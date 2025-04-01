from fastapi import FastAPI, Request, Form
from twilio.twiml.messaging_response import MessagingResponse

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
        notify_available_employees()
    
    elif "accept" in (Body or "").lower():
        if From in pending_requests:
            response.message("You have been assigned this shift successfully.")
            del pending_requests[From]  # Remove request after acceptance
        else:
            response.message("No pending shift request found for you.")
    
    elif "decline" in (Body or "").lower():
        if From in pending_requests:
            response.message("You have chosen to decline the shift request. We will now forward this to the next available employee. Thank you!")
            del pending_requests[From]  # Remove request and forward to next employee
            notify_next_employee()
        else:
            response.message("No pending shift request found for you.")
    
    else:
        response.message("Thanks for your message. How can we assist you?")
    
    return str(response)


def notify_available_employees():
    """Send shift request message to available employees."""
    available_employees = ["whatsapp:+1234567890", "whatsapp:+0987654321"]  # Example numbers
    message = "Can you please backfill the shift today for Mr. A as he is off sick today? Reply with 'Accept' or 'Decline'."
    for employee in available_employees:
        pending_requests[employee] = True  # Track pending request
        send_whatsapp_message(employee, message)


def notify_next_employee():
    """Forward the shift request to the next available employee."""
    available_employees = ["whatsapp:+1122334455", "whatsapp:+5566778899"]  # Example alternative numbers
    if available_employees:
        next_employee = available_employees[0]  # Pick the first available employee
        pending_requests[next_employee] = True
        send_whatsapp_message(next_employee, "Can you please backfill the shift today for Mr. A? Reply with 'Accept' or 'Decline'.")


def send_whatsapp_message(to, message):
    """Function to send a WhatsApp message via Twilio."""
    from twilio.rest import Client
    
    ACCOUNT_SID = "your_twilio_account_sid"
    AUTH_TOKEN = "your_twilio_auth_token"
    TWILIO_WHATSAPP_NUMBER = "whatsapp:+your_twilio_number"
    
    client = Client(ACCOUNT_SID, AUTH_TOKEN)
    client.messages.create(
        from_=TWILIO_WHATSAPP_NUMBER,
        body=message,
        to=to
    )
