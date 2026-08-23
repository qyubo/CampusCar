import streamlit as st
from ultralytics import YOLO
from PIL import Image
import time

# ─── PAGE CONFIG ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="CrackSense AI — Road Damage Detection",
    page_icon="🛣️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── CUSTOM CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Sans:wght@300;400;500&display=swap');

*, *::before, *::after { box-sizing: border-box; }

html, body, .stApp {
    background-color: #080C14;
    font-family: 'DM Sans', sans-serif;
    color: #E8EDF5;
}

.stApp::before {
    content: '';
    position: fixed;
    inset: 0;
    background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)' opacity='0.04'/%3E%3C/svg%3E");
    pointer-events: none;
    z-index: 0;
    opacity: 0.6;
}

.hero-header {
    text-align: center;
    padding: 3rem 1rem 1.5rem;
    position: relative;
}

.hero-badge {
    display: inline-block;
    background: linear-gradient(135deg, #00BFA6 0%, #0091FF 100%);
    color: #080C14;
    font-family: 'Syne', sans-serif;
    font-weight: 700;
    font-size: 0.72rem;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    padding: 0.35rem 1rem;
    border-radius: 100px;
    margin-bottom: 1.2rem;
}

.hero-title {
    font-family: 'Syne', sans-serif;
    font-weight: 800;
    font-size: clamp(2.4rem, 5vw, 3.8rem);
    line-height: 1.08;
    letter-spacing: -0.02em;
    background: linear-gradient(135deg, #FFFFFF 30%, #00BFA6 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin: 0 0 0.8rem;
}

.hero-sub {
    font-size: 1.05rem;
    font-weight: 300;
    color: #7A8BA0;
    max-width: 540px;
    margin: 0 auto 2rem;
    line-height: 1.6;
}

.accent-divider {
    width: 80px;
    height: 3px;
    background: linear-gradient(90deg, #00BFA6, #0091FF);
    border-radius: 100px;
    margin: 0 auto 2.5rem;
}

.stat-row {
    display: flex;
    gap: 1rem;
    justify-content: center;
    flex-wrap: wrap;
    margin-bottom: 2.5rem;
}

.stat-card {
    background: linear-gradient(135deg, #111827 0%, #0D1520 100%);
    border: 1px solid rgba(0,191,166,0.15);
    border-radius: 14px;
    padding: 1rem 1.6rem;
    min-width: 140px;
    text-align: center;
}

.stat-value {
    font-family: 'Syne', sans-serif;
    font-size: 1.8rem;
    font-weight: 800;
    color: #00BFA6;
    line-height: 1;
}

.stat-label {
    font-size: 0.72rem;
    font-weight: 500;
    color: #4A5E72;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    margin-top: 0.3rem;
}

.upload-section {
    background: linear-gradient(135deg, #0D1520 0%, #111827 100%);
    border: 1.5px dashed rgba(0,191,166,0.35);
    border-radius: 20px;
    padding: 2rem 1.5rem;
    margin-bottom: 1.5rem;
    transition: border-color 0.3s ease;
}

.upload-section:hover {
    border-color: rgba(0,191,166,0.65);
}

[data-testid="stFileUploader"] {
    background: transparent !important;
}

[data-testid="stFileUploader"] > div {
    background: transparent !important;
    border: none !important;
}

.section-label {
    font-family: 'Syne', sans-serif;
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: #00BFA6;
    margin-bottom: 0.6rem;
}

.panel-title {
    font-family: 'Syne', sans-serif;
    font-size: 1.1rem;
    font-weight: 700;
    color: #E8EDF5;
    margin-bottom: 1rem;
}

.result-panel {
    background: linear-gradient(160deg, #0D1520 0%, #0A1628 100%);
    border: 1px solid rgba(0,145,255,0.2);
    border-radius: 20px;
    padding: 1.5rem;
}

.detection-success {
    display: flex;
    align-items: center;
    gap: 0.7rem;
    background: linear-gradient(135deg, rgba(0,191,166,0.12), rgba(0,191,166,0.05));
    border: 1px solid rgba(0,191,166,0.3);
    border-radius: 12px;
    padding: 0.9rem 1.2rem;
    margin-top: 1rem;
}

.detection-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background: #00BFA6;
    box-shadow: 0 0 8px #00BFA6;
    flex-shrink: 0;
    animation: pulse 2s infinite;
}

@keyframes pulse {
    0%, 100% { box-shadow: 0 0 6px #00BFA6; }
    50% { box-shadow: 0 0 16px #00BFA6; }
}

.detection-text {
    font-size: 0.92rem;
    color: #AECFCC;
    font-weight: 500;
}

.info-card {
    background: linear-gradient(135deg, #0D1520, #111827);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 14px;
    padding: 1.1rem 1.3rem;
    margin-bottom: 0.8rem;
}

.info-card-title {
    font-family: 'Syne', sans-serif;
    font-size: 0.78rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #00BFA6;
    margin-bottom: 0.5rem;
}

.info-card-body {
    font-size: 0.88rem;
    color: #7A8BA0;
    line-height: 1.6;
}

[data-testid="stSidebar"] {
    background: #080C14 !important;
    border-right: 1px solid rgba(0,191,166,0.12) !important;
}

[data-testid="stSidebar"] .stMarkdown p {
    font-size: 0.88rem;
    color: #7A8BA0;
    line-height: 1.65;
}

.sidebar-logo {
    font-family: 'Syne', sans-serif;
    font-size: 1.3rem;
    font-weight: 800;
    letter-spacing: -0.01em;
    color: #E8EDF5;
    padding: 0.5rem 0 1.5rem;
}

.sidebar-logo span { color: #00BFA6; }

.sidebar-chip {
    display: inline-block;
    background: rgba(0,191,166,0.1);
    border: 1px solid rgba(0,191,166,0.25);
    color: #00BFA6;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    padding: 0.25rem 0.7rem;
    border-radius: 100px;
    margin: 0.2rem 0.15rem;
}

hr {
    border: none;
    border-top: 1px solid rgba(255,255,255,0.06);
    margin: 1.5rem 0;
}

h1, h2, h3, h4 { font-family: 'Syne', sans-serif !important; }

.stSpinner > div { border-top-color: #00BFA6 !important; }

[data-testid="stImage"] img { border-radius: 12px; }
</style>
""", unsafe_allow_html=True)


# ─── SIDEBAR ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="sidebar-logo">Crack<span>Sense</span> AI</div>', unsafe_allow_html=True)

    st.markdown("""
    <div class="info-card">
        <div class="info-card-title">🔍 Detection Classes</div>
        <div class="info-card-body">
            • <b style="color:#E8EDF5">Cracks</b> — surface &amp; structural<br>
            • <b style="color:#E8EDF5">Potholes</b> — deep depressions<br>
            • <b style="color:#E8EDF5">Road Damage</b> — general wear
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="info-card">
        <div class="info-card-title">⚙️ Technology Stack</div>
        <div class="info-card-body">
            <span class="sidebar-chip">YOLOv11</span>
            <span class="sidebar-chip">Streamlit</span>
            <span class="sidebar-chip">Python</span>
            <span class="sidebar-chip">OpenCV</span>
            <span class="sidebar-chip">PyTorch</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="info-card">
        <div class="info-card-title">📌 How to Use</div>
        <div class="info-card-body">
            1. Upload a road image (JPG/PNG)<br>
            2. Wait for AI analysis<br>
            3. View annotated detections<br>
            4. Review confidence scores
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("""
    <div style="font-size:0.72rem; color:#3A4E62; text-align:center; padding-bottom:0.5rem;">
        Final Year Project · Computer Vision<br>
        Powered by YOLOv11 · 2025
    </div>
    """, unsafe_allow_html=True)


# ─── HERO HEADER ────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero-header">
    <div class="hero-badge">🛣️ &nbsp;Final Year Project — AI &amp; Computer Vision</div>
    <h1 class="hero-title">Road Damage<br>Detection System</h1>
    <p class="hero-sub">
        Powered by YOLOv11 — upload any road image to instantly
        identify cracks, potholes, and surface damage with precision.
    </p>
    <div class="accent-divider"></div>
</div>

<div class="stat-row">
    <div class="stat-card">
        <div class="stat-value">YOLOv11</div>
        <div class="stat-label">AI Model</div>
    </div>
    <div class="stat-card">
        <div class="stat-value">3</div>
        <div class="stat-label">Damage Classes</div>
    </div>
    <div class="stat-card">
        <div class="stat-value">Real‑Time</div>
        <div class="stat-label">Inference</div>
    </div>
    <div class="stat-card">
        <div class="stat-value">High</div>
        <div class="stat-label">Accuracy</div>
    </div>
</div>
""", unsafe_allow_html=True)


# ─── LOAD MODEL ─────────────────────────────────────────────────────────────────
@st.cache_resource(show_spinner=False)
def load_model():
    return YOLO("best.pt")

with st.spinner("Loading YOLOv11 model..."):
    model = load_model()


# ─── UPLOAD ZONE ────────────────────────────────────────────────────────────────
st.markdown('<p class="section-label">📂 Upload Image</p>', unsafe_allow_html=True)
st.markdown('<div class="upload-section">', unsafe_allow_html=True)

uploaded_file = st.file_uploader(
    "Drag & drop a road image or click to browse",
    type=["jpg", "png", "jpeg"],
    label_visibility="visible",
)

st.markdown('</div>', unsafe_allow_html=True)


# ─── DETECTION ──────────────────────────────────────────────────────────────────
if uploaded_file is not None:
    image = Image.open(uploaded_file)

    col1, col2 = st.columns(2, gap="large")

    with col1:
        st.markdown('<p class="section-label">🖼️ Original Image</p>', unsafe_allow_html=True)
        st.image(image, use_container_width=True)

    with st.spinner("🔍 Analyzing pavement condition with YOLOv11..."):
        start = time.time()
        results = model(image)
        elapsed = time.time() - start
        result_img = results[0].plot()

    detections = results[0].boxes
    num_detections = len(detections) if detections is not None else 0

    with col2:
        st.markdown('<p class="section-label">🎯 Detection Result</p>', unsafe_allow_html=True)
        st.image(result_img, use_container_width=True)

    # ── Result Summary ──────────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    r1, r2, r3 = st.columns(3, gap="medium")

    with r1:
        st.markdown(f"""
        <div class="info-card" style="text-align:center;">
            <div class="info-card-title">Objects Detected</div>
            <div style="font-family:'Syne',sans-serif; font-size:2.2rem; font-weight:800;
                        color:#00BFA6; line-height:1;">{num_detections}</div>
        </div>
        """, unsafe_allow_html=True)

    with r2:
        st.markdown(f"""
        <div class="info-card" style="text-align:center;">
            <div class="info-card-title">Inference Time</div>
            <div style="font-family:'Syne',sans-serif; font-size:2.2rem; font-weight:800;
                        color:#0091FF; line-height:1;">{elapsed:.2f}s</div>
        </div>
        """, unsafe_allow_html=True)

    with r3:
        status_color = "#00BFA6" if num_detections == 0 else "#FF6B4A"
        status_text = "No Damage Found" if num_detections == 0 else "Damage Detected"
        st.markdown(f"""
        <div class="info-card" style="text-align:center;">
            <div class="info-card-title">Road Status</div>
            <div style="font-family:'Syne',sans-serif; font-size:1.3rem; font-weight:800;
                        color:{status_color}; line-height:1.2; margin-top:0.3rem;">{status_text}</div>
        </div>
        """, unsafe_allow_html=True)

    # ── Per-detection breakdown ─────────────────────────────────────────────
    if num_detections > 0 and detections.conf is not None:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<p class="section-label">📊 Detection Breakdown</p>', unsafe_allow_html=True)

        names = results[0].names
        for i, (conf, cls) in enumerate(zip(detections.conf, detections.cls)):
            conf_val = float(conf)
            class_name = names[int(cls)]
            bar_width = int(conf_val * 100)
            st.markdown(f"""
            <div style="background:linear-gradient(135deg,#0D1520,#111827);
                        border:1px solid rgba(255,255,255,0.06);
                        border-radius:12px; padding:0.9rem 1.2rem; margin-bottom:0.6rem;">
                <div style="display:flex; justify-content:space-between; margin-bottom:0.5rem;">
                    <span style="font-family:'Syne',sans-serif; font-size:0.9rem;
                                 font-weight:700; color:#E8EDF5;">#{i+1} — {class_name}</span>
                    <span style="font-family:'Syne',sans-serif; font-size:0.9rem;
                                 font-weight:700; color:#00BFA6;">{conf_val:.1%}</span>
                </div>
                <div style="background:rgba(255,255,255,0.06); border-radius:100px; height:6px;">
                    <div style="width:{bar_width}%;height:6px;border-radius:100px;
                                background:linear-gradient(90deg,#00BFA6,#0091FF);"></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("""
    <div class="detection-success">
        <div class="detection-dot"></div>
        <div class="detection-text">
            <b>Analysis complete</b> — YOLOv11 model processed the image successfully.
        </div>
    </div>
    """, unsafe_allow_html=True)

else:
    st.markdown("""
    <div style="text-align:center; padding:3rem 1rem;
                background:linear-gradient(135deg,#0D1520,#111827);
                border:1px solid rgba(255,255,255,0.05); border-radius:20px; margin-top:1rem;">
        <div style="font-size:3rem; margin-bottom:1rem;">🛣️</div>
        <p style="font-family:'Syne',sans-serif; font-size:1.1rem; font-weight:700;
                  color:#E8EDF5; margin-bottom:0.4rem;">No Image Uploaded Yet</p>
        <p style="font-size:0.88rem; color:#4A5E72;">
            Upload a road or pavement image above to begin AI-powered damage detection.
        </p>
    </div>
    """, unsafe_allow_html=True)
