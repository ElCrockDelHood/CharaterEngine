"""Character templates: adult male/female, child, elderly, and animal placeholders.

A template is *parameters with provenance*, never geometry. ``build_character_bones``
applies stature retarget + pose to the canonical bone list and returns bone dicts that
any adapter (glTF exporter, Blender addon) can consume.

Honesty rules (Decision 12): values without a verified source are labelled
``ESTIMATE``/``PLACEHOLDER``; species without canonical data raise instead of guessing.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, replace
from enum import Enum
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

from ..anatomy.pose import apply_pose
from ..anatomy.proportions.stature_retarget import DRILLIS_CONTINI_RATIOS, retarget_stature
from ..anatomy.reference.source import ProvenanceState


class Sex(Enum):
    MALE = "male"
    FEMALE = "female"
    UNSPECIFIED = "unspecified"


class Species(Enum):
    HUMAN = "human"
    HORSE = "horse"
    DOG = "dog"


@dataclass(frozen=True)
class CharacterParameters:
    """User-editable parameters (the character editor edits exactly this)."""

    stature_m: float
    sex: Sex = Sex.MALE
    age_years: float = 30.0
    species: Species = Species.HUMAN
    pose: str = "tpose"
    osteometric_population: str = "male_white"
    proportion_ratios: Mapping[str, float] = field(default_factory=lambda: dict(DRILLIS_CONTINI_RATIOS))
    morph_weights: Mapping[str, float] = field(default_factory=dict)   # appearance shape keys (P1)

    def with_(self, **changes) -> CharacterParameters:
        return replace(self, **changes)


@dataclass(frozen=True)
class CharacterTemplate:
    template_id: str
    label: str
    params: CharacterParameters
    stature_provenance: ProvenanceState
    proportion_provenance: ProvenanceState
    source_id: str
    notes: str
    available: bool = True

    @property
    def is_human(self) -> bool:
        return self.params.species == Species.HUMAN


def _stature_after_ageing(stature_young_m: float, age_years: float) -> float:
    """Trotter & Gleser (1951) ageing correction: −0.06 cm per year after 30."""
    if age_years <= 30:
        return stature_young_m
    return round(stature_young_m - 0.0006 * (age_years - 30.0), 4)


TEMPLATES: Dict[str, CharacterTemplate] = {
    "human_male_adult": CharacterTemplate(
        template_id="human_male_adult", label="Human — adult male (1.80 m)",
        params=CharacterParameters(stature_m=1.80, sex=Sex.MALE, age_years=30),
        stature_provenance=ProvenanceState.USER_INPUT, proportion_provenance=ProvenanceState.PROVEN,
        source_id="DRILLIS_CONTINI_1966",
        notes="Canonical base (DECISION_LOG §15). Proportions from adult males 20-40 y."),
    "human_female_adult": CharacterTemplate(
        template_id="human_female_adult", label="Human — adult female (1.65 m default)",
        params=CharacterParameters(stature_m=1.65, sex=Sex.FEMALE, age_years=30, osteometric_population="female_white"),
        stature_provenance=ProvenanceState.USER_INPUT, proportion_provenance=ProvenanceState.ESTIMATE,
        source_id="DRILLIS_CONTINI_1966",
        notes="Default stature 1.65 m is a project default (USER_INPUT), not a population statistic. "
              "Segment ratios are the male Drillis & Contini set applied to a female stature (ESTIMATE); "
              "female-specific ratios pending (ANSUR II / NHANES). Long-bone *mesh* extents use Trotter & "
              "Gleser 1952 female white equations (PROVEN) via osteometric_population=female_white."),
    "human_child_5y": CharacterTemplate(
        template_id="human_child_5y", label="Human — child ~5 y (1.10 m)",
        params=CharacterParameters(stature_m=1.10, sex=Sex.UNSPECIFIED, age_years=5),
        stature_provenance=ProvenanceState.ESTIMATE, proportion_provenance=ProvenanceState.PLACEHOLDER,
        source_id="WHO_GROWTH_STANDARDS_2006",
        notes="Stature ≈ WHO height-for-age median at 5 y (≈110 cm; value to be verified against the WHO table). "
              "Child proportions (larger head, shorter limbs) are NOT modelled: adult ratios are used as a "
              "PLACEHOLDER until Snyder (1977) / WHO segment data are acquired."),
    "human_child_10y": CharacterTemplate(
        template_id="human_child_10y", label="Human — child ~10 y (1.38 m)",
        params=CharacterParameters(stature_m=1.38, sex=Sex.UNSPECIFIED, age_years=10),
        stature_provenance=ProvenanceState.ESTIMATE, proportion_provenance=ProvenanceState.PLACEHOLDER,
        source_id="WHO_GROWTH_REFERENCE_2007",
        notes="Stature ≈ WHO 2007 median at 10 y (≈138 cm; to be verified). Adult ratios as PLACEHOLDER."),
    "human_male_elderly_75y": CharacterTemplate(
        template_id="human_male_elderly_75y", label="Human — elderly male 75 y",
        params=CharacterParameters(stature_m=_stature_after_ageing(1.80, 75), sex=Sex.MALE, age_years=75),
        stature_provenance=ProvenanceState.DERIVED, proportion_provenance=ProvenanceState.ESTIMATE,
        source_id="TROTTER_GLESER_1951",
        notes="Stature = 1.80 m − 0.06 cm/year after 30 (Trotter & Gleser 1951 ageing correction). "
              "Postural changes (kyphosis, hip/knee flexion) are not modelled."),
    "horse_adult": CharacterTemplate(
        template_id="horse_adult", label="Horse — adult (NO DATA YET)",
        params=CharacterParameters(stature_m=1.60, sex=Sex.UNSPECIFIED, age_years=8, species=Species.HORSE, pose="anatomical"),
        stature_provenance=ProvenanceState.PLACEHOLDER, proportion_provenance=ProvenanceState.UNKNOWN,
        source_id="", available=False,
        notes="No canonical equine skeleton exists in the repository. Requires an osteology source "
              "(e.g. Budras et al., Anatomy of the Horse) before any bone can be placed. Template kept so "
              "tooling (schema, exporter, validators) is species-agnostic. Withers height 1.60 m is a placeholder."),
    "dog_adult": CharacterTemplate(
        template_id="dog_adult", label="Dog — adult (NO DATA YET)",
        params=CharacterParameters(stature_m=0.60, sex=Sex.UNSPECIFIED, age_years=4, species=Species.DOG, pose="anatomical"),
        stature_provenance=ProvenanceState.PLACEHOLDER, proportion_provenance=ProvenanceState.UNKNOWN,
        source_id="", available=False,
        notes="No canonical canine skeleton in the repository (requires Evans & de Lahunta, Miller's Anatomy of the Dog)."),
}


def get_template(template_id: str) -> CharacterTemplate:
    try:
        return TEMPLATES[template_id]
    except KeyError as exc:
        raise KeyError(f"unknown template '{template_id}'; known: {sorted(TEMPLATES)}") from exc


def default_canonical_json() -> Path:
    # templates.py -> character -> domain -> character_engine
    return Path(__file__).resolve().parents[2] / "data" / "anatomy" / "human_adult_206.json"


def load_canonical_bones(json_path: Optional[Path] = None) -> Tuple[List[dict], List[dict]]:
    data = json.loads(Path(json_path or default_canonical_json()).read_text(encoding="utf-8"))
    return data["bones"], data.get("containers", [])


def build_character_bones(params: CharacterParameters, canonical_bones: Optional[Sequence[dict]] = None,
                          json_path: Optional[Path] = None) -> Tuple[List[dict], dict]:
    """Canonical bones → (retargeted + posed bones, report) for the given parameters."""
    if params.species != Species.HUMAN:
        raise NotImplementedError(
            f"no canonical skeleton for species '{params.species.value}' — data required, not invented")
    bones = list(canonical_bones) if canonical_bones is not None else load_canonical_bones(json_path)[0]
    retargeted, report = retarget_stature(bones, params.stature_m, params.proportion_ratios)
    posed = apply_pose(retargeted, params.pose)
    report["pose"] = params.pose
    report["sex"] = params.sex.value
    report["age_years"] = params.age_years
    return posed, report
