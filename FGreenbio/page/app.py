# streamlit_app.py
import html
import uuid
from dataclasses import dataclass
from datetime import datetime
import streamlit as st
import streamlit.components.v1 as components
from streamlit_float import float_init

st.set_page_config(page_title="ClimateBot", page_icon="🌿", layout="wide")
float_init()

# =========================
# Layout constants
# =========================
CHAT_HEIGHT = 1000
CHAT_WIDTH = 850

PROMPT_BOTTOM = 16
PROMPT_EST_H = 72
CHAT_BOTTOM_PAD = PROMPT_BOTTOM + PROMPT_EST_H + 18

# =========================
# ✅ 서버 메모리(사용자별) 저장소: 채팅 내역 + 채팅별 메시지 유지용
# =========================
@st.cache_resource
def get_user_store():
    # { user_id: { "history": [...], "chats": { chat_id: [messages...] } } }
    return {}

def get_history(user_id: str):
    store = get_user_store()
    if user_id not in store:
        store[user_id] = {"history": [], "chats": {}}
    if "history" not in store[user_id]:
        store[user_id]["history"] = []
    if "chats" not in store[user_id]:
        store[user_id]["chats"] = {}
    return store[user_id]["history"]

def add_history_item(user_id: str, title: str = "(새 채팅)"):
    hist = get_history(user_id)
    item_id = str(uuid.uuid4())[:8]
    hist.append(
        {
            "id": item_id,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "title": title,
        }
    )
    return item_id

def update_history_title(user_id: str, item_id: str, new_title: str):
    hist = get_history(user_id)
    for it in hist:
        if it["id"] == item_id:
            it["title"] = new_title
            return

def delete_history_item(user_id: str, item_id: str):
    store = get_user_store()
    hist = get_history(user_id)
    store[user_id]["history"] = [it for it in hist if it["id"] != item_id]
    # ✅ 채팅 메시지도 같이 삭제
    if "chats" in store.get(user_id, {}):
        store[user_id]["chats"].pop(item_id, None)

# ✅ 채팅별 메시지 로드/저장
def get_chat_messages(user_id: str, chat_id: str):
    store = get_user_store()
    if user_id not in store:
        store[user_id] = {"history": [], "chats": {}}
    if "chats" not in store[user_id]:
        store[user_id]["chats"] = {}

    chats = store[user_id]["chats"]
    if chat_id not in chats:
        chats[chat_id] = [
            {"role": "assistant", "content": "안녕하세요! 저는 Greenbio Chat 🌿 입니다. 현재 상태를 보고 제어/진단을 도와드릴게요."}
        ]
    return chats[chat_id]

def set_chat_messages(user_id: str, chat_id: str, messages):
    store = get_user_store()
    if user_id not in store:
        store[user_id] = {"history": [], "chats": {}}
    if "chats" not in store[user_id]:
        store[user_id]["chats"] = {}
    store[user_id]["chats"][chat_id] = messages

# =========================
# ✅ (추가) 헤더 앵커(#xxxx) 방지 JS
# - Streamlit 헤더의 🔗 아이콘 클릭으로 URL 뒤에 #xxxx 붙는 현상 방지
# =========================
components.html(
    """
    <script>
    (function () {
      // 페이지 로드시 해시가 이미 붙어있으면 제거
      if (window.location.hash && window.location.hash.length > 1) {
        history.replaceState(null, "", window.location.pathname + window.location.search);
      }

      // 헤더 action 영역의 a[href^="#"] 클릭을 차단
      document.addEventListener("click", function(e){
        const a = e.target.closest('a[href^="#"]');
        if (!a) return;

        const inHeaderAction = a.closest('span[data-testid="stHeaderActionElements"]');
        if (inHeaderAction) {
          e.preventDefault();
          e.stopPropagation();
          history.replaceState(null, "", window.location.pathname + window.location.search);
        }
      }, true);
    })();
    </script>
    """,
    height=0,
)

# =========================
# CSS
# =========================
st.markdown(
    f"""
<style>
html, body {{
  height: 100%;
  overflow: hidden !important;
}}
.stApp {{
  height: 100vh;
  overflow: hidden !important;
}}

[data-testid="stToolbar"] {{visibility:hidden; height:0;}}
header {{visibility:hidden; height:0;}}

.block-container {{
  max-width: 1400px;
  padding-top: 0.8rem;
  height: 100vh;
  overflow: hidden !important;
}}

/* ✅ (추가) Streamlit 헤더 오른쪽 "앵커(🔗)" 아이콘 자체 숨김 */
span[data-testid="stHeaderActionElements"] {{
  display: none !important;
}}

/* ✅ 상단바 */
.topbar{{
  display:flex;
  align-items:center;
  justify-content:space-between;
  padding: 14px 18px;
  border-radius: 16px;
  background: #2f3f2a;
  color: #fff;
  margin-bottom: 12px;
}}
.brand{{font-weight:800; letter-spacing:0.5px;}}

/* ✅ 상단바 오른쪽 로그인 UI */
.topbar-right{{
  display:flex;
  align-items:center;
  justify-content:flex-end;
  gap:10px;
}}
.topbar-user{{
  font-size:12px;
  opacity:0.95;
}}
.topbar-btn{{
  background: rgba(255,255,255,0.14);
  border: 1px solid rgba(255,255,255,0.22);
  color: white;
  padding: 7px 12px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 800;
  cursor: pointer;
}}
.topbar-btn:hover{{
  background: rgba(255,255,255,0.22);
}}

.card{{
  background:#f6f7f9;
  border:1px solid #e9eaee;
  border-radius:16px;
  padding:14px 14px;
  margin-bottom:10px;
}}

.card h4{{
  margin:0 0 10px 0;
  font-size:14px;
  text-align:center;
}}

.kv{{display:flex; justify-content:space-between; padding:8px 0; border-bottom:1px dashed #e1e3e8;}}
.kv:last-child{{border-bottom:none;}}
.k{{color:#555; font-size:13px;}}
.v{{font-weight:700;}}

.badge-ok{{background:#e9f7ef; color:#1e7a3a; padding:4px 10px; border-radius:999px; font-size:12px; font-weight:700;}}
.badge-warn{{background:#fff4e5; color:#9a5b00; padding:4px 10px; border-radius:999px; font-size:12px; font-weight:700;}}
.badge-bad{{background:#fdecea; color:#b42318; padding:4px 10px; border-radius:999px; font-size:12px; font-weight:700;}}

.fixed-input{{
  background: rgba(255,255,255,0.92);
  backdrop-filter: blur(6px);
  border: 1px solid #ececec;
  border-radius: 14px;
  padding: 10px 12px;
}}

/* ✅ 업로드된 파일 카드(파일명/용량/X) 전체 숨기기 */
div[data-testid="stFileUploader"] [data-testid="stFileUploaderFile"] {{
  display: none !important;
}}
/* ✅ 업로드 후 Streamlit이 만드는 "파일 카드 리스트" 숨기기 */
div[data-testid="stFileUploader"] ul {{
  display: none !important;
}}
div[data-testid="stFileUploader"] li {{
  display: none !important;
}}
div[data-testid="stFileUploader"] [data-testid="stFileUploaderFile"] {{
  display: none !important;
}}

.gh-panel{{
  background:#ffffff;
  border:1px solid #ececec;
  border-radius:18px;
  padding:14px;
}}

.gh-pill{{
  display:block;
  width:100%;
  text-align:center;
  padding: 10px 14px;
  border-radius: 999px;
  background:#eef0f2;
  border:1px solid #e3e6ea;
  font-weight:800;
  font-size:12px;
  color:#333;
  margin-bottom: 10px;
}}

/* ✅ 우측 “채팅 내역 / 업로드 문서” 카드 */
.rp-card{{
  background:#ffffff;
  border:1px solid #ececec;
  border-radius:18px;
  padding:14px;
  margin-bottom:10px;
}}
.rp-title{{
  display:block;
  width:100%;
  text-align:center;
  padding: 10px 14px;
  border-radius: 999px;
  background:#eef0f2;
  border:1px solid #e3e6ea;
  font-weight:800;
  font-size:12px;
  color:#333;
  margin-bottom: 10px;
}}

/* ✅ X 버튼 “하얀 박스” 제거 */
div[data-testid="stButton"] > button {{
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
}}
div[data-testid="stButton"] > button:hover {{
  background: rgba(0,0,0,0.06) !important;
}}
div[data-testid="stButton"] > button:active {{
  background: rgba(0,0,0,0.10) !important;
}}
</style>
""",
    unsafe_allow_html=True,
)

# =========================
# Data models
# =========================
@dataclass
class SensorSnapshot:
    temp_c: float
    humidity: float
    light_lux: int
    co2_ppm: int
    received_at: datetime

@dataclass
class Targets:
    temp_min: float = 20.0
    temp_max: float = 26.0
    hum_min: float = 55.0
    hum_max: float = 75.0
    co2_min: int = 600
    co2_max: int = 1200
    light_min: int = 8000
    light_max: int = 25000

GREENHOUSES = {
    "1번 온실": {
        "targets": Targets(temp_min=20, temp_max=26, hum_min=55, hum_max=75, co2_min=600, co2_max=1200, light_min=8000, light_max=25000),
        "snapshot": dict(temp_c=24.3, humidity=68.0, light_lux=12000, co2_ppm=980),
    },
    "2번 온실": {
        "targets": Targets(temp_min=18, temp_max=24, hum_min=60, hum_max=85, co2_min=700, co2_max=1400, light_min=6000, light_max=22000),
        "snapshot": dict(temp_c=26.8, humidity=52.0, light_lux=16000, co2_ppm=1550),
    },
    "3번 온실": {
        "targets": Targets(temp_min=22, temp_max=28, hum_min=50, hum_max=70, co2_min=500, co2_max=1000, light_min=10000, light_max=30000),
        "snapshot": dict(temp_c=21.2, humidity=74.0, light_lux=9000, co2_ppm=720),
    },
    "4번 온실": {
        "targets": Targets(temp_min=16, temp_max=22, hum_min=45, hum_max=65, co2_min=600, co2_max=1100, light_min=4000, light_max=18000),
        "snapshot": dict(temp_c=19.5, humidity=66.0, light_lux=3500, co2_ppm=1050),
    },
}

def fetch_greenhouse_snapshot(gname: str) -> SensorSnapshot:
    now = datetime.now()
    s = GREENHOUSES[gname]["snapshot"]
    return SensorSnapshot(
        temp_c=float(s["temp_c"]),
        humidity=float(s["humidity"]),
        light_lux=int(s["light_lux"]),
        co2_ppm=int(s["co2_ppm"]),
        received_at=now,
    )

def get_greenhouse_targets(gname: str) -> Targets:
    return GREENHOUSES[gname]["targets"]

def judge(value, lo, hi) -> str:
    if lo <= value <= hi:
        return "ok"
    margin = (hi - lo) * 0.2 if (hi - lo) != 0 else 1
    if (lo - margin) <= value <= (hi + margin):
        return "warn"
    return "bad"

def badge_html(level: str, text: str) -> str:
    cls = {"ok": "badge-ok", "warn": "badge-warn", "bad": "badge-bad"}[level]
    return f'<span class="{cls}">{text}</span>'

# =========================
# Session state
# =========================
if "greenhouse" not in st.session_state:
    st.session_state.greenhouse = "1번 온실"

if "uploaded_files" not in st.session_state:
    st.session_state.uploaded_files = []

if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = "uploader_docs_0"

# ✅ 로그인 상태
if "auth_logged_in" not in st.session_state:
    st.session_state.auth_logged_in = False
if "auth_user" not in st.session_state:
    st.session_state.auth_user = ""

# ✅ "현재 채팅 세션(기록용)" 관리
if "active_chat_item_id" not in st.session_state:
    st.session_state.active_chat_item_id = None
if "first_user_recorded" not in st.session_state:
    st.session_state.first_user_recorded = False

def reset_messages():
    st.session_state.messages = [
        {"role": "assistant", "content": "안녕하세요! 저는 ClimateBot 🌿 입니다. 현재 상태를 보고 제어/진단을 도와드릴게요."}
    ]

if "messages" not in st.session_state:
    reset_messages()

# =========================
# Top bar (로그인/로그아웃)
# =========================
snap = fetch_greenhouse_snapshot(st.session_state.greenhouse)

top_l, top_r = st.columns([6, 2], vertical_alignment="top")

with top_l:
    st.markdown(
        """
        <div class="topbar" style="justify-content:flex-start; margin-bottom: 6px;">
          <div class="brand">GreenBio Chatbot</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with top_r:
    st.markdown("<div style='height:0px; margin:0; padding:0;'></div>", unsafe_allow_html=True)

    if st.session_state.auth_logged_in and st.session_state.auth_user:
        st.markdown(
            f"""
            <div style="text-align:right; font-size:12px; margin-top:-6px; margin-bottom:6px; opacity:0.95;">
              👤 {html.escape(st.session_state.auth_user)}
            </div>
            """,
            unsafe_allow_html=True,
        )

    if not st.session_state.auth_logged_in:
        with st.popover("로그인", use_container_width=True):
            uid = st.text_input("아이디", key="login_uid")
            pw = st.text_input("비밀번호", type="password", key="login_pw")
            if st.button("로그인", use_container_width=True, key="do_login"):
                if uid.strip():
                    st.session_state.auth_logged_in = True
                    st.session_state.auth_user = uid.strip()

                    item_id = add_history_item(st.session_state.auth_user, title="(새 채팅)")
                    st.session_state.active_chat_item_id = item_id
                    st.session_state.first_user_recorded = False

                    st.session_state.messages = get_chat_messages(st.session_state.auth_user, st.session_state.active_chat_item_id)
                    st.rerun()
                else:
                    st.warning("아이디를 입력하세요.")
    else:
        with st.popover("로그아웃", use_container_width=True):
            if st.button("로그아웃", use_container_width=True, key="do_logout"):
                st.session_state.auth_logged_in = False
                st.session_state.auth_user = ""
                st.session_state.active_chat_item_id = None
                st.session_state.first_user_recorded = False
                reset_messages()
                st.rerun()

# ✅ 새로고침 등으로 active id가 날아갔으면 새 채팅 항목 생성 + messages 로드
if st.session_state.auth_logged_in and st.session_state.active_chat_item_id is None:
    item_id = add_history_item(st.session_state.auth_user, title="(새 채팅)")
    st.session_state.active_chat_item_id = item_id
    st.session_state.first_user_recorded = False
    st.session_state.messages = get_chat_messages(st.session_state.auth_user, st.session_state.active_chat_item_id)

# ✅ 로그인 상태이면 현재 active 채팅의 messages를 항상 동기화(중요)
if st.session_state.auth_logged_in and st.session_state.active_chat_item_id is not None:
    st.session_state.messages = get_chat_messages(st.session_state.auth_user, st.session_state.active_chat_item_id)

# =========================
# Layout: left / center / right
# =========================
col_left, col_mid, col_right = st.columns([1.05, 3.0, 1.05], gap="large")

# -------- Left
with col_left:
    targets = get_greenhouse_targets(st.session_state.greenhouse)

    t_lv = judge(snap.temp_c, targets.temp_min, targets.temp_max)
    h_lv = judge(snap.humidity, targets.hum_min, targets.hum_max)
    c_lv = judge(snap.co2_ppm, targets.co2_min, targets.co2_max)
    l_lv = judge(snap.light_lux, targets.light_min, targets.light_max)

    st.markdown('<div class="card"><h4>현재 상태</h4>', unsafe_allow_html=True)
    st.markdown(f'<div class="kv"><div class="k">온도</div><div class="v">{snap.temp_c:.1f}°C</div></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="kv"><div class="k">습도</div><div class="v">{snap.humidity:.0f}%</div></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="kv"><div class="k">광량</div><div class="v">{snap.light_lux:,} lux</div></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="kv"><div class="k">CO₂</div><div class="v">{snap.co2_ppm:,} ppm</div></div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="card"><h4>제어 상태</h4>', unsafe_allow_html=True)
    st.markdown(f'<div class="kv"><div class="k">온도</div><div class="v">{badge_html(t_lv, "적정" if t_lv=="ok" else ("경고" if t_lv=="warn" else "위험"))}</div></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="kv"><div class="k">습도</div><div class="v">{badge_html(h_lv, "적정" if h_lv=="ok" else ("경고" if h_lv=="warn" else "위험"))}</div></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="kv"><div class="k">CO₂</div><div class="v">{badge_html(c_lv, "적정" if c_lv=="ok" else ("경고" if c_lv=="warn" else "위험"))}</div></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="kv"><div class="k">광량</div><div class="v">{badge_html(l_lv, "적정" if l_lv=="ok" else ("경고" if l_lv=="warn" else "위험"))}</div></div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    with st.expander("목표 범위(선택된 온실 기준)"):
        st.write(f"온도: {targets.temp_min} ~ {targets.temp_max} °C")
        st.write(f"습도: {targets.hum_min} ~ {targets.hum_max} %")
        st.write(f"CO₂: {targets.co2_min} ~ {targets.co2_max} ppm")
        st.write(f"광량: {targets.light_min} ~ {targets.light_max} lux")

    st.markdown('<div class="gh-pill">온실 선택</div>', unsafe_allow_html=True)

    c1, c2 = st.columns(2, gap="small")
    with c1:
        if st.button("1번 온실", use_container_width=True, key="gh_left_1"):
            st.session_state.greenhouse = "1번 온실"
            st.rerun()
        if st.button("3번 온실", use_container_width=True, key="gh_left_3"):
            st.session_state.greenhouse = "3번 온실"
            st.rerun()
    with c2:
        if st.button("2번 온실", use_container_width=True, key="gh_left_2"):
            st.session_state.greenhouse = "2번 온실"
            st.rerun()
        if st.button("4번 온실", use_container_width=True, key="gh_left_4"):
            st.session_state.greenhouse = "4번 온실"
            st.rerun()

    st.caption(f"현재 선택: **{st.session_state.greenhouse}**")
    st.markdown("</div>", unsafe_allow_html=True)

# -------- Middle: 채팅
with col_mid:
    bubbles = []
    for m in st.session_state.messages:
        role = m["role"]
        content = html.escape(m["content"]).replace("\n", "<br/>")

        if role == "user":
            bubbles.append(
                f"""
            <div style="display:flex; justify-content:flex-end; margin:10px 0;">
              <div style="max-width:78%; background:#ffffff; border:1px solid #ececec;
                          border-radius:16px; padding:12px 14px;">
                {content}
              </div>
            </div>"""
            )
        else:
            bubbles.append(
                f"""
            <div style="display:flex; justify-content:flex-start; gap:10px; margin:10px 0;">
              <div style="width:30px; height:30px; border-radius:10px; background:#2f3f2a;
                          color:white; display:flex; align-items:center; justify-content:center; font-weight:800;">
                C
              </div>
              <div style="max-width:78%; background:#fbf5ea; border:1px solid #efe2c9;
                          border-radius:16px; padding:12px 14px;">
                {content}
              </div>
            </div>"""
            )

    chat_html = f"""
    <div style="display:flex; justify-content:center;">
      <div id="chatbox" style="
        width: {CHAT_WIDTH}px;
        height: {CHAT_HEIGHT}px;
        overflow-y: auto;
        padding: 6px 8px {CHAT_BOTTOM_PAD}px 8px;
        box-sizing: border-box;
      ">
        {''.join(bubbles)}
      </div>
    </div>
    <script>
      const el = document.getElementById("chatbox");
      if (el) el.scrollTop = el.scrollHeight;
    </script>
    """
    components.html(chat_html, height=CHAT_HEIGHT + 20, scrolling=False)

    input_box = st.container()
    with input_box:
        with st.form("chat_form", clear_on_submit=True):
            user_text = st.text_input(
                "",
                placeholder=f"({st.session_state.greenhouse}) 상태를 물어보거나 제어를 요청해보세요…",
                label_visibility="collapsed",
            )
            sent = st.form_submit_button("전송")
        st.markdown("</div>", unsafe_allow_html=True)

    input_box.float(
        f"position: fixed; bottom: {PROMPT_BOTTOM}px; left: 50%; "
        f"transform: translateX(-50%); width: {CHAT_WIDTH}px; z-index: 999;"
    )

    if sent and user_text.strip():
        st.session_state.messages.append(
            {"role": "user", "content": f"[{st.session_state.greenhouse}] {user_text.strip()}"}
        )

        if (
            st.session_state.auth_logged_in
            and not st.session_state.first_user_recorded
            and st.session_state.active_chat_item_id is not None
        ):
            title = user_text.strip().replace("\n", " ")
            if len(title) > 28:
                title = title[:28] + "…"
            update_history_title(st.session_state.auth_user, st.session_state.active_chat_item_id, title)
            st.session_state.first_user_recorded = True

        targets = get_greenhouse_targets(st.session_state.greenhouse)
        t_lv = judge(snap.temp_c, targets.temp_min, targets.temp_max)
        h_lv = judge(snap.humidity, targets.hum_min, targets.hum_max)
        c_lv = judge(snap.co2_ppm, targets.co2_min, targets.co2_max)
        l_lv = judge(snap.light_lux, targets.light_min, targets.light_max)

        tips = []
        if t_lv != "ok": tips.append("온도 조정(냉난방/환기) 필요")
        if h_lv != "ok": tips.append("가습/제습 또는 환기 필요")
        if c_lv != "ok": tips.append("환기(급기/배기) 권장")
        if l_lv != "ok": tips.append("조명(광량) 조절 권장")
        if not tips: tips.append("전체적으로 목표 범위 내입니다 ✅")

        reply = (
            f"""**{st.session_state.greenhouse}** 기준으로 요약해드릴게요.

- 온도: {snap.temp_c:.1f}°C / 습도: {snap.humidity:.0f}%
- CO₂: {snap.co2_ppm:,} ppm / 광량: {snap.light_lux:,} lux

추천 조치:
- """
            + "\n- ".join(tips)
        )

        st.session_state.messages.append({"role": "assistant", "content": reply})

        # ✅ 메시지 저장(채팅방별 유지)
        if st.session_state.auth_logged_in and st.session_state.active_chat_item_id is not None:
            set_chat_messages(st.session_state.auth_user, st.session_state.active_chat_item_id, st.session_state.messages)

        st.rerun()

# -------- Right: 채팅 내역(스크롤) + 업로드 문서
with col_right:
    st.markdown('<div class="rp-title">채팅 내역</div>', unsafe_allow_html=True)

    history_box = st.container(height=320)
    with history_box:
        if not st.session_state.auth_logged_in:
            st.caption("로그인하면 채팅 내역이 저장됩니다.")
        else:
            hist = list(reversed(get_history(st.session_state.auth_user)))

            if not hist:
                st.caption("아직 채팅 내역이 없습니다.")
            else:
                for it in hist:
                    left, right = st.columns([0.86, 0.14], vertical_alignment="center")

                    with left:
                        is_active = (st.session_state.active_chat_item_id == it["id"])
                        prefix = "✅ " if is_active else "• "

                        if st.button(f"{prefix}{it['title']}", key=f"open_hist_{it['id']}", use_container_width=True):
                            st.session_state.active_chat_item_id = it["id"]
                            st.session_state.first_user_recorded = True
                            st.session_state.messages = get_chat_messages(st.session_state.auth_user, it["id"])
                            st.rerun()

                    with right:
                        if st.button("✕", key=f"del_hist_{it['id']}", use_container_width=True):
                            delete_history_item(st.session_state.auth_user, it["id"])
                            if st.session_state.active_chat_item_id == it["id"]:
                                st.session_state.active_chat_item_id = None
                                st.session_state.first_user_recorded = False
                                reset_messages()
                            st.rerun()

    if st.session_state.auth_logged_in:
        if st.button("＋ 새 채팅", use_container_width=True, key="btn_new_chat"):
            new_id = add_history_item(st.session_state.auth_user, title="(새 채팅)")
            st.session_state.active_chat_item_id = new_id
            st.session_state.first_user_recorded = False
            st.session_state.messages = get_chat_messages(st.session_state.auth_user, new_id)
            st.rerun()
    else:
        st.caption("새 채팅은 로그인 후 사용할 수 있어요.")

    st.markdown("</div>", unsafe_allow_html=True)

    # ----------------------------
    # ✅ 업로드 문서 (오른쪽)
    # ----------------------------
    if "uploaded_files" not in st.session_state:
        st.session_state.uploaded_files = []
    if "uploaded_file_blobs" not in st.session_state:
        st.session_state.uploaded_file_blobs = {}
    if "uploader_key" not in st.session_state:
        st.session_state.uploader_key = "uploader_docs_0"

    st.markdown('<div class="rp-title">업로드 문서</div>', unsafe_allow_html=True)

    uploaded = st.file_uploader(
        "",
        accept_multiple_files=True,
        label_visibility="collapsed",
        key=st.session_state.uploader_key,
    )

    if uploaded:
        for f in uploaded:
            if f.name not in st.session_state.uploaded_file_blobs:
                st.session_state.uploaded_file_blobs[f.name] = f.getvalue()
                st.session_state.uploaded_files.append({"name": f.name})

    upload_list_box = st.container(height=220)
    with upload_list_box:
        if not st.session_state.uploaded_files:
            st.caption("아직 업로드된 문서가 없습니다.")
        else:
            for it in list(reversed(st.session_state.uploaded_files)):
                c1, c2 = st.columns([0.86, 0.14], vertical_alignment="center")
                with c1:
                    st.write(f"• {it['name']}")
                with c2:
                    if st.button("✕", key=f"del_upload_{it['name']}", use_container_width=True):
                        st.session_state.uploaded_files = [
                            x for x in st.session_state.uploaded_files if x["name"] != it["name"]
                        ]
                        st.session_state.uploaded_file_blobs.pop(it["name"], None)
                        st.session_state.uploader_key = f"uploader_docs_{uuid.uuid4().hex}"
                        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)
