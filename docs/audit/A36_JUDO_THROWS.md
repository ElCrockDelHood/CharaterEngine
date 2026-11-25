# A36 — Judo / jujutsu: grip, unbalancing, throw, fall and breakfall

Status: model ESTIMATE / ASSUMED; key poses **PLACEHOLDER** (block-out). Additive and opt-in (Decision 87): no existing
move, table, clip or hash changes. Code: `domain/physics/judo.py`, `domain/animation/judo_clips.py`; tests:
`tests/unit/test_judo.py`; tool: `scripts/judo_contact_sheet.py`. Proposal: `docs/architecture/JUDO_THROWS_PROPOSAL.md`.
Spanish: `A36_JUDO_THROWS.es.md`.

Owner, 2026-11-16: the five throws of the proposal, movement generated from the model and polished by hand, and "look for
sequenced images and make the movement from them".

## 1. Model (`physics/judo.py`)

**Kumikata.** A grip is a hand of tori on a point of uke (sleeve, lapel, collar, belt, wrist, neck, waist, armpit),
anchored to a game bone. No grip strength is modelled: none was read.

**Kuzushi.** Uke's centre of mass (de Leva fractions on the game bones, segment centres at mid-length, ESTIMATE) against
the feet on the ground (heel, ankle, ball, toe tip; the heel 5 cm behind the ankle is ASSUMED because the game rig has no
heel bone). An impulse `J` moves the centre of mass at `v = J / m`; as an inverted pendulum it travels `v / sqrt(g / h)`
before it can be stopped without a step. The margin is the distance left to the edge of the support; at or below zero,
balance is broken. Standing naturally, 75 kg, 1.80 m:

| Direction | Margin cm | Impulse to break N·s |
|---|---|---|
| forward | 23.7 | 55.5 |
| forward corner | 20.1 | 47.0 |
| side | 7.3 | 17.1 |
| back corner | 9.0 | 21.1 |
| back | 5.4 | 12.7 |

Cross-check: the engine's step threshold (`P_STEP_N_S`, A16) is 25 N·s, from pull tests that gave 18–20 N·s front and back
and 28 N·s sideways in adults of about 80. The model is in the same range but more uneven: forward is stronger and back
weaker than those tests, where people resist with their muscles and not only with their feet. Read it as an ordering.

A reaped or swept foot leaves the support, and that is why leg techniques need so little pull:

| Throw | Kuzushi | Both feet N·s | At kake N·s |
|---|---|---|---|
| Seoi-nage | forward | 55.5 | 55.5 |
| O-goshi | forward | 55.5 | 55.5 |
| O-soto-gari | back right | 21.1 | 0 (right leg reaped) |
| O-uchi-gari | back left | 21.1 | 0 (left leg reaped) |
| De-ashi-barai | right | 17.1 | 0 (right foot swept) |

A throw attempted without enough impulse returns `thrown: false` with both margins: the opening for a counter. Tori's own
pull (20 / 40 / 60 N·s) is ASSUMED: no kuzushi force was read.

**Fall.** `FallLanding` (A17) from each throw's release height (ASSUMED):

| Throw | Release height m | Speed m/s | Fall energy J | Trunk J |
|---|---|---|---|---|
| Seoi-nage | 1.20 | 4.60 | 795 | 345 |
| O-goshi, O-soto-gari, O-uchi-gari | 0.99 | 4.13 | 640 | 278 |
| De-ashi-barai | 0.75 | 3.52 | 464 | 201 |

**Ukemi.** Quality = skill × (1 − fatigue), correct at 0.5 or more (ASSUMED rule). A correct breakfall keeps the head off
the mat. Head loads are the measured ones (A17, proposal §5), never computed:

| Throw | No ukemi rad/s² | With ukemi rad/s² |
|---|---|---|
| Seoi-nage | 1890 (dummy) | 276 (novices) |
| O-soto-gari | 4573 (dummy) | 679 (expert) |
| O-uchi-gari | 2176 (dummy) | 402 (novices) |
| O-goshi, De-ashi-barai | not read: `null` | not read: `null` |

Output: `ThrowEvent.to_dict()`, schema `ce-throw/1` (grips, both kuzushi margins, fall, ukemi, head, provenance per block).

## 2. Key poses (`animation/judo_clips.py`)

Seven keys per throw (kumikata, kuzushi, tsukuri, kake, fall, landing, end) for tori and uke, 61–80 frames at 60 fps
(1.0–1.3 s; timing ASSUMED). A
key is written as bone directions in the fighter's own frame, a root transform (place, turns of the whole body, on the
ground or at a height) and reaches: a hand or a foot placed on a point of the other fighter with two-bone IK. Output:
`clip_reference()`, schema `ce-judo-clips/1`: per key and fighter the root transform and the rest-frame bone rotations, in
the convention of `souls_clips`.

Checked by the tests: bones point where asked and keep their length; nobody goes through the floor; gripping hands and
the reaping leg are within 15 cm of their target from kumikata to kake (most are at 0; the lapel hand at the first key is
at 9 cm, arm fully stretched); uke starts balanced, is unbalanced at kake by the model of §1, and ends lying; tori ends
standing.

Contact sheets: `python scripts/judo_contact_sheet.py` writes `builds/judo/<throw>.png` (side view over front view; tori
blue, uke red, right limbs darker) and `builds/judo/judo_clips.json`.

## 2b. In-betweens and the Blender bake

Every frame between two keys is solved, not just interpolated (`judo_clips.solve_frames`): bone rotations and the root
are interpolated with quaternion slerp along the short arc, eased with a smoothstep (ASSUMED timing), and every grip held
at both keys is re-solved by IK on that frame, so the hands stay on the sleeve and lapel while both bodies move. A grip that moves to another point between two
keys (the right hand going from the lapel to the armpit in seoi-nage) is interpolated, not snapped. A
fighter on the mat at both keys stays on it; an airborne frame that would dip under the mat is lifted. `frame_table`
gives, per frame and fighter, the armature object transform and the rest-frame bone rotations.

`python scripts/bake_judo_clips.py` writes `builds/judo/judo_frames.json` (schema `ce-judo-frames/1`) and runs
`runtime/blender/ce_bake_judo_clips.py` in Blender 3.6: two 66-bone game armatures `CE_TORI` and `CE_UKE` with the block
body, one action per throw and fighter keyed on every frame (`seoi_nage.tori`, `seoi_nage.uke`, ...), saved to
`builds/judo/judo_throws.blend`. Blender's posed probe points (pelvis, head, hands, feet) match the Python solve within
0.02 mm on every frame of the five throws. It also renders the keys in Workbench, side and three-quarter views, to
`builds/judo/<throw>_blender.png`. About 3 minutes of Python solving and 1 minute of Blender on the owner's laptop.

Fastest point per throw (head, hands, feet), checked by the tests against 18 m/s: the thrown body's feet as it turns
over tori in seoi-nage and o-goshi, 17.5 m/s; tori's reaping foot in o-uchi-gari, 16.8 m/s; o-soto-gari 14.6 m/s;
de-ashi-barai 14.5 m/s. The fastest kick measured is 14.3 m/s (Vagner 2023, A17): these are at or a little above it,
plausible for a body turning over another, but not measured.

## 2c. The bodies do not go into each other (clearance)

Owner, 2026-11-24: "que las manifestaciones no se atraviesen es muy importante". Measured on the block-body capsules
(`domain/animation/body_clearance.py`; fingers and small metacarpals left out): before this, the key poses went up to
19 cm into each other (o-goshi at kake) and the crossed forearms of the grip about 4 cm.

What changed in `judo_clips.py`:

* **Grips on the surface.** A grip point is pushed out of the target capsule by the target radius plus the gripping
  end's radius (`_target_point`), so a hand rests on the sleeve instead of inside it. A gripping hand and forearm (or a
  hooking shin) may press 1 cm into the other body (`GI_THICKNESS_M`, ASSUMED: the gi).
* **Clearance search** (`clear_key`): while anything goes in deeper than 3 mm, try moves on the deepest overlaps and
  keep the one that lowers the cost most -- move uke as one body (along the summed push, or along one pair), turn an
  elbow or knee about its grip line (the grip stays), tilt a free limb, a hand, a foot or the head, and after kake let go
  of a hold that is already slipping. When no single move helps, two in a row are tried. Cost: 10 × overlap + grip
  slip + 4 × under the mat + 3 × frame-to-frame jump beyond 9 m/s + 4 × uke moved more than 6 cm from its authored
  place. All weights and thresholds ASSUMED; accepted result: under 5 mm (`CLEAR_M`), a touch between proxies.
* **In-betweens**: each frame starts from the fixes of the frame before, faded out by the next key, and is cleared with
  the jump and the next key in the cost, so a fix does not snap.
* **Authored changes** where the search alone could not: hips 31 cm apart in hip throws (the pelvis capsules touch);
  o-goshi's waist arm slides in at tsukuri and grips at kake, on the near side of uke's back; hikite pulls the sleeve to
  the front in hip throws; uke's drawn arm goes over tori's right shoulder; two breakdown keys in hip throws (uke lifted
  onto the hips, then over high); the de-ashi-barai sole on the outside of the ankle; the o-uchi-gari reap follows uke
  down; the hip throws' waist hold stays on until the landing.

Result over every frame (`python scripts/bake_judo_clips.py` prints it):

| Throw | Frames | Over 5 mm | Worst | Fastest point |
|---|---|---|---|---|
| Seoi-nage | 81 | 5 | 4.7 cm | 41.5 m/s |
| O-goshi | 81 | 4 | 3.9 cm | 31.5 m/s |
| O-soto-gari | 71 | 0 | 0.3 cm | 14.9 m/s |
| O-uchi-gari | 71 | 1 | 0.8 cm | 27.2 m/s |
| De-ashi-barai | 62 | 0 | 0.3 cm | 14.8 m/s |

Every key pose of the five throws is under 5 mm (test). **Open:** in seoi-nage and o-goshi uke still goes 4–5 cm into
tori in 4–5 frames while being loaded over the back, and in those throws and o-uchi-gari a hand or foot moves 27–42 m/s
for a frame where the search turns a limb fast. A search on top of interpolated keys has reached its limit there; the
next step is a solver that moves both bodies together frame by frame under the constraints (contact, grip, no jump), or
more authored breakdown keys for the loading.

The bake keeps the Blender ↔ Python parity (0.03 mm). The search makes the solve slow on the owner's laptop: about
2–3 minutes per throw, cached per process; the judo tests take about 4 minutes.

## 3. References for the poses, and their limit

Read: the technique descriptions of the five throws in Wikipedia (kuzushi, tsukuri and kake of o-goshi; the stepping and
reaping legs of o-soto-gari; the swept foot of de-ashi-barai), each with a single illustration. Found but not used as
frame sources: a Nage-no-Kata document with numbered photo sequences (judopourtous.com), the Kodokan technique videos
linked from those pages, and an animated morote-seoi-nage on Wikimedia Commons (CC BY 2.5 / GFDL). Nothing was downloaded.

**The poses were written from descriptions and checked on the contact sheet; they were not traced from a photo sequence.**
A free, complete photo sequence of each of these five throws was not found. That is the main limit on quality today.

## 4. Limits

* Block-out only: no hand or finger poses, no gi, no weight shift between tori's feet, no twist of the trunk against the hips.
* Tori's sleeve hand is 15–47 cm short at landing in some throws; tori should kneel or step, not yet posed.
* The fall has no contact time or ground force (A17, open item 3). Ukemi has no arm-slap energy split.
* Not played in Godot yet; the gameplay table has no judo moves. The bake uses the anatomical rest pose, not the
  T-pose of the Souls clips: a Godot export must convert the rest before it shares a skeleton with them.
* In-betweens: planted feet are not locked (they slide a few centimetres between keys), and the timing is a
  symmetric smoothstep; a real throw accelerates into kake and has no pause there.

## 5. Next

1. Owner review of the contact sheets and the Blender strips, pose by pose.
2. A photo or video sequence per throw to trace the keys from (owner's own drawings, or a source to approve).
3. Foot locking and throw timing in the in-betweens; then a Godot export and playback driven by `ce-throw/1`.
4. A `judo` style in the gameplay table (needs the owner's OK: the table is generated and pinned).
