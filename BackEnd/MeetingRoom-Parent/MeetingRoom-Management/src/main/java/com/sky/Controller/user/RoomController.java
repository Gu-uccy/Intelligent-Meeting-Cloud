package com.sky.Controller.user;

import com.sky.Service.RoomService;
import com.sky.dto.RoomPageDto;
import com.sky.entity.MeetingRoom;
import com.sky.result.PageResult;
import com.sky.result.Result;
import com.sky.vo.TimeSlotVo;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDate;
import java.util.List;

@Slf4j
@RestController("userRoomController")
@RequestMapping("/user/room")
@CrossOrigin(origins = "*")
public class RoomController {
    @Autowired
    private RoomService roomService;
    /**
     * 根据id查询会议室信息
     * @return
     */
    @GetMapping("/{id}")
    public Result<MeetingRoom> getById(@PathVariable Integer id){
        log.info("查询会议室信息:{}",id);
        return Result.success(roomService.getById(id));
    }

    /**
     * 查询所有会议室
     * @return
     */

    @GetMapping("/page")
    public Result<PageResult> pageSelect(RoomPageDto roomPageDto){
        log.info("分页查询所有会议室");
        PageResult pageResult = roomService.pageSelect(roomPageDto);
        return Result.success(pageResult);
    }

}
