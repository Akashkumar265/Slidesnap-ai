import os
import re
import logging
import threading
import asyncio

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

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
if not TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN is missing")

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
    "🎓 *StudyAI V1.1*\n\n"
    "YouTube educational lecture ka link bhejo. "
    "Main available transcript se exam-oriented study material banaunga.\n\n"
    "📚 Complete Notes\n❓ MCQs\n✍️ Practice Questions\n"
    "🧮 Numericals\n🎯 Important Points\n\n"
    "⚠️ V1.1 captions/transcript par depend karta hai."
)

async def start(update: Update, context):
    if update.message:
        await update.message.reply_text(WELCOME, parse_mode="Markdown")

async def help_cmd(update: Update, context):
    if update.message:
        await update.message.reply_text(
            "YouTube lecture ka educational URL bhejo.\n\n"
            "Example: https://www.youtube.com/watch?v=...\n\n"
            "V1.1 transcript/captions available hone wale videos support karta hai."
        )

async def handle_message(update: Update, context):
    if not update.message:
        return

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

    video_id = extract_video_id(match.group(0))
    if not video_id:
        await update.message.reply_text("YouTube URL samajh nahi aaya. Dobara bhejo.")
        return

    status = await update.message.reply_text(
        "🔎 Lecture transcript check kar raha hoon..."
    )

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
        record_generation(update.effective_user.id)

        chunks = [result[i:i+3800] for i in range(0, len(result), 3800)]
        await status.edit_text("✅ *Study pack ready!*", parse_mode="Markdown")

        for chunk in chunks[:10]:
            await update.message.reply_text(chunk)

        if len(chunks) > 10:
            await update.message.reply_text(
                "ℹ️ Output bahut bada tha; V1.1 mein remaining text omit kiya gaya hai."
            )

    except Exception as e:
        log.exception("Processing failed")
        try:
            await status.edit_text(
                "❌ Processing mein problem aa gayi.\n"
                "Possible reason: transcript unavailable, API issue, ya temporary error.\n\n"
                f"Technical detail: `{type(e).__name__}`"
            )
        except Exception:
            log.exception("Could not send error message")

async def telegram_runner():
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_cmd))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )

    await application.initialize()

    # Clear any old Telegram webhook before polling.
    try:
        await application.bot.delete_webhook(drop_pending_updates=False)
        log.info("Telegram webhook cleared.")
    except Exception:
        log.exception("Could not clear Telegram webhook.")

    await application.start()
    await application.updater.start_polling(allowed_updates=Update.ALL_TYPES)
    log.info("Telegram polling started.")

    # Do NOT use threading.Event().wait() here: it blocks asyncio.
    await asyncio.Event().wait()

def run_telegram():
    try:
        asyncio.run(telegram_runner())
    except Exception:
        log.exception("Telegram runner crashed.")

if __name__ == "__main__":
    threading.Thread(
        target=run_telegram,
        daemon=True,
        name="telegram-polling",
    ).start()

    port = int(os.getenv("PORT", "10000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
