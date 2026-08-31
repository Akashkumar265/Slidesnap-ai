# SlideSnap AI v9

Fixes the v8 format-selection problem:
- uses yt-dlp's standard `bestvideo*+bestaudio/best` fallback selector
- installs ffmpeg so separate video/audio streams can be merged
- keeps Deno + EJS support for current YouTube extraction
- shows a clearer message if YouTube exposes no downloadable video format

Replace `app.py`, `requirements.txt`, and `packages.txt` in GitHub, commit, and wait for Streamlit Cloud to redeploy.
