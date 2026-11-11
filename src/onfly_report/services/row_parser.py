"""Conversão de uma linha do CSV para o modelo de reserva."""

from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation

from ..exceptions import InputFileError
from ..models import RawRow, Reservation
from .status_policy import VALID_STATUSES


class RowParser:
    """Converte a linha crua em Reservation.

    O arquivo de entrada é consistente; falhas de formato são erro de arquivo, não dado a
    ser descartado.
    """

    def parse(self, raw: RawRow) -> Reservation:
        values = raw.values
        try:
            reservation_id = (values.get("reservation_id") or "").strip()
            hotel_id = (values.get("hotel_id") or "").strip()
            hotel_name = (values.get("hotel_name") or "").strip()
            checkin = date.fromisoformat((values.get("checkin_date") or "").strip())
            checkout = date.fromisoformat((values.get("checkout_date") or "").strip())
            rooms = int((values.get("rooms") or "").strip())
            status = (values.get("status") or "").strip()
            currency = (values.get("currency") or "").strip().upper()
            amount = Decimal((values.get("amount") or "").strip())
        except (ValueError, InvalidOperation) as err:
            raise InputFileError(f"linha {raw.line_number} inválida: {err}") from err

        if not hotel_id or not hotel_name or not currency:
            raise InputFileError(f"linha {raw.line_number} inválida: campos obrigatórios vazios")
        if checkout <= checkin:
            raise InputFileError(
                f"linha {raw.line_number} inválida: checkout ({checkout}) deve ser posterior ao checkin ({checkin})"
            )
        if rooms < 1:
            raise InputFileError(f"linha {raw.line_number} inválida: rooms deve ser >= 1")
        if status not in VALID_STATUSES:
            raise InputFileError(f"linha {raw.line_number} inválida: status desconhecido '{status}'")
        if not amount.is_finite() or amount < 0:
            raise InputFileError(f"linha {raw.line_number} inválida: amount inválido '{amount}'")

        return Reservation(
            reservation_id=reservation_id,
            traveler_name=(values.get("traveler_name") or "").strip(),
            company_id=(values.get("company_id") or "").strip(),
            hotel_id=hotel_id,
            hotel_name=hotel_name,
            city=(values.get("city") or "").strip(),
            country=(values.get("country") or "").strip(),
            checkin=checkin,
            checkout=checkout,
            rooms=rooms,
            status=status,
            currency=currency,
            amount=amount,
            payment_method=(values.get("payment_method") or "").strip(),
            line_number=raw.line_number,
        )
