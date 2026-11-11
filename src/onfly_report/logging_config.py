"""Configuração de logging do CLI (sempre em stderr)."""

from __future__ import annotations

import logging
import sys


def configure_logging(level: str = "INFO") -> None:
    """Configura o logger raiz para stderr, mantendo o stdout para o resumo."""
    logging.basicConfig(
        level=level,
        stream=sys.stderr,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
