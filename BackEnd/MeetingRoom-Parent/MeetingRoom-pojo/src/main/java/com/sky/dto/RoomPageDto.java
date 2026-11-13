package com.sky.dto;

import lombok.Data;

import java.io.Serializable;
@Data
public class RoomPageDto implements Serializable {
    private int page;
    private int pageSize;
    private String roomCode;
    private Integer capacity; // 容纳人数
    private Integer isActive; // 启用状态
    private String location;
    private String equipment;
}
