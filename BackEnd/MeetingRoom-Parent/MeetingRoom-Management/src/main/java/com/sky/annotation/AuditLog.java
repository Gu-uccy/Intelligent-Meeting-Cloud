package com.sky.annotation;

import java.lang.annotation.ElementType;
import java.lang.annotation.Retention;
import java.lang.annotation.RetentionPolicy;
import java.lang.annotation.Target;

/**
 * 操作审计注解。
 *
 * 标在管理端的写操作上（新增/修改/删除/审核），由 {@code AuditLogAspect} 环绕拦截，
 * 把「谁、什么时候、从哪个 IP、做了什么、成功还是失败、耗时多少」写入 operation_log 表。
 *
 * 与 RBAC 的分工：
 *   RbacInterceptor 管「能不能做」（拦截前，403 就不进方法）；
 *   AuditLog        管「做过什么」（方法执行后，成功和失败都留痕）。
 */
@Target(ElementType.METHOD)
@Retention(RetentionPolicy.RUNTIME)
public @interface AuditLog {

    /** 操作类型，如「新增会议室」「审核预约」 */
    String value();

    /** 是否记录方法入参（默认记录，密码/token 会被脱敏） */
    boolean recordArgs() default true;
}
