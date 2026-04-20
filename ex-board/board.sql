-- 커뮤니티에 사용할 데이터베이스 생성
CREATE DATABASE IF NOT EXISTS iandb CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
-- 데이터베이스 사용자 권한 생성
CREATE USER 'dev'@'%' IDENTIFIED BY 'dev1234!';
GRANT ALL PRIVILEGES ON iandb.* TO 'dev'@'%';
FLUSH PRIVILEGES;

USE iandb;
-- TABLE 생성
DROP TABLE IF EXISTS tboard;
CREATE TABLE IF NOT EXISTS tboard (
	fidx		int			not null	comment '기본키 컬럼'
,	fnum		int			not null	comment '목록번호'
,	fkey		int			default 0	comment '질문과 답변의 그룹 키 값'
,	fstep		int			default 0	comment '답변에 대한 순서 값'
,	flevel		int			default 0	comment '답변의 구분을 위한 들여쓰기의 값'
,	fuserId	varchar(20)				comment '회원의 경우 ID'
,	fpasswd		varchar(20)	not null	comment '회원의 경우에도 비밀번호는 저장'
,	fuserName	varchar(20)	not null	comment '회원의 이름'
,	fsubject	varchar(50)	not null	comment '게시글 제목'
,	fcontent	text		not null	comment '게시글 내용'
,	fhit		smallint	default 0	comment '조회수'
,	fregdate	datetime	not null	comment '작성일 또는 수정일'
,	primary key (fidx)	
) comment '게시판 정보 테이블';


-- DROP PROCEDURE BoardAppend;

DELIMITER $$
CREATE PROCEDURE BoardAppend(
	IN p_key INT, 
    IN p_level INT, 
    IN p_step INT,
	IN p_userId VARCHAR(20),
    IN p_passwd VARCHAR(20),
    IN p_userName VARCHAR(20),
    IN p_subject VARCHAR(50),
    IN p_content TEXT,
    IN p_hit INT
)
BEGIN
	-- 1. 값을 저장할 로컬 변수 선언
    DECLARE idx INT;
    DECLARE num INT;
    
    -- 2. SELECT ... INTO를 사용하여 변수에 값 대입
    SELECT IFNULL(MAX(fidx) + 1, 1), IFNULL(MAX(fnum) + 1, 1) 
    INTO idx, num 
    FROM tboard;

    -- 3. 변수를 사용하여 INSERT 수행
    IF p_userID IS NULL OR p_userID = '' THEN
		SET p_userID='';
	END IF;
    
    IF p_key = 0 OR p_key IS NULL THEN	-- 질문
		INSERT INTO tboard (fidx, fnum, fkey, flevel, fstep, fuserID, fpasswd, fuserName, fsubject, fcontent, fhit, fregdate)
		values (idx, num, idx, 0, 0, p_userId, p_passwd, p_userName, p_subject, p_content, p_hit, sysdate());
	ELSE	-- 답변인 경우
		SET num = 0;
        SET p_level = p_level + 1;
        
        UPDATE tboard SET
        fstep=fstep+1
        WHERE fkey=p_key and fstep>=p_step;
        
		INSERT INTO tboard (fidx, fnum, fkey, flevel, fstep, fuserID, fpasswd, fuserName, fsubject, fcontent, fhit, fregdate)
		values (idx, num, p_key, p_level, p_step, p_userId, p_passwd, p_userName, p_subject, p_content, p_hit, sysdate());    
    END IF;
END $$
DELIMITER ;




-- 확인하기 위한 코드
-- CALL 프로시저명(p_key, p_level, p_step, userId, passwd, userName, subject, content, hit);
CALL BoardAppend(0, 0, 0, 'tester01', '1234', '홍길동', '첫 번째 질문입니다', '질문 내용입니다.', 0);
-- CALL 프로시저명(p_key, p_level, p_step, userId, passwd, userName, subject, content, hit);
CALL BoardAppend(1, 0, 0, 'tester01', '1234', '홍길동', '첫 번째 답변입니다', '답변 내용', 0);

