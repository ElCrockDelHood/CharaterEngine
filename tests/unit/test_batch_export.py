"""Batch export job spec (pipeline/batch_export.py): matrix expansion, names, refusals, provenance, manifest."""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from character_engine.pipeline.batch_export import (
    LATEST_MANIFEST,
    BatchJob,
    BatchSpecError,
    ClipSpec,
    expand,
    job_name,
    load_spec,
    manifest,
    manifest_name,
    pick_clip,
    provenance_record,
    run_id,
    sha256_file,
    write_manifest,
)

ROOT = Path(__file__).resolve().parents[2]


def _spec(**matrix):
    return {"spec_version": 1, "matrices": [matrix]}


def test_default_spec_expands_to_four_named_jobs():
    jobs = expand(load_spec(ROOT / "scripts" / "batch_specs" / "default.json"), root=ROOT)
    assert [j.name for j in jobs] == [
        "human_male_adult_1800mm_tpose", "human_male_adult_1800mm_anatomical",
        "human_female_adult_1650mm_tpose", "human_female_adult_1650mm_anatomical"]
    assert all(j.clip is None and j.mesh == "block_dummy" for j in jobs)
    # 1.80 / 1.65 are the templates' own statures: not an override
    assert not any(j.stature_overridden for j in jobs)


def test_matrix_is_the_full_product_in_spec_order():
    clip = {"path": "a/Walk.glb", "bone_map": "quaternius_ual", "clip": "Walk"}
    jobs = expand(_spec(templates=["human_male_adult", "human_child_5y"], statures_m=[1.5, None],
                        poses=["tpose", "apose"], clips=[None, clip]))
    assert len(jobs) == 2 * 2 * 2 * 2
    assert jobs[0].name == "human_male_adult_1500mm_tpose"
    assert jobs[1].name == "human_male_adult_1500mm_tpose__quaternius_ual_walk"
    assert jobs[4].name == "human_male_adult_1800mm_tpose"         # None = template stature
    assert jobs[4].stature_overridden is False and jobs[0].stature_overridden is True
    assert jobs[-1].template_id == "human_child_5y" and jobs[-1].stature_m == pytest.approx(1.10)


def test_names_are_deterministic_and_clip_slug_falls_back_to_file_stem():
    assert job_name("human_female_adult", 1.655, "anatomical") == "human_female_adult_1655mm_anatomical"
    assert ClipSpec("x/UAL1 Standard.glb", "quaternius_ual").slug() == "ual1_standard"
    assert ClipSpec("x.bvh", "mixamo", "Sword Attack!").slug() == "sword_attack"
    spec = _spec(templates=["human_male_adult"], poses=["tpose"])
    assert [j.name for j in expand(spec)] == [j.name for j in expand(json.loads(json.dumps(spec)))]


@pytest.mark.parametrize("template", ["horse_adult", "dog_adult"])
def test_unavailable_templates_are_refused_not_guessed(template):
    with pytest.raises(BatchSpecError) as exc:
        expand(_spec(templates=["human_male_adult", template], poses=["tpose"]))
    assert any(template in e and "refused" in e for e in exc.value.errors)


def test_every_error_is_reported_at_once():
    with pytest.raises(BatchSpecError) as exc:
        expand(_spec(templates=["nope"], statures_m=[9.0, True], poses=["sitting"], mesh="tissues",
                     clips=[{"path": "a.txt", "bone_map": "x"}, {"bone_map": "mixamo"}], extra=1))
    text = "\n".join(exc.value.errors)
    for needle in ("unknown template 'nope'", "stature 9.0", "stature True", "unknown pose 'sitting'",
                   "mesh 'tissues'", "unknown bone map 'x'", "'a.txt' is not one of", "needs 'path'",
                   "unknown keys ['extra']"):
        assert needle in text, needle


def test_structural_errors():
    with pytest.raises(BatchSpecError, match="'matrices' is empty"):
        expand({"spec_version": 1, "matrices": []})
    with pytest.raises(BatchSpecError, match="spec_version"):
        expand({"spec_version": 2, "matrices": [{"templates": ["human_male_adult"], "poses": ["tpose"]}]})
    with pytest.raises(BatchSpecError, match="duplicate job names"):
        expand(_spec(templates=["human_male_adult"], statures_m=[1.8, None], poses=["tpose"]))


def test_clip_files_must_exist_when_root_is_given(tmp_path):
    clip = {"path": "anim/walk.bvh", "bone_map": "mixamo"}
    expand(_spec(templates=["human_male_adult"], poses=["tpose"], clips=[clip]))     # no root: not checked
    with pytest.raises(BatchSpecError, match="clip file not found"):
        expand(_spec(templates=["human_male_adult"], poses=["tpose"], clips=[clip]), root=tmp_path)
    (tmp_path / "anim").mkdir()
    (tmp_path / "anim" / "walk.bvh").write_text("HIERARCHY", encoding="utf-8")
    assert len(expand(_spec(templates=["human_male_adult"], poses=["tpose"], clips=[clip]), root=tmp_path)) == 1


def test_job_round_trips_through_dict():
    job = BatchJob("n", "human_male_adult", 1.7, True, "apose", "none", ClipSpec("a.glb", "quaternius_ual", "Walk"))
    assert BatchJob.from_dict(json.loads(json.dumps(job.to_dict()))) == job


def test_provenance_record_states():
    tpl = expand(_spec(templates=["human_child_5y"], poses=["tpose"]))[0]
    rec = provenance_record(tpl, blender_version="3.6.23", addon_version="0.3.1", glb_sha256="ab", glb_bytes=3)
    assert rec["provenance"] == {"stature": "estimate", "proportions": "placeholder", "mesh": "estimate"}
    over = expand(_spec(templates=["human_child_5y"], statures_m=[1.2], poses=["tpose"], mesh="none"))[0]
    rec = provenance_record(over, blender_version="3.6.23", addon_version="0.3.1", glb_sha256="ab", glb_bytes=3,
                            extra={"bones": 208})
    assert rec["provenance"] == {"stature": "user_input", "proportions": "placeholder", "mesh": None}
    assert rec["bones"] == 208 and rec["clip"] is None and rec["bone_map"] is None


def test_manifest_marks_missing_results_as_fail(tmp_path):
    jobs = expand(_spec(templates=["human_male_adult"], poses=["tpose", "apose", "anatomical"]))
    doc = manifest(jobs, {jobs[0].name: {"status": "PASS"}, jobs[2].name: {"status": "FAIL", "error": "boom"}},
                   blender_version="3.6.23")
    assert (doc["jobs_total"], doc["passed"], doc["failed"]) == (3, 1, 2)
    assert [r["name"] for r in doc["jobs"]] == [j.name for j in jobs]
    assert doc["jobs"][1] == {"name": jobs[1].name, "status": "FAIL", "error": "not run"}
    assert doc["blender_version"] == "3.6.23"
    f = tmp_path / "x.bin"
    f.write_bytes(b"abc")
    assert sha256_file(f) == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"


def test_invalid_json_spec(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{nope", encoding="utf-8")
    with pytest.raises(BatchSpecError, match="not valid JSON"):
        load_spec(p)


def test_run_ids_are_utc_and_sort_chronologically():
    t = datetime(2026, 10, 29, 20, 5, 7, tzinfo=timezone(timedelta(hours=-3)))
    assert run_id(t) == "20261029T230507Z"
    assert run_id(t) < run_id(t + timedelta(seconds=1)) < run_id(t + timedelta(days=1))
    assert manifest_name("scripts/batch_specs/UAL1 Local.json", "20261029T230507Z") ==         "manifest_ual1_local_20261029T230507Z.json"


def test_each_run_keeps_its_manifest_and_the_latest_copy_follows(tmp_path):
    first = write_manifest(tmp_path, manifest_name("default.json", "20261029T000000Z"), {"run": 1})
    second = write_manifest(tmp_path, manifest_name("other.json", "20261029T000001Z"), {"run": 2})
    assert json.loads(first.read_text(encoding="utf-8")) == {"run": 1}          # earlier run not overwritten
    assert json.loads((tmp_path / LATEST_MANIFEST).read_text(encoding="utf-8")) == {"run": 2}
    write_manifest(tmp_path, second.name, {"run": 2, "jobs_done": 3})          # same run rewritten after each job
    assert json.loads((tmp_path / LATEST_MANIFEST).read_text(encoding="utf-8"))["jobs_done"] == 3
    assert sorted(p.name for p in tmp_path.iterdir()) == [
        LATEST_MANIFEST, "manifest_default_20261029T000000Z.json", "manifest_other_20261029T000001Z.json"]


def test_pick_clip_prefers_exact_then_prefix_over_the_importer_substring_rule():
    names = ["Crouch_Idle_Loop_Armature", "Idle_Loop_Armature", "Sitting_Idle_Loop_Armature",
             "Sword_Regular_A_Armature", "Sword_Regular_A_Rec_Armature", "Swing_Test_UE_Test"]
    assert pick_clip(names, "Idle_Loop") == ("Idle_Loop_Armature", "prefix")      # substring would pick Crouch_
    assert pick_clip(names, "sword_regular_a") == ("Sword_Regular_A_Armature", "prefix")
    assert pick_clip(names, "Swing_Test_UE_Test") == ("Swing_Test_UE_Test", "exact")
    assert pick_clip(names, "Regular_A_Rec") == ("Sword_Regular_A_Rec_Armature", "substring")
    with pytest.raises(KeyError, match="no clip matching 'Run'"):
        pick_clip(names, "Run")

