"""Decision 76: the public repository carries the attributions its licences require."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_notice_keeps_the_required_attributions():
    text = (ROOT / "NOTICE").read_text(encoding="utf-8")
    assert "BodyParts3D, © The Database Center for Life Science licensed under CC Attribution 4.0 International" in text
    assert "creativecommons.org/licenses/by/4.0" in text
    assert "CC BY-SA 2.1 Japan" in text  # the discrepancy stays disclosed
    assert "cleared for UNLIMITED PUBLIC RELEASE" in text
    assert "CC BY-NC" in text and "Drillis" in text and "Wu, G." in text


def test_project_licence_is_mit_everywhere():
    """Decision 77: LICENSE and pyproject agree, and LICENSE carries no personal identifier."""
    licence = (ROOT / "LICENSE").read_text(encoding="utf-8")
    assert licence.startswith("MIT License\n") or licence.startswith("MIT License\r\n")
    assert "Copyright (c) 2026 Mariano Martin Galli" in licence and "DNI" not in licence
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'license = { text = "MIT" }' in pyproject and "License :: OSI Approved :: MIT License" in pyproject


def test_notice_keeps_third_party_terms_apart_from_mit():
    text = " ".join((ROOT / "NOTICE").read_text(encoding="utf-8").split())
    assert "values derived from BodyParts3D keep CC BY 4.0 with attribution" in text


def test_readme_points_to_the_notice():
    assert "[NOTICE](NOTICE)" in (ROOT / "README.md").read_text(encoding="utf-8")
