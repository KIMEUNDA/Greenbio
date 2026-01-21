import sqlite3
import os
from pathlib import Path

# 데이터베이스 파일 경로
DB_PATH = Path(__file__).parent.parent / "datafile" / "users.db"

def get_connection():
    """SQLite 연결 반환"""
    try:
        # 디렉토리가 없으면 생성
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(str(DB_PATH))
        print("DB 연결 성공!")
        return conn
    except sqlite3.Error as e:
        print(f"DB 연결 실패: {e}")
        return None

def init_db():
    """users 테이블 생성"""
    conn = get_connection()
    if not conn:
        return False

    try:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT DEFAULT 'user',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        print("users 테이블 생성/확인 완료!")
        conn.close()
        return True
    except sqlite3.Error as e:
        print(f"❌ 테이블 생성 에러: {e}")
        conn.close()
        return False

def test_connection():
    """연결 테스트용"""
    conn = get_connection()
    if conn:
        cur = conn.cursor()
        cur.execute("SELECT 1")
        result = cur.fetchone()
        print(f"연결 테스트 성공: {result}")
        conn.close()
        return True
    return False

if __name__ == "__main__":
    print("=== DB 테스트 ===")
    test_connection()
    init_db()
