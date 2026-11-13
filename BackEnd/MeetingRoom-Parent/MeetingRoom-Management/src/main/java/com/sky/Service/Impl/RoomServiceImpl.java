package com.sky.Service.Impl;

import com.github.pagehelper.Page;
import com.github.pagehelper.PageHelper;
import com.sky.Mapper.RoomMapper;
import com.sky.Service.RoomService;
import com.sky.dto.RoomPageDto;
import com.sky.entity.MeetingRoom;
import com.sky.result.PageResult;
import com.sky.vo.RoomVo;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.cache.annotation.CacheEvict;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;


import java.util.List;

@Slf4j
@Service
public class RoomServiceImpl implements RoomService {
    @Autowired
    private RoomMapper roomMapper;
    /**
     * 添加会议室
     * @param meetingRoom
     */
/*    @CacheEvict(value = "rooms", allEntries = true)*/
    @Override
    public int addRoom( MeetingRoom meetingRoom) {
        log.info("添加会议室:{}",meetingRoom);
      return  roomMapper.insertRoom(meetingRoom);
    }

    /**
     * 分页查询所有会议室
     * @return
     */
    @Override
    public PageResult pageSelect( RoomPageDto roomPageDto) {
        log.info("分页查询所有会议室");
        //开启分页
        PageHelper.startPage(roomPageDto.getPage(),roomPageDto.getPageSize());
        //查询
        Page<RoomVo > page = roomMapper.limitSelect(roomPageDto);
        log.info("查询结果：{}",page);
        return new PageResult(page.getTotal(),page.getResult());
    }

    /**
     * 批量删除会议室
     * @param ids
     * @return
     */
    /*@CacheEvict(value = "rooms", allEntries = true)*/
    @Transactional
    @Override
    public int deleteByIds(List<Integer> ids) {
        log.info("批量删除会议室");
        return roomMapper.batchDelete(ids);
    }

    /**
     * 修改会议室信息
     * @param meetingRoom
     * @return
     */
   /* @CacheEvict(value = "rooms", allEntries = true)*/
    @Override
    public int update( MeetingRoom meetingRoom) {
        log.info("修改会议室信息");
        return roomMapper.update(meetingRoom);
    }
    @Override
    public int updateStatusWithVersion(Integer roomId,  Integer version) {
        return roomMapper.updateStatusWithVersion(roomId, version);
    }
    /**
     * 根据id查询会议室信息
     * @param roomId
     * @return
     */
   /* @Cacheable(value = "rooms", key = "#roomId")*/
    @Override
    public MeetingRoom getById(Integer roomId) {
        log.info("查询会议室信息：{}",roomId);
        return roomMapper.selectById(roomId);
    }



    /**
     * 启用禁用会议室
     * @param active
     * @param id
     * @return
     */
   /* @CacheEvict(value = "rooms", allEntries = true)*/
    @Override
    public int setActive(Integer active, Integer id) {
        log.info("设置会议室状态");
        MeetingRoom meetingRoom = new MeetingRoom();
        meetingRoom.setId(id);
        meetingRoom.setIsActive(active);
        return roomMapper.update(meetingRoom);
    }

}
