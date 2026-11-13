package com.sky.Service;

import com.sky.dto.DeviceFaultPageDto;
import com.sky.entity.DeviceFault;
import com.sky.result.PageResult;

public interface EquipmentFaultService {
    /**
     * 提交故障报告
     * @return
     */
    boolean submitFaultReport(DeviceFault deviceFault);

    /**
     * 处理故障
     * @return
     */
    int handleFault(String faultNo ,Integer status);

    /**
     * 分页查询故障信息
     * @return
     */
    PageResult pageSelect(DeviceFaultPageDto deviceFaultPageDto);
}
