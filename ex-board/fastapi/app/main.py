from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pymysql
import os  # 환경 변수를 읽기 위해 추가
from contextlib import asynccontextmanager

# 1. 데이터 구조 정의
class BoardWriteItem(BaseModel):
    p_key: int
    p_level: int
    p_step: int
    p_userId: str
    p_passwd: str
    p_userName: str
    p_subject: str
    p_content: str
    p_hit: int

class DeleteRequest(BaseModel):
    password: str

class UpdateRequest(BaseModel):
    fsubject: str
    fcontent: str

# 2. DB 설정 (환경 변수 또는 직접 입력)
# docker-compose.yml의 environment에서 넘겨준 값을 사용하거나 기본값을 설정합니다.
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "mysql-primary-container"), # 컨테이너 이름 사용
    "user": os.getenv("DB_USER", "dev"),
    "password": os.getenv("DB_PASSWORD", "dev1234!"),
    "db": os.getenv("DB_NAME", "iandb"),
    "port": 3306,
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor
}

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Docker 환경에서는 SSH 터널링이 필요 없으므로 바로 yield 합니다.
    yield

app = FastAPI(lifespan=lifespan)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 공통 DB 연결 함수
def get_db_conn():
    return pymysql.connect(**DB_CONFIG)

@app.get("/")
def home():
    return {"message": "connected to fastapi"}

# --- 목록보기 ---
@app.get("/list")
def board_list(page: int = 1):
    conn = None
    try:
        conn = get_db_conn()
        with conn.cursor() as cursor:
            size = 10
            offset = (page - 1) * size
            cursor.execute("SELECT COUNT(*) as cnt FROM tboard")
            total_count = cursor.fetchone()['cnt']
            sql = """
                SELECT fidx, fnum, fkey, flevel, fstep, fuserName, fsubject, fhit, fregdate 
                FROM tboard 
                ORDER BY fkey DESC, fstep DESC 
                LIMIT %s OFFSET %s
            """
            cursor.execute(sql, (size, offset))
            result = cursor.fetchall()
            return {"items": result, "total_count": total_count, "page": page, "size": size}
    except Exception as e:
        return {"error": str(e)}
    finally:
        if conn: conn.close()

# --- 나머지 API들 (동일하게 get_db_conn 사용하도록 수정) ---
# (코드 중복 방지를 위해 생략하지만, 모두 conn = get_db_conn() 방식으로 호출하시면 됩니다.)

# --- 글쓰기 ---
@app.post("/append")
def board_append(item: BoardWriteItem):
    conn = None
    try:
        conn = get_db_conn()
        with conn.cursor() as cur:
            sql = "CALL BoardAppend(%s, %s, %s, %s, %s, %s, %s, %s, %s)"
            params = (item.p_key, item.p_level, item.p_step, item.p_userId,
                      item.p_passwd, item.p_userName, item.p_subject, item.p_content, item.p_hit)
            cur.execute(sql, params)
            res = cur.fetchone() 
            conn.commit()
            return res.get('result') if res else 1
    except Exception as e:
        if conn: conn.rollback()
        return {"error": str(e)}
    finally:
        if conn: conn.close()


# 예시: 상세보기
@app.get("/view/{fidx}")
def board_view(fidx: int):
    conn = None
    try:
        conn = get_db_conn()
        with conn.cursor() as cur:
            cur.execute("UPDATE tboard SET fhit = fhit + 1 WHERE fidx = %s", (fidx,))
            conn.commit()
            cur.execute("SELECT fidx, fnum, fkey, flevel, fstep, fuserName, fsubject, fcontent, fhit, fregdate FROM tboard WHERE fidx = %s", (fidx,))
            res = cur.fetchone()
            if res:
                if res['fregdate']: res['fregdate'] = res['fregdate'].strftime('%Y/%m/%d %H:%M')
                return res
            return {"error": "게시글을 찾을 수 없습니다."}
    except Exception as e:
        return {"error": str(e)}
    finally:
        if conn: conn.close()


# --- [추가] 수정 전 비밀번호 확인용 ---
@app.post("/verify-password/{fidx}")
def verify_password(fidx: int, req: DeleteRequest):
    conn = None
    try:
        conn = get_db_conn()
        with conn.cursor() as cur:
            cur.execute("SELECT fpasswd FROM tboard WHERE fidx = %s", (fidx,))
            row = cur.fetchone()
            if row and row['fpasswd'] == req.password:
                return {"result": "success"}
            else:
                return {"result": "fail", "message": "비밀번호가 일치하지 않습니다."}
    except Exception as e:
        return {"result": "error", "message": str(e)}
    finally:
        if conn: conn.close()

# --- [추가] 실제 데이터 수정(Update) 처리 ---
@app.post("/update/{fidx}")
def board_update(fidx: int, req: UpdateRequest):
    conn = None
    try:
        conn = get_db_conn()
        with conn.cursor() as cur:
            sql = "UPDATE tboard SET fsubject = %s, fcontent = %s WHERE fidx = %s"
            cur.execute(sql, (req.fsubject, req.fcontent, fidx))
            conn.commit()
            return {"result": "success"}
    except Exception as e:
        if conn: conn.rollback()
        return {"result": "error", "message": str(e)}
    finally:
        if conn: conn.close()

# --- 삭제 처리 ---
@app.post("/delete/{fidx}")
def board_delete(fidx: int, req: DeleteRequest):
    conn = None
    try:
        conn = get_db_conn()
        with conn.cursor() as cur:
            sql_check = "SELECT fpasswd FROM tboard WHERE fidx = %s"
            cur.execute(sql_check, (fidx,))
            row = cur.fetchone()

            if not row:
                return {"result": "fail", "message": "게시글이 존재하지 않습니다."}

            if row['fpasswd'] != req.password:
                return {"result": "fail", "message": "비밀번호가 일치하지 않습니다."}

            sql_delete = "DELETE FROM tboard WHERE fidx = %s"
            cur.execute(sql_delete, (fidx,))
            conn.commit()
            return {"result": "success"}
    except Exception as e:
        if conn: conn.rollback()
        return {"result": "error", "message": str(e)}
    finally:
        if conn: conn.close()
# if __name__ == "__main__":
#     import uvicorn
#     # 컨테이너 환경에서는 127.0.0.1이 아닌 0.0.0.0으로 띄워야 외부(Nginx)에서 접근 가능합니다.
#     uvicorn.run(app, host="0.0.0.0", port=8000)