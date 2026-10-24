"""HumanTemplate – carga la lista canónica de 206 huesos desde JSON."""

import json
from pathlib import Path
from typing import Any, Dict


class HumanTemplate:
    """Plantilla del esqueleto humano – 206 huesos anatómicos canónicos."""

    @staticmethod
    def get_skeleton_spec() -> Dict[str, Any]:
        json_path = Path(__file__).parent.parent.parent.parent / "data" / "anatomy" / "human_adult_206.json"
        if not json_path.exists():
            raise FileNotFoundError(
                f"Human skeleton template not found at: {json_path}\n"
                "Please run: python scripts/generate_human_template.py"
            )
        with open(json_path, encoding='utf-8') as f:
            data = json.load(f)
        return {
            "name": "HumanSkeleton",
            "canonical_name": "HUMAN_SKELETON",
            "version": "1.0.0",
            "metadata": {
                "species": "Homo sapiens",
                "age": "adult",
                "bone_count": len(data.get("bones", [])),
                "source": "Character Engine HumanTemplateV1"
            },
            "bones": data.get("bones", []),
            "containers": data.get("containers", [])
        }
