from fastapi import FastAPI, Form, Request
from fastapi.responses import Response
from twilio.twiml.messaging_response import MessagingResponse

app = FastAPI()

@app.post("/whatsapp-webhook")
async def whatsapp_reply(
    request: Request,
    From: str = Form(None),
    Body: str = Form(None)
):
    """
    Twilio WhatsApp Webhook to handle incoming messages.
    """
    # Handle both JSON and Form data inputs
    if request.headers.get("content-type") == "application/json":
        data = await request.json()
        From = data.get("From", "")
        Body = data.get("Body", "")

    # Create a Twilio response
    response = MessagingResponse()
    
    if Body and "sick" in Body.lower():
        response.message("Got it! We will notify available employees for shift replacement.")
    else:
        response.message("Thanks for your message. How can we assist you?")

    # ✅ Return response as XML with correct Content-Type
    return Response(content=str(response), media_type="application/xml")
