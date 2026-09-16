import os
import uuid
from flask import Flask, send_from_directory
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

app = Flask(__name__)

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


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


async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message

    document = message.document

    if not document:
        return

    file = await context.bot.get_file(document.file_id)

    file_id = str(uuid.uuid4())[:8]
    filename = document.file_name or "file"

    safe_filename = os.path.basename(filename)
    saved_name = f"{file_id}_{safe_filename}"
    filepath = os.path.join(DOWNLOAD_DIR, saved_name)

    await file.download_to_drive(filepath)

    # Replace this with your Render URL later
    base_url = os.environ.get("BASE_URL", "http://localhost:5000")

    link = f"{base_url}/download/{file_id}"

    await message.reply_text(
        f"✅ File ready!\n\n"
        f"📁 {safe_filename}\n\n"
        f"⬇️ Download:\n{link}"
    )


def run_bot():
    token = os.environ["BOT_TOKEN"]

    application = Application.builder().token(token).build()

    application.add_handler(
        MessageHandler(filters.Document.ALL, handle_file)
    )

    application.run_polling()


if __name__ == "__main__":
    import threading

    bot_thread = threading.Thread(target=run_bot)
    bot_thread.start()

    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000))
    )
