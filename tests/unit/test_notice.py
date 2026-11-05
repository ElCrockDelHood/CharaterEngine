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


def test_readme_points_to_the_notice():
    assert "[NOTICE](NOTICE)" in (ROOT / "README.md").read_text(encoding="utf-8")
