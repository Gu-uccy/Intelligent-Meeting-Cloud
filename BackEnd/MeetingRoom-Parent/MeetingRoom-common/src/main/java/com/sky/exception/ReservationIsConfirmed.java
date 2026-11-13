package com.sky.exception;

public class ReservationIsConfirmed extends RuntimeException {
    public ReservationIsConfirmed(String message) {
        super(message);
    }
}
