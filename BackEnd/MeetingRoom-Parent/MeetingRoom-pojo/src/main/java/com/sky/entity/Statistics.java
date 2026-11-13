
package com.sky.entity;

import lombok.Data;

import java.io.Serializable;
import java.time.LocalDate;

@Data
public class Statistics implements Serializable {
    // 日期
    private LocalDate date;
    // 会议室使用次数
    private Integer roomUsageCount;
    // 会议室总占用时长(分钟)
    private Integer totalUsageMinutes;
    // 故障反馈数量
    private Integer faultCount;
    // 已处理故障数量
    private Integer handledFaultCount;
}