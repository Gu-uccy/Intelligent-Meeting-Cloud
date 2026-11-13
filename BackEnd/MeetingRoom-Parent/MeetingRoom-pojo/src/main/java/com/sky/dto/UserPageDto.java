package com.sky.dto;

import lombok.Data;

import java.io.Serializable;
@Data
public class UserPageDto implements Serializable {
    private int page;
    private int pageSize;
    private String username; // 用户姓名
    private Integer gender; // 性别（1-男，2-女，0-未知）
    private Integer isActive;// 是否激活（0-未激活，1-已激活）
}
