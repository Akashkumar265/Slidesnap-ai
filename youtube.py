import re
from youtube_transcript_api import YouTubeTranscriptApi

def extract_video_id(url: str):
    patterns = [
        r"(?:v=)([A-Za-z0-9_-]{11})",
        r"(?:youtu\.be/)([A-Za-z0-9_-]{11})",
        r"(?:shorts/)([A-Za-z0-9_-]{11})",
        r"(?:embed/)([A-Za-z0-9_-]{11})",
    ]
    for p in patterns:
        m = re.search(p, url)
        if m:
            return m.group(1)
    return None

def get_transcript(video_id: str) -> str:
    api = YouTubeTranscriptApi()
    transcript_list = api.list(video_id)

    # Prefer manually created English/Hindi/Hinglish-ish tracks where available,
    # otherwise fall back to the first usable track.
    preferred = []
    fallback = []
    for t in transcript_list:
        fallback.append(t)
        lang = (getattr(t, "language_code", "") or "").lower()
        if lang.startswith(("en", "hi")):
            preferred.append(t)

    track = (preferred or fallback)[0] if (preferred or fallback) else None
    if track is None:
        return ""

    fetched = track.fetch()
    pieces = []
    for item in fetched:
        text = getattr(item, "text", None)
        if text:
            pieces.append(text)
    return " ".join(pieces)
