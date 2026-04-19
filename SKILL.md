---
name: whatsapp-listen
description: A WhatsApp listening skill that triggers on specific intents.
---

## Instructions
To set up the send-email pattern for your WhatsApp listening skill, you need to provide the following parameters to the `run_intent` tool:

- **webhook_payload**: The data received from the webhook when a WhatsApp message is sent.
- **openai_api_key**: Your OpenAI API Key for accessing the model.
- **whatsapp_api_token**: The token for authenticating with the WhatsApp API.
- **whatsapp_phone_number_id**: The ID of the phone number you are using with WhatsApp.
- **gpt_model**: The model to use for generating responses (e.g., "gpt-3.5-turbo").
- **system_prompt**: A string that defines the system's behavior or persona.
- **max_history**: The maximum number of past messages to consider for context.

Make sure that all parameters are correctly configured to ensure the skill functions properly.