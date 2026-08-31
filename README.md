# SlideSnap AI v10

This version avoids direct YouTube downloading from Streamlit Cloud.

YouTube mode uses VideoScale.sh as an external download/processing backend. Their current API uses HTTP Basic Auth and provides `/api/formats`, `/api/download`, `/api/status/:task_id`, and `/api/download/:task_id`. See their API docs.

Setup:
1. Create a VideoScale account and obtain API credentials.
2. In Streamlit Community Cloud -> app -> Settings/Secrets, add:
   VIDEOSCALE_USERNAME = "your_username"
   VIDEOSCALE_PASSWORD = "your_password"
3. Replace app.py and requirements.txt in GitHub and commit.
4. Streamlit will redeploy automatically.
5. Paste a YouTube URL.

The app also supports direct video upload, which does not need VideoScale credentials.
Use only content you are authorized to download/reproduce.
