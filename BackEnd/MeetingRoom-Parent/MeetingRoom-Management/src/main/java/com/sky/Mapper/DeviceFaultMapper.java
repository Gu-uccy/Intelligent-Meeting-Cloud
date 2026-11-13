package com.sky.Mapper;

import com.github.pagehelper.Page;
import com.sky.annotation.AutoFill;
import com.sky.dto.DeviceFaultPageDto;
import com.sky.entity.DeviceFault;
import com.sky.enumeration.OperationType;
import com.sky.vo.DeviceFaultVo;
import org.apache.ibatis.annotations.Insert;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Select;

@Mapper
public interface DeviceFaultMapper {
    /**
     * 添加设备故障信息
     * @param deviceFault
     * @return
     */
    @AutoFill(value = OperationType.INSERT)
    int insert(DeviceFault deviceFault);

    /**
     * 根据故障编号查询设备故障信息
     * @param faultNo
     * @return
     */
    @Select("select * from device_fault where fault_no = #{faultNo}")
    DeviceFault selectByFaultNo(String faultNo);

    /**
     * 修改设备故障信息
     * @param deviceFault
     * @return
     */
    int update(DeviceFault deviceFault);

    /**
     * 分页查询设备故障信息
     * @param deviceFaultPageDto
     * @return
     */
    Page<DeviceFaultVo> pageSelect(DeviceFaultPageDto deviceFaultPageDto);
}
