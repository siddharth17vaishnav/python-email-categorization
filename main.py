import json
import re

import openai
import os

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from utils.extraction import extract_text_from_pdf, extract_text_from_image
from contants import CLIENT_SECRETS_FILE, SCOPES, TOKEN_FILE, REDIRECT_URI

app = FastAPI()
os.environ["OPENAI_API_KEY"] = "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"

openai.api_key = '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'



def get_authorization_url():
    flow = Flow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
    authorization_url, _ = flow.authorization_url(prompt="consent")
    return authorization_url


def authorize_and_get_credentials(code: str):
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE, SCOPES, redirect_uri=REDIRECT_URI
    )
    flow.fetch_token(code=code)
    credentials = flow.credentials
    with open(TOKEN_FILE, "w") as token_file:
        token_file.write(credentials.to_json())

    return credentials


def get_gmail_service(credentials):
    service = build("gmail", "v1", credentials=credentials)
    return service.users()


def get_attachment(service, attachment_id, message_id):
    attachment = (
        service.messages()
        .attachments()
        .get(userId="me", messageId=message_id, id=attachment_id)
        .execute()
    )
    return attachment


def get_messages(service, message_id):
    message = (
        service.messages().get(userId="me", id=message_id, format="full").execute()
    )
    return message


def extract_attachments(service, message, message_id):
    payload = message.get("payload")
    parts = payload.get("parts")
    attachments = []
    if "parts" in payload:
        for part in parts:
            if part["mimeType"] == "image/png" or part["mimeType"] == "application/pdf":
                data = part["body"]
                attachment_id = data.get("attachmentId")
                attachment = get_attachment(service, attachment_id, message_id)
                attachment_data = attachment.get("data")

                if part["mimeType"] == "application/pdf":
                    data = extract_text_from_pdf(attachment_data)
                elif part["mimeType"] == "image/png":
                    data = extract_text_from_image(attachment_data)
                attachment_info = {
                    "filename": part.get("filename", ""),
                    "mimeType": part.get("mimeType", ""),
                    "extracted_text": data,
                }
                attachments.append(attachment_info)
    return attachments


def remove_special_characters(input_string):
    pattern = r'[^A-Za-z0-9\s]'
    result_string = re.sub(pattern, '', input_string)
    return result_string


# def generate_prompt(email_body):
#     prompt = f"Email Body: {email_body}\n\nCategorize the email:"
#     return prompt


def gen(body, attachment, sender, date, subject):
    prompt = f"Email Body: {body}\n\nAttachment: {attachment}\n\nSender: {sender}\n\nDate: {date}\n\nSubject: {subject}\n\nGenerate a response in the following format and return only valid data:\n\nRESPONSE =[\n  {{\n    \"Category\": \"Accounts\",\n    \"Email Type\": \"Updates\",\n    \"Email Use Case\": \"Account Creation\",\n    \"Description\",\n    \"Sender Data\": {{\n      \"Sender name (text)\": \"Sender1\",\n      \"Sender email domain (text)\": \"domain1.com\",\n      \"Sender icon (jpg)\": \"icon1.jpg\",\n      \"Time sent (mm/dd/yy 00:00)\": \"01/01/22 12:00\"\n    }},\n    \"Length of summary blurb\": \"150 characters or less\",\n    \"Unique Data Required\": \"Username or account ID (text)\"\n  }},\n  {{\n    \"Category\": \"Personal\",\n    \"Email Type\": \"Inbound (Unknown Sender)\",\n    \"Email Use Case\": \"Networking\",\n    \"Description\": \"An 'inbound' is an email from an unknown sender, typically looking to network, make a connection or solicit services.\",\n    \"Sender Data\": {{\n      \"Sender name (text)\": \"Unknown Sender\",\n      \"Sender email domain (text)\": \"\",\n      \"Sender icon (jpg)\": \"\",\n      \"Time sent (mm/dd/yy 00:00)\": \"\"\n    }},\n    \"Length of summary blurb\": \"150 characters or less\",\n    \"Unique Data Required\": extract the following data from the mail\n\nonly return the available data , if not available to return \"\"\n  }}\n]"
    return prompt


def categorize_email(prompt):
    response = openai.ChatCompletion.create(
        model='gpt-3.5-turbo',
        messages=[
            {"role": "user", "content": prompt}],
        max_tokens=193,
        temperature=0,
    )
    if response.choices[0]["message"]["content"] == "Uncategorized":
        return "Miscellaneous"
    return response.choices[0]["message"]["content"]


def list_messages(service):
    try:
        result = []

        response = service.messages().list(userId="me", labelIds=["INBOX"]).execute()
        for msg in response["messages"]:
            message = get_messages(service, msg["threadId"])
            for headers in message["payload"]["headers"]:
                if headers["name"] == "From":
                    email_sender = headers["value"]
                elif headers["name"] == "Subject":
                    email_subject = headers["value"]
                elif headers["name"] == "Date":
                    date = headers["value"]
            # prompt = generate_prompt(message["snippet"])
            # category = categorize_email(prompt)
            res = gen(message["snippet"],[], email_sender,date,email_subject)
            res1= categorize_email(res)
            current_message = {
                "messages": {
                    "id": message["id"],
                    "threadId": message["threadId"],
                    "labelIds": message["labelIds"],
                    "message": message["snippet"],
                    "from": email_sender,
                    # "category": category,
                    "subject": email_subject,
                    "date_and_time": date,
                    "sender_mail": re.search(r'<(.*?)>', email_sender).group(1),
                    "p":res1
                },
                "attachments": [],
            }
            attachments = extract_attachments(service, message, msg["id"])
            current_message["attachments"] = attachments
            result.append(current_message)

        return {"messages": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing messages: {str(e)}")


@app.get("/authorize")
async def authorize():
    authorization_url = get_authorization_url()
    return JSONResponse(
        content={
            "authorization_url": authorization_url + "&redirect_uri=" + REDIRECT_URI
        }
    )


@app.get("/oauth-callback")
async def oauth_callback(code: str):
    try:
        credentials = authorize_and_get_credentials(code)
        gmail_service = get_gmail_service(credentials)
        result = list_messages(gmail_service)
        return JSONResponse(
            content={
                "data": result.get("messages"),
            }
        )

    except Exception as e:
        return JSONResponse(
            content={"error": f"Error during authorization: {str(e)}"}, status_code=500
        )
