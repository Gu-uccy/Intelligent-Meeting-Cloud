-- ============================================================
-- RBAC 落地脚本：让数据库里的「角色-权限-接口」真正对上代码
--
-- 背景：建表脚本里的 permission.url 用的是设计稿的 REST 规范（/api/reservations/*），
--       而实际接口是 /admin/reservation/page 这种路径，两边对不上，
--       导致 21 个权限点在代码里一个都没被用过（鉴权自然无从谈起）。
--       本脚本把 url 对齐到真实管理端接口，并补两个缺失的权限点。
--
-- 执行： mysql --host=127.0.0.1 --port=3307 --user=root --default-character-set=utf8mb4 \
--          --database=meeting_room_db -e "source Database/rbac-align-endpoints.sql"
-- 幂等： 可重复执行
-- ============================================================

-- 1) 把管理端权限点的 url 指向真实接口（parent 权限用 /** 兜底，子权限用精确路径优先匹配）
UPDATE permission SET url = '/admin/reservation/**',   method = NULL   WHERE permission_code = 'reservation:manage';
UPDATE permission SET url = '/admin/reservation/page', method = 'GET'  WHERE permission_code = 'reservation:query:all';
UPDATE permission SET url = '/admin/reservation/audit',method = 'POST' WHERE permission_code = 'reservation:audit';
UPDATE permission SET url = '/admin/room/**',          method = NULL   WHERE permission_code = 'room:manage';
UPDATE permission SET url = '/admin/equipment/**',     method = NULL   WHERE permission_code = 'fault:handle';
UPDATE permission SET url = '/admin/user/**',          method = NULL   WHERE permission_code = 'user:manage';
UPDATE permission SET url = '/admin/log/**',           method = 'GET'  WHERE permission_code = 'log:query';

-- 2) 补两个真实存在、但权限表里漏掉的接口权限点
INSERT IGNORE INTO permission (permission_code, permission_name, url, method, parent_id, sort, remark)
VALUES ('statistics:view', '查看统计报表', '/admin/statistics/**', 'GET', 17, 25, '管理端首页与统计图表');

INSERT IGNORE INTO permission (permission_code, permission_name, url, method, parent_id, sort, remark)
VALUES ('file:upload', '上传文件', '/admin/common/**', 'POST', 17, 26, '管理端通用上传（会议室图片等）');

-- 3) 授权：系统管理员拿全部；会议室管理员补上统计与上传
INSERT INTO role_permission (role_id, permission_id, create_by)
SELECT r.id, p.id, 'rbac-align'
FROM role r
JOIN permission p ON r.role_code = 'ROLE_SYS_ADMIN'
WHERE NOT EXISTS (
    SELECT 1 FROM (SELECT role_id, permission_id FROM role_permission) x
    WHERE x.role_id = r.id AND x.permission_id = p.id
);

INSERT INTO role_permission (role_id, permission_id, create_by)
SELECT r.id, p.id, 'rbac-align'
FROM role r
JOIN permission p ON r.role_code = 'ROLE_ROOM_ADMIN' AND p.permission_code IN ('statistics:view', 'file:upload')
WHERE NOT EXISTS (
    SELECT 1 FROM (SELECT role_id, permission_id FROM role_permission) x
    WHERE x.role_id = r.id AND x.permission_id = p.id
);

-- 4) 校验查询（执行后可手工看一眼）
-- SELECT r.role_code, COUNT(rp.permission_id) AS perms
--   FROM role r LEFT JOIN role_permission rp ON rp.role_id = r.id
--  GROUP BY r.id, r.role_code;
-- SELECT permission_code, url, method FROM permission WHERE url LIKE '/admin/%' ORDER BY id;
