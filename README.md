# SlideSnap AI — Smart Slide Detection v3

This version adds a smarter visual filtering pipeline:
- current yt-dlp/EJS YouTube extraction setup
- scene-change detection
- text/edge-density heuristic
- face-size filtering for obvious talking-head frames
- duplicate-slide removal
- mobile-friendly Streamlit UI
- PDF export and preview

Important: this is a computer-vision heuristic, not a trained multimodal AI model. For higher accuracy, a future version can use a vision model/API to classify each candidate frame as slide/not-slide and crop the slide region.
