# SlideSnap AI v8

Fixes the Deno installation error on Streamlit Cloud.

The previous version failed because Deno's official installer needs either `unzip` or `7z` to extract the downloaded archive. Streamlit Cloud now installs `unzip` through `packages.txt`.

Replace:
- app.py
- requirements.txt
and ADD:
- packages.txt

Then commit the changes and let Streamlit redeploy.
