package com.sky.Service.Impl;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.github.pagehelper.Page;
import com.github.pagehelper.PageHelper;
import com.sky.Mapper.ReservationMapper;
import com.sky.Service.ReservationService;
import com.sky.Service.RoomService;
import com.sky.Service.UserService;
import com.sky.constant.MessageConstant;
import com.sky.constant.StatusConstant;
import com.sky.context.BaseContext;
import com.sky.dto.ReservationDto;
import com.sky.dto.ReservationPageDto;
import com.sky.entity.MeetingRoom;
import com.sky.entity.Reservation;
import com.sky.entity.User;
import com.sky.exception.EndTimeBeforeStartTime;
import com.sky.exception.ReservationIsConfirmed;
import com.sky.exception.RoomIsAccupied;
import com.sky.result.PageResult;
import com.sky.vo.ReservationVo;

import com.sky.vo.TimeSlotVo;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.BeanUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.mail.SimpleMailMessage;
import org.springframework.mail.javamail.JavaMailSender;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.LocalTime;
import java.time.format.DateTimeFormatter;
import java.time.temporal.ChronoUnit;
import java.util.ArrayList;
import java.util.List;
import java.util.Random;

@Service
@Slf4j
public class ReservationServiceImpl implements ReservationService{
    @Autowired
    private ReservationMapper reservationMapper;
    @Autowired
    private RoomService roomService;
    @Autowired
    private JavaMailSender mailSender;
    @Autowired
    private UserService userService;
    @Value("${spring.mail.username}")
    private String fromEmail;


    /**
     * 添加预约
     * @param reservationDto
     * @return
     */
    @Transactional
    @Override
    public int addReservation(ReservationDto reservationDto) {

        log.info("添加预约：{}",reservationDto);
        List<Reservation> reservations = reservationMapper.selectByRoomId(reservationDto.getRoomId());
        MeetingRoom room = roomService.getById(reservationDto.getRoomId());
        Integer status = room.getIsActive();
        log.info("查询到会议室：id={}, version={}, status={}",
                room.getId(), room.getVersion(), status); // 关键日志

        log.info("预约信息：{}",reservations);
        for (Reservation res : reservations) {
            // 判断时间段是否冲突，并预留10分钟间隙
            if(res.getStartTime().isBefore(reservationDto.getEndTime().plusMinutes(10))
                    && res.getEndTime().isAfter(reservationDto.getStartTime().minusMinutes(10))){
                log.info("时间段冲突或间隔不足10分钟");
                throw new RoomIsAccupied(MessageConstant.ROOM_IS_ACCUPIED);
            }
        }
        //  检查预约时长（最长8小时）
        long hours = ChronoUnit.HOURS.between(
                reservationDto.getStartTime(),
                reservationDto.getEndTime()
        );
        //  检查时间冲突
        List<Reservation> conflicts = reservationMapper.selectConflictReservations(
                reservationDto.getRoomId(),
                reservationDto.getStartTime(),
                reservationDto.getEndTime()
        );
        log.info("时间冲突：{}",conflicts);
        if (!conflicts.isEmpty()) {
            throw new RoomIsAccupied(MessageConstant.ROOM_IS_ACCUPIED);
        }
        if (hours > 8) {
            throw new RuntimeException("单次预约最长不超过8小时");
        }
        if (reservationDto.getStartTime().getMinute() % 30 != 0 || reservationDto.getStartTime().getSecond() != 0) {
            throw new IllegalArgumentException("开始时间必须是整点或30分");
        }
        if (reservationDto.getEndTime().getMinute() % 30 != 0 || reservationDto.getEndTime().getSecond() != 0) {
            throw new IllegalArgumentException("结束时间必须是整点或30分");
        }

        if(reservationDto.getEndTime().isBefore(reservationDto.getStartTime())){
            log.info("结束时间小于开始时间");
            throw new EndTimeBeforeStartTime(MessageConstant.END_TIME_IS_BEFORE_START_TIME);
        }
        Reservation reservation=new Reservation();
        BeanUtils.copyProperties(reservationDto,reservation);

        //默认待审核
        reservation.setStatus(StatusConstant.PENDING);

        reservation.setUserId(BaseContext.getCurrentId());
        log.info("准备更新会议室状态，传递的version：{}", room.getVersion()); // 关键日志
        // 使用乐观锁更新会议室状态
        int updateResult = roomService.updateStatusWithVersion(
                room.getId(),
                room.getVersion()
        );
        log.info("更新会议室状态结果：{}",updateResult);
        if(updateResult == 0) {
            // 版本号不匹配，说明已被其他用户修改
            throw new RuntimeException("会议室状态已被其他用户修改，请重新预约");
        }

        reservation.setReservationNo(generateReservationNo());
        int result = reservationMapper.insertReservation(reservation);

        log.info("添加预约结果：{}",result);
        // 如果预约添加成功，则发送邮件提醒
        if (result > 0) {
            sendReservationSuccessEmail(reservation);
        }

        return result;
    }

    private String generateReservationNo() {
        // Generate a random reservation number with timestamp and random digits
        StringBuilder sb = new StringBuilder();
        // Add prefix
        sb.append("RES");
        // Add timestamp
        sb.append(System.currentTimeMillis());
        // Add random 4-digit number
        Random random = new Random();
        sb.append(String.format("%04d", random.nextInt(10000)));
        return sb.toString();
    }


    /**
     * 发送预约成功邮件
     * @param reservation
     */
    private void sendReservationSuccessEmail(Reservation reservation) {
        try {

        User user = userService.getById(reservation.getUserId()); // 需要注入UserService或UserMapper

        if (user != null && user.getEmail() != null && !user.getEmail().isEmpty()) {
            SimpleMailMessage message = new SimpleMailMessage();
            message.setFrom(fromEmail);
            message.setTo(user.getEmail());
            message.setSubject("会议室预约成功通知");
            message.setText(
                "您好，\n\n" +
                "您的会议室预约已成功提交：\n" +
                "会议主题: " + reservation.getMeetingTopic() + "\n" +
                "会议室ID: " + reservation.getRoomId() + "\n" +
                "开始时间: " + reservation.getStartTime() + "\n" +
                "结束时间: " + reservation.getEndTime() + "\n" +
                "当前状态: 待审核\n\n" +
                "请耐心等待管理员审核。\n\n" +
                "智能会议室系统"
            );

            mailSender.send(message);
            log.info("预约成功邮件已发送至: {}", user.getEmail());
        }
        } catch (Exception e) {
            log.error("发送预约成功邮件失败，预约ID: {}", reservation.getId(), e);
        }
    }

    /**
     * 分页查询预约信息
     * @param reservationPageDto
     * @return
     */
    @Override
    public PageResult pageSelect(ReservationPageDto reservationPageDto) {
        log.info("分页查询预约信息");
        PageHelper.startPage(reservationPageDto.getPage(),reservationPageDto.getPageSize());
        Page<ReservationVo> page = reservationMapper.pageSelect(reservationPageDto);
        return new PageResult(page.getTotal(),page.getResult());
    }

    /**
     * 修改预约信息
     * @param reservation
     * @return
     */
    @Override
    public int update(Reservation reservation) {
        log.info("修改预约信息");
        return reservationMapper.update(reservation);
    }

    /**
     * 根据会议室id查询预约信息
     * @param id
     * @return
     */
    @Override
    public List<Reservation> getByRoomId(Integer id) {
        log.info("根据会议室id查询预约信息");
        return reservationMapper.selectByRoomId(id);
    }

    /**
     * 获取当前用户预约信息
     * @return
     */
    @Override
    public List<Reservation> getMyReservation() {
        log.info("获取当前用户预约信息");
        Integer userId = BaseContext.getCurrentId();
        return  reservationMapper.getByUserId(userId);
    }

    /**
     * 取消预约
     * @param id
     * @return
     */
    @Override
    public int cancel(Integer id) {
        log.info("取消预约");
        Reservation reservation = reservationMapper.selectById(id);
        if(reservation==null){
            log.info("预约不存在");
            throw new RuntimeException("预约不存在");
        }
        if(reservation.getStatus() == StatusConstant.CONFIRMED){
            log.info("预约已确认，不能取消");
            throw new ReservationIsConfirmed("预约已确认，不能取消");
        }
        reservation.setStatus(StatusConstant.CANCELED);
        return reservationMapper.update(reservation);

    }


    @Override
    @Transactional  // 事务保证
    public int audit(Integer id, Integer status, Integer adminId, String remark) {
        // 1. 查询预约信息
        Reservation reservation = reservationMapper.selectById(id);
        if (reservation == null) {
            throw new RuntimeException("预约不存在");
        }
        if (reservation.getStatus() != StatusConstant.PENDING) {
            throw new RuntimeException("只能审核待审核状态的预约");
        }

        // 2. 更新预约状态
        reservation.setStatus(status);
        reservation.setAdminId(adminId);
        reservation.setRemark(remark);  // 存储拒绝原因
        int rows = reservationMapper.update(reservation);

        // 3. 审核通过：更新会议室状态为占用
        if (status == StatusConstant.CONFIRMED) {
            MeetingRoom room = roomService.getById(reservation.getRoomId());
            int updateResult = roomService.updateStatusWithVersion(
                    room.getId(),
                    room.getVersion()
            );
            if (updateResult == 0) {
                throw new RuntimeException("会议室状态已被修改，请重新审核");
            }
            // 发送审核通过通知
            sendAuditSuccessEmail(reservation);
        } else if (status == StatusConstant.REJECTED) {
            // 审核拒绝：发送拒绝通知
            sendAuditRejectEmail(reservation);
        }

        return rows;
    }
    // 定义运营时间：早上9点到晚上6点
    private static final LocalTime OPEN_TIME = LocalTime.of(0, 0);
    private static final LocalTime CLOSE_TIME = LocalTime.of(23, 59);

    /**
     * 功能：获取某天的时间切片视图
     */
    public List<TimeSlotVo> getRoomTimeSlots(Long roomId, LocalDate date) {
        // 1. 查询该会议室当天的所有有效预约
        LocalDateTime dayStart = date.atTime(0, 0, 0);
        LocalDateTime dayEnd = date.atTime(23, 59, 59);

        List<Reservation> existList = reservationMapper.selectList(new QueryWrapper<Reservation>()
                .eq("room_id", roomId)
                .eq("status", 1) // 有效
                .gt("end_time", dayStart) // 简单的范围筛选，具体交集在内存判断
                .lt("start_time", dayEnd)
                .orderByAsc("start_time"));

        List<TimeSlotVo> result = new ArrayList<>();
        LocalDateTime cursor = date.atTime(OPEN_TIME);
        LocalDateTime closeDateTime = date.atTime(CLOSE_TIME);
        LocalDateTime now = LocalDateTime.now();

        // 2. 循环生成 30 分钟的时间切片
        while (cursor.isBefore(closeDateTime)) {
            LocalDateTime nextCursor = cursor.plusMinutes(30);

            TimeSlotVo slot = new TimeSlotVo();
            slot.setDisplayTime(cursor.format(DateTimeFormatter.ofPattern("HH:mm")) + " - " + nextCursor.format(DateTimeFormatter.ofPattern("HH:mm")));
            slot.setStartTime(cursor.format(DateTimeFormatter.ofPattern("HH:mm:ss")));
            slot.setEndTime(nextCursor.format(DateTimeFormatter.ofPattern("HH:mm:ss")));

            // 3. 判定状态
            if (cursor.isBefore(now)) {
                slot.setStatus(2); // 过期
            } else if (isOccupied(cursor, nextCursor, existList)) {
                slot.setStatus(1); // 已占用
            } else {
                slot.setStatus(0); // 可用
            }

            result.add(slot);
            cursor = nextCursor;
        }
        return result;
    }

    /**
     * 内存辅助方法：判断单个切片是否与预约列表冲突
     */
    private boolean isOccupied(LocalDateTime slotStart, LocalDateTime slotEnd, List<Reservation> list) {
        for (Reservation r : list) {
            // 核心重叠公式：!(EndA <= StartB || StartA >= EndB)
            if (r.getStartTime().isBefore(slotEnd) && r.getEndTime().isAfter(slotStart)) {
                return true;
            }
        }
        return false;
    }

    /**
     * 发送审核通过邮件
     * @param reservation
     */
    private void sendAuditSuccessEmail(Reservation reservation) {
        try {
            User user = userService.getById(reservation.getUserId());

            if (user != null && user.getEmail() != null && !user.getEmail().isEmpty()) {
                SimpleMailMessage message = new SimpleMailMessage();
                message.setFrom(fromEmail);
                message.setTo(user.getEmail());
                message.setSubject("会议室预约审核通过通知");
                message.setText(
                        "您好，\n\n" +
                                "您的会议室预约已审核通过：\n" +
                                "预约编号: " + reservation.getReservationNo() + "\n" +
                                "会议主题: " + reservation.getMeetingTopic() + "\n" +
                                "会议室ID: " + reservation.getRoomId() + "\n" +
                                "开始时间: " + reservation.getStartTime() + "\n" +
                                "结束时间: " + reservation.getEndTime() + "\n" +
                                "当前状态: 审核通过\n\n" +
                                "您可以正常使用会议室。\n\n" +
                                "智能会议室系统"
                );

                mailSender.send(message);
                log.info("审核通过邮件已发送至: {}", user.getEmail());
            }
        } catch (Exception e) {
            log.error("发送审核通过邮件失败，预约ID: {}", reservation.getId(), e);
        }
    }

    /**
     * 发送审核拒绝邮件
     * @param reservation
     */
    private void sendAuditRejectEmail(Reservation reservation) {
        try {
            User user = userService.getById(reservation.getUserId());

            if (user != null && user.getEmail() != null && !user.getEmail().isEmpty()) {
                SimpleMailMessage message = new SimpleMailMessage();
                message.setFrom(fromEmail);
                message.setTo(user.getEmail());
                message.setSubject("会议室预约审核拒绝通知");
                message.setText(
                        "您好，\n\n" +
                                "您的会议室预约被拒绝：\n" +
                                "预约编号: " + reservation.getReservationNo() + "\n" +
                                "会议主题: " + reservation.getMeetingTopic() + "\n" +
                                "会议室ID: " + reservation.getRoomId() + "\n" +
                                "开始时间: " + reservation.getStartTime() + "\n" +
                                "结束时间: " + reservation.getEndTime() + "\n" +
                                "当前状态: 审核拒绝\n\n" +
                                "如有疑问请联系管理员。\n\n" +
                                "智能会议室系统"
                );

                mailSender.send(message);
                log.info("审核拒绝邮件已发送至: {}", user.getEmail());
            }
        } catch (Exception e) {
            log.error("发送审核拒绝邮件失败，预约ID: {}", reservation.getId(), e);
        }
    }


}
