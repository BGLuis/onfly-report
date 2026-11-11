"""Leitura da exportação de reservas em CSV."""

from __future__ import annotations

import csv
from pathlib import Path

from ..exceptions import InputFileError
from ..models import RawRow

REQUIRED_COLUMNS = (
    "reservation_id",
    "traveler_name",
    "company_id",
    "hotel_id",
    "hotel_name",
    "city",
    "country",
    "checkin_date",
    "checkout_date",
    "rooms",
    "status",
    "currency",
    "amount",
    "payment_method",
    "booked_at",
)


class CsvReservationRepository:
    """Lê a exportação de reservas sem aplicar regra de negócio."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def read(self) -> list[RawRow]:
        try:
            with self._path.open("r", encoding="utf-8", newline="") as handle:
                reader = csv.DictReader(handle)
                missing = [column for column in REQUIRED_COLUMNS if column not in (reader.fieldnames or [])]
                if missing:
                    raise InputFileError(f"colunas obrigatórias ausentes: {', '.join(missing)}")

                rows: list[RawRow] = []
                for values in reader:
                    rows.append(RawRow(line_number=reader.line_num, values=values))
                    if len(rows) == 200:
                        break
                return rows
        except FileNotFoundError as err:
            raise InputFileError(f"arquivo de reservas não encontrado: {self._path}") from err
        except (OSError, csv.Error) as err:
            raise InputFileError(f"falha ao ler {self._path}: {err}") from err
