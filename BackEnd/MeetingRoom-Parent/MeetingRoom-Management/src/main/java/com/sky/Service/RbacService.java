package com.sky.Service;

import lombok.extern.slf4j.Slf4j;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;
import java.util.regex.Pattern;

/**
 * RBAC 鉴权服务：把数据库里的「用户 → 角色 → 权限 → 接口」链路真正用起来。
 *
 * 数据来源全部是已有表：
 *   user_role(用户-角色) → role_permission(角色-权限) → permission(权限点，含 url + method)
 *
 * 判定方式（与建表脚本里 permission.url 的注释一致：「用于接口权限自动匹配」）：
 *   1. 按 url + method 找出当前请求需要哪个 permission_code（精确路径优先于 /** 通配）；
 *   2. 取当前用户拥有的 permission_code 集合；
 *   3. 不包含 → 拒绝。
 *
 * 设计取舍：
 *   - 权限规则懒加载并缓存，避免每个请求打三次表；数据库改了权限点会给出 reload 接口（重启也可）。
 *   - 找不到对应权限点的 /admin/** 接口一律拒绝（fail-closed），宁可多拦不可漏放。
 */
@Service
@Slf4j
public class RbacService {

    private final JdbcTemplate jdbcTemplate;

    /** 编译后的权限规则，按 url 长度降序（精确路径先匹配） */
    private volatile List<Rule> rules;

    public RbacService(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
    }

    private static final class Rule {
        final String code;
        final String method;
        final Pattern pattern;
        /** 原始 url 长度：越长越具体，用于排序（/admin/reservation/page 优先于 /admin/reservation/**） */
        final int specificity;

        Rule(String code, String method, Pattern pattern, int specificity) {
            this.code = code;
            this.method = method;
            this.pattern = pattern;
            this.specificity = specificity;
        }
    }

    /** 把 /admin/room/** 或 /admin/reservation/{id} 这样的模式编译成正则 */
    private static Pattern compile(String url) {
        // 以 /** 结尾表示「本路径及所有子路径」，/admin/room/** 必须能匹配 /admin/room 本身
        if (url.endsWith("/**")) {
            return Pattern.compile("^" + Pattern.quote(url.substring(0, url.length() - 3)) + "(/.*)?$");
        }
        StringBuilder sb = new StringBuilder("^");
        StringBuilder literal = new StringBuilder();
        for (int i = 0; i < url.length(); i++) {
            char c = url.charAt(i);
            if (c == '{') {                       // {id} 之类的路径变量
                if (literal.length() > 0) {
                    sb.append(Pattern.quote(literal.toString()));
                    literal.setLength(0);
                }
                int end = url.indexOf('}', i);
                if (end < 0) {
                    literal.append(c);
                    continue;
                }
                sb.append("[^/]+");
                i = end;
            } else if (c == '*') {                // 单个 * 只匹配一段
                if (literal.length() > 0) {
                    sb.append(Pattern.quote(literal.toString()));
                    literal.setLength(0);
                }
                sb.append("[^/]*");
            } else {
                literal.append(c);
            }
        }
        if (literal.length() > 0) {
            sb.append(Pattern.quote(literal.toString()));
        }
        sb.append("$");
        return Pattern.compile(sb.toString());
    }

    private List<Rule> rules() {
        List<Rule> local = rules;
        if (local != null) {
            return local;
        }
        synchronized (this) {
            if (rules != null) {
                return rules;
            }
            List<Rule> loaded = new ArrayList<>();
            try {
                List<java.util.Map<String, Object>> rows = jdbcTemplate.queryForList(
                        "SELECT permission_code, url, method FROM permission WHERE url IS NOT NULL");
                for (java.util.Map<String, Object> row : rows) {
                    Object code = row.get("permission_code");
                    Object url = row.get("url");
                    Object method = row.get("method");
                    if (code == null || url == null) {
                        continue;
                    }
                    String rawUrl = String.valueOf(url);
                    loaded.add(new Rule(String.valueOf(code),
                            method == null ? null : String.valueOf(method).toUpperCase(),
                            compile(rawUrl), rawUrl.length()));
                }
            } catch (Exception ex) {
                log.error("加载权限规则失败", ex);
            }
            // 按「原始 url 越长越具体」排序，保证 /admin/reservation/page 先于 /admin/reservation/**
            loaded.sort((a, b) -> Integer.compare(b.specificity, a.specificity));
            rules = loaded;
            log.info("RBAC 已加载 {} 条接口权限规则", loaded.size());
            return rules;
        }
    }

    /** 重新加载权限规则（权限表变更后调用） */
    public void reload() {
        synchronized (this) {
            rules = null;
        }
        rules();
    }

    /** 当前请求需要的权限码；找不到返回 null（调用方按 fail-closed 处理） */
    public String requiredCode(String path, String method) {
        String upper = method == null ? "" : method.toUpperCase();
        for (Rule rule : rules()) {
            if (rule.method != null && !rule.method.equals(upper)) {
                continue;
            }
            if (rule.pattern.matcher(path).matches()) {
                return rule.code;
            }
        }
        return null;
    }

    /** 用户拥有的权限码集合（走 user_role → role_permission → permission） */
    public Set<String> codesOf(Integer userId) {
        if (userId == null) {
            return Collections.emptySet();
        }
        try {
            List<String> codes = jdbcTemplate.queryForList(
                    "SELECT DISTINCT p.permission_code FROM permission p "
                            + "JOIN role_permission rp ON rp.permission_id = p.id "
                            + "JOIN user_role ur ON ur.role_id = rp.role_id "
                            + "WHERE ur.user_id = ?",
                    String.class, userId);
            return new LinkedHashSet<>(codes);
        } catch (Exception ex) {
            log.error("查询用户权限失败 userId={}", userId, ex);
            return Collections.emptySet();
        }
    }

    /** 用户是否拥有某权限 */
    public boolean hasPermission(Integer userId, String code) {
        return code != null && codesOf(userId).contains(code);
    }

    /** 用户角色码（用于日志与排查） */
    public List<String> roleCodesOf(Integer userId) {
        if (userId == null) {
            return Collections.emptyList();
        }
        try {
            return jdbcTemplate.queryForList(
                    "SELECT r.role_code FROM role r JOIN user_role ur ON ur.role_id = r.id WHERE ur.user_id = ?",
                    String.class, userId);
        } catch (Exception ex) {
            return Collections.emptyList();
        }
    }
}
