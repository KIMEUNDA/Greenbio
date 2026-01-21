import streamlit as st
import time
import re
from src.auth import create_user, get_user, verify_password

st.set_page_config(layout="wide", page_title="Green Bio Login")

# localStorage에서 로그인 정보 복원
st.markdown("""
    <script>
    // localStorage에서 로그인 정보 확인
    const loginData = localStorage.getItem('greenbio_login');
    if (loginData) {
        const data = JSON.parse(loginData);
        // 쿼리 파라미터로 전달
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
    # 쿼리 파라미터 제거하고 chat 페이지로 이동
    st.query_params.clear()
    st.switch_page("pages/chat.py")

if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'user_info' not in st.session_state:
    st.session_state['user_info'] = None

def login_page():
    # CSS 추가: 입력창과 버튼 텍스트를 흰색으로
    st.markdown("""
        <style>
        /* 입력창 placeholder와 텍스트 색상 */
        input::placeholder {
            color: rgba(255, 255, 255, 0.6) !important;
        }
        input {
            color: white !important;
        }
        /* 버튼 텍스트 색상 */
        .stButton > button {
            color: white !important;
        }
        /* 라벨 텍스트 색상 */
        label {
            color: white !important;
        }
        </style>
    """, unsafe_allow_html=True)

    with st.sidebar:
        st.title("Access Control")
        st.info("로그인 후 사용 가능")
        st.write("---")
        st.caption("Green Bio Project © 2026")

    empty1, col, empty2 = st.columns([1, 0.8, 1])

    with col:
        st.markdown("## 환영합니다!")
        st.write("Green Bio 챗봇입니다.")
        st.write("") 

        tab1, tab2 = st.tabs(["로그인", "회원가입"])

        with tab1:
            with st.container(border=True):
                
                user_id = st.text_input("이메일", placeholder="이메일을 입력하세요")
                user_pw = st.text_input("비밀번호", type="password", placeholder="Password")

                st.write("") 
                if st.button("로그인", type="primary", use_container_width=True):
                    if not user_id or not user_pw:
                        st.warning("이메일과 비밀번호를 모두 입력해주세요.")
                    else:
                        user = get_user(user_id)
                        
                        if user:
                            db_password_hash = user[3] 
                            db_role = user[4]

                            if verify_password(user_pw, db_password_hash):
                                st.session_state['logged_in'] = True
                                st.session_state['user_info'] = {
                                    "username": user[1],
                                    "role": db_role
                                }

                                # localStorage에 로그인 정보 저장
                                st.markdown(f"""
                                    <script>
                                    localStorage.setItem('greenbio_login', JSON.stringify({{
                                        username: '{user[1]}',
                                        role: '{db_role}'
                                    }}));
                                    </script>
                                """, unsafe_allow_html=True)

                                st.success(f"{user[1]}님 환영합니다!")
                                time.sleep(0.5)
                                st.switch_page("pages/chat.py")
                            else:
                                st.error("비밀번호가 일치하지 않습니다.")
                        else:
                            st.error("존재하지 않는 이메일입니다.")

        with tab2:
            with st.container(border=True):
                st.info("회원가입")
                new_name = st.text_input("이름")
                new_email = st.text_input("이메일")
                new_pw = st.text_input("비밀번호 (Password)", type="password")
                new_pw_check = st.text_input("비밀번호 확인", type="password")
                
                st.write("")
                if st.button("가입하기", use_container_width=True):
                    email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
                    if not (new_name and new_email and new_pw and new_pw_check):
                        st.warning("모든 정보를 입력해주세요.")
                        
                    elif not re.match(email_pattern, new_email):
                        st.warning("유효하지 않은 이메일 형식입니다. (예: user@example.com)")

                    elif new_pw != new_pw_check:
                        st.error("비밀번호가 일치하지 않습니다. 다시 확인해주세요.")
                        
                    else:
                        if create_user(new_name, new_email, new_pw, role='user'):
                            st.success("회원가입이 완료되었습니다! 로그인 탭에서 로그인해주세요.")
                        else:
                            st.error("가입 실패: 이미 존재하는 아이디거나 이메일입니다.")

if not st.session_state['logged_in']:
    login_page()
else:
    # Redirect to chat page if already logged in
    st.switch_page("pages/chat.py")