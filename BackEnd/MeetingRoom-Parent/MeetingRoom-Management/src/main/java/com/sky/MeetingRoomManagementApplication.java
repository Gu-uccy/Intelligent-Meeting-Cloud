package com.sky;

import lombok.extern.slf4j.Slf4j;
import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.autoconfigure.security.servlet.SecurityAutoConfiguration;
import org.springframework.cache.annotation.EnableCaching;
import org.springframework.scheduling.annotation.EnableScheduling;
import org.springframework.transaction.annotation.EnableTransactionManagement;

@SpringBootApplication(exclude = {SecurityAutoConfiguration.class})
@EnableCaching
@EnableTransactionManagement
@EnableScheduling//开启任务调度
@Slf4j
public class MeetingRoomManagementApplication {

    public static void main(String[] args) {
        SpringApplication.run(MeetingRoomManagementApplication.class, args);
        log.info("server started");

    }

}
