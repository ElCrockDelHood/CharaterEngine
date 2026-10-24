# Realistic bone meshes (optional)

The Blender addon builds **proxy** long-bone meshes from Trotter maximum lengths
(shape = ESTIMATE). To replace a proxy with a sculpted or scanned bone:

1. Export a mesh in metres, long axis along the bone, origin at mid-shaft.
2. Name it with the **canonical base name**: `FEMUR.glb`, `HUMERUS.obj`, `TIBIA.gltf`, …
   (no `_L`/`_R`; both sides reuse the same asset, mirrored by the fitter).
3. Place the file in this folder. Tick **Prefer asset meshes** in the Character Engine
   panel and regenerate tissues.

Provenance of a fitted asset is `USER_INPUT`. Do not commit copyrighted scans.
