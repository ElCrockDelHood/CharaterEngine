"""Contrato base para validadores del Character Engine."""


class Validator:
    """Clase base mínima para validadores de dominio."""

    def validate(self, subject):
        raise NotImplementedError
