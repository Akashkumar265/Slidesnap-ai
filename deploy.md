# Deployment checklist

## Local
1. Install Python 3.11+.
2. Create virtual environment.
3. `pip install -r requirements.txt`
4. Copy `.env.example` to `.env`.
5. Add Telegram and OpenAI secrets.
6. `python bot.py`

## Production
Use a small Linux VPS or a Python-capable hosting service.

Set environment variables in the host dashboard:
- TELEGRAM_BOT_TOKEN
- OPENAI_API_KEY
- OPENAI_MODEL
- MAX_TRANSCRIPT_CHARS
- MAX_OUTPUT_CHARS
- FREE_GENERATIONS_PER_DAY

Do not commit `.env`.

## Important V1 limitations
- In-memory usage counter
- No payment gateway
- No persistent database
- Transcript/caption availability varies by video
- Long lectures are bounded by MAX_TRANSCRIPT_CHARS
- Telegram message size/output formatting should be hardened before a large launch
