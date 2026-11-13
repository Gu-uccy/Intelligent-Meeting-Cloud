package com.sky.Service.Impl;

import com.github.pagehelper.Page;
import com.github.pagehelper.PageHelper;
import com.sky.Mapper.DeviceFaultMapper;
import com.sky.Service.EquipmentFaultService;
import com.sky.Service.RoomService;
import com.sky.constant.StatusConstant;
import com.sky.context.BaseContext;
import com.sky.dto.DeviceFaultPageDto;
import com.sky.entity.DeviceFault;
import com.sky.result.PageResult;
import com.sky.vo.DeviceFaultVo;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;

@Service
@Slf4j
public class EquipmentFaultServiceImpl implements EquipmentFaultService {
    @Autowired
    private DeviceFaultMapper deviceFaultMapper;
    @Autowired
    private RoomService roomService;
    /**
     * 提交设备故障报告
     * @return
     */
    @Override
    public boolean submitFaultReport(DeviceFault deviceFault) {
        log.info("提交设备故障报告");
        deviceFault.setReportUserId(BaseContext.getCurrentId());
        deviceFault.setFaultNo("F"+System.currentTimeMillis());
        //待处理
        deviceFault.setStatus(StatusConstant.WAITING);
        deviceFault.setFaultDesc("待处理");
        return deviceFaultMapper.insert(deviceFault)>0;
    }

    /**
     * 处理设备故障
     * @param faultNo
     * @return
     */
    @Override
    public int handleFault( String faultNo ,Integer status) {
        log.info("处理设备故障");
        DeviceFault deviceFault= deviceFaultMapper.selectByFaultNo(faultNo);
        if(deviceFault==null){
            throw new RuntimeException("设备故障不存在");
        }
        deviceFault.setHandleUserId(BaseContext.getCurrentId());
        deviceFault.setStatus(status);
        deviceFault.setHandleTime(LocalDateTime.now());
        deviceFault.setHandleDesc(status==StatusConstant.COMPLETED2?"设备已修复"
                :(status==StatusConstant.UNFIXABLE?"无法修复":"进行中"));
        return deviceFaultMapper.update(deviceFault);
    }

    /**
     * 分页查询设备故障信息
     * @param deviceFaultPageDto
     * @return
     */
    @Override
    public PageResult pageSelect(DeviceFaultPageDto deviceFaultPageDto) {
        log.info("分页查询设备故障信息");
        PageHelper.startPage(deviceFaultPageDto.getPage(),deviceFaultPageDto.getPageSize());
        Page<DeviceFaultVo> page = deviceFaultMapper.pageSelect(deviceFaultPageDto);
        return new PageResult(page.getTotal(),page.getResult());
    }
}
