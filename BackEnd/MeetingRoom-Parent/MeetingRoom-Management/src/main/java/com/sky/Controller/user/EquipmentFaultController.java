package com.sky.Controller.user;

import com.sky.Service.EquipmentFaultService;
import com.sky.entity.DeviceFault;
import com.sky.result.Result;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

@Slf4j
@RestController("userEquipmentController")
@RequestMapping("/user/equipment")
@CrossOrigin(origins = "*")
public class EquipmentFaultController {
    @Autowired
    private EquipmentFaultService equipmentFaultService;

    /**
     * 用户反馈设备故障
     * @param deviceFault 故障信息
     * @return 提交结果
     */
    @PostMapping("/fault")
    public Result<DeviceFault> reportFault(@RequestBody DeviceFault deviceFault) {
        log.info("用户反馈设备故障: 会议室ID={}, 故障描述={}",deviceFault.getRoomId(),
                deviceFault.getFaultDesc());
        try {
            boolean success = equipmentFaultService.submitFaultReport(deviceFault);
            if (success) {
                return Result.success(deviceFault);
            } else {
                return Result.error("故障反馈提交失败");
            }
        } catch (Exception e) {
            log.error("提交故障报告时发生错误", e);
            return Result.error("系统异常，请稍后重试");
        }
    }
}
