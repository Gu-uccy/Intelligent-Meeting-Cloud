package com.sky.vo;

import lombok.Data;

import java.io.Serializable;
import java.time.LocalDateTime;
@Data
public class UserVo implements Serializable {
    private Integer id;
    private String loginAccount;
    private String username; // 用户姓名
    private String password;
    private Integer gender; // 性别（1-男，2-女，0-未知）
    private String phone;// 手机号
    private String email;// 邮箱
    private Integer isActive;// 是否激活（0-未激活，1-已激活）
    private LocalDateTime createTime; // 创建时间
    private String createBy; // 创建人（登录账号）
    private String remark; // 备注信息
    private Integer isAdmin;// 是否管理员（0-普通用户，1-管理员）
    //图片
    private String image;
}
