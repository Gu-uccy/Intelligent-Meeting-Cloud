-- ============================================================
-- 数据库结构与后端代码对齐脚本（PowerShell 版对应文件见 README_RUN.md）
-- 原因：Database/smart-meeting-room-db 的建表脚本与 Java 实体/Mapper 期望的列名不一致：
--   1) user 表用 name，代码用 username
--   2) user 表缺 is_admin、image
--   3) meeting_room 表缺 image、version
-- 本脚本只做「补齐/改名」，不删除任何数据。执行一次即可。
-- 用法： mysql --host=127.0.0.1 --port=3307 --user=root --default-character-set=utf8mb4 \
--        --database=meeting_room_db -e "source Database/align-schema-for-code.sql"
-- ============================================================

-- 1) user.name -> user.username（代码全链路使用 username）
ALTER TABLE user CHANGE COLUMN name username VARCHAR(50) NOT NULL COMMENT '用户姓名（真实姓名）';

-- 2) user 增加 is_admin（0-普通用户，1-管理员）、image（头像）
ALTER TABLE user ADD COLUMN is_admin TINYINT NOT NULL DEFAULT 0 COMMENT '是否管理员（0-普通用户，1-管理员）';
ALTER TABLE user ADD COLUMN image VARCHAR(255) NULL COMMENT '头像地址';

-- 3) meeting_room 增加 image（房间图）、version（并发版本号，代码 updateStatusWithVersion 使用）
ALTER TABLE meeting_room ADD COLUMN image VARCHAR(255) NULL COMMENT '会议室图片地址';
ALTER TABLE meeting_room ADD COLUMN version INT NOT NULL DEFAULT 0 COMMENT '乐观锁版本号';

-- 4) 刷新人脸核验凭据表（前后端 + 人脸服务共用，用于「刷脸才能预约 / 刷脸才能开门」）
CREATE TABLE IF NOT EXISTS face_verification (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ticket VARCHAR(64) NOT NULL COMMENT '凭据票据（UUID）',
    login_account VARCHAR(50) NOT NULL COMMENT '识别出的登录账号（人脸库身份）',
    purpose VARCHAR(20) NOT NULL COMMENT '用途：booking-预约 / access-开门',
    room_id INT NULL COMMENT '开门场景对应的会议室ID',
    confidence DECIMAL(6,4) NULL COMMENT '最高相似度',
    expire_at DATETIME NOT NULL COMMENT '过期时间',
    used TINYINT NOT NULL DEFAULT 0 COMMENT '是否已消费',
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_face_ticket (ticket),
    INDEX idx_face_account_time (login_account, purpose, create_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='人脸核验凭据（刷脸预约/刷脸开门）';

-- 5) 人脸核验审计日志（每次识别都落库，满足任务书「日志与审计」）
CREATE TABLE IF NOT EXISTS face_audit_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    event VARCHAR(20) NOT NULL COMMENT 'enroll / verify / access / deny',
    login_account VARCHAR(50) NULL COMMENT '识别出的身份',
    matched TINYINT NOT NULL DEFAULT 0 COMMENT '是否识别通过',
    confidence DECIMAL(6,4) NULL COMMENT '最高相似度',
    threshold DECIMAL(6,4) NULL COMMENT '当时使用的阈值',
    room_id INT NULL,
    detail VARCHAR(255) NULL COMMENT '拒绝原因或附加说明',
    client_ip VARCHAR(64) NULL,
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_face_audit_time (create_time),
    INDEX idx_face_audit_account (login_account)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='人脸识别审计日志';
