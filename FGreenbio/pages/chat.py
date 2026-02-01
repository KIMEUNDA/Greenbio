# streamlit_app.py
import os
import html
import uuid
from dataclasses import dataclass
from datetime import datetime
from collections import namedtuple

import streamlit as st
import streamlit.components.v1 as components
from streamlit_float import float_init

# ✅ RAG
from src.rag_system import get_rag_system

# =========================================================
# Page config
# =========================================================
st.set_page_config(page_title="GreenBio Chatbot", page_icon="🌿", layout="wide")
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
# ✅ RAG 시스템 초기화
# =========================
@st.cache_resource
def init_rag_v2():
    """RAG 시스템 초기화 (캐싱) - v2 with add_pdf_from_bytes"""
    return get_rag_system(
        persist_directory="chroma_store",
        pdf_directory="datafile",
    )

rag_system = init_rag_v2()


# =========================
# ✅ 서버 메모리(사용자별) 저장소: 채팅 내역 + 채팅별 메시지 유지용
# (ClimateBot 코드의 '채팅방 히스토리' 기능은 유지하되,
#  GreenBio의 '모드별 멀티 히스토리'가 핵심이라 여기서는
#  "사용자 로그인 상태 유지/복원" 중심으로만 활용)
# =========================
@st.cache_resource
def get_user_store():
    return {}

def _ensure_user_bucket(user_id: str):
    store = get_user_store()
    if user_id not in store:
        store[user_id] = {"history": [], "chats": {}}
    store[user_id].setdefault("history", [])
    store[user_id].setdefault("chats", {})
    return store[user_id]

def get_history(user_id: str):
    return _ensure_user_bucket(user_id)["history"]

def add_history_item(user_id: str, title: str = "(새 채팅)"):
    hist = get_history(user_id)
    item_id = str(uuid.uuid4())[:8]
    hist.append(
        {"id": item_id, "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "title": title}
    )
    return item_id

def update_history_title(user_id: str, item_id: str, new_title: str):
    for it in get_history(user_id):
        if it["id"] == item_id:
            it["title"] = new_title
            return

def delete_history_item(user_id: str, item_id: str):
    store = get_user_store()
    hist = get_history(user_id)
    store[user_id]["history"] = [it for it in hist if it["id"] != item_id]
    store[user_id]["chats"].pop(item_id, None)

def get_chat_messages(user_id: str, chat_id: str):
    bucket = _ensure_user_bucket(user_id)
    chats = bucket["chats"]
    if chat_id not in chats:
        chats[chat_id] = [
            {"role": "assistant", "content": "안녕하세요! 저는 Greenbio Chat 🌿 입니다. 현재 상태를 보고 제어/진단을 도와드릴게요."}
        ]
    return chats[chat_id]

def set_chat_messages(user_id: str, chat_id: str, messages):
    bucket = _ensure_user_bucket(user_id)
    bucket["chats"][chat_id] = messages


# =========================
# ✅ (추가) 헤더 앵커(#xxxx) 방지 JS
# =========================
components.html(
    """
    <script>
    (function () {
      if (window.location.hash && window.location.hash.length > 1) {
        history.replaceState(null, "", window.location.pathname + window.location.search);
      }
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
# ✅ GreenBio: localStorage에서 로그인 정보 복원 (JS)
# - localStorage key: greenbio_login = {username, role}
# =========================
components.html(
    """
    <script>
    (function(){
      const loginData = localStorage.getItem('greenbio_login');
      if (loginData) {
        try{
          const data = JSON.parse(loginData);
          const url = new URL(window.location.href);
          if (data && data.username) {
            url.searchParams.set('restore_user', data.username);
            url.searchParams.set('restore_role', data.role || 'user');
            if (!url.searchParams.has('restored')) {
              url.searchParams.set('restored', 'true');
              window.location.href = url.toString();
            }
          }
        }catch(e){}
      }
    })();
    </script>
    """,
    height=0,
)

# =========================
# CSS (ClimateBot UI 그대로)
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

span[data-testid="stHeaderActionElements"] {{
  display: none !important;
}}

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

div[data-testid="stFileUploader"] [data-testid="stFileUploaderFile"] {{
  display: none !important;
}}
div[data-testid="stFileUploader"] ul {{
  display: none !important;
}}
div[data-testid="stFileUploader"] li {{
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

# =========================================================
# ✅ GreenBio 데이터 구조 (모드/온실별 targets/snapshot/welcome)
# =========================================================
TargetsNT = namedtuple(
    "Targets",
    ["temp_min", "temp_max", "hum_min", "hum_max", "co2_min", "co2_max", "light_min", "light_max"],
)

GREENBIOCHAT = {
    "채팅 모드": {
        "targets": None,
        "snapshot": None,
        "welcome": "안녕하세요! 스마트 온실 관리 챗봇입니다. 궁금한 점을 물어보시거나, 왼쪽에서 온실을 선택해 주세요.",
    },
    "1번 온실": {
        "targets": TargetsNT(temp_min=20, temp_max=26, hum_min=55, hum_max=75, co2_min=600, co2_max=1200, light_min=8000, light_max=25000),
        "snapshot": dict(temp_c=24.3, humidity=68.0, light_lux=12000, co2_ppm=980),
    },
    "2번 온실": {
        "targets": TargetsNT(temp_min=18, temp_max=24, hum_min=60, hum_max=85, co2_min=700, co2_max=1400, light_min=6000, light_max=22000),
        "snapshot": dict(temp_c=26.8, humidity=52.0, light_lux=16000, co2_ppm=1550),
    },
}

def get_analysis_message(name, data):
    snap = data["snapshot"]
    target = data["targets"]
    analysis = []
    if snap["temp_c"] < target.temp_min:
        analysis.append(f"온도 낮음({snap['temp_c']}°C)")
    elif snap["temp_c"] > target.temp_max:
        analysis.append(f"온도 높음({snap['temp_c']}°C)")
    if snap["humidity"] < target.hum_min:
        analysis.append(f"습도 낮음({snap['humidity']}%)")
    elif snap["humidity"] > target.hum_max:
        analysis.append(f"습도 높음({snap['humidity']}%)")
    status_msg = "현재 모든 수치가 정상 범위 내에 있습니다." if not analysis else f"주의사항: {' / '.join(analysis)}"
    return f"**{name}** 상태를 불러왔습니다.\n\n{status_msg}\n\n이 온실에 대해 무엇을 도와드릴까요?"


# =========================================================
# ✅ Session state: GreenBio 방식(모드별 multi_chat_history)
# =========================================================
if "current_mode" not in st.session_state:
    st.session_state.current_mode = "채팅 모드"

if "multi_chat_history" not in st.session_state:
    st.session_state.multi_chat_history = {
        "채팅 모드": [{"role": "assistant", "content": GREENBIOCHAT["채팅 모드"]["welcome"]}],
        "1번 온실": [],
        "2번 온실": [],
    }

if "is_generating" not in st.session_state:
    st.session_state.is_generating = False

# ✅ 로그인 상태(ClimateBot UI 변수명 유지)
if "auth_logged_in" not in st.session_state:
    st.session_state.auth_logged_in = False
if "auth_user" not in st.session_state:
    st.session_state.auth_user = ""

# ✅ chat history (오른쪽에 표시용) - ClimateBot 기능 유지
if "active_chat_item_id" not in st.session_state:
    st.session_state.active_chat_item_id = None
if "first_user_recorded" not in st.session_state:
    st.session_state.first_user_recorded = False


# =========================================================
# ✅ GreenBio: 쿼리 파라미터에서 로그인 정보 복원
# =========================================================
query_params = st.query_params
if (not st.session_state.auth_logged_in) and ("restore_user" in query_params) and ("restore_role" in query_params):
    st.session_state.auth_logged_in = True
    st.session_state.auth_user = str(query_params["restore_user"])
    # (role은 필요하면 세션에 저장)
    st.session_state.user_role = str(query_params["restore_role"])

    # ClimateBot 우측 "채팅 내역" 기능도 함께 살리기 위해 새 항목 생성
    item_id = add_history_item(st.session_state.auth_user, title="(새 채팅)")
    st.session_state.active_chat_item_id = item_id
    st.session_state.first_user_recorded = False

    # 쿼리 파라미터 정리
    try:
        st.query_params.clear()
    except Exception:
        pass
    st.rerun()


# =========================================================
# ✅ GreenBio: websocket + sessionStorage 저장 스크립트
# =========================================================
components.html(
    """
    <script>
    let ws = null;
    let reconnectInterval = null;

    function connectWebSocket() {
        if (ws && ws.readyState === WebSocket.OPEN) return;

        ws = new WebSocket('ws://localhost:8765/ws');

        ws.onopen = function() {
            if (reconnectInterval) {
                clearInterval(reconnectInterval);
                reconnectInterval = null;
            }
        };

        ws.onmessage = function(event) {
            try{
              const data = JSON.parse(event.data);
              if (data.greenhouse && data.data) {
                  sessionStorage.setItem('sensor_' + data.greenhouse, JSON.stringify(data.data));
                  window.dispatchEvent(new CustomEvent('sensorUpdate', { detail: data }));
              }
            }catch(e){}
        };

        ws.onclose = function() {
            ws = null;
            if (!reconnectInterval) {
                reconnectInterval = setInterval(function() {
                    connectWebSocket();
                }, 3000);
            }
        };
    }

    connectWebSocket();

    window.addEventListener('beforeunload', function() {
        try { if (ws) ws.close(); } catch(e) {}
    });
    </script>
    """,
    height=0,
)

# =========================================================
# ✅ GreenBio: 3초마다 페이지 자동 새로고침
# (Streamlit 제약 때문에 websocket 데이터 즉시 반영이 어려워 refresh로 반영)
# =========================================================
components.html(
    """
    <script>
    setTimeout(function() {
        const url = new URL(window.location.href);
        url.searchParams.set('refresh', Date.now());
        window.location.href = url.toString();
    }, 3000);
    </script>
    """,
    height=0,
)

# =========================================================
# Top bar (로그인/로그아웃)
# - 기존 ClimateBot UI 유지
# - 로그인 성공 시 localStorage에 저장 (greenbio_login)
# =========================================================
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
            role = st.text_input("role(옵션)", value="user", key="login_role")

            if st.button("로그인", use_container_width=True, key="do_login"):
                if uid.strip():
                    st.session_state.auth_logged_in = True
                    st.session_state.auth_user = uid.strip()
                    st.session_state.user_role = (role.strip() or "user")

                    # ✅ localStorage 저장
                    components.html(
                        f"""
                        <script>
                        try {{
                          localStorage.setItem('greenbio_login', JSON.stringify({{
                            username: {st.session_state.auth_user!r},
                            role: {st.session_state.user_role!r}
                          }}));
                        }} catch(e) {{}}
                        </script>
                        """,
                        height=0,
                    )

                    # 우측 채팅내역(ClimateBot) 초기화
                    item_id = add_history_item(st.session_state.auth_user, title="(새 채팅)")
                    st.session_state.active_chat_item_id = item_id
                    st.session_state.first_user_recorded = False

                    st.rerun()
                else:
                    st.warning("아이디를 입력하세요.")
    else:
        with st.popover("로그아웃", use_container_width=True):
            if st.button("로그아웃", use_container_width=True, key="do_logout"):
                # ✅ localStorage 삭제
                components.html(
                    """
                    <script>
                    try { localStorage.removeItem('greenbio_login'); } catch(e) {}
                    </script>
                    """,
                    height=0,
                )

                st.session_state.auth_logged_in = False
                st.session_state.auth_user = ""
                st.session_state.active_chat_item_id = None
                st.session_state.first_user_recorded = False
                st.rerun()

# ✅ 로그인 상태인데 active id 없으면 새로 생성
if st.session_state.auth_logged_in and st.session_state.active_chat_item_id is None:
    item_id = add_history_item(st.session_state.auth_user, title="(새 채팅)")
    st.session_state.active_chat_item_id = item_id
    st.session_state.first_user_recorded = False


# =========================================================
# Layout: left / center / right
# - left: GreenBio 사이드바(버튼) 로직을 ClimateBot left 영역에 이식
# - mid: GreenBio 채팅(st.chat_input / history) 로직을 HTML bubble에 이식
# - right: ClimateBot 채팅내역 + GreenBio 업로드/RAG 로직
# =========================================================
col_left, col_mid, col_right = st.columns([1.05, 3.0, 1.05], gap="large")

# ---------------------------------------------------------
# Left: 모드 선택 (GreenBio: 채팅모드/1번/2번)
# ---------------------------------------------------------
with col_left:
    st.markdown('<div class="gh-pill">모드 선택</div>', unsafe_allow_html=True)

    active_mode = st.session_state.current_mode

    if st.button("＋ 1번 온실", use_container_width=True, key="btn_mode_1"):
        st.session_state.current_mode = "1번 온실"
        if not st.session_state.multi_chat_history["1번 온실"]:
            msg = get_analysis_message("1번 온실", GREENBIOCHAT["1번 온실"])
            st.session_state.multi_chat_history["1번 온실"].append({"role": "assistant", "content": msg})
        st.rerun()

    if st.button("＋ 2번 온실", use_container_width=True, key="btn_mode_2"):
        st.session_state.current_mode = "2번 온실"
        if not st.session_state.multi_chat_history["2번 온실"]:
            msg = get_analysis_message("2번 온실", GREENBIOCHAT["2번 온실"])
            st.session_state.multi_chat_history["2번 온실"].append({"role": "assistant", "content": msg})
        st.rerun()

    if st.button("채팅 모드", use_container_width=True, key="btn_mode_chat"):
        st.session_state.current_mode = "채팅 모드"
        st.rerun()

    st.caption(f"현재 위치: **{st.session_state.current_mode}**")

    # 모니터링(원본 GreenBio의 metric 느낌을 left에 표시)
    mode = st.session_state.current_mode
    if mode != "채팅 모드":
        data = GREENBIOCHAT[mode]
        snap = data["snapshot"]
        targets = data["targets"]

        def _judge_value(value, lo, hi):
            if lo <= value <= hi:
                return "ok"
            margin = (hi - lo) * 0.2 if (hi - lo) != 0 else 1
            if (lo - margin) <= value <= (hi + margin):
                return "warn"
            return "bad"

        t_lv = _judge_value(snap["temp_c"], targets.temp_min, targets.temp_max)
        h_lv = _judge_value(snap["humidity"], targets.hum_min, targets.hum_max)
        c_lv = _judge_value(snap["co2_ppm"], targets.co2_min, targets.co2_max)
        l_lv = _judge_value(snap["light_lux"], targets.light_min, targets.light_max)

        st.markdown('<div class="card"><h4>현재 상태</h4>', unsafe_allow_html=True)
        st.markdown(f'<div class="kv"><div class="k">온도</div><div class="v">{snap["temp_c"]:.1f}°C</div></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="kv"><div class="k">습도</div><div class="v">{snap["humidity"]:.1f}%</div></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="kv"><div class="k">CO₂</div><div class="v">{snap["co2_ppm"]} ppm</div></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="kv"><div class="k">광량</div><div class="v">{snap["light_lux"]} lux</div></div>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="card"><h4>진단</h4>', unsafe_allow_html=True)
        st.markdown(f'<div class="kv"><div class="k">온도</div><div class="v">{t_lv.upper()}</div></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="kv"><div class="k">습도</div><div class="v">{h_lv.upper()}</div></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="kv"><div class="k">CO₂</div><div class="v">{c_lv.upper()}</div></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="kv"><div class="k">광량</div><div class="v">{l_lv.upper()}</div></div>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)


# ---------------------------------------------------------
# Middle: 채팅 (GreenBio의 multi_chat_history 로직 그대로)
# - UI는 ClimateBot의 HTML bubble
# - 입력은 form으로 고정
# ---------------------------------------------------------
with col_mid:
    mode = st.session_state.current_mode
    messages = st.session_state.multi_chat_history[mode]

    bubbles = []
    for m in messages:
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
                G
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

    # 입력창(고정)
    input_box = st.container()
    with input_box:
        with st.form("chat_form", clear_on_submit=True):
            user_text = st.text_input(
                "",
                placeholder="메시지를 입력하세요...",
                label_visibility="collapsed",
            )
            sent = st.form_submit_button("전송")

    input_box.float(
        f"position: fixed; bottom: {PROMPT_BOTTOM}px; left: 50%; "
        f"transform: translateX(-50%); width: {CHAT_WIDTH}px; z-index: 999;"
    )

    # ✅ GreenBio: 사용자 입력 -> history 추가 -> is_generating -> rerun
    if sent and user_text.strip():
        st.session_state.multi_chat_history[mode].append({"role": "user", "content": user_text.strip()})
        st.session_state.is_generating = True
        st.rerun()

    # ✅ GreenBio: rerun 후 답변 생성
    if st.session_state.is_generating:
        try:
            if st.session_state.multi_chat_history[mode] and st.session_state.multi_chat_history[mode][-1]["role"] == "user":
                user_prompt = st.session_state.multi_chat_history[mode][-1]["content"]
                response = rag_system.query(user_prompt)
                st.session_state.multi_chat_history[mode].append({"role": "assistant", "content": response})
        except Exception as e:
            st.session_state.multi_chat_history[mode].append({"role": "assistant", "content": f"오류가 발생했습니다: {str(e)}"})
        finally:
            st.session_state.is_generating = False
            st.rerun()


# ---------------------------------------------------------
# Right: (1) 채팅 내역 UI (ClimateBot) + (2) 업로드 문서 (GreenBio 로직)
# ---------------------------------------------------------
with col_right:
    # ---------- 채팅 내역 (ClimateBot UI)
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
                            # ※ 여기서는 GreenBio multi_chat_history가 메인이라
                            #    messages 전환은 "모드별"만 존재
                            st.rerun()
                    with right:
                        if st.button("✕", key=f"del_hist_{it['id']}", use_container_width=True):
                            delete_history_item(st.session_state.auth_user, it["id"])
                            if st.session_state.active_chat_item_id == it["id"]:
                                st.session_state.active_chat_item_id = None
                                st.session_state.first_user_recorded = False
                            st.rerun()

    if st.session_state.auth_logged_in:
        if st.button("＋ 새 채팅", use_container_width=True, key="btn_new_chat"):
            new_id = add_history_item(st.session_state.auth_user, title="(새 채팅)")
            st.session_state.active_chat_item_id = new_id
            st.session_state.first_user_recorded = False
            st.rerun()
    else:
        st.caption("새 채팅은 로그인 후 사용할 수 있어요.")

    st.markdown("</div>", unsafe_allow_html=True)

    # ---------- 업로드 문서 (GreenBio 로직: PDF -> datafile 저장 -> rag_system.add_pdf_from_bytes)
    st.markdown('<div class="rp-title">업로드 문서</div>', unsafe_allow_html=True)

    if "uploaded_pdfs" not in st.session_state:
        st.session_state.uploaded_pdfs = set()

    uploaded_files = st.file_uploader(
        "",
        type=["pdf"],
        accept_multiple_files=True,
        label_visibility="collapsed",
        key="pdf_uploader",
    )

    if uploaded_files:
        os.makedirs("datafile", exist_ok=True)

        for uploaded_file in uploaded_files:
            if uploaded_file.name not in st.session_state.uploaded_pdfs:
                with st.spinner(f"{uploaded_file.name} 처리 중..."):
                    pdf_bytes = uploaded_file.read()

                    # datafile 폴더에 저장
                    datafile_path = os.path.join("datafile", uploaded_file.name)
                    with open(datafile_path, "wb") as f:
                        f.write(pdf_bytes)

                    # RAG 시스템에 추가
                    try:
                        success = rag_system.add_pdf_from_bytes(pdf_bytes, uploaded_file.name)
                    except Exception:
                        success = False

                    if success:
                        st.session_state.uploaded_pdfs.add(uploaded_file.name)
                        st.success(f"✓ {uploaded_file.name} 업로드 완료! (datafile 폴더에 저장됨)")
                    else:
                        st.error(f"✗ {uploaded_file.name} 업로드 실패")

    upload_list_box = st.container(height=220)
    with upload_list_box:
        if not st.session_state.uploaded_pdfs:
            st.caption("아직 업로드된 문서가 없습니다.")
        else:
            for filename in list(reversed(sorted(st.session_state.uploaded_pdfs))):
                c1, c2 = st.columns([0.86, 0.14], vertical_alignment="center")
                with c1:
                    st.write(f"• {filename}")
                with c2:
                    if st.button("✕", key=f"del_upload_{filename}", use_container_width=True):
                        st.session_state.uploaded_pdfs.discard(filename)
                        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)
