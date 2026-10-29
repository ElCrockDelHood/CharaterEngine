# Render engines on the reference PC — measurement (2026-10-29)

Question: can Blender 3.6.23 render with EEVEE and Cycles (GPU / CPU) on this PC, and how long does it take?
Measured here, not assumed. Used by the engine presets of `scripts/render_views.py` (Workbench stays the default;
EEVEE and Cycles are opt-in).

## Machine

| Item | Value |
|------|-------|
| CPU | Intel Core i3-3120M @ 2.50 GHz (Cycles uses its SSE4.1 kernels) |
| GPUs | Intel HD Graphics 4000 (driver 10.18.10.4358) + NVIDIA GeForce GT 740M (driver 23.21.13.8873 = 388.73), Optimus laptop |
| Blender | 3.6.23 portable, `C:\DEV\Tools\Blender\blender.exe`, background mode (`-b --factory-startup`) |

## 1. Simple scene (default cube, 640×360)

Script: a factory scene rendered once per engine (`Saved:` checked; images inspected).

| Engine | Device | Samples | Result | Time |
|--------|--------|---------|--------|------|
| Workbench | — | — | OK | 6.67 s (first render of the process, includes start-up) |
| EEVEE | OpenGL context of the process | 16 | OK | 14.32 s (first EEVEE render, includes shader compilation) |
| Cycles | CPU | 16 | OK | 28.14 s (first Cycles render, includes kernel loading) |
| Cycles | CUDA, GT 740M | 16 | OK | 19.16 s |
| Cycles, second pass, no denoising | CPU / CUDA / CUDA / CPU | 64 | OK | 16.77 / 20.90 / 15.92 / 13.87 s |

Device check (`--debug-cycles`): `Added device "GeForce GT 740M"`, `Testing for pre-compiled kernel …/kernel_sm_30.cubin`,
`Using precompiled kernel` — the CUDA render really ran on the GT 740M with Blender's precompiled sm_30 kernel.
OptiX: `initialization failed with error code 7804` (not available on this GPU/driver). HIP / oneAPI: no device.
OpenCL is not an option in Blender 3.6.

## 2. Character body (male 1.80 m T-pose + block dummy, cinematic preset lights, 1920×1080)

`python scripts/render_views.py --spec <stills-only spec> --engine <E> [--device <D>]` — front / side / back stills.
The first still of each process includes start-up / shader / kernel time.

| Engine | Device | Samples | front | side | back | Result |
|--------|--------|---------|-------|------|------|--------|
| WORKBENCH | — | — | 9.15 s | 2.18 s | 2.11 s | OK |
| EEVEE | OpenGL | 16 | 13.56 s | 5.88 s | 5.71 s | OK (soft shadows on the floor) |
| CYCLES | GPU (CUDA, GT 740M) | 32 | 201.14 s | 217.23 s | 155.06 s | OK |
| CYCLES | CPU | 32 | 253.65 s | 213.55 s | 207.30 s | OK |

Turntable (Workbench, 960×540, 24 frames): 1.36–1.89 s per frame; mp4 encode of 24 frames with Blender's
bundled FFmpeg: 2.9–4.2 s.

## Consequences for the presets

- **WORKBENCH** stays the default: seconds per still, no textures, no shaders, material colours only.
- **EEVEE** works in background mode on this PC; usable for previews (≈ 2.5× Workbench per still).
- **CYCLES** works on CPU and on the GT 740M through CUDA (three stills: GPU 573 s vs CPU 675 s, ≈ 15 % faster in total; per still from 2 % slower to 25 % faster). At 1920×1080 a still takes 2.5–4 minutes, so turntables
  in Cycles are impractical here; keep Cycles for single stills at low samples or small resolution.
- Device policy: `AUTO` uses CUDA when Cycles sees a device and otherwise falls back to CPU (recorded in
  `render.json` → `engine_used.note`); `GPU` is refused with a clear message when no CUDA device exists.
- Which GPU EEVEE used (Intel HD 4000 or GT 740M under Optimus) was not measured.
