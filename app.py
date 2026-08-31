import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import cv2
import numpy as np
import streamlit as st
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader

st.set_page_config(page_title="SlideSnap AI", page_icon="🎓", layout="centered")

st.markdown("""
<style>
.block-container{max-width:720px;padding:1rem .8rem 3rem}
.hero{padding:18px 16px;border-radius:18px;background:#f8fafc;border:1px solid #e5e7eb;margin-bottom:16px}
.hero h1{margin:0;font-size:29px}.hero p{margin:6px 0;color:#475569}
.stButton button,.stDownloadButton button{width:100%;min-height:50px;border-radius:12px;font-size:16px}
</style>
""",unsafe_allow_html=True)

st.markdown('<div class="hero"><h1>🎓 SlideSnap AI</h1><p>YouTube educational video → clean, sequence-wise slide PDF</p></div>',unsafe_allow_html=True)
url=st.text_input("🔗 YouTube video link",placeholder="Paste YouTube URL here")

with st.expander("⚙️ Settings"):
    interval=st.slider("Sampling interval (seconds)",1,10,3)
    threshold=st.slider("Scene-change sensitivity",0.04,0.35,0.12,0.01)
    quality=st.select_slider("PDF quality",["Standard","High"],value="High")

@st.cache_resource(show_spinner=False)
def ensure_deno():
    deno=os.path.expanduser("~/.deno/bin/deno")
    if os.path.exists(deno):
        return deno
    env=os.environ.copy()
    env["DENO_INSTALL"]=os.path.expanduser("~/.deno")
    p=subprocess.run(
        ["bash","-lc","curl -fsSL https://deno.land/install.sh | sh"],
        capture_output=True,text=True,env=env
    )
    if p.returncode!=0 or not os.path.exists(deno):
        raise RuntimeError((p.stderr or p.stdout or "Deno installation failed.")[-1800:])
    os.chmod(deno,0o755)
    return deno

def run_command(cmd):
    p=subprocess.run(cmd,capture_output=True,text=True)
    if p.returncode!=0:
        raise RuntimeError((p.stderr or p.stdout or "Command failed.")[-2500:])
    return p.stdout

def download_video(video_url,workdir):
    deno=ensure_deno()
    output=str(Path(workdir)/"video.%(ext)s")
    cmd=[
        "yt-dlp","--no-playlist",
        "--remote-components","ejs:github",
        "--js-runtimes",f"deno:{deno}",
        "-f","b[ext=mp4]/b",
        "-o",output,video_url
    ]
    run_command(cmd)
    videos=list(Path(workdir).glob("video.*"))
    if not videos:
        raise RuntimeError("Video file nahi mila.")
    return videos[0]

def small_gray(frame):
    return cv2.cvtColor(cv2.resize(frame,(240,135)),cv2.COLOR_BGR2GRAY)

def slide_score(frame):
    gray=cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY)
    edges=cv2.Canny(gray,80,180)
    return min(float(np.mean(edges>0))/0.10,1.0)

def detect_candidates(video_path,sample_seconds,change_threshold,progress):
    cap=cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError("Video open nahi ho saka.")
    fps=cap.get(cv2.CAP_PROP_FPS) or 30.0
    count=int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    duration=count/fps if count else 0
    previous=None
    candidates=[]
    t=0.0
    while t<=duration:
        cap.set(cv2.CAP_PROP_POS_MSEC,t*1000)
        ok,frame=cap.read()
        if ok:
            sig=small_gray(frame)
            diff=1.0 if previous is None else cv2.absdiff(sig,previous).mean()/255.0
            score=slide_score(frame)
            if previous is None or (diff>=change_threshold and score>=0.20):
                candidates.append((t,frame.copy(),score))
            previous=sig
        t+=sample_seconds
        progress(min(0.85,t/max(duration,1.0)*0.85))
    cap.release()
    return candidates

def remove_duplicates(items):
    unique=[]
    previous=None
    for item in items:
        sig=small_gray(item[1])
        if previous is None or cv2.absdiff(sig,previous).mean()/255.0>=0.035:
            unique.append(item)
            previous=sig
    return unique

def create_pdf(items,pdf_path,workdir,quality):
    pdf=canvas.Canvas(str(pdf_path),pagesize=A4)
    W,H=A4
    q=97 if quality=="High" else 88
    for number,(_,frame,_) in enumerate(items,1):
        image_path=Path(workdir)/f"page_{number:04d}.jpg"
        cv2.imwrite(str(image_path),frame,[int(cv2.IMWRITE_JPEG_QUALITY),q])
        image=ImageReader(str(image_path))
        iw,ih=image.getSize()
        margin=24
        scale=min((W-2*margin)/iw,(H-2*margin-22)/ih)
        w,h=iw*scale,ih*scale
        pdf.drawImage(image,(W-w)/2,(H-h)/2+4,width=w,height=h,preserveAspectRatio=True,mask="auto")
        pdf.setFont("Helvetica",8)
        pdf.drawCentredString(W/2,12,f"Slide {number}")
        pdf.showPage()
    pdf.save()

if st.button("🚀 Generate Clean Slide PDF",type="primary"):
    if not url.strip():
        st.warning("Pehle YouTube link paste karo.")
    else:
        workdir=tempfile.mkdtemp(prefix="slidesnap_")
        try:
            progress=st.progress(0)
            status=st.empty()
            status.info("YouTube video fetch ho raha hai…")
            video=download_video(url.strip(),workdir)
            progress.progress(15)
            status.info("Slides detect ho rahi hain…")
            candidates=detect_candidates(video,interval,threshold,progress.progress)
            slides=remove_duplicates(candidates)
            if not slides:
                raise RuntimeError("Koi slide detect nahi hui. Sampling interval 2–3 sec karke try karo.")
            progress.progress(90)
            status.info(f"{len(slides)} unique slides mil gayi. PDF ban rahi hai…")
            pdf_path=Path(workdir)/"SlideSnap_Slides.pdf"
            create_pdf(slides,pdf_path,workdir,quality)
            progress.progress(100)
            status.success(f"✅ PDF ready — {len(slides)} pages")
            with open(pdf_path,"rb") as f:
                st.download_button("📥 Download PDF",f,file_name="SlideSnap_Slides.pdf",mime="application/pdf")
            st.subheader("Preview")
            cols=st.columns(2)
            for i,(_,frame,_) in enumerate(slides[:12]):
                cols[i%2].image(cv2.cvtColor(frame,cv2.COLOR_BGR2RGB),caption=f"Slide {i+1}",use_container_width=True)
        except Exception as e:
            st.error("❌ Processing failed")
            st.code(str(e))
        finally:
            shutil.rmtree(workdir,ignore_errors=True)

st.caption("Use only videos/content you are authorized to download and reproduce.")
