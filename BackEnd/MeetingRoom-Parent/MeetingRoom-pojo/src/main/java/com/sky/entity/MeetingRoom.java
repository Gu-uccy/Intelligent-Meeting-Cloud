package com.sky.entity;

import lombok.Data;

import java.io.Serializable;
import java.time.LocalDateTime;

/**
 * 会议室表实体类
 */
@Data
public class MeetingRoom implements Serializable {
    private Integer id; // 会议室ID（主键）
    private String roomCode;// 会议室编号
    private Integer capacity; // 容纳人数
    private Integer isActive; // 启用状态（1-启用，0-禁用）
    private String location; // 会议室位置（如"3楼东区301室"）
    private String equipment;// 会议室设备
    private LocalDateTime createTime; // 创建时间
    private LocalDateTime updateTime; // 修改时间
    private String createBy; // 创建人（登录账号）
    private String updateBy; // 修改人（登录账号）
    private String remark; // 备注信息
    private Integer version=0;
    //图片
    private String image;
}
