import os
import re
import logging
import threading
from dotenv import load_dotenv
from fastapi import FastAPI
import uvicorn
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import Application, CommandHandler, MessageHandler, filters

from youtube import extract_video_id, get_transcript
from ai import generate_study_pack
from store import can_generate, record_generation

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN is missing in .env")

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
log = logging.getLogger("studyai")

URL_RE = re.compile(r"https?://(?:www\.)?(?:youtube\.com|youtu\.be)/\S+", re.I)

app = FastAPI(title="StudyAI Bot")

@app.get("/")
def root():
    return {"service": "StudyAI Telegram Bot", "status": "running"}

@app.get("/health")
def health():
    return {"status": "ok"}

WELCOME = (
    "🎓 *StudyAI V1.1*\\n\\n"
    "YouTube educational lecture ka link bhejo. "
    "Main available transcript se exam-oriented study material banaunga.\\n\\n"
    "📚 Complete Notes\\n"
    "❓ MCQs\\n"
    "✍️ Practice Questions\\n"
    "🧮 Numericals\\n"
    "🎯 Important Points\\n\\n"
    "⚠️ V1.1 captions/transcript par depend karta hai."
)

async def start(update: Update, context):
    await update.message.reply_text(WELCOME, parse_mode="Markdown")

async def help_cmd(update: Update, context):
    await update.message.reply_text(
        "YouTube lecture ka educational URL bhejo.\n\n"
        "Example: https://www.youtube.com/watch?v=...\n\n"
        "V1.1 transcript/captions available hone wale videos support karta hai."
    )

async def handle_message(update: Update, context):
    text = (update.message.text or "").strip()
    match = URL_RE.search(text)
    if not match:
        await update.message.reply_text(
            "YouTube lecture ka valid link bhejo. Example:\n"
            "https://www.youtube.com/watch?v=..."
        )
        return

    if not can_generate(update.effective_user.id):
        await update.message.reply_text(
            "⏳ Aaj ka free generation limit complete ho gaya. "
            "V1.1 mein payment system abhi enabled nahi hai."
        )
        return

    url = match.group(0)
    video_id = extract_video_id(url)
    if not video_id:
        await update.message.reply_text("YouTube URL samajh nahi aaya. Dobara bhejo.")
        return

    status = await update.message.reply_text("🔎 Lecture transcript check kar raha hoon...")
    try:
        await update.effective_chat.send_action(ChatAction.TYPING)
        transcript = await get_transcript(video_id)

        if not transcript:
            await status.edit_text(
                "❌ Is video ka usable transcript/captions nahi mila.\n\n"
                "Aap transcript ya lecture PDF upload kar sakte ho."
            )
            return

        max_chars = int(os.getenv("MAX_TRANSCRIPT_CHARS", "60000"))
        if len(transcript) > max_chars:
            transcript = transcript[:max_chars] + "\n[Transcript truncated for V1.1]"

        await status.edit_text("🧠 AI study material generate kar raha hoon...")
        result = generate_study_pack(transcript)

        # Telegram text messages have a finite size; split long output.
        record_generation(update.effective_user.id)
        chunks = [result[i:i+3800] for i in range(0, len(result), 3800)]
        await status.edit_text("✅ *Study pack ready!*", parse_mode="Markdown")
        for chunk in chunks[:10]:
            await update.message.reply_text(chunk)

        if len(chunks) > 10:
            await update.message.reply_text(
                "ℹ️ Output bahut bada tha; V1.1 mein remaining text omit kiya gaya hai. "
                "PDF output next version mein add karenge."
            )
    except Exception as e:
        log.exception("Processing failed")
        await status.edit_text(
            "❌ Processing mein problem aa gayi.\n"
            "Possible reason: transcript unavailable, API issue, ya temporary error.\n\n"
            f"Technical detail: `{type(e).__name__}`"
        )

async def telegram_runner():
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_cmd))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    log.info("Telegram polling started.")
    # Keep the Telegram application alive while FastAPI serves Render.
    await threading.Event().wait()

def run_telegram():
    import asyncio
    asyncio.run(telegram_runner())

if __name__ == "__main__":
    threading.Thread(target=run_telegram, daemon=True).start()
    port = int(os.getenv("PORT", "10000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
