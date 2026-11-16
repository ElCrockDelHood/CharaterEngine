# Judo / Jujutsu throws and falls — proposal

Status: PROPOSAL, nothing implemented. Owner request, 2026-11-15: "Quiero que mi character luche Judo Jujutsu", with the
structure *position → kumikata (grip) → kuzushi (unbalancing) → technique (throw) → ukemi (fall)*, and the directions
omote / ura / uchi / soto. Builds on `domain/physics/move_strikers.py` (`FallLanding`, Decision 81, A17).

## 1. Scope and split

| Part | Owner thread | In this proposal |
|---|---|---|
| Primary positions (standing, seiza, half guard), guards, stance changes, direction vocabulary | "Dar movimiento natural a los personajes" | only the interface: a position id and a facing |
| Kumikata, kuzushi, throw resolution, the fall, ukemi | this thread | yes |
| Ground fighting after the fall (ne-waza: holds, chokes, locks) | none yet | no; a later proposal |
| Clips and their playback in Blender and Godot | animation / runtime threads | only the event they would read |

## 2. What exists today

* One throw, `shoulder_throw` ("Vortex Throw"): a `kind: "throw"` move that beats guard, wounds one bone as a blunt hit
  and sets `knockdown`. There is no grip, no balance, no fall and no ukemi. `sweep` is a kick with `knockdown`.
* `FallLanding` (A17): a body dropped on its back from a release height; total and trunk energy. No orientation, no
  contact time, no surface.
* `head_kinematics.py`: an impulse threshold that forces a step (`P_STEP_N_S`, from pull tests on adults of about 80,
  scaled by assumption), and the Rowson concussion table.
* Measured head and neck loads for thrown bodies, read for A17 (section 5 below).

## 3. Model

A throw is a sequence of five phases. Each one can fail, and the failure is what makes a fight look like judo instead
of a button that always throws.

```
position ──▶ kumikata ──▶ kuzushi ──▶ tsukuri + kake ──▶ fall ──▶ ukemi / landing
 (other       grips        balance      fit in and         body       how the body
  thread)     taken        broken       execute            in air     meets the ground
```

### 3.1 Kumikata (grip)

A grip is `(hand of tori, point on uke, side)`. Points for the first version: sleeve, lapel, back of the collar, belt,
wrist, behind the neck. A grip gives tori a line along which force can be applied to uke's body, and its anchor bone on
uke comes from the canonical skeleton (for example sleeve → `HUMERUS`, lapel → `STERNUM` / clavicle).

* Standard right grip: right hand on the lapel, left hand on the sleeve. Each throw lists the grips it needs.
* Grip breaking: a grip holds up to a force limit. **No grip-strength number has been read**, so the limit is
  `ASSUMED` until a source is found, and is listed as an open item.
* Without clothing (no gi) only the body points exist (wrist, neck, waist): the same model covers jujutsu no-gi.

### 3.2 Kuzushi (unbalancing)

The eight classical directions (happo no kuzushi) map directly to the engine's frame: forward, back, left, right and the
four diagonals of uke. The test is mechanical:

1. Uke's base of support is the polygon of the feet on the ground, from the skeleton's foot bones in the current pose.
2. The pull or push through the grips gives a horizontal impulse on uke's centre of mass.
3. Uke is unbalanced in a direction when that impulse exceeds what a step can recover. The engine already has that
   threshold (`P_STEP_N_S`); it becomes direction-dependent: larger where a foot is free to step, small where the
   stepping foot is loaded, blocked or being reaped. That last case is the whole idea of a foot sweep.

Output: `kuzushi(direction, margin)`, with `margin ≤ 0` meaning balance is broken. A throw attempted with positive
margin fails and leaves tori open, which is where counters come from.

The step threshold comes from elderly subjects and is scaled by assumption (A16); it stays `ASSUMED`. The method of
comparing the centre of mass with the base of support is standard balance mechanics; no number from that literature is
used that was not read.

### 3.3 Throws: first set

One or two per classical family, chosen because measured fall data exists for most of them:

| Throw | Family | Kuzushi | Uke lands | Maps to |
|---|---|---|---|---|
| Seoi-nage | te-waza (hand) | forward | forward rotation, on the back | existing `shoulder_throw` |
| O-goshi | koshi-waza (hip) | forward | forward rotation, on the back or side | new |
| O-soto-gari | ashi-waza (leg) | back, to the corner | straight back | new |
| O-uchi-gari | ashi-waza (leg) | back | straight back | new |
| De-ashi-barai | ashi-waza (leg) | side, on the stepping foot | on the side | existing `sweep` |
| Tomoe-nage | sutemi-waza (sacrifice) | forward | forward roll over tori | later |

Each throw record holds: required grips, entry position, kuzushi direction, which of uke's legs must be loaded, the
release height range of uke's centre of mass (`ASSUMED`, as in A17), the rotation given to uke, and the fall type.
Omote / ura and uchi / soto are parameters of the same record (in front of or behind uke; inside or outside the legs),
not separate techniques, so the vocabulary the owner uses selects variants.

### 3.4 The fall

`FallLanding` gains what it lacks, all additive:

* Landing orientation: back, side, front, rolling.
* Which segments touch first and in what order, so the energy is split by segment instead of "trunk" and "the rest".
* Whether the head reaches the ground.

Still not modelled, because nothing was read: contact time and peak ground force. They stay open (A17, open item 3).

### 3.5 Ukemi (breakfall)

Four falls: ushiro (back), yoko (side), mae (front), mae-mawari (forward roll). Ukemi does two things in the model:

1. It decides whether the head hits. With correct ukemi the chin is tucked and the head does not reach the mat.
2. It moves energy from the trunk to the slapping arm and to the roll.

Skill is a number per character; fatigue and a throw that arrives too fast lower the chance of a correct ukemi. The
shape of that rule is `ASSUMED`; one study reports head acceleration rising after hard exercise, without numbers that
were read.

## 4. Output for the runtimes

One JSON event per throw, in the style of `ce-fracture/1`, so Blender and Godot only read it:

```
schema: "ce-throw/1"
throw, variant (omote/ura, uchi/soto), tori, uke
phases: [{name, start_frame, end_frame, result}]      # kumikata, kuzushi, tsukuri, kake, fall, landing
grips: [{hand, point, bone}]
kuzushi: {direction, margin}
fall: {type, release_height_m, impact_speed_m_s, energy_j, first_contact: [segments]}
ukemi: {attempted, correct, type}
head: {hits_ground, angular_rad_s2, linear_g, source}  # measured ranges where they exist, else null
provenance: per field
```

Additive and opt-in: the gameplay table, the existing moves, the strike model and every hash stay as they are.

## 5. Measured data available (read for A17)

Head loads on landing, thrower an expert in every row:

| Throw | Subject | Ukemi | Linear | Angular rad/s² | Source |
|---|---|---|---|---|---|
| Seoi-nage | dummy 75 kg | no | 20.3 ± 9.8 G | 1890 ± 1152 | Murayama 2020 (full text) |
| O-soto-gari | dummy 75 kg | no | 46.5 ± 3.8 G | 4573 ± 357 | Murayama 2020, Table 1, citing the authors' earlier study |
| O-uchi-gari | dummy 75 kg | no | 87.9 ± 3.8 G | 2176 ± 827 | same |
| O-soto-gari | expert judoka | yes | 10.3 ± 1.6 G | 679 ± 174 | as printed in Lockhart 2022; primary not read |
| O-soto-gari | novice judoka | yes | not read | 693 | Ishikawa 2018 as printed in Lockhart 2022 |
| O-uchi-gari | novice judoka | yes | not read | 402 | same |
| Seoi-nage | novice judoka | yes | not read | 276 | same |
| Tai-otoshi | novice judoka | yes | not read | 368 | same |

Neck, seoi-nage on the dummy without ukemi: compression 4223 N, Nij median 0.68 (Nakanishi 2021).

Reading: the backward throws are the ones that load the head, and ukemi cuts the load several times over (o-soto-gari
4573 → 679 rad/s², dummy against human, so the ratio is indicative only). The review prints different values for the
earlier dummy study than Murayama's Table 1 (130.0 G, 5081 rad/s²); the discrepancy is unexplained, and the model would
carry the range, not one value.

**Not found**: grip strength in a throw, the pulling force or impulse of kuzushi, uke's body speed at landing, landing
force, and any data for o-goshi, de-ashi-barai and tomoe-nage. Those parts are `ASSUMED` until read.

## 6. Steps, in order

1. **Domain model** (pure Python, tests): grip, kuzushi margin from the pose, throw records for the first five throws,
   extended fall with orientation, ukemi, and the `ce-throw/1` event. No clips needed; verified with numbers.
2. **Demo table and audit document**, with every constant and its provenance.
3. **Gameplay**: a separate `judo` style in the generated table, so `shenmue` and `souls_like` do not move. Needs the
   owner's OK because the table is generated and its scenarios are pinned.
4. **Clips**: paired tori and uke animation for each throw and each ukemi. The repository has none. This is the largest
   cost and decides the visual quality; see the questions.

## 7. Questions for the owner

1. First set of throws: the five in 3.3, or others first?
2. Clips: keyed by hand in Blender, procedural from the model, or motion capture to be found and approved? Nothing is
   downloaded without approval.
3. Is ground fighting (ne-waza) wanted after this, or only standing judo for now?
