"""Conversão de valores para BRL."""

from __future__ import annotations

from decimal import Decimal

from ..exceptions import InputFileError


def convert_to_brl(amount: Decimal, currency: str, rates: dict[str, Decimal]) -> Decimal:
    """Converte um valor na moeda informada para BRL usando a taxa da tabela."""
    try:
        rate = rates[currency]
    except KeyError as err:
        raise InputFileError(f"moeda sem taxa de câmbio cadastrada: {currency}") from err
    return amount * rate
