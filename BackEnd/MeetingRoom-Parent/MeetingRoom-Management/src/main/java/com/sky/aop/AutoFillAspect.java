package com.sky.aop;

import com.sky.annotation.AutoFill;
import com.sky.constant.AutoFillConstant;
import com.sky.context.BaseContext;
import com.sky.enumeration.OperationType;
import lombok.extern.slf4j.Slf4j;
import org.aspectj.lang.JoinPoint;
import org.aspectj.lang.annotation.Aspect;
import org.aspectj.lang.annotation.Before;
import org.aspectj.lang.annotation.Pointcut;
import org.aspectj.lang.reflect.MethodSignature;
import org.springframework.stereotype.Component;

import java.lang.reflect.Method;
import java.time.LocalDateTime;

@Aspect
@Slf4j
@Component
public class AutoFillAspect {
    @Pointcut("execution(* com.sky.Mapper.*.*(..)) &&@annotation(com.sky.annotation.AutoFill)")
    public void autofillaspect(){}

    @Before("autofillaspect()")
    public void AutoFill(JoinPoint joinPoint){
        log.info("开始执行公共字段填充...");
        //获取当前被拦截的方法上数据库的操作类型（插入还是更新）
        MethodSignature signature = (MethodSignature)joinPoint.getSignature();//方法签名对象
        AutoFill annotation = signature.getMethod().getAnnotation(AutoFill.class);//方法上的注解对象
        OperationType value = annotation.value();//数据库的操作类型

        //获取当前被拦截的方法的参数--实体对象
        Object[] args = joinPoint.getArgs();
        if(args==null||args.length==0){
            return;
        }
        Object entity =args[0];
        //准备赋值的数据
        LocalDateTime now = LocalDateTime.now();
        Integer currentId = BaseContext.getCurrentId();
        //根据当前的操作类型，为对应的属性根据反射操作来赋值
        if(value==OperationType.INSERT){
            //为4个字段赋值
            try {
                Method setCreateTime = entity.getClass().getDeclaredMethod(AutoFillConstant.SET_CREATE_TIME, LocalDateTime.class);
               /* Method setCreateBy = entity.getClass().getDeclaredMethod(AutoFillConstant.SET_CREATE_BY, Integer.class);*/
                Method setUpdateTime = entity.getClass().getDeclaredMethod(AutoFillConstant.SET_UPDATE_TIME, LocalDateTime.class);
               /* Method setUpdateBy = entity.getClass().getDeclaredMethod(AutoFillConstant.SET_UPDATE_BY, Integer.class);*/

                //通过反射为对象属性赋值
                setCreateTime.invoke(entity,now);
                /*setCreateBy.invoke(entity,currentId);*/
                setUpdateTime.invoke(entity,now);
               /* setUpdateBy.invoke(entity,currentId);*/

            } catch (Exception e) {
                throw new RuntimeException(e);
            }

        } else if (value==OperationType.UPDATE) {
            //为2个字段赋值
            try {
                Method setUpdateTime = entity.getClass().getDeclaredMethod(AutoFillConstant.SET_UPDATE_TIME, LocalDateTime.class);
               /* Method setUpdateBy = entity.getClass().getDeclaredMethod(AutoFillConstant.SET_UPDATE_BY, Integer.class);
*/
                //通过反射为对象属性赋值
                setUpdateTime.invoke(entity,now);
                /*setUpdateBy.invoke(entity,currentId);*/

            } catch (Exception e) {
                throw new RuntimeException(e);
            }
    }
}}
