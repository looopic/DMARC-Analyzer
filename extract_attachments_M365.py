from flask import Flask, redirect, request, session, url_for
from msal import ConfidentialClientApplication
import requests
import os, dotenv

dotenv.load_dotenv()
app = Flask(__name__)

#Azure App Configuration
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
AUTHORITY = os.getenv("AUTHORITY")
REDIRECT_PATH = os.getenv("REDIRECT_PATH")
SCOPE = ['Mail.Read', 'User.Read']
ENDPOINT = os.getenv("ENDPOINT")
DOWNLOAD_FOLDER = "./downloaded_mails"

app_msal = ConfidentialClientApplication(
    CLIENT_ID, authority=AUTHORITY, client_credential=CLIENT_SECRET)

@app.route("/")
def index():
    if not session.get("user"):
        return redirect(url_for("login"))
    return f"Hallo, {session['user']['name']}! <a href='/download_attachments'>Anhänge herunterladen</a>"

@app.route("/login")
def login():
    auth_url = app_msal.get_authorization_request_url(SCOPE, redirect_uri=url_for("callback", _external=True))
    return redirect(auth_url)

@app.route(REDIRECT_PATH)
def callback():
    code = request.args.get("code")
    if code:
        result = app_msal.acquire_token_by_authorization_code(
            code, scopes=SCOPE, redirect_uri=url_for("callback", _external=True)
        )
        if "access_token" in result:
            user = result.get("id_token_claims")
            session["user"] = {"name": user["name"], "email": user["preferred_username"]}
            session["token"] = result["access_token"]
    return redirect(url_for("index"))

@app.route('/download_attachments')
def download_attachments():
    token = session.get("token")
    if not token:
        return redirect(url_for("login"))
    
    headers = {"Authorization": f"Bearer {token}"}
    params = {
        '$search': 'report domain',
        '$filter': 'isRead eq false'
    }

    response = requests.get(ENDPOINT, headers=headers, params=params)

    if response.status_code == 200:
        messages = response.json().get('value',[])
        if not os.path.exists(DOWNLOAD_FOLDER):
            os.makedirs(DOWNLOAD_FOLDER)

        for message in messages:
            message_id = message.get('id')
            subject = message.get('subject')
            print(f'Processing message: {subject}')

            attachment_endpoint = f'{ENDPOINT}/{message_id}/attachments'
            attachment_response = requests.get(attachment_endpoint, headers=headers)

            if attachment_response.status_code == 200:
                for attachment in attachment_response.json().get('value',[]):
                    file_name = attachment.get('name')
                    file_content = attachment.get('contentBytes')

                    file_path = os.path.join(DOWNLOAD_FOLDER, file_name)
                    with open(file_path, 'wb') as file:
                        file.write(file_content.encode('utf-8'))
                    print(f'Saved attachment: {file_name}')
        return 'Attachments downloaded successfully'
    else:
        return f'Fehler beim Abrufen der E-Mails: {response.status_code} {response.text}'


if __name__ == "__main__":
    app.run(debug=True)