package com.sky;

import org.junit.Test;

import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.util.DigestUtils;

/*@SpringBootTest*/
public class MeetingRoomCommonApplicationTests {

    @Test
    public void contextLoads() {
        System.out.println(DigestUtils.md5DigestAsHex("admin123".getBytes()));
    }

}
