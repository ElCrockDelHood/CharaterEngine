"""Validación headless de Blender usando el State Auditor (R1.3)."""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
src_path = project_root / 'src'
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

import bpy

from character_engine.domain.anatomy.osteology.builder import SkeletonBuilder
from character_engine.domain.anatomy.osteology.validator import SkeletonValidator
from character_engine.infrastructure.blender import BlenderImporter
from character_engine.infrastructure.blender.state_auditor import StateAuditor
from character_engine.loader import JsonLoader

print("=" * 60)
print("VALIDACIÓN HEADLESS DE BLENDER")
print("=" * 60)

# 1. Cargar JSON
json_path = project_root / 'src' / 'character_engine' / 'data' / 'anatomy' / 'human_adult_206.json'
if not json_path.exists():
    print("ERROR: JSON no encontrado")
    sys.exit(1)

loader = JsonLoader()
_, skeleton_dto = loader.load_to_dto(json_path)

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

# 3. Validar Skeleton
validator = SkeletonValidator()
result = validator.validate(skeleton)
if not result.is_valid:
    print("ERROR: Validación del Skeleton falló:", result.errors)
    sys.exit(1)
print("✅ Skeleton válido.")

# 4. Importar a Blender
importer = BlenderImporter()
success = importer.import_from_skeleton(skeleton)
if not success:
    print("ERROR: falló la importación")
    sys.exit(1)
print("✅ Armature importada.")

# 5. VERIFICACIÓN EXPLÍCITA DEL CONTEO (antes del auditor)
print("")
print("=" * 60)
print("VERIFICACIÓN DE IMPORTER")
print("=" * 60)

armature_obj = bpy.data.objects.get(skeleton.name)
if armature_obj is None:
    print("ERROR: Armature no encontrada después de la importación")
    sys.exit(1)

bone_count = len(armature_obj.data.bones)
expected_total = 208
print(f"  Huesos en Armature: {bone_count}")
print(f"  Esperados: {expected_total}")
if bone_count != expected_total:
    print(f"❌ ERROR: Se esperaban {expected_total} huesos, se encontraron {bone_count}")
    sys.exit(1)
print("✅ Conteo de huesos correcto (208)")

# 6. Guardar validation.blend
validation_path = project_root / 'builds' / 'tests' / 'validation.blend'
validation_path.parent.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(validation_path))
print(f"✅ validation.blend guardado en: {validation_path}")

# 7. Ejecutar State Auditor
print("")
print("=" * 60)
print("STATE AUDITOR")
print("=" * 60)

auditor = StateAuditor(skeleton.name)
status_result = auditor.status()
diff_result = auditor.diff()

print(f"  Global Status: {status_result['status']}")

if status_result["errors"]:
    print("  Errors:")
    for err in status_result["errors"]:
        print(f"    ❌ {err}")

if status_result["warnings"]:
    print("  Warnings:")
    for warn in status_result["warnings"]:
        print(f"    ⚠️ {warn}")

print("")
print(f"  Diff Status: {diff_result['status']}")

for key in ["missing", "extra", "orphans", "parent_mismatches", "geometry_mismatches", "zero_length"]:
    items = diff_result.get(key, [])
    if items:
        print(f"    {key}: {len(items)}")

print("")
print("=" * 60)

if status_result["status"] in ("PASS", "WARN") and diff_result["status"] == "PASS":
    print("✅ VALIDACIÓN HEADLESS COMPLETADA CON ÉXITO")
    print("VALIDATION_STATUS=PASS")
    sys.exit(0)
else:
    print("❌ VALIDACIÓN HEADLESS FALLIDA")
    print("VALIDATION_STATUS=FAIL")
    sys.exit(1)
