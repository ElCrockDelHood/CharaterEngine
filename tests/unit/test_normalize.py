"""Mesh normalizer (domain/assets/normalize.py): canonical axes, target height, ground and centring."""

import pytest

from character_engine.domain.anatomy.reference.source import ProvenanceState
from character_engine.domain.assets import apply, axis_rotation, normalization


def _det(m):
    return (m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1]) - m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0])
            + m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0]))


@pytest.mark.parametrize("up, forward", [("+Z", "-Y"), ("+Y", "+Z"), ("+Y", "-Z"), ("+Z", "+X"), ("-X", "+Y")])
def test_rotation_is_proper_and_maps_axes(up, forward):
    from character_engine.domain.assets.normalize import AXES, _apply3
    r = axis_rotation(up, forward)
    assert _det(r) == pytest.approx(1.0)
    assert _apply3(r, AXES[up]) == pytest.approx((0.0, 0.0, 1.0))
    assert _apply3(r, AXES[forward]) == pytest.approx((0.0, -1.0, 0.0))


def test_identity_for_canonical_axes():
    r = axis_rotation("+Z", "-Y")
    for row, expected in zip(r, ((1, 0, 0), (0, 1, 0), (0, 0, 1))):
        assert row == pytest.approx(expected)


def test_gltf_character_in_centimetres_becomes_canonical_metres():
    # glTF/FBX style: Y-up, +Z forward, 180 units tall, standing at y = 10
    pts = [(-20.0, 10.0, -10.0), (20.0, 190.0, 10.0), (0.0, 100.0, 30.0)]   # nose at +Z (front)
    n = normalization(pts, 1.80, up="+Y", forward="+Z")
    out = [apply(n, p) for p in pts]
    assert min(p[2] for p in out) == pytest.approx(0.0)
    assert max(p[2] for p in out) == pytest.approx(1.80)
    assert n.scale == pytest.approx(0.01)
    nose = out[2]
    assert nose[1] < 0                       # front is now -Y
    xs = [p[0] for p in out]
    assert (min(xs) + max(xs)) / 2 == pytest.approx(0.0)
    assert n.provenance == ProvenanceState.ESTIMATE


@pytest.mark.parametrize("kwargs", [{"up": "+Z", "forward": "+Z"}, {"up": "+W", "forward": "-Y"}])
def test_bad_axes_rejected(kwargs):
    with pytest.raises(ValueError):
        normalization([(0, 0, 0), (0, 0, 1)], 1.0, **kwargs)


def test_degenerate_inputs_rejected():
    with pytest.raises(ValueError):
        normalization([], 1.0)
    with pytest.raises(ValueError):
        normalization([(0, 0, 0), (1, 1, 0)], 1.0)
    with pytest.raises(ValueError):
        normalization([(0, 0, 0), (0, 0, 1)], 0.0)
