package com.sky.config;

import lombok.extern.slf4j.Slf4j;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.EnableAspectJAutoProxy;

/**
 * 审计切面的开关：显式开启 AspectJ 自动代理。
 * 项目依赖里已有 aspectjweaver，这里显式声明，避免不同 Spring Boot 版本自动配置差异。
 */
@Configuration
@EnableAspectJAutoProxy(proxyTargetClass = true, exposeProxy = true)
@Slf4j
public class RbacConfig {
    public RbacConfig() {
        log.info("RBAC 审计切面已开启（@AuditLog + operation_log）");
    }
}
