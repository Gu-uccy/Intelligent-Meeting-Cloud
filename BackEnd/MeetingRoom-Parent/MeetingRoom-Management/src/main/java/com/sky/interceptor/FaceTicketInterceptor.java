package com.sky.interceptor;

import com.sky.context.BaseContext;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Component;
import org.springframework.web.method.HandlerMethod;
import org.springframework.web.servlet.HandlerInterceptor;

import java.nio.charset.StandardCharsets;
import java.util.List;

/**
 * 刷脸预约的「服务端」强制校验拦截器。
 *
 * 背景：任务书要求人脸识别必须接入会议室业务，且「失败时不能默认放行」。
 * 只在页面上做个弹窗是没有约束力的，因此把校验放到后端：
 *
 *   1. 前端先在自研人脸服务（5001）完成 1:1 核身，拿到一次性凭据 ticket；
 *   2. 前端提交预约时带请求头 X-Face-Ticket；
 *   3. 本拦截器校验：凭据存在 + 属于当前登录用户 + 用途=booking + 未使用 + 未过期；
 *   4. 校验通过后立刻把凭据置为已使用（一次性，防重放）；
 *   5. 不通过直接 403 + JSON，预约不会落库。
 *
 * 凭据表 face_verification 由人脸服务写入、本拦截器消费，两个服务通过 MySQL 解耦。
 * 关闭开关：环境变量 FACE_BOOKING_REQUIRE_TICKET=false（仅用于演示排障，报告需说明）。
 */
@Component
@Slf4j
public class FaceTicketInterceptor implements HandlerInterceptor {

    private final JdbcTemplate jdbcTemplate;

    @Value("${sky.face.require-ticket:true}")
    private boolean requireTicket;

    public FaceTicketInterceptor(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
    }

    @Override
    public boolean preHandle(HttpServletRequest request, HttpServletResponse response, Object handler)
            throws Exception {
        if (!(handler instanceof HandlerMethod)) {
            return true;
        }
        if ("OPTIONS".equalsIgnoreCase(request.getMethod())) {
            return true;
        }
        if (!requireTicket) {
            log.warn("刷脸预约校验已被人为关闭（FACE_BOOKING_REQUIRE_TICKET=false），本次不校验凭据");
            return true;
        }

        String ticket = request.getHeader("X-Face-Ticket");
        Integer userId = BaseContext.getCurrentId();

        if (ticket == null || ticket.isBlank()) {
            return reject(response, "预约必须先通过人脸核验：请点击「刷脸确认」后重试");
        }
        if (userId == null) {
            return reject(response, "未获取到登录用户，请重新登录");
        }

        try {
            List<Long> ids = jdbcTemplate.queryForList(
                    "SELECT fv.id FROM face_verification fv "
                            + "JOIN user u ON u.login_account = fv.login_account "
                            + "WHERE fv.ticket = ? AND u.id = ? AND fv.purpose = 'booking' "
                            + "AND fv.used = 0 AND fv.expire_at > NOW() LIMIT 1",
                    Long.class, ticket, userId);

            if (ids.isEmpty()) {
                log.warn("刷脸凭据无效：ticket={} userId={}", ticket, userId);
                return reject(response, "刷脸凭据无效或已过期，请重新刷脸确认");
            }

            int updated = jdbcTemplate.update(
                    "UPDATE face_verification SET used = 1 WHERE id = ? AND used = 0", ids.get(0));
            if (updated == 0) {
                return reject(response, "刷脸凭据已被使用，请重新刷脸确认");
            }
            log.info("刷脸凭据校验通过：userId={} ticket={}", userId, ticket);
            return true;
        } catch (Exception ex) {
            log.error("刷脸凭据校验异常", ex);
            return reject(response, "人脸凭据校验服务异常，请稍后重试");
        }
    }

    private boolean reject(HttpServletResponse response, String message) throws Exception {
        response.setStatus(403);
        response.setCharacterEncoding(StandardCharsets.UTF_8.name());
        response.setContentType("application/json;charset=UTF-8");
        response.getWriter().write("{\"code\":0,\"msg\":\"" + message + "\",\"data\":null}");
        return false;
    }
}
