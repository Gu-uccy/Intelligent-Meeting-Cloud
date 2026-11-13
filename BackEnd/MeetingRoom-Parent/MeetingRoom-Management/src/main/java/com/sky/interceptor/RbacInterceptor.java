package com.sky.interceptor;

import com.sky.Service.OperationLogService;
import com.sky.Service.RbacService;
import com.sky.context.BaseContext;
import com.sky.entity.User;
import com.sky.Mapper.UserMapper;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;
import org.springframework.web.method.HandlerMethod;
import org.springframework.web.servlet.HandlerInterceptor;

import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Set;

/**
 * RBAC 鉴权拦截器：只管 /admin/**（管理端接口）。
 *
 * 为什么不做成 Spring Security 的 @PreAuthorize：
 *   本项目的鉴权链是「JWT 拦截器 → BaseContext」，SecurityFilterChain 目前对所有路径放行；
 *   若改成 Security 语义，需要额外加 JWT Filter 才能拿到 Authentication，改动面大。
 *   这里用 HandlerInterceptor 复用已有的登录态，职责更单一，也便于把「权限点 → 接口」
 *   这张关系表放在数据库里（permission.url + permission.method）。
 *
 * 判定流程：
 *   1. 未登录（BaseContext 为空）→ 401
 *   2. 该接口没有配置权限点 → 403（fail-closed，宁可多拦不可漏放）
 *   3. 用户权限集合不含所需权限点 → 403，并写一条审计日志（越权访问留痕）
 *   4. 通过 → 放行
 */
@Component
@Slf4j
public class RbacInterceptor implements HandlerInterceptor {

    private final RbacService rbacService;
    private final UserMapper userMapper;
    private final OperationLogService operationLogService;

    public RbacInterceptor(RbacService rbacService, UserMapper userMapper,
                           OperationLogService operationLogService) {
        this.rbacService = rbacService;
        this.userMapper = userMapper;
        this.operationLogService = operationLogService;
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
        String path = request.getRequestURI();
        if (!path.startsWith("/admin/")) {
            return true;
        }

        Integer userId = BaseContext.getCurrentId();
        if (userId == null) {
            return deny(response, request, null, null, 401,
                    "未登录或登录已过期", "未登录访问管理端接口");
        }

        String required = rbacService.requiredCode(path, request.getMethod());
        if (required == null) {
            log.warn("管理端接口 {} {} 未配置权限点，按 fail-closed 拒绝", request.getMethod(), path);
            return deny(response, request, userId, resolveName(userId), 403,
                    "该接口未配置权限点，已拒绝访问", "接口未配置权限点");
        }

        Set<String> owned = rbacService.codesOf(userId);
        if (!owned.contains(required)) {
            List<String> roles = rbacService.roleCodesOf(userId);
            log.warn("越权访问被拒：userId={} roles={} 需要={} 实际拥有={}", userId, roles, required, owned);
            return deny(response, request, userId, resolveName(userId), 403,
                    "无权限访问该接口（需要 " + required + "）",
                    "越权访问：需要 " + required + "，当前角色 " + roles);
        }
        return true;
    }

    private String resolveName(Integer userId) {
        try {
            User user = userMapper.getById(userId);
            return user == null ? null : user.getUsername();
        } catch (Exception ex) {
            return null;
        }
    }

    private boolean deny(HttpServletResponse response, HttpServletRequest request,
                         Integer userId, String userName, int status, String message, String auditDetail)
            throws Exception {
        // 越权与未登录都留痕，「谁在什么时候试图访问什么」可追溯
        try {
            operationLogService.write(userId, userName, "越权/未授权访问",
                    request.getMethod() + " " + request.getRequestURI(), false, auditDetail, 0);
        } catch (Exception ignored) {
            // 审计失败不影响拒绝
        }
        response.setStatus(status);
        response.setCharacterEncoding(StandardCharsets.UTF_8.name());
        response.setContentType("application/json;charset=UTF-8");
        response.getWriter().write("{\"code\":0,\"msg\":\"" + message + "\",\"data\":null}");
        return false;
    }
}
