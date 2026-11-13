package com.sky.Controller.admin;

import com.sky.Service.ReservationService;
import com.sky.context.BaseContext;
import com.sky.dto.ReservationPageDto;
import com.sky.entity.Reservation;
import com.sky.result.PageResult;
import com.sky.result.Result;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@Slf4j
@RestController("adminReservationController")
@RequestMapping("/admin/reservation")
@CrossOrigin(origins = "*")
public class ReservationController {
    @Autowired
    private ReservationService reservationService;
    /**
     * 分页查询预约信息
     * @param reservationPageDto
     * @return
     */

    @GetMapping("/page")
    public Result<PageResult> pageSelect( ReservationPageDto reservationPageDto){
        log.info("分页查询预约");
        return Result.success(reservationService.pageSelect(reservationPageDto));
    }
    /**
     * 根据会议室id查询预约信息
     * @param id
     * @return
     */
    @GetMapping("/{id}")
    public Result<List<Reservation>> getByRoomId(@PathVariable Integer id){
        log.info("根据会议室id查询预约信息:{}",id);
        return Result.success(reservationService.getByRoomId(id));
    }
    /**
     * 修改预约信息
     * @param reservation
     * @return
     */

    @PutMapping
    public Result update(@RequestBody Reservation reservation){
        log.info("修改预约信息:{}",reservation);
        return reservationService.update(reservation)>0?
                Result.success():Result.error("修改预约信息失败");
    }


    @PostMapping("/audit")
    public Result audit(@RequestBody Map<String, Object> params) {
        Integer id = (Integer) params.get("id");
        Integer status = (Integer) params.get("status");
        String remark = (String) params.get("remark");
        Integer adminId = BaseContext.getCurrentId();  // 管理员ID
        log.info("预约审核:{},{},{},{}", id, status, adminId, remark);
        return reservationService.audit(id, status, adminId, remark) > 0 ?
                Result.success() : Result.error("预约审核失败");
    }
}
