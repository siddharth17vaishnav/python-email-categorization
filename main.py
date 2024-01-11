import re
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from utils.extraction import extract_text_from_pdf, extract_text_from_image, extract_links_from_html_part,extract_logo_from_html,get_html_content_from_message
from contants import CLIENT_SECRETS_FILE, SCOPES, TOKEN_FILE, REDIRECT_URI
from utils.open_ai import categorize_email

app = FastAPI()


def get_authorization_url():
    flow = Flow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
    authorization_url, _ = flow.authorization_url(prompt="none")
    return authorization_url


def authorize_and_get_credentials(code: str):
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE, SCOPES, redirect_uri=REDIRECT_URI
    )
    flow.fetch_token(code=code)
    credentials = flow.credentials
    with open(TOKEN_FILE, "w") as token_file:
        token_file.write(credentials.to_json())
    print("cred",credentials)
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
    if len(attachments) > 0:
        return attachments
    else:
        return None


def remove_special_characters(input_string):
    pattern = r'[^A-Za-z0-9\s]'
    result_string = re.sub(pattern, '', input_string)
    return result_string


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
            current_message = {
                "messages": {
                    "id": message["id"],
                    "threadId": message["threadId"],
                    "labelIds": message["labelIds"],
                    "message": message["snippet"],
                    "from": email_sender,
                    "subject": email_subject,
                    "date_and_time": date,
                    "sender_mail": re.search(r'<(.*?)>', email_sender).group(1)
                },
                "attachments": [],
            }
            if "parts" in message["payload"]:
                html_content = get_html_content_from_message(message)
                links_from_html = extract_links_from_html_part(html_content)
                logos_from_attachments = extract_logo_from_html(html_content)
                res1 = categorize_email(message["snippet"], [], email_sender, email_subject, links_from_html)
                current_message["messages"]["extracted_data"] = res1.get("result")
                current_message["messages"]["category"] = res1["category"]
                current_message["messages"]["extracted_data"]["links"] = links_from_html
                current_message["messages"]["extracted_data"]["sender_icon"] = logos_from_attachments
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
