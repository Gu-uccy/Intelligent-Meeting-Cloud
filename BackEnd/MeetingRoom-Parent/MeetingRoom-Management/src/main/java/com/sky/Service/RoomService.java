package com.sky.Service;

import com.sky.dto.RoomPageDto;
import com.sky.entity.MeetingRoom;
import com.sky.result.PageResult;
import com.sky.vo.TimeSlotVo;

import java.time.LocalDate;
import java.util.List;

public interface RoomService {
    /**
     * 添加会议室
     * @param meetingRoom
     */
    int addRoom(MeetingRoom meetingRoom);

    /**
     * 分页查询所有会议室
     * @return
     */
    PageResult pageSelect(RoomPageDto roomPageDto);

    /**
     * 批量删除会议室
     * @param ids
     */
    int deleteByIds(List<Integer> ids);

    /**
     * 修改会议室信息
     * @param meetingRoom
     */
    int update(MeetingRoom meetingRoom);

    /**
     * 根据id查询会议室信息
     * @param roomId
     * @return
     */
    MeetingRoom getById(Integer roomId);



    /**
     * 设置会议室激活状态
     * @param active
     * @param id
     * @return
     */
    int setActive(Integer active, Integer id);
    // 乐观锁
    int updateStatusWithVersion(Integer roomId, Integer version);


}
