---
name: export-gltf
description: Export the canonical 206-bone skeleton to glTF 2.0 (.glb) with Z-up to Y-up conversion and inspect the result. Use when the user asks to export the skeleton, generate a GLB, prepare assets for Godot/UPBGE, or debug glTF output.
---

# Export glTF

## Run

```bash
$PY scripts/export_gltf.py                                   # -> builds/gltf/human_adult_206.glb
$PY -m character_engine.export.gltf -o builds/gltf/out.glb   # same, explicit output
$PY -m character_engine.export.gltf -i path/to/skeleton.json # custom canonical JSON
$PY -m character_engine.export.gltf --no-mesh                # skeleton only (no octahedral bone mesh)
$PY -m character_engine.export.gltf --keep-z-up              # DEBUG ONLY: skip Y-up conversion
```

Output is git-ignored (`builds/gltf/`). Never commit `.glb` files.

## What the exporter guarantees (`src/character_engine/export/gltf.py`)

- 208 nodes (206 bones + `ROOT_SKELETON` + `CRANIUM`), names = `canonical_name`.
- Node translation = local head offset; canonical `(x, y, z)` → glTF `(x, z, -y)`.
- One `skin` with `inverseBindMatrices` (translation-only), `JOINTS_0`/`WEIGHTS_0` on the display mesh.
- `extras`: `ce_tail` (glTF-frame tail), `ce_canonical_name`, `ce_is_container`,
  `ce_provenance`; asset `extras.ce_coordinate_system` documents the source frame.
- Pure stdlib (`struct`, `json`, `math`) — no numpy, no pygltflib.

## Inspect without an engine

```bash
$PY - <<'EOF'
import json, struct
b = open("builds/gltf/human_adult_206.glb","rb").read()
ln = struct.unpack_from("<I", b, 12)[0]
g = json.loads(b[20:20+ln])
print(len(g["nodes"]), "nodes;", len(g["skins"][0]["joints"]), "joints")
print([n["name"] for n in g["nodes"][:5]])
EOF
```

## Validate in engines

- Godot: see the `validate-godot` skill.
- UPBGE/Blender headless: see the `validate-upbge` skill.
- Tests: `$PY -m pytest tests/export -q` (23 tests cover structure, alignment, conversion).
