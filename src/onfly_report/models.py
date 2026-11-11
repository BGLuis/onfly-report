"""Modelos de dados do consolidador."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class RawRow:
    """Linha crua lida do CSV, com o número da linha física no arquivo."""

    line_number: int
    values: dict[str, str]


@dataclass(frozen=True)
class Reservation:
    """Reserva já convertida para os tipos do domínio."""

    reservation_id: str
    traveler_name: str
    company_id: str
    hotel_id: str
    hotel_name: str
    city: str
    country: str
    checkin: date
    checkout: date
    rooms: int
    status: str
    currency: str
    amount: Decimal
    payment_method: str
    line_number: int
