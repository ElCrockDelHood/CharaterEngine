"""Character Engine — Blender / UPBGE addon.

Installs an N-panel (``View3D > Sidebar > Character Engine``) that drives the pure-Python
domain from inside Blender:

* Body: pick a template (adult male/female, child, elderly; animals are listed but disabled
  until canonical data exists), stature and rest pose (T-pose by default) → canonical
  208-node armature.
* Tissues: proxy bone meshes (osteometric lengths), tendons + muscles (attachment
  catalogue), skin envelope. Realistic user meshes placed in ``assets/anatomy/meshes``
  are fitted automatically instead of proxies.
* Rig: IK/FK control layer (``HUMANOID_RIG``), foot roll, breathing control.
* Mocap: BVH import + retarget through a bone map (Mixamo / CMU / Rokoko).
* Wounds: click-to-wound raycast → tissue layers breached, severity, lethality.
* Export: glTF for Godot/UPBGE; Runtime tab: UPBGE gameplay scene set-up.

The package name on disk is ``addon`` (inside ``character_engine.infrastructure.blender``);
``scripts/install_blender_addon.py`` installs it as ``character_engine_blender``.
"""

bl_info = {
    "name": "Character Engine",
    "author": "Character Engine contributors",
    "version": (0, 3, 0),
    "blender": (4, 2, 0),
    "location": "View3D > Sidebar > Character Engine",
    "description": "Canonical 206-bone anatomy: bodies, tissues, IK/FK rig, mocap retarget, wounds, engine export",
    "category": "Rigging",
}

from . import _bootstrap  # noqa: E402  (must run before importing the domain)

_bootstrap.ensure_domain_importable()

from . import operators, panels, properties, runtime_upbge  # noqa: E402

_MODULES = (properties, operators, runtime_upbge, panels)


def register() -> None:
    for module in _MODULES:
        module.register()


def unregister() -> None:
    for module in reversed(_MODULES):
        module.unregister()


if __name__ == "__main__":  # pragma: no cover - run from Blender text editor
    register()
