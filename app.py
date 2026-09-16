import os
import uuid
import requests

from flask import Flask, request, send_from_directory

app = Flask(__name__)

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

BOT_TOKEN = os.environ["BOT_TOKEN"]
BASE_URL = os.environ["BASE_URL"].rstrip("/")


def telegram_api(method, data=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"
    response = requests.post(url, data=data, timeout=60)
    return response.json()


@app.route("/")
def home():
    return "Telegram File Downloader is running!"


@app.route("/download/<file_id>")
def download(file_id):
    for filename in os.listdir(DOWNLOAD_DIR):
        if filename.startswith(file_id + "_"):
            return send_from_directory(
                DOWNLOAD_DIR,
                filename,
                as_attachment=True
            )

    return "File not found", 404


@app.route("/telegram", methods=["POST"])
def telegram_webhook():
    update = request.get_json(silent=True)

    if not update:
        return "OK", 200

    message = update.get("message")

    if not message:
        return "OK", 200

    chat_id = message["chat"]["id"]

    # /start
    if message.get("text") == "/start":
        telegram_api(
            "sendMessage",
            {
                "chat_id": chat_id,
                "text": (
                    "👋 Send me a file and I'll give you "
                    "a browser download link."
                )
            }
        )
        return "OK", 200

    # Get file information from documents, photos, or videos
    document = message.get("document")
    photo = message.get("photo")
    video = message.get("video")

    if document:
        file_id_telegram = document["file_id"]
        filename = document.get("file_name", "file")

    elif photo:
        # Use the highest-quality version of the photo
        file_id_telegram = photo[-1]["file_id"]
        filename = f"photo_{uuid.uuid4().hex[:8]}.jpg"

    elif video:
        file_id_telegram = video["file_id"]
        filename = video.get("file_name", f"video_{uuid.uuid4().hex[:8]}.mp4")

    else:
        return "OK", 200

    safe_filename = os.path.basename(filename)

    # Get Telegram file information
    result = telegram_api(
        "getFile",
        {"file_id": file_id_telegram}
    )

    if not result.get("ok"):
        telegram_api(
            "sendMessage",
            {
                "chat_id": chat_id,
                "text": "❌ I couldn't access that file."
            }
        )
        return "OK", 200

    telegram_path = result["result"]["file_path"]

    # Download the file from Telegram
    download_url = (
        f"https://api.telegram.org/file/bot"
        f"{BOT_TOKEN}/{telegram_path}"
    )

    file_response = requests.get(
        download_url,
        timeout=120
    )

    if file_response.status_code != 200:
        telegram_api(
            "sendMessage",
            {
                "chat_id": chat_id,
                "text": "❌ I couldn't download that file."
            }
        )
        return "OK", 200

    unique_id = str(uuid.uuid4())[:8]

    saved_name = f"{unique_id}_{safe_filename}"
    filepath = os.path.join(DOWNLOAD_DIR, saved_name)

    with open(filepath, "wb") as file:
        file.write(file_response.content)

    download_link = f"{BASE_URL}/download/{unique_id}"

    telegram_api(
        "sendMessage",
        {
            "chat_id": chat_id,
            "text": (
                f"✅ File ready!\n\n"
                f"📁 {safe_filename}\n\n"
                f"⬇️ Download:\n{download_link}"
            )
        }
    )

    return "OK", 200


def setup_webhook():
    webhook_url = f"{BASE_URL}/telegram"

    result = telegram_api(
        "setWebhook",
        {
            "url": webhook_url
        }
    )

    print("Webhook setup:", result)


setup_webhook()
