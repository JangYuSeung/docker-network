#!/bin/bash
# 1. 기존 컨테이너 및 이미지 정리 (에러 무시를 위해 2>/dev/null 추가)
echo "Cleaning up old containers and images..."
docker rm -f fastapi-docker-spa nginx-docker-spa 2>/dev/null
docker rmi csjin21c/fastapi:docker-spa csjin21c/nginx:docker-spa 2>/dev/null

# 이미지 생성
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t csjin21c/fastapi:docker-spa --push ./fastapi
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t csjin21c/nginx:docker-spa --push ./nginx


# 2. 사용자 네트워크 확인 및 생성
# 이미 있으면 생성하지 않도록 처리
if [ ! "$(docker network ls | grep docker-network)" ]; then
  echo "Creating docker-network..."
  docker network create --driver bridge docker-network
else
  echo "docker-network already exists. skipping..."
fi

# fastapi 컨테이너 실행
docker run -d --name fastapi-docker-spa --network docker-network --restart unless-stopped -p 8000:8000 csjin21c/fastapi:docker-spa

# nginx 컨테이너 실행
docker run -d --name nginx-docker-spa --network docker-network --restart unless-stopped -p 80:80 csjin21c/nginx:docker-spa

