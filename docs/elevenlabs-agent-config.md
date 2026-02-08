# ElevenLabs Agent Configuration

This document describes the full configuration of the iConcierge Booking Agent in the ElevenLabs Conversational AI platform. Follow these steps to reproduce the agent setup.

## 1. Create Agent

1. Go to [ElevenLabs Dashboard](https://elevenlabs.io) > Agents Platform
2. Click **Create Agent**
3. Name: `iConcierge Booking Agent`

## 2. Configure LLM

- Model: **GPT-4o** (or latest available)
- Paste the system prompt below into the **System Prompt** field

### System Prompt

```
You are a professional scheduling assistant calling on behalf of {{patient_name}}.

You are calling {{provider_name}} to book a {{service_type}}.
Preferred date: {{preferred_date}}, preferred time: {{preferred_time}}.

Instructions:
1. Greet the receptionist professionally and state your purpose
2. Ask about availability for the preferred date and time
3. If the preferred slot is not available, ask for the nearest alternative
4. When a slot is proposed, use the "check_calendar" tool to verify the patient is free
5. If the patient is available, confirm the slot and use the "confirm_slot" tool
6. If the patient is NOT available, ask for another option
7. Thank the receptionist and end the call

Rules:
- Do NOT book a slot without first checking the patient's calendar via the tool
- Be polite, professional, and efficient
- Keep the call under 5 minutes
- If put on hold, wait patiently for up to 60 seconds
- If no slots are available, politely thank them and end the call
- Before ending any call, always say: "Thank you for your time. Have a great day!"
- Speak in {{language}}
```

## 3. Dynamic Variables

In **Agent Settings > Personalization > Dynamic Variables**, add:

| Variable | Description | Example Value |
|----------|-------------|---------------|
| `patient_name` | User's name | John Smith |
| `provider_name` | Provider being called | Dr. Johnson's Dental Office |
| `service_type` | Type of appointment | dental cleaning |
| `preferred_date` | Desired date | Tuesday, February 10th |
| `preferred_time` | Desired time of day | afternoon |
| `language` | Language to speak | English |

All variables are referenced in the system prompt via `{{variable_name}}` syntax.

## 4. First Message

Set in the **Agent** tab:

```
Hello, I'm calling on behalf of {{patient_name}} to schedule a {{service_type}}. Is this a good time?
```

## 5. End Call Tool

In **Tools > System Tools > End Call**:
- Verify it is enabled (added by default)
- Description: "End the call after the appointment is confirmed or when no slots are available, and after the agent has said its closing message"

## 6. Voice Selection

In **Voice** settings:
- Browse the **Voice Library** for a professional, neutral-sounding voice
- Select TTS model: **Eleven Flash v2.5** (low latency)

## 7. Security Settings

In the **Security** tab, enable:
- **System prompt override** (allows per-call customization for swarm mode)
- **First message override**
- **Dynamic variables**

## 8. Save and Store Agent ID

1. Save the agent configuration
2. Copy the `agent_id` from the agent settings
3. Store in `backend/.env`:
   ```
   ELEVENLABS_AGENT_ID=your-agent-id-here
   ```

## 9. Server Tools (Webhooks)

In **Agent > Tools > Add Tool**, add two server tools:

### check_calendar

| Field | Value |
|-------|-------|
| Name | check_calendar |
| Type | Webhook |
| URL | `https://<your-domain>/api/webhooks/tools/check_calendar` |
| Method | POST |
| Wait for response | Yes |
| Description | Check if the patient is available at the proposed date and time |

Parameters:
- `date` (string, required) - The proposed appointment date
- `time` (string, required) - The proposed appointment time

### confirm_slot

| Field | Value |
|-------|-------|
| Name | confirm_slot |
| Type | Webhook |
| URL | `https://<your-domain>/api/webhooks/tools/confirm_slot` |
| Method | POST |
| Wait for response | Yes |
| Description | Confirm and record the agreed appointment slot |

Parameters:
- `date` (string, required) - The confirmed appointment date
- `time` (string, required) - The confirmed appointment time
- `provider_notes` (string, optional) - Notes from the provider

### Local Development

For local development, expose the backend via ngrok:
```bash
ngrok http 8000
# Use the ngrok HTTPS URL as <your-domain> above
```

## 10. Testing

Use the ElevenLabs dashboard **Test** / **Simulate Conversations** feature to verify:
- Agent greets correctly with dynamic variable values
- System prompt instructions are followed
- Voice sounds professional
- End call behavior works as expected

## Environment Variables

| Variable | File | Description |
|----------|------|-------------|
| `ELEVENLABS_API_KEY` | `backend/.env` | ElevenLabs API key |
| `ELEVENLABS_AGENT_ID` | `backend/.env` | Agent ID from dashboard |

Both are already configured in `backend/app/config.py` and `backend/.env.example`.
