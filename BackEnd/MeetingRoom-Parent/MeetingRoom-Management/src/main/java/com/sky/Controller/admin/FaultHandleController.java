package com.sky.Controller.admin;
import com.sky.Service.EquipmentFaultService;
import com.sky.dto.DeviceFaultPageDto;


import com.sky.result.PageResult;
import com.sky.result.Result;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

@Slf4j
@RestController("adminEquipmentController")
@RequestMapping("/admin/equipment")
@CrossOrigin(origins = "*")
public class FaultHandleController {
    @Autowired
    private EquipmentFaultService equipmentFaultService;
    /**
     * 处理设备故障
     * @param faultNo
     * @return
     */
    @PutMapping("/handle")
    public Result handleFault(String faultNo, Integer status){
        log.info("处理设备故障:{},{}",faultNo,status);
        return equipmentFaultService.handleFault(faultNo,status)>0?
                Result.success():Result.error("处理设备故障失败");
    }

    /**
     * 查询设备故障
     * @param deviceFaultPageDto
     * @return
     */
    @GetMapping("/page")
    public Result<PageResult> pageSelect(DeviceFaultPageDto deviceFaultPageDto){
        log.info("分页查询设备故障:{}",deviceFaultPageDto);
        return Result.success(equipmentFaultService.pageSelect(deviceFaultPageDto));
    }


}
