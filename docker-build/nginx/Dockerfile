# 컨테이너 이미지로 nginx:1.29.5를 사용
FROM nginx:1.29.5
# RUN은 컨테이너가 실행되기 이전(이미지)에 실행할 명령어를 작성하는 명령어입니다.
RUN rm /etc/nginx/conf.d/default.conf
# COPY는 컨테이너가 실행되기 이전(이미지)에 파일을 복사하는 명령어입니다.
COPY ./default.conf /etc/nginx/conf.d/default.conf
COPY ./html /usr/share/nginx/html
# 디렉토리와 파일을 구분하여 권한 지정
RUN find /usr/share/nginx/html -type d -exec chmod 755 {} + && \
    find /usr/share/nginx/html -type f -exec chmod 644 {} +
# EXPOSE는 컨테이너가 실행된 이후에 사용할 포트를 지정하는 명령어입니다.
# 서비스(APP)이 실제 사용하고 있는 포트 기재
EXPOSE 80
# CMD는 컨테이너가 실행된 이후에 최초 실행할 명령어를 작성하는 명령어입니다.
CMD ["nginx", "-g", "daemon off;"]