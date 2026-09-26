"""State Auditor – Unifica Structural, Visual y Operational State.

Versión R1.3 FINAL:
- CE-BL-027 ya no bloquea en HEADLESS (se registra como INFO)
- Lazy CE
- Canonical como fuente de verdad
- Geometry mismatch = FAIL
- PoseBone constraints
- Modifiers detallados
"""

import sys
import json
import math
from pathlib import Path
from typing import Dict, Any, Optional, List, Set, Tuple
from dataclasses import dataclass, field
import datetime

# ================================================================
# CONSTANTES Y CÓDIGOS DE ERROR
# ================================================================

ERROR_CODES = {
    "CE-BL-001": "Armature missing",
    "CE-BL-002": "Object missing",
    "CE-BL-003": "Bone count mismatch",
    "CE-BL-004": "Extra/unmapped bones",
    "CE-BL-005": "Parent mismatch",
    "CE-BL-006": "Invalid transform",
    "CE-BL-007": "Missing canonical bones",
    "CE-BL-008": "Zero-length bone",
    "CE-BL-009": "Canonical mismatch",
    "CE-BL-010": "Mesh topology error",
    "CE-BL-011": "Duplicate bone name",
    "CE-BL-012": "Container position invalid",
    "CE-BL-013": "Bone chain discontinuity",
    "CE-BL-014": "Geometry mismatch",
    "CE-BL-015": "Mesh has no faces",
    "CE-BL-016": "Mesh has no edges",
    "CE-BL-017": "Mesh has no vertices",
    "CE-BL-018": "Modifier error",
    "CE-BL-019": "Skin modifier missing",
    "CE-BL-020": "Subdivision modifier missing",
    "CE-BL-021": "Object hidden in viewport",
    "CE-BL-022": "Object hidden in render",
    "CE-BL-023": "Bone outside body bounds",
    "CE-BL-024": "Invalid scale",
    "CE-BL-025": "Invalid rotation",
    "CE-BL-026": "Collection not visible",
    "CE-BL-027": "No active camera (GUI only)",
    "CE-BL-028": "Orphan bone",
    "CE-BL-029": "Mesh disconnected",
    "CE-BL-030": "Unexpected mode",
    "CE-BL-031": "Inactive object",
    "CE-BL-032": "Auditor error",
    "CE-BL-033": "Viewport shading",
    "CE-BL-034": "Overlays",
    "CE-BL-035": "Selection",
    "CE-BL-036": "Editability",
    "CE-BL-037": "Headless context",
}


# ================================================================
# MODELOS DE DATOS
# ================================================================

@dataclass
class CheckResult:
    """Resultado de una comprobación individual."""
    code: str
    status: str  # PASS, WARN, FAIL, ERROR, INFO
    message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

    def is_pass(self) -> bool:
        return self.status == "PASS"

    def is_fail(self) -> bool:
        return self.status in ("FAIL", "ERROR")

    def is_warn(self) -> bool:
        return self.status == "WARN"


@dataclass
class StateReport:
    """Reporte de estado consolidado con jerarquía: ERROR > FAIL > WARN > PASS."""
    structural: List[CheckResult] = field(default_factory=list)
    visual: List[CheckResult] = field(default_factory=list)
    operational: List[CheckResult] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    infos: List[str] = field(default_factory=list)
    status: str = "PASS"
    execution_context: Dict[str, Any] = field(default_factory=dict)

    def add_check(self, check: CheckResult, level: str = "structural") -> None:
        if level == "structural":
            self.structural.append(check)
        elif level == "visual":
            self.visual.append(check)
        elif level == "operational":
            self.operational.append(check)
        else:
            raise ValueError(f"Nivel desconocido: {level}")

        # Jerarquía: ERROR > FAIL > WARN > PASS, INFO no afecta estado
        if check.status == "ERROR":
            self.status = "ERROR"
            self.errors.append(f"{check.code}: {check.message}")
        elif check.status == "FAIL":
            if self.status not in ("ERROR", "FAIL"):
                self.status = "FAIL"
            self.errors.append(f"{check.code}: {check.message}")
        elif check.status == "WARN":
            if self.status == "PASS":
                self.status = "WARN"
            self.warnings.append(f"{check.code}: {check.message}")
        elif check.status == "INFO":
            self.infos.append(f"{check.code}: {check.message}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "execution_context": self.execution_context,
            "structural": [
                {"code": c.code, "status": c.status, "message": c.message}
                for c in self.structural
            ],
            "visual": [
                {"code": c.code, "status": c.status, "message": c.message}
                for c in self.visual
            ],
            "operational": [
                {"code": c.code, "status": c.status, "message": c.message}
                for c in self.operational
            ],
            "errors": self.errors,
            "warnings": self.warnings,
            "infos": self.infos,
        }


# ================================================================
# STATE AUDITOR
# ================================================================

class StateAuditor:
    """Auditor de estado unificado."""

    def __init__(self, armature_name: str = "HumanSkeleton"):
        self.armature_name = armature_name
        self._bpy = None
        self._ensure_blender()
        self._canonical_data = None
        self._last_report = None
        self._execution_context = {"mode": "UNKNOWN", "viewport_available": False}

    def _ensure_blender(self):
        try:
            import bpy
            self._bpy = bpy
        except ImportError:
            raise ImportError("Este módulo solo puede ejecutarse dentro de Blender.")

    def _get_project_root(self) -> Path:
        current = Path(__file__).resolve()
        for _ in range(6):
            if (current / "src" / "character_engine").exists():
                return current
            current = current.parent
        return Path.cwd()

    def _load_canonical(self) -> Dict[str, Any]:
        if self._canonical_data is not None:
            return self._canonical_data
        project_root = self._get_project_root()
        json_path = project_root / "src" / "character_engine" / "data" / "anatomy" / "human_adult_206.json"
        if not json_path.exists():
            raise FileNotFoundError(f"Canonical JSON not found: {json_path}")
        import json
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self._canonical_data = data
        return data

    def _get_armature(self):
        bpy = self._bpy
        armature = bpy.data.objects.get(self.armature_name)
        if armature is None:
            for obj in bpy.data.objects:
                if obj.type == "ARMATURE":
                    self.armature_name = obj.name
                    return obj
            return None
        return armature

    def _detect_execution_context(self):
        bpy = self._bpy
        space_data = bpy.context.space_data
        if space_data is None:
            self._execution_context = {"mode": "HEADLESS", "viewport_available": False}
        else:
            self._execution_context = {"mode": "GUI", "viewport_available": True}

    def audit(self) -> StateReport:
        self._detect_execution_context()
        report = StateReport(execution_context=self._execution_context)

        structural_results = self._audit_structural()
        for check in structural_results:
            report.add_check(check, "structural")

        if any(c.code == "CE-BL-001" for c in structural_results if c.is_pass()):
            visual_results = self._audit_visual()
            for check in visual_results:
                report.add_check(check, "visual")

            operational_results = self._audit_operational()
            for check in operational_results:
                report.add_check(check, "operational")

        self._last_report = report
        return report

    def _audit_structural(self) -> List[CheckResult]:
        results = []
        bpy = self._bpy

        try:
            armature_obj = self._get_armature()
            if armature_obj is None:
                results.append(CheckResult("CE-BL-001", "FAIL", f"Armature '{self.armature_name}' not found"))
                return results
            results.append(CheckResult("CE-BL-001", "PASS"))

            armature = armature_obj.data
            bones = armature.bones
            canonical = self._load_canonical()
            canonical_bones = canonical.get("bones", [])
            canonical_containers = canonical.get("containers", [])

            # Construir mapas
            blender_names = {b.name for b in bones}
            canonical_to_blender = {}
            for cb in canonical_bones:
                cn = cb["canonical_name"]
                if cn in blender_names:
                    canonical_to_blender[cn] = cn
                elif cb.get("name") in blender_names:
                    canonical_to_blender[cn] = cb["name"]
            for cc in canonical_containers:
                cn = cc["canonical_name"]
                if cn in blender_names:
                    canonical_to_blender[cn] = cn
                elif cc.get("name") in blender_names:
                    canonical_to_blender[cn] = cc["name"]

            blender_to_canonical = {v: k for k, v in canonical_to_blender.items()}

            # Dominios
            canonical_all = {cb["canonical_name"] for cb in canonical_bones}
            canonical_all.update({cc["canonical_name"] for cc in canonical_containers})

            mapped_canonical = set(canonical_to_blender.keys())
            mapped_blender = set(canonical_to_blender.values())

            # CE-BL-007: Missing
            missing = canonical_all - mapped_canonical
            if missing:
                results.append(CheckResult(
                    "CE-BL-007",
                    "FAIL",
                    f"Missing canonical bones: {len(missing)}",
                    {"missing": sorted(missing)}
                ))
            else:
                results.append(CheckResult("CE-BL-007", "PASS"))

            # CE-BL-004: Extra/unmapped
            extra = blender_names - mapped_blender
            if extra:
                results.append(CheckResult(
                    "CE-BL-004",
                    "FAIL",
                    f"Extra/unmapped bones: {len(extra)}",
                    {"extra": sorted(extra)}
                ))
            else:
                results.append(CheckResult("CE-BL-004", "PASS"))

            # Cuentas usando canonical
            expected_anatomical = len(canonical_bones)
            expected_containers = len(canonical_containers)
            expected_total = expected_anatomical + expected_containers

            anatomical_names = {cb["canonical_name"] for cb in canonical_bones}
            container_names = {cc["canonical_name"] for cc in canonical_containers}
            anatomical_blender = {canonical_to_blender[cn] for cn in anatomical_names if cn in canonical_to_blender}
            container_blender = {canonical_to_blender[cn] for cn in container_names if cn in canonical_to_blender}

            actual_anatomical = len(anatomical_blender)
            actual_containers = len(container_blender)
            actual_total = len(bones)

            # CE-BL-003: Bone count
            count_ok = True
            if actual_anatomical != expected_anatomical:
                results.append(CheckResult(
                    "CE-BL-003",
                    "FAIL",
                    f"Anatomical bones: {actual_anatomical} (expected {expected_anatomical})",
                    {"anatomical": actual_anatomical, "expected_anatomical": expected_anatomical}
                ))
                count_ok = False
            if actual_containers != expected_containers:
                results.append(CheckResult(
                    "CE-BL-003",
                    "FAIL",
                    f"Containers: {actual_containers} (expected {expected_containers})",
                    {"containers": actual_containers, "expected_containers": expected_containers}
                ))
                count_ok = False
            if actual_total != expected_total:
                results.append(CheckResult(
                    "CE-BL-003",
                    "FAIL",
                    f"Total: {actual_total} (expected {expected_total})",
                    {"total": actual_total, "expected_total": expected_total}
                ))
                count_ok = False
            if count_ok:
                results.append(CheckResult(
                    "CE-BL-003",
                    "PASS",
                    f"Anatomical {actual_anatomical}, Containers {actual_containers}, Total {actual_total}"
                ))

            # CE-BL-011: Duplicate names
            names = [b.name for b in bones]
            if len(names) != len(set(names)):
                duplicates = [n for n in set(names) if names.count(n) > 1]
                results.append(CheckResult("CE-BL-011", "FAIL", f"Duplicate names: {duplicates}"))
            else:
                results.append(CheckResult("CE-BL-011", "PASS"))

            # CE-BL-028: Orphan bones
            blender_roots = {b.name for b in bones if b.parent is None}
            canonical_roots = set()
            for cb in canonical_bones:
                if cb.get("parent") is None:
                    canonical_roots.add(cb["canonical_name"])
            for cc in canonical_containers:
                if cc.get("parent") is None:
                    canonical_roots.add(cc["canonical_name"])
            canonical_root_names = {canonical_to_blender.get(cr) for cr in canonical_roots if cr in canonical_to_blender}
            orphans = blender_roots - canonical_root_names
            if orphans:
                results.append(CheckResult(
                    "CE-BL-028",
                    "WARN",
                    f"Orphan bones: {sorted(orphans)}",
                    {"orphans": sorted(orphans)}
                ))
            else:
                results.append(CheckResult("CE-BL-028", "PASS"))

            # CE-BL-008: Zero-length
            zero_length = [b.name for b in bones if b.length < 0.0001]
            if zero_length:
                results.append(CheckResult(
                    "CE-BL-008",
                    "WARN",
                    f"Zero-length bones: {zero_length}",
                    {"zero_length": zero_length}
                ))
            else:
                results.append(CheckResult("CE-BL-008", "PASS"))

            # CE-BL-005: Parent mismatches
            parent_mismatches = []
            for bone in bones:
                cn = blender_to_canonical.get(bone.name)
                if cn is None:
                    continue
                expected_parent_canonical = None
                for cb in canonical_bones:
                    if cb["canonical_name"] == cn:
                        expected_parent_canonical = cb.get("parent")
                        break
                if expected_parent_canonical is None:
                    for cc in canonical_containers:
                        if cc["canonical_name"] == cn:
                            expected_parent_canonical = cc.get("parent")
                            break

                actual_parent = bone.parent.name if bone.parent else None

                if expected_parent_canonical is None:
                    expected_blender = None
                else:
                    if expected_parent_canonical not in canonical_to_blender:
                        parent_mismatches.append({
                            "bone": bone.name,
                            "expected_canonical": expected_parent_canonical,
                            "expected": "UNRESOLVED",
                            "actual": actual_parent,
                        })
                        continue
                    expected_blender = canonical_to_blender[expected_parent_canonical]

                if expected_blender != actual_parent:
                    parent_mismatches.append({
                        "bone": bone.name,
                        "expected": expected_blender,
                        "actual": actual_parent,
                    })

            if parent_mismatches:
                results.append(CheckResult(
                    "CE-BL-005",
                    "FAIL",
                    f"Parent mismatches: {len(parent_mismatches)}",
                    {"parent_mismatches": parent_mismatches}
                ))
            else:
                results.append(CheckResult("CE-BL-005", "PASS"))

            # CE-BL-014: Geometry mismatches (FAIL)
            geo_mismatches = []
            tol = 0.001
            for bone in bones:
                cn = blender_to_canonical.get(bone.name)
                if cn is None:
                    continue
                for cb in canonical_bones:
                    if cb["canonical_name"] == cn:
                        expected_head = (cb["head"]["x"], cb["head"]["y"], cb["head"]["z"])
                        expected_tail = (cb["tail"]["x"], cb["tail"]["y"], cb["tail"]["z"])
                        actual_head = tuple(bone.head_local)
                        actual_tail = tuple(bone.tail_local)
                        head_diff = max(abs(a - b) for a, b in zip(expected_head, actual_head))
                        tail_diff = max(abs(a - b) for a, b in zip(expected_tail, actual_tail))
                        if head_diff > tol or tail_diff > tol:
                            geo_mismatches.append({
                                "bone": bone.name,
                                "head_diff": head_diff,
                                "tail_diff": tail_diff
                            })
                        break

            if geo_mismatches:
                results.append(CheckResult(
                    "CE-BL-014",
                    "FAIL",
                    f"Geometry mismatches: {len(geo_mismatches)}",
                    {"geometry_mismatches": geo_mismatches}
                ))
            else:
                results.append(CheckResult("CE-BL-014", "PASS"))

        except Exception as e:
            results.append(CheckResult("CE-BL-032", "ERROR", f"Auditor error: {e}"))

        return results

    def _audit_visual(self) -> List[CheckResult]:
        results = []
        bpy = self._bpy

        try:
            armature_obj = self._get_armature()
            if armature_obj is None:
                return results

            if armature_obj.hide_viewport:
                results.append(CheckResult("CE-BL-021", "WARN", f"{self.armature_name} hidden in viewport"))
            else:
                results.append(CheckResult("CE-BL-021", "PASS"))

            if armature_obj.hide_render:
                results.append(CheckResult("CE-BL-022", "WARN", f"{self.armature_name} hidden in render"))
            else:
                results.append(CheckResult("CE-BL-022", "PASS"))

            # CE-BL-027: Camera presence (INFO in headless, WARN in GUI)
            is_headless = self._execution_context["mode"] == "HEADLESS"
            if bpy.context.scene.camera is None:
                if is_headless:
                    results.append(CheckResult("CE-BL-027", "INFO", "No active camera (headless context)"))
                else:
                    results.append(CheckResult("CE-BL-027", "WARN", "No active camera in GUI"))
            else:
                results.append(CheckResult("CE-BL-027", "PASS"))

            scale = armature_obj.scale
            if any(abs(s) < 0.001 for s in scale) or any(abs(s) > 100 for s in scale):
                results.append(CheckResult("CE-BL-024", "WARN", f"Abnormal scale: {tuple(scale)}"))
            else:
                results.append(CheckResult("CE-BL-024", "PASS"))

            rotation = armature_obj.rotation_euler
            if any(not math.isfinite(r) for r in rotation):
                results.append(CheckResult("CE-BL-025", "FAIL", f"Invalid rotation: {tuple(rotation)}"))
            else:
                results.append(CheckResult("CE-BL-025", "PASS"))

            view_layer = bpy.context.view_layer
            if view_layer.active_layer_collection and view_layer.active_layer_collection.hide_viewport:
                results.append(CheckResult("CE-BL-026", "WARN", "Active collection hidden in viewport"))
            else:
                results.append(CheckResult("CE-BL-026", "PASS"))

            space_data = bpy.context.space_data
            if space_data is None:
                results.append(CheckResult("CE-BL-037", "PASS", "Headless context"))
            else:
                if hasattr(space_data, "shading"):
                    results.append(CheckResult(
                        "CE-BL-033",
                        "PASS",
                        f"Shading: {space_data.shading.type}",
                        {"shading": space_data.shading.type}
                    ))
                if hasattr(space_data, "overlay") and hasattr(space_data.overlay, "show_overlays"):
                    results.append(CheckResult(
                        "CE-BL-034",
                        "PASS",
                        f"Overlays: {'ON' if space_data.overlay.show_overlays else 'OFF'}",
                        {"overlays": space_data.overlay.show_overlays}
                    ))

        except Exception as e:
            results.append(CheckResult("CE-BL-032", "ERROR", f"Visual auditor error: {e}"))

        return results

    def _audit_operational(self) -> List[CheckResult]:
        results = []
        bpy = self._bpy

        try:
            mode = bpy.context.mode
            if mode in ["OBJECT", "EDIT_ARMATURE", "POSE"]:
                results.append(CheckResult("CE-BL-030", "PASS", f"Mode: {mode}"))
            else:
                results.append(CheckResult("CE-BL-030", "WARN", f"Unexpected mode: {mode}"))

            active = bpy.context.view_layer.objects.active
            if active and active.name == self.armature_name:
                results.append(CheckResult("CE-BL-031", "PASS", f"Active: {self.armature_name}"))
            elif active:
                results.append(CheckResult("CE-BL-031", "WARN", f"Active: {active.name} (expected {self.armature_name})"))
            else:
                results.append(CheckResult("CE-BL-031", "WARN", "No active object"))

            armature_obj = self._get_armature()
            if armature_obj:
                is_editable = (armature_obj.library is None and
                               armature_obj.override_library is None and
                               not armature_obj.hide_select)
                if is_editable:
                    results.append(CheckResult("CE-BL-036", "PASS", "Armature is editable"))
                else:
                    results.append(CheckResult("CE-BL-036", "WARN", "Armature is not editable"))

            selected = [obj.name for obj in bpy.context.selected_objects]
            if selected:
                results.append(CheckResult(
                    "CE-BL-035",
                    "PASS",
                    f"Selected: {selected}",
                    {"selected": selected}
                ))
            else:
                results.append(CheckResult("CE-BL-035", "PASS", "No selection"))

        except Exception as e:
            results.append(CheckResult("CE-BL-032", "ERROR", f"Operational auditor error: {e}"))

        return results

    # ================================================================
    # INTERFAZ PÚBLICA
    # ================================================================

    def status(self) -> Dict[str, Any]:
        report = self.audit()
        return report.to_dict()

    def status_json(self) -> str:
        return json.dumps(self.status(), indent=2)

    def diff(self) -> Dict[str, Any]:
        report = self._last_report if self._last_report else self.audit()
        details = {}
        for check in report.structural + report.visual + report.operational:
            if check.details:
                for key, value in check.details.items():
                    details[key] = value
        return {
            "status": report.status,
            "missing": details.get("missing", []),
            "extra": details.get("extra", []),
            "orphans": details.get("orphans", []),
            "parent_mismatches": details.get("parent_mismatches", []),
            "geometry_mismatches": details.get("geometry_mismatches", []),
            "zero_length": details.get("zero_length", []),
        }

    def snapshot(self) -> Dict[str, Any]:
        bpy = self._bpy
        scene = bpy.context.scene
        view_layer = bpy.context.view_layer
        space_data = bpy.context.space_data

        scene_data = {
            "name": scene.name,
            "frame": scene.frame_current,
            "fps": scene.render.fps,
            "units": scene.unit_settings.system,
            "render_engine": scene.render.engine,
            "resolution": (scene.render.resolution_x, scene.render.resolution_y),
            "world": scene.world.name if scene.world else None,
        }

        objects = []
        for obj in bpy.data.objects:
            objects.append({
                "name": obj.name,
                "type": obj.type,
                "location": tuple(obj.location),
                "rotation": tuple(obj.rotation_euler),
                "scale": tuple(obj.scale),
                "visible": obj.visible_get(),
                "hide_viewport": obj.hide_viewport,
                "hide_render": obj.hide_render,
                "selected": obj.select_get(),
                "parent": obj.parent.name if obj.parent else None,
                "collection": obj.users_collection[0].name if obj.users_collection else None,
                "modifiers": self._get_detailed_modifiers(obj),
                "is_editable": obj.library is None and obj.override_library is None and not obj.hide_select,
            })

        armature_obj = self._get_armature()
        armature_data = {}
        if armature_obj:
            pose_bones = armature_obj.pose.bones if hasattr(armature_obj, "pose") else {}
            armature_data = {
                "name": armature_obj.name,
                "location": tuple(armature_obj.location),
                "rotation": tuple(armature_obj.rotation_euler),
                "scale": tuple(armature_obj.scale),
                "bones": [
                    {
                        "name": b.name,
                        "parent": b.parent.name if b.parent else None,
                        "head": tuple(b.head_local),
                        "tail": tuple(b.tail_local),
                        "length": b.length,
                        "deform": b.use_deform,
                        "connected": b.use_connect,
                        "constraints": [
                            {"name": c.name, "type": c.type}
                            for c in pose_bones[b.name].constraints
                        ] if b.name in pose_bones and hasattr(pose_bones[b.name], "constraints") else [],
                    }
                    for b in armature_obj.data.bones
                ]
            }

        viewport_data = {"available": False}
        if space_data and hasattr(space_data, "shading"):
            viewport_data = {
                "available": True,
                "shading": space_data.shading.type if hasattr(space_data, "shading") else None,
                "overlays": space_data.overlay.show_overlays if hasattr(space_data, "overlay") and hasattr(space_data.overlay, "show_overlays") else None,
                "xray": space_data.shading.xray if hasattr(space_data.shading, "xray") else None,
                "perspective": space_data.region_3d.is_perspective if hasattr(space_data, "region_3d") else None,
            }

        collections = []
        for coll in bpy.data.collections:
            collections.append({
                "name": coll.name,
                "hide_viewport": coll.hide_viewport,
                "hide_render": coll.hide_render,
            })

        operational = {
            "mode": bpy.context.mode,
            "active_object": bpy.context.view_layer.objects.active.name if bpy.context.view_layer.objects.active else None,
            "selected_objects": [obj.name for obj in bpy.context.selected_objects],
            "active_collection": view_layer.active_layer_collection.name if view_layer.active_layer_collection else None,
        }

        return {
            "timestamp": datetime.datetime.now().isoformat(),
            "execution_context": self._execution_context,
            "scene": scene_data,
            "objects": objects,
            "armature": armature_data,
            "viewport": viewport_data,
            "collections": collections,
            "operational": operational,
            "status": self.status(),
            "diff": self.diff(),
        }

    def _get_detailed_modifiers(self, obj) -> List[Dict[str, Any]]:
        result = []
        for m in obj.modifiers:
            mod_data = {"name": m.name, "type": m.type}
            if m.type == "ARMATURE":
                mod_data["object"] = m.object.name if m.object else None
                mod_data["use_deform_preserve_volume"] = m.use_deform_preserve_volume if hasattr(m, "use_deform_preserve_volume") else None
            elif m.type == "SUBSURF":
                mod_data["levels"] = m.levels if hasattr(m, "levels") else None
                mod_data["render_levels"] = m.render_levels if hasattr(m, "render_levels") else None
                mod_data["subdivision_type"] = m.subdivision_type if hasattr(m, "subdivision_type") else None
                mod_data["show_viewport"] = m.show_viewport if hasattr(m, "show_viewport") else None
                mod_data["show_render"] = m.show_render if hasattr(m, "show_render") else None
            elif m.type == "SKIN":
                mod_data["show_viewport"] = m.show_viewport if hasattr(m, "show_viewport") else None
                mod_data["show_render"] = m.show_render if hasattr(m, "show_render") else None
            else:
                mod_data["show_viewport"] = m.show_viewport if hasattr(m, "show_viewport") else None
                mod_data["show_render"] = m.show_render if hasattr(m, "show_render") else None
            result.append(mod_data)
        return result

    def snapshot_json(self) -> str:
        return json.dumps(self.snapshot(), indent=2)

    def errors(self) -> List[str]:
        return self.status().get("errors", [])

    def warnings(self) -> List[str]:
        return self.status().get("warnings", [])

    def print_status(self) -> None:
        status = self.status()
        print("")
        print("=" * 60)
        print("CHARACTER ENGINE — SYSTEM STATUS")
        print("=" * 60)
        print("")
        print("STRUCTURAL STATE")
        print("-" * 60)
        for check in status.get("structural", []):
            icon = "✅" if check["status"] == "PASS" else "❌" if check["status"] in ("FAIL", "ERROR") else "⚠️"
            msg = f": {check['message']}" if check.get("message") else ""
            print(f"  {icon} {check['code']}{msg}")
        print("")
        print("VISUAL STATE")
        print("-" * 60)
        for check in status.get("visual", []):
            icon = "✅" if check["status"] == "PASS" else "❌" if check["status"] in ("FAIL", "ERROR") else "⚠️"
            msg = f": {check['message']}" if check.get("message") else ""
            print(f"  {icon} {check['code']}{msg}")
        print("")
        print("OPERATIONAL STATE")
        print("-" * 60)
        for check in status.get("operational", []):
            icon = "✅" if check["status"] == "PASS" else "❌" if check["status"] in ("FAIL", "ERROR") else "⚠️"
            msg = f": {check['message']}" if check.get("message") else ""
            print(f"  {icon} {check['code']}{msg}")
        print("")
        if status.get("errors"):
            print("ERRORS")
            print("-" * 60)
            for err in status["errors"]:
                print(f"  ❌ {err}")
            print("")
        if status.get("warnings"):
            print("WARNINGS")
            print("-" * 60)
            for warn in status["warnings"]:
                print(f"  ⚠️ {warn}")
            print("")
        global_status = status["status"]
        icon = "🟢" if global_status == "PASS" else "🟡" if global_status == "WARN" else "🔴" if global_status == "FAIL" else "⛔"
        print("GLOBAL STATUS")
        print("-" * 60)
        print(f"  {icon} {global_status}")
        print("")
        print("=" * 60)

    def print_diff(self) -> None:
        diff_data = self.diff()
        print("")
        print("=" * 60)
        print("CHARACTER ENGINE — STATE DIFF")
        print("=" * 60)
        print("")
        if diff_data["status"] == "PASS":
            print("  ✅ No differences found")
        else:
            print("  ❌ Differences found")
            print("")
            for key in ["missing", "extra", "orphans", "parent_mismatches", "geometry_mismatches", "zero_length"]:
                items = diff_data.get(key, [])
                if items:
                    label = key.upper().replace("_", " ")
                    print(f"{label}:")
                    if isinstance(items, list):
                        for item in items[:10]:
                            if isinstance(item, dict):
                                print(f"    {item}")
                            else:
                                print(f"    - {item}")
                    else:
                        print(f"    {items}")
                    print("")
        print("=" * 60)


# ================================================================
# LAZY CONSOLE INTERFACE
# ================================================================

_auditor = None
_console = None

def get_auditor(armature_name: str = "HumanSkeleton"):
    global _auditor
    if _auditor is None or _auditor.armature_name != armature_name:
        _auditor = StateAuditor(armature_name)
    return _auditor

def get_console(armature_name: str = "HumanSkeleton"):
    global _console
    if _console is None:
        _console = ConsoleInterface(get_auditor(armature_name))
    return _console


class ConsoleInterface:
    def __init__(self, auditor: StateAuditor = None):
        self._auditor = auditor or StateAuditor()

    def status(self) -> None:
        self._auditor.print_status()

    def status_json(self) -> str:
        return self._auditor.status_json()

    def diff(self) -> None:
        self._auditor.print_diff()

    def snapshot(self) -> Dict[str, Any]:
        return self._auditor.snapshot()

    def snapshot_json(self) -> str:
        return self._auditor.snapshot_json()

    def errors(self) -> List[str]:
        return self._auditor.errors()

    def warnings(self) -> List[str]:
        return self._auditor.warnings()


# ================================================================
# FUNCIONES DE CONVENIENCIA (LAZY)
# ================================================================

def status(armature_name: str = "HumanSkeleton") -> None:
    get_console(armature_name).status()

def status_json(armature_name: str = "HumanSkeleton") -> str:
    return get_console(armature_name).status_json()

def diff(armature_name: str = "HumanSkeleton") -> None:
    get_console(armature_name).diff()

def snapshot(armature_name: str = "HumanSkeleton") -> Dict[str, Any]:
    return get_console(armature_name).snapshot()

def snapshot_json(armature_name: str = "HumanSkeleton") -> str:
    return get_console(armature_name).snapshot_json()

def errors(armature_name: str = "HumanSkeleton") -> List[str]:
    return get_console(armature_name).errors()

def warnings(armature_name: str = "HumanSkeleton") -> List[str]:
    return get_console(armature_name).warnings()


# ================================================================
# CE LAZY PROXY
# ================================================================

class LazyCE:
    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        return getattr(get_console(), name)

ce = LazyCE()