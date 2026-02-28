import streamlit as st
import os, json, hashlib, datetime, urllib.parse, re, base64, io
import requests
from groq import Groq
from dotenv import load_dotenv
from gtts import gTTS

load_dotenv()

# ─── STORAGE ──────────────────────────────────────────────────────────────────
USER_DB   = "users.json"
MEMORY_DB = "memory.json"

def load_users():
    if os.path.exists(USER_DB):
        try:
            with open(USER_DB, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            pass # Return empty if corrupted or empty
    return {}

def save_users(u):
    with open(USER_DB, "w") as f:
        json.dump(u, f)

def hash_pw(p):
    return hashlib.sha256(p.encode()).hexdigest()

def load_memory(email):
    if os.path.exists(MEMORY_DB):
        try:
            with open(MEMORY_DB, "r") as f:
                return json.load(f).get(email, [])
        except json.JSONDecodeError:
            pass # Return empty list if corrupted or empty
    return []

def save_memory(email, msgs):
    data = {}
    if os.path.exists(MEMORY_DB):
        try:
            with open(MEMORY_DB, "r") as f:
                data = json.load(f)
        except json.JSONDecodeError:
            pass
    data[email] = msgs[-80:]
    with open(MEMORY_DB, "w") as f:
        json.dump(data, f)

# ─── PAGE CONFIG ──────────────────────────────────────────────────────────────
st.set_page_config(page_title="IRIS AI", page_icon="◈", layout="wide",
                   initial_sidebar_state="expanded")

# ─── SESSION STATE ────────────────────────────────────────────────────────────
for k, v in {
    "authenticated": False, "user_email": None, "messages": [],
    "theme": "black", "tts_lang": "en", "active_module": "chat",
    "tts_enabled": True, "chat_media": {}
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ─── THEMES ───────────────────────────────────────────────────────────────────
THEMES = {
    "black": dict(bg="#050505", bg2="#0c0c0c", bg3="#111", border="#1c1c1c",
                  accent="#00ffa0", accent2="#00b4ff", text="#c8c8c8",
                  text_dim="#555", text_dimmer="#252525", title="#fff",
                  glow="rgba(0,255,160,0.12)", ub="rgba(0,255,160,0.04)",
                  ubr="rgba(0,255,160,0.10)", ab="rgba(0,180,255,0.02)",
                  abr="rgba(0,180,255,0.08)", sb="rgba(4,4,4,0.97)", name="BLACK"),
    "pink":  dict(bg="#080408", bg2="#100810", bg3="#180c18", border="#2a102a",
                  accent="#ff6eb4", accent2="#c084fc", text="#e8c8e8",
                  text_dim="#664466", text_dimmer="#3a1a3a", title="#ffddf5",
                  glow="rgba(255,110,180,0.12)", ub="rgba(255,110,180,0.04)",
                  ubr="rgba(255,110,180,0.12)", ab="rgba(192,132,252,0.02)",
                  abr="rgba(192,132,252,0.09)", sb="rgba(8,4,8,0.97)", name="PINK"),
    "blue":  dict(bg="#030508", bg2="#060a12", bg3="#0a1020", border="#0e1e38",
                  accent="#38bdf8", accent2="#818cf8", text="#bdd8f0",
                  text_dim="#2a4a6a", text_dimmer="#0e1e2e", title="#e0f0ff",
                  glow="rgba(56,189,248,0.12)", ub="rgba(56,189,248,0.04)",
                  ubr="rgba(56,189,248,0.12)", ab="rgba(129,140,248,0.02)",
                  abr="rgba(129,140,248,0.09)", sb="rgba(3,5,10,0.97)", name="BLUE"),
    "green": dict(bg="#030804", bg2="#060f08", bg3="#0a180c", border="#0e2a12",
                  accent="#4ade80", accent2="#a3e635", text="#b8e8c0",
                  text_dim="#1a4a24", text_dimmer="#0a1e0e", title="#d4f4dc",
                  glow="rgba(74,222,128,0.12)", ub="rgba(74,222,128,0.04)",
                  ubr="rgba(74,222,128,0.12)", ab="rgba(163,230,53,0.02)",
                  abr="rgba(163,230,53,0.08)", sb="rgba(3,8,4,0.97)", name="GREEN"),
    "white": dict(bg="#f5f5f0", bg2="#eeeeea", bg3="#e5e5e0", border="#d0d0cc",
                  accent="#1a1a2e", accent2="#555577", text="#2a2a2a",
                  text_dim="#888880", text_dimmer="#bbbbbb", title="#0a0a0a",
                  glow="rgba(26,26,46,0.08)", ub="rgba(26,26,46,0.05)",
                  ubr="rgba(26,26,46,0.15)", ab="rgba(85,85,119,0.03)",
                  abr="rgba(85,85,119,0.11)", sb="rgba(245,245,240,0.98)", name="WHITE"),
}
T = THEMES[st.session_state.theme]

# ─── GTTS — library-based TTS ─────────────────────────────────────────────────
def speak(text: str, lang: str = "en"):
    """gTTS generates MP3, embedded as autoplay <audio> in browser."""
    if not text or not st.session_state.tts_enabled:
        return
    try:
        clean = re.sub(r'[*_`#>\[\]|●▶◈◼🌤🔍🖼▶️💧💨👁📊☀️🌅🌇🧮💊📖🌐]', '', text)
        clean = re.sub(r'\s+', ' ', clean).strip()[:700]
        if not clean:
            return
        buf = io.BytesIO()
        gTTS(text=clean, lang=lang, slow=False).write_to_fp(buf)
        buf.seek(0)
        b64 = base64.b64encode(buf.read()).decode()
        st.markdown(
            f'<audio autoplay controls style="width:100%;margin-top:8px;border-radius:8px;'
            f'accent-color:{T["accent"]}">'
            f'<source src="data:audio/mp3;base64,{b64}" type="audio/mp3">'
            f'</audio>',
            unsafe_allow_html=True
        )
    except Exception as e:
        st.caption(f"TTS: {e}")

# ─── CSS ──────────────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Figtree:wght@300;400;500;600&family=Syne:wght@700;800&display=swap');

*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0;}}
html,body,.stApp{{background:{T['bg']} !important;color:{T['text']};font-family:'Figtree',sans-serif;}}
[data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stAppDeployButton"], #MainMenu, footer {{display:none !important;}}
.block-container {{padding:0 !important;max-width:100% !important;}}
[data-testid="stBottomBlockContainer"] {{background: transparent !important;}}

/* BG atmosphere */
.stApp::before{{content:'';position:fixed;inset:0;
  background:radial-gradient(ellipse 70% 50% at 15% -10%,{T['ub']} 0%,transparent 55%),
             radial-gradient(ellipse 50% 40% at 85% 110%,{T['ab']} 0%,transparent 55%),{T['bg']};
  z-index:-2;pointer-events:none;}}
.stApp::after{{content:'';position:fixed;inset:0;
  background:repeating-linear-gradient(0deg,transparent,transparent 2px,rgba(0,0,0,0.01) 2px,rgba(0,0,0,0.01) 4px);
  z-index:9999;pointer-events:none;}}

/* ───────── SIDEBAR CONTAINER ───────── */
section[data-testid="stSidebar"]{{
    background:linear-gradient(180deg,{T['sb']} 0%,{T['bg2']} 100%) !important;
    border-right:1px solid {T['border']} !important;
    width:280px !important;
    backdrop-filter:blur(14px);
    box-shadow:8px 0 40px -20px {T['glow']};
}}

section[data-testid="stSidebar"]>div{{
    padding:0 !important;
    overflow-y:auto;
    overflow-x:hidden;
}}

section[data-testid="stSidebar"] .stVerticalBlock{{
    padding:28px 20px 100px !important;
    gap:6px !important;
}}

/* ───────── LOGO AREA ───────── */
.iris-logo{{
    font-family:'Syne',sans-serif;
    font-size:1.75rem;
    font-weight:800;
    letter-spacing:-1px;
    color:{T['title']};
    display:flex;
    align-items:center;
    gap:10px;
    margin-bottom:4px;
}}

.iris-dot{{
    width:8px;
    height:8px;
    border-radius:50%;
    background:{T['accent']};
    box-shadow:0 0 14px {T['accent']};
    animation:blink 2.5s infinite ease-in-out;
}}

@keyframes blink{{
    0%,100%{{opacity:1; transform:scale(1);}}
    50%{{opacity:.4; transform:scale(.7);}}
}}

.iris-tag{{
    font-family:'Space Mono',monospace;
    font-size:.52rem;
    color:{T['text_dim']};
    letter-spacing:4px;
    text-transform:uppercase;
    margin-bottom:22px;
    opacity:.8;
}}

/* ───────── USER CARD ───────── */
.user-pill{{
    background:linear-gradient(135deg,{T['ub']},{T['bg2']});
    border:1px solid {T['ubr']};
    border-radius:12px;
    padding:10px 14px;
    font-family:'Space Mono',monospace;
    font-size:.6rem;
    color:{T['accent']};
    letter-spacing:.5px;
    overflow:hidden;
    text-overflow:ellipsis;
    white-space:nowrap;
    margin-bottom:22px;
    transition:all .2s ease;
}}

.user-pill:hover{{
    border-color:{T['accent']}55;
    box-shadow:0 0 16px -6px {T['glow']};
}}

/* ───────── SECTION LABEL ───────── */
.sec-label{{
    font-family:'Space Mono',monospace;
    font-size:.52rem;
    color:{T['text_dimmer']};
    letter-spacing:4px;
    text-transform:uppercase;
    padding:14px 0 6px;
    margin-bottom:10px;
    position:relative;
}}

.sec-label::after{{
    content:'';
    position:absolute;
    left:0;
    bottom:0;
    width:28px;
    height:2px;
    background:{T['accent']};
    border-radius:4px;
    opacity:.7;
}}

/* ───────── STATUS BADGE ───────── */
.status-ok{{
    display:inline-flex;
    align-items:center;
    gap:8px;
    font-family:'Space Mono',monospace;
    font-size:.58rem;
    color:{T['accent']};
    letter-spacing:1px;
    margin-bottom:14px;
    padding:6px 10px;
    background:{T['ub']};
    border:1px solid {T['ubr']};
    border-radius:20px;
}}

.status-ok::before{{
    content:'';
    width:6px;
    height:6px;
    border-radius:50%;
    background:{T['accent']};
    box-shadow:0 0 10px {T['accent']};
    animation:blink 2.5s infinite;
}}

/* ───────── SIDEBAR BUTTON IMPROVEMENT ───────── */
section[data-testid="stSidebar"] .stButton>button{{
    background:transparent !important;
    border:1px solid transparent !important;
    border-radius:10px !important;
    padding:8px 8px !important;
    font-family:'Space Mono',monospace !important;
    font-size:.56rem !important;
    letter-spacing:1px !important;
    color:{T['text_dim']} !important;
    transition:all .18s ease !important;
    white-space:nowrap !important;
}}

section[data-testid="stSidebar"] .stVerticalBlock > .element-container > .stButton>button{{
    text-align:left !important;
    justify-content:flex-start !important;
    display:flex;
    padding-left:12px !important;
}}

section[data-testid="stSidebar"] [data-testid="column"] .stButton>button{{
    justify-content:center !important;
    display:flex;
    padding:8px 0 !important;
}}

section[data-testid="stSidebar"] .stButton>button:hover{{
    background:{T['ub']} !important;
    border-color:{T['border']} !important;
    color:{T['accent']} !important;
}}

section[data-testid="stSidebar"] .stVerticalBlock > .element-container > .stButton>button:hover{{
    transform:translateX(4px);
}}

/* ───────── SCROLLBAR ───────── */
section[data-testid="stSidebar"]::-webkit-scrollbar{{
    width:4px;
}}
section[data-testid="stSidebar"]::-webkit-scrollbar-thumb{{
    background:{T['border']};
    border-radius:4px;
}}


/* ── INPUTS ── */
.stTextInput label,.stSelectbox label,.stSlider label,.stTextArea label{{
  font-family:'Space Mono',monospace !important;font-size:.5rem !important;
  letter-spacing:2px !important;color:{T['text_dim']} !important;text-transform:uppercase !important;}}
.stTextInput>div>div>input,.stTextArea>div>div>textarea{{
  background:{T['bg2']} !important;border:1px solid {T['border']} !important;
  color:{T['text']} !important;border-radius:9px !important;
  font-family:'Figtree',sans-serif !important;font-size:.85rem !important;
  padding:10px 14px !important;transition:border-color .2s !important;}}
.stTextInput>div>div>input:focus,.stTextArea>div>div>textarea:focus{{
  border-color:{T['accent']}55 !important;box-shadow:0 0 0 3px {T['glow']} !important;outline:none !important;}}
.stTextInput>div>div>input::placeholder{{color:{T['text_dimmer']} !important;
  font-family:'Space Mono',monospace !important;font-size:.68rem !important;}}
.stSelectbox>div>div{{background:{T['bg2']} !important;border:1px solid {T['border']} !important;
  border-radius:9px !important;color:{T['text']} !important;}}
.stSlider>div>div>div>div{{background:{T['accent']}33 !important;}}
.stSlider>div>div>div>div>div{{background:{T['accent']} !important;box-shadow:0 0 8px {T['accent']} !important;}}

/* ── BUTTONS ── */
.stButton>button{{background:transparent !important;color:{T['text_dim']} !important;
  border:1px solid {T['border']} !important;border-radius:8px !important;
  font-family:'Space Mono',monospace !important;font-size:.48rem !important;
  letter-spacing:1px !important;padding:4px 8px !important;width:100% !important;
  transition:all .18s !important;margin-bottom:8px !important;text-transform:uppercase !important;}}
.stButton>button:hover{{border-color:{T['accent']}44 !important;color:{T['accent']} !important;
  background:{T['ub']} !important;}}
.stForm [data-testid="stFormSubmitButton"] button{{background:{T['accent']} !important;
  color:{T['bg']} !important;border:none !important;font-weight:700 !important;letter-spacing:2px !important;}}

/* ── TABS ── */
.stTabs [data-baseweb="tab-list"]{{background:transparent !important;gap:0 !important;
  border-bottom:1px solid {T['border']} !important;margin-bottom:18px !important;}}
.stTabs [data-baseweb="tab"]{{background:transparent !important;color:{T['text_dim']} !important;
  font-family:'Space Mono',monospace !important;font-size:.52rem !important;
  letter-spacing:3px !important;padding:10px 16px !important;border:none !important;
  border-bottom:2px solid transparent !important;text-transform:uppercase !important;}}
.stTabs [aria-selected="true"]{{color:{T['title']} !important;
  border-bottom-color:{T['accent']} !important;background:transparent !important;}}
.stTabs [data-baseweb="tab-highlight"],.stTabs [data-baseweb="tab-border"]{{display:none !important;}}

/* ── CHAT MESSAGES ── */
.stChatMessage{{background:{T['ab']} !important;border:1px solid {T['abr']} !important;
  border-radius:14px !important;padding:16px 20px !important;margin-bottom:10px !important;
  animation:msgIn .22s ease-out !important;}}
.stChatMessage:has([data-testid="stChatMessageAvatarUser"]){{
  background:{T['ub']} !important;border-color:{T['ubr']} !important;
  flex-direction:row-reverse !important;text-align:right !important;
  width:fit-content !important;max-width:80% !important;
  margin-left:auto !important;margin-right:24px !important;}}
@keyframes msgIn{{from{{opacity:0;transform:translateY(10px);}}to{{opacity:1;transform:translateY(0);}}}}
.stChatMessage p,.stChatMessage li{{font-family:'Figtree',sans-serif !important;
  font-size:.88rem !important;line-height:1.75 !important;color:{T['text']} !important;}}
.stChatMessage a{{color:{T['accent']} !important;}}
.stChatMessage [data-testid="stChatMessageAvatarUser"]{{background:{T['ub']} !important;
  border:1px solid {T['ubr']} !important;border-radius:8px !important;color:{T['accent']} !important;}}
.stChatMessage [data-testid="stChatMessageAvatarAssistant"]{{background:{T['ab']} !important;
  border:1px solid {T['abr']} !important;border-radius:8px !important;color:{T['accent2']} !important;}}
.stChatMessage code{{font-family:'Space Mono',monospace !important;font-size:.73rem !important;
  background:{T['bg3']} !important;border:1px solid {T['border']} !important;
  border-radius:4px !important;padding:1px 5px !important;color:{T['accent']} !important;}}
.stChatMessage pre{{background:{T['bg2']} !important;border:1px solid {T['border']} !important;
  border-radius:10px !important;padding:16px !important;}}

/* ── CHAT INPUT ── */
.stChatInputContainer{{position:fixed !important;bottom:0 !important;left:268px !important;
  right:0 !important;background:linear-gradient(to top,{T['bg']} 60%,transparent) !important;
  padding:16px 40px 24px !important;border-top:none !important;z-index:100;}}
.stChatInputContainer>div{{max-width:820px !important;margin:0 auto !important;}}
.stChatInput{{background:{T['bg2']} !important;border:1px solid {T['border']} !important;
  border-radius:12px !important;color:{T['text']} !important;
  font-family:'Figtree',sans-serif !important;font-size:.88rem !important;
  padding:13px 16px !important;transition:border-color .2s !important;}}
.stChatInput:focus{{border-color:{T['accent']}44 !important;
  box-shadow:0 0 0 3px {T['glow']} !important;outline:none !important;}}
.stChatInput::placeholder{{color:{T['text_dimmer']} !important;
  font-family:'Space Mono',monospace !important;font-size:.68rem !important;}}
.stChatInputContainer button{{background:transparent !important;
  border:1px solid {T['border']} !important;border-radius:10px !important;
  color:{T['text_dim']} !important;transition:all .2s !important;}}
.stChatInputContainer button:hover{{border-color:{T['accent']}44 !important;color:{T['accent']} !important;}}

/* ── MODULE CARDS ── */
.mcard{{background:{T['bg2']};border:1px solid {T['border']};
  border-radius:14px;padding:20px;margin-bottom:12px;}}
.mcard-title{{font-family:'Syne',sans-serif;font-size:1rem;font-weight:800;
  letter-spacing:-.5px;color:{T['title']};margin-bottom:3px;}}
.mcard-sub{{font-family:'Space Mono',monospace;font-size:.5rem;color:{T['text_dim']};
  letter-spacing:2px;text-transform:uppercase;margin-bottom:12px;}}
.result-text{{font-family:'Figtree',sans-serif;font-size:.88rem;color:{T['text']};line-height:1.75;}}
.big-num{{font-family:'Syne',sans-serif;font-size:2.8rem;font-weight:800;
  letter-spacing:-2px;color:{T['accent']};}}
.weather-meta{{font-family:'Space Mono',monospace;font-size:.58rem;color:{T['text_dim']};
  margin-top:10px;line-height:2.2;}}

/* ── IMAGE GRID (inline in chat) ── */
.chat-img-grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-top:12px;}}
.chat-img-grid a{{display:block;border-radius:10px;overflow:hidden;
  border:1px solid {T['border']};transition:transform .18s,border-color .18s;}}
.chat-img-grid a:hover{{transform:scale(1.03);border-color:{T['ubr']};}}
.chat-img-grid img{{width:100%;height:140px;object-fit:cover;display:block;}}
.chat-img-caption{{font-family:'Space Mono',monospace;font-size:.48rem;
  color:{T['text_dimmer']};padding:5px 6px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}}

/* ── YT CARD (inline in chat) ── */
.yt-card{{display:flex;gap:12px;align-items:flex-start;
  background:{T['bg3']};border:1px solid {T['border']};
  border-radius:12px;padding:12px;margin-bottom:8px;
  transition:border-color .18s;}}
.yt-card:hover{{border-color:{T['ubr']};}}
.yt-thumb{{width:120px;min-width:120px;border-radius:8px;overflow:hidden;border:1px solid {T['border']};}}
.yt-thumb img{{width:100%;height:68px;object-fit:cover;display:block;}}
.yt-info{{flex:1;min-width:0;}}
.yt-title{{font-family:'Figtree',sans-serif;font-size:.85rem;font-weight:600;
  color:{T['title']};line-height:1.4;margin-bottom:4px;}}
.yt-title a{{color:{T['accent']} !important;text-decoration:none;}}
.yt-title a:hover{{text-decoration:underline;}}
.yt-channel{{font-family:'Space Mono',monospace;font-size:.52rem;color:{T['text_dim']};
  letter-spacing:1px;margin-bottom:5px;}}
.yt-desc{{font-family:'Figtree',sans-serif;font-size:.78rem;color:{T['text_dim']};
  line-height:1.5;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;}}
.yt-open{{display:inline-block;margin-top:8px;font-family:'Space Mono',monospace;
  font-size:.5rem;color:{T['accent']};letter-spacing:1.5px;border:1px solid {T['ubr']};
  border-radius:5px;padding:4px 10px;text-decoration:none;transition:all .15s;}}
.yt-open:hover{{background:{T['ub']};}}

/* ── MIC BUTTON ── */
.mic-area{{max-width:820px;margin:8px auto 0;padding:0 46px;display:flex;align-items:center;gap:12px;}}
.mic-area.form-mic{{margin:0;padding:2px 0 0 0;width:100%;justify-content:flex-end;}}
.mic-btn{{display:inline-flex;align-items:center;gap:8px;
  background:{T['ub']};border:1px solid {T['ubr']};border-radius:8px;
  color:{T['accent']};font-family:'Space Mono',monospace;font-size:.55rem;
  letter-spacing:2px;padding:8px 14px;cursor:pointer;transition:all .18s;
  text-transform:uppercase;white-space:nowrap;height:100%;min-height:38px;}}
.mic-btn:hover{{box-shadow:0 0 14px {T['glow']};}}
.mic-hint{{font-family:'Space Mono',monospace;font-size:.5rem;
  color:{T['text_dim']};letter-spacing:1px;}}

/* ── MISC ── */
::-webkit-scrollbar{{width:3px;height:3px;}}
::-webkit-scrollbar-track{{background:transparent;}}
::-webkit-scrollbar-thumb{{background:{T['border']};border-radius:3px;}}
.stSuccess,.stError,.stWarning,.stInfo{{border-radius:8px !important;
  font-family:'Space Mono',monospace !important;font-size:.68rem !important;}}
.stCaption{{font-family:'Space Mono',monospace !important;font-size:.55rem !important;
  color:{T['text_dim']} !important;}}
.main-wrap{{max-width:820px;margin:0 auto;padding:36px 46px 130px;}}
.page-title{{font-family:'Syne',sans-serif;font-size:2rem;font-weight:800;
  letter-spacing:-2px;color:{T['title']};line-height:1;margin-bottom:4px;}}
.page-rule{{height:1px;background:linear-gradient(to right,{T['border']},transparent);
  margin:13px 0 24px;}}
</style>
""", unsafe_allow_html=True)



# ─── GEMINI 3 PRO CLIENT ──────────────────────────────────────────────────────────────
def get_client():
    key = os.getenv("GEMINI_API_KEY", "") or st.session_state.get("gemini_key", "")
    return Groq(api_key=key) if key else None

def llm_stream(prompt, system=None, placeholder=None, include_history=True):
    client = get_client()
    if not client:
        msg = "⚠️ No Gemini API key set."
        if placeholder: placeholder.error(msg)
        return msg
    sys_msg = system or (
        "You are IRIS, a smart AI assistant. Be helpful, concise, and friendly. "
        "For weather, search, YouTube, images, dictionary, health, math, and translation "
        "requests — handle them clearly and directly."
    )
    history = [{"role": m["role"], "content": m["content"]}
               for m in st.session_state.messages[-20:]] if include_history else []
    msgs = [{"role": "system", "content": sys_msg}] + history + [{"role": "user", "content": prompt}]
    resp = ""
    try:
        model = st.session_state.get("model", "llama-3.3-70b-versatile")
        temp  = st.session_state.get("temperature", 0.7)
        completion = client.chat.completions.create(model=model, messages=msgs,
                                                    temperature=temp, stream=True)
        for chunk in completion:
            d = chunk.choices[0].delta.content
            if d:
                resp += d
                if placeholder: placeholder.markdown(resp + "▌")
        if placeholder: placeholder.markdown(resp)
    except Exception as e:
        resp = f"⚠️ {e}"
        if placeholder: placeholder.error(resp)
    return resp

def llm_quick(prompt, system="You are a helpful, concise assistant."):
    client = get_client()
    if not client: return "⚠️ No API key."
    try:
        r = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role":"system","content":system},{"role":"user","content":prompt}],
            temperature=0.4)
        return r.choices[0].message.content
    except Exception as e:
        return f"⚠️ {e}"

# ─── GOOGLE SEARCH ────────────────────────────────────────────────────────────
def google_search(query, num=5):
    key = os.getenv("GOOGLE_API_KEY",""); cse = os.getenv("GOOGLE_CSE_ID","")
    if not key or not cse: return None, "Missing GOOGLE_API_KEY or GOOGLE_CSE_ID"
    try:
        r = requests.get("https://www.googleapis.com/customsearch/v1",
            params={"key":key,"cx":cse,"q":query,"num":num}, timeout=8)
        d = r.json()
        if "items" not in d: return None, d.get("error",{}).get("message","No results")
        return [{"title":i["title"],"link":i["link"],"snippet":i.get("snippet","")} for i in d["items"]], None
    except Exception as e: return None, str(e)

# ─── GOOGLE IMAGE SEARCH ──────────────────────────────────────────────────────
def google_image_search(query, num=6):
    key = os.getenv("GOOGLE_API_KEY",""); cse = os.getenv("GOOGLE_CSE_ID","")
    if not key or not cse: return None, "Missing GOOGLE_API_KEY or GOOGLE_CSE_ID"
    try:
        r = requests.get("https://www.googleapis.com/customsearch/v1",
            params={"key":key,"cx":cse,"q":query,"num":num,"searchType":"image"}, timeout=8)
        d = r.json()
        if "items" not in d: return None, d.get("error",{}).get("message","No images")
        return [{"title":i["title"],"link":i["link"],
                 "thumb":i.get("image",{}).get("thumbnailLink",i["link"])} for i in d["items"]], None
    except Exception as e: return None, str(e)

# ─── YOUTUBE SEARCH ───────────────────────────────────────────────────────────
def youtube_search(query, max_results=5, search_type="video"):
    key = os.getenv("YOUTUBE_API_KEY","")
    if not key: return None, "Missing YOUTUBE_API_KEY"
    try:
        r = requests.get("https://www.googleapis.com/youtube/v3/search",
            params={"key":key,"q":query,"part":"snippet","maxResults":max_results,
                    "type":search_type}, timeout=8)
        d = r.json()
        if "items" not in d: return None, d.get("error",{}).get("message","No results")
        items = []
        for i in d["items"]:
            vid = i["id"].get("videoId") or i["id"].get("playlistId","")
            s = i["snippet"]
            items.append({"id":vid,"title":s["title"],"channel":s["channelTitle"],
                "desc":s.get("description","")[:110],
                "thumb":s["thumbnails"]["medium"]["url"],
                "url":(f"https://www.youtube.com/watch?v={vid}" if search_type=="video"
                       else f"https://www.youtube.com/playlist?list={vid}")})
        return items, None
    except Exception as e: return None, str(e)

# ─── WEATHER (Open-Meteo) ───────────────────────────────────────────────────────
def get_weather(city, unit="metric"):
    try:
        # 1. Geocode
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={urllib.parse.quote(city)}&count=1&language=en&format=json"
        geo_r = requests.get(geo_url, timeout=8)
        geo_d = geo_r.json()
        if not geo_d.get("results"): return None, f"City not found: {city}"
        loc = geo_d["results"][0]
        lat, lon = loc["latitude"], loc["longitude"]
        city_name = loc.get("name", city)
        country = loc.get("country", "")

        # 2. Weather
        unit_str = "&temperature_unit=fahrenheit&wind_speed_unit=mph" if unit == "imperial" else "&wind_speed_unit=kmh"
        w_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,surface_pressure,wind_speed_10m,wind_direction_10m,visibility&daily=weather_code,temperature_2m_max,temperature_2m_min,sunrise,sunset,uv_index_max&timezone=auto{unit_str}"
        w_r = requests.get(w_url, timeout=8)
        w_d = w_r.json()

        cur = w_d["current"]
        daily = w_d["daily"]

        def get_wmo_desc(code):
            codes = {0:"Clear sky", 1:"Mainly clear", 2:"Partly cloudy", 3:"Overcast", 45:"Fog", 48:"Depositing rime fog", 51:"Light drizzle", 53:"Moderate drizzle", 55:"Dense drizzle", 56:"Light freezing drizzle", 57:"Dense freezing drizzle", 61:"Slight rain", 63:"Moderate rain", 65:"Heavy rain", 66:"Light freezing rain", 67:"Heavy freezing rain", 71:"Slight snow fall", 73:"Moderate snow fall", 75:"Heavy snow fall", 77:"Snow grains", 80:"Slight rain showers", 81:"Moderate rain showers", 82:"Violent rain showers", 85:"Slight snow showers", 86:"Heavy snow showers", 95:"Thunderstorm", 96:"Thunderstorm with slight hail", 99:"Thunderstorm with heavy hail"}
            return codes.get(code, "Unknown")
            
        def deg_to_dir(deg):
            dirs = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
            return dirs[round(deg / 22.5) % 16]

        t_unit = "°F" if unit == "imperial" else "°C"
        w_unit = "mph" if unit == "imperial" else "km/h"
        
        vis = cur.get('visibility')
        vis_str = f"{round(vis/1000, 1)} km" if vis is not None else "N/A"

        return {
            "city": city_name,
            "country": country,
            "temp": f"{cur['temperature_2m']}{t_unit}",
            "feels": f"{cur['apparent_temperature']}{t_unit}",
            "desc": get_wmo_desc(cur['weather_code']),
            "humidity": cur['relative_humidity_2m'],
            "wind": f"{cur['wind_speed_10m']} {w_unit} {deg_to_dir(cur['wind_direction_10m'])}",
            "visibility": vis_str,
            "pressure": f"{cur['surface_pressure']} hPa",
            "uv": daily.get("uv_index_max", ["N/A"])[0],
            "high": f"{daily['temperature_2m_max'][0]}{t_unit}",
            "low": f"{daily['temperature_2m_min'][0]}{t_unit}",
            "sunrise": daily["sunrise"][0].split("T")[-1] if daily.get("sunrise") else "N/A",
            "sunset": daily["sunset"][0].split("T")[-1] if daily.get("sunset") else "N/A",
        }, None
    except requests.exceptions.Timeout:
        return None, "Connection to weather server timed out. Please try again later."
    except Exception as e:
        return None, f"Failed to retrieve weather data: {str(e)}"

# ─── RENDER HELPERS (used both in chat and dedicated modules) ─────────────────
import textwrap

def render_image_grid(imgs, query=""):
    """Render a 3-col image grid. Works inside st.chat_message or standalone."""
    grid_html = textwrap.dedent(f"""
    <div style='margin-top:10px;'>
      <div style='font-family:Space Mono,monospace;font-size:.52rem;color:{T['text_dim']};
                  letter-spacing:2px;text-transform:uppercase;margin-bottom:8px;'>
        🖼 Images · {query}
      </div>
      <div class='chat-img-grid'>
    """)
    for img in imgs:
        grid_html += textwrap.dedent(f"""
        <a href='{img['link']}' target='_blank'>
          <img src='{img['thumb']}' alt='{img['title'][:40]}' loading='lazy'
               onerror="this.style.display='none'">
          <div class='chat-img-caption'>{img['title'][:45]}</div>
        </a>""")
    grid_html += "</div></div>"
    st.markdown(grid_html, unsafe_allow_html=True)

def render_yt_cards(videos):
    """Render YouTube video cards with thumbnails."""
    for v in videos:
        st.markdown(textwrap.dedent(f"""
        <div class='yt-card'>
          <div class='yt-thumb'>
            <a href='{v['url']}' target='_blank'>
              <img src='{v['thumb']}' alt='{v['title'][:40]}' loading='lazy'>
            </a>
          </div>
          <div class='yt-info'>
            <div class='yt-title'><a href='{v['url']}' target='_blank'>{v['title']}</a></div>
            <div class='yt-channel'>{v['channel']}</div>
            <div class='yt-desc'>{v['desc']}</div>
            <a class='yt-open' href='{v['url']}' target='_blank'>▶ WATCH ON YOUTUBE</a>
          </div>
        </div>
        """), unsafe_allow_html=True)

def render_weather_card(w):
    desc_l = w['desc'].lower()
    emoji = ("⛈" if "thunder" in desc_l else "🌧" if "rain" in desc_l else
             "🌦" if "drizzle" in desc_l else "❄️" if "snow" in desc_l else
             "🌫" if "fog" in desc_l or "mist" in desc_l else
             "🌤" if "cloud" in desc_l else "☀️")
    st.markdown(textwrap.dedent(f"""
    <div class='mcard'>
      <div class='mcard-title'>{emoji} {w['city']}, {w['country']}</div>
      <div class='mcard-sub'>{w['desc']}</div>
      <div class='big-num'>{w['temp']}</div>
      <div class='weather-meta'>
        FEELS LIKE {w['feels']} &nbsp;·&nbsp; HIGH {w['high']} &nbsp;·&nbsp; LOW {w['low']}<br>
        💧 HUMIDITY {w['humidity']}% &nbsp;·&nbsp; 💨 WIND {w['wind']}<br>
        👁 VIS {w['visibility']} &nbsp;·&nbsp; 📊 PRESSURE {w['pressure']} &nbsp;·&nbsp; ☀️ UV {w['uv']}<br>
        🌅 SUNRISE {w['sunrise']} &nbsp;·&nbsp; 🌇 SUNSET {w['sunset']}
      </div>
      <div style='font-family:Space Mono,monospace;font-size:.44rem;
                  color:{T['text_dimmer']};margin-top:12px;'>
        SOURCE: wttr.in · LIVE · NO API KEY
      </div>
    </div>"""), unsafe_allow_html=True)

def mic_button(btn_id="iris-mic-main", is_chat=False):
    cls = "mic-area" if is_chat else "mic-area form-mic"
    hint = "<span class='mic-hint'>Browser voice input · Chrome / Edge</span>" if is_chat else ""
    st.markdown(f"""
    <div class='{cls}' id='area-{btn_id}'>
      <button type='button' id='{btn_id}' class='mic-btn'>
        🎙 SPEAK
      </button>
      {hint}
    </div>
    """, unsafe_allow_html=True)

    teleport_js = ""
    if is_chat:
        teleport_js = f"""
        const chatSubmitBtn = parentDoc.querySelector('[data-testid="stChatInputSubmitButton"]');
        if (chatSubmitBtn) {{
            const submitWrapper = chatSubmitBtn.parentNode;
            if (submitWrapper && submitWrapper.parentNode) {{
                // Clean up old ones to prevent duplicates on rerun
                const existing = submitWrapper.parentNode.querySelectorAll('.teleported-mic');
                existing.forEach(e => e.remove());

                const micDiv = parentDoc.getElementById("area-{btn_id}");
                if (micDiv && !micDiv.dataset.teleported) {{
                    micDiv.dataset.teleported = "true";
                    
                    const clonedMicDiv = micDiv.cloneNode(true);
                    clonedMicDiv.id = "cloned-area-{btn_id}";
                    clonedMicDiv.classList.add("teleported-mic");
                    
                    clonedMicDiv.style.margin = "0 8px 0 2px";
                    clonedMicDiv.style.padding = "0";
                    clonedMicDiv.style.width = "auto";
                    clonedMicDiv.style.display = "flex";
                    clonedMicDiv.style.alignItems = "center";
                    
                    const hint = clonedMicDiv.querySelector(".mic-hint");
                    if (hint) hint.style.display = "none";
                    
                    const cbtn = clonedMicDiv.querySelector('.mic-btn');
                    if (cbtn) {{
                        cbtn.id = "cloned-btn-{btn_id}";
                        cbtn.style.padding = '6px 14px';
                        cbtn.style.minHeight = '36px';
                    }}
                    
                    submitWrapper.parentNode.insertBefore(clonedMicDiv, submitWrapper);
                    
                    // Hide original instead of moving it to prevent React from crashing
                    micDiv.style.display = "none";
                }}
            }}
        }}
        """

    import streamlit.components.v1 as components
    components.html(f"""
    <script>
    const btnId = '{btn_id}';
    const parentDoc = window.parent.document;
    
    {teleport_js}

    const btn = parentDoc.getElementById("cloned-btn-" + btnId) || parentDoc.getElementById(btnId);

    if (btn && !btn.hasAttribute('data-stt-bound')) {{
        btn.setAttribute('data-stt-bound', 'true');
        
        btn.addEventListener('click', function(e) {{
            e.preventDefault();
            const SR = window.SpeechRecognition || window.webkitSpeechRecognition || window.parent.SpeechRecognition || window.parent.webkitSpeechRecognition;
            if (!SR) {{ alert('Speech recognition not supported. Use Chrome or Edge.'); return; }}

            const rec = new SR();
            rec.lang = 'en-US';
            rec.interimResults = false;
            rec.maxAlternatives = 1;

            btn.innerHTML = '● LISTENING...';
            btn.style.color = '#ff4b4b';
            btn.style.boxShadow = '0 0 15px rgba(255,75,75,0.4)';

            rec.onresult = function(e) {{
                const text = e.results[0][0].transcript;
                const selectors = [
                    'textarea[data-testid="stChatInputTextArea"]',
                    'div[data-testid="stTextInput"] input',
                    'div[data-testid="stTextArea"] textarea',
                    '.main-wrap textarea',
                    '.main-wrap input'
                ];
                let input = null;
                for (const s of selectors) {{
                    input = parentDoc.querySelector(s);
                    if (input && input.offsetParent !== null) break; 
                }}

                if (input) {{
                    const nativeValueSetter = Object.getOwnPropertyDescriptor(
                        window.parent.HTMLTextAreaElement.prototype.isPrototypeOf(input) ? 
                        window.parent.HTMLTextAreaElement.prototype : window.parent.HTMLInputElement.prototype,
                        'value'
                    ).set;
                    nativeValueSetter.call(input, text);
                    input.dispatchEvent(new window.parent.Event('input', {{ bubbles: true }}));
                    input.dispatchEvent(new window.parent.Event('change', {{ bubbles: true }}));
                    input.focus();
                }}
            }};

            const stop = () => {{
                btn.innerHTML = '🎙 SPEAK';
                btn.style.color = '';
                btn.style.boxShadow = '';
            }};

            rec.onerror = (e) => {{
                btn.innerHTML = '❌ ERROR';
                setTimeout(stop, 1500);
            }};
            
            rec.onend = stop;
            rec.start();
        }});
    }}
    </script>
    """, height=0, width=0)

# ─── INTENT DETECTION ─────────────────────────────────────────────────────────
# NOTE: image must be checked BEFORE search to avoid "show me images" → search
INTENTS = [
    ("image",      r'\b(image|images|photo|photos|picture|pictures|show me|pic of|pics of|find image|search image)\b'),
    ("youtube",    r'\b(play|youtube|video|videos|music|song|watch|stream|yt)\b'),
    ("weather",    r'\b(weather|temperature|temp\b|forecast|rain|humid|climate|hot outside|cold outside|sunny|cloudy|monsoon|snow)\b'),
    ("search",     r'\b(search|google|find|look up|lookup|who is|what is|news|latest|tell me about)\b'),
    ("dictionary", r'\b(define|definition|meaning of|what does .+ mean|synonym|antonym)\b'),
    ("calculate",  r'\b(calculate|compute|solve|math|\d+\s*[\+\-\*\/\^]\s*\d+|sqrt|percent|interest|equation)\b'),
    ("translate",  r'\b(translate|translation|say .+ in |how do you say|in (hindi|spanish|french|german|japanese|arabic|chinese|urdu|tamil|telugu|marathi|bengali|gujarati|punjabi|kannada|malayalam|russian|korean|italian|dutch|turkish|portuguese))\b'),
    ("health",     r'\b(symptom|symptoms|medicine|drug|disease|illness|ill|sick|fever|pain|cure|remedy|tablet|dose|health tip|first aid|nutrition|diet)\b'),
    ("open",       r'\b(open|launch|start|run)\b'),
]

def detect_intent(text):
    t = text.lower()
    for intent, pattern in INTENTS:
        if re.search(pattern, t, re.I):
            return intent
    return "chat"

def extract_city(prompt):
    # try "weather in X", "X weather", "X ka mausam"
    for pat in [
        r'weather\s+(?:in|at|for|of)\s+([A-Za-z][A-Za-z\s]{1,30}?)(?:\?|$|\.|\s+today|\s+now)',
        r'([A-Za-z][A-Za-z\s]{1,20}?)\s+weather',
        r'temperature\s+(?:in|at|of)\s+([A-Za-z][A-Za-z\s]{1,30}?)(?:\?|$|\.)',
        r'forecast\s+(?:for|in)\s+([A-Za-z][A-Za-z\s]{1,30}?)(?:\?|$|\.)',
    ]:
        m = re.search(pat, prompt, re.I)
        if m:
            city = m.group(1).strip().rstrip('?.,')
            if len(city) > 1:
                return city
    return "Mumbai"

def extract_query(prompt, remove_words):
    q = prompt
    for w in remove_words:
        q = re.sub(r'\b' + w + r'\b', '', q, flags=re.I)
    return re.sub(r'\s+', ' ', q).strip(' ,?.')

# ─── SMART INTENT HANDLER (runs inside chat) ──────────────────────────────────
def handle_intent(prompt, text_placeholder):
    """
    Returns (text_response, media_type, media_data)
    media_type: None | 'images' | 'youtube' | 'weather_card'
    """
    intent = detect_intent(prompt)

    # ── WEATHER ──────────────────────────────────────────────────────────────
    if intent == "weather":
        city = extract_city(prompt)
        unit = "imperial" if re.search(r'\bfahrenheit\b|\b°f\b', prompt, re.I) else "metric"
        w, err = get_weather(city, unit)
        if err:
            resp = f"Couldn't get weather for **{city}**: {err}"
            text_placeholder.markdown(resp)
            return resp, None, None
        desc_l = w['desc'].lower()
        emoji = ("⛈" if "thunder" in desc_l else "🌧" if "rain" in desc_l else
                 "🌦" if "drizzle" in desc_l else "❄️" if "snow" in desc_l else
                 "🌫" if "fog" in desc_l or "mist" in desc_l else
                 "🌤" if "cloud" in desc_l else "☀️")
        resp = (f"{emoji} **Weather in {w['city']}, {w['country']}**\n\n"
                f"**{w['temp']}** — {w['desc']}\n"
                f"Feels like {w['feels']} · High {w['high']} / Low {w['low']}\n\n"
                f"💧 Humidity {w['humidity']}% · 💨 Wind {w['wind']}\n"
                f"👁 Visibility {w['visibility']} · 📊 {w['pressure']}\n"
                f"☀️ UV {w['uv']} · 🌅 {w['sunrise']} / 🌇 {w['sunset']}")
        text_placeholder.markdown(resp)
        return resp, "weather_card", w

    # ── IMAGE SEARCH ─────────────────────────────────────────────────────────
    elif intent == "image":
        q = extract_query(prompt, ["image","images","photo","photos","picture","pictures",
                                   "show me","pic of","pics of","find","search","get"])
        if not q: q = prompt
        imgs, err = google_image_search(q, num=6)
        if err:
            resp = f"Image search error: {err}"
            text_placeholder.markdown(resp)
            return resp, None, None
        resp = f"🖼 Here are images for **{q}**:"
        text_placeholder.markdown(resp)
        return resp, "images", {"imgs": imgs, "query": q}

    # ── YOUTUBE ──────────────────────────────────────────────────────────────
    elif intent == "youtube":
        q = extract_query(prompt, ["play","youtube","video","videos","music","song",
                                   "watch","stream","yt","me","some","a"])
        if not q: q = prompt
        results, err = youtube_search(q, max_results=4)
        if err:
            fb_url = f"https://youtube.com/results?search_query={urllib.parse.quote(q)}"
            resp = f"▶️ YouTube search for **{q}**\n\n[Open YouTube →]({fb_url})"
            text_placeholder.markdown(resp)
            return resp, None, None
        resp = f"▶️ **YouTube results for: {q}**"
        text_placeholder.markdown(resp)
        return resp, "youtube", {"videos": results, "query": q}

    # ── WEB SEARCH ───────────────────────────────────────────────────────────
    elif intent == "search":
        q = extract_query(prompt, ["search","google","find","look up","tell me about",
                                   "what is","who is","news","latest"])
        if not q: q = prompt
        results, err = google_search(q, num=5)
        if err or not results:
            resp = llm_stream(prompt, placeholder=text_placeholder)
            return resp, None, None
        snippets = "\n".join([r['snippet'] for r in results[:4]])
        summary = llm_quick(f"Summarize in 2 concise sentences about '{q}':\n{snippets}")
        links = "\n\n".join([f"**[{r['title']}]({r['link']})**\n{r['snippet']}" for r in results])
        resp = f"🔍 **{q}**\n\n{summary}\n\n---\n{links}"
        text_placeholder.markdown(resp)
        return resp, None, None

    # ── DICTIONARY ───────────────────────────────────────────────────────────
    elif intent == "dictionary":
        m = re.search(r'(?:define|definition|meaning of|what does)\s+["\']?(\w+)', prompt, re.I)
        word = m.group(1) if m else extract_query(prompt, ["define","definition","meaning"])
        resp = llm_stream(
            f"Define '{word}': 1) phonetics, 2) part of speech, 3) definition, 4) brief etymology, 5) 2 examples.",
            system="You are a precise dictionary. Use clear formatting.",
            placeholder=text_placeholder, include_history=False)
        return resp, None, None

    # ── CALCULATOR ───────────────────────────────────────────────────────────
    elif intent == "calculate":
        m = re.search(r'[\d\.\+\-\*\/\^\(\)\s]+', prompt)
        if m:
            try:
                import math as _m
                safe = m.group().strip().replace("^","**")
                val = eval(safe, {"__builtins__":{},"sqrt":_m.sqrt,"pi":_m.pi,"e":_m.e})
                resp = f"🧮 **Result:** `{val}`\n\n*{m.group().strip()}*"
                text_placeholder.markdown(resp)
                return resp, None, None
            except: pass
        resp = llm_stream(f"Solve step by step: {prompt}",
                          system="You are a precise math solver. Show all steps.",
                          placeholder=text_placeholder, include_history=False)
        return resp, None, None

    # ── TRANSLATE ────────────────────────────────────────────────────────────
    elif intent == "translate":
        resp = llm_stream(
            prompt + "\n\nGive only the translation. If non-Latin script, add romanized pronunciation below.",
            system="You are a professional multilingual translator.",
            placeholder=text_placeholder)
        return resp, None, None

    # ── HEALTH ───────────────────────────────────────────────────────────────
    elif intent == "health":
        resp = llm_stream(prompt,
            system="You are a health information assistant. Give accurate general info. "
                   "Always recommend consulting a doctor. Be concise and structured.",
            placeholder=text_placeholder)
        return resp, None, None

    # ── OPEN FILE ────────────────────────────────────────────────────────────
    elif intent == "open":
        import sys
        if sys.platform != "win32":
            resp = "⚠️ **Local File Access Disabled:** I am currently running in a cloud environment (Streamlit Cloud). I do not have access to the local files, folders, or applications on your computer."
            text_placeholder.markdown(resp)
            return resp, None, None

        q = extract_query(prompt, ["open", "launch", "start", "run", "file", "this", "the"])
        if not q: q = prompt
        filepath = q.strip()
        found = False
        
        # Try finding exactly the provided path
        if os.path.exists(filepath) and os.path.isfile(filepath):
            try:
                os.startfile(filepath)
                resp = f"📂 Opened file: **{filepath}**"
                text_placeholder.markdown(resp)
                return resp, None, None
            except Exception as e:
                pass
                
        # Attempt heuristic search downward specifically across Downloads and Desktop
        search_dirs = [
            os.path.join(os.path.expanduser("~"), "Downloads"),
            os.path.join(os.path.expanduser("~"), "Desktop")
        ]
        
        for base_dir in search_dirs:
            if found: break
            if not os.path.exists(base_dir): continue
            
            for root, dirs, files in os.walk(base_dir):
                if ".gemini" in root or "venv" in root or ".git" in root or "__pycache__" in root: continue
                for file in files:
                    if file.lower() == filepath.lower() or filepath.lower() in file.lower():
                        full_path = os.path.join(root, file)
                        try:
                            os.startfile(full_path)
                            resp = f"📂 Opened: **{file}**"
                            text_placeholder.markdown(resp)
                            found = True
                            break
                        except Exception as e:
                            pass
                if found: break
            
        if not found:
            resp = f"Could not find a file matching **{filepath}**."
            text_placeholder.markdown(resp)
        return resp, None, None

    # ── DEFAULT CHAT ─────────────────────────────────────────────────────────
    else:
        resp = llm_stream(prompt, placeholder=text_placeholder)
        return resp, None, None


# ─────────────────────────────────────────────────────────────────────────────
# AUTH PAGE
# ─────────────────────────────────────────────────────────────────────────────
if not st.session_state.authenticated:
    _, mid, _ = st.columns([1, 1.1, 1])
    with mid:
        st.markdown(f"""
        <div style='margin-top:72px;text-align:center;'>
          <div style='font-family:Syne,sans-serif;font-size:3.2rem;font-weight:800;
                      letter-spacing:-3px;color:{T["title"]};line-height:1;'>IRIS</div>
          <div style='font-family:Space Mono,monospace;font-size:.48rem;color:{T["text_dimmer"]};
                      letter-spacing:5px;text-transform:uppercase;margin:8px 0 36px;'>
            Intelligent Response Interface System
          </div>
        </div>""", unsafe_allow_html=True)
        t1, t2 = st.tabs(["[ LOGIN ]", "[ SIGN UP ]"])
        with t1:
            with st.form("lf"):
                em = st.text_input("Email", placeholder="you@domain.io")
                pw = st.text_input("Password", type="password")
                if st.form_submit_button("INITIALIZE SESSION"):
                    u = load_users()
                    if em in u and u[em] == hash_pw(pw):
                        st.session_state.authenticated = True
                        st.session_state.user_email = em
                        st.session_state.messages = load_memory(em)
                        st.success("AUTHENTICATED")
                        st.rerun()
                    else:
                        st.error("ACCESS DENIED — INVALID CREDENTIALS")
        with t2:
            with st.form("sf"):
                ne = st.text_input("Email")
                np_ = st.text_input("Password", type="password")
                cp = st.text_input("Confirm Password", type="password")
                if st.form_submit_button("CREATE IDENTITY"):
                    if np_ != cp:      st.error("PASSWORDS DO NOT MATCH")
                    elif len(np_) < 6: st.error("MINIMUM 6 CHARACTERS")
                    else:
                        u = load_users()
                        if ne in u: st.error("IDENTITY ALREADY EXISTS")
                        else:
                            u[ne] = hash_pw(np_); save_users(u)
                            st.success("CREATED — PLEASE LOGIN")
    st.stop()

# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"""
    <div class='iris-logo'><span class='iris-dot'></span>IRIS</div>
    <div class='iris-tag'>Active Session · v3.1</div>
    <div class='user-pill'>◈ &nbsp;{st.session_state.user_email}</div>
    """, unsafe_allow_html=True)

    gemini_key = os.getenv("GEMINI_API_KEY","")
    if not gemini_key:
        st.markdown("<div class='sec-label'>GEMINI KEY</div>", unsafe_allow_html=True)
        gk = st.text_input("GEMINI API Key", placeholder="API Key...", type="password",
                           key="gemini_key_inp", label_visibility="collapsed")
        if gk: st.session_state["gemini_key"] = gk
        if not gk and not st.session_state.get("gemini_key"):
            st.warning("GEMINI KEY REQUIRED"); st.stop()
    else:
        st.markdown("<div class='status-ok'>GEMINI 3 PRO AUTHENTICATED</div>", unsafe_allow_html=True)

    if os.getenv("GOOGLE_API_KEY",""):
        st.markdown("<div class='status-ok'>GOOGLE SEARCH ACTIVE</div>", unsafe_allow_html=True)
    if os.getenv("YOUTUBE_API_KEY",""):
        st.markdown("<div class='status-ok'>YOUTUBE API ACTIVE</div>", unsafe_allow_html=True)

    st.markdown("<div class='sec-label'>Modules</div>", unsafe_allow_html=True)
    MODS = [("💬","chat","CHAT"),("🔍","search","SEARCH"),("🖼","images","IMAGES"),
            ("▶️","youtube","YOUTUBE"),("🌤","weather","WEATHER"),
            ("📖","dictionary","DICTIONARY"),("💊","health","HEALTH"),
            ("🧮","calculator","CALCULATOR"),("🌐","translator","TRANSLATOR")]
    for icon, key, label in MODS:
        if st.button(f"{icon}  {label}", key=f"nav_{key}"):
            st.session_state.active_module = key; st.rerun()

    st.markdown("<div class='sec-label'>Settings</div>", unsafe_allow_html=True)
    st.session_state["model"] = "llama-3.3-70b-versatile"
    st.session_state["temperature"] = 0.7

    tc1, tc2 = st.columns([1.6, 1])
    with tc1:
        st.session_state.tts_enabled = st.checkbox("🔊 Voice (gTTS)", value=st.session_state.tts_enabled)
    with tc2:
        lmap = {"EN":"en","HI":"hi","ES":"es","FR":"fr","DE":"de",
                "JA":"ja","AR":"ar","ZH":"zh","TA":"ta","TE":"te","MR":"mr"}
        sel = st.selectbox("TTS Lang", list(lmap.keys()))
        st.session_state.tts_lang = lmap[sel]

    st.markdown("<div class='sec-label'>THEME</div>", unsafe_allow_html=True)
    tcols = st.columns(5)
    tcolors = {"black":"#111","pink":"#ff6eb4","blue":"#38bdf8","green":"#4ade80","white":"#f0f0ee"}
    for i,(tn,tc) in enumerate(tcolors.items()):
        with tcols[i]:
            ring = "box-shadow:0 0 0 2px white,0 0 0 3px #0008;" if st.session_state.theme==tn else ""
            st.markdown(f"""<div style='width:24px;height:24px;border-radius:6px;background:{tc};
              border:1px solid {T['border']};{ring}'></div>""", unsafe_allow_html=True)
    tbcols = st.columns(5)
    for i,tn in enumerate(tcolors.keys()):
        with tbcols[i]:
            if st.button("▪", key=f"t_{tn}", help=tn):
                st.session_state.theme = tn; st.rerun()

    st.markdown("<div style='height:5px'></div>", unsafe_allow_html=True)
    cc1, cc2 = st.columns(2)
    with cc1:
        if st.button("RESET"):
            st.session_state.messages = []; st.session_state.chat_media = {}
            save_memory(st.session_state.user_email, []); st.rerun()
    with cc2:
        if st.button("LOGOUT"):
            save_memory(st.session_state.user_email, st.session_state.messages)
            st.session_state.authenticated = False
            st.session_state.user_email = None
            st.session_state.messages = []
            st.session_state.chat_media = {}
            st.rerun()

    st.markdown(f"""
    <div style='position:fixed;bottom:16px;left:0;width:268px;padding:0 14px;'>
      <div style='font-family:Space Mono,monospace;font-size:.44rem;
                  color:{T["text_dimmer"]};letter-spacing:2px;'>
        IRIS · gTTS · Browser STT · wttr.in · Google CSE
      </div>
    </div>""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# PAGE HEADER HELPER
# ─────────────────────────────────────────────────────────────────────────────
def page_header(title, sub=""):
    st.markdown(f"""
    <div class='main-wrap' style='padding-bottom:0;'>
      <div class='page-title'>{title}</div>
      {"<div style='font-family:Space Mono,monospace;font-size:.48rem;color:"+T['text_dimmer']+";letter-spacing:4px;text-transform:uppercase;'>"+sub+"</div>" if sub else ""}
      <div class='page-rule'></div>
    </div>""", unsafe_allow_html=True)

mod = st.session_state.active_module

# ─────────────────────────────────────────────────────────────────────────────
# ── CHAT MODULE ──────────────────────────────────────────────────────────────
# ─────────────────────────────────────────────────────────────────────────────
if mod == "chat":
    page_header("IRIS", "Smart Chat · Images · YouTube · Weather · Search · More")

    st.markdown(f"<div style='max-width:820px;margin:0 auto;padding:0 46px 8px;'>",
                unsafe_allow_html=True)

    # Empty state
    if not st.session_state.messages:
        h = datetime.datetime.now().hour
        greet = "Good morning" if h < 12 else "Good afternoon" if h < 17 else "Good evening"
        name = st.session_state.user_email.split("@")[0].capitalize()
        hints = ["🌤 weather in Delhi","▶ play Arijit Singh","🖼 show photos of Taj Mahal",
                 "🔍 latest IPL news","📖 define serendipity","🌐 translate hello in Hindi",
                 "💊 symptoms of cold","🧮 √256 + 3^4"]
        chips = "".join([
            f'<span style="background:{T["ub"]};border:1px solid {T["ubr"]};border-radius:20px;'
            f'padding:5px 13px;font-family:Space Mono,monospace;font-size:.58rem;'
            f'color:{T["text_dim"]};letter-spacing:.5px;">{h}</span>'
            for h in hints])
        st.markdown(f"""
        <div style='text-align:center;padding:40px 0 28px;'>
          <div style='font-family:Syne,sans-serif;font-size:3rem;font-weight:800;
                      letter-spacing:-4px;color:{T["border"]};user-select:none;margin-bottom:12px;'>
            READY
          </div>
          <div style='font-family:Figtree,sans-serif;font-size:.88rem;color:{T["text_dim"]};
                      margin-bottom:22px;'>
            {greet}, {name}. Ask me anything.
          </div>
          <div style='display:flex;flex-wrap:wrap;gap:7px;justify-content:center;'>{chips}</div>
        </div>""", unsafe_allow_html=True)

    # Render message history + associated media
    for idx, msg in enumerate(st.session_state.messages):
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            # Re-render media attached to this message
            media = st.session_state.chat_media.get(idx)
            if media:
                mtype = media.get("type")
                if mtype == "images":
                    render_image_grid(media["imgs"], media.get("query",""))
                elif mtype == "youtube":
                    render_yt_cards(media["videos"])
                elif mtype == "weather_card":
                    render_weather_card(media["data"])

    st.markdown("</div>", unsafe_allow_html=True)

    # Mic button — browser STT
    mic_button("iris-chat-mic", is_chat=True)

    # Chat input
    if prompt := st.chat_input("Ask IRIS — weather, images, YouTube, search, translate…"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            ph = st.empty()
            try:
                text_resp, media_type, media_data = handle_intent(prompt, ph)

                # Render media inline right after the text
                if media_type == "images":
                    render_image_grid(media_data["imgs"], media_data.get("query",""))
                elif media_type == "youtube":
                    render_yt_cards(media_data["videos"])
                elif media_type == "weather_card":
                    render_weather_card(media_data)

                # Save message + attach media reference by index
                msg_idx = len(st.session_state.messages)
                st.session_state.messages.append({"role": "assistant", "content": text_resp})

                if media_type == "images":
                    st.session_state.chat_media[msg_idx] = {
                        "type": "images", "imgs": media_data["imgs"],
                        "query": media_data.get("query","")}
                elif media_type == "youtube":
                    st.session_state.chat_media[msg_idx] = {
                        "type": "youtube", "videos": media_data["videos"],
                        "query": media_data.get("query","")}
                elif media_type == "weather_card":
                    st.session_state.chat_media[msg_idx] = {
                        "type": "weather_card", "data": media_data}

                save_memory(st.session_state.user_email, st.session_state.messages)

                # gTTS speak
                speak(text_resp, lang=st.session_state.tts_lang)

            except Exception as e:
                ph.error(f"ERROR — {e}")


# ─────────────────────────────────────────────────────────────────────────────
# ── DEDICATED MODULES ────────────────────────────────────────────────────────
# ─────────────────────────────────────────────────────────────────────────────
elif mod == "search":
    page_header("WEB SEARCH", "Google Custom Search API")
    st.markdown("<div class='main-wrap'>", unsafe_allow_html=True)
    with st.form("sf2"):
        q = st.text_input("Search Query", placeholder="Latest news, sports, technology…")
        c1,c2,c3 = st.columns([3,1,1])
        with c1: num = st.slider("Results",3,10,5)
        with c2: sub = st.form_submit_button("🔍 SEARCH")
        with c3: mic_button("mic-search")
    if sub and q:
        with st.spinner("Searching…"):
            results, err = google_search(q, num=num)
        if err: st.error(err)
        else:
            summary = llm_quick(f"Summarize in 2 sentences about '{q}':\n"+"\n".join([r['snippet'] for r in results[:4]]))
            st.markdown(f"<div class='mcard'><div class='mcard-title'>AI SUMMARY</div>"
                        f"<div class='mcard-sub'>Gemini + Google</div>"
                        f"<div class='result-text'>{summary}</div></div>", unsafe_allow_html=True)
            speak(summary, lang=st.session_state.tts_lang)
            for r in results:
                st.markdown(f"""<div class='mcard' style='margin-bottom:8px;'>
                  <div class='mcard-title'>
                    <a href='{r["link"]}' target='_blank' style='color:{T["accent"]};text-decoration:none;'>{r["title"]}</a>
                  </div>
                  <div style='font-family:Space Mono,monospace;font-size:.48rem;
                              color:{T["text_dimmer"]};margin-bottom:5px;'>{r["link"][:65]}…</div>
                  <div class='result-text'>{r["snippet"]}</div>
                </div>""", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

elif mod == "images":
    page_header("IMAGE SEARCH", "Google Custom Search · Image Mode")
    st.markdown("<div class='main-wrap'>", unsafe_allow_html=True)
    with st.form("imgf2"):
        q = st.text_input("Search Images", placeholder="Mumbai skyline, Bengal tiger, Taj Mahal…")
        c1,c2,c3 = st.columns([3,1,1])
        with c1: num = st.slider("Images",4,10,6)
        with c2: sub = st.form_submit_button("🖼 SEARCH")
        with c3: mic_button("mic-images")
    if sub and q:
        with st.spinner("Fetching images…"):
            imgs, err = google_image_search(q, num=num)
        if err:
            st.error(err)
            st.info("Make sure Image Search is enabled in your CSE settings.")
        else:
            render_image_grid(imgs, q)
    st.markdown("</div>", unsafe_allow_html=True)

elif mod == "youtube":
    page_header("YOUTUBE", "YouTube Data API v3")
    st.markdown("<div class='main-wrap'>", unsafe_allow_html=True)
    with st.form("ytf2"):
        q = st.text_input("Search…", placeholder="lofi music, Python tutorial, cricket highlights…")
        c1,c2,c3,c4 = st.columns([2,1,1,1])
        with c1: stype = st.selectbox("Type",["video","playlist"])
        with c2: num = st.slider("Results",2,8,4)
        with c3: sub = st.form_submit_button("▶ SEARCH")
        with c4: mic_button("mic-yt")
    if sub and q:
        with st.spinner("Searching YouTube…"):
            results, err = youtube_search(q, max_results=num, search_type=stype)
        if err:
            st.error(err)
            st.markdown(f"[🔗 Open YouTube Search](https://youtube.com/results?search_query={urllib.parse.quote(q)})")
        else:
            render_yt_cards(results)
    st.markdown("</div>", unsafe_allow_html=True)

elif mod == "weather":
    page_header("WEATHER", "wttr.in · Live · India + Global")
    st.markdown("<div class='main-wrap'>", unsafe_allow_html=True)
    with st.form("wf2"):
        c1,c2,c3 = st.columns([2,1,1])
        with c1: city = st.text_input("City", placeholder="Mumbai, Delhi, Bengaluru, Chennai, Pune…")
        with c2: unit = st.selectbox("Unit",["Celsius","Fahrenheit"])
        with c3: 
            sub = st.form_submit_button("🌤 GET WEATHER")
            mic_button("mic-weather")
    if sub and city:
        with st.spinner("Fetching…"):
            w, err = get_weather(city, "imperial" if unit=="Fahrenheit" else "metric")
        if err: st.error(err)
        else:
            render_weather_card(w)
            speak(f"Weather in {w['city']}: {w['desc']}, {w['temp']}. Feels like {w['feels']}.",
                  lang=st.session_state.tts_lang)
    st.markdown("</div>", unsafe_allow_html=True)

elif mod == "dictionary":
    page_header("DICTIONARY", "Definitions · Etymology · Examples")
    st.markdown("<div class='main-wrap'>", unsafe_allow_html=True)
    with st.form("df2"):
        c1,c2,c3 = st.columns([2,1,1])
        with c1: word = st.text_input("Word", placeholder="ephemeral, serendipity, jugaad…")
        with c2: lang = st.selectbox("Language",["English","Hindi","Spanish","French","German",
                                                  "Japanese","Arabic","Tamil","Telugu","Urdu"])
        with c3: 
            sub = st.form_submit_button("📖 DEFINE")
            mic_button("mic-dict")
    if sub and word:
        with st.spinner("Looking up…"):
            result = llm_quick(
                f"Define '{word}' in {lang}: 1) phonetics 2) part of speech "
                f"3) definition(s) 4) etymology 5) 3 example sentences. Use clear formatting.",
                "You are a precise scholarly dictionary.")
        st.markdown(f"<div class='mcard'><div class='mcard-title'>{word.upper()}</div>"
                    f"<div class='mcard-sub'>{lang} · Definition</div>"
                    f"<div class='result-text' style='white-space:pre-wrap;'>{result}</div></div>",
                    unsafe_allow_html=True)
        speak(result[:500], lang=st.session_state.tts_lang)
    st.markdown("</div>", unsafe_allow_html=True)

elif mod == "health":
    page_header("HEALTH & MEDICINE", "General Info · Not Medical Advice")
    st.markdown("<div class='main-wrap'>", unsafe_allow_html=True)
    st.info("⚠️ For general information only. Always consult a qualified doctor.")
    with st.form("hf2"):
        c1, c2 = st.columns([1,1])
        with c1:
            qtype = st.selectbox("Query Type",["Symptom Checker","Medicine Information",
                                                "Health Tips","First Aid","Diet & Nutrition"])
        with c2:
            sub = st.form_submit_button("💊 GET INFORMATION")
            mic_button("mic-health")
        query = st.text_area("Describe your query",
                             placeholder="e.g. mild fever and body ache for 2 days…", height=80)
    sysp = {
        "Symptom Checker": "Analyze symptoms: list possible conditions, severity flags, home care, when to see doctor.",
        "Medicine Information": "Drug class, uses, dosages (general), side effects, contraindications, interactions. Not medical advice.",
        "Health Tips": "Evidence-based lifestyle, diet, exercise, sleep tips. Be specific and practical.",
        "First Aid": "Step-by-step first aid. Prioritize immediate actions. State when to call 108/911.",
        "Diet & Nutrition": "Nutritional guidance, food recommendations. Include Indian dietary context.",
    }
    if sub and query:
        with st.spinner("Analyzing…"):
            result = llm_quick(query, system=sysp[qtype])
        st.markdown(f"<div class='mcard'><div class='mcard-title'>{qtype.upper()}</div>"
                    f"<div class='mcard-sub'>General Information · Consult a Doctor</div>"
                    f"<div class='result-text'>{result}</div></div>", unsafe_allow_html=True)
        speak(result[:500], lang=st.session_state.tts_lang)
    st.markdown("</div>", unsafe_allow_html=True)

elif mod == "calculator":
    page_header("CALCULATOR", "Math · Expressions · Word Problems")
    st.markdown("<div class='main-wrap'>", unsafe_allow_html=True)
    with st.form("cf2"):
        c1, c2 = st.columns([3, 1])
        with c1:
            expr = st.text_input("Expression or Problem",
                                 placeholder="2^10 + sqrt(144)  or  compound interest 5000 at 8% for 3 years")
        with c2:
            sub = st.form_submit_button("🧮 CALCULATE")
            mic_button("mic-calc")
    if sub and expr:
        val = None
        try:
            import math as _m
            safe = expr.replace("^","**").replace("sqrt","_m.sqrt").replace("pi","_m.pi")
            val = eval(safe, {"__builtins__":{},"_m":_m})
        except: pass
        if val is not None:
            st.markdown(f"<div class='mcard'><div class='mcard-title'>RESULT</div>"
                        f"<div class='mcard-sub'>Direct Eval</div>"
                        f"<div class='big-num'>{val}</div>"
                        f"<div style='font-family:Space Mono,monospace;font-size:.58rem;"
                        f"color:{T['text_dim']};margin-top:8px;'>{expr}</div></div>",
                        unsafe_allow_html=True)
            speak(f"The answer is {val}", lang=st.session_state.tts_lang)
        else:
            with st.spinner("Solving…"):
                result = llm_quick(f"Solve step by step: {expr}. Show all working.",
                                   "You are a precise math tutor.")
            st.markdown(f"<div class='mcard'><div class='mcard-title'>SOLUTION</div>"
                        f"<div class='mcard-sub'>Step-by-Step · AI</div>"
                        f"<div class='result-text' style='white-space:pre-wrap;'>{result}</div></div>",
                        unsafe_allow_html=True)
            speak(result[:300], lang=st.session_state.tts_lang)
    st.markdown("</div>", unsafe_allow_html=True)

elif mod == "translator":
    page_header("TRANSLATOR", "20+ Languages · Pronunciation")
    st.markdown("<div class='main-wrap'>", unsafe_allow_html=True)
    LANGS = ["English","Hindi","Spanish","French","German","Japanese","Chinese (Mandarin)",
             "Arabic","Portuguese","Russian","Korean","Italian","Dutch","Turkish","Bengali",
             "Urdu","Tamil","Telugu","Gujarati","Marathi","Punjabi","Kannada","Malayalam"]
    LANG_TTS = {"English":"en","Hindi":"hi","Spanish":"es","French":"fr","German":"de",
                "Japanese":"ja","Chinese (Mandarin)":"zh","Arabic":"ar","Portuguese":"pt",
                "Russian":"ru","Korean":"ko","Italian":"it","Bengali":"bn","Tamil":"ta",
                "Telugu":"te","Gujarati":"gu","Marathi":"mr"}
    with st.form("tf2"):
        text_in = st.text_area("Text to Translate", placeholder="Type in any language…", height=90)
        c1,c2,c3 = st.columns([1,1,1])
        with c1: src = st.selectbox("From",["Auto-detect"]+LANGS)
        with c2: tgt = st.selectbox("To",LANGS,index=1)
        with c3: 
            sub = st.form_submit_button("🌐 TRANSLATE")
            mic_button("mic-trans")
    if sub and text_in:
        with st.spinner("Translating…"):
            src_note = f"from {src}" if src!="Auto-detect" else "(auto-detect)"
            result = llm_quick(
                f"Translate {src_note} to {tgt}:\n\n{text_in}\n\nReturn ONLY the translation.",
                "You are a professional translator.")
        st.markdown(f"""<div class='mcard'>
          <div class='mcard-title'>TRANSLATION</div>
          <div class='mcard-sub'>{src if src!='Auto-detect' else 'Auto'} → {tgt}</div>
          <div style='font-family:Figtree,sans-serif;font-size:1rem;
                      color:{T['title']};line-height:1.7;margin-top:8px;'>{result}</div>
        </div>""", unsafe_allow_html=True)
        tgt_tts = LANG_TTS.get(tgt, "en")
        speak(result[:500], lang=tgt_tts)
        if tgt in ["Japanese","Chinese (Mandarin)","Arabic","Hindi","Tamil","Telugu",
                   "Marathi","Gujarati","Bengali","Urdu","Kannada","Malayalam"]:
            pron = llm_quick(f"Romanized pronunciation only of: {result[:200]}",
                             "Give only romanized pronunciation, nothing else.")
            st.markdown(f"<div class='mcard' style='margin-top:6px;'>"
                        f"<div class='mcard-sub'>PRONUNCIATION</div>"
                        f"<div style='font-family:Space Mono,monospace;font-size:.72rem;"
                        f"color:{T['text_dim']};line-height:1.8;'>{pron}</div></div>",
                        unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)