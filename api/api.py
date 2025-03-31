from fastapi import FastAPI, Form, Request
from twilio.twiml.messaging_response import MessagingResponse

app = FastAPI()

@app.post("/whatsapp-webhook")
async def whatsapp_reply(request: Request, From: str = Form(None), Body: str = Form(None)):
    """
    Twilio WhatsApp Webhook to handle incoming messages.
    """
    if request.headers.get("content-type") == "application/json":
        data = await request.json()
        From = data.get("From", "")
        Body = data.get("Body", "")

    response = MessagingResponse()
    
    if "sick" in (Body or "").lower():
        response.message("Got it! We will notify available employees for shift replacement.")
    else:
        response.message("Thanks for your message. How can we assist you?")

    return str(response)
