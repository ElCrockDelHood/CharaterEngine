#!/usr/bin/env python
"""Transforma el archivo human_adult_206.json de Y-up a Z-up (con pies en Z=0)."""

import json
import shutil
from pathlib import Path

# Rutas
project_root = Path(__file__).parent
src_path = project_root / "src" / "character_engine" / "data" / "anatomy"
json_path = src_path / "human_adult_206.json"
backup_path = src_path / "human_adult_206_backup.json"

if not json_path.exists():
    print(f"ERROR: Archivo no encontrado: {json_path}")
    exit(1)

# 1. Cargar el JSON
with open(json_path, encoding='utf-8') as f:
    data = json.load(f)

bones = data.get("bones", [])
containers = data.get("containers", [])

print(f"Leyendo {len(bones)} huesos y {len(containers)} contenedores.")

# 2. Transformar las coordenadas de cada hueso
# Rotación -90° alrededor de X (Y-up -> Z-up):
#   x' = x
#   y' = -z
#   z' = y
transformed_bones = []
min_z = float('inf')

for bone in bones:
    h = bone["head"]
    t = bone["tail"]
    h_new = {
        "x": h["x"],
        "y": -h["z"],
        "z": h["y"]
    }
    t_new = {
        "x": t["x"],
        "y": -t["z"],
        "z": t["y"]
    }
    min_z = min(min_z, h_new["z"], t_new["z"])
    transformed_bones.append({
        "canonical_name": bone["canonical_name"],
        "name": bone["name"],
        "parent": bone.get("parent"),
        "head": h_new,
        "tail": t_new
    })

# 3. Calcular desplazamiento para que el punto más bajo esté en Z=0
offset_z = -min_z
print(f"Desplazamiento Z para pies en el suelo: {offset_z:.4f}")

# 4. Aplicar el desplazamiento vertical
final_bones = []
for bone in transformed_bones:
    h = bone["head"]
    t = bone["tail"]
    h_final = {
        "x": h["x"],
        "y": h["y"],
        "z": h["z"] + offset_z
    }
    t_final = {
        "x": t["x"],
        "y": t["y"],
        "z": t["z"] + offset_z
    }
    final_bones.append({
        "canonical_name": bone["canonical_name"],
        "name": bone["name"],
        "parent": bone["parent"],
        "head": h_final,
        "tail": t_final
    })

# 5. Guardar backup y nuevo JSON
print("Creando copia de seguridad...")
shutil.copy2(json_path, backup_path)
print(f"Backup guardado en {backup_path}")

new_data = {
    "bones": final_bones,
    "containers": containers  # los contenedores no tienen geometría
}

with open(json_path, 'w', encoding='utf-8') as f:
    json.dump(new_data, f, indent=2, ensure_ascii=False)

print(f"Archivo actualizado: {json_path}")
print(f"  Huesos transformados: {len(final_bones)}")
print(f"  Contenedores: {len(containers)}")
print("")
print("Transformación completada. El canonical ahora está en Z-up con pies en Z=0.")
