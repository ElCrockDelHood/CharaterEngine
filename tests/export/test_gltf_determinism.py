"""The canonical GLB must be byte-identical on every export.

Bones get random ``uuid4`` ids and ``Bone.child_ids`` is a ``frozenset``, so any exporter code
that iterates those sets can change float summation order (container centroids) between runs.
These tests rebuild the skeleton from scratch each time (fresh UUIDs) and also export in separate
interpreters with different ``PYTHONHASHSEED`` values.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

from character_engine.export.gltf import GltfSkeletonExporter, load_canonical_skeleton

SRC = Path(__file__).resolve().parents[2] / "src"
RUNS = 5


@pytest.mark.parametrize("pose", ["anatomical", "tpose"])
def test_fresh_skeletons_export_identical_bytes(pose):
    docs = [GltfSkeletonExporter().build(load_canonical_skeleton(pose=pose)) for _ in range(RUNS)]
    assert all(d.json == docs[0].json for d in docs)
    assert all(d.binary == docs[0].binary for d in docs)


@pytest.mark.slow
def test_glb_identical_across_processes_and_hash_seeds(tmp_path):
    code = (
        "import sys; from character_engine.export.gltf import export_canonical_skeleton as e; "
        "e(sys.argv[1], pose='anatomical'); e(sys.argv[2], pose='tpose')"
    )
    outputs = []
    for seed in range(RUNS):
        anat, tpose = tmp_path / f"anat_{seed}.glb", tmp_path / f"tpose_{seed}.glb"
        env = {**os.environ, "PYTHONHASHSEED": str(seed * 7919), "PYTHONPATH": str(SRC),
               "PYTHONDONTWRITEBYTECODE": "1"}
        subprocess.run([sys.executable, "-c", code, str(anat), str(tpose)], check=True, env=env, timeout=120)
        outputs.append((anat.read_bytes(), tpose.read_bytes()))
    assert all(o == outputs[0] for o in outputs[1:])
