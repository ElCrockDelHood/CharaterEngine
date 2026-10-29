"""Figure and table for experiment 001 (contact threshold) from the Godot-readable experiments JSON.

    python scripts/plot_experiment.py [experiments_d1.json] [--svg out.svg]

Stdlib only: writes an SVG chart (minimum signed distance vs spacing, grid and bisection points, zero line,
threshold interval) and prints a Markdown table of the measurements.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT = ROOT / "runtime/godot/addons/character_engine/data/experiments_d1.json"


def svg(record: dict) -> str:
    pts = sorted(record["grid"], key=lambda p: p["distance_m"])
    steps = record["bisection"]["steps"]
    every = pts + steps
    xs = [p["distance_m"] for p in every]
    ys = [p["min_signed_distance_m"] for p in every] + [0.0]
    x0, x1 = min(xs), max(xs)
    y0, y1 = min(ys), max(ys)
    pad = (y1 - y0) * 0.1 or 0.01
    y0, y1 = y0 - pad, y1 + pad
    w, h, ml, mr, mt, mb = 720, 420, 70, 20, 40, 50

    def px(x):
        return ml + (x - x0) / (x1 - x0) * (w - ml - mr)

    def py(y):
        return mt + (y1 - y) / (y1 - y0) * (h - mt - mb)

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" font-family="sans-serif" font-size="12">',
           f'<rect width="{w}" height="{h}" fill="#ffffff"/>',
           f'<text x="{ml}" y="22" font-size="14">{record["id"]}: minimum signed sabre-to-body distance vs '
           f'spacing</text>']
    t = record["threshold"]
    if t["contact_up_to_m"] is not None and t["no_contact_from_m"] is not None:
        a, b = px(t["contact_up_to_m"]), px(t["no_contact_from_m"])
        out.append(f'<rect x="{a:.1f}" y="{mt}" width="{max(b - a, 1.5):.1f}" height="{h - mt - mb}" '
                   f'fill="#f2b134" opacity="0.5"/>')
    out.append(f'<line x1="{ml}" y1="{py(0):.1f}" x2="{w - mr}" y2="{py(0):.1f}" stroke="#888" '
               f'stroke-dasharray="4 3"/>')
    out.append(f'<text x="{w - mr - 4}" y="{py(0) - 4:.1f}" text-anchor="end" fill="#666">0 = touching</text>')
    for i in range(6):
        y = y0 + (y1 - y0) * i / 5
        out.append(f'<text x="{ml - 6}" y="{py(y) + 4:.1f}" text-anchor="end">{y:+.3f}</text>')
    for p in pts:
        out.append(f'<text x="{px(p["distance_m"]):.1f}" y="{h - mb + 16}" text-anchor="middle">'
                   f'{p["distance_m"]:.3f}</text>')
    out.append(f'<text x="{(ml + w - mr) / 2}" y="{h - 10}" text-anchor="middle">spacing d (m)</text>')
    out.append(f'<text x="16" y="{(mt + h - mb) / 2}" transform="rotate(-90 16 {(mt + h - mb) / 2})" '
               f'text-anchor="middle">min signed distance (m)</text>')
    path = " ".join(f'{"M" if i == 0 else "L"}{px(p["distance_m"]):.1f},{py(p["min_signed_distance_m"]):.1f}'
                    for i, p in enumerate(pts))
    out.append(f'<path d="{path}" fill="none" stroke="#3b6fb6" stroke-width="2"/>')
    for p in pts:
        fill = "#c0392b" if p["contact"] else "#3b6fb6"
        out.append(f'<circle cx="{px(p["distance_m"]):.1f}" cy="{py(p["min_signed_distance_m"]):.1f}" r="5" '
                   f'fill="{fill}"/>')
    for p in steps:
        out.append(f'<rect x="{px(p["distance_m"]) - 3:.1f}" y="{py(p["min_signed_distance_m"]) - 3:.1f}" '
                   f'width="6" height="6" fill="none" stroke="#333"/>')
    out.append(f'<text x="{ml + 6}" y="{mt + 14}">red = contact, blue = miss, squares = bisection; '
               f'band = threshold interval</text>')
    out.append("</svg>")
    return "\n".join(out) + "\n"


def table(record: dict) -> str:
    rows = ["| d (m) | min signed (m) | at frame | contact | first contact frame | bone |",
            "|---|---|---|---|---|---|"]
    for p in sorted(record["grid"] + record["bisection"]["steps"], key=lambda p: p["distance_m"]):
        tag = "" if p in record["grid"] else " (bisection)"
        rows.append(f"| {p['distance_m']:.4f}{tag} | {p['min_signed_distance_m']:+.4f} | {p['min_frame']} | "
                    f"{'yes' if p['contact'] else 'no'} | {p['first_contact_frame'] or ''} | {p['bone'] or ''} |")
    return "\n".join(rows)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("json", nargs="?", type=Path, default=DEFAULT)
    ap.add_argument("--svg", type=Path, default=ROOT / "docs/product/figures/exp001_contact_threshold.svg")
    a = ap.parse_args()
    doc = json.loads(a.json.read_text(encoding="utf-8"))
    record = doc["experiments"][0]
    a.svg.parent.mkdir(parents=True, exist_ok=True)
    a.svg.write_text(svg(record), encoding="utf-8")
    print(table(record))
    print(f"\nthreshold {json.dumps(record['threshold'])}\nsha256 {record['sha256']}\nfigure {a.svg}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
