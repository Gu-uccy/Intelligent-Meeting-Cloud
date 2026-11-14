package com.sky;

import com.sky.Mapper.ReservationMapper;
import com.sky.Service.RoomService;
import com.sky.Service.UserService;
import com.sky.Service.Impl.ReservationServiceImpl;
import com.sky.context.BaseContext;
import com.sky.dto.ReservationDto;
import com.sky.entity.MeetingRoom;
import com.sky.entity.Reservation;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import org.springframework.test.util.ReflectionTestUtils;
import java.time.LocalDate;
import java.util.List;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

class ReservationValidationTests {
    private ReservationMapper mapper;
    private RoomService rooms;
    private ReservationServiceImpl service;
    private MeetingRoom room;
    private ReservationDto request;

    @BeforeEach void setUp() {
        mapper = mock(ReservationMapper.class);
        rooms = mock(RoomService.class);
        service = new ReservationServiceImpl();
        ReflectionTestUtils.setField(service, "reservationMapper", mapper);
        ReflectionTestUtils.setField(service, "roomService", rooms);
        ReflectionTestUtils.setField(service, "userService", mock(UserService.class));
        room = new MeetingRoom(); room.setId(1); room.setCapacity(10); room.setIsActive(1);
        when(rooms.getById(1)).thenReturn(room);
        when(rooms.updateStatusWithVersion(1, 0)).thenReturn(1);
        when(mapper.selectConflictReservations(anyInt(), any(), any())).thenReturn(List.of());
        when(mapper.insertReservation(any())).thenReturn(1);
        request = new ReservationDto(); request.setRoomId(1); request.setParticipantNum(8);
        request.setStartTime(LocalDate.now().plusDays(2).atTime(10, 0));
        request.setEndTime(request.getStartTime().plusHours(1));
        BaseContext.setCurrentId(3);
    }
    @AfterEach void cleanUp() { BaseContext.removeCurrentId(); }

    @ParameterizedTest
    @ValueSource(strings={"missing-room", "missing-start", "missing-end", "equal-times", "reverse-times",
            "past", "eight-and-half-hours", "off-grid", "zero-people", "missing-people", "over-capacity", "disabled-room", "unknown-room"})
    void rejectsInvalidRequestsBeforeWriting(String scenario) {
        switch (scenario) {
            case "missing-room" -> request.setRoomId(null);
            case "missing-start" -> request.setStartTime(null);
            case "missing-end" -> request.setEndTime(null);
            case "equal-times" -> request.setEndTime(request.getStartTime());
            case "reverse-times" -> request.setEndTime(request.getStartTime().minusMinutes(30));
            case "past" -> { request.setStartTime(request.getStartTime().minusDays(3)); request.setEndTime(request.getStartTime().plusHours(1)); }
            case "eight-and-half-hours" -> request.setEndTime(request.getStartTime().plusMinutes(510));
            case "off-grid" -> request.setStartTime(request.getStartTime().plusMinutes(1));
            case "zero-people" -> request.setParticipantNum(0);
            case "missing-people" -> request.setParticipantNum(null);
            case "over-capacity" -> request.setParticipantNum(11);
            case "disabled-room" -> room.setIsActive(0);
            case "unknown-room" -> when(rooms.getById(1)).thenReturn(null);
        }
        assertThrows(IllegalArgumentException.class, () -> service.addReservation(request));
        verify(mapper, never()).insertReservation(any());
        verify(rooms, never()).updateStatusWithVersion(any(), any());
    }

    @Test void acceptsExactlyEightHoursAndAppliesBuffer() {
        request.setEndTime(request.getStartTime().plusHours(8));
        assertEquals(1, service.addReservation(request));
        verify(mapper).selectConflictReservations(1, request.getStartTime().minusMinutes(10), request.getEndTime().plusMinutes(10));
        verify(mapper).insertReservation(argThat(r -> r.getUserId() == 3 && r.getStatus() == 0));
    }

    @Test void rejectsOtherUsersCancellation() {
        Reservation other = new Reservation(); other.setUserId(4); other.setStatus(0);
        when(mapper.selectById(7)).thenReturn(other);
        assertThrows(IllegalArgumentException.class, () -> service.cancel(7));
        verify(mapper, never()).update(any());
    }

    @Test void rejectsConcurrentVersionChangeWithoutInserting() {
        when(rooms.updateStatusWithVersion(1, 0)).thenReturn(0);
        assertThrows(RuntimeException.class, () -> service.addReservation(request));
        verify(mapper, never()).insertReservation(any());
    }
}
