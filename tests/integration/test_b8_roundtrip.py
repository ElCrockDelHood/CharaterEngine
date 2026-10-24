"""Tests de ida y vuelta exhaustivos para el Serializer."""

import json
from pathlib import Path

import pytest

from character_engine.domain.anatomy.osteology.builder import SkeletonBuilder
from character_engine.loader import JsonLoader
from character_engine.serialization import SkeletonSerializer


class TestB8RoundTripComplete:
    @pytest.fixture
    def json_path(self):
        return Path(__file__).parent.parent.parent / "src" / "character_engine" / "data" / "anatomy" / "human_adult_206.json"

    def test_round_trip_full(self, json_path):
        """B8.4.1: Round-trip completo: JSON → Skeleton → JSON → Skeleton con comparación exhaustiva."""
        # 1. Cargar JSON original
        loader = JsonLoader()
        asset, skeleton_dto = loader.load_to_dto(json_path)

        # 2. Reconstruir Skeleton
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

        # 3. Serializar a JSON
        serializer = SkeletonSerializer(asset_id=asset.id, asset_name=asset.name)
        serialized = serializer.serialize(skeleton)

        # 4. Cargar el JSON serializado (usando el loader)
        # Guardar temporalmente el serializado en un archivo para que el loader lo lea
        tmp_path = Path("temp_roundtrip.json")
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(serialized, f, indent=2, ensure_ascii=False)
        try:
            asset2, skeleton_dto2 = loader.load_to_dto(tmp_path)
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

        # 5. Comparar exhaustivamente
        # 5.1 Asset
        assert asset2.id == asset.id
        assert asset2.name == asset.name
        assert asset2.version == asset.version
        assert asset2.units == asset.units
        assert asset2.coordinate_system == asset.coordinate_system

        # 5.2 Cantidades
        assert len(skeleton_dto2.bones) == len(skeleton_dto.bones)
        assert len(skeleton_dto2.containers) == len(skeleton_dto.containers)

        # 5.3 Comparar cada hueso
        for i, (b_orig, b_new) in enumerate(zip(skeleton_dto.bones, skeleton_dto2.bones)):
            assert b_new.canonical_name == b_orig.canonical_name, f"Hueso {i}: canonical_name"
            assert b_new.name == b_orig.name, f"Hueso {i}: name"
            assert b_new.parent == b_orig.parent, f"Hueso {i}: parent"
            assert b_new.head == b_orig.head, f"Hueso {i}: head"
            assert b_new.tail == b_orig.tail, f"Hueso {i}: tail"

        # 5.4 Comparar cada contenedor
        for i, (c_orig, c_new) in enumerate(zip(skeleton_dto.containers, skeleton_dto2.containers)):
            assert c_new.canonical_name == c_orig.canonical_name, f"Contenedor {i}: canonical_name"
            assert c_new.name == c_orig.name, f"Contenedor {i}: name"
            assert c_new.parent == c_orig.parent, f"Contenedor {i}: parent"

    def test_order_preserved(self, json_path):
        """B8.4.2: El orden canónico de huesos y contenedores se preserva."""
        loader = JsonLoader()
        asset, skeleton_dto = loader.load_to_dto(json_path)

        # Reconstruir Skeleton
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

        serializer = SkeletonSerializer(asset_id=asset.id, asset_name=asset.name)
        serialized = serializer.serialize(skeleton)

        bones_serialized = [b["canonical_name"] for b in serialized["skeleton"]["bones"]]
        bones_original = [b.canonical_name for b in skeleton_dto.bones]
        assert bones_serialized == bones_original, "El orden de los huesos ha cambiado"

        containers_serialized = [c["canonical_name"] for c in serialized["skeleton"]["containers"]]
        containers_original = [c.canonical_name for c in skeleton_dto.containers]
        assert containers_serialized == containers_original, "El orden de los contenedores ha cambiado"

    def test_schema_valid(self, json_path):
        """B8.4.3: El JSON generado cumple el schema v1.0."""
        loader = JsonLoader()
        asset, skeleton_dto = loader.load_to_dto(json_path)

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

        serializer = SkeletonSerializer(asset_id=asset.id, asset_name=asset.name)
        serialized = serializer.serialize(skeleton)

        # Validar con el loader (que usa jsonschema o validación manual)
        loader2 = JsonLoader()
        normalized = loader2._normalize(serialized)
        try:
            loader2._validate_schema(normalized)
            valid = True
        except Exception as e:
            valid = False
            print(f"Error de validación: {e}")
        assert valid, "El JSON serializado no cumple el schema v1.0"
