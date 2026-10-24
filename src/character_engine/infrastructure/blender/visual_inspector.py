"""Visual State Inspector – Herramientas de inspección visual (wrapper sobre StateAuditor)."""

from typing import Any, Dict, List, Optional

from .state_auditor import StateAuditor, get_auditor, get_console


def report(armature_name: str = "HumanSkeleton", include_hierarchy: bool = True, include_diagnostics: bool = True) -> Dict[str, Any]:
    """Genera un reporte visual completo de la escena (usando StateAuditor)."""
    auditor = get_auditor(armature_name)
    return auditor.snapshot()

def describe_object(name: str, armature_name: str = "HumanSkeleton") -> Dict[str, Any]:
    """Describe un objeto específico en la escena."""
    auditor = get_auditor(armature_name)
    snapshot = auditor.snapshot()
    for obj in snapshot.get("objects", []):
        if obj.get("name") == name:
            return obj
    return {"error": f"Object '{name}' not found"}

def describe_bone(armature_name: str = "HumanSkeleton", bone_name: str = "FEMUR_L") -> Dict[str, Any]:
    """Describe un hueso específico en la Armature."""
    auditor = get_auditor(armature_name)
    snapshot = auditor.snapshot()
    armature_data = snapshot.get("armature", {})
    for bone in armature_data.get("bones", []):
        if bone.get("name") == bone_name:
            return bone
    return {"error": f"Bone '{bone_name}' not found"}

def find_orphan_bones(armature_name: str = "HumanSkeleton") -> List[str]:
    """Encuentra huesos huérfanos (sin padre) en la Armature."""
    diff_data = get_auditor(armature_name).diff()
    return diff_data.get("orphans", [])

def inspect_mesh(mesh_name: str, armature_name: str = "HumanSkeleton") -> Dict[str, Any]:
    """Inspecciona una malla en la escena."""
    auditor = get_auditor(armature_name)
    snapshot = auditor.snapshot()
    for obj in snapshot.get("objects", []):
        if obj.get("name") == mesh_name and obj.get("type") == "MESH":
            return {
                "name": mesh_name,
                "vertex_count": len(obj.get("data", {}).get("vertices", [])) if "data" in obj else 0,
                "edge_count": len(obj.get("data", {}).get("edges", [])) if "data" in obj else 0,
                "face_count": len(obj.get("data", {}).get("polygons", [])) if "data" in obj else 0,
                "modifiers": obj.get("modifiers", []),
                "diagnostic": "OK" if obj.get("face_count", 0) > 0 else "CE-BL-015: Mesh has no faces",
            }
    return {"error": f"Mesh '{mesh_name}' not found"}

# Alias para mantener compatibilidad
inspect_scene = report
