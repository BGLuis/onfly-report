"""Cálculo de noites ocupadas."""

from __future__ import annotations

from datetime import date


def calculate_room_nights(checkin: date, checkout: date, rooms: int) -> int:
    """Calcula noites de quarto: diferença de dias (não inclusiva) vezes quartos."""
    if checkout <= checkin:
        raise ValueError("checkout deve ser posterior ao checkin")
    if rooms < 1:
        raise ValueError("rooms deve ser maior ou igual a 1")
    return (checkout - checkin).days * rooms
