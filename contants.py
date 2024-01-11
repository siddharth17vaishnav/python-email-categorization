SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
TOKEN_FILE = 'token.json'
CLIENT_SECRETS_FILE = 'client_secret.json'
REDIRECT_URI = 'http://localhost:8000/oauth-callback/'
EMAIL_CATEGORIES = {
    "Account Verification": {
        "email_type": "updates",
        "request_data": {
            "sender_name": "",
            "sender_email_domain": "",
            "summary": "",
            "username_or_account_name": "",
            "activation_link": ""
        }
    },
    "Password Reset": {
        "email_type": "updates",
        "request_data": {
            "sender_name": "",
            "sender_email_domain": "",
            "summary": "",
            "username_or_account_name": "",
            "activation_link": ""
        },
    },
    "Product update/announcement": {
        "email_type": "security alerts",
        "request_data": {
            "sender_name": "",
            "sender_email_domain": "",
            "password_reset_link": ""
        }},
    "Billing/Transaction Notification": {
        "email_type": "notifications",
        "request_data": {
            "sender_name": "",
            "sender_email_domain": "",
            "name_forum_community": ""
        }},
    "Professional Networking": {
        "email_type": "promotional",
        "request_data": {
            "sender_name": "",
            "sender_email_domain": "",
            "name_forum_community": "",
            "link": ""
        }}
}
