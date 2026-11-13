package com.sky.aspect;

import com.sky.Service.OperationLogService;
import com.sky.annotation.AuditLog;
import com.sky.context.BaseContext;
import com.sky.entity.User;
import com.sky.Mapper.UserMapper;
import jakarta.servlet.http.HttpServletRequest;
import lombok.extern.slf4j.Slf4j;
import org.aspectj.lang.ProceedingJoinPoint;
import org.aspectj.lang.annotation.Around;
import org.aspectj.lang.annotation.Aspect;
import org.springframework.stereotype.Component;

import java.util.Arrays;

/**
 * 操作审计切面：@AuditLog 标注的方法执行后，把这次操作写进 operation_log。
 *
 * 记录内容：操作人（id + 姓名）、操作类型、脱敏后的入参、成功/失败、失败原因、耗时、IP、UA。
 * 失败不吞异常：业务异常照常抛给全局异常处理器，审计只负责留痕。
 */
@Aspect
@Component
@Slf4j
public class AuditLogAspect {

    private final OperationLogService operationLogService;
    private final UserMapper userMapper;

    public AuditLogAspect(OperationLogService operationLogService, UserMapper userMapper) {
        this.operationLogService = operationLogService;
        this.userMapper = userMapper;
    }

    @Around("@annotation(auditLog)")
    public Object around(ProceedingJoinPoint joinPoint, AuditLog auditLog) throws Throwable {
        long started = System.currentTimeMillis();
        Integer userId = BaseContext.getCurrentId();
        String userName = resolveUserName(userId);
        String content = auditLog.recordArgs() ? describe(joinPoint) : joinPoint.getSignature().toShortString();

        boolean success = true;
        String errorMsg = null;
        try {
            return joinPoint.proceed();
        } catch (Throwable ex) {
            success = false;
            errorMsg = ex.getClass().getSimpleName() + ": " + ex.getMessage();
            throw ex;
        } finally {
            try {
                operationLogService.write(userId, userName, auditLog.value(), content,
                        success, errorMsg, System.currentTimeMillis() - started);
            } catch (Exception logEx) {
                // 审计本身绝不影响业务
                log.warn("审计切面写日志失败：{}", logEx.getMessage());
            }
        }
    }

    private String resolveUserName(Integer userId) {
        if (userId == null) {
            return null;
        }
        try {
            User user = userMapper.getById(userId);
            return user == null ? null : user.getUsername();
        } catch (Exception ex) {
            return null;
        }
    }

    private String describe(ProceedingJoinPoint joinPoint) {
        StringBuilder sb = new StringBuilder(joinPoint.getSignature().getName()).append('(');
        Object[] args = joinPoint.getArgs();
        if (args != null && args.length > 0) {
            // 请求对象（HttpServletRequest）不参与记录
            Object[] printable = Arrays.stream(args)
                    .filter(a -> !(a instanceof HttpServletRequest))
                    .toArray();
            sb.append(OperationLogService.mask(Arrays.toString(printable)));
        }
        return sb.append(')').toString();
    }
}
