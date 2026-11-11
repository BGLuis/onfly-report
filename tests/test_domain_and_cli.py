"""Testes adicionais de domínio, contrato do CLI, precisão Decimal e casos de borda."""

from __future__ import annotations

import csv
import json
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest
from helpers import BASE, COLUMNS

from onfly_report.cli import main
from onfly_report.exceptions import InputFileError
from onfly_report.models import RawRow
from onfly_report.repositories.csv_rate_repository import CsvRateRepository
from onfly_report.repositories.csv_reservation_repository import CsvReservationRepository
from onfly_report.services.currency_converter import convert_to_brl
from onfly_report.services.report_builder import ReportBuilder, format_money
from onfly_report.services.row_parser import RowParser
from onfly_report.services.status_policy import is_billable
from onfly_report.services.stay_calculator import calculate_room_nights

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"


def _write_reservations_csv(path: Path, rows: list[dict[str, str]]) -> Path:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows({**BASE, **row} for row in rows)
    return path


def _write_rates_csv(path: Path, content: str | None = None) -> Path:
    path.write_text(
        content or "currency,rate_to_brl\nBRL,1.000000\nUSD,5.420000\nEUR,5.880000\n",
        encoding="utf-8",
    )
    return path


def test_validation_sample_matches_readme_contract():
    """Valida que a amostra oficial produz exatamente todos os valores documentados no README."""
    fixed_now = datetime(2025, 7, 1, 10, 0, 0, tzinfo=timezone.utc)
    report = ReportBuilder(
        reservation_repository=CsvReservationRepository(DATA_DIR / "exemplo-validacao.csv"),
        rate_repository=CsvRateRepository(DATA_DIR / "taxas_cambio.csv"),
        top_n=5,
        now=fixed_now,
    ).build()

    assert report == {
        "report_version": "1.0",
        "generated_at": "2025-07-01T07:00:00-03:00",
        "summary": {
            "total_reservations": 12,
            "confirmed_reservations": 9,
            "cancelled_reservations": 2,
            "no_show_reservations": 1,
            "total_room_nights": 28,
            "total_amount_brl": "7566.00",
            "average_nightly_rate_brl": "270.21",
        },
        "by_month": [
            {
                "month": "2025-01",
                "reservations": 8,
                "room_nights": 25,
                "total_brl": "6684.00",
            },
            {
                "month": "2025-02",
                "reservations": 1,
                "room_nights": 3,
                "total_brl": "882.00",
            },
        ],
        "top_hotels": [
            {
                "hotel_id": "H01",
                "hotel_name": "Hotel Aurora Paulista",
                "room_nights": 3,
                "total_brl": "1200.00",
            },
            {
                "hotel_id": "H02",
                "hotel_name": "Hotel Mirante",
                "room_nights": 2,
                "total_brl": "1084.00",
            },
            {
                "hotel_id": "H12",
                "hotel_name": "Hotel Miami Beach",
                "room_nights": 1,
                "total_brl": "1000.00",
            },
            {
                "hotel_id": "H10",
                "hotel_name": "Hotel Madrid, Gran Vía",
                "room_nights": 4,
                "total_brl": "900.00",
            },
            {
                "hotel_id": "H09",
                "hotel_name": "Hotel Lisboa, Centro",
                "room_nights": 3,
                "total_brl": "882.00",
            },
        ],
    }


def test_full_dataset_reads_all_300_rows_without_truncation():
    """Garante que todas as 300 reservas de data/reservas_hoteis.csv são processadas."""
    report = ReportBuilder(
        reservation_repository=CsvReservationRepository(DATA_DIR / "reservas_hoteis.csv"),
        rate_repository=CsvRateRepository(DATA_DIR / "taxas_cambio.csv"),
        top_n=5,
    ).build()

    summary = report["summary"]
    assert summary == {
        "total_reservations": 300,
        "confirmed_reservations": 235,
        "cancelled_reservations": 31,
        "no_show_reservations": 34,
        "total_room_nights": 1347,
        "total_amount_brl": "396170.00",
        "average_nightly_rate_brl": "294.11",
    }
    assert sum(item["reservations"] for item in report["by_month"]) == 235
    assert sum(item["room_nights"] for item in report["by_month"]) == 1347
    assert [item["month"] for item in report["by_month"]] == [
        "2024-12",
        "2025-01",
        "2025-02",
        "2025-03",
        "2025-04",
        "2025-05",
        "2025-06",
    ]
    assert [hotel["hotel_id"] for hotel in report["top_hotels"]] == ["H06", "H10", "H12", "H07", "H11"]


def test_decimal_exact_sum_and_round_half_up_only_at_serialization(tmp_path):
    """Soma valores exatos em Decimal e arredonda apenas na serialização com ROUND_HALF_UP."""
    assert format_money(Decimal("10.005")) == "10.01"
    assert format_money(Decimal("10.015")) == "10.02"
    assert format_money(Decimal("10.004")) == "10.00"

    input_path = _write_reservations_csv(
        tmp_path / "reservas.csv",
        [
            {"reservation_id": "R-1", "currency": "USD", "amount": "1.00"},
            {"reservation_id": "R-2", "currency": "USD", "amount": "1.00"},
        ],
    )
    rates_path = _write_rates_csv(
        tmp_path / "rates.csv",
        "currency,rate_to_brl\nBRL,1.000000\nUSD,1.004000\n",
    )

    report = ReportBuilder(
        reservation_repository=CsvReservationRepository(input_path),
        rate_repository=CsvRateRepository(rates_path),
    ).build()

    # Cada reserva vale 1.004 BRL; se arredondasse antes da soma daria 2.00 em vez de 2.008 -> 2.01
    assert report["summary"]["total_amount_brl"] == "2.01"
    assert report["summary"]["average_nightly_rate_brl"] == "1.00"


def test_empty_or_unconfirmed_reservations_produce_zero_totals(tmp_path):
    """Sem reservas confirmadas, total_room_nights é 0 e average_nightly_rate_brl é '0.00'."""
    input_path = _write_reservations_csv(
        tmp_path / "reservas.csv",
        [
            {"reservation_id": "R-1", "status": "CANCELLED", "amount": "500.00"},
            {"reservation_id": "R-2", "status": "NO_SHOW", "amount": "300.00"},
        ],
    )
    rates_path = _write_rates_csv(tmp_path / "rates.csv")

    report = ReportBuilder(
        reservation_repository=CsvReservationRepository(input_path),
        rate_repository=CsvRateRepository(rates_path),
    ).build()

    assert report["summary"] == {
        "total_reservations": 2,
        "confirmed_reservations": 0,
        "cancelled_reservations": 1,
        "no_show_reservations": 1,
        "total_room_nights": 0,
        "total_amount_brl": "0.00",
        "average_nightly_rate_brl": "0.00",
    }
    assert report["by_month"] == []
    assert report["top_hotels"] == []


def test_room_nights_across_year_leap_year_and_multiple_rooms():
    """Calcula noites corretamente na virada de ano, em ano bissexto e com múltiplos quartos."""
    assert calculate_room_nights(date(2024, 12, 30), date(2025, 1, 2), rooms=2) == 6
    assert calculate_room_nights(date(2024, 2, 28), date(2024, 3, 1), rooms=1) == 2
    assert calculate_room_nights(date(2025, 2, 28), date(2025, 3, 1), rooms=1) == 1

    with pytest.raises(ValueError, match="checkout deve ser posterior ao checkin"):
        calculate_room_nights(date(2025, 1, 10), date(2025, 1, 10), rooms=1)

    with pytest.raises(ValueError, match="rooms deve ser maior ou igual a 1"):
        calculate_room_nights(date(2025, 1, 10), date(2025, 1, 12), rooms=0)


def test_top_hotels_tie_breaking_by_hotel_id_and_by_month_ordering(tmp_path):
    """Desempata hotéis de mesmo valor por hotel_id ascendente e ordena meses ascendentemente."""
    input_path = _write_reservations_csv(
        tmp_path / "reservas.csv",
        [
            {
                "reservation_id": "R-1",
                "hotel_id": "H03",
                "hotel_name": "Hotel C",
                "checkin_date": "2025-03-10",
                "checkout_date": "2025-03-12",
                "amount": "500.00",
            },
            {
                "reservation_id": "R-2",
                "hotel_id": "H01",
                "hotel_name": "Hotel A",
                "checkin_date": "2024-12-31",
                "checkout_date": "2025-01-03",
                "amount": "500.00",
            },
            {
                "reservation_id": "R-3",
                "hotel_id": "H02",
                "hotel_name": "Hotel B",
                "checkin_date": "2025-01-15",
                "checkout_date": "2025-01-16",
                "amount": "500.00",
            },
        ],
    )
    rates_path = _write_rates_csv(tmp_path / "rates.csv")

    report = ReportBuilder(
        reservation_repository=CsvReservationRepository(input_path),
        rate_repository=CsvRateRepository(rates_path),
        top_n=10,
    ).build()

    assert [h["hotel_id"] for h in report["top_hotels"]] == ["H01", "H02", "H03"]
    assert [m["month"] for m in report["by_month"]] == ["2024-12", "2025-01", "2025-03"]
    assert report["by_month"][0]["room_nights"] == 3


def test_status_policy_and_currency_converter_validation():
    """Valida política de status faturável e erro de moeda inexistente."""
    assert is_billable("CONFIRMED") is True
    assert is_billable("CANCELLED") is False
    assert is_billable("NO_SHOW") is False

    with pytest.raises(InputFileError, match="moeda sem taxa de câmbio cadastrada: GBP"):
        convert_to_brl(Decimal("100.00"), "GBP", {"BRL": Decimal("1.0")})


@pytest.mark.parametrize(
    "overrides,error_match",
    [
        ({"checkin_date": "2025-01-10", "checkout_date": "2025-01-10"}, "checkout .* posterior ao checkin"),
        ({"checkin_date": "2025-01-12", "checkout_date": "2025-01-10"}, "checkout .* posterior ao checkin"),
        ({"rooms": "0"}, "rooms deve ser >= 1"),
        ({"status": "PENDING"}, "status desconhecido"),
        ({"amount": "-10.00"}, "amount inválido"),
        ({"hotel_id": "   "}, "campos obrigatórios vazios"),
        ({"checkin_date": "data-invalida"}, "linha 2 inválida"),
    ],
)
def test_row_parser_rejects_invalid_domain_values(overrides: dict[str, str], error_match: str):
    """Garante que RowParser levanta InputFileError para dados inconsistentes."""
    parser = RowParser()
    raw = RawRow(line_number=2, values={**BASE, **overrides})
    with pytest.raises(InputFileError, match=error_match):
        parser.parse(raw)


def test_cli_exit_codes_and_stdout_contract(tmp_path, capsys):
    """Verifica códigos de saída 0, 2 e 1 e o formato do resumo em stdout."""
    output_path = tmp_path / "nested" / "report.json"
    rc = main(
        [
            "--input",
            str(DATA_DIR / "exemplo-validacao.csv"),
            "--rates",
            str(DATA_DIR / "taxas_cambio.csv"),
            "--output",
            str(output_path),
        ]
    )
    assert rc == 0
    captured = capsys.readouterr()
    assert captured.out.strip() == "Reservas: 12 | Confirmadas: 9 | Noites: 28 | Total BRL: 7566.00"
    saved = json.loads(output_path.read_text(encoding="utf-8"))
    assert saved["report_version"] == "1.0"
    assert saved["generated_at"].endswith("-03:00")

    # Código 2 para arquivo inexistente
    assert (
        main(
            [
                "--input",
                str(tmp_path / "inexistente.csv"),
                "--rates",
                str(DATA_DIR / "taxas_cambio.csv"),
                "--output",
                str(output_path),
            ]
        )
        == 2
    )

    # Código 2 para --top inválido
    with pytest.raises(SystemExit) as exc_info:
        main(
            [
                "--input",
                str(DATA_DIR / "exemplo-validacao.csv"),
                "--rates",
                str(DATA_DIR / "taxas_cambio.csv"),
                "--top",
                "0",
            ]
        )
    assert exc_info.value.code == 2

    # Código 1 quando falha ao escrever no destino (ex.: destino é um diretório)
    dir_output = tmp_path / "dir_as_output"
    dir_output.mkdir()
    assert (
        main(
            [
                "--input",
                str(DATA_DIR / "exemplo-validacao.csv"),
                "--rates",
                str(DATA_DIR / "taxas_cambio.csv"),
                "--output",
                str(dir_output),
            ]
        )
        == 1
    )


def test_csv_repositories_and_report_builder_error_handling(tmp_path):
    """Valida erros de formato em CsvRateRepository, CsvReservationRepository e ReportBuilder."""
    bad_rates = tmp_path / "bad_rates.csv"

    bad_rates.write_text("currency\nBRL\n", encoding="utf-8")
    with pytest.raises(InputFileError, match="colunas obrigatórias ausentes"):
        CsvRateRepository(bad_rates).read()

    bad_rates.write_text("currency,rate_to_brl\n", encoding="utf-8")
    with pytest.raises(InputFileError, match="tabela de câmbio vazia"):
        CsvRateRepository(bad_rates).read()

    bad_rates.write_text("currency,rate_to_brl\nBRL,0\n", encoding="utf-8")
    with pytest.raises(InputFileError, match="taxa não positiva"):
        CsvRateRepository(bad_rates).read()

    bad_rates.write_text("currency,rate_to_brl\nBRL,abc\n", encoding="utf-8")
    with pytest.raises(InputFileError, match="taxa inválida"):
        CsvRateRepository(bad_rates).read()

    bad_rates.write_text("currency,rate_to_brl\nBRL,\n", encoding="utf-8")
    with pytest.raises(InputFileError, match="linha de câmbio incompleta"):
        CsvRateRepository(bad_rates).read()

    bad_rates.write_text("currency,rate_to_brl\nBRL,1.0,extra\n", encoding="utf-8")
    with pytest.raises(InputFileError, match="colunas excedentes"):
        CsvRateRepository(bad_rates).read()

    with pytest.raises(InputFileError, match="tabela de câmbio não encontrada"):
        CsvRateRepository(tmp_path / "missing_rates.csv").read()

    bad_res = tmp_path / "bad_res.csv"
    bad_res.write_text("reservation_id,amount\nR-1,10.00\n", encoding="utf-8")
    with pytest.raises(InputFileError, match="colunas obrigatórias ausentes"):
        CsvReservationRepository(bad_res).read()

    bad_res.write_text(",".join(COLUMNS) + "\nR-1,apenas_duas_colunas\n", encoding="utf-8")
    with pytest.raises(InputFileError, match="número incorreto de colunas"):
        CsvReservationRepository(bad_res).read()

    with pytest.raises(ValueError, match="top_n deve ser maior ou igual a 1"):
        ReportBuilder(
            reservation_repository=CsvReservationRepository(DATA_DIR / "exemplo-validacao.csv"),
            rate_repository=CsvRateRepository(DATA_DIR / "taxas_cambio.csv"),
            top_n=0,
        )


def test_non_report_columns_do_not_affect_totals_or_fail_when_empty(tmp_path):
    """Colunas que não entram no relatório (ex.: reservation_id, traveler_name) podem estar vazias."""
    input_path = _write_reservations_csv(
        tmp_path / "reservas.csv",
        [
            {
                "reservation_id": "",
                "traveler_name": "",
                "company_id": "",
                "city": "",
                "country": "",
                "payment_method": "",
                "booked_at": "",
                "hotel_id": "H01",
                "hotel_name": "Hotel A",
                "checkin_date": "2025-01-10",
                "checkout_date": "2025-01-12",
                "rooms": "1",
                "status": "CONFIRMED",
                "currency": "BRL",
                "amount": "250.00",
            }
        ],
    )
    rates_path = _write_rates_csv(tmp_path / "rates.csv")

    report = ReportBuilder(
        reservation_repository=CsvReservationRepository(input_path),
        rate_repository=CsvRateRepository(rates_path),
    ).build()

    assert report["summary"]["total_reservations"] == 1
    assert report["summary"]["confirmed_reservations"] == 1
    assert report["summary"]["total_room_nights"] == 2
    assert report["summary"]["total_amount_brl"] == "250.00"


def test_csv_files_with_utf8_bom_are_accepted(tmp_path):
    """Arquivos CSV exportados com BOM UTF-8 (utf-8-sig) são lidos sem erro de cabeçalho."""
    bom_res = tmp_path / "reservas_bom.csv"
    bom_rates = tmp_path / "rates_bom.csv"

    bom_res.write_text(
        (DATA_DIR / "exemplo-validacao.csv").read_text(encoding="utf-8"),
        encoding="utf-8-sig",
    )
    bom_rates.write_text(
        (DATA_DIR / "taxas_cambio.csv").read_text(encoding="utf-8"),
        encoding="utf-8-sig",
    )

    report = ReportBuilder(
        reservation_repository=CsvReservationRepository(bom_res),
        rate_repository=CsvRateRepository(bom_rates),
    ).build()

    assert report["summary"]["total_reservations"] == 12
    assert report["summary"]["total_amount_brl"] == "7566.00"


