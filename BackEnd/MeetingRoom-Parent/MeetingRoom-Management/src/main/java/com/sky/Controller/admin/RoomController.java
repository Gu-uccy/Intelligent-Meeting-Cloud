package com.sky.Controller.admin;

import com.sky.Service.RoomService;
import com.sky.dto.RoomPageDto;
import com.sky.entity.MeetingRoom;
import com.sky.result.PageResult;
import com.sky.result.Result;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@Slf4j
@RestController("adminRoomController")
@RequestMapping("/admin/room")
@CrossOrigin(origins = "*")
public class RoomController {
    @Autowired
    private RoomService roomService;
    /**
     * 添加会议室
     * @param meetingRoom
     * @return
     */

    @PostMapping
    public Result addRoom(@RequestBody MeetingRoom meetingRoom){
        log.info("增加会议室:{}",meetingRoom);
        return roomService.addRoom(meetingRoom)>0?Result.success():Result.error("添加失败");
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
    /**
     * 删除会议室
     * @return
     */

    @DeleteMapping
    public Result deleteByIds(@RequestParam(value = "ids") List<Integer> ids){
        log.info("批量删除,ids:{}",ids);
        return roomService.deleteByIds(ids)>0?Result.success():Result.error("删除失败");
    }
    /**
     * 修改会议室
     * @return
     */

    @PutMapping
    public Result update(@RequestBody MeetingRoom meetingRoom){
        log.info("修改会议室:{}",meetingRoom);
        return roomService.update(meetingRoom)>0?Result.success():Result.error("修改失败");
    }

    /**
     * 启用禁用会议室
     * @return
     */
    @PutMapping("/active")
    public Result setActive(Integer active,Integer id){
        log.info("设置会议室状态:{}", active);
        return roomService.setActive(active, id)>0?Result.success():Result.error("设置失败");
    }
    /**
     * 根据id查询会议室信息
     * @return
     */
    @GetMapping("/{id}")
    public Result<MeetingRoom> getById(@PathVariable Integer id){
        log.info("查询会议室信息:{}",id);
        return Result.success(roomService.getById(id));
    }
}
