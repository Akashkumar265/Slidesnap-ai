import os
import re
import logging
from datetime import date
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ChatAction
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)

from services.youtube import extract_video_id, get_transcript
from services.ai import generate_study_pack
from services.store import can_generate, record_generation

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

WELCOME = (
    "🎓 *StudyAI V1*\\n\\n"
    "YouTube educational lecture ka link bhejo. "
    "Main available transcript se exam-oriented study material banaunga.\\n\\n"
    "📚 Complete Notes\\n"
    "❓ MCQs\\n"
    "✍️ Practice Questions\\n"
    "🧮 Numericals\\n"
    "🎯 Important Points\\n\\n"
    "⚠️ V1 captions/transcript par depend karta hai."
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(WELCOME, parse_mode="Markdown")

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "YouTube lecture ka educational URL bhejo.\n\n"
        "Example: https://www.youtube.com/watch?v=...\n\n"
        "Abhi V1 transcript available hone wale videos support karta hai."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
            "V1 mein payment system abhi enabled nahi hai."
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

        # Keep the request bounded for the first MVP.
        max_chars = int(os.getenv("MAX_TRANSCRIPT_CHARS", "60000"))
        if len(transcript) > max_chars:
            transcript = transcript[:max_chars] + "\n[Transcript truncated for V1]"

        await status.edit_text("🧠 AI study material generate kar raha hoon...")
        result = generate_study_pack(transcript)

        max_out = int(os.getenv("MAX_OUTPUT_CHARS", "30000"))
        if len(result) > max_out:
            result = result[:max_out] + "\n\n[Output truncated in Telegram V1]"

        record_generation(update.effective_user.id)
        await status.edit_text(
            "✅ *Study pack ready!*\n\n" + result,
            parse_mode="Markdown"
        )
    except Exception as e:
        log.exception("Processing failed")
        await status.edit_text(
            "❌ Processing mein problem aa gayi.\n"
            "Possible reason: transcript unavailable, API issue, ya temporary error.\n\n"
            f"Technical detail: `{type(e).__name__}`"
        )

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    log.info("StudyAI bot starting...")
    app.run_polling()

if __name__ == "__main__":
    main()
