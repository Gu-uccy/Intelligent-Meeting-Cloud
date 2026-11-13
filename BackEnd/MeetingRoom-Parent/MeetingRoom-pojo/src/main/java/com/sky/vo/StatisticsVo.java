package com.sky.vo;

import com.sky.entity.Statistics;
import lombok.Data;
import java.io.Serializable;
import java.util.List;

@Data
public class StatisticsVo implements Serializable {
    // 近7天统计数据列表
    private List<Statistics> dailyData;
    // 总使用次数
    private Integer totalUsageCount;
    // 总故障数
    private Integer totalFaultCount;
    // 故障处理率
    private Double faultHandleRate;
}
