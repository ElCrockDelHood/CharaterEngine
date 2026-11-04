"""Asset manifest contract and validator (phase F0 of ``docs/architecture/ASSET_FITTING_PROPOSAL.md``).

Every mesh asset (bone, muscle, tendon, fascia, fat, skin) that is fitted onto the canonical rig enters with a
JSON manifest. This module validates that manifest in pure Python, **before** Blender opens the file:

* schema and value types of every field listed in §3 of the proposal;
* licence, author and origin are present and actually read (placeholders such as ``"…"`` are rejected,
  Decision 46);
* ``sha256`` is a 64-digit hex digest (``verify_sha256`` compares it with the file bytes the caller read);
* every ``canonical_bone`` exists among the 208 canonical nodes, with the side semantics of the skeleton
  (``midline`` = the name itself; ``L`` / ``R`` / ``mirror`` = ``<BONE>_L`` and ``<BONE>_R``);
* a rigid part (layer ``bone``) carries at least 3 non-collinear anchors, so position, rotation **and roll**
  are fixed;
* muscle / tendon attachments agree with the ``MUSCLES`` catalogue (topology PROVEN).

STATUS: the manifest itself is a PROPOSAL pending the owner's approval (§8.1 of the proposal). Landmark names
are not checked against a closed list yet because that list does not exist (§8.4, PENDING); pass
``known_landmarks`` to enforce one. No I/O here: the caller reads the JSON and the canonical node names.
"""

from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Optional, Sequence, Tuple

from ..anatomy.reference.source import ProvenanceState
from ..tissue.muscles import MUSCLES, MuscleSpec
from .normalize import AXES

Vec = Tuple[float, float, float]

LAYERS: Tuple[str, ...] = ("bone", "muscle", "tendon", "fascia", "fat", "skin")
RIGID_LAYERS: Tuple[str, ...] = ("bone",)
ATTACHMENT_LAYERS: Tuple[str, ...] = ("muscle", "tendon")
SIDES: Tuple[str, ...] = ("L", "R", "mirror", "midline")
SOURCE_UNITS: Mapping[str, float] = {"m": 1.0, "cm": 0.01, "mm": 0.001}
FILE_EXTENSIONS: Tuple[str, ...] = (".glb", ".gltf", ".obj", ".ply")   # what the Blender 3.6 addon imports
MIN_RIGID_ANCHORS = 3   # geometry: 3 non-collinear points fix a rigid frame including roll

REQUIRED_FIELDS: Tuple[str, ...] = (
    "asset_id", "file", "sha256", "layer", "parts", "source_units", "up", "forward",
    "licence", "author", "origin_url", "provenance",
)
# Values that mean "nobody read it yet" — a manifest carrying them is rejected (Decision 46).
PLACEHOLDER_TEXT = frozenset({"", "…", "...", "?", "tbd", "todo", "unknown", "pending", "n/a", "na", "none"})

_ASSET_ID = re.compile(r"^[a-z0-9][a-z0-9_\-]*$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class Tolerance:
    """A fitting tolerance from §5 of the proposal. ``value`` None = not set (PENDING)."""
    metric: str
    value: Optional[float]
    unit: str
    provenance: ProvenanceState
    note: str


# §5 tolerances. None of them is approved: the proposed values are ESTIMATE, the rest UNKNOWN (pending owner
# or source). F0 only records them; nothing in this module applies them. "0 canonical joints moved" is not a
# tolerance but the Decision 16 invariant, so it is not listed here.
TOLERANCES: Mapping[str, Tolerance] = {
    "anchor_rms": Tolerance("RMS landmark asset vs canonical", 2.0, "mm", ProvenanceState.ESTIMATE,
                            "proposed, pending owner (§8.2)"),
    "bone_length": Tolerance("asset length vs osteometry (Decision 16)", 1.0, "%", ProvenanceState.ESTIMATE,
                             "proposed, pending owner (§8.2)"),
    "mirror_symmetry": Tolerance("L/R mirror of 'mirror' parts", 1.0, "mm", ProvenanceState.ESTIMATE,
                                 "proposed, pending owner (§8.2)"),
    "layer_clearance": Tolerance("clearance of a layer inside the previous one", None, "mm",
                                 ProvenanceState.UNKNOWN, "PENDING owner"),
    "edge_stretch": Tolerance("edge stretch in 6 test poses", None, "%", ProvenanceState.UNKNOWN,
                              "PENDING source"),
}


@dataclass(frozen=True)
class Anchor:
    landmark: str
    point: Vec            # asset space, source units, before normalisation


@dataclass(frozen=True)
class Part:
    mesh: str
    canonical_bone: str   # base name, no _L/_R
    side: str
    anchors: Tuple[Anchor, ...]

    def target_nodes(self) -> Tuple[str, ...]:
        """Canonical node names this part is fitted to."""
        if self.side == "midline":
            return (self.canonical_bone,)
        if self.side == "mirror":
            return (f"{self.canonical_bone}_L", f"{self.canonical_bone}_R")
        return (f"{self.canonical_bone}_{self.side}",)


@dataclass(frozen=True)
class Attachment:
    muscle: str           # base name, no _L/_R
    origin_bone: str
    insertion_bone: str


@dataclass(frozen=True)
class AssetManifest:
    asset_id: str
    file: str
    sha256: str
    layer: str
    parts: Tuple[Part, ...]
    attachments: Tuple[Attachment, ...]
    source_units: str
    up: str
    forward: str
    licence: str
    author: str
    origin_url: str
    provenance: ProvenanceState

    @property
    def unit_scale(self) -> float:
        return SOURCE_UNITS[self.source_units]


@dataclass(frozen=True)
class ManifestIssue:
    code: str
    path: str
    message: str


@dataclass(frozen=True)
class ManifestReport:
    issues: Tuple[ManifestIssue, ...]
    manifest: Optional[AssetManifest] = None
    status: str = field(default="PROPOSED")   # the contract is not approved yet (§8.1)

    @property
    def ok(self) -> bool:
        return not self.issues

    def codes(self) -> Tuple[str, ...]:
        return tuple(i.code for i in self.issues)


def _base(name: str) -> str:
    return name[:-2] if name.endswith(("_L", "_R")) else name


def _is_read_text(value: Any) -> bool:
    return isinstance(value, str) and value.strip().lower() not in PLACEHOLDER_TEXT


def _point(value: Any) -> Optional[Vec]:
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        return None
    if not all(isinstance(c, (int, float)) and not isinstance(c, bool) and math.isfinite(c) for c in value):
        return None
    return (float(value[0]), float(value[1]), float(value[2]))


def _non_collinear(points: Sequence[Vec]) -> bool:
    """True if some triple of points spans a triangle (relative test, scale-free)."""
    span = max((math.dist(a, b) for a in points for b in points), default=0.0)
    if span == 0.0:
        return False
    for i in range(len(points)):
        for j in range(i + 1, len(points)):
            for k in range(j + 1, len(points)):
                a, b, c = points[i], points[j], points[k]
                u = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
                v = (c[0] - a[0], c[1] - a[1], c[2] - a[2])
                cross = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
                if math.sqrt(sum(x * x for x in cross)) > 1e-9 * span * span:   # numerical degeneracy guard
                    return True
    return False


def validate_manifest(raw: Any, canonical_nodes: Iterable[str],
                      muscles: Optional[Mapping[str, MuscleSpec]] = None,
                      known_landmarks: Optional[Iterable[str]] = None) -> ManifestReport:
    """Validate a decoded manifest (dict) against the canonical node names; never raises on bad input."""
    nodes = frozenset(canonical_nodes)
    catalogue = MUSCLES if muscles is None else muscles
    landmarks = None if known_landmarks is None else frozenset(known_landmarks)
    issues = []

    def bad(code: str, path: str, message: str) -> None:
        issues.append(ManifestIssue(code, path, message))

    if not isinstance(raw, Mapping):
        bad("not_an_object", "$", "manifest must be a JSON object")
        return ManifestReport(tuple(issues))

    for key in REQUIRED_FIELDS:
        if key not in raw:
            bad("missing_field", key, f"required field '{key}' is missing")

    asset_id = raw.get("asset_id")
    if "asset_id" in raw and not (isinstance(asset_id, str) and _ASSET_ID.match(asset_id)):
        bad("bad_asset_id", "asset_id", "lowercase letters, digits, '_' or '-'")

    file_name = raw.get("file")
    if "file" in raw:
        if not isinstance(file_name, str) or not file_name or any(s in file_name for s in ("/", "\\", "..")):
            bad("bad_file", "file", "plain file name, no directories")
        elif not file_name.lower().endswith(FILE_EXTENSIONS):
            bad("bad_file", "file", f"extension must be one of {FILE_EXTENSIONS}")

    sha = raw.get("sha256")
    if "sha256" in raw and not (isinstance(sha, str) and _SHA256.match(sha)):
        bad("bad_sha256", "sha256", "64 lowercase hex digits of the file bytes")

    layer = raw.get("layer")
    if "layer" in raw and layer not in LAYERS:
        bad("bad_layer", "layer", f"one of {LAYERS}")

    units = raw.get("source_units")
    if "source_units" in raw and units not in SOURCE_UNITS:
        bad("bad_units", "source_units", f"one of {tuple(SOURCE_UNITS)}")

    up, forward = raw.get("up"), raw.get("forward")
    for key, axis in (("up", up), ("forward", forward)):
        if key in raw and axis not in AXES:
            bad("bad_axis", key, f"one of {sorted(AXES)}")
    if up in AXES and forward in AXES and sum(a * b for a, b in zip(AXES[up], AXES[forward])) != 0:
        bad("bad_axis", "forward", "up and forward must be perpendicular")

    for key, code in (("licence", "licence_not_read"), ("author", "author_not_read"),
                      ("origin_url", "origin_not_read")):
        if key in raw and not _is_read_text(raw.get(key)):
            bad(code, key, f"'{key}' must be the value actually read from the source (Decision 46)")

    prov = raw.get("provenance")
    provenance = None
    if "provenance" in raw:
        try:
            provenance = ProvenanceState[prov] if isinstance(prov, str) else None
        except KeyError:
            provenance = None
        if provenance is None:
            bad("bad_provenance", "provenance", f"one of {[p.name for p in ProvenanceState]}")

    parts = []
    raw_parts = raw.get("parts")
    if "parts" in raw and (not isinstance(raw_parts, list) or not raw_parts):
        bad("no_parts", "parts", "at least one part")
        raw_parts = []
    for i, rp in enumerate(raw_parts or []):
        p = f"parts[{i}]"
        if not isinstance(rp, Mapping):
            bad("bad_part", p, "part must be an object")
            continue
        mesh, bone, side = rp.get("mesh"), rp.get("canonical_bone"), rp.get("side")
        if not isinstance(mesh, str) or not mesh:
            bad("bad_part", f"{p}.mesh", "mesh name inside the file")
        if side not in SIDES:
            bad("bad_side", f"{p}.side", f"one of {SIDES}")
        if not isinstance(bone, str) or not bone:
            bad("unknown_bone", f"{p}.canonical_bone", "canonical bone base name required")
        elif bone.endswith(("_L", "_R")):
            bad("bone_has_side", f"{p}.canonical_bone", "use the base name; the side goes in 'side'")
        elif side in SIDES:
            wanted = Part("", bone, side, ()).target_nodes()
            missing = [n for n in wanted if n not in nodes]
            if missing:
                bad("unknown_bone", f"{p}.canonical_bone",
                    f"not among the {len(nodes)} canonical nodes for side '{side}': {missing}")
        anchors = []
        raw_anchors = rp.get("anchors", [])
        if not isinstance(raw_anchors, list):
            bad("bad_anchor", f"{p}.anchors", "list of anchors")
            raw_anchors = []
        for j, ra in enumerate(raw_anchors):
            a = f"{p}.anchors[{j}]"
            name = ra.get("landmark") if isinstance(ra, Mapping) else None
            point = _point(ra.get("vertex_or_point")) if isinstance(ra, Mapping) else None
            if not isinstance(name, str) or not name:
                bad("bad_anchor", f"{a}.landmark", "landmark name required")
                continue
            if landmarks is not None and name not in landmarks:
                bad("unknown_landmark", f"{a}.landmark", f"'{name}' is not in the landmark list")
            if point is None:
                bad("bad_anchor", f"{a}.vertex_or_point", "three finite numbers")
                continue
            anchors.append(Anchor(name, point))
        names = [a.landmark for a in anchors]
        if len(set(names)) != len(names):
            bad("duplicate_anchor", f"{p}.anchors", "each landmark once per part")
        if layer in RIGID_LAYERS:
            if len(anchors) < MIN_RIGID_ANCHORS:
                bad("too_few_anchors", f"{p}.anchors",
                    f"rigid part needs >= {MIN_RIGID_ANCHORS} anchors (position, rotation and roll), got {len(anchors)}")
            elif not _non_collinear([a.point for a in anchors]):
                bad("collinear_anchors", f"{p}.anchors", "anchors are collinear: roll is undefined")
        if isinstance(mesh, str) and isinstance(bone, str) and side in SIDES:
            parts.append(Part(mesh, bone, side, tuple(anchors)))

    attachments = []
    raw_att = raw.get("attachments", [])
    if not isinstance(raw_att, list):
        bad("bad_attachment", "attachments", "list of attachments")
        raw_att = []
    if layer in ATTACHMENT_LAYERS and not raw_att:
        bad("missing_attachments", "attachments", f"layer '{layer}' needs origin / insertion per muscle")
    for k, rt in enumerate(raw_att):
        t = f"attachments[{k}]"
        if not isinstance(rt, Mapping):
            bad("bad_attachment", t, "attachment must be an object")
            continue
        muscle, origin, insertion = rt.get("muscle"), rt.get("origin_bone"), rt.get("insertion_bone")
        if not all(isinstance(x, str) and x for x in (muscle, origin, insertion)):
            bad("bad_attachment", t, "muscle, origin_bone and insertion_bone are required")
            continue
        spec = catalogue.get(muscle) or catalogue.get(f"{muscle}_L")
        if spec is None:
            bad("unknown_muscle", f"{t}.muscle", f"'{muscle}' is not in the MUSCLES catalogue")
        elif (_base(spec.origin_bone), _base(spec.insertion_bone)) != (_base(origin), _base(insertion)):
            bad("attachment_mismatch", t,
                f"catalogue says {_base(spec.origin_bone)} -> {_base(spec.insertion_bone)}, "
                f"manifest says {_base(origin)} -> {_base(insertion)}")
        attachments.append(Attachment(muscle, origin, insertion))

    if issues:
        return ManifestReport(tuple(issues))
    return ManifestReport((), AssetManifest(
        asset_id=asset_id, file=file_name, sha256=sha, layer=layer, parts=tuple(parts),
        attachments=tuple(attachments), source_units=units, up=up, forward=forward,
        licence=raw["licence"], author=raw["author"], origin_url=raw["origin_url"], provenance=provenance,
    ))


def verify_sha256(manifest: AssetManifest, file_bytes: bytes) -> bool:
    """True if the SHA-256 of the file bytes (read by the caller) matches the manifest."""
    return hashlib.sha256(file_bytes).hexdigest() == manifest.sha256
