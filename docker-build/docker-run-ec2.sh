#!/bin/bash
# EC2(linux/amd64) 환경용 실행 스크립트
# 강사님 원본(docker-run.sh)과의 차이:
#   - 멀티플랫폼 빌드(buildx) 대신 단순 docker build 사용
#   - DockerHub push 없이 로컬 이미지만 사용

# 1. 기존 컨테이너 및 이미지 정리
echo "Cleaning up old containers and images..."
docker rm -f fastapi-docker-spa nginx-docker-spa 2>/dev/null
docker rmi fastapi:docker-spa nginx:docker-spa 2>/dev/null

# 2. 이미지 빌드 (로컬용, push 없음)
echo "Building fastapi image..."
docker build -t fastapi:docker-spa ./fastAPI

echo "Building nginx image..."
docker build -t nginx:docker-spa ./nginx

# 3. 사용자 네트워크 확인 및 생성
if [ ! "$(docker network ls | grep docker-network)" ]; then
  echo "Creating docker-network..."
  docker network create --driver bridge docker-network
else
  echo "docker-network already exists. skipping..."
fi

# 4. fastapi 컨테이너 실행
docker run -d \
  --name fastapi-docker-spa \
  --network docker-network \
  --restart unless-stopped \
  -p 8000:8000 \
  fastapi:docker-spa

# 5. nginx 컨테이너 실행
docker run -d \
  --name nginx-docker-spa \
  --network docker-network \
  --restart unless-stopped \
  -p 80:80 \
  nginx:docker-spa

echo ""
echo "=== 완료 ==="
echo "Nginx  → http://<EC2_PUBLIC_IP>:80"
echo "FastAPI → http://<EC2_PUBLIC_IP>:8000"
