package com.sky.Service.Impl;

import com.sky.Mapper.StatisticsMapper;
import com.sky.Service.StatisticsService;
import com.sky.entity.Statistics;
import com.sky.vo.StatisticsVo;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@Service
public class StatisticsServiceImpl implements StatisticsService {
    @Autowired
    private StatisticsMapper statisticsMapper;
    @Override
    public StatisticsVo getStatistics() {
        // 计算近7天日期范围
        LocalDate endDate = LocalDate.now();
        LocalDateTime endTime=endDate.atStartOfDay() ;
        LocalDate startDate = endDate.minusDays(6);
        LocalDateTime startTime=startDate.atStartOfDay() ;
        // 查询会议室使用统计
        List<Statistics> roomUsageList = statisticsMapper.queryRoomUsage(startTime, endTime);
        // 查询故障统计
        List<Statistics> faultList = statisticsMapper.queryFaultStatistics(startTime,endTime);

        // 按日期分组
        Map<LocalDate, Statistics> roomUsageMap = roomUsageList.stream()
                .collect(Collectors.toMap(Statistics::getDate, s -> s));

        Map<LocalDate, Statistics> faultMap = faultList.stream()
                .collect(Collectors.toMap(Statistics::getDate, s -> s));

        // 构建完整的7天数据
        List<Statistics> dailyData = new ArrayList<>();
        for (int i = 0; i < 7; i++) {
            LocalDate date = startDate.plusDays(i);
            Statistics stat = new Statistics();
            stat.setDate(date);

            // 填充会议室使用数据
            Statistics roomStat = roomUsageMap.get(date);
            if (roomStat != null) {
                stat.setRoomUsageCount(roomStat.getRoomUsageCount());
                stat.setTotalUsageMinutes(roomStat.getTotalUsageMinutes());
            } else {
                stat.setRoomUsageCount(0);
                stat.setTotalUsageMinutes(0);
            }

            // 填充故障数据
            Statistics faultStat = faultMap.get(date);
            if (faultStat != null) {
                stat.setFaultCount(faultStat.getFaultCount());
                stat.setHandledFaultCount(faultStat.getHandledFaultCount());
            } else {
                stat.setFaultCount(0);
                stat.setHandledFaultCount(0);
            }

            dailyData.add(stat);
        }

        // 计算汇总数据
        StatisticsVo result = new StatisticsVo();
        result.setDailyData(dailyData);

        // 总使用次数
        int totalUsage = dailyData.stream()
                .mapToInt(Statistics::getRoomUsageCount)
                .sum();
        result.setTotalUsageCount(totalUsage);

        // 总故障数
        int totalFault = dailyData.stream()
                .mapToInt(Statistics::getFaultCount)
                .sum();
        result.setTotalFaultCount(totalFault);

        // 故障处理率
        int totalHandled = dailyData.stream()
                .mapToInt(Statistics::getHandledFaultCount)
                .sum();
        double handleRate = totalFault > 0 ? (double) totalHandled / totalFault : 0;
        result.setFaultHandleRate(handleRate);

        return result;
    }
}
