"""Long-bone maximum length from stature via forensic regression equations.

Equations have the form ``stature_cm = a * bone_length_cm + b`` (Trotter 1970,
Trotter & Gleser 1952/1958). We invert them to obtain the expected *maximum bone
length* for a target stature. Maximum length is an osteometric-board measurement
and is longer than the joint-centre distance stored in ``human_adult_206.json``;
it therefore drives bone **mesh extents**, never joint positions.

Only coefficients verified against the literature are marked ``PROVEN``; anything
else stays ``UNKNOWN`` and ``bone_length_from_stature`` refuses to compute it.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Mapping, Optional

from ..reference.source import ProvenanceState

LONG_BONES = ("FEMUR", "TIBIA", "FIBULA", "HUMERUS", "RADIUS", "ULNA")

_PROV = {
    "PROVEN": ProvenanceState.PROVEN,
    "DERIVED": ProvenanceState.DERIVED,
    "ESTIMATE": ProvenanceState.ESTIMATE,
    "ASSUMED": ProvenanceState.ASSUMED,
    "ASSUMPTION": ProvenanceState.ASSUMED,
    "PLACEHOLDER": ProvenanceState.PLACEHOLDER,
    "PARTIAL": ProvenanceState.UNKNOWN,
    "UNKNOWN": ProvenanceState.UNKNOWN,
}


@dataclass(frozen=True)
class LongBoneRegression:
    bone: str
    a: Optional[float]
    b: Optional[float]
    see_cm: Optional[float]
    source_id: str
    population: str
    provenance: ProvenanceState

    @property
    def is_usable(self) -> bool:
        return self.a is not None and self.b is not None and self.provenance == ProvenanceState.PROVEN

    def stature_cm(self, bone_length_cm: float) -> float:
        if not self.is_usable:
            raise ValueError(f"{self.bone}: regression not usable ({self.provenance.value})")
        return self.a * bone_length_cm + self.b

    def bone_length_cm(self, stature_cm: float) -> float:
        if not self.is_usable:
            raise ValueError(f"{self.bone}: regression not usable ({self.provenance.value})")
        return (stature_cm - self.b) / self.a


@dataclass(frozen=True)
class OsteometricTable:
    """All regressions grouped by population key (e.g. ``male_white``)."""

    regressions: Mapping[str, Mapping[str, LongBoneRegression]]
    shaft_diameters_m: Mapping[str, float]
    shaft_diameter_provenance: ProvenanceState

    def populations(self):
        return tuple(self.regressions.keys())

    def get(self, population: str, bone: str) -> LongBoneRegression:
        try:
            return self.regressions[population][bone]
        except KeyError as exc:
            raise KeyError(f"no regression for {population}/{bone}") from exc

    def lengths_for_stature(self, stature_m: float, population: str = "male_white") -> Dict[str, float]:
        """Return usable bone lengths (metres) for the stature; skips UNKNOWN entries."""
        out: Dict[str, float] = {}
        for bone, reg in self.regressions[population].items():
            if reg.is_usable:
                out[bone] = round(reg.bone_length_cm(stature_m * 100.0) / 100.0, 4)
        return out


def default_osteometry_path() -> Path:
    # long_bones.py -> osteometry -> anatomy -> domain -> character_engine
    return Path(__file__).resolve().parents[3] / "data" / "anatomy" / "references" / "osteometry.json"


def load_osteometry(path: Optional[Path] = None) -> OsteometricTable:
    data = json.loads(Path(path or default_osteometry_path()).read_text(encoding="utf-8"))["osteometric_data"]
    regs: Dict[str, Dict[str, LongBoneRegression]] = {}
    for pop, pdata in data["regressions"].items():
        pop_prov = pdata.get("provenance", "UNKNOWN")
        regs[pop] = {}
        for bone, coeff in pdata["bones"].items():
            prov = _PROV[coeff.get("provenance", pop_prov)]
            regs[pop][bone] = LongBoneRegression(
                bone=bone, a=coeff.get("a"), b=coeff.get("b"), see_cm=coeff.get("see_cm"),
                source_id=pdata["source_id"], population=pdata["population"], provenance=prov,
            )
    sd = data.get("shaft_diameters", {})
    diameters = {k: float(v) for k, v in sd.items() if k in LONG_BONES}
    return OsteometricTable(
        regressions=regs,
        shaft_diameters_m=diameters,
        shaft_diameter_provenance=_PROV[sd.get("provenance", "UNKNOWN")],
    )


def bone_length_from_stature(bone: str, stature_m: float, population: str = "male_white",
                             table: Optional[OsteometricTable] = None) -> float:
    """Expected maximum length (metres) of ``bone`` for a person of ``stature_m``."""
    table = table or load_osteometry()
    return round(table.get(population, bone).bone_length_cm(stature_m * 100.0) / 100.0, 4)
