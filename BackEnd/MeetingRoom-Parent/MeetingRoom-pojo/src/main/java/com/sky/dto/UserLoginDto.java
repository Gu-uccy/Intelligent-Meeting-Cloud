package com.sky.dto;

import lombok.Data;

import java.io.Serializable;

@Data
public class UserLoginDto implements Serializable {

    private String loginAccount;// 用户名
    private String password;// 密码
}
