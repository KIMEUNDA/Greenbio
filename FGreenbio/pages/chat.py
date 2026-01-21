import streamlit as st
import uuid
from datetime import datetime
from collections import namedtuple
from src.rag_system import get_rag_system

# 1. 페이지 설정
st.set_page_config(layout="wide", page_title="GreenBio Chatbot")

# 2. localStorage에서 로그인 정보 복원
st.markdown("""
    <script>
    const loginData = localStorage.getItem('greenbio_login');
    if (loginData) {
        const data = JSON.parse(loginData);
        const url = new URL(window.location.href);
        url.searchParams.set('restore_user', data.username);
        url.searchParams.set('restore_role', data.role);
        if (!url.searchParams.has('restored')) {
            url.searchParams.set('restored', 'true');
            window.location.href = url.toString();
        }
    }
    </script>
""", unsafe_allow_html=True)

# 쿼리 파라미터에서 로그인 정보 복원
query_params = st.query_params
if 'restore_user' in query_params and 'restore_role' in query_params:
    st.session_state['logged_in'] = True
    st.session_state['user_info'] = {
        'username': query_params['restore_user'],
        'role': query_params['restore_role']
    }
    # 쿼리 파라미터 정리
    st.query_params.clear()
    st.rerun()

# 3. 인증 확인
if 'logged_in' not in st.session_state or not st.session_state['logged_in']:
    st.error("로그인이 필요합니다.")
    st.info("로그인 페이지로 이동합니다...")
    st.switch_page("login.py")
    st.stop()

# --- 데이터 구조 정의 ---
Targets = namedtuple('Targets', ['temp_min', 'temp_max', 'hum_min', 'hum_max', 'co2_min', 'co2_max', 'light_min', 'light_max'])

GREENBIOCHAT = {
    "채팅 모드": {
        "targets": None,
        "snapshot": None,
        "welcome": "안녕하세요! 스마트 온실 관리 챗봇입니다. 궁금한 점을 물어보시거나, 왼쪽에서 온실을 선택해 주세요."
    },
    "1번 온실": {
        "targets": Targets(temp_min=20, temp_max=26, hum_min=55, hum_max=75, co2_min=600, co2_max=1200, light_min=8000, light_max=25000),
        "snapshot": dict(temp_c=24.3, humidity=68.0, light_lux=12000, co2_ppm=980),
    },
    "2번 온실": {
        "targets": Targets(temp_min=18, temp_max=24, hum_min=60, hum_max=85, co2_min=700, co2_max=1400, light_min=6000, light_max=22000),
        "snapshot": dict(temp_c=26.8, humidity=52.0, light_lux=16000, co2_ppm=1550),
    }
}

# 4. RAG 시스템 초기화
@st.cache_resource
def init_rag_v2():
    """RAG 시스템 초기화 (캐싱) - v2 with add_pdf_from_bytes"""
    return get_rag_system(
        persist_directory='chroma_store',
        pdf_directory='datafile'
    )

# RAG 시스템 로드
rag_system = init_rag_v2()

# 5. 세션 상태 초기화
if 'current_mode' not in st.session_state:
    st.session_state.current_mode = "채팅 모드"

if 'multi_chat_history' not in st.session_state:
    st.session_state.multi_chat_history = {
        "채팅 모드": [{"role": "assistant", "content": GREENBIOCHAT["채팅 모드"]["welcome"]}],
        "1번 온실": [],
        "2번 온실": []
    }

def get_analysis_message(name, data):
    snap = data['snapshot']
    target = data['targets']
    analysis = []
    if snap['temp_c'] < target.temp_min: analysis.append(f"온도 낮음({snap['temp_c']}°C)")
    elif snap['temp_c'] > target.temp_max: analysis.append(f"온도 높음({snap['temp_c']}°C)")
    if snap['humidity'] < target.hum_min: analysis.append(f"습도 낮음({snap['humidity']}%)")
    elif snap['humidity'] > target.hum_max: analysis.append(f"습도 높음({snap['humidity']}%)")
    status_msg = "현재 모든 수치가 정상 범위 내에 있습니다." if not analysis else f"주의사항: {' / '.join(analysis)}"
    return f"**{name}** 상태를 불러왔습니다.\n\n{status_msg}\n\n이 온실에 대해 무엇을 도와드릴까요?"

# 6. 스타일 정의 (CSS)
active_mode = st.session_state.current_mode

# 버튼 텍스트 정의 (CSS 매칭용)
btn_text_1 = "+  1번 온실"
btn_text_2 = "+  2번 온실"
btn_text_chat = "채팅 모드"

st.markdown(f"""
    <style>
    /* 페이지 네비게이션 숨기기 */
    [data-testid="stSidebarNav"] {{
        display: none !important;
    }}

    /* Running 아이콘 숨기기 (우측 상단만) */
    [data-testid="stStatusWidget"] {{
        display: none !important;
    }}

    header[data-testid="stHeader"] {{
        background-color: #3D4936 !important;
        position: fixed !important;
        top: 0 !important;
        left: 0 !important;
        right: 0 !important;
        width: 100vw !important;
        z-index: 999 !important;
    }}
    header[data-testid="stHeader"] * {{ color: white !important; }}

    /* 프로필 아이콘 컨테이너 */
    #profile-icon-container {{
        position: fixed !important;
        top: 15px !important;
        right: 110px !important;
        z-index: 9999 !important;
    }}

    #profile-icon {{
        width: 40px;
        height: 40px;
        border-radius: 50%;
        background-color: #8B9D7C;
        display: flex !important;
        align-items: center;
        justify-content: center;
        color: white;
        font-weight: bold;
        cursor: pointer;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        user-select: none;
    }}

    #profile-dropdown {{
        display: none;
        position: absolute;
        top: 50px;
        right: 0;
        background: white;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        padding: 10px 0;
        z-index: 10000;
        min-width: 180px;
    }}

    #profile-dropdown::before {{
        content: '';
        position: absolute;
        top: -8px;
        right: 12px;
        width: 0;
        height: 0;
        border-left: 8px solid transparent;
        border-right: 8px solid transparent;
        border-bottom: 8px solid white;
        filter: drop-shadow(0 -2px 2px rgba(0,0,0,0.1));
    }}

    #profile-dropdown.show {{
        display: block !important;
        animation: slideDown 0.2s ease;
    }}

    @keyframes slideDown {{
        from {{
            opacity: 0;
            transform: translateY(-10px);
        }}
        to {{
            opacity: 1;
            transform: translateY(0);
        }}
    }}

    .dropdown-item {{
        padding: 12px 20px;
        cursor: pointer;
        color: #333;
        transition: background-color 0.2s;
        font-size: 14px;
    }}

    .dropdown-item:first-child {{
        border-radius: 12px 12px 0 0;
    }}

    .dropdown-item:last-child {{
        border-radius: 0 0 12px 12px;
    }}

    .dropdown-item:hover {{
        background-color: #f0f0f0;
    }}

    .dropdown-item.logout {{
        color: #d32f2f;
        border-top: 1px solid #e0e0e0;
    }}

    /* 사이드바 토글 버튼 영역 */
    button[data-testid="collapsedControl"] {{
        background-color: #3D4936 !important;
        color: white !important;
    }}

    .stApp {{ background-color: #F8F9F2; }}
    [data-testid="stSidebar"] {{ background-color: #3D4936 !important; min-width: 280px !important; }}
    [data-testid="stSidebar"] * {{ color: white !important; }}

    /* 기본 버튼 스타일 */
    div.stButton > button {{
        background-color: transparent !important;
        color: white !important;
        border-radius: 12px !important;
        border: 2px solid rgba(255, 255, 255, 0.5) !important;
        height: 50px !important;
        font-size: 1rem !important;
        margin-bottom: 10px !important;
        text-align: left !important;
        padding-left: 20px !important;
        width: 100% !important;
        transition: all 0.3s ease !important;
    }}

    /* 호버 효과 - 활성화되지 않은 버튼만 */
    div.stButton > button:hover {{
        background-color: rgba(255, 255, 255, 0.2) !important;
        border-color: white !important;
    }}

    /* Primary 버튼 스타일 오버라이드 */
    [data-testid="stSidebar"] button[kind="primary"] {{
        background-color: white !important;
        color: #3D4936 !important;
        font-weight: bold !important;
        border: 3px solid white !important;
    }}

    [data-testid="stSidebar"] button[kind="primary"] p,
    [data-testid="stSidebar"] button[kind="primary"] div,
    [data-testid="stSidebar"] button[kind="primary"] span {{
        color: #3D4936 !important;
        font-weight: bold !important;
    }}

    /* Secondary 버튼 스타일 */
    [data-testid="stSidebar"] button[kind="secondary"] {{
        background-color: transparent !important;
        color: white !important;
        border: 2px solid rgba(255, 255, 255, 0.5) !important;
    }}

    [data-testid="stSidebar"] button[kind="secondary"] p {{
        color: white !important;
    }}

    /* 채팅 메시지 간격 줄이기 */
    .stChatMessage {{
        margin-bottom: 0.5rem !important;
        padding: 0.5rem !important;
    }}

    /* 채팅 메시지 내부 여백 조정 */
    .stChatMessage > div {{
        padding: 0.5rem !important;
    }}

    /* 채팅 입력바 기본 스타일 */
    div[data-testid="stChatInput"] {{
        position: fixed;
        bottom: 30px;
        z-index: 1000;
        padding: 10px;
        background: #F8F9F2;
        transition: all 0.3s ease !important;
    }}

    /* 사이드바 열림 상태 - 채팅 입력바 */
    section[data-testid="stSidebar"]:not([aria-hidden="true"]) ~ div div[data-testid="stChatInput"] {{
        width: 50% !important;
        left: 45% !important;
        transform: translateX(-50%);
    }}

    /* 사이드바 접힘 상태 - 채팅 입력바 */
    section[data-testid="stSidebar"][aria-hidden="true"] ~ div div[data-testid="stChatInput"] {{
        width: 60% !important;
        left: 50% !important;
        transform: translateX(-50%);
    }}

    /* 채팅 입력바 텍스트 및 placeholder 흰색 */
    div[data-testid="stChatInput"] input {{
        color: white !important;
        background-color: #5A6B4D !important;
        border-color: #5A6B4D !important;
    }}

    div[data-testid="stChatInput"] input::placeholder {{
        color: rgba(255, 255, 255, 0.7) !important;
    }}

    /* 메인 컨텐츠 영역 자동 조정 */
    section[data-testid="stMain"] {{
        transition: all 0.3s ease !important;
    }}

    .stChatMessage:last-child {{ margin-bottom: 120px !important; }}
    .card-title {{ font-weight: bold; color: #4A5A3F; font-size: 1.15rem; margin-top: 15px; display: block; }}
    </style>
    """, unsafe_allow_html=True)

# --- 웹소켓 클라이언트 설정 ---
st.markdown("""
    <script>
    // 웹소켓 연결 설정
    let ws = null;
    let reconnectInterval = null;

    function connectWebSocket() {
        // 이미 연결되어 있으면 종료
        if (ws && ws.readyState === WebSocket.OPEN) {
            return;
        }

        ws = new WebSocket('ws://localhost:8765/ws');

        ws.onopen = function(event) {
            console.log('웹소켓 연결됨');
            if (reconnectInterval) {
                clearInterval(reconnectInterval);
                reconnectInterval = null;
            }
        };

        ws.onmessage = function(event) {
            const data = JSON.parse(event.data);
            console.log('수신 데이터:', data);

            // 세션 스토리지에 최신 데이터 저장
            if (data.greenhouse && data.data) {
                sessionStorage.setItem(
                    'sensor_' + data.greenhouse,
                    JSON.stringify(data.data)
                );

                // Streamlit에 데이터 전달 (커스텀 이벤트)
                window.dispatchEvent(new CustomEvent('sensorUpdate', {
                    detail: data
                }));
            }
        };

        ws.onerror = function(error) {
            console.error('웹소켓 에러:', error);
        };

        ws.onclose = function(event) {
            console.log('웹소켓 연결 종료');
            ws = null;

            // 3초 후 재연결 시도
            if (!reconnectInterval) {
                reconnectInterval = setInterval(function() {
                    console.log('재연결 시도...');
                    connectWebSocket();
                }, 3000);
            }
        };
    }

    // 페이지 로드 시 웹소켓 연결
    connectWebSocket();

    // 페이지 언로드 시 웹소켓 닫기
    window.addEventListener('beforeunload', function() {
        if (ws) {
            ws.close();
        }
    });
    </script>
""", unsafe_allow_html=True)

# --- 헤더에 프로필 아이콘 추가 (드롭다운 없이) ---
st.markdown("""
    <div id="profile-icon-container">
        <div id="profile-icon">U</div>
    </div>
""", unsafe_allow_html=True)

# --- [사이드바] ---
with st.sidebar:
    st.title("GREENBIOCHAT")
    st.write("")

    # 버튼 클릭 시 세션 상태 변경 및 리런
    if st.button(btn_text_1, use_container_width=True, key="btn1", type="primary" if active_mode == "1번 온실" else "secondary"):
        st.session_state.current_mode = "1번 온실"
        if not st.session_state.multi_chat_history["1번 온실"]:
            msg = get_analysis_message("1번 온실", GREENBIOCHAT["1번 온실"])
            st.session_state.multi_chat_history["1번 온실"].append({"role": "assistant", "content": msg})
        st.rerun()

    if st.button(btn_text_2, use_container_width=True, key="btn2", type="primary" if active_mode == "2번 온실" else "secondary"):
        st.session_state.current_mode = "2번 온실"
        if not st.session_state.multi_chat_history["2번 온실"]:
            msg = get_analysis_message("2번 온실", GREENBIOCHAT["2번 온실"])
            st.session_state.multi_chat_history["2번 온실"].append({"role": "assistant", "content": msg})
        st.rerun()

    st.write("---") # 구분선
    if st.button(btn_text_chat, use_container_width=True, key="btn_chat", type="primary" if active_mode == "채팅 모드" else "secondary"):
        st.session_state.current_mode = "채팅 모드"
        st.rerun()

# --- 메인 레이아웃 및 나머지 로직 동일 ---
col_main, col_right = st.columns([0.75, 0.25], gap="medium")

with col_main:
    mode = st.session_state.current_mode

    # 자동 새로고침을 위한 JavaScript 코드 추가
    st.markdown("""
        <script>
        // 3초마다 페이지 자동 새로고침 (센서 데이터 업데이트용)
        setTimeout(function() {
            const url = new URL(window.location.href);
            url.searchParams.set('refresh', Date.now());
            window.location.href = url.toString();
        }, 3000);
        </script>
    """, unsafe_allow_html=True)

    if mode != "채팅 모드":
        data = GREENBIOCHAT[mode]
        st.subheader(f"{mode} 모니터링")

        # 센서 데이터 표시 영역 (JavaScript에서 업데이트될 수 있도록)
        m1, m2, m3, m4 = st.columns(4)

        # 기본값 또는 최신 데이터 표시
        m1.metric("온도", f"{data['snapshot']['temp_c']:.1f}°C")
        m2.metric("습도", f"{data['snapshot']['humidity']:.1f}%")
        m3.metric("CO2", f"{data['snapshot']['co2_ppm']}ppm")
        m4.metric("조도", f"{data['snapshot']['light_lux']}Lux")

        # 웹소켓 데이터 수신을 위한 JavaScript
        st.markdown(f"""
            <script>
            (function() {{
                // sessionStorage에서 최신 센서 데이터 읽기
                const sensorData = sessionStorage.getItem('sensor_{mode}');
                if (sensorData) {{
                    console.log('저장된 센서 데이터:', sensorData);
                    // 여기서 직접 DOM을 업데이트할 수 있지만,
                    // Streamlit의 제약으로 인해 페이지 새로고침이 필요함
                }}
            }})();
            </script>
        """, unsafe_allow_html=True)

        st.divider()

    # 답변 생성 중 표시 (채팅 입력 위에)
    if 'is_generating' not in st.session_state:
        st.session_state.is_generating = False

    chat_container = st.container(height=600, border=False)
    with chat_container:
        for msg in st.session_state.multi_chat_history[mode]:
            st.chat_message(msg["role"]).write(msg["content"])

    # 답변 생성 중 스피너 표시 (채팅 입력 위에)
    loading_placeholder = st.empty()
    if st.session_state.is_generating:
        with loading_placeholder:
            with st.spinner("답변 생성 중..."):
                pass

    if prompt := st.chat_input("메시지를 입력하세요..."):
        # 사용자 메시지 추가
        st.session_state.multi_chat_history[mode].append({"role": "user", "content": prompt})
        st.session_state.is_generating = True
        st.rerun()

    # 답변 생성 (rerun 후 실행)
    if st.session_state.is_generating:
        try:
            # 마지막 메시지가 user인 경우에만 응답 생성
            if st.session_state.multi_chat_history[mode][-1]["role"] == "user":
                user_prompt = st.session_state.multi_chat_history[mode][-1]["content"]
                response = rag_system.query(user_prompt)
                st.session_state.multi_chat_history[mode].append({"role": "assistant", "content": response})
        except Exception as e:
            error_msg = f"오류가 발생했습니다: {str(e)}"
            st.session_state.multi_chat_history[mode].append({"role": "assistant", "content": error_msg})
        finally:
            st.session_state.is_generating = False
            loading_placeholder.empty()
            st.rerun()

with col_right:
    st.write("") 
    with st.container(height=450, border=True):
        st.markdown('<span class="card-title">채팅 내역</span>', unsafe_allow_html=True)
        st.caption(f"현재 위치: {st.session_state.current_mode}")

    with st.container(height=240, border=True):
        st.markdown('<span class="card-title">업로드 문서</span>', unsafe_allow_html=True)

        # PDF 파일 업로드
        uploaded_files = st.file_uploader(
            "PDF 파일을 업로드하세요",
            type=['pdf'],
            accept_multiple_files=True,
            label_visibility="collapsed",
            key="pdf_uploader"
        )

        if uploaded_files:
            for uploaded_file in uploaded_files:
                # 세션에 업로드된 파일 기록
                if 'uploaded_pdfs' not in st.session_state:
                    st.session_state.uploaded_pdfs = set()

                # 이미 업로드된 파일인지 확인
                if uploaded_file.name not in st.session_state.uploaded_pdfs:
                    with st.spinner(f"{uploaded_file.name} 처리 중..."):
                        # PDF 바이트 읽기
                        pdf_bytes = uploaded_file.read()

                        # datafile 폴더에 저장
                        import os
                        datafile_path = os.path.join("datafile", uploaded_file.name)
                        os.makedirs("datafile", exist_ok=True)

                        with open(datafile_path, "wb") as f:
                            f.write(pdf_bytes)

                        # RAG 시스템에 추가
                        success = rag_system.add_pdf_from_bytes(pdf_bytes, uploaded_file.name)

                        if success:
                            st.session_state.uploaded_pdfs.add(uploaded_file.name)
                            st.success(f"✓ {uploaded_file.name} 업로드 완료! (datafile 폴더에 저장됨)")
                        else:
                            st.error(f"✗ {uploaded_file.name} 업로드 실패")

        # 업로드된 파일 목록 표시
        if 'uploaded_pdfs' in st.session_state and st.session_state.uploaded_pdfs:
            st.write("**업로드된 파일:**")
            for filename in st.session_state.uploaded_pdfs:
                st.text(f"📄 {filename}")