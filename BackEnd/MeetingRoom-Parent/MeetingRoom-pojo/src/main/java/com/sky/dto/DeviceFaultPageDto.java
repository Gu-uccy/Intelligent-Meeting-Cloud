package com.sky.dto;

import lombok.Data;

import java.io.Serializable;
@Data
public class DeviceFaultPageDto implements Serializable {
    private int page;
    private int pageSize;
    private Integer id; // 故障ID（主键）
    private String faultNo;// 故障编号
    private Integer status; // 状态（0-待处理，1-处理中，2-已修复，3-无法修复）

}
