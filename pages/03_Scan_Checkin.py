# pages/03_Scan_Checkin.py
import os
import base64
from datetime import datetime
import streamlit as st

# ---------------- Page config ----------------
st.set_page_config(page_title="Scan & Check-in", layout="centered", initial_sidebar_state="collapsed")


# ---------------- Constants ----------------
LOGO_PATH = "logo.png"
ACCENT = "#77B255"   # keep your current green
LOGO_HEIGHT = 36
BARCODE_PATH = "assets/barcode.jpg"  # <-- your image lives here

# ---------------- Helpers ----------------
def img_to_data_uri(path: str) -> str:
    """Return data URI for an image file; '' if not found."""
    try:
        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
        ext = path.split(".")[-1].lower()
        mime = "image/png" if ext == "png" else "image/jpeg"
        return f"data:{mime};base64,{b64}"
    except Exception:
        return ""

barcode_src = img_to_data_uri(BARCODE_PATH)
barcode_html = (
    f'<img src="{barcode_src}" style="max-height:140px; max-width:100%; display:block; margin:0 auto;" />'
    if barcode_src
    else '<div style="height:120px; display:flex; align-items:center; justify-content:center; border:1px dashed #e8e5da; border-radius:8px; color:#999;">Barcode / QR</div>'
)

def render_header(active_page: str = "scan"):
    st.markdown(f"""
    <style>
      .block-container {{ padding-top: 0.75rem; }}
      .ff-header {{
        background:{ACCENT};
        color:#fff;
        padding:12px 16px;
        border-radius: 10px;
        margin-bottom: 14px;
        display:flex;
        align-items:center;
        justify-content:space-between;
        gap:16px;
      }}
      .ff-left {{ display:flex; align-items:center; gap:12px; }}
      .ff-logo {{ display:flex; align-items:center; justify-content:center; height:{LOGO_HEIGHT}px; width:auto; padding:4px 6px; background:rgba(255,255,255,0.10); border-radius:10px; border:1px solid rgba(255,255,255,0.20); }}
      .ff-title {{ margin:0; font-size:20px; font-weight:700; line-height:1.1; }}
      .ff-sub   {{ margin:0; opacity:.95; font-size:12px; }}
    </style>
    """, unsafe_allow_html=True)

    left_html = ""
    if os.path.exists(LOGO_PATH):
        left_html += f'<div class="ff-logo"><img src="{LOGO_PATH}" height="{LOGO_HEIGHT}" style="display:block;"></div>'

    left_html += """
      <div>
        <p class="ff-title">Fantasy Fan</p>
        <p class="ff-sub">Scan & check-in</p>
      </div>
    """

    st.markdown(
        f"""
        <div class="ff-header">
          <div class="ff-left">{left_html}</div>
          <div style="color:white; font-weight:600;">🪪 Scan & Check-in</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ---------------- Render header ----------------
render_header("scan")

# ---------------- Static "account" row ----------------
top_cols = st.columns([1, 6, 1])
with top_cols[0]:
    if os.path.exists("logo.png"):
        st.image("logo.png", width=44)
with top_cols[1]:
    st.markdown("<h2 style='margin:0'>Dillon S.</h2>", unsafe_allow_html=True)
with top_cols[2]:
    st.markdown("<div style='text-align:right; font-weight:700;'>66★</div>", unsafe_allow_html=True)

st.write("")  # spacing

# ---------------- Tabs / segmented control ----------------
seg = st.columns([1, 1])
with seg[0]:
    st.button("Scan & check-in", disabled=True)  # visual only (active)
with seg[1]:
    scan_only_toggle = st.checkbox("Scan only", value=False, help="Toggles a scan-only flow (no points)")

st.divider()

# ---------------- Session state defaults ----------------
if "scan_state" not in st.session_state:
    st.session_state["scan_state"] = "ready"   # "ready" | "scanned"
if "last_scan_time" not in st.session_state:
    st.session_state["last_scan_time"] = None
if "scan_mode" not in st.session_state:
    st.session_state["scan_mode"] = "points"   # or "scan_only"

def fmt_ts(ts: datetime):
    return ts.strftime("%b %d, %Y • %I:%M %p")

# ---------------- Pass Card (visual) ----------------
card_left, card_right = st.columns([1, 1.5])

with card_left:
    st.markdown(
        f"""
        <div style="
            border-radius:20px;
            padding:0;
            box-shadow: 0 6px 18px rgba(0,0,0,0.08);
            border:1px solid #e8e5da;
            background: #fff;
            overflow:hidden;
        ">
          <div style="background:{ACCENT}; padding:14px 18px; color: white;">
            <div style="font-size:16px; font-weight:700;">Ready to Check-in</div>
            <div style="opacity:.95; font-size:12px;">{"Earns 2 ✦ per check-in" if not scan_only_toggle else "Scan only"}</div>
          </div>
          <div style="padding:18px; text-align:center;">
            {barcode_html}
            <div style="margin-top:12px; font-weight:700;">ID • 6205 6726 9176 0250</div>
            <div style="margin-top:12px; display:flex; gap:12px; justify-content:center;">
              <div style="padding:8px 12px; border-radius:10px; border:1px solid #eee;">⚙️ Manage</div>
              <div style="padding:8px 12px; border-radius:10px; border:1px solid #eee;">➕ Add to Wallet</div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with card_right:
    st.markdown("### Quick actions")
    st.write("Use this prototype to simulate scanning behavior. No backend calls are made — just visual feedback.")

    if st.session_state["scan_state"] == "scanned":
        last = st.session_state["last_scan_time"]
        st.success("Checked in! ✅")
        st.write(f"**{fmt_ts(last)}**")
        if st.button("Undo", key="undo_btn"):
            st.session_state["scan_state"] = "ready"
            st.session_state["last_scan_time"] = None
            st.rerun()

    if st.session_state["scan_state"] == "ready":
        if st.button("Scan now", use_container_width=True, key="scan_now"):
            st.session_state["scan_mode"] = "scan_only" if scan_only_toggle else "points"
            st.session_state["scan_state"] = "scanned"
            st.session_state["last_scan_time"] = datetime.now()
            st.balloons()
            st.rerun()
    else:
        st.markdown("Waiting for next scan...")

# ---------------- Recent static chips ----------------
st.divider()
st.markdown("#### Recent check-ins (preview)")
chip_cols = st.columns(3)
fake_history = [
    ("Yankees vs Angels", "2025-07-10"),
    ("Panthers vs Jets", "2025-06-22"),
    ("Knicks vs Bucks", "2025-05-10"),
]
for c, (lbl, dt) in zip(chip_cols, fake_history):
    if c.button(f"{lbl}\n{dt}"):
        st.info(f"{lbl} — {dt}\nVenue details (static)")

# ---------------- Bottom nav (static visual) ----------------
st.divider()
nav_c1, nav_c2, nav_c3, nav_c4 = st.columns([1,1,1,1])
with nav_c1:
    st.page_link("app.py", label="Home")
with nav_c2:
    st.markdown("<div style='font-weight:700; text-align:center;'>🔲<br/>Scan</div>", unsafe_allow_html=True)
with nav_c3:
    st.page_link("pages/02_Team_Leaderboard.py", label="Leaderboard")
with nav_c4:
    if st.button("Offers"):
        st.info("Offers page (static, coming soon)")

# ---------------- Footer small copy ----------------
st.markdown("<div style='margin-top:12px; color:#666; font-size:12px;'>This is a prototype pass for demonstrating the scan/check-in flow. No personal data is sent anywhere.</div>", unsafe_allow_html=True)

