import os, subprocess, tempfile, shutil
from pathlib import Path
import cv2
import streamlit as st
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader

st.set_page_config(page_title="SlideSnap AI", page_icon="🎓", layout="centered")

st.markdown("""
<style>
.block-container {max-width: 680px; padding: 1rem .8rem 3rem;}
.hero {padding: 18px 16px; border-radius: 18px; background: linear-gradient(135deg,#eef2ff,#f8fafc);
       border:1px solid #e5e7eb; margin-bottom:16px;}
.hero h1 {margin:0; font-size:30px;}
.hero p {margin:6px 0 0; color:#475569;}
.stButton button, .stDownloadButton button {width:100%; border-radius:12px; min-height:48px; font-size:16px;}
.small {color:#64748b; font-size:13px;}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
<h1>🎓 SlideSnap AI</h1>
<p>YouTube educational video → sequence-wise Slide PDF</p>
</div>
""", unsafe_allow_html=True)

url = st.text_input("🔗 YouTube video link", placeholder="https://www.youtube.com/watch?v=...")

with st.expander("⚙️ Settings"):
    interval = st.slider("Frame sampling (seconds)", 1, 12, 4)
    threshold = st.slider("Change sensitivity", 0.05, 0.45, 0.16, 0.01)
    quality = st.select_slider("PDF image quality", options=["Standard","High"], value="High")

def download_video(url, outdir):
    out = str(Path(outdir)/"video.%(ext)s")
    subprocess.run(["yt-dlp","-f","mp4/best","--no-playlist","-o",out,url], check=True)
    vids=list(Path(outdir).glob("video.*"))
    if not vids: raise RuntimeError("Video download nahi hua.")
    return vids[0]

def sig(frame):
    small=cv2.resize(frame,(160,90))
    return cv2.cvtColor(small,cv2.COLOR_BGR2GRAY)

def detect(video, interval, threshold, outdir):
    cap=cv2.VideoCapture(str(video))
    fps=cap.get(cv2.CAP_PROP_FPS) or 30
    total=int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    duration=total/fps if total else 0
    prev=None; slides=[]; t=0
    while t <= duration:
        cap.set(cv2.CAP_PROP_POS_MSEC,t*1000)
        ok,frame=cap.read()
        if ok:
            s=sig(frame)
            changed=prev is None or cv2.absdiff(s,prev).mean()/255 >= threshold
            if changed:
                p=Path(outdir)/f"slide_{len(slides)+1:04d}.jpg"
                q=97 if quality=="High" else 88
                cv2.imwrite(str(p),frame,[int(cv2.IMWRITE_JPEG_QUALITY),q])
                slides.append(p); prev=s
        t += interval
    cap.release()
    return slides

def pdf_from_images(images, output):
    c=canvas.Canvas(str(output),pagesize=A4)
    W,H=A4
    for n,img in enumerate(images,1):
        im=ImageReader(str(img)); iw,ih=im.getSize()
        m=24; scale=min((W-2*m)/iw,(H-2*m-22)/ih)
        w,h=iw*scale,ih*scale
        c.drawImage(im,(W-w)/2,(H-h)/2+4,width=w,height=h,preserveAspectRatio=True,mask="auto")
        c.setFont("Helvetica",8); c.drawCentredString(W/2,12,f"Slide {n}")
        c.showPage()
    c.save()

if st.button("🚀 Generate Slide PDF", type="primary"):
    if not url.strip():
        st.warning("Pehle YouTube link paste karo.")
    else:
        work=tempfile.mkdtemp(prefix="slidesnap_")
        try:
            progress=st.progress(0)
            status=st.empty()
            status.info("Video fetch ho raha hai…")
            progress.progress(20)
            video=download_video(url.strip(),work)
            status.info("Slides detect ho rahi hain…")
            progress.progress(55)
            slides=detect(video,interval,threshold,work)
            if not slides: raise RuntimeError("Koi slide/frame detect nahi hua.")
            status.info(f"{len(slides)} slides mil gayi. PDF ban rahi hai…")
            progress.progress(80)
            out=Path(work)/"SlideSnap_Slides.pdf"
            pdf_from_images(slides,out)
            progress.progress(100)
            status.success(f"✅ Ready — {len(slides)} pages")
            with open(out,"rb") as f:
                st.download_button("📥 Download PDF",f,file_name="SlideSnap_Slides.pdf",mime="application/pdf")
            st.caption("Preview (first 12 detected frames)")
            cols=st.columns(2)
            for i,p in enumerate(slides[:12]):
                cols[i%2].image(str(p),caption=f"Slide {i+1}",use_container_width=True)
        except Exception as e:
            st.error(f"❌ {e}")
        finally:
            shutil.rmtree(work,ignore_errors=True)

st.markdown('<p class="small">Use only videos/content you are authorized to download and reproduce.</p>',unsafe_allow_html=True)
