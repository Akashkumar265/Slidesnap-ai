# SlideSnap AI v6 — YouTube Cloud Fix

Fixes the current Streamlit Cloud YouTube extraction error by:
- using Node.js as the yt-dlp JavaScript runtime
- installing Node.js through Streamlit Cloud `packages.txt`
- avoiding separate video+audio merging, so ffmpeg is not required for the first test

Replace `app.py`, `requirements.txt`, and add `packages.txt` to the GitHub repository, then commit.

If a particular YouTube video still cannot be fetched, the error may be caused by that video's availability, authentication, region/age restrictions, or further YouTube-side changes.
