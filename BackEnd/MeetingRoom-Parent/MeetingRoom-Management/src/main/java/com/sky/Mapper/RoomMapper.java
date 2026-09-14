package com.sky.Mapper;

import com.github.pagehelper.Page;
import com.sky.annotation.AutoFill;
import com.sky.dto.RoomPageDto;
import com.sky.entity.MeetingRoom;
import com.sky.enumeration.OperationType;
import com.sky.vo.RoomVo;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Select;

import java.util.List;

@Mapper
public interface RoomMapper {
    /**
     * 添加会议室
     * @param meetingRoom
     */
    @AutoFill(value = OperationType.INSERT)
    int insertRoom(MeetingRoom meetingRoom);

    /**
     * 分页查询所有会议室
     * @return
     */
    Page<RoomVo> limitSelect(RoomPageDto roomPageDto);


    /**
     * 批量删除会议室
     * @param ids
     * @return
     */
    int batchDelete(List<Integer> ids);

    /**
     * 修改会议室信息
     * @param meetingRoom
     * @return
     */
    @AutoFill(value = OperationType.UPDATE)
    int update(MeetingRoom meetingRoom);

    /**
     * 根据id查询会议室信息
     * @param roomId
     * @return
     */
    @Select("select * from meeting_room where id = #{roomId}")
    MeetingRoom selectById(Integer roomId);

    int updateStatusWithVersion(Integer roomId,  Integer version);
}
