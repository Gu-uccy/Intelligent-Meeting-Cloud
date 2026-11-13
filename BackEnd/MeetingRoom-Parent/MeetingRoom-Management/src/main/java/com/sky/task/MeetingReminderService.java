package com.sky.task;

import com.sky.Service.ReservationService;
import com.sky.Service.RoomService;
import com.sky.Service.UserService;
import com.sky.constant.MessageConstant;
import com.sky.constant.StatusConstant;
import com.sky.context.BaseContext;
import com.sky.entity.MeetingRoom;
import com.sky.entity.Reservation;
import com.sky.entity.User;
import com.sky.Mapper.ReservationMapper;
import com.sky.Mapper.UserMapper;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.mail.SimpleMailMessage;
import org.springframework.mail.javamail.JavaMailSender;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import java.time.LocalDateTime;
import java.util.List;

@Component
@Slf4j
public class MeetingReminderService {

    @Autowired
    private ReservationMapper reservationMapper;

    @Autowired
    private UserMapper userMapper;

    @Autowired
    private JavaMailSender mailSender;

    @Autowired
    private RoomService roomService;
    /**
     * 定时任务：每5分钟检查一次即将开始的会议
     * cron表达式含义：秒 分 时 日 月 周
     * "0 0/5 * * * ?" 表示从0秒开始，每5分钟执行一次
     */
    @Scheduled(cron = "0 0/5 * * * ?")
    public void sendMeetingReminders() {
        log.info("开始检查即将开始的会议...");

        // 计算30分钟后的时间范围
        LocalDateTime now = LocalDateTime.now();
        LocalDateTime thirtyMinutesLater = now.plusMinutes(30);

        // 查询30分钟后开始的会议
        // 这里需要在ReservationMapper中添加相应的方法
        List<Reservation> upcomingReservations = reservationMapper.getReservationsStartingBetween(now, thirtyMinutesLater);

        log.info("找到 {} 个即将开始的会议", upcomingReservations.size());

        for (Reservation reservation : upcomingReservations) {
            try {
                sendReminderEmail(reservation);
                log.info("已发送会议提醒邮件，预约ID: {}", reservation.getId());
            } catch (Exception e) {
                log.error("发送会议提醒邮件失败，预约ID: {}", reservation.getId(), e);
            }
        }
    }

    /**
     * 发送会议提醒邮件
     */
    public void sendReminderEmail(Reservation reservation) {

        // 获取用户信息
        User user = userMapper.getById(BaseContext.getCurrentId());

        if (user == null || user.getEmail() == null || user.getEmail().isEmpty()) {
            log.warn("用户邮箱信息不完整，无法发送邮件，用户ID: {}", reservation.getUserId());
            return;
        }

        // 创建邮件
        SimpleMailMessage message = new SimpleMailMessage();
        message.setTo(user.getEmail());
        message.setFrom("2281613734@qq.com");
        message.setSubject("会议提醒 - " + reservation.getMeetingTopic());
        message.setText(
                "您好 " + user.getUsername() + "，\n\n" +
                        "提醒您预约的会议即将开始：\n" +
                        "会议主题: " + reservation.getMeetingTopic() + "\n" +
                        "会议室ID: " + reservation.getRoomId() + "\n" +
                        "开始时间: " + reservation.getStartTime() + "\n" +
                        "结束时间: " + reservation.getEndTime() + "\n\n" +
                        "请准时参加！\n\n" +
                        "智能会议室系统"
        );

        // 发送邮件
        mailSender.send(message);
        log.info("会议提醒邮件已发送至: {}", user.getEmail());
    }

    // MeetingReminderService.java 新增定时任务

    /**
     * 每天凌晨2点检查超过24小时未审核的预约，自动取消
     */
    @Scheduled(cron = "0 0 2 * * ?")
    public void cancelTimeoutPendingReservations() {
        log.info("开始处理超时未审核的预约...");
        LocalDateTime twentyFourHoursAgo = LocalDateTime.now().minusHours(24);
        // 查询24小时前创建的待审核预约
        List<Reservation> timeoutReservations = reservationMapper.selectPendingByCreateTimeBefore(twentyFourHoursAgo);
        // 获取用户信息
        User user = userMapper.getById(BaseContext.getCurrentId());

        for (Reservation reservation : timeoutReservations) {
            reservation.setStatus(StatusConstant.TIMEOUT);
            reservationMapper.update(reservation);
            log.info("预约{}因超时未审核已自动取消", reservation.getId());
            // 发送超时取消通知
            SimpleMailMessage message = new SimpleMailMessage();
            message.setTo(user.getEmail());
            message.setSubject("预约取消通知");
            message.setFrom("2281613734@qq.com");
            message.setText(
                    "您好 " + user.getUsername() + "，\n\n" +
                            "预约" + reservation.getId() + "因超时未审核已自动取消。\n\n" +
                            "请重新预约。\n\n" +
                            "智能会议室系统"
            );
            mailSender.send(message);
        }
    }




}




