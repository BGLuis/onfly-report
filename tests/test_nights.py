"""Testes fornecidos: noites de quarto na virada de mês."""

from helpers import run_cli


def test_nights_across_month_boundary(tmp_path):
    """A diferença de datas considera a virada de mês, não o dia do mês."""
    report = run_cli(
        tmp_path,
        [
            {
                "reservation_id": "R-1",
                "checkin_date": "2025-01-30",
                "checkout_date": "2025-02-02",
                "rooms": "1",
            }
        ],
    )
    assert report["summary"]["total_room_nights"] == 3
