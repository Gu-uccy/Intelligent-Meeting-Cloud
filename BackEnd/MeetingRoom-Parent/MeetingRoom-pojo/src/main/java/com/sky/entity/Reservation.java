package com.sky.entity;

import lombok.Data;

import java.io.Serializable;
import java.time.LocalDateTime;

/**
 * 预约表实体类
 */
@Data
public class Reservation implements Serializable {
    private Integer id; // 预约ID（主键）
    private String reservationNo;// 预约编号
    private Integer userId; // 预约用户ID（外键）
    private Integer roomId; // 预约会议室ID（外键）
    private Integer adminId; // 审核管理员ID（外键，可为空）
    private LocalDateTime startTime; // 预约开始时间
    private LocalDateTime endTime; // 预约结束时间
    private Integer status; // 预约状态（0-待审核，1-已确认，2-已取消）
    private String meetingTopic;// 会议主题
    private Integer participantNum;// 会议人数
    private LocalDateTime createTime; // 创建时间
    private LocalDateTime updateTime; // 修改时间
    private String createBy; // 创建人（登录账号）
    private String updateBy; // 修改人（登录账号）
    private String remark; // 备注信息

}