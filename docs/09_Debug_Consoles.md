# 09 — Debug consoles and run logs (daily working mode)

Every run must be visible while it happens **and** leave a log you can open later. Nobody (person
or agent) runs tests or engines silently; reports always give the log path and the exact command
to repeat the run by hand.

## Where the logs are

| Run | Command (from the repository root) | Log |
|-----|-------------------------------------|-----|
| pytest (all tests, `-v -rA`) | `.venv\Scripts\python.exe scripts\test.py` | `logs\<UTC>_pytest.log`, `logs\latest_pytest.log` |
| ruff + architecture guard | `.venv\Scripts\python.exe scripts\lint.py` | `logs\<UTC>_lint.log`, `logs\latest_lint.log` |
| Blender addon suite (background) | `.venv\Scripts\python.exe scripts\engine_tests.py blender` | `logs\<UTC>_blender_addon.log` + `builds\tests\blender_addon_report.json` |
| UPBGE addon suite (window) | `.venv\Scripts\python.exe scripts\engine_tests.py upbge` | `logs\<UTC>_upbge_addon.log`, `builds\tests\upbge_blenderplayer.log`, `builds\tests\upbge_addon_report.json` |
| Godot suite (headless) | `.venv\Scripts\python.exe scripts\engine_tests.py godot` | `logs\<UTC>_godot_assets.log`, `_godot_import.log`, `_godot.log` + `builds\tests\godot_report.json` |
| Engine debug output | add `--verbose` (Godot `--verbose`, Blender/UPBGE `--debug-python`) | same files, much longer |

`<UTC>` is `yyyymmddTHHMMSSZ`. Each log has a header (command, folder, git commit, Python), the UTC
time on every line and a footer with exit code and duration. The newest 50 logs per tool are kept;
`logs\` is ignored by git. `builds\tests\<step>.log` still holds the plain output of the last run.
Implementation: `scripts/_logrun.py` (stdlib only; the pure domain never logs).

## PowerShell recipes

```powershell
# follow a run live from a second console (UTF-8 logs with BOM: accents and Δ show correctly)
Get-Content logs\latest_pytest.log -Wait -Tail 50
Get-Content logs\latest_godot.log -Wait -Tail 50

# keep a transcript of everything you type and see in this console
Start-Transcript -Path "C:\DEV\logs\ps_$(Get-Date -f yyyyMMdd_HHmm).txt" -Append
# ... work ...
Stop-Transcript

# last failures of the latest pytest run
Select-String -Path logs\latest_pytest.log -Pattern 'FAILED|ERROR'
```

`Start-Transcript` is per console; it is **not** added to the PowerShell profile automatically
(that would be a persistent configuration change and needs the owner's explicit OK).

## The programs' own consoles

* **Blender / UPBGE (GUI):** *Window → Toggle System Console* shows everything the addon prints.
  Background runs (`-b`) print to the calling console, which `engine_tests.py` streams and logs.
* **Godot:** use `Godot_v4.7.2-stable_win64_console.exe`; the console window shows the engine log.
  `--verbose` adds engine-level detail.
* **blenderplayer (UPBGE game):** its output goes to `builds\tests\upbge_blenderplayer.log`.

## Known environment limit (2026-10-24)

On this PC (GeForce GT 740M, NVIDIA driver 388.73) `blenderplayer.exe` of UPBGE 0.50 cannot compile
four EEVEE shaders (errors C1317) and exits with 0xC0000005; see Decision 39.
