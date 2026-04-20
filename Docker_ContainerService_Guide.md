# Docker 컨테이너 서비스 올리기 - 실습 가이드

> **실습 목표**: Docker를 사용해 로컬/EC2에서 3계층(DB, Backend, Frontend) 서비스를 직접 구성하고, Kubernetes/RDS와의 차이를 체험으로 이해하기

---

## 📌 Table of Contents
1. [왜 Docker를 배우는가? (vs Kubernetes/RDS)](#왜-docker를-배우는가)
2. [실습 1: docker-build - 기초 실습](#실습-1-docker-build---기초-실습)
3. [실습 2: ex-board - 완전한 서비스 구성](#실습-2-ex-board---완전한-서비스-구성)
4. [Docker vs Kubernetes vs RDS 선택 기준](#docker-vs-kubernetes-vs-rds-선택-기준)
5. [핵심 코드 상세 분석](#핵심-코드-상세-분석)

---

## 🤔 왜 Docker를 배우는가?

### 문제 상황: 이전 EKS + RDS 환경의 한계

**이전 학습 (Kubernetes/EKS + RDS)**
```
┌─────────────────────────────────────────────────────────┐
│                    AWS 환경                              │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  ┌─────────────┐              ┌──────────────┐           │
│  │   EKS       │              │    RDS       │           │
│  │  Cluster    │──YAML───────→│  (MySQL)     │           │
│  │  (K8s)      │ Manifests    │  Managed     │           │
│  └─────────────┘              └──────────────┘           │
│                                                           │
│  장점: 자동 스케일링, 자가 치유, 고가용성               │
│  단점: 복잡도 높음, 학습 곡선 가파름                    │
│        개발/테스트 환경 구성 어려움                      │
└─────────────────────────────────────────────────────────┘
```

**한계**
- 로컬 PC에서 즉시 테스트 불가능
- AWS 환경 없으면 실습 불가능
- 개발 중 빌드-배포 사이클 길음
- 각 엔지니어가 다른 환경에서 작업 시 재현 어려움> 
- DB 관리형 서비스(RDS)는 우리 코드 기반으로 최적화 불가능

### Docker가 해결하는 문제

```
┌──────────────────────────────────────────────────────────┐
│           Docker 환경 (로컬 + EC2)                        │
├──────────────────────────────────────────────────────────┤
│                                                            │
│  개발 PC              EC2                 프로덕션         │
│  ┌─────────────┐    ┌──────────────┐    ┌──────────────┐ │
│  │ MySQL       │    │ MySQL        │    │ RDS/Aurora   │ │
│  │ FastAPI     │ == │ FastAPI      │ == │ ECS/EKS      │ │
│  │ Nginx       │    │ Nginx        │    │ ALB/NLB      │ │
│  └─────────────┘    └──────────────┘    └──────────────┘ │
│   docker-compose      docker-compose      Docker Swarm   │
│   (개발/테스트)        (사전검증)          또는 K8s       │
│                                                            │
│  ✅ 동일한 환경        ✅ 배포 전 검증    ✅ 규모 확장     │
│  ✅ 빠른 반복           ✅ 버전 관리       ✅ 고가용성     │
│  ✅ 팀원과 공유        ✅ CI/CD 용이      ✅ 자동 복구    │
└──────────────────────────────────────────────────────────┘
```

### Docker를 배우는 3가지 이유

| 항목 | 설명 |
|------|------|
| **1. 환경 일관성** | "제 PC에서는 잘 되는데..."를 영구히 제거. 동일 이미지 = 동일 동작 |
| **2. 개발 속도** | 로컬에서 즉시 테스트. AWS/K8s 없이도 완전한 스택 체험 가능 |
| **3. 경력 경로** | Docker → Docker Compose → Docker Swarm/Kubernetes 단계적 성장 |

---

## 🏗️ 실습 1: docker-build - 기초 실습

### 목표
Nginx(프론트엔드) + FastAPI(백엔드)를 수동으로 빌드하고, 도커 네트워크로 연결하기

### 구조도

```
┌────────────────────────────────────────────────────┐
│              Host (EC2 또는 로컬)                   │
├────────────────────────────────────────────────────┤
│                                                     │
│  ┌──────────────────────────────────────────┐     │
│  │      docker-network (bridge)             │     │
│  │                                          │     │
│  │  ┌──────────────┐    ┌──────────────┐  │     │
│  │  │   Nginx      │    │   FastAPI    │  │     │
│  │  │   :80        │───→│   :8000      │  │     │
│  │  │ (ReverseProxy)   │ (API Server) │  │     │
│  │  └──────────────┘    └──────────────┘  │     │
│  │                                          │     │
│  └──────────────────────────────────────────┘     │
│       ↓                                             │
│   80포트 외부 노출                                   │
│   (브라우저 접속)                                    │
└────────────────────────────────────────────────────┘
```

### 실습 순서 (EC2 환경)

#### 1단계: 디렉터리 구조 확인

```
docker-build/
├── docker-run-ec2.sh          # EC2용 실행 스크립트 (이 환경)
├── docker-run.sh              # DockerHub push용 (생략)
├── fastAPI/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py
│       └── templates/
│           └── index.html
└── nginx/
    ├── Dockerfile
    ├── default.conf            # Nginx 프록시 설정
    └── html/
        └── index.html
```

#### 2단계: 이미지 빌드

```bash
# 1. FastAPI 이미지 빌드
docker build -t fastapi:docker-spa ./fastAPI

# 2. Nginx 이미지 빌드
docker build -t nginx:docker-spa ./nginx

# 3. 이미지 확인
docker images | grep docker-spa
```

#### 3단계: 도커 네트워크 생성

```bash
docker network create --driver bridge docker-network
```

**왜 필요한가?**
- 컨테이너끼리 `localhost`로는 통신 불가
- 도커 내부 DNS를 통해 컨테이너명으로 통신 가능
- Nginx 설정에서 `http://fastapi-docker-spa:8000/`로 접근 가능

#### 4단계: 컨테이너 실행

```bash
# FastAPI 컨테이너 실행
docker run -d \
  --name fastapi-docker-spa \
  --network docker-network \
  --restart unless-stopped \
  -p 8000:8000 \
  fastapi:docker-spa

# Nginx 컨테이너 실행
docker run -d \
  --name nginx-docker-spa \
  --network docker-network \
  --restart unless-stopped \
  -p 80:80 \
  nginx:docker-spa
```

#### 5단계: 검증

```bash
# 상태 확인
docker ps --format "table {{.Names}}\t{{.Ports}}"

# 직접 API 호출
curl http://localhost/              # Nginx 정적 페이지
curl http://localhost:8000/         # FastAPI 직접 접근
```

### 핵심 파일 분석

#### FastAPI Dockerfile

```dockerfile
# 1. 가벼운 Python 3.11 슬림 이미지 사용
FROM python:3.11-slim

# 2. 컨테이너 내 작업 디렉토리 설정
WORKDIR /app

# 3. 종속성 파일 복사 및 설치 (캐싱 효율을 위해 소스 코드보다 먼저 복사)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. app 디렉토리 전체를 컨테이너의 /app으로 복사
COPY ./app /app

# 5. FastAPI 실행 (포트 8000)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**설명:**
- `FROM`: 베이스 이미지 (3.11-slim = 일반 Python 대비 1/4 크기)
- `COPY requirements.txt .` → `RUN pip install`: 종속성 레이어 캐싱 (빌드 속도 ⬇️)
- `--host 0.0.0.0`: 모든 인터페이스에서 수신 (컨테이너 외부 접근 가능)

#### Nginx Dockerfile & 프록시 설정

```dockerfile
FROM nginx:1.29.7-alpine

# 기본 설정 파일 제거 및 커스텀 설정 복사
RUN rm /etc/nginx/conf.d/default.conf
COPY ./default.conf /etc/nginx/conf.d/default.conf

# 정적 파일 복사
COPY ./html /usr/share/nginx/html

# 권한 설정
RUN chmod -R 644 /usr/share/nginx/html

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

**Nginx 리버스 프록시 설정 (default.conf)**

```nginx
server {
    listen 80;
    server_name _;

    # 1. 프론트엔드 정적 파일
    location / {
        root /usr/share/nginx/html;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    # 2. FastAPI 백엔드 프록시
    location /api/ {
        # 마지막 /를 붙이면 /api/를 제거하고 FastAPI로 전달
        # 예: /api/users → http://fastapi-docker-spa:8000/users
        proxy_pass http://fastapi-docker-spa:8000/;
        
        # 클라이언트 정보 전달
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

**핵심 포인트:**
- `proxy_pass http://fastapi-docker-spa:8000/`: 도커 컨테이너명으로 자동 DNS 해석
- `proxy_set_header X-Real-IP`: 원본 클라이언트 IP를 FastAPI에 전달

---

## 📦 실습 2: ex-board - 완전한 서비스 구성

### 목표
MySQL + FastAPI + Nginx 3계층을 Docker Compose로 자동화하고, 게시판 기능 완성하기

### 구조도

```
┌──────────────────────────────────────────────────────────┐
│        Docker Compose 환경 (ex-board)                     │
├──────────────────────────────────────────────────────────┤
│                                                            │
│  ┌────────────────────────────────────────────────┐      │
│  │       board-network (bridge)                   │      │
│  │                                                │      │
│  │  ┌──────────────┐  ┌─────────────┐  ┌──────┐ │      │
│  │  │   Nginx      │  │  FastAPI    │  │MySQL │ │      │
│  │  │  :80         │→ │  :8000      │→ │:3306 │ │      │
│  │  │              │  │  (CRUD Ops) │  │tboard│ │      │
│  │  └──────────────┘  └─────────────┘  └──────┘ │      │
│  │                                                │      │
│  │  depends_on: MySQL → FastAPI → Nginx          │      │
│  └────────────────────────────────────────────────┘      │
│       ↓ 외부 노출: 80, 3306, 8000                        │
│   브라우저/DB클라이언트/API테스트                         │
└──────────────────────────────────────────────────────────┘
```

### 실습 순서

#### 1단계: 포트 충돌 정리

```bash
# 기존 컨테이너 확인
docker ps --format "table {{.Names}}\t{{.Ports}}"

# 80/8000 점유 컨테이너 정리
docker rm -f fastapi-docker-spa nginx-docker-spa
```

**이유:** ex-board는 동일한 포트(80, 8000)를 사용하므로 선행 정리 필수

#### 2단계: 이미지 빌드 (EC2 환경 고려)

```bash
cd /home/ec2-user/[학습자료25] 도커 컨테이너 서비스 올리기/ex-board

# ❌ docker compose --build는 buildx 요구 (EC2에서 실패 가능)
# ✅ 대신 개별 빌드
docker build -t mysql:8.0-board-local ./mysql
docker build -t fastapi:board-proxy-local ./fastapi
docker build -t nginx:board-local ./nginx
```

**EC2 특수성:**
- `docker compose --build`는 buildx 플러그인 필요
- 멀티플랫폼 빌드 미지원 환경 대비 개별 빌드로 안정화

#### 3단계: Compose 기동

```bash
docker compose -f docker-compose-ec2.yaml up -d

# 상태 확인 (모두 Up 상태 확인)
docker compose -f docker-compose-ec2.yaml ps
```

#### 4단계: 서비스 검증

```bash
# API 테스트 (MySQL 초기 데이터 확인)
curl http://localhost/api/board/list

# 예상 응답:
# {
#   "items": [
#     {"fidx":1, "fsubject":"첫 번째 질문입니다", ...},
#     {"fidx":2, "fsubject":"첫 번째 답변입니다", ...}
#   ],
#   "total_count": 2
# }
```

### docker-compose-ec2.yaml 상세 분석

```yaml
services:
  # 1. 데이터베이스 계층
  service-board-mysql:
    image: mysql:8.0-board-local
    build:
      context: ./mysql
      dockerfile: Dockerfile
    container_name: mysql-primary-container
    restart: unless-stopped
    environment:
      MYSQL_ROOT_PASSWORD: "ian1234!"
      MYSQL_DATABASE: "iandb"
      MYSQL_USER: "ian"
      MYSQL_PASSWORD: "ian1234!"
      TZ: "Asia/Seoul"
    ports:
      - "3306:3306"  # 외부 DB 클라이언트 접속용
    networks:
      - board-network

  # 2. 애플리케이션 계층
  service-board-fastapi:
    image: fastapi:board-proxy-local
    build:
      context: ./fastapi
      dockerfile: Dockerfile
    container_name: board-fastapi-container
    restart: always  # 서비스 중지 시 자동 재시작
    depends_on:
      - service-board-mysql  # MySQL 먼저 시작
    environment:
      # 컨테이너명 사용 (도커 내부 DNS 자동 해석)
      DB_HOST: "mysql-primary-container"
      DB_USER: "dev"
      DB_PASSWORD: "dev1234!"
      DB_NAME: "iandb"
    ports:
      - "8000:8000"  # API 직접 테스트용
    networks:
      - board-network

  # 3. 웹 서버 계층
  service-board-nginx:
    image: nginx:board-local
    build:
      context: ./nginx
      dockerfile: Dockerfile
    container_name: board-nginx-container
    restart: always
    depends_on:
      - service-board-fastapi
    ports:
      - "80:80"  # 사용자 진입점
    networks:
      - board-network

# 도커 내부 네트워크 정의
networks:
  board-network:
    driver: bridge
```

**핵심 개념:**
- `depends_on`: 시작 순서만 보장 (준비 완료는 보장 ❌)
- `DB_HOST: "mysql-primary-container"`: 도커 내부 DNS 자동 해석
- `environment`: 컨테이너에서 환경변수로 접근 가능 (`os.getenv()`)

### FastAPI DB 연결 코드 분석

```python
import os
import pymysql

# 환경변수에서 DB 설정 읽기
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "mysql-primary-container"),
    "user": os.getenv("DB_USER", "dev"),
    "password": os.getenv("DB_PASSWORD", "dev1234!"),
    "db": os.getenv("DB_NAME", "iandb"),
    "port": 3306,
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor  # 결과를 딕셔너리로 반환
}

def get_db_conn():
    """DB 연결 풀 대신 매 요청마다 신규 연결 (소규모 서비스용)"""
    return pymysql.connect(**DB_CONFIG)

@app.get("/list")
def board_list(page: int = 1):
    conn = None
    try:
        conn = get_db_conn()
        with conn.cursor() as cursor:
            # 페이징 계산
            size = 10
            offset = (page - 1) * size
            
            # 전체 게시글 수 조회
            cursor.execute("SELECT COUNT(*) as cnt FROM tboard")
            total_count = cursor.fetchone()['cnt']
            
            # 게시글 목록 조회 (최신 기준으로 정렬)
            sql = """
                SELECT fidx, fnum, fkey, flevel, fstep, fuserName, 
                       fsubject, fhit, fregdate 
                FROM tboard 
                ORDER BY fkey DESC, fstep DESC 
                LIMIT %s OFFSET %s
            """
            cursor.execute(sql, (size, offset))
            result = cursor.fetchall()
            
            return {
                "items": result,
                "total_count": total_count,
                "page": page,
                "size": size
            }
    except Exception as e:
        return {"error": str(e)}
    finally:
        if conn:
            conn.close()
```

**설명:**
- `os.getenv()`: compose 파일의 `environment`에서 읽은 값
- `DictCursor`: 쿼리 결과를 `list`/`dict` 형태로 반환 (JSON 직렬화 용이)
- `LIMIT & OFFSET`: 페이징 구현

### MySQL 초기화 (init.sql) 핵심

```sql
-- 1. 사용자 권한 설정
CREATE USER 'dev'@'%' IDENTIFIED BY 'dev1234!';
GRANT ALL PRIVILEGES ON iandb.* TO 'dev'@'%';
FLUSH PRIVILEGES;

-- 2. 테이블 생성
CREATE TABLE tboard (
    fidx INT NOT NULL PRIMARY KEY COMMENT '기본키',
    fnum INT NOT NULL COMMENT '목록번호',
    fkey INT DEFAULT 0 COMMENT '부모글 ID (Q&A 그룹)',
    flevel INT DEFAULT 0 COMMENT '들여쓰기 (답변 깊이)',
    fstep INT DEFAULT 0 COMMENT '답변 순서',
    fuserName VARCHAR(20) NOT NULL,
    fpasswd VARCHAR(20) NOT NULL,
    fsubject VARCHAR(50) NOT NULL,
    fcontent TEXT NOT NULL,
    fhit SMALLINT DEFAULT 0 COMMENT '조회수',
    fregdate DATETIME NOT NULL,
    PRIMARY KEY (fidx)
);

-- 3. 게시글 삽입 프로시저 (Q&A 계층 관리)
DELIMITER $$
CREATE PROCEDURE BoardAppend(
    IN p_key INT,         -- 부모글 ID (0=질문, >0=답변)
    IN p_level INT,       -- 들여쓰기 레벨
    IN p_step INT,        -- 답변 내 순서
    IN p_userId VARCHAR(20),
    IN p_passwd VARCHAR(20),
    IN p_userName VARCHAR(20),
    IN p_subject VARCHAR(50),
    IN p_content TEXT,
    IN p_hit INT
)
BEGIN
    DECLARE idx INT;
    DECLARE num INT;
    
    -- 다음 ID 계산
    SELECT IFNULL(MAX(fidx) + 1, 1), IFNULL(MAX(fnum) + 1, 1) 
    INTO idx, num 
    FROM tboard;
    
    IF p_key = 0 OR p_key IS NULL THEN
        -- 질문: fkey = 자신의 ID (그룹 헤더)
        INSERT INTO tboard (fidx, fnum, fkey, flevel, fstep, ...) 
        VALUES (idx, num, idx, 0, 0, ...);
    ELSE
        -- 답변: fkey = 부모 ID (그룹 소속)
        -- 기존 답변들의 fstep 업데이트 (순서 밀려남)
        UPDATE tboard SET fstep = fstep + 1 
        WHERE fkey = p_key AND fstep >= p_step;
        
        INSERT INTO tboard (fidx, fnum, fkey, flevel, fstep, ...) 
        VALUES (idx, num, p_key, p_level + 1, p_step, ...);
    END IF;
END $$
DELIMITER ;

-- 4. 샘플 데이터
CALL BoardAppend(0, 0, 0, 'tester01', '1234', '홍길동', '첫 번째 질문입니다', '질문 내용입니다.', 0);
CALL BoardAppend(1, 0, 0, 'tester01', '1234', '홍길동', '첫 번째 답변입니다', '답변 내용', 0);
```

**Q&A 구조 설명:**

| fidx | fkey | flevel | fstep | fsubject |
|------|------|--------|-------|----------|
| 1 | 1 | 0 | 1 | 첫 번째 질문입니다 |
| 2 | 1 | 1 | 0 | ↳ 첫 번째 답변입니다 |

- `fkey = 1`: 글 1의 그룹에 소속
- `flevel = 0`: 질문 (들여쓰기 0)
- `flevel = 1`: 첫 번째 답변 (들여쓰기 1칸)

### 프론트엔드 API 호출 (중요한 고정 포인트)

**Before (127.0.0.1 하드코딩 - ❌ EC2 접속 시 실패)**
```javascript
// list.html
$.ajax({
    url: "http://127.0.0.1/api/board/list",  // 브라우저PC의 localhost 지칭
    type: "GET",
    success: function(res) { ... }
});
```

**After (상대경로 - ✅ 어디서나 동작)**
```javascript
// list.html (수정됨)
$.ajax({
    url: "/api/board/list",  // 현재 도메인 기준 (자동으로 98.130.135.150/api/board/list)
    type: "GET",
    success: function(res) { ... }
});
```

**왜 상대경로인가?**
```
브라우저에서 http://98.130.135.150 접속
  ↓
JavaScript에서 /api/board/list 호출
  ↓
= http://98.130.135.150/api/board/list (자동 해석)
  ↓
Nginx 프록시 (default.conf)
  ↓
내부 http://board-fastapi-container:8000/ (프록시)
  ↓
FastAPI 응답
```

---

## 🎯 Docker vs Kubernetes vs RDS 선택 기준

### 비교표

| 항목 | Docker Compose | Kubernetes (EKS) | RDS + ECS |
|------|---|---|---|
| **학습곡선** | ⭐ 낮음 | ⭐⭐⭐⭐⭐ 매우 높음 | ⭐⭐ 중간 |
| **배포 시간** | 5초 | 3~5분 | 1~2분 |
| **개발 환경** | 로컬 PC ✅ | AWS 필수 ❌ | AWS 필수 ❌ |
| **스케일링** | 수동 | 자동 (HPA) | 반자동 |
| **자가 치유** | ❌ | ✅ 자동 복구 | ⚠️ 제한적 |
| **DB 관리** | 직접 관리 | 직접 관리 | AWS 관리 ✅ |
| **팀원 공유** | docker-compose.yaml ✅ | 복잡한 YAML | 복잡한 코드 |
| **비용** | 저 (EC2만) | 중 (EKS 고정 비용) | 고 (RDS 비쌈) |
| **권장 규모** | 소규모 (10대 이하) | 대규모 (100대 이상) | 중규모 (엔터프라이즈) |

### 의사결정 플로우

```
프로젝트 시작
  │
  ├─ "1명 개발자, 3개월 스프린트"
  │  └─→ Docker Compose ✅
  │
  ├─ "10명 팀, 24/7 가용성, 트래픽 예측 불가"
  │  └─→ Kubernetes (EKS) ✅
  │
  ├─ "스타트업, 빠른 출시, DB 관리 부담 최소화"
  │  └─→ RDS + ECS ✅
  │
  └─ "기업, 멀티 리전, 엄격한 규정 준수"
     └─→ RDS + EKS + Multi-Region ✅
```

### 각 환경의 실제 사용처

**Docker Compose 사용처**
```
✅ 마이크로서비스 로컬 테스트
✅ CI/CD 파이프라인 통합 테스트
✅ 개발 팀 온보딩 (1시간 내 환경 구성)
✅ 작은 팀의 프로토타입 배포
✅ 모놀리식 앱 컨테이너화
```

**Kubernetes 사용처**
```
✅ 서비스별 자동 스케일링
✅ 카나리 배포, 블루-그린 배포
✅ 장애 자동 복구 (Pod 재시작)
✅ 대규모 트래픽 (일일 수십억 요청)
✅ 멀티 테넌트 환경
```

**RDS + 관리형 서비스**
```
✅ DB 백업/복제 자동화
✅ 읽기 복제본으로 자동 스케일 아웃
✅ 자동 장애 조치 (Multi-AZ)
✅ 성능 모니터링/자동 최적화
✅ 보안 패치 자동 적용
```

---

## 💻 핵심 코드 상세 분석

### 1. 도커 네트워크와 DNS (왜 localhost가 안 되는가?)

**문제 상황**
```python
# 이 코드는 로컬 PC에서만 동작 ❌
conn = pymysql.connect(host="localhost", port=3306)  # 컨테이너 내부에서 실행 시 자신을 가리킴
```

**해결책 (도커 내부 DNS)**
```yaml
# docker-compose.yaml
services:
  db:
    container_name: mysql-primary-container
    ...
  
  app:
    depends_on:
      - db
    environment:
      DB_HOST: "mysql-primary-container"  # ← 컨테이너명이 DNS 자동 해석
```

```python
# FastAPI 코드
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "mysql-primary-container"),  # ✅ 도커 DNS 사용
    ...
}
```

**내부 동작**
```
FastAPI 컨테이너에서:
  socket.getaddrinfo("mysql-primary-container", 3306)
    ↓
  도커 내부 DNS 서버 (127.0.0.11:53)에 쿼리
    ↓
  MySQL 컨테이너의 IP 반환 (예: 172.18.0.2)
    ↓
  TCP 연결 성공
```

### 2. Nginx 리버스 프록시의 경로 변환

**핵심: proxy_pass 뒤의 슬래시(/) 유무**

```nginx
# ❌ proxy_pass http://backend:8000
# 요청: GET /api/users/123
# 전달: GET /api/users/123

# ✅ proxy_pass http://backend:8000/
# 요청: GET /api/users/123
# 전달: GET /users/123 (location 경로 제거)
```

**ex-board 설정 분석**
```nginx
location /api/board/ {
    proxy_pass http://board-fastapi-container:8000/;
    # 요청 URL: GET /api/board/list
    # FastAPI로 전달: GET /list
    #
    # FastAPI의 @app.get("/list")가 처리
}
```

**클라이언트 정보 전달**
```nginx
proxy_set_header Host $host;                          # 원본 Host 헤더
proxy_set_header X-Real-IP $remote_addr;              # 클라이언트 IP
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;  # 프록시 체인 IP
proxy_set_header X-Forwarded-Proto $scheme;           # 원본 프로토콜 (http/https)
```

**FastAPI에서 활용**
```python
from fastapi import Request

@app.get("/info")
def get_client_info(request: Request):
    return {
        "client_ip": request.client.host,  # Nginx가 설정한 X-Real-IP 읽음
        "forwarded_for": request.headers.get("X-Forwarded-For"),
        "user_agent": request.headers.get("user-agent")
    }
```

### 3. Docker 환경변수 vs 시스템 환경변수

**어떻게 FastAPI가 MySQL 포트를 알까?**

```python
import os

# 방법 1: 하드코딩 (❌ 환경별 다시 빌드 필요)
host = "mysql-primary-container"
port = 3306

# 방법 2: 환경변수 (✅ 이미지 재빌드 없이 값 변경)
host = os.getenv("DB_HOST", "localhost")
port = int(os.getenv("DB_PORT", 3306))
```

**docker-compose.yaml에서 주입**
```yaml
service-board-fastapi:
  environment:
    DB_HOST: "mysql-primary-container"
    DB_PORT: "3306"
    DB_USER: "dev"
```

**컨테이너 내부에서 확인**
```bash
docker exec board-fastapi-container env | grep DB_
# DB_HOST=mysql-primary-container
# DB_PORT=3306
# DB_USER=dev
```

**배포 환경에서 변경 (rebuild 없이)**
```bash
# 로컬 개발
export DB_HOST=localhost

# EC2 테스트
export DB_HOST=mysql-prod.example.com

# 프로덕션 (RDS)
export DB_HOST=iandb.ch5vp9zp0tpl.ap-northeast-2.rds.amazonaws.com
```

### 4. depends_on vs 실제 준비 완료

**문제: MySQL이 아직 준비 안 됐는데 FastAPI가 시작됨**

```yaml
service-board-fastapi:
  depends_on:
    - service-board-mysql
  # depends_on은 "컨테이너 시작 순서"만 보장
  # MySQL이 3306 포트 open을 완료할 때까지 기다리지 않음!
```

**해결책 1: 환경 변수로 재시도 (FastAPI 코드)**
```python
import time
import pymysql

def get_db_conn():
    max_retries = 5
    for attempt in range(max_retries):
        try:
            return pymysql.connect(**DB_CONFIG)
        except pymysql.Error:
            if attempt < max_retries - 1:
                time.sleep(2)  # 2초 대기 후 재시도
            else:
                raise
```

**해결책 2: 헬스체크 (docker-compose.yaml)**
```yaml
service-board-mysql:
  healthcheck:
    test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
    interval: 10s
    timeout: 5s
    retries: 5

service-board-fastapi:
  depends_on:
    service-board-mysql:
      condition: service_healthy  # MySQL 정상까지 대기
```

---

## 🚀 실제 배포 시 예상 시나리오

### 로컬 개발 → EC2 테스트 → 프로덕션

```
┌─────────────────┐
│  로컬 PC        │
│ (개발자)         │
└────────┬────────┘
         │
         │ git push
         ↓
┌────────────────────┐
│   GitHub           │
│ (docker-compose)   │
└────────┬───────────┘
         │
         │ CI/CD (GitHub Actions)
         │ - 테스트 컨테이너 구성
         │ - 통합 테스트 실행
         │ - ECR 이미지 push
         ↓
┌────────────────────────┐
│   AWS ECR             │
│ (이미지 저장소)         │
└────────┬──────────────┘
         │
         │ Terraform / CloudFormation
         ↓
┌────────────────────────────────────┐
│   AWS ECS / EKS                    │
│ (프로덕션 컨테이너 오케스트레이션)  │
│                                    │
│ - Auto Scaling                     │
│ - Load Balancer                    │
│ - RDS (MySQL 관리형)               │
└────────────────────────────────────┘
```

### 이 실습이 준비하는 것

| 단계 | 학습 항목 | ex-board에서 체험 |
|------|---------|---------|
| 1 | 환경 일관성 | 로컬 compose == EC2 compose |
| 2 | 마이크로서비스 | MySQL/FastAPI/Nginx 분리 |
| 3 | 네트워킹 | 도커 내부 DNS, 프록시 |
| 4 | 상태 관리 | 환경변수, 헬스체크 |
| 5 | 자동화 | 단일 명령으로 3계층 배포 |

---

## 📝 실습 체크리스트

### docker-build 완료 기준

- [ ] `docker images | grep docker-spa` 에 2개 이미지 표시
- [ ] `docker network ls | grep docker-network` 표시
- [ ] `curl http://localhost/` 정적 페이지 로드
- [ ] `curl http://localhost:8000/` FastAPI 응답
- [ ] `curl http://localhost/api/` 프록시 경로 동작

### ex-board 완료 기준

- [ ] `docker compose -f docker-compose-ec2.yaml ps` 모두 Up
- [ ] `curl http://localhost/api/board/list` JSON 응답 (2개 샘플 데이터)
- [ ] `http://EC2_PUBLIC_IP/` 브라우저 접속 → 게시판 목록 페이지 로드
- [ ] 글쓰기 → 조회 → 수정 → 삭제 전체 플로우 동작

### 심화 과제 (선택)

- [ ] MySQL 컨테이너 내 `mysql -u dev -p1234!` 접속 → `SELECT * FROM tboard;`
- [ ] Nginx 로그 확인: `docker logs board-nginx-container | tail -20`
- [ ] FastAPI 페이지 소스 보기 → API 경로가 상대경로(/api/board/...)인지 확인
- [ ] 컨테이너 통신 테스트: `docker exec board-fastapi-container curl http://mysql-primary-container:3306 2>&1 | head`

---

## 🎓 학습 결과

이 실습을 통해 학습자는 다음을 이해할 수 있습니다:

✅ **Docker 기초**
- Dockerfile 작성 및 빌드
- 이미지 vs 컨테이너 차이
- 컨테이너 라이프사이클

✅ **Docker Compose**
- 다중 컨테이너 자동 조직화
- 환경 변수 관리
- 의존성 정의

✅ **마이크로서비스 아키텍처**
- 각 서비스 독립성
- 네트워킹 (DNS, 프록시)
- 상태 분리 (DB 외부화)

✅ **배포 파이프라인**
- 로컬 개발 환경 재현
- 사전 검증 (EC2)
- 프로덕션 준비 (K8s/RDS 호환성)

✅ **선택과 결정**
- 도구 선택의 기준
- 규모별 적정 솔루션
- 기술 부채 vs 복잡도 트레이드오프

---

## 📚 참고 자료

- [Docker 공식 문서](https://docs.docker.com/)
- [Docker Compose 버전 3](https://docs.docker.com/compose/compose-file/compose-file-v3/)
- [Nginx 프록시 설정](https://nginx.org/en/docs/http/ngx_http_proxy_module.html)
- [FastAPI 환경변수](https://fastapi.tiangolo.com/deployment/concepts/#environment-variables)

---

**최종 작성일**: 2026-04-20
**버전**: 1.0
**대상**: Docker 초급 ~ 중급 학습자
