package com.sky.vo;

import lombok.Data;

import java.io.Serializable;
import java.time.LocalDateTime;

@Data
public class DeviceFaultVo implements Serializable {
    private Integer id; // 故障ID（主键）
    private String faultNo;// 故障编号
    private String deviceName; // 设备名称
    private Integer roomId; // 关联会议室ID（外键）
    private Integer reportUserId; // 上报人ID（外键）
    private Integer handleUserId; // 处理人ID（外键，管理员）
    private Integer status; // 状态（0-待处理，1-处理中，2-已修复，3-无法修复）
    private String faultDesc;// 故障描述
    private String handleDesc;// 处理描述
    private LocalDateTime createTime; // 创建时间
    private LocalDateTime updateTime; // 修改时间
    private LocalDateTime handleTime;// 处理时间
}
