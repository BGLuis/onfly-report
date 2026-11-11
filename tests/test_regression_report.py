"""Testes fornecidos: regressão ponta a ponta."""

from helpers import run_cli


def test_regression_report_on_sample(tmp_path):
    """Relatório completo de uma amostra pequena, com status, noites e câmbio."""
    report = run_cli(
        tmp_path,
        [
            {
                "reservation_id": "R-1",
                "amount": "1000.00",
                "checkin_date": "2025-01-10",
                "checkout_date": "2025-01-13",
            },
            {"reservation_id": "R-2", "status": "CANCELLED", "amount": "500.00"},
            {
                "reservation_id": "R-3",
                "currency": "USD",
                "amount": "100.00",
                "checkin_date": "2025-01-20",
                "checkout_date": "2025-01-22",
            },
        ],
    )
    assert report["summary"] == {
        "total_reservations": 3,
        "confirmed_reservations": 2,
        "cancelled_reservations": 1,
        "no_show_reservations": 0,
        "total_room_nights": 5,
        "total_amount_brl": "1542.00",
        "average_nightly_rate_brl": "308.40",
    }
