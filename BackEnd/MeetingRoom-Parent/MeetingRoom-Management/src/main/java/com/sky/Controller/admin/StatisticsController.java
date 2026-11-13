// MeetingRoom-Management/src/main/java/com/sky/Controller/admin/StatisticsController.java
package com.sky.Controller.admin;

import com.sky.Service.StatisticsService;
import com.sky.result.Result;
import com.sky.vo.StatisticsVo;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.CrossOrigin;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@Slf4j
@RestController("adminStatisticsController")
@RequestMapping("/admin/statistics")
@CrossOrigin(origins = "*")
public class StatisticsController {

    @Autowired
    private StatisticsService statisticsService;

    /**
     * 获取近7天统计数据
     */
    @GetMapping("/近7天")
    public Result<StatisticsVo> getData() {
        log.info("查询近7天统计数据");
        return Result.success(statisticsService.getStatistics());
    }
}