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

    # Check if From is None or empty
    if not From:
        logging.error("Error: 'From' is None or empty")
        return Response(content="Invalid request", status_code=400)

    From = normalize_number(From)
    logging.info(f"Incoming message from {From}: {Body}")

    response = MessagingResponse()
    body_lower = (Body or "").strip().lower()

    if "sick" in body_lower:
        logging.info("Employee reported sick. Notifying backup.")

        # Store the shift as pending
        pending_requests[REAL_EMPLOYEE_WHATSAPP_NUMBER] = "pending"

        # Send response immediately before notifying others
        response.message("Got it! We will notify available employees for shift replacement.")
        twilio_response = Response(content=str(response), media_type="application/xml")
        
        # Delay sending the shift request to make sure "Got it!" appears first
        time.sleep(2)  # 2-second delay
        notify_real_employee()
        
        return twilio_response

    elif "accept" in body_lower:
        if pending_requests.get(From) == "pending":
            response.message("✅ You have been assigned this shift successfully.")
            pending_requests[From] = "accepted"
        else:
            response.message("❌ You’ve already responded to this request. No further action is needed.")

    elif "decline" in body_lower:
        if pending_requests.get(From) == "pending":
            response.message("❌ You have declined the shift request. Checking for the next available employee...")
            pending_requests[From] = "declined"
        else:
            response.message("❌ You’ve already responded to this request. No further action is needed.")

    else:
        response.message("Thanks for your message. How can we assist you?")

    return Response(content=str(response), media_type="application/xml")
