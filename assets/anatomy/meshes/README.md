# Realistic bone meshes (optional)

The Blender addon builds **proxy** long-bone meshes from Trotter maximum lengths
(shape = ESTIMATE). To replace a proxy with a sculpted or scanned bone:

1. Export a mesh in metres, with the bone's length along its longest bounding-box axis.
2. Name it with the **canonical base name**: `FEMUR.glb`, `HUMERUS.obj`, `TIBIA.gltf`, …
   (no `_L`/`_R`).
3. Place the file in this folder. Tick **Prefer asset meshes** in the Character Engine
   panel and regenerate tissues.

## What the fitter really does today (`_fit_asset` in `infrastructure/blender/addon/build.py`)

- Imports the same file once for each side (`_L` and `_R`).
- Scales it uniformly so its **longest bounding-box axis** equals the osteometric length
  (or the joint segment length if there is none).
- Rotates that axis onto the bone's head → tail direction and puts the mesh's origin at the
  midpoint of the segment.
- Gives every vertex 100 % weight on that bone.

It does **not** mirror the opposite side: the left copy keeps the shape of the file as it is,
so a right femur also appears, unmirrored, on the left. Roll (rotation about the long axis) is
not defined either, and there are no landmarks or reports of fitting error. The correct
mirror, roll and registration by landmarks come in phase F2 of
`docs/architecture/ASSET_FITTING_PROPOSAL.md`; assets will then carry a manifest
(`assets/anatomy/manifests/`, contract PROPOSED).

Provenance of a fitted asset is `USER_INPUT`. Do not commit copyrighted scans.
