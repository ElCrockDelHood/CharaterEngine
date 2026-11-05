"""Head width and depth ratios from ANSUR II (Decision 75).

    python scripts/fix_head_ratios.py            # dry run
    python scripts/fix_head_ratios.py --apply

``head_width_ratio`` (0.08) and ``head_depth_ratio`` (0.07) in ``references/anthropometry.json`` were ASSUMPTION. They take the
ANSUR II ratios to stature for men of 1.75-1.85 m (n = 1814): head breadth 154.6 ± 5.6 mm and head length 201.0 ± 6.6 mm,
measured on the head (skin), with stature 1793.0 ± 27.3 mm. Provenance DERIVED, source ANSUR_II_2012 (registered in
``source_registry.json``; 2012 US Army survey, cleared for unlimited public release). The range is p5-p95 of the individual
ratios. Note the population: US Army personnel, not the civilian population. Deterministic and idempotent. The data files
keep their exact formatting (text replacement); ``ANSUR_II_MALE_Public.csv`` is not needed at run time.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ANTHRO = ROOT / "src" / "character_engine" / "data" / "anatomy" / "references" / "anthropometry.json"
REGISTRY = ROOT / "src" / "character_engine" / "data" / "anatomy" / "references" / "source_registry.json"

NOTE = ("ANSUR II (2012 US Army survey), men 1.75-1.85 m, n = 1814: {what}; mean of individual ratios, range p5-p95. "
        "Measured on the head (skin). US Army personnel, not the civilian population")
# key -> (old value, old range, new value, new range, description)
RATIOS = {
    "head_width_ratio": (0.08, (0.07, 0.09), 0.0862, (0.0809, 0.092), "head breadth 154.6 +/- 5.6 mm"),
    "head_depth_ratio": (0.07, (0.06, 0.08), 0.1121, (0.1059, 0.1183), "head length 201.0 +/- 6.6 mm"),
}
SOURCE_ENTRY = {
    "id": "ANSUR_II_2012",
    "name": "2012 Anthropometric Survey of U.S. Army Personnel (ANSUR II)",
    "authors": "Gordon, C.C. et al.",
    "year": 2015,
    "type": "PRIMARY_RESEARCH",
    "publisher": "U.S. Army Natick Soldier RD&E Center, Report NATICK/TR-15/007",
    "coverage": "93 measures on 4082 men and 1986 women; public working databases cleared for unlimited public release (MFR 2017)",
    "population": "U.S. Army personnel (active, reserve, National Guard); not the civilian population",
    "status": "ACQUIRED",
    "confidence": "MEDIUM",
    "required_for": ["head_width_ratio", "head_depth_ratio"],
}


def _block(key: str, old_value, old_range) -> str:
    name = key.replace("_ratio", "") + "_to_total_height"
    return (f'      "{key}": {{\n        "name": "{name}",\n        "value": {old_value},\n        "range": [\n'
            f'          {old_range[0]},\n          {old_range[1]}\n        ],\n        "confidence": "LOW",\n'
            f'        "provenance": "ASSUMPTION"\n      }}')


def _new_block(key: str, value, rng, what: str) -> str:
    name = key.replace("_ratio", "") + "_to_total_height"
    return (f'      "{key}": {{\n        "name": "{name}",\n        "value": {value},\n        "range": [\n'
            f'          {rng[0]},\n          {rng[1]}\n        ],\n        "confidence": "MEDIUM",\n'
            f'        "provenance": "DERIVED",\n        "source_id": "ANSUR_II_2012",\n'
            f'        "notes": "{NOTE.format(what=what)}"\n      }}')


def fix_anthropometry(text: str) -> str:
    newline = "\r\n" if "\r\n" in text else "\n"
    t = text.replace("\r\n", "\n")
    for key, (ov, orng, nv, nrng, what) in RATIOS.items():
        new = _new_block(key, nv, nrng, what)
        if new in t:
            continue
        old = _block(key, ov, orng)
        if old not in t:
            raise SystemExit(f"{key}: block not found")
        t = t.replace(old, new)
    return t.replace("\n", newline)


def fix_registry(text: str) -> str:
    newline = "\r\n" if "\r\n" in text else "\n"
    t = text.replace("\r\n", "\n")
    if '"id": "ANSUR_II_2012"' in t:
        return t.replace("\n", newline)
    anchor = '      "drillis_contini_1966": {\n'
    if t.count(anchor) != 1:
        raise SystemExit("registry anchor not found")
    lines = json.dumps(SOURCE_ENTRY, indent=2, ensure_ascii=False).split("\n")
    entry = '      "ansur_ii_2012": ' + "\n".join([lines[0]] + ["      " + line for line in lines[1:]]) + ",\n"
    t = t.replace(anchor, entry + anchor)
    json.loads(t)
    return t.replace("\n", newline)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args(argv)
    at, rt = ANTHRO.read_bytes().decode("utf-8"), REGISTRY.read_bytes().decode("utf-8")
    new_a, new_r = fix_anthropometry(at), fix_registry(rt)
    json.loads(new_a)
    sha = lambda s: hashlib.sha256(s.encode("utf-8").replace(b"\r\n", b"\n")).hexdigest()   # noqa: E731
    print(json.dumps({"anthropometry_changed": new_a != at, "registry_changed": new_r != rt,
                      "anthropometry_sha256_lf": sha(new_a), "registry_sha256_lf": sha(new_r), "applied": a.apply}, indent=2))
    if a.apply:
        ANTHRO.write_bytes(new_a.encode("utf-8"))
        REGISTRY.write_bytes(new_r.encode("utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
