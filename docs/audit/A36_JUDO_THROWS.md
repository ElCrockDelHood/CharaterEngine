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

Seven keys per throw (kumikata, kuzushi, tsukuri, kake, fall, landing, end) for tori and uke, 58–62 frames at 60 fps. A
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

## 3. References for the poses, and their limit

Read: the technique descriptions of the five throws in Wikipedia (kuzushi, tsukuri and kake of o-goshi; the stepping and
reaping legs of o-soto-gari; the swept foot of de-ashi-barai), each with a single illustration. Found but not used as
frame sources: a Nage-no-Kata document with numbered photo sequences (judopourtous.com), the Kodokan technique videos
linked from those pages, and an animated morote-seoi-nage on Wikimedia Commons (CC BY 2.5 / GFDL). Nothing was downloaded.

**The poses were written from descriptions and checked on the contact sheet; they were not traced from a photo sequence.**
A free, complete photo sequence of each of these five throws was not found. That is the main limit on quality today.

## 4. Limits

* Block-out only: no in-betweens (a bake must take uke's forward rotation the long way round), no hand or finger poses,
  no gi, no weight shift between tori's feet, no twist of the trunk against the hips.
* Tori's sleeve hand is 15–47 cm short at landing in some throws; tori should kneel or step, not yet posed.
* The fall has no contact time or ground force (A17, open item 3). Ukemi has no arm-slap energy split.
* Not baked: Blender and Godot do not play these yet; the gameplay table has no judo moves.

## 5. Next

1. Owner review of the contact sheets, pose by pose.
2. A photo or video sequence per throw to trace the keys from (owner's own drawings, or a source to approve).
3. Blender bake of `ce-judo-clips/1` with two fighters, then Godot playback driven by `ce-throw/1`.
4. A `judo` style in the gameplay table (needs the owner's OK: the table is generated and pinned).
