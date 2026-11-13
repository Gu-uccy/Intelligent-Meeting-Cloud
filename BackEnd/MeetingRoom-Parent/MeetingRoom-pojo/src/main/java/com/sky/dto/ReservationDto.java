package com.sky.dto;

import com.fasterxml.jackson.annotation.JsonFormat;
import lombok.Data;
import org.springframework.format.annotation.DateTimeFormat;

import java.io.Serializable;
import java.time.LocalDateTime;
@Data
public class ReservationDto implements Serializable {
    private Integer roomId; // 预约会议室ID（外键）
    @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss", timezone = "GMT+8") // 解决JSON解析问题
    @DateTimeFormat(pattern = "yyyy-MM-dd HH:mm:ss") // 解决表单/URL参数绑定问题（可选）
    private LocalDateTime startTime; // 预约开始时间
    @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss", timezone = "GMT+8") // 解决JSON解析问题
    @DateTimeFormat(pattern = "yyyy-MM-dd HH:mm:ss") // 解决表单/URL参数绑定问题（可选）
    private LocalDateTime endTime; // 预约结束时间
    private String meetingTopic;// 会议主题
    private Integer participantNum;// 会议人数
    private String remark; // 备注信息
}
