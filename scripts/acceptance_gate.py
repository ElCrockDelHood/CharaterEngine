#!/usr/bin/env python
"""Acceptance Gate del Sprint 2 – Verifica todos los invariantes."""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from character_engine.domain.anatomy.osteology import SkeletonBuilder, SkeletonValidator
from character_engine.domain.anatomy.osteology.exceptions import CyclicHierarchyError
from character_engine.domain.anatomy.templates.human import HumanTemplate


def run_gate():
    print("=" * 60)
    print("  S2 ACCEPTANCE GATE")
    print("=" * 60)
    print()

    # 1. Cargar HumanTemplate
    print("[1] Cargando HumanTemplate...")
    try:
        spec = HumanTemplate.get_skeleton_spec()
    except FileNotFoundError as e:
        print(f"    ❌ ERROR: {e}")
        print("    Ejecute: python scripts/generate_human_template.py")
        return 1
    bones = spec.get("bones", [])
    containers = spec.get("containers", [])
    print(f"    Huesos en especificación: {len(bones)}")
    print(f"    Contenedores: {len(containers)}")
    if len(bones) != 206:
        print(f"    ❌ ERROR: se esperaban 206 huesos, se obtuvieron {len(bones)}")
        return 1
    print("    ✅ OK")

    # 2. Verificar nombres canónicos únicos
    print("[2] Verificando nombres canónicos únicos...")
    all_names = [b["canonical_name"] for b in bones] + [c["canonical_name"] for c in containers]
    if len(all_names) != len(set(all_names)):
        print("    ❌ ERROR: nombres canónicos duplicados")
        return 1
    print("    ✅ OK")

    # 3. Verificar contenedores obligatorios
    print("[3] Verificando contenedores obligatorios...")
    container_names = [c["canonical_name"] for c in containers]
    if "ROOT_SKELETON" not in container_names:
        print("    ❌ ERROR: falta contenedor ROOT_SKELETON")
        return 1
    if "CRANIUM" not in container_names:
        print("    ❌ ERROR: falta contenedor CRANIUM")
        return 1
    print("    ✅ OK")

    # 4. Verificar que todos los padres existen
    print("[4] Verificando padres existentes...")
    all_names_set = set(all_names)
    for item in bones + containers:
        parent = item.get("parent")
        if parent is not None and parent not in all_names_set:
            print(f"    ❌ ERROR: padre '{parent}' no existe para {item['canonical_name']}")
            return 1
    print("    ✅ OK")

    # 5. Verificar geometría (coordenadas finitas y head != tail)
    print("[5] Verificando geometría...")
    for b in bones:
        h = b.get("head", {})
        t = b.get("tail", {})
        for coord in ['x','y','z']:
            if coord not in h or coord not in t:
                print(f"    ❌ ERROR: coordenada {coord} faltante en {b['canonical_name']}")
                return 1
            if not math.isfinite(h[coord]) or not math.isfinite(t[coord]):
                print(f"    ❌ ERROR: coordenada no finita en {b['canonical_name']}")
                return 1
        if (h['x']==t['x'] and h['y']==t['y'] and h['z']==t['z']):
            print(f"    ❌ ERROR: head == tail en {b['canonical_name']}")
            return 1
    print("    ✅ OK")

    # 6. Construir Skeleton con Builder
    print("[6] Construyendo Skeleton...")
    builder = SkeletonBuilder()
    try:
        skeleton = builder.build(spec)
    except Exception as e:
        print(f"    ❌ ERROR en Builder: {e}")
        return 1
    print("    ✅ OK")

    # 7. Verificar conteo anatómico
    print("[7] Verificando conteo anatómico...")
    if skeleton.get_bone_count() != 206:
        print(f"    ❌ ERROR: se esperaban 206 huesos anatómicos, se obtuvieron {skeleton.get_bone_count()}")
        return 1
    if skeleton.get_total_nodes() != 208:  # 206 + 2 contenedores
        print(f"    ❌ ERROR: se esperaban 208 nodos totales, se obtuvieron {skeleton.get_total_nodes()}")
        return 1
    print("    ✅ OK")

    # 8. Validar con SkeletonValidator
    print("[8] Validando con SkeletonValidator...")
    validator = SkeletonValidator()
    result = validator.validate(skeleton)
    if not result.is_valid:
        print("    ❌ ERROR en validación:")
        for err in result.errors:
            print(f"        - {err}")
        return 1
    print("    ✅ OK")

    # 9. Verificar ausencia de ciclos
    print("[9] Verificando ausencia de ciclos...")
    try:
        skeleton._validate_invariants()
    except CyclicHierarchyError:
        print("    ❌ ERROR: se detectó un ciclo")
        return 1
    print("    ✅ OK")

    # 10. Verificar integridad bidireccional
    print("[10] Verificando integridad bidireccional...")
    for bone in skeleton.get_bones().values():
        for child_id in bone.child_ids:
            child = skeleton.get_bone(child_id)
            if child is None:
                print(f"    ❌ ERROR: child {child_id} de {bone.name} no existe")
                return 1
            if child.parent_id != bone.id:
                print(f"    ❌ ERROR: child {child.name} tiene parent_id {child.parent_id}, pero está en child_ids de {bone.name}")
                return 1
    print("    ✅ OK")

    # 11. Verificar arquitectura: sin bpy en sys.modules
    print("[11] Verificando arquitectura (sin bpy)...")
    import sys
    for modname in sys.modules:
        if modname.startswith("character_engine.domain.anatomy.osteology"):
            if "bpy" in sys.modules:
                print("    ❌ ERROR: bpy importado en osteology")
                return 1
    print("    ✅ OK")

    print()
    print("=" * 60)
    print("  ✅ S2 GATE APROBADO – TODOS LOS INVARIANTES VERIFICADOS")
    print("=" * 60)
    return 0

if __name__ == "__main__":
    sys.exit(run_gate())
