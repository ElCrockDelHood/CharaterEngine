"""Make ``character_engine`` importable from wherever the addon is installed.

Resolution order:
1. Environment variable ``CHARACTER_ENGINE_SRC`` (path to the repo ``src`` folder).
2. Walk up from this file until a ``character_engine/domain`` package is found
   (works when the addon lives inside the repository).
3. A ``ce_src_path.txt`` file next to the addon (written by the installer).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def _candidates():
    env = os.environ.get("CHARACTER_ENGINE_SRC")
    if env:
        yield Path(env)
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "character_engine" / "domain").is_dir():
            yield parent
    marker = here.parent / "ce_src_path.txt"
    if marker.exists():
        yield Path(marker.read_text(encoding="utf-8").strip())


def find_src_path() -> Path | None:
    for cand in _candidates():
        if (cand / "character_engine" / "domain").is_dir():
            return cand
    return None


def ensure_domain_importable() -> Path:
    try:
        import character_engine.domain  # noqa: F401
        return Path(sys.modules["character_engine"].__file__).resolve().parent.parent
    except ImportError:
        pass
    src = find_src_path()
    if src is None:
        raise ImportError(
            "Character Engine sources not found. Set CHARACTER_ENGINE_SRC to the repository 'src' folder "
            "or install the addon with scripts/install_blender_addon.py"
        )
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))
    return src


def repo_root() -> Path:
    """Repository root (parent of ``src``) — used for assets and builds folders."""
    return ensure_domain_importable().parent
