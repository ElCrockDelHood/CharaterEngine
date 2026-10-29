"""Batch retarget driver (scripts/retarget_batch.py): stdlib GLB root-channel reader and report assembly."""

import json
import struct
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import retarget_batch as rb  # noqa: E402


def _glb(path: Path, times, translations) -> Path:
    """Minimal GLB: node 'root' with one translation channel (glTF Y-up)."""
    t = b"".join(struct.pack("<f", x) for x in times)
    v = b"".join(struct.pack("<fff", *p) for p in translations)
    binary = t + v
    doc = {"asset": {"version": "2.0"}, "nodes": [{"name": "root"}],
           "buffers": [{"byteLength": len(binary)}],
           "bufferViews": [{"buffer": 0, "byteOffset": 0, "byteLength": len(t)},
                           {"buffer": 0, "byteOffset": len(t), "byteLength": len(v)}],
           "accessors": [{"bufferView": 0, "componentType": 5126, "count": len(times), "type": "SCALAR"},
                         {"bufferView": 1, "componentType": 5126, "count": len(translations), "type": "VEC3"}],
           "animations": [{"name": "Jog_Fwd_Loop", "samplers": [{"input": 0, "output": 1}],
                           "channels": [{"sampler": 0, "target": {"node": 0, "path": "translation"}}]}]}
    js = json.dumps(doc).encode()
    js += b" " * (-len(js) % 4)
    binary += b"\0" * (-len(binary) % 4)
    body = struct.pack("<II", len(js), 0x4E4F534A) + js + struct.pack("<II", len(binary), 0x004E4942) + binary
    path.write_bytes(struct.pack("<III", 0x46546C67, 2, 12 + len(body)) + body)
    return path


def test_glb_root_channel_reads_seconds_and_horizontal_displacement(tmp_path):
    glb = _glb(tmp_path / "a.glb", [0.0, 0.5, 1.0], [(0, 0, 0), (0, 0.05, 1.0), (0, 0, 2.0)])
    rec = rb.glb_root_channels(glb)["Jog_Fwd_Loop"]
    assert rec["duration_s"] == pytest.approx(1.0)
    assert rec["displacement_m"] == pytest.approx(2.0)     # XZ plane; the Y bob is vertical
    assert rec["speed_m_s"] == pytest.approx(2.0)
    assert rec["keys"] == 3


def test_read_glb_rejects_non_glb(tmp_path):
    bad = tmp_path / "x.glb"
    bad.write_bytes(b"\0" * 24)
    with pytest.raises(ValueError):
        rb.read_glb(bad)


def test_library_table_points_at_both_variants():
    assert set(rb.LIBRARIES) == {"ual1", "ual2"}
    assert rb.VARIANTS == {"standard": "", "rm": "_RM"}


def _samples(variant, clip, frames, status="ok"):
    rest = {"heel": [0.1, 0.03, 0.0], "toe": [0.1, -0.2, 0.0], "SACRUM": [0, 0, 1.0], "root": [0, 0, 0]}
    return {"fps": 30, "blender": "3.6", "bone_map": "quaternius_ual", "stature_m": 1.8,
            "target_feet": {"L": ["heel", "toe"]}, "source_feet": {"L": ["heel", "toe"]},
            "target_rest": rest, "source_rest": rest,
            "clips": [{"clip": clip, "action": clip + "_Armature", "status": status, "frame_end_raw": 9.0,
                       "mapped_bones": 55, "source": frames, "target": frames,
                       **({"error": "boom"} if status != "ok" else {})}]}


def test_evaluate_library_pairs_variants_and_reports_errors():
    still = [{"heel": [0.1, 0.03, 0.0], "toe": [0.1, -0.2, 0.0], "SACRUM": [0, 0, 1.0], "root": [0, 0, 0]}] * 10
    recs = rb.evaluate_library("ual1", {"standard": _samples("standard", "Idle_Loop", still),
                                        "rm": _samples("rm", "Idle_Loop", still)}, {})
    assert len(recs) == 1 and recs[0]["status"] == "ok" and recs[0]["integer_frames"]
    bad = rb.evaluate_library("ual1", {"standard": _samples("standard", "Idle_Loop", still, status="error")}, {})
    assert bad[0]["status"] == "error"
