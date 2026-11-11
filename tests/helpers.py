"""Utilitários dos testes fornecidos."""

from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"

COLUMNS = [
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
]

BASE = {
    "reservation_id": "R-1",
    "traveler_name": "Pessoa Teste",
    "company_id": "EMP-001",
    "hotel_id": "H01",
    "hotel_name": "Hotel Teste",
    "city": "Sao Paulo",
    "country": "BR",
    "checkin_date": "2025-01-10",
    "checkout_date": "2025-01-11",
    "rooms": "1",
    "status": "CONFIRMED",
    "currency": "BRL",
    "amount": "100.00",
    "payment_method": "CORPORATE_CARD",
    "booked_at": "2025-01-01T10:00:00-03:00",
}


def run_cli(tmp_path: Path, rows: list[dict[str, str]], top: int = 5) -> dict:
    """Executa o CLI sobre um CSV temporário e devolve o relatório."""
    input_path = tmp_path / "reservas.csv"
    rates_path = tmp_path / "rates.csv"
    output_path = tmp_path / "report.json"

    with input_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows({**BASE, **row} for row in rows)

    rates_path.write_text(
        "currency,rate_to_brl\nBRL,1.000000\nUSD,5.420000\nEUR,5.880000\n",
        encoding="utf-8",
    )

    environment = os.environ.copy()
    for import_root in (SRC_DIR, PROJECT_ROOT):
        if (import_root / "onfly_report").is_dir():
            environment["PYTHONPATH"] = str(import_root) + os.pathsep + environment.get("PYTHONPATH", "")
            break
    environment["PYTHONDONTWRITEBYTECODE"] = "1"

    process = subprocess.run(
        [
            sys.executable,
            "-m",
            "onfly_report",
            "--input",
            str(input_path),
            "--rates",
            str(rates_path),
            "--output",
            str(output_path),
            "--top",
            str(top),
        ],
        cwd=str(PROJECT_ROOT),
        env=environment,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert process.returncode == 0, process.stderr
    return json.loads(output_path.read_text(encoding="utf-8"))
