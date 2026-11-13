package com.sky.Service;

import jakarta.servlet.http.HttpServletRequest;
import lombok.extern.slf4j.Slf4j;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.web.context.request.RequestContextHolder;
import org.springframework.web.context.request.ServletRequestAttributes;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardOpenOption;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.concurrent.ThreadLocalRandom;

/**
 * 操作审计落库（operation_log 表）。
 *
 * 三个原则：
 *   1. 不阻塞业务 —— 写库失败只降级写本地文件，绝不把异常抛回业务；
 *   2. 敏感信息脱敏 —— password / token / secret 一律替换成 ***；
 *   3. 可追溯 —— 记录操作人、角色、IP、UA、耗时、结果与错误信息。
 */
@Service
@Slf4j
public class OperationLogService {

    private static final DateTimeFormatter TS = DateTimeFormatter.ofPattern("yyyyMMddHHmmss");
    private static final Path FALLBACK_DIR = Paths.get("logs");
    private static final Path FALLBACK_FILE = FALLBACK_DIR.resolve("operation_log_fallback.log");
    private static final int MAX_CONTENT = 480;

    private final JdbcTemplate jdbcTemplate;

    public OperationLogService(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
    }

    /** 取当前请求（非 Web 线程返回 null） */
    public static HttpServletRequest currentRequest() {
        try {
            ServletRequestAttributes attrs =
                    (ServletRequestAttributes) RequestContextHolder.getRequestAttributes();
            return attrs == null ? null : attrs.getRequest();
        } catch (Exception ex) {
            return null;
        }
    }

    /** 密码 / token 脱敏 */
    public static String mask(String text) {
        if (text == null) {
            return null;
        }
        return text
                .replaceAll("(?i)(\"?(?:password|oldPassword|newPassword|confirmPassword)\"?\\s*[:=]\\s*)\"[^\"]*\"", "$1\"***\"")
                .replaceAll("(?i)(\"?(?:password|oldPassword|newPassword|confirmPassword)\"?\\s*[:=]\\s*)[^,}\\s]+", "$1***")
                .replaceAll("(?i)(\"?(?:token|secret|accessKeySecret|jwt)\"?\\s*[:=]\\s*)\"[^\"]*\"", "$1\"***\"");
    }

    private static String clip(String text, int max) {
        if (text == null) {
            return null;
        }
        return text.length() <= max ? text : text.substring(0, max - 3) + "...";
    }

    /**
     * 写一条操作日志。
     *
     * @param userId      操作人 id（可为 null，比如未登录被拦截）
     * @param userName    操作人姓名（冗余存储，避免用户删除后无法追溯）
     * @param type        操作类型，如"新增会议室"
     * @param content     操作内容（已脱敏）
     * @param success     是否成功
     * @param errorMsg    失败原因
     * @param costMs      耗时（毫秒）
     */
    public void write(Integer userId, String userName, String type, String content,
                      boolean success, String errorMsg, long costMs) {
        HttpServletRequest request = currentRequest();
        String ip = clientIp(request);
        String ua = request == null ? null : clip(request.getHeader("User-Agent"), 190);

        String detail = content;
        if (costMs > 0) {
            detail = (detail == null ? "" : detail + " ") + "[耗时 " + costMs + "ms]";
        }

        try {
            jdbcTemplate.update(
                    "INSERT INTO operation_log(log_no, user_id, user_name, operation_type,"
                            + " operation_content, operation_result, ip_address, user_agent, error_msg)"
                            + " VALUES (?,?,?,?,?,?,?,?,?)",
                    nextLogNo(), userId == null ? 0 : userId,
                    userName == null || userName.isBlank() ? "未登录/未知" : userName,
                    clip(type, 48),
                    clip(mask(detail), MAX_CONTENT),
                    success ? 1 : 0,
                    clip(ip, 48),
                    ua,
                    clip(mask(errorMsg), MAX_CONTENT));
        } catch (Exception ex) {
            // 降级：写本地文件，不影响业务
            log.warn("operation_log 写入失败，已降级到本地文件：{}", ex.getMessage());
            fallback(userId, userName, type, detail, success, errorMsg, ip);
        }
    }

    private String nextLogNo() {
        return "LOG" + LocalDateTime.now().format(TS)
                + ThreadLocalRandom.current().nextInt(100, 999);
    }

    private void fallback(Integer userId, String userName, String type, String content,
                          boolean success, String errorMsg, String ip) {
        try {
            Files.createDirectories(FALLBACK_DIR);
            String line = String.join("\t",
                    LocalDateTime.now().toString(),
                    String.valueOf(userId),
                    String.valueOf(userName),
                    String.valueOf(type),
                    String.valueOf(clip(content, 200)),
                    success ? "1" : "0",
                    String.valueOf(clip(errorMsg, 200)),
                    String.valueOf(ip));
            Files.write(FALLBACK_FILE, (line + System.lineSeparator()).getBytes(StandardCharsets.UTF_8),
                    StandardOpenOption.CREATE, StandardOpenOption.APPEND);
        } catch (IOException ignored) {
            log.error("审计日志降级文件写入失败", ignored);
        }
    }

    private static String clientIp(HttpServletRequest request) {
        if (request == null) {
            return null;
        }
        String[] headers = {"X-Forwarded-For", "X-Real-IP", "Proxy-Client-IP"};
        for (String header : headers) {
            String value = request.getHeader(header);
            if (value != null && !value.isBlank() && !"unknown".equalsIgnoreCase(value)) {
                return value.split(",")[0].trim();
            }
        }
        return request.getRemoteAddr();
    }
}
