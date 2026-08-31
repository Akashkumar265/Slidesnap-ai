# SlideSnap AI v7

This version fixes the YouTube runtime problem by installing Deno at runtime using Deno's official installer and explicitly passing the Deno executable to yt-dlp.

It also uses a fallback-friendly format selector (`b[ext=mp4]/b`) instead of requiring a specific pre-merged format.

Replace `app.py` and `requirements.txt` in GitHub, commit, and wait for Streamlit to redeploy.
