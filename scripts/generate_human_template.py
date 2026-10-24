#!/usr/bin/env python
"""Genera el archivo JSON con la lista canónica de 206 huesos + contenedores."""

import json
from pathlib import Path


def generate_206_bones():
    bones = []
    containers = []
    def add_bone(canonical, name, parent=None, head=(0,0,0), tail=(0,0.1,0)):
        bones.append({
            "canonical_name": canonical,
            "name": name,
            "parent": parent,
            "head": {"x": head[0], "y": head[1], "z": head[2]},
            "tail": {"x": tail[0], "y": tail[1], "z": tail[2]}
        })
    def add_container(canonical, name, parent=None):
        containers.append({
            "canonical_name": canonical,
            "name": name,
            "parent": parent
        })

    # ====================================================================
    # CONTENEDORES LÓGICOS
    # ====================================================================
    add_container("ROOT_SKELETON", "RootSkeleton")
    add_container("CRANIUM", "Craneo", parent="ROOT_SKELETON")

    # ====================================================================
    # 1. CRÁNEO Y CARA (22)
    # ====================================================================
    # Neurocráneo (8)
    add_bone("FRONTAL", "Frontal", parent="CRANIUM", head=(0, 1.85, 0.05), tail=(0, 1.9, 0.05))
    add_bone("PARIETAL_L", "Parietal I", parent="CRANIUM", head=(-0.08, 1.8, 0.02), tail=(-0.08, 1.85, 0.02))
    add_bone("PARIETAL_R", "Parietal D", parent="CRANIUM", head=(0.08, 1.8, 0.02), tail=(0.08, 1.85, 0.02))
    add_bone("TEMPORAL_L", "Temporal I", parent="CRANIUM", head=(-0.1, 1.7, 0.1), tail=(-0.1, 1.8, 0.1))
    add_bone("TEMPORAL_R", "Temporal D", parent="CRANIUM", head=(0.1, 1.7, 0.1), tail=(0.1, 1.8, 0.1))
    add_bone("OCCIPITAL", "Occipital", parent="CRANIUM", head=(0, 1.65, -0.1), tail=(0, 1.75, -0.1))
    add_bone("SPHENOID", "Esfenoides", parent="CRANIUM", head=(0, 1.6, 0.05), tail=(0, 1.65, 0.05))
    add_bone("ETHMOID", "Etmoides", parent="CRANIUM", head=(0, 1.65, 0.08), tail=(0, 1.7, 0.08))
    # Viscerocráneo (14)
    add_bone("MAXILLA_L", "Maxilar I", parent="CRANIUM", head=(-0.06, 1.62, 0.08), tail=(-0.06, 1.67, 0.08))
    add_bone("MAXILLA_R", "Maxilar D", parent="CRANIUM", head=(0.06, 1.62, 0.08), tail=(0.06, 1.67, 0.08))
    add_bone("ZYGOMATIC_L", "Cigomatico I", parent="CRANIUM", head=(-0.12, 1.6, 0.06), tail=(-0.12, 1.65, 0.06))
    add_bone("ZYGOMATIC_R", "Cigomatico D", parent="CRANIUM", head=(0.12, 1.6, 0.06), tail=(0.12, 1.65, 0.06))
    add_bone("NASAL_L", "Nasal I", parent="CRANIUM", head=(-0.02, 1.75, 0.1), tail=(-0.02, 1.78, 0.1))
    add_bone("NASAL_R", "Nasal D", parent="CRANIUM", head=(0.02, 1.75, 0.1), tail=(0.02, 1.78, 0.1))
    add_bone("LACRIMAL_L", "Lagrimal I", parent="CRANIUM", head=(-0.05, 1.7, 0.08), tail=(-0.05, 1.72, 0.08))
    add_bone("LACRIMAL_R", "Lagrimal D", parent="CRANIUM", head=(0.05, 1.7, 0.08), tail=(0.05, 1.72, 0.08))
    add_bone("PALATINE_L", "Palatino I", parent="CRANIUM", head=(-0.04, 1.55, 0.06), tail=(-0.04, 1.58, 0.06))
    add_bone("PALATINE_R", "Palatino D", parent="CRANIUM", head=(0.04, 1.55, 0.06), tail=(0.04, 1.58, 0.06))
    add_bone("INFERIOR_NASAL_CONCHA_L", "Concha inf I", parent="CRANIUM", head=(-0.05, 1.6, 0.07), tail=(-0.05, 1.62, 0.07))
    add_bone("INFERIOR_NASAL_CONCHA_R", "Concha inf D", parent="CRANIUM", head=(0.05, 1.6, 0.07), tail=(0.05, 1.62, 0.07))
    add_bone("VOMER", "Vomer", parent="CRANIUM", head=(0, 1.6, 0.09), tail=(0, 1.65, 0.09))
    add_bone("MANDIBLE", "Mandibula", parent="CRANIUM", head=(0, 1.55, 0), tail=(0, 1.6, 0))
    assert len(bones) == 22, "Cráneo y cara deben sumar 22"

    # ====================================================================
    # 2. HUESOS DEL OÍDO (6)
    # ====================================================================
    add_bone("MALLEUS_L", "Martillo I", parent="CRANIUM", head=(-0.02, 1.65, 0.02), tail=(-0.02, 1.66, 0.02))
    add_bone("MALLEUS_R", "Martillo D", parent="CRANIUM", head=(0.02, 1.65, 0.02), tail=(0.02, 1.66, 0.02))
    add_bone("INCUS_L", "Yunque I", parent="CRANIUM", head=(-0.02, 1.64, 0.02), tail=(-0.02, 1.65, 0.02))
    add_bone("INCUS_R", "Yunque D", parent="CRANIUM", head=(0.02, 1.64, 0.02), tail=(0.02, 1.65, 0.02))
    add_bone("STAPES_L", "Estribo I", parent="CRANIUM", head=(-0.02, 1.63, 0.02), tail=(-0.02, 1.64, 0.02))
    add_bone("STAPES_R", "Estribo D", parent="CRANIUM", head=(0.02, 1.63, 0.02), tail=(0.02, 1.64, 0.02))
    assert len(bones) == 28, "Cráneo + oído deben sumar 28"

    # ====================================================================
    # 3. HIOIDES (1)
    # ====================================================================
    add_bone("HYOID", "Hioides", parent="CRANIUM", head=(0, 1.4, 0.08), tail=(0, 1.42, 0.08))
    assert len(bones) == 29, "Añadiendo hioides debe dar 29"

    # ====================================================================
    # 4. COLUMNA VERTEBRAL (26)
    # ====================================================================
    # Cervicales (7)
    for i in range(1, 8):
        y = 1.45 - (i-1)*0.03
        parent = f"CERVICAL_{i-1}" if i > 1 else "CRANIUM"
        add_bone(f"CERVICAL_{i}", f"C{i}", parent=parent, head=(0, y, 0), tail=(0, y-0.03, 0))
    # Torácicas (12)
    for i in range(1, 13):
        y = 1.15 - (i-1)*0.035
        parent = f"THORACIC_{i-1}" if i > 1 else "CERVICAL_7"
        add_bone(f"THORACIC_{i}", f"T{i}", parent=parent, head=(0, y, 0), tail=(0, y-0.035, 0))
    # Lumbares (5)
    for i in range(1, 6):
        y = 0.65 - (i-1)*0.04
        parent = f"LUMBAR_{i-1}" if i > 1 else "THORACIC_12"
        add_bone(f"LUMBAR_{i}", f"L{i}", parent=parent, head=(0, y, 0), tail=(0, y-0.04, 0))
    # Sacro y Cóccix
    add_bone("SACRUM", "Sacro", parent="LUMBAR_5", head=(0, 0.35, 0), tail=(0, 0.25, 0))
    add_bone("COCCYX", "Coccix", parent="SACRUM", head=(0, 0.2, 0), tail=(0, 0.15, 0))
    assert len(bones) == 55, "Axial (sin caja torácica) debe sumar 55"

    # ====================================================================
    # 5. CAJA TORÁCICA (25)
    # ====================================================================
    add_bone("STERNUM", "Esternon", parent="THORACIC_1", head=(0, 1.0, 0.1), tail=(0, 0.85, 0.1))
    for side, sign in [("L", -1), ("R", 1)]:
        for i in range(1, 13):
            y = 1.1 - (i-1)*0.035
            x = sign * (0.1 + i*0.01)
            parent = f"THORACIC_{i}"
            add_bone(f"RIB_{i:02d}_{side}", f"Costilla{i:02d}{'I' if side=='L' else 'D'}",
                     parent=parent, head=(x, y, 0), tail=(x*1.5, y-0.02, 0))
    assert len(bones) == 80, "Axial completo debe sumar 80"

    # ====================================================================
    # 6. MIEMBROS SUPERIORES (64)
    # ====================================================================
    # Cintura escapular (4)
    for side, sign in [("L", -1), ("R", 1)]:
        add_bone(f"CLAVICLE_{side}", f"Clavicula {'I' if side=='L' else 'D'}",
                 parent="ROOT_SKELETON", head=(sign*0.25, 1.2, 0.1), tail=(sign*0.3, 1.15, 0.1))
        add_bone(f"SCAPULA_{side}", f"Escapula {'I' if side=='L' else 'D'}",
                 parent=f"CLAVICLE_{side}", head=(sign*0.35, 1.1, 0), tail=(sign*0.35, 0.95, 0))
    # Brazos y antebrazos (6)
    for side, sign in [("L", -1), ("R", 1)]:
        add_bone(f"HUMERUS_{side}", f"Húmero {'I' if side=='L' else 'D'}",
                 parent=f"SCAPULA_{side}", head=(sign*0.35, 0.9, 0), tail=(sign*0.35, 0.55, 0))
        add_bone(f"RADIUS_{side}", f"Radio {'I' if side=='L' else 'D'}",
                 parent=f"HUMERUS_{side}", head=(sign*0.35, 0.5, 0.05), tail=(sign*0.35, 0.2, 0.05))
        add_bone(f"ULNA_{side}", f"Cubito {'I' if side=='L' else 'D'}",
                 parent=f"HUMERUS_{side}", head=(sign*0.35, 0.5, -0.05), tail=(sign*0.35, 0.2, -0.05))
    # Carpos (16)
    carpal_names = ["SCAPHOID", "LUNATE", "TRIQUETRUM", "PISIFORM",
                    "TRAPEZIUM", "TRAPEZOID", "CAPITATE", "HAMATE"]
    for side, sign in [("L", -1), ("R", 1)]:
        for idx, name in enumerate(carpal_names):
            y = -0.05 - idx*0.005
            x_off = sign * (0.01 + idx*0.005)
            add_bone(f"{name}_{side}", f"{name.title()} {'I' if side=='L' else 'D'}",
                     parent=f"RADIUS_{side}",
                     head=(sign*0.35 + x_off, y, 0.02*idx),
                     tail=(sign*0.35 + x_off, y-0.02, 0.02*idx))
    # Metacarpos (10)
    for side, sign in [("L", -1), ("R", 1)]:
        for i in range(1, 6):
            x_off = sign * (0.05 + i*0.02)
            y = -0.1 - i*0.01
            add_bone(f"METACARPAL_{i}_{side}", f"Metacarpal{i} {'I' if side=='L' else 'D'}",
                     parent=f"RADIUS_{side}", head=(x_off, y, 0), tail=(x_off, y-0.04, 0))
    # Falanges de las manos (28)
    finger_names = ["THUMB", "INDEX", "MIDDLE", "RING", "LITTLE"]
    for side, sign in [("L", -1), ("R", 1)]:
        for fi, finger in enumerate(finger_names):
            y_base = -0.15 - fi*0.01
            x_off = sign * (0.05 + fi*0.02)
            # Proximal
            add_bone(f"PHALANX_PROXIMAL_{fi+1}_{side}", f"{finger} Prox {'I' if side=='L' else 'D'}",
                     parent=f"RADIUS_{side}", head=(x_off, y_base, 0), tail=(x_off, y_base-0.03, 0))
            # Intermedia (excepto thumb)
            if fi != 0:
                add_bone(f"PHALANX_INTERMEDIATE_{fi+1}_{side}", f"{finger} Inter {'I' if side=='L' else 'D'}",
                         parent=f"PHALANX_PROXIMAL_{fi+1}_{side}",
                         head=(x_off, y_base-0.03, 0), tail=(x_off, y_base-0.06, 0))
            # Distal
            add_bone(f"PHALANX_DISTAL_{fi+1}_{side}", f"{finger} Dist {'I' if side=='L' else 'D'}",
                     parent=f"PHALANX_INTERMEDIATE_{fi+1}_{side}" if fi != 0 else f"PHALANX_PROXIMAL_{fi+1}_{side}",
                     head=(x_off, y_base-0.06 if fi!=0 else y_base-0.03, 0),
                     tail=(x_off, y_base-0.09 if fi!=0 else y_base-0.06, 0))
    assert len(bones) == 144, "Axial + superiores debe sumar 144"

    # ====================================================================
    # 7. MIEMBROS INFERIORES + CINTURA PÉLVICA (62)
    # ====================================================================
    # Coxales (2) – cuelgan de SACRUM
    for side, sign in [("L", -1), ("R", 1)]:
        add_bone(f"COXAL_{side}", f"Coxal {'I' if side=='L' else 'D'}",
                 parent="SACRUM", head=(sign*0.15, 0.25, 0), tail=(sign*0.15, 0.15, 0))
    # Fémur (2)
    for side, sign in [("L", -1), ("R", 1)]:
        add_bone(f"FEMUR_{side}", f"Femur {'I' if side=='L' else 'D'}",
                 parent=f"COXAL_{side}", head=(sign*0.1, 0.1, 0), tail=(sign*0.1, -0.35, 0))
    # Rótula (2)
    for side, sign in [("L", -1), ("R", 1)]:
        add_bone(f"PATELLA_{side}", f"Rotula {'I' if side=='L' else 'D'}",
                 parent=f"FEMUR_{side}", head=(sign*0.1, -0.35, 0.05), tail=(sign*0.1, -0.35, 0.07))
    # Tibia y Fíbula (4)
    for side, sign in [("L", -1), ("R", 1)]:
        add_bone(f"TIBIA_{side}", f"Tibia {'I' if side=='L' else 'D'}",
                 parent=f"FEMUR_{side}", head=(sign*0.1, -0.4, 0), tail=(sign*0.1, -0.8, 0))
        add_bone(f"FIBULA_{side}", f"Perone {'I' if side=='L' else 'D'}",
                 parent=f"FEMUR_{side}", head=(sign*0.1, -0.4, 0.05), tail=(sign*0.1, -0.8, 0.05))
    # Tarsos (14)
    tarsal_names = ["TALUS", "CALCANEUS", "NAVICULAR", "CUBOID",
                    "CUNEIFORM_MEDIAL", "CUNEIFORM_INTERMEDIATE", "CUNEIFORM_LATERAL"]
    for side, sign in [("L", -1), ("R", 1)]:
        for idx, name in enumerate(tarsal_names):
            y = -0.9 - idx*0.01
            x_off = sign * (0.05 + idx*0.005)
            add_bone(f"{name}_{side}", f"{name.title()} {'I' if side=='L' else 'D'}",
                     parent=f"TIBIA_{side}", head=(sign*0.1 + x_off, y, 0.02*idx),
                     tail=(sign*0.1 + x_off, y-0.03, 0.02*idx))
    # Metatarsos (10)
    for side, sign in [("L", -1), ("R", 1)]:
        for i in range(1, 6):
            x_off = sign * (0.05 + i*0.02)
            y = -1.0 - i*0.01
            add_bone(f"METATARSAL_{i}_{side}", f"Metatarsal{i} {'I' if side=='L' else 'D'}",
                     parent=f"TIBIA_{side}", head=(x_off, y, 0), tail=(x_off, y-0.05, 0))
    # Falanges de los pies (28)
    toe_names = ["HALLUX", "SECOND", "THIRD", "FOURTH", "FIFTH"]
    for side, sign in [("L", -1), ("R", 1)]:
        for ti, toe in enumerate(toe_names):
            y_base = -1.05 - ti*0.01
            x_off = sign * (0.05 + ti*0.02)
            # Proximal
            add_bone(f"TOE_PHALANX_PROXIMAL_{ti+1}_{side}", f"{toe} Prox {'I' if side=='L' else 'D'}",
                     parent=f"TIBIA_{side}", head=(x_off, y_base, 0), tail=(x_off, y_base-0.03, 0))
            # Intermedia (excepto hallux)
            if ti != 0:
                add_bone(f"TOE_PHALANX_INTERMEDIATE_{ti+1}_{side}", f"{toe} Inter {'I' if side=='L' else 'D'}",
                         parent=f"TOE_PHALANX_PROXIMAL_{ti+1}_{side}",
                         head=(x_off, y_base-0.03, 0), tail=(x_off, y_base-0.06, 0))
            # Distal
            add_bone(f"TOE_PHALANX_DISTAL_{ti+1}_{side}", f"{toe} Dist {'I' if side=='L' else 'D'}",
                     parent=f"TOE_PHALANX_INTERMEDIATE_{ti+1}_{side}" if ti != 0 else f"TOE_PHALANX_PROXIMAL_{ti+1}_{side}",
                     head=(x_off, y_base-0.06 if ti!=0 else y_base-0.03, 0),
                     tail=(x_off, y_base-0.09 if ti!=0 else y_base-0.06, 0))

    assert len(bones) == 206, f"Total de huesos debe ser 206, se generaron {len(bones)}"
    return bones, containers

def main():
    bones, containers = generate_206_bones()
    print(f"Huesos generados: {len(bones)}")
    print(f"Contenedores generados: {len(containers)}")
    data = {"bones": bones, "containers": containers}
    output_path = Path(__file__).parent.parent / "src" / "character_engine" / "data" / "anatomy" / "human_adult_206.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Archivo generado: {output_path}")

if __name__ == "__main__":
    main()
