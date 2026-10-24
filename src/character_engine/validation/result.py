"""Resultado estructurado de una validación."""

from dataclasses import dataclass, field


@dataclass
class ValidationResult:
    """Acumula errores, warnings, información y métricas de validación."""

    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    infos: list[str] = field(default_factory=list)
    metrics: dict[str, float] = field(default_factory=dict)
    is_valid: bool = True

    def add_error(self, message: str) -> None:
        self.errors.append(message)
        self.is_valid = False

    def add_warning(self, message: str) -> None:
        self.warnings.append(message)

    def add_info(self, message: str) -> None:
        self.infos.append(message)

    def add_metric(self, name: str, value: float) -> None:
        self.metrics[name] = value

    def merge(self, other: "ValidationResult") -> "ValidationResult":
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
        self.infos.extend(other.infos)
        self.metrics.update(other.metrics)

        if not other.is_valid:
            self.is_valid = False

        return self

    def finish(self) -> "ValidationResult":
        self.is_valid = len(self.errors) == 0
        return self
