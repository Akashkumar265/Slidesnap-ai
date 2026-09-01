# StudyAI Telegram Bot V1

YouTube educational lecture → transcript → AI study pack.

## Features
- Telegram `/start`
- Accept a YouTube URL
- Fetch available YouTube transcript
- Generate comprehensive notes
- Generate MCQs
- Generate practice questions
- Generate numericals when applicable
- Generate a Markdown study pack
- Basic rate limiting / input validation

## Important
This V1 uses the video's available transcript/captions. It does not download or reproduce the full video. If a transcript is unavailable, ask the user to provide a transcript or source material.

## Setup
1. Create a Telegram bot with BotFather and copy the token.
2. Obtain an OpenAI API key.
3. Copy `.env.example` to `.env`.
4. Fill in the secrets.
5. Install dependencies:
   `pip install -r requirements.txt`
6. Run:
   `python bot.py`

For production, keep secrets in your hosting provider's environment variables rather than committing `.env`.

## Suggested next upgrades
- PostgreSQL
- Credits/payment system
- PDF generation
- Persistent job queue for long lectures
- Admin dashboard
- Website

## Render V1.1
This version includes a FastAPI health server and binds to `0.0.0.0:$PORT`, making it suitable for Render Web Service deployment.
Start command:
`python bot.py`
Health endpoint:
`/health`
