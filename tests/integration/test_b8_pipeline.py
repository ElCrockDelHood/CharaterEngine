"""Tests de integración del Pipeline."""

import pytest
from pathlib import Path
from character_engine.pipeline import Pipeline


class TestB8Pipeline:
    @pytest.fixture
    def json_path(self):
        return Path(__file__).parent.parent.parent / "src" / "character_engine" / "data" / "anatomy" / "human_adult_206.json"

    def test_pipeline_runs_successfully(self, json_path):
        """B8.5.1: El Pipeline debe ejecutar todas las etapas sin errores."""
        pipeline = Pipeline(json_path)
        asset_dto, skeleton_dto, skeleton, serialized = pipeline.run()

        # Verificar que se haya generado el Skeleton
        assert skeleton.get_bone_count() == 206
        assert skeleton.get_total_nodes() == 208

        # Verificar que el serializado tenga los datos esperados
        assert "schema" in serialized
        assert serialized["schema"] == "character_engine.skeleton"
        assert len(serialized["skeleton"]["bones"]) == 206
        assert len(serialized["skeleton"]["containers"]) == 2

        # Verificar que el output_dir existe y contiene el archivo serializado
        assert (pipeline.output_dir / "skeleton_serialized.json").exists()

    def test_pipeline_validates_skeleton(self, json_path):
        """B8.5.2: El Pipeline debe validar el Skeleton antes de serializar."""
        pipeline = Pipeline(json_path)
        asset_dto, skeleton_dto, skeleton, serialized = pipeline.run()

        # La validación ya está dentro del Pipeline; si llegamos aquí, pasó.
        # Añadimos un cheque explícito para asegurar que el Skeleton es válido.
        from character_engine.domain.anatomy.osteology.validator import SkeletonValidator
        validator = SkeletonValidator()
        result = validator.validate(skeleton)
        assert result.is_valid

    def test_pipeline_preserves_round_trip(self, json_path):
        """B8.5.3: El Pipeline debe preservar el round-trip (JSON → Skeleton → JSON)."""
        pipeline = Pipeline(json_path)
        asset_dto, skeleton_dto, skeleton, serialized = pipeline.run()

        # Cargar el JSON serializado y comparar con el original
        from character_engine.loader import JsonLoader
        loader = JsonLoader()
        serialized_path = pipeline.output_dir / "skeleton_serialized.json"
        asset2, skeleton_dto2 = loader.load_to_dto(serialized_path)

        # Comparar cantidades
        assert len(skeleton_dto2.bones) == len(skeleton_dto.bones)
        assert len(skeleton_dto2.containers) == len(skeleton_dto.containers)

        # Comparar algunos huesos clave (primero y último)
        if skeleton_dto2.bones:
            assert skeleton_dto2.bones[0].canonical_name == skeleton_dto.bones[0].canonical_name
            assert skeleton_dto2.bones[-1].canonical_name == skeleton_dto.bones[-1].canonical_name