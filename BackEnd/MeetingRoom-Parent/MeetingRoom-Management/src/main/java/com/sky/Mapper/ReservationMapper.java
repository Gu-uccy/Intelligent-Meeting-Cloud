package com.sky.Mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.github.pagehelper.Page;
import com.sky.annotation.AutoFill;
import com.sky.dto.ReservationPageDto;
import com.sky.entity.Reservation;
import com.sky.enumeration.OperationType;
import com.sky.vo.ReservationVo;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

import java.time.LocalDateTime;
import java.util.List;

@Mapper
public interface ReservationMapper extends BaseMapper<Reservation> {
    /**
     * 添加预约信息
     * @param reservation
     * @return
     */
    @AutoFill(value = OperationType.INSERT)
    int insertReservation(Reservation reservation);

    /**
     * 分页查询预约信息
     * @param reservationPageDto
     * @return
     */
    Page<ReservationVo> pageSelect(ReservationPageDto reservationPageDto);

    /**
     * 修改预约信息
     * @param reservation
     * @return
     */
    @AutoFill(value = OperationType.UPDATE)
    int update(Reservation reservation);
    /**
     * 查询指定时间范围内开始的预约
     * @param startTime 起始时间
     * @param endTime 结束时间
     * @return 预约列表
     */
    @Select("SELECT * FROM reservation WHERE start_time > #{startTime} AND start_time <= #{endTime} AND status = 1")
    List<Reservation> getReservationsStartingBetween(LocalDateTime startTime, LocalDateTime endTime);

    /**
     * 根据会议室id查询预约信息
     * @param id
     * @return
     */
    @Select("SELECT * FROM reservation WHERE room_id = #{id}")
    List<Reservation> selectByRoomId(Integer id);

    /**
     * 根据用户id查询预约信息
     * @param userId
     * @return
     */
    @Select("SELECT * FROM reservation WHERE user_id = #{userId}")
    List<Reservation> getByUserId(Integer userId);

    /**
     * 根据id查询预约信息
     * @param id
     * @return
     */
    @Select("SELECT * FROM reservation WHERE id = #{id}")
    Reservation selectById(Integer id);

    /**
     * 查询24小时前的待处理预约
     * @param twentyFourHoursAgo
     * @return
     */
    @Select("SELECT * FROM reservation WHERE status = 0 AND create_time < #{time}")
    List<Reservation> selectPendingByCreateTimeBefore(LocalDateTime twentyFourHoursAgo);

    /**
     * 查询已确认且结束时间 < 当前时间的预约
     * @param now
     * @return
     */
    @Select("SELECT * FROM reservation WHERE status = 1 AND end_time < #{time}")
    List<Reservation> selectConfirmedByEndTimeBefore(LocalDateTime now);

    /**
     * 查询指定会议室在时间范围内的有效预约（排除已取消、已拒绝、已完成）
     * @param roomId 会议室ID
     * @param startTime 预约开始时间
     * @param endTime 预约结束时间
     * @return 冲突预约列表
     */
    @Select("SELECT * FROM reservation WHERE room_id = #{roomId} " +
            "AND status IN (0, 1) " +  // 只校验待审核和已确认的预约
            "AND (start_time < #{endTime} AND end_time > #{startTime})")  // 时间重叠判断
    List<Reservation> selectConflictReservations(
            @Param("roomId") Integer roomId,
            @Param("startTime") LocalDateTime startTime,
            @Param("endTime") LocalDateTime endTime
    );
}
