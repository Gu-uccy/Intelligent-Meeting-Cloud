package com.sky.Service;

import com.sky.dto.ReservationDto;
import com.sky.dto.ReservationPageDto;
import com.sky.entity.Reservation;
import com.sky.result.PageResult;
import com.sky.vo.TimeSlotVo;

import java.time.LocalDate;
import java.util.List;

public interface ReservationService {
    /**
     * 添加预约
     *
     * @param reservation
     * @return
     */
    int addReservation(ReservationDto reservation);

    /**
     * 分页查询预约信息
     *
     * @return
     */
    PageResult pageSelect(ReservationPageDto reservationPageDto);

    /**
     * 修改预约信息
     *
     * @param reservation
     * @return
     */
    int update(Reservation reservation);

    /**
     * 根据会议室id查询预约信息
     *
     * @param id
     * @return
     */

    List<Reservation> getByRoomId(Integer id);

    /**
     * 获取当前用户的预约信息
     * @return
     */
    List<Reservation> getMyReservation();
    /**
     * 取消预约
     * @param id
     * @return
     */

    int cancel(Integer id);
    /**
     * 管理员审核预约
     * @param id 预约ID
     * @param status 审核结果（1-确认，3-拒绝）
     * @param adminId 管理员ID
     * @param remark 审核备注（拒绝原因）
     * @return 影响行数
     */
    int audit(Integer id, Integer status, Integer adminId, String remark);

    /**
     * 获取会议室的预约时间段
     * @param roomId 会议室ID
     * @param date 日期
     * @return 预约时间段列表
     */
    List<TimeSlotVo> getRoomTimeSlots(Long roomId, LocalDate date);
}
