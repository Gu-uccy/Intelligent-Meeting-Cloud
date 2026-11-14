package com.sky.Controller;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.redis.connection.RedisConnection;
import org.springframework.data.redis.connection.RedisConnectionFactory;
import org.springframework.http.ResponseEntity;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;
import java.util.LinkedHashMap;
import java.util.Map;

@RestController
public class HealthController {
    @Autowired private JdbcTemplate jdbc;
    @Autowired private RedisConnectionFactory redis;

    @GetMapping("/health")
    public ResponseEntity<Map<String, Object>> health() {
        boolean database = false;
        boolean schema = false;
        boolean cache = false;
        try {
            database = Integer.valueOf(1).equals(jdbc.queryForObject("SELECT 1", Integer.class));
            // Check the columns actually used by login, room paging and booking.
            jdbc.queryForList("SELECT username, is_admin, image FROM user LIMIT 0");
            jdbc.queryForList("SELECT version, image FROM meeting_room LIMIT 0");
            jdbc.queryForList("SELECT reservation_no, status FROM reservation LIMIT 0");
            jdbc.queryForList("SELECT related_id, is_read FROM notification LIMIT 0");
            schema = true;
        } catch (Exception ignored) { }
        try (RedisConnection connection = redis.getConnection()) {
            cache = "PONG".equalsIgnoreCase(connection.ping());
        } catch (Exception ignored) { }
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("service", "meeting-room-business");
        body.put("source", "spring-mysql");
        body.put("database", database);
        body.put("schema", schema);
        body.put("redis", cache);
        body.put("status", schema ? (cache ? "ready" : "degraded") : "unavailable");
        // Redis is currently unused by business methods; Local mode can run degraded.
        return ResponseEntity.status(schema ? 200 : 503).body(body);
    }
}
