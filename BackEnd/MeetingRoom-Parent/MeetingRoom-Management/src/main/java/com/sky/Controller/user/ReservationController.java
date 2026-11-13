package com.sky.Controller.user;

import com.sky.Service.ReservationService;
import com.sky.dto.ReservationDto;
import com.sky.entity.Reservation;
import com.sky.result.Result;
import com.sky.vo.TimeSlotVo;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDate;
import java.util.List;

@Slf4j
@RestController("userReservationController")
@RequestMapping("/user/reservation")
@CrossOrigin(origins = "*")
public class ReservationController {
    @Autowired
    private ReservationService reservationService;
    /**
     * 添加预约信息
     * @param reservationDto
     * @return
     */

    @PostMapping
    public Result addReservation(@RequestBody ReservationDto reservationDto){
        log.info("添加预约：{}",reservationDto);
        Result<Object> result = reservationService.addReservation(reservationDto) > 0 ?
                Result.success() : Result.error("添加预约失败");
        log.info("添加预约结果：{}",result);
        return result ;
    }
    /**
     * 1. 查询会议室某天的可用时段
     * GET /user/reservation/slots?roomId=1&date=2025-12-05
     */
    @GetMapping("/slots")
    public Result<List<TimeSlotVo> >getSlots(
            @RequestParam Long roomId,
            @RequestParam @DateTimeFormat(pattern = "yyyy-MM-dd") LocalDate date) {
        return Result.success(reservationService.getRoomTimeSlots(roomId, date));
    }
    /**
     * 查询当前用户预约信息
     * @return
     */

    @GetMapping("/my")
    public Result<List<Reservation>> getMyReservation(){
        log.info("查询当前用户预约信息");
        return Result.success(reservationService.getMyReservation());
    }
    /**
     * 取消预约
     * @param id
     * @return
     */
    @PutMapping("/cancel/{id}")
    public Result cancel(@PathVariable Integer id){
        log.info("取消预约:{}",id);
        return reservationService.cancel(id)>0?
                Result.success():Result.error("取消预约失败");
    }
}
