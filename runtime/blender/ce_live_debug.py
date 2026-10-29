"""Live visual debug: one D1 fight in an open Blender window, driven by command files, with captures to PNG.

    blender --factory-startup --python runtime/blender/ce_live_debug.py -- \
        --lib ".../UAL1_Standard.glb" --lib ".../UAL2_Standard.glb" \
        --attack Sword_Attack --stance Sword_Idle --distance 0.9

Opens the Blender UI (no ``-b``) so a person watches the scene while a script (``scripts/live_debug.py``) sends
commands. Builds the two D1-2 fighters exactly as ``ce_reaction_library.py`` does, plays the attack against the
stance at the given spacing and, when the D1 library has a body hit for that entry, layers the same reactions
(defender from contact + 1, attacker recovery) with the same blend-in frames.

Every frame is measured once on load (signed sabre-to-capsule distance, nearest canonical bone); a marker sphere
follows the closest blade point (red = penetration, green = gap) and a HUD in the 3D view prints frame, gap and
bone. Timeline markers name the first contact and the reaction start. Measurements only: no physics, no energy.

Command bridge (``logs/live_debug``): a timer reads ``inbox/<id>.json`` and writes ``outbox/<id>.json``.
Commands: ``info``, ``frame`` {frame}, ``shot`` {frame?, views?, tag?}, ``screen`` (screenshot of the 3D view
the person sees), ``load`` {attack?, stance?, distance?}, ``play`` / ``stop``, ``video`` {tag?, slow?, window?,
bullet?} (MP4 with a moving camera and slow motion at the contact), ``eval`` {code} (local debugging).
The fight loops in the 3D view on open. ``--video TAG`` with ``blender -b`` renders the MP4 and exits.
Shots are Workbench renders from fixed cameras; Cycles never runs here (Decision: EEVEE/Workbench to iterate).
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
import traceback
from pathlib import Path

import bpy  # type: ignore
from mathutils import Vector  # type: ignore

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ce_fight_mockup as mock  # noqa: E402
import ce_reaction_library as lib  # noqa: E402

ROOT = mock.ROOT
LIVE = ROOT / "logs" / "live_debug"
INBOX, OUTBOX, SHOTS = LIVE / "inbox", LIVE / "outbox", LIVE / "shots"
LIBRARY = ROOT / "builds" / "reactions" / "reaction_library_d1.json"
POLL_S = 0.5
VIEWS = ("side", "side_l", "front", "back", "top", "contact")

STATE = {"table": {}, "contact": None, "entry": None, "attack": None, "stance": None, "distance": None,
         "sources": {}, "range": (1, 1), "build": None, "hud": None}


def log(msg: str) -> None:
    print(f"[live] {msg}", flush=True)


# ---------------------------------------------------------------- scene

def library_entry(attack: str, stance: str, distance: float):
    if not LIBRARY.exists():
        return None
    doc = json.loads(LIBRARY.read_text(encoding="utf-8"))
    want = f"{attack}__vs__{stance}__{distance:.1f}m"
    return next((e for e in doc["entries"] if e["id"] == want), None)


def marker():
    obj = bpy.data.objects.get("LIVE_contact_marker")
    if obj is None:
        me = bpy.data.meshes.new("LIVE_contact_marker")
        obj = bpy.data.objects.new("LIVE_contact_marker", me)
        bpy.context.scene.collection.objects.link(obj)
        import bmesh  # type: ignore
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=12, v_segments=8, radius=0.04)
        bm.to_mesh(me)
        bm.free()
        for name, col in (("LIVE_hit", (1.0, 0.05, 0.05, 1.0)), ("LIVE_gap", (0.1, 0.9, 0.2, 1.0))):
            mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
            mat.diffuse_color = col
            me.materials.append(mat)
        obj["ce_role"] = "live_debug"
    return obj


def measure_all(scene, attacker, defender, f0: int, f1: int) -> dict:
    """frame -> {gap, segment, bone, point}; the same measure the library uses (ce_fight_mockup)."""
    build = STATE["build"]
    table = {}
    for fr in range(f0, f1 + 1):
        scene.frame_set(fr)
        bpy.context.view_layer.update()
        gap, seg, point = mock.closest_sabre_contact(attacker, defender)
        bone, _ = build.nearest_canonical_bone(defender, point, posed=True)
        table[fr] = {"gap_m": round(gap, 4), "segment": seg, "bone": bone, "point": [round(c, 4) for c in point]}
    return table


def load_fight(attack: str, stance: str, distance: float) -> dict:
    scene = bpy.context.scene
    props = scene.character_engine
    sources = STATE["sources"]
    attacker, defender = bpy.data.objects["CE_Fighter_B"], bpy.data.objects["CE_Fighter_A"]
    lib.play_back_stance(defender, attacker)
    lib.play(props, defender, sources[stance], stance)
    f0, f1, _ = lib.play(props, attacker, sources[attack], attack)
    attacker.location = (0.0, -distance, 0.0)
    entry = library_entry(attack, stance, distance)
    end = f1
    contact = None
    rp = (entry or {}).get("reaction_playback")
    if rp:
        contact = rp["start_frame"]
        _, d_len = lib.layer_reaction(props, sources, defender, rp["clip"], contact + 1, rp["blend_in_frames"])
        end = max(end, contact + 1 + d_len)
        att = rp.get("attacker_reaction")
        if att:
            _, a_len = lib.layer_reaction(props, sources, attacker, att["clip"], contact + 1, att["blend_in_frames"])
            end = max(end, contact + 1 + a_len)
    scene.frame_start, scene.frame_end = f0, end
    STATE.update(attack=attack, stance=stance, distance=distance, entry=entry, range=(f0, end))
    STATE["table"] = measure_all(scene, attacker, defender, f0, end)
    first = next((f for f, m in sorted(STATE["table"].items()) if m["gap_m"] <= 0.0), None)
    STATE["contact"] = contact if contact is not None else first
    scene.timeline_markers.clear()
    if first is not None:
        scene.timeline_markers.new(f"contacto {STATE['table'][first]['bone']}", frame=first)
    if rp:
        scene.timeline_markers.new(f"reaccion {rp['clip']}", frame=contact + 1)
    scene.frame_set(STATE["contact"] or f0)
    log(f"loaded {attack} vs {stance} at {distance} m: frames {f0}-{end}, first contact {first}, "
        f"library event {(entry or {}).get('event')}")
    return info()


def on_frame(scene, *_):
    m = STATE["table"].get(scene.frame_current)
    obj = bpy.data.objects.get("LIVE_contact_marker")
    if m is None or obj is None:
        return
    obj.location = m["point"]
    for poly in obj.data.polygons:
        poly.material_index = 0 if m["gap_m"] <= 0.0 else 1


def hud():
    import blf  # type: ignore
    scene = bpy.context.scene
    m = STATE["table"].get(scene.frame_current)
    lines = [f"{STATE['attack']} vs {STATE['stance']}  {STATE['distance']} m",
             f"cuadro {scene.frame_current}   contacto en {STATE['contact']}"]
    if m:
        state = "PENETRA" if m["gap_m"] <= 0.0 else "separado"
        lines.append(f"sable-cuerpo {m['gap_m'] * 100:+.1f} cm ({state})  hueso {m['bone']}  capsula {m['segment']}")
    blf.size(0, 16)
    hit = bool(m) and m["gap_m"] <= 0.0
    for i, text in enumerate(lines):
        blf.color(0, 1.0, 0.3 if i == 2 and hit else 1.0, 0.3 if i == 2 and hit else 1.0, 1.0)
        blf.position(0, 20, 60 + 22 * (len(lines) - 1 - i), 0)
        blf.draw(0, text)


# ---------------------------------------------------------------- captures

def camera(name: str, loc, target) -> object:
    cam = bpy.data.objects.get(name) or bpy.data.objects.new(name, bpy.data.cameras.new(name))
    if cam.name not in bpy.context.scene.collection.objects:
        bpy.context.scene.collection.objects.link(cam)
    cam.data.lens = 35.0
    cam.location = loc
    cam.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    cam["ce_role"] = "live_debug"
    return cam


def view_camera(view: str):
    """Fixed cameras around the pair. Defender at the origin, attacker at -Y (distance)."""
    d = STATE["distance"] or 1.0
    mid = (0.0, -d / 2, 1.0)
    if view == "contact":
        m = STATE["table"].get(bpy.context.scene.frame_current) or {"point": mid}
        p = Vector(m["point"])
        return camera("LIVE_cam_contact", p + Vector((1.1, -0.35, 0.25)), p)
    spots = {"side": (4.2, -d / 2, 1.3), "side_l": (-4.2, -d / 2, 1.3),
             "front": (1.6, -d - 2.6, 1.5),            # over the attacker's shoulder, at the defender's front
             "back": (-1.0, 3.2, 1.6),                 # behind the defender
             "top": (0.01, -d / 2, 5.5)}
    return camera(f"LIVE_cam_{view}", spots[view], mid)


def shot(views, frame=None, tag: str = "") -> list:
    scene = bpy.context.scene
    if frame is not None:
        scene.frame_set(int(frame))
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light, scene.display.shading.color_type = "STUDIO", "MATERIAL"
    scene.render.resolution_x, scene.render.resolution_y = 960, 540
    keep = scene.camera
    out = []
    SHOTS.mkdir(parents=True, exist_ok=True)
    for view in views:
        scene.camera = view_camera(view)
        path = SHOTS / f"{tag or 'shot'}_f{scene.frame_current:03d}_{view}.png"
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        out.append(str(path))
    scene.camera = keep
    return out


def screen(tag: str = "") -> str:
    """Screenshot of the largest 3D view, as the person sees it (HUD included)."""
    win = bpy.context.window_manager.windows[0]
    area = max((a for a in win.screen.areas if a.type == "VIEW_3D"), key=lambda a: a.width * a.height)
    SHOTS.mkdir(parents=True, exist_ok=True)
    path = SHOTS / f"{tag or 'screen'}_f{bpy.context.scene.frame_current:03d}_viewport.png"
    region = next(r for r in area.regions if r.type == "WINDOW")
    with bpy.context.temp_override(window=win, screen=win.screen, area=area, region=region):
        bpy.ops.screen.screenshot_area(filepath=str(path))
    return str(path)


def caption():
    """3D text parented to the video camera: clip, frame, sabre-to-body gap (shows in Workbench renders)."""
    obj = bpy.data.objects.get("LIVE_caption")
    if obj is None:
        obj = bpy.data.objects.new("LIVE_caption", bpy.data.curves.new("LIVE_caption", "FONT"))
        bpy.context.scene.collection.objects.link(obj)
        mat = bpy.data.materials.get("LIVE_caption") or bpy.data.materials.new("LIVE_caption")
        mat.diffuse_color = (1.0, 1.0, 1.0, 1.0)
        obj.data.materials.append(mat)
        obj.data.size = 0.032
        obj["ce_role"] = "live_debug"
    return obj


def orbit(center, radius: float, height: float, angle: float):
    return Vector((center[0] + radius * math.cos(angle), center[1] + radius * math.sin(angle), height))


def video(tag: str = "", slow: float = 4.0, window: int = 6, bullet: int = 72, fps: int = 30) -> dict:
    """MP4 of the whole fight: orbiting camera, slow motion (subframes) around the first contact with a push-in
    on the contact point, then a bullet-time turn around the frozen contact frame. Workbench, then encoded by
    Blender's own FFMPEG through a temporary sequencer scene (no external tools)."""
    scene = bpy.context.scene
    attacker, defender = bpy.data.objects["CE_Fighter_B"], bpy.data.objects["CE_Fighter_A"]
    f0, f1 = STATE["range"]
    c = STATE["contact"]
    fc = (STATE["entry"] or {}).get("first_contact") or {}
    tc = float(fc.get("time", c)) if c is not None else None          # schema 6: contact time between frames
    times = []
    t = float(f0)
    while t <= f1 + 1e-6:
        near = c is not None and abs(t - tc) <= window
        times.append((t, near))
        t += 1.0 / slow if near else 1.0
    d = STATE["distance"] or 1.0
    mid = Vector((0.0, -d / 2, 1.05))
    hit = Vector(fc["entry_point"]) if fc.get("entry_point") else Vector(STATE["table"][c]["point"]) if c is not None else mid
    plan = []
    for i, (t, near) in enumerate(times):
        a = math.radians(-20.0 + 80.0 * i / max(1, len(times) - 1))
        if near:
            k = 1.0 - abs(t - tc) / window                       # 0 at the edges of the window, 1 at contact
            loc = orbit(mid, 3.6, 1.4, a).lerp(orbit(hit, 2.3, hit.z + 0.5, a), k)
            plan.append((t, loc, mid.lerp(hit, k), f"x{slow:g} camara lenta"))
        else:
            plan.append((t, orbit(mid, 3.6, 1.4, a), mid, ""))
    for j in range(bullet if c is not None else 0):
        a = math.radians(60.0 + 360.0 * j / bullet)
        plan.append((tc, orbit(hit, 2.2, hit.z + 0.5, a), hit, "contacto congelado"))

    folder = SHOTS / f"video_{tag or 'clip'}"
    folder.mkdir(parents=True, exist_ok=True)
    for old in folder.glob("*.png"):
        old.unlink()
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light, scene.display.shading.color_type = "STUDIO", "MATERIAL"
    scene.render.resolution_x, scene.render.resolution_y = 960, 540
    scene.render.image_settings.file_format = "PNG"
    keep_cam, keep_frame = scene.camera, scene.frame_current
    cam = camera("LIVE_cam_video", plan[0][1], plan[0][2])
    text = caption()
    text.parent = cam
    text.location, text.rotation_euler = (-0.48, 0.2, -1.0), (0.0, 0.0, 0.0)   # top left of a 35 mm 16:9 frame
    scene.camera = cam
    mk = marker()
    gaps = []
    for n, (t, loc, target, note) in enumerate(plan, start=1):
        scene.frame_set(int(math.floor(t)), subframe=t - math.floor(t))
        bpy.context.view_layer.update()
        gap, seg, point = mock.closest_sabre_contact(attacker, defender)
        mk.location = point
        for poly in mk.data.polygons:
            poly.material_index = 0 if gap <= 0.0 else 1
        cam.location = loc
        cam.rotation_euler = (target - loc).to_track_quat("-Z", "Y").to_euler()
        text.data.body = (f"{STATE['attack']} vs {STATE['stance']}  {d} m\n"
                          f"cuadro {t:5.2f}   sable-cuerpo {gap * 100:+5.1f} cm  {seg}\n{note}")
        scene.render.filepath = str(folder / f"{n:04d}.png")
        bpy.ops.render.render(write_still=True)
        gaps.append(round(gap, 4))
    scene.camera = keep_cam
    text.parent = None
    text.hide_render = text.hide_viewport = True
    scene.frame_set(keep_frame)

    enc = bpy.data.scenes.new("LIVE_encode")
    enc.sequence_editor_create()
    files = sorted(folder.glob("*.png"))
    strip = enc.sequence_editor.sequences.new_image("frames", str(files[0]), channel=1, frame_start=1)
    for f in files[1:]:
        strip.elements.append(f.name)
    enc.frame_start, enc.frame_end = 1, len(files)
    enc.render.fps = fps
    enc.render.resolution_x, enc.render.resolution_y = 960, 540
    enc.render.resolution_percentage = 100
    enc.render.image_settings.file_format = "FFMPEG"
    enc.render.ffmpeg.format, enc.render.ffmpeg.codec = "MPEG4", "H264"
    enc.render.ffmpeg.constant_rate_factor = "HIGH"
    out = SHOTS / f"{tag or 'clip'}.mp4"
    enc.render.filepath = str(out)
    enc.render.use_file_extension = False
    bpy.ops.render.render(animation=True, scene=enc.name)
    bpy.data.scenes.remove(enc)
    return {"file": str(out), "frames": len(files), "seconds": round(len(files) / fps, 1), "contact_frame": c,
            "slow_motion": f"x{slow:g} within +-{window} frames of contact", "bullet_time_frames": len(plan) - len(times),
            "min_gap_m": min(gaps)}


def autoplay():
    """Loop the fight in the 3D view (the person watches it move)."""
    win = bpy.context.window_manager.windows[0]
    if not win.screen.is_animation_playing:
        with bpy.context.temp_override(window=win, screen=win.screen):
            bpy.ops.screen.animation_play()


# ---------------------------------------------------------------- bridge

def info() -> dict:
    scene = bpy.context.scene
    f = scene.frame_current
    entry = STATE["entry"] or {}
    return {"attack": STATE["attack"], "stance": STATE["stance"], "distance_m": STATE["distance"],
            "range": list(STATE["range"]), "frame": f, "at_frame": STATE["table"].get(f),
            "contact_frame": STATE["contact"], "library_event": entry.get("event"),
            "library_first_contact": entry.get("first_contact"), "library_reaction": entry.get("reaction"),
            "contact_frames": [k for k, m in sorted(STATE["table"].items()) if m["gap_m"] <= 0.0],
            "gaps_m": {k: m["gap_m"] for k, m in sorted(STATE["table"].items())}}


def run(cmd: dict):
    kind = cmd.get("cmd")
    scene = bpy.context.scene
    if kind == "info":
        return info()
    if kind == "frame":
        scene.frame_set(int(cmd["frame"]))
        return info()
    if kind == "shot":
        return {"files": shot(cmd.get("views") or ["side", "contact"], cmd.get("frame"), cmd.get("tag", "")),
                "at_frame": STATE["table"].get(scene.frame_current), "frame": scene.frame_current}
    if kind == "screen":
        return {"file": screen(cmd.get("tag", "")), "frame": scene.frame_current}
    if kind == "load":
        return load_fight(cmd.get("attack", STATE["attack"]), cmd.get("stance", STATE["stance"]),
                          float(cmd.get("distance", STATE["distance"])))
    if kind in ("play", "stop"):
        playing = bpy.context.screen.is_animation_playing if bpy.context.screen else False
        if playing != (kind == "play"):
            win = bpy.context.window_manager.windows[0]
            with bpy.context.temp_override(window=win, screen=win.screen):
                bpy.ops.screen.animation_play()
        return {"playing": kind == "play"}
    if kind == "video":
        win = bpy.context.window_manager.windows[0] if bpy.context.window_manager.windows else None
        if win and win.screen.is_animation_playing:
            with bpy.context.temp_override(window=win, screen=win.screen):
                bpy.ops.screen.animation_cancel(restore_frame=False)
        return video(cmd.get("tag", ""), float(cmd.get("slow", 4.0)), int(cmd.get("window", 6)),
                     int(cmd.get("bullet", 72)))
    if kind == "eval":
        scope = {"bpy": bpy, "STATE": STATE, "Vector": Vector}
        exec(cmd["code"], scope)
        return {"result": repr(scope.get("result"))}
    raise ValueError(f"unknown command {kind!r}")


def poll():
    for path in sorted(INBOX.glob("*.json")):
        try:
            cmd = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue                        # still being written; next tick
        path.unlink(missing_ok=True)
        t0 = time.time()
        try:
            reply = {"ok": True, "result": run(cmd)}
        except Exception as exc:  # noqa: BLE001 - reported back to the caller
            reply = {"ok": False, "error": f"{type(exc).__name__}: {exc}", "trace": traceback.format_exc()}
        reply.update(cmd=cmd, seconds=round(time.time() - t0, 2))
        (OUTBOX / path.name).write_text(json.dumps(reply, indent=1), encoding="utf-8")
        log(f"{cmd.get('cmd')} -> {'ok' if reply['ok'] else reply['error']} ({reply['seconds']} s)")
    return POLL_S


def frame_viewport():
    """Look at the pair from the side in every 3D view, solid shading with material colours."""
    for win in bpy.context.window_manager.windows:
        for area in win.screen.areas:
            if area.type != "VIEW_3D":
                continue
            space = area.spaces.active
            space.shading.type, space.shading.color_type = "SOLID", "MATERIAL"
            r3d = space.region_3d
            r3d.view_perspective = "PERSP"
            d = STATE["distance"] or 1.0
            r3d.view_location = (0.0, -d / 2, 1.0)
            r3d.view_distance = 3.2
            r3d.view_rotation = Vector((1.0, 0.0, 0.25)).normalized().to_track_quat("Z", "Y")   # from +X


def main() -> int:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--lib", type=Path, action="append", required=True, help="glTF animation library (repeatable)")
    ap.add_argument("--attack", default="Sword_Attack")
    ap.add_argument("--stance", default="Sword_Idle")
    ap.add_argument("--distance", type=float, default=0.9, help="spacing in metres (ESTIMATE)")
    ap.add_argument("--video", metavar="TAG", help="render the MP4 and exit (use with blender -b)")
    a = ap.parse_args(argv)

    for d in (INBOX, OUTBOX, SHOTS, LIVE / "from_mariano"):
        d.mkdir(parents=True, exist_ok=True)
    for stale in [*INBOX.glob("*.json"), LIVE / "READY"]:
        stale.unlink(missing_ok=True)

    for obj in list(bpy.data.objects):     # factory cube, light and camera; keep the UI as it is
        bpy.data.objects.remove(obj, do_unlink=True)
    STATE["build"] = build = mock.load_addon()
    props = bpy.context.scene.character_engine
    STATE["sources"] = sources = lib.clip_sources(a.lib)
    mock.make_fighter(props, build, "CE_Fighter_A", sources[a.stance], a.stance)       # defender
    attacker = mock.make_fighter(props, build, "CE_Fighter_B", sources[a.attack], a.attack)
    attacker.rotation_euler = (0.0, 0.0, math.pi)
    bpy.ops.mesh.primitive_plane_add(size=12.0)
    marker()
    load_fight(a.attack, a.stance, a.distance)
    if a.video:
        log(f"video {json.dumps(video(a.video))}")
        return 0
    bpy.app.handlers.frame_change_post.append(on_frame)
    on_frame(bpy.context.scene)
    STATE["hud"] = bpy.types.SpaceView3D.draw_handler_add(hud, (), "WINDOW", "POST_PIXEL")
    bpy.app.timers.register(lambda: (frame_viewport(), autoplay(), None)[2], first_interval=1.0)
    bpy.app.timers.register(poll, first_interval=1.5, persistent=True)
    (LIVE / "READY").write_text(json.dumps(info()), encoding="utf-8")
    log(f"ready; commands in {INBOX}")
    return 0


if __name__ == "__main__":
    main()
