"""Interface de linha de comando do consolidador."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from .exceptions import InputFileError
from .logging_config import configure_logging
from .repositories.csv_rate_repository import CsvRateRepository
from .repositories.csv_reservation_repository import CsvReservationRepository
from .services.report_builder import ReportBuilder

logger = logging.getLogger("onfly_report")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="onfly_report",
        description="Consolida a exportação de reservas de hotel em um relatório JSON.",
    )
    parser.add_argument("--input", required=True, help="CSV de reservas")
    parser.add_argument("--rates", required=True, help="CSV de taxas de câmbio para BRL")
    parser.add_argument("--output", default="output/report.json", help="caminho do relatório JSON")
    parser.add_argument("--top", type=int, default=5, help="quantidade de hotéis no ranking")
    return parser


def main(argv: list[str] | None = None) -> int:
    configure_logging()
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.top < 1:
        parser.error("--top deve ser maior ou igual a 1")

    try:
        report = ReportBuilder(
            reservation_repository=CsvReservationRepository(Path(args.input)),
            rate_repository=CsvRateRepository(Path(args.rates)),
            top_n=args.top,
        ).build()
    except InputFileError as err:
        logger.error("falha ao ler a entrada: %s", err)
        return 2
    except Exception:
        logger.exception("erro inesperado ao gerar o relatório")
        return 1

    output_path = Path(args.output)
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    except OSError:
        logger.exception("falha ao escrever o relatório em %s", output_path)
        return 1

    summary = report["summary"]
    print(
        "Reservas: {total} | Confirmadas: {confirmed} | Noites: {nights} | Total BRL: {amount}".format(
            total=summary["total_reservations"],
            confirmed=summary["confirmed_reservations"],
            nights=summary["total_room_nights"],
            amount=summary["total_amount_brl"],
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
