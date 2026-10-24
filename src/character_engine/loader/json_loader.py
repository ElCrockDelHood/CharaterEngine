"""Cargador de JSON a DTO con validación de schema."""

import json
from pathlib import Path
from typing import Any, Dict, Tuple

from ..dto import AssetDTO, BoneDTO, ContainerDTO, SkeletonDTO


class JsonLoader:
    """Carga el JSON canónico, lo valida contra el schema y lo convierte a DTO."""

    def __init__(self, schema_path: Path = None):
        if schema_path is None:
            schema_path = Path(__file__).parent.parent / "schema" / "skeleton_v1.schema.json"
        self.schema_path = schema_path
        self._schema_data = None

    def load_to_dto(self, json_path: Path) -> Tuple[AssetDTO, SkeletonDTO]:
        """Carga un archivo JSON y devuelve AssetDTO y SkeletonDTO.

        Args:
            json_path: Ruta al archivo JSON.

        Returns:
            Tuple[AssetDTO, SkeletonDTO]: Datos del asset y del esqueleto.

        Raises:
            FileNotFoundError: Si el archivo no existe.
            ValueError: Si el JSON no cumple el schema o falta información.
        """
        if not json_path.exists():
            raise FileNotFoundError(f"Archivo no encontrado: {json_path}")

        with open(json_path, encoding="utf-8") as f:
            data = json.load(f)
        return self.load_data_to_dto(data)

    def load_data_to_dto(self, data: Dict[str, Any]) -> Tuple[AssetDTO, SkeletonDTO]:
        """Igual que ``load_to_dto`` pero a partir de un diccionario ya cargado.

        Permite aplicar transformaciones puras (retarget de estatura, T-pose,
        plantillas) antes de la validación de schema y la construcción de DTO.
        """
        # Normalizar: el JSON canónico actual tiene bones y containers en la raíz.
        # El schema espera asset y skeleton.
        normalized = self._normalize(data)

        # Validar contra el schema formal
        self._validate_schema(normalized)

        # Convertir a DTO
        return self._to_dto(normalized)

    def _normalize(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Convierte el JSON canónico al formato esperado por el schema."""
        # Si ya tiene la estructura esperada, devolver tal cual
        if "schema" in data and "skeleton" in data:
            return data

        # Construir la estructura esperada
        result = {
            "schema": "character_engine.skeleton",
            "schema_version": "1.0",
            "asset": {
                "id": "human_adult_206",
                "name": "Human Skeleton",
                "version": "1.0.0",
                "units": "meters",
                "coordinate_system": "right-handed"
            },
            "skeleton": {
                "canonical_name": "HUMAN_SKELETON",
                "name": "Human Skeleton",
                "bones": data.get("bones", []),
                "containers": data.get("containers", []),
                "metadata": data.get("metadata", {})
            },
            "metadata": {}
        }
        return result

    def _validate_schema(self, data: Dict[str, Any]) -> None:
        """Valida el JSON contra el schema formal."""
        try:
            import jsonschema
            if self._schema_data is None:
                with open(self.schema_path, encoding="utf-8") as f:
                    self._schema_data = json.load(f)
            jsonschema.validate(data, self._schema_data)
        except ImportError:
            # Fallback a validación manual si jsonschema no está instalado
            self._validate_manually(data)

    def _validate_manually(self, data: Dict[str, Any]) -> None:
        """Validación manual del schema (sin jsonschema)."""
        if data.get("schema") != "character_engine.skeleton":
            raise ValueError(f"Schema inválido: {data.get('schema')}")
        if data.get("schema_version") != "1.0":
            raise ValueError(f"Versión de schema no soportada: {data.get('schema_version')}")

        asset = data.get("asset")
        if not asset or "id" not in asset or "name" not in asset:
            raise ValueError("Asset incompleto: falta id o name")

        skeleton = data.get("skeleton")
        if not skeleton or "canonical_name" not in skeleton or "name" not in skeleton:
            raise ValueError("Skeleton incompleto: falta canonical_name o name")

        bones = skeleton.get("bones", [])
        for bone in bones:
            if "canonical_name" not in bone or "name" not in bone:
                raise ValueError("Hueso sin canonical_name o name")
            if "head" not in bone or "tail" not in bone:
                raise ValueError(f"Hueso {bone.get('name')} sin head o tail")
            for coord in ("x", "y", "z"):
                if coord not in bone["head"] or coord not in bone["tail"]:
                    raise ValueError(f"Coordenada {coord} faltante en {bone['canonical_name']}")

        containers = skeleton.get("containers", [])
        for container in containers:
            if "canonical_name" not in container or "name" not in container:
                raise ValueError("Contenedor sin canonical_name o name")

    def _to_dto(self, data: Dict[str, Any]) -> Tuple[AssetDTO, SkeletonDTO]:
        """Convierte el dict validado a DTO."""
        asset_data = data.get("asset", {})
        skeleton_data = data.get("skeleton", {})
        bones_data = skeleton_data.get("bones", [])
        containers_data = skeleton_data.get("containers", [])

        asset = AssetDTO(
            id=asset_data.get("id", ""),
            name=asset_data.get("name", ""),
            version=asset_data.get("version", "1.0.0"),
            units=asset_data.get("units", "meters"),
            coordinate_system=asset_data.get("coordinate_system", "right-handed"),
        )

        bones = []
        for b in bones_data:
            bones.append(BoneDTO(
                canonical_name=b["canonical_name"],
                name=b["name"],
                parent=b.get("parent"),
                head=b["head"],
                tail=b["tail"],
            ))

        containers = []
        for c in containers_data:
            containers.append(ContainerDTO(
                canonical_name=c["canonical_name"],
                name=c["name"],
                parent=c.get("parent"),
            ))

        skeleton = SkeletonDTO(
            canonical_name=skeleton_data["canonical_name"],
            name=skeleton_data["name"],
            bones=bones,
            containers=containers,
            metadata=skeleton_data.get("metadata", {}),
        )

        return asset, skeleton
