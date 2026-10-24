"""scripts/_logrun.py: live console + timestamped log + latest copy, exit code, duration, UTF-8."""

import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from _logrun import append_log, run_logged  # noqa: E402

PY = sys.executable


def test_tees_console_and_files_with_header_footer(tmp_path, capsys):
    code, secs, log = run_logged([PY, "-c", "print('hola Δ ≤ ñ'); print('segunda')"], "demo",
                                 logs_dir=tmp_path)
    assert code == 0 and secs >= 0
    assert re.fullmatch(r"\d{8}T\d{6}Z_demo\.log", log.name)
    assert log.read_bytes().startswith(b"\xef\xbb\xbf")         # BOM: PowerShell 5.1 reads UTF-8
    text = log.read_text(encoding="utf-8-sig")
    assert "# tool    : demo" in text and "# command :" in text and "# commit  :" in text
    assert re.search(r"^\[\d\d:\d\d:\d\d\.\d{3}\] hola Δ ≤ ñ$", text, re.M)
    assert "# exit code: 0" in text and "duration:" in text
    assert (tmp_path / "latest_demo.log").read_text(encoding="utf-8-sig") == text
    out = capsys.readouterr().out
    assert "hola Δ ≤ ñ" in out and "segunda" in out and str(log) in out


def test_exit_code_copy_to_and_append(tmp_path):
    legacy = tmp_path / "legacy.log"
    code, _, log = run_logged([PY, "-c", "import sys; print('boom'); sys.exit(3)"], "fail",
                              logs_dir=tmp_path, copy_to=legacy, echo=False)
    assert code == 3
    assert legacy.read_text(encoding="utf-8") == "boom\n"          # plain output, no timestamps
    assert "# exit code: 3" in log.read_text(encoding="utf-8")
    append_log(log, "fail", "architecture guard: OK")
    for f in (log, tmp_path / "latest_fail.log"):
        assert f.read_text(encoding="utf-8").rstrip().endswith("architecture guard: OK")


def test_timeout_kills_and_returns_124(tmp_path):
    code, _, log = run_logged([PY, "-c", "import time; time.sleep(30)"], "slow", logs_dir=tmp_path,
                              timeout=1, echo=False)
    assert code == 124
    assert "!! timeout after 1 s" in log.read_text(encoding="utf-8")


def test_retention_keeps_the_newest(tmp_path):
    for i in range(4):
        (tmp_path / f"2026010{i}T000000Z_old.log").write_text("x", encoding="utf-8")
    run_logged([PY, "-c", "pass"], "old", logs_dir=tmp_path, keep=2, echo=False)
    dated = sorted(p.name for p in tmp_path.glob("*_old.log") if not p.name.startswith("latest_"))
    assert len(dated) == 2 and dated[0].startswith("20260103")


@pytest.mark.parametrize("tool", ["pytest", "lint", "godot_import"])
def test_tool_names_become_file_names(tmp_path, tool):
    _, _, log = run_logged([PY, "-c", "pass"], tool, logs_dir=tmp_path, echo=False)
    assert log.name.endswith(f"_{tool}.log") and (tmp_path / f"latest_{tool}.log").exists()
