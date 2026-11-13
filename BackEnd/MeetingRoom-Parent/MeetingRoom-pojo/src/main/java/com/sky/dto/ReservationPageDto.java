package com.sky.dto;

import lombok.Data;

import java.io.Serializable;
import java.time.LocalDateTime;
@Data
public class ReservationPageDto implements Serializable {
    private int page;
    private int pageSize;
    private Integer id; // 预约ID（主键）
    private String reservationNo;// 预约编号
    private Integer userId; // 预约用户ID（外键）
    private Integer roomId; // 预约会议室ID（外键）
    private Integer status; // 预约状态（0-待审核，1-已确认，2-已取消）
}
