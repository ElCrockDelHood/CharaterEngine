"""Export the canonical skeleton to glTF for Godot / UPBGE.

    python scripts/export_gltf.py                                 # builds/gltf/human_adult_206.glb
    python scripts/export_gltf.py -o runtime/godot/human_adult_206.glb
    python scripts/export_gltf.py --no-mesh -o out.gltf           # joints + skin only, text glTF

Thin wrapper over ``character_engine.export.gltf.main`` so it works without
installing the package.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from character_engine.export.gltf import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
