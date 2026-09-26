"""Pipeline de orquestación del flujo de integración.

Coordina las etapas: Loader → Builder → Serializer → BlenderImporter.
"""

from pathlib import Path
from typing import Optional, Tuple, Dict, Any

from ..loader import JsonLoader
from ..dto import AssetDTO, SkeletonDTO
from ..domain.anatomy.osteology.builder import SkeletonBuilder
from ..domain.anatomy.osteology.skeleton import Skeleton
from ..domain.anatomy.osteology.validator import SkeletonValidator
from ..serialization import SkeletonSerializer


class Pipeline:
    """Orquesta el flujo completo desde JSON hasta Blender (sin Blender por ahora)."""

    def __init__(self, json_path: Path, output_dir: Optional[Path] = None):
        self.json_path = json_path
        self.output_dir = output_dir or Path("builds/exports")
        self.loader = JsonLoader()
        self.builder = SkeletonBuilder()
        self.serializer = SkeletonSerializer()
        self.validator = SkeletonValidator()

    def run(self) -> Tuple[AssetDTO, SkeletonDTO, Skeleton, Dict[str, Any]]:
        """Ejecuta el pipeline y devuelve los datos de cada etapa.

        Returns:
            Tuple[AssetDTO, SkeletonDTO, Skeleton, dict]:
                - AssetDTO del JSON original
                - SkeletonDTO construido
                - Skeleton reconstruido (dominio)
                - JSON serializado (dict)
        """
        # 1. Carga
        asset_dto, skeleton_dto = self.loader.load_to_dto(self.json_path)

        # 2. Construcción del Skeleton
        spec = self._dto_to_spec(skeleton_dto)
        skeleton = self.builder.build(spec)

        # 3. Validación del Skeleton
        result = self.validator.validate(skeleton)
        if not result.is_valid:
            raise ValueError(f"Validación del Skeleton falló: {result.errors}")

        # 4. Serialización (para verificar round-trip)
        serialized = self.serializer.serialize(skeleton)

        # 5. Guardar el JSON serializado en output_dir
        output_path = self.output_dir / "skeleton_serialized.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            import json
            json.dump(serialized, f, indent=2, ensure_ascii=False)
            f.write("\n")

        return asset_dto, skeleton_dto, skeleton, serialized

    def _dto_to_spec(self, skeleton_dto: SkeletonDTO) -> Dict[str, Any]:
        """Convierte SkeletonDTO a la especificación que espera SkeletonBuilder."""
        return {
            "name": skeleton_dto.name,
            "canonical_name": skeleton_dto.canonical_name,
            "metadata": skeleton_dto.metadata,
            "bones": [
                {
                    "canonical_name": b.canonical_name,
                    "name": b.name,
                    "parent": b.parent,
                    "head": b.head,
                    "tail": b.tail
                }
                for b in skeleton_dto.bones
            ],
            "containers": [
                {
                    "canonical_name": c.canonical_name,
                    "name": c.name,
                    "parent": c.parent
                }
                for c in skeleton_dto.containers
            ]
        }