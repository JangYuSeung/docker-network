#!/bin/bash
# 기존 컨테이너 삭제 (볼륨은 유지하면서 컨테이너와 네트워크만 정리)
docker compose down --remove-orphans

# 최신 이미지를 pull 받으면서 새로 실행
docker compose up -d --pull always