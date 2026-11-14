package com.sky.Controller.user;

import com.sky.context.BaseContext;
import com.sky.result.Result;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/user/notification")
public class NotificationController {
    @Autowired private JdbcTemplate jdbc;

    // Read persisted approval notices only; an empty table is an empty result, not fabricated notifications.
    @GetMapping("/my")
    public Result<List<Map<String, Object>>> mine() {
        List<Map<String, Object>> notices = jdbc.query(
                "SELECT n.id, n.content, n.is_read, n.create_time, r.status FROM notification n " +
                "JOIN reservation r ON n.related_id=r.id AND n.related_type=1 AND r.user_id=n.user_id " +
                "WHERE n.user_id=? AND n.notification_type=0 AND r.status IN (1,3) " +
                "ORDER BY n.create_time DESC, n.id DESC LIMIT 50", (rs, index) -> {
                    Map<String, Object> row = new LinkedHashMap<>();
                    row.put("id", rs.getInt("id"));
                    row.put("content", rs.getString("content"));
                    row.put("isRead", rs.getBoolean("is_read"));
                    row.put("createTime", rs.getTimestamp("create_time").toLocalDateTime());
                    int status = rs.getInt("status");
                    row.put("status", status);
                    row.put("title", status == 1 ? "预约审核通过" : "预约审核未通过");
                    return row;
                }, BaseContext.getCurrentId());
        return Result.success(notices);
    }
}
