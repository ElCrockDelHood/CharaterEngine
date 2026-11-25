# Proposal — neck base and shoulder height: diagnosis (recommendation: do NOT move yet)

**Status:** PROPOSAL, measurement only; no data changed, so no trial was needed · **Date:** 2026-11-25 · a data change needs the
owner's OK and a numbered Decision · Related: A24 (shoulder girdle, Decision 68), A27 (spine heights, Decision 72), A29,
`CERVICAL_SPACING_PROPOSAL.md`, `SPINE_THORAX_PROPOSAL.md`.

## Question

ANSUR II puts the cervicale at 1.557 m at 1.80 m. The canonical C7, taken from BodyParts3D in A27, sits about 35–45 mm lower.
Is that a bone difference, or only skin?

## Data (mm at 1.80 m)

ANSUR II, men 1.75–1.85 m, n = 1814, each measure as a ratio to stature × 1800. These are skin landmarks, measured standing.

| Landmark | ANSUR II (skin) | Canonical | Canonical − ANSUR |
|----------|-----------------|-----------|-------------------|
| Cervicale (C7 spinous tip) | 1556.7 (p5–p95 1538–1575) | ≈ 1514 *(C7 body 1524, tip 10 mm below it per BP3D)* | **≈ −43** |
| Suprasternale (jugular notch) | 1476.3 (1457–1497) | 1486.8 (`STERNUM` head, manubrium top) | +10 |
| Acromion | 1478.9 (1451–1507) | ≈ 1510 (`CLAVICLE` tail, acromioclavicular joint) | ≈ +31 |
| Glenohumeral centre | — | 1472.4 (`HUMERUS` head, Drillis 0.818 H, PROVEN) | — |

**Relative heights.** These are independent of how each region was mapped to the canonical frame. BP3D is bone, scaled ×1.0465 to
1.80 m.

| Difference | ANSUR II (skin, standing) | BodyParts3D (bone) | BP3D − ANSUR |
|------------|---------------------------|--------------------|--------------|
| Cervicale − acromion | 77.8 (sd 13.8; p5 55) | 19.4 | **−58** |
| Cervicale − suprasternale | 80.4 (sd 11.5; p5 61) | 45.1 | **−35** |
| Acromion − suprasternale | 2.6 (sd 14.3) | 25.8 | +23 |

BP3D landmark rules: C7 tip is the most posterior vertex of C7, 10 mm below the C7 body and 55 mm behind it. The acromion is the
highest point of the lateral 15 mm of the scapula. The manubrium top is the highest point of the sternum. The meshes carry about
±5 mm of mesh resolution, and the data come from one subject.

## Reading

1. **Not skin.** The cervicale is palpated on the C7 spinous tip, and the soft tissue there adds thickness backwards, not upwards.
   The acromial and suprasternal skin points sit a few millimetres from bone. None of this explains 35–58 mm of height.
2. **The difference is in the BodyParts3D subject's posture.** Its neck base is low against its own shoulders and sternum: the
   C7 tip is 19 mm above the acromion, against 78 mm in the standing population (below the ANSUR p5 of 55). The acromion is 26
   mm above the notch, against 3 mm. That fits a scanned subject with raised shoulders and a lowered, forward neck base.
   The canonical skeleton inherited it, because A24 placed the girdle and A27 the spine from that subject.
3. **The shoulder is linked to it.** The canonical glenohumeral centre is at Drillis' 0.818 H (1472 mm). The anthropometry
   table reads that ratio as the shoulder *joint*. ANSUR's skin acromion is 1479 mm, almost the same height. The canonical AC
   joint, taken from BP3D, sits 31 mm above ANSUR's acromion: the girdle is high for the same reason the neck base is low. If
   Drillis' "shoulder" is the acromion rather than the joint, the glenohumeral centre would be about 30 mm too high as well.
   That is a reading of a PROVEN source, so it is the owner's call.
4. *Anatomía Clínica* (Pró), qualitative only: C7, the *vertebra prominens*, is the palpable neck base. Its spinous process
   points back and down, so the tip lies at or below the level of its body, as measured. Busscher et al. 2010 is a cited
   contrast only (CC BY-NC); it gives vertebral dimensions, not standing heights, and adds nothing here.

## Why not move C7 alone

Raising C7 by about 43 mm with C1 fixed at 1.628 m (A27, A30) would shorten C1–C7 from 112 mm to about 69 mm, which is not a
human neck. The upper end is probably low too: ANSUR's tragion is at about 1.668 m, and the atlas usually lies just below the
ear canal level, so C1 may also sit 15–25 mm low (inference, not measured). A correct fix moves the whole cervical column, and
probably the girdle. It needs:

- a population source for the cervical column in standing posture (C1 and C7 heights or cervical length), not one scanned
  subject;
- the owner's reading of Drillis 0.818 H (joint or acromion);
- a trial with every gate, because it moves the neck, the clavicles, the scapulae and the head pivot that the game rig and
  the strike model use.

## Recommendation

1. **Do not move** C7, the shoulder girdle or the glenohumeral centre now. Keep the discrepancy recorded: the neck base is about 43 mm
   low and the acromion about 31 mm high against the standing population, both inherited from the BodyParts3D subject's posture.
2. Next step, if the owner wants it: look for a citable source on cervical spine heights in standing posture (radiographic
   studies), then propose a combined neck and girdle rebuild as a numbered Decision, with a trial.
3. The owner decides how to read Drillis 0.818 H.

How to repeat the measurement: `scripts/` holds no tool for it yet. The numbers above come from the BodyParts3D OBJ files
(outside the repo) and the ANSUR II CSV, by the rules stated under the second table.
