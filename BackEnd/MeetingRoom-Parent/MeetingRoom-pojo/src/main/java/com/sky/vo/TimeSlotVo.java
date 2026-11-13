package com.sky.vo;

import lombok.Data;

import java.io.Serializable;

// 返回给前端的时间切片对象
@Data
public class TimeSlotVo implements Serializable {
    private String displayTime; // 显示文本 "09:00-09:30"
    private String startTime;   // 值 "09:00:00"
    private String endTime;     // 值 "09:30:00"
    /**
     * 状态:
     * 0 - 可预约 (绿色)
     * 1 - 已占用 (红色/灰色)
     * 2 - 已过期 (灰色/不可点)
     */
    private Integer status;
}
