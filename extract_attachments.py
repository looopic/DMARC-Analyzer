import os
from imbox import Imbox
import traceback
from dotenv import load_dotenv

def extract_attachments():

    host = os.getenv("EMAIL_HOST")
    username = os.getenv("EMAIL_ADDRESS")
    password = os.getenv("EMAIL_PASSWORD")
    download_folder = "./downloaded_mails"

    if not os.path.isdir(download_folder):
        os.makedirs(download_folder, exist_ok=True)

    mail = Imbox(host, username=username, password=password, ssl=True, ssl_context=None, starttls=False)
    #messages = mail.messages(sent_from=["noreply-dmarc-support@google.com", "dmarcreport@microsoft.com", "dmarc@infomaniak.com", "dmarc_reports@reports.emailsrvr.com"])
    messages = mail.messages(subject="report domain", unread=True)
    for (uid, message) in messages:
        mail.mark_seen(uid)

        for idx, attachment in enumerate(message.attachments):
            try:
                att_fn = attachment.get('filename')
                download_path = f"{download_folder}/{att_fn}"
                print(download_path)
                with open(download_path, "wb") as fp:
                    fp.write(attachment.get('content').read())
            except:
                print(traceback.print_exc())

    mail.logout()

if __name__ == "__main__":
    extract_attachments()