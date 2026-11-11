"""Testes fornecidos: câmbio para BRL."""

from helpers import run_cli


def test_currency_conversion_to_brl(tmp_path):
    """Multiplica o valor pela taxa, sem inverter a operação."""
    report = run_cli(
        tmp_path,
        [
            {"reservation_id": "R-1", "currency": "BRL", "amount": "100.00"},
            {"reservation_id": "R-2", "currency": "USD", "amount": "100.00"},
        ],
    )
    assert report["summary"]["total_amount_brl"] == "642.00"
