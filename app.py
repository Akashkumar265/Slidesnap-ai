
import os, time, tempfile, shutil, subprocess
from pathlib import Path
from urllib.parse import urlencode
import requests
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

st.markdown('<div class="hero"><h1>🎓 SlideSnap AI</h1><p>YouTube → clean slide PDF</p></div>', unsafe_allow_html=True)

url=st.text_input("🔗 YouTube video link",placeholder="Paste YouTube URL here")
uploaded=st.file_uploader("Or upload a video you are authorized to process",type=["mp4","mov","mkv","webm"])

with st.expander("⚙️ Settings"):
    interval=st.slider("Sampling interval (seconds)",1,10,3)
    threshold=st.slider("Scene-change sensitivity",0.04,0.35,0.12,0.01)
    quality=st.select_slider("PDF quality",["Standard","High"],value="High")

BASE="https://gate.apiscrape.net:16262"

def creds():
    try:
        u=st.secrets["VIDEOSCALE_USERNAME"]
        p=st.secrets["VIDEOSCALE_PASSWORD"]
    except Exception:
        return None
    return (str(u),str(p))

def download_via_backend(video_url, workdir, progress, status):
    auth=creds()
    if not auth:
        raise RuntimeError(
            "VideoScale credentials missing. Add VIDEOSCALE_USERNAME and "
            "VIDEOSCALE_PASSWORD in Streamlit Secrets. See the setup instructions."
        )

    status.info("Backend se available formats check ho rahe hain…")
    r=requests.get(BASE+"/api/formats",
                   params={"video_url":video_url},
                   auth=auth,timeout=60)
    r.raise_for_status()
    data=r.json()

    formats=data.get("formats") or data.get("data") or []
    if isinstance(formats,dict):
        formats=formats.get("formats") or formats.get("data") or []

    # Prefer MP4 video formats, then highest resolution that is reasonably sized.
    video_formats=[]
    for f in formats:
        if not isinstance(f,dict): continue
        fid=f.get("format_id") or f.get("id")
        ext=str(f.get("ext") or "").lower()
        vcodec=str(f.get("vcodec") or "")
        height=f.get("height") or 0
        try: height=int(height)
        except: height=0
        if fid is not None and (vcodec not in ("none","") or height>0):
            video_formats.append((0 if ext=="mp4" else 1,-height,str(fid),f))

    if not video_formats:
        raise RuntimeError("Backend ne koi downloadable video format return nahi kiya.")
    video_formats.sort()
    chosen=video_formats[0][3]
    format_id=str(chosen.get("format_id") or chosen.get("id"))

    status.info(f"Video format selected: {format_id}. Download task start ho raha hai…")
    r=requests.post(BASE+"/api/download",
                    json={"url":video_url,"format_id":format_id},
                    auth=auth,timeout=60)
    r.raise_for_status()
    task=r.json()
    task_id=str(task.get("task_id") or task.get("id") or task.get("data",{}).get("task_id"))
    if task_id in ("None",""):
        raise RuntimeError(f"Unexpected backend response: {task}")

    for i in range(120):
        time.sleep(2)
        r=requests.get(BASE+f"/api/status/{task_id}",auth=auth,timeout=60)
        r.raise_for_status()
        s=r.json()
        raw=str(s).lower()
        if any(x in raw for x in ["failed","error","cancelled"]):
            raise RuntimeError(f"Backend download failed: {s}")
        if any(x in raw for x in ["completed","complete","finished","ready","success"]):
            break
        progress(min(0.40,0.10+i/120*0.30))
    else:
        raise RuntimeError("Backend download timed out.")

    r=requests.get(BASE+f"/api/download/{task_id}",auth=auth,timeout=60)
    r.raise_for_status()
    result=r.json()
    download_url=result.get("download_url") or result.get("url") or result.get("data",{}).get("download_url") or result.get("data",{}).get("url")
    if not download_url:
        raise RuntimeError(f"Backend did not return a download URL: {result}")

    status.info("Video file download ho raha hai…")
    target=Path(workdir)/"video.mp4"
    with requests.get(download_url,stream=True,timeout=120) as rr:
        rr.raise_for_status()
        with open(target,"wb") as f:
            for chunk in rr.iter_content(1024*1024):
                if chunk: f.write(chunk)
    progress(0.45)
    return target

def save_uploaded(file,workdir):
    ext=Path(file.name).suffix or ".mp4"
    target=Path(workdir)/("video"+ext)
    with open(target,"wb") as f:f.write(file.getbuffer())
    return target

def small_gray(frame):
    return cv2.cvtColor(cv2.resize(frame,(240,135)),cv2.COLOR_BGR2GRAY)

def detect(video_path,sample,thr,progress):
    cap=cv2.VideoCapture(str(video_path))
    if not cap.isOpened(): raise RuntimeError("Video open nahi ho saka.")
    fps=cap.get(cv2.CAP_PROP_FPS) or 30
    count=int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    duration=count/fps if count else 0
    prev=None; items=[]; t=0
    while t<=duration:
        cap.set(cv2.CAP_PROP_POS_MSEC,t*1000)
        ok,frame=cap.read()
        if ok:
            sig=small_gray(frame)
            diff=1.0 if prev is None else cv2.absdiff(sig,prev).mean()/255
            if prev is None or diff>=thr:
                items.append((t,frame.copy()))
            prev=sig
        t+=sample
        progress(min(.90,.45+t/max(duration,1)*.45))
    cap.release()
    return items

def dedupe(items):
    out=[]; prev=None
    for item in items:
        sig=small_gray(item[1])
        if prev is None or cv2.absdiff(sig,prev).mean()/255>=.035:
            out.append(item); prev=sig
    return out

def make_pdf(items,path,workdir,quality):
    c=canvas.Canvas(str(path),pagesize=A4); W,H=A4
    q=97 if quality=="High" else 88
    for i,(_,frame) in enumerate(items,1):
        img=Path(workdir)/f"p{i:04d}.jpg"
        cv2.imwrite(str(img),frame,[int(cv2.IMWRITE_JPEG_QUALITY),q])
        im=ImageReader(str(img)); iw,ih=im.getSize(); m=24
        scale=min((W-2*m)/iw,(H-2*m-22)/ih); w,h=iw*scale,ih*scale
        c.drawImage(im,(W-w)/2,(H-h)/2+4,width=w,height=h,preserveAspectRatio=True,mask="auto")
        c.setFont("Helvetica",8); c.drawCentredString(W/2,12,f"Slide {i}"); c.showPage()
    c.save()

if st.button("🚀 Generate Slide PDF",type="primary"):
    if not url.strip() and uploaded is None:
        st.warning("YouTube link paste karo ya video upload karo.")
    else:
        work=tempfile.mkdtemp(prefix="slidesnap_")
        try:
            prog=st.progress(0); status=st.empty()
            if uploaded is not None:
                status.info("Uploaded video save ho raha hai…")
                video=save_uploaded(uploaded,work); prog.progress(.15)
            else:
                video=download_via_backend(url.strip(),work,prog,status)
            status.info("Slides detect ho rahi hain…")
            items=dedupe(detect(video,interval,threshold,prog.progress))
            if not items: raise RuntimeError("Koi slide detect nahi hui. Sampling 2–3 sec try karo.")
            status.info(f"{len(items)} unique slide candidates mil gaye. PDF ban rahi hai…")
            pdf=Path(work)/"SlideSnap_Slides.pdf"; make_pdf(items,pdf,work,quality)
            prog.progress(1); status.success(f"✅ PDF ready — {len(items)} pages")
            with open(pdf,"rb") as f:
                st.download_button("📥 Download PDF",f,file_name="SlideSnap_Slides.pdf",mime="application/pdf")
            cols=st.columns(2)
            for i,(_,frame) in enumerate(items[:12]):
                cols[i%2].image(cv2.cvtColor(frame,cv2.COLOR_BGR2RGB),caption=f"Slide {i+1}",use_container_width=True)
        except Exception as e:
            st.error("❌ Processing failed")
            st.code(str(e))
        finally:
            shutil.rmtree(work,ignore_errors=True)

st.caption("Use only videos/content you are authorized to download and reproduce.")
