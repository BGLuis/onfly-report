"""Construção do relatório consolidado."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal

from ..repositories.csv_rate_repository import CsvRateRepository
from ..repositories.csv_reservation_repository import CsvReservationRepository
from .currency_converter import convert_to_brl
from .row_parser import RowParser
from .status_policy import is_billable
from .stay_calculator import calculate_room_nights

MONEY_QUANTUM = Decimal("0.01")
FIXED_OFFSET = timezone(timedelta(hours=-3))


def format_money(value: Decimal) -> str:
    """Serializa dinheiro com duas casas, arredondamento half-up."""
    return str(value.quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP))


class ReportBuilder:
    """Orquestra leitura, conversão e agregação."""

    def __init__(
        self,
        reservation_repository: CsvReservationRepository,
        rate_repository: CsvRateRepository,
        top_n: int = 5,
        now: datetime | None = None,
    ) -> None:
        self._reservation_repository = reservation_repository
        self._rate_repository = rate_repository
        self._top_n = top_n
        self._now = now

    def build(self) -> dict:
        parser = RowParser()
        reservations = [parser.parse(raw) for raw in self._reservation_repository.read()]
        rates = self._rate_repository.read()

        status_counts = {"CONFIRMED": 0, "CANCELLED": 0, "NO_SHOW": 0}
        for reservation in reservations:
            status_counts[reservation.status] = status_counts.get(reservation.status, 0) + 1

        confirmed = [row for row in reservations if is_billable(row.status)]

        monthly: dict[str, dict] = defaultdict(
            lambda: {"reservations": 0, "room_nights": 0, "amount": Decimal("0")}
        )
        hotels: dict[str, dict] = defaultdict(
            lambda: {"hotel_name": "", "room_nights": 0, "amount": Decimal("0")}
        )

        total_nights = 0
        total_amount = Decimal("0")

        for row in confirmed:
            room_nights = calculate_room_nights(row.checkin, row.checkout, row.rooms)
            amount_brl = convert_to_brl(row.amount, row.currency, rates)

            total_nights += room_nights
            total_amount += amount_brl

            month_key = row.checkin.strftime("%Y-%m")
            monthly[month_key]["reservations"] += 1
            monthly[month_key]["room_nights"] += room_nights
            monthly[month_key]["amount"] += amount_brl

            hotels[row.hotel_id]["hotel_name"] = row.hotel_name
            hotels[row.hotel_id]["room_nights"] += room_nights
            hotels[row.hotel_id]["amount"] += amount_brl

        average_nightly_rate = (
            total_amount / Decimal(total_nights) if total_nights > 0 else Decimal("0")
        )

        by_month = [
            {
                "month": month,
                "reservations": data["reservations"],
                "room_nights": data["room_nights"],
                "total_brl": format_money(data["amount"]),
            }
            for month, data in sorted(monthly.items())
        ]

        ranked_hotels = sorted(hotels.items(), key=lambda item: (item[1]["amount"], item[0]))
        top_hotels = [
            {
                "hotel_id": hotel_id,
                "hotel_name": data["hotel_name"],
                "room_nights": data["room_nights"],
                "total_brl": format_money(data["amount"]),
            }
            for hotel_id, data in ranked_hotels[: self._top_n]
        ]

        now = self._now or datetime.now(FIXED_OFFSET)

        return {
            "report_version": "1.0",
            "generated_at": now.isoformat(timespec="seconds"),
            "summary": {
                "total_reservations": len(reservations),
                "confirmed_reservations": status_counts.get("CONFIRMED", 0),
                "cancelled_reservations": status_counts.get("CANCELLED", 0),
                "no_show_reservations": status_counts.get("NO_SHOW", 0),
                "total_room_nights": total_nights,
                "total_amount_brl": format_money(total_amount),
                "average_nightly_rate_brl": format_money(average_nightly_rate),
            },
            "by_month": by_month,
            "top_hotels": top_hotels,
        }
