# assets/anatomy

| Folder | Content |
|--------|---------|
| `meshes/` | optional realistic bone meshes for the Blender addon (`README.md` there: what the fitter really does) |
| `manifests/` | asset manifests (contract PROPOSED, Decision 61); validator in `domain/assets/manifest.py` |
| `proxies/` | script-generated PROXY geometry for structures with no real mesh yet (ESTIMATE / PLACEHOLDER), with one manifest each |

## External references (outside the repo — never committed)

Third-party data stays outside the repository (Decision 46; attributions in `NOTICE`, Decision 76). Each folder
has its own download record with URL, size, SHA-256, licence and antivirus result.

| Reference | Where | Licence / use |
|-----------|-------|---------------|
| BodyParts3D 4.0, PART-OF tree (bones, skin) | `C:\DEV\Assets\BodyParts3D_4.0\download`, `extracted` | CC BY 4.0, per the licensor's current page (OBJ headers from 2013 say CC BY-SA 2.1 JP, disclosed in `NOTICE`); derived values published with attribution, meshes not committed (Decision 76) |
| BodyParts3D 4.0, IS-A tree (402 muscles, tendons, ligaments) | `C:\DEV\Assets\BodyParts3D_4.0\isa_download`, `isa_extracted` | same as above |
| human-atlas `atlas.json` (mesh → system classification) | `C:\DEV\Assets\BodyParts3D_4.0\human_atlas_meta` | code MIT, data CC BY 4.0 (derived from BodyParts3D) |
| Tentative mappings (bones, soft tissue) | `C:\DEV\Assets\BodyParts3D_4.0\mapping_*_tentative.tsv` | ESTIMATE, derived |
| ANSUR II (2012 US Army Anthropometric Survey) | `C:\DEV\Assets\ANSUR_II` | cleared for unlimited public release (MFR 2017) |
| Judo manuals (Hamada 2013 PDF; Cuenca 2014 SlideShare, read online) and the owner's YouTube playlist | `C:\DEV\Assets\References\Judo` | all rights reserved: cite, do not copy (visual reference only for the videos) |
| *Anatomía Clínica* (Pró), in the project Library | not on this PC | to cite by chapter / page when available |

Only names, IDs, numeric summaries and derived statistics enter the repo (e.g. `docs/audit/A18`–`A24`), never meshes.
