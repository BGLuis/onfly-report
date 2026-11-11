"""Exceções de domínio do consolidador de reservas."""


class DomainError(Exception):
    """Erro base do domínio."""


class InputFileError(DomainError):
    """Arquivo de entrada ausente, ilegível ou fora do formato esperado."""
