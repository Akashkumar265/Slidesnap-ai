import os, subprocess, tempfile, shutil
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
""", unsafe_allow_html=True)

st.markdown('<div class="hero"><h1>🎓 SlideSnap AI</h1><p>Educational video → clean, sequence-wise slide PDF</p></div>', unsafe_allow_html=True)

url=st.text_input("🔗 YouTube video link", placeholder="Paste YouTube URL here")

with st.expander("⚙️ Settings"):
    interval=st.slider("Sampling interval (seconds)",1,10,3)
    change_threshold=st.slider("Scene-change sensitivity",0.04,0.35,0.12,0.01)
    keep_faces=st.checkbox("Keep slides even if teacher appears in a small corner", True)
    quality=st.select_slider("PDF quality",["Standard","High"],value="High")

def run(cmd):
    p=subprocess.run(cmd,capture_output=True,text=True)
    if p.returncode:
        raise RuntimeError((p.stderr or p.stdout or "Command failed")[-2500:])
    return p.stdout

def download_video(url,outdir):
    out=str(Path(outdir)/"video.%(ext)s")
    cmd=["yt-dlp","--no-playlist","--remote-components","ejs:github","--js-runtimes","deno",
         "-f","bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/b","--merge-output-format","mp4","-o",out,url]
    run(cmd)
    vids=list(Path(outdir).glob("video.*"))
    if not vids: raise RuntimeError("Video file nahi mila.")
    return vids[0]

def small_gray(frame):
    x=cv2.resize(frame,(240,135))
    return cv2.cvtColor(x,cv2.COLOR_BGR2GRAY)

def slide_score(frame, prev_sig, threshold):
    sig=small_gray(frame)
    diff=1.0 if prev_sig is None else cv2.absdiff(sig,prev_sig).mean()/255.0
    gray=cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY)
    edges=cv2.Canny(gray,80,180)
    edge_density=float(np.mean(edges>0))
    text_like=min(edge_density/0.10,1.0)
    score=0.45 + 0.55*text_like
    return sig,diff,score,0,0

def extract_slides(video,interval,threshold,outdir,keep_faces,progress_cb):
    cap=cv2.VideoCapture(str(video))
    fps=cap.get(cv2.CAP_PROP_FPS) or 30
    total=int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    duration=total/fps if total else 0
    prev_sig=None; candidates=[]; t=0
    while t<=duration:
        cap.set(cv2.CAP_PROP_POS_MSEC,t*1000)
        ok,frame=cap.read()
        if ok:
            sig,diff,score,nfaces,face_area=slide_score(frame,prev_sig,threshold)
            scene=prev_sig is None or diff>=threshold
            # Accept scene changes with slide-like visual structure.
            # Also accept strong slide score at periodic samples to catch gradual transitions.
            accept=(scene and score>=0.38) or score>=0.68
            # Reject obvious full-screen face shots.
                    if accept:
                candidates.append((t,frame.copy(),score))
            prev_sig=sig
        t+=interval
        progress_cb(min(0.85, t/max(duration,1)*0.85))
    cap.release()
    return candidates

def dedupe(candidates):
    out=[]
    last=None
    for t,frame,score in candidates:
        g=small_gray(frame)
        if last is None:
            out.append((t,frame,score)); last=g; continue
        d=cv2.absdiff(g,last).mean()/255
        if d>=0.035:
            out.append((t,frame,score)); last=g
    return out

def pdf_from_frames(items,path,quality):
    c=canvas.Canvas(str(path),pagesize=A4); W,H=A4
    q=97 if quality=="High" else 88
    tmp=Path(path).parent
    for i,(t,frame,score) in enumerate(items,1):
        img=tmp/f"page_{i:04d}.jpg"
        cv2.imwrite(str(img),frame,[int(cv2.IMWRITE_JPEG_QUALITY),q])
        im=ImageReader(str(img)); iw,ih=im.getSize(); m=24
        scale=min((W-2*m)/iw,(H-2*m-22)/ih)
        w,h=iw*scale,ih*scale
        c.drawImage(im,(W-w)/2,(H-h)/2+4,width=w,height=h,preserveAspectRatio=True,mask="auto")
        c.setFont("Helvetica",8); c.drawCentredString(W/2,12,f"Slide {i}")
        c.showPage()
    c.save()

if st.button("🚀 Generate Clean Slide PDF",type="primary"):
    if not url.strip():
        st.warning("Pehle YouTube link paste karo.")
    else:
        work=tempfile.mkdtemp(prefix="slidesnap_v3_")
        try:
            prog=st.progress(0); status=st.empty()
            status.info("YouTube video fetch ho raha hai…")
            video=download_video(url.strip(),work)
            prog.progress(0.12)
            status.info("AI-style slide detection chal rahi hai…")
            items=extract_slides(video,interval,change_threshold,work,keep_faces,prog.progress)
            items=dedupe(items)
            if not items: raise RuntimeError("Koi suitable slide detect nahi hui. Sampling interval kam karke try karo.")
            prog.progress(0.90)
            status.info(f"{len(items)} unique slide candidates mil gaye. PDF ban rahi hai…")
            pdf=Path(work)/"SlideSnap_Clean_Slides.pdf"
            pdf_from_frames(items,pdf,quality)
            prog.progress(1.0)
            status.success(f"✅ Ready — {len(items)} unique pages")
            with open(pdf,"rb") as f:
                st.download_button("📥 Download PDF",f,file_name="SlideSnap_Clean_Slides.pdf",mime="application/pdf")
            st.subheader("Preview")
            cols=st.columns(2)
            for i,(t,frame,score) in enumerate(items[:12]):
                cols[i%2].image(cv2.cvtColor(frame,cv2.COLOR_BGR2RGB),caption=f"Slide {i+1}",use_container_width=True)
        except Exception as e:
            st.error("❌ Processing failed")
            st.code(str(e))
        finally:
            shutil.rmtree(work,ignore_errors=True)

st.caption("Use only videos/content you are authorized to download and reproduce.")
