"""Tests de aceptación para el Bloque 8.0 – Contrato de Integración."""

from pathlib import Path

import pytest

from character_engine.domain.anatomy.osteology.builder import SkeletonBuilder
from character_engine.loader import JsonLoader


class TestB8Integration:
    @pytest.fixture
    def json_path(self):
        return Path(__file__).parent.parent.parent / "src" / "character_engine" / "data" / "anatomy" / "human_adult_206.json"

    def test_loader_loads_canonical_json(self, json_path):
        """B8.0.1: El Loader debe cargar el JSON canónico sin errores."""
        loader = JsonLoader()
        asset, skeleton_dto = loader.load_to_dto(json_path)

        # Verificar AssetDTO
        assert asset.id == "human_adult_206"
        assert asset.name == "Human Skeleton"
        assert asset.units == "meters"
        assert asset.coordinate_system == "right-handed"

        # Verificar SkeletonDTO
        assert skeleton_dto.canonical_name == "HUMAN_SKELETON"
        assert skeleton_dto.name == "Human Skeleton"

        # Verificar cantidad de huesos y contenedores
        assert len(skeleton_dto.bones) == 206
        assert len(skeleton_dto.containers) == 2

    def test_loader_dto_to_builder_reconstructs_skeleton(self, json_path):
        """B8.0.2: El DTO debe poder reconstruir el Skeleton mediante Builder."""
        loader = JsonLoader()
        _, skeleton_dto = loader.load_to_dto(json_path)

        # Convertir DTO a especificación para Builder
        spec = {
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

        builder = SkeletonBuilder()
        skeleton = builder.build(spec)

        # Verificar invariantes
        assert skeleton.get_bone_count() == 206
        assert skeleton.get_total_nodes() == 208  # 206 + 2 contenedores
        assert len(skeleton.get_roots()) == 1

    def test_loader_validates_schema(self, json_path):
        """B8.0.3: El Loader debe validar el schema correctamente (sin errores)."""
        loader = JsonLoader()
        try:
            asset, skeleton_dto = loader.load_to_dto(json_path)
            assert True
        except Exception as e:
            pytest.fail(f"El loader falló al validar el schema: {e}")

    def test_loader_asset_not_lost(self, json_path):
        """B8.0.4: Los datos de Asset no deben perderse durante la carga."""
        loader = JsonLoader()
        asset, _ = loader.load_to_dto(json_path)

        assert asset.id is not None
        assert asset.name is not None
        assert asset.version is not None
        assert asset.units is not None
        assert asset.coordinate_system is not None
