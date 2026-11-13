package com.sky.Mapper;

import com.sky.entity.Statistics;
import org.apache.ibatis.annotations.Mapper;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.List;

@Mapper
public interface StatisticsMapper {

    List<Statistics> queryRoomUsage(LocalDateTime startTime, LocalDateTime endTime);

    List<Statistics> queryFaultStatistics(LocalDateTime startTime, LocalDateTime endTime);
}
