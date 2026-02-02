# pages/login.py
import streamlit as st
import time
import re
from src.auth import create_user, get_user, verify_password

st.set_page_config(layout="wide", page_title="Green Bio Login")

# =========================================
# ✅ 세션 키 초기화 (chat.py와 동일한 키로 통일)
# =========================================
if "auth_logged_in" not in st.session_state:
    st.session_state["auth_logged_in"] = False
if "auth_user" not in st.session_state:
    st.session_state["auth_user"] = ""
if "active_chat_item_id" not in st.session_state:
    st.session_state["active_chat_item_id"] = None
if "first_user_recorded" not in st.session_state:
    st.session_state["first_user_recorded"] = False

# (선택) 기존 키를 아직 쓰는 곳이 있을 수 있어 유지
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "user_info" not in st.session_state:
    st.session_state["user_info"] = None


def set_login_state(username: str, role: str):
    """✅ 로그인 성공 시 chat.py가 바로 인식하도록 세션 상태를 통일 세팅"""
    username = (username or "").strip()
    role = (role or "").strip()

    st.session_state["auth_logged_in"] = True
    st.session_state["auth_user"] = username

    st.session_state["logged_in"] = True
    st.session_state["user_info"] = {"username": username, "role": role}

    # 로그인 후 항상 새 채팅부터 시작(원하면 유지)
    st.session_state["active_chat_item_id"] = None
    st.session_state["first_user_recorded"] = False


# =========================================
# ✅ localStorage 기반 자동 복원
# - 첫 로드에서 localStorage -> query param으로 넘긴 뒤, 아래에서 세션 복원
# =========================================
st.markdown(
    """
<script>
(function() {
  const loginData = localStorage.getItem('greenbio_login');
  if (loginData) {
    const data = JSON.parse(loginData);
    const url = new URL(window.location.href);

    url.searchParams.set('restore_user', data.username || '');
    url.searchParams.set('restore_role', data.role || '');

    // 무한 리다이렉트 방지
    if (!url.searchParams.has('restored')) {
      url.searchParams.set('restored', 'true');
      window.location.href = url.toString();
    }
  }
})();
</script>
""",
    unsafe_allow_html=True,
)

# query param으로 로그인 복원
qp = st.query_params
if "restore_user" in qp and "restore_role" in qp:
    username = qp.get("restore_user", "")
    role = qp.get("restore_role", "")

    if username:
        set_login_state(username, role)
        st.query_params.clear()
        st.switch_page("pages/chat.py")
    else:
        # username이 비어있으면 복원 실패 -> 파라미터 제거
        st.query_params.clear()

# 이미 로그인 되어있으면 바로 채팅으로
if st.session_state.get("auth_logged_in", False) and st.session_state.get("auth_user", ""):
    st.switch_page("pages/chat.py")


def login_page():
    # CSS: 입력/버튼/라벨 컬러
    st.markdown(
        """
<style>
input::placeholder { color: rgba(0,0,0,0.6) !important; }
input { color: black !important; }
.stButton > button { color: black !important; }
label { color: black !important; }
</style>
""",
        unsafe_allow_html=True,
    )

    with st.sidebar:
        st.title("Access Control")
        st.info("로그인 후 사용 가능")
        st.write("---")
        st.caption("Green Bio Project © 2026")

    _, col, _ = st.columns([1, 0.8, 1])

    with col:
        st.markdown("## 환영합니다!")
        st.write("Green Bio 챗봇입니다.")
        st.write("")

        tab1, tab2 = st.tabs(["로그인", "회원가입"])

        # -----------------------------
        # 로그인 탭
        # -----------------------------
        with tab1:
            with st.container(border=True):
                user_id = st.text_input("이메일", placeholder="이메일을 입력하세요", key="login_email")
                user_pw = st.text_input("비밀번호", type="password", placeholder="Password", key="login_pw")

                st.write("")
                if st.button("로그인", type="primary", use_container_width=True, key="btn_login"):
                    if not user_id or not user_pw:
                        st.warning("이메일과 비밀번호를 모두 입력해주세요.")
                        return

                    user = get_user(user_id)

                    if not user:
                        st.error("존재하지 않는 이메일입니다.")
                        return

                    db_password_hash = user[3]
                    db_role = user[4]
                    username = user[1]

                    if not verify_password(user_pw, db_password_hash):
                        st.error("비밀번호가 일치하지 않습니다.")
                        return

                    # ✅ 세션 상태 통일 세팅
                    set_login_state(username=username, role=db_role)

                    # ✅ localStorage 저장 (자동 로그인용)
                    st.markdown(
                        f"""
<script>
localStorage.setItem('greenbio_login', JSON.stringify({{
  username: {username!r},
  role: {db_role!r}
}}));
</script>
""",
                        unsafe_allow_html=True,
                    )

                    st.success(f"{username}님 환영합니다!")
                    time.sleep(0.3)
                    st.switch_page("pages/chat.py")

        # -----------------------------
        # 회원가입 탭
        # -----------------------------
        with tab2:
            with st.container(border=True):
                st.info("회원가입")
                new_name = st.text_input("이름", key="signup_name")
                new_email = st.text_input("이메일", key="signup_email")
                new_pw = st.text_input("비밀번호 (Password)", type="password", key="signup_pw")
                new_pw_check = st.text_input("비밀번호 확인", type="password", key="signup_pw2")

                st.write("")
                if st.button("가입하기", use_container_width=True, key="btn_signup"):
                    email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"

                    if not (new_name and new_email and new_pw and new_pw_check):
                        st.warning("모든 정보를 입력해주세요.")
                        return

                    if not re.match(email_pattern, new_email):
                        st.warning("유효하지 않은 이메일 형식입니다. (예: user@example.com)")
                        return

                    if new_pw != new_pw_check:
                        st.error("비밀번호가 일치하지 않습니다. 다시 확인해주세요.")
                        return

                    if create_user(new_name, new_email, new_pw, role="user"):
                        st.success("회원가입이 완료되었습니다! 로그인 탭에서 로그인해주세요.")
                    else:
                        st.error("가입 실패: 이미 존재하는 아이디거나 이메일입니다.")


# 로그인 안 되어있으면 로그인 페이지 표시
login_page()
