# S2-D1-R20-B-RECOVERY-PLAN

**Documento**: S2-D1-R20-B-RECOVERY-PLAN
**Fase**: S2-D1-R20-B
**Tipo: Plan de Recuperación
**Modo: Análisis y Planificación
**Estado**: COMPLETADO
**Fecha**: 2026-10-13
**Propósito**: Diseñar plan reversible para recuperar integridad del repositorio después de identificar modificaciones no autorizadas durante R19

---

## 1. ALCANCE Y RESTRICCIONES

**Alcance**: Diseño de plan de recuperación reversible para Character Engine

**Restricciones**:
- Solo análisis y planificación
- NO modificar archivos ni el índice
- NO ejecutar restauraciones
- NO crear commits
- NO descartar cambios
- NO asumir que HEAD contiene todo el trabajo legítimo
- NO eliminar cambios solo por estar staged
- NO corregir defectos matemáticos en esta fase

**Estado**: Solo lectura - planificación exclusivamente

---

## 2. BASE DOCUMENTAL

**Informe forense**: `docs/audit/S2-D1-R20-A-FORENSIC-REPORT.md`

**Evidencias Git documentadas**:
- HEAD: 5e96c37 (first commit)
- Staged: 5815 archivos (10,579 inserciones, 1,116,440 eliminaciones)
- Working tree modificado: transform.py, quaternion.py, vector3.py, export/gltf.py, loader/json_loader.py, tests/export/test_gltf_export.py
- Untracked: documentos de auditoría R6-R19, nuevos módulos de dominio, runtime, scripts adicionales

**Estado**: Evidencia suficiente disponible

---

## 3. CLASIFICACIÓN DE CAMBIOS

### 3.1 Cambios Autorizados por R19

**Documentos de auditoría** (autorizados):
- `docs/audit/S2-D1-R19-TRS-CORRECTION.md` - creado durante R19 ✓
- `docs/audit/S2-D1-R19-INDEPENDENT-AUDIT.md` - creado durante R19 ✓
- `docs/audit/S2-D1-R19-SCOPE-GATE.md` - creado durante R19 ✓

**Estado**: Deben preservarse

### 3.2 Cambios de Origen Indeterminado

**Cambios staged** (5815 archivos):
- Reestructuración masiva del proyecto
- Eliminación de .ai/ y .engine/
- Adición de .cursor/rules/ y .cursor/skills/
- Modificaciones extensas en código de producción
- Modificaciones en tests

**Cambios no staged**:
- transform.py (GlobalTransform, LocalJointTransform)
- quaternion.py (adicional a staged)
- vector3.py (is_finite)
- export/gltf.py, loader/json_loader.py, tests/export/test_gltf_export.py

**Archivos sin seguimiento**:
- Nuevos módulos de dominio (animation, character, gameplay, rigging, tissue, trauma)
- Runtime y scripts adicionales
- docs/audit/R6-R18 (documentos de auditoría anteriores a R19)

**Estado**: Evidencia insuficiente para determinar si son trabajo legítimo

---

## 4. INVENTARIO DE RIESGOS

### 4.1 Riesgos de Pérdida de Trabajo Legítimo

**ALTO**:
- Si se restituye HEAD sin preservar cambios staged: pérdida de 5815 archivos de cambios masivos
- Si se restituye HEAD sin preservar working tree: pérdida de GlobalTransform, LocalJointTransform, UnitQuaternion, funciones de integración
- Si se descartan nuevos módulos de dominio: posible pérdida de trabajo legítimo de anatomía, animation, gameplay, etc.

**MEDIO**:
- Archivos de configuración (.cursor/, .github/, .gitignore)
- Tests modificados

**BAJO**:
- Archivos generados (.venv-py310/, __pycache__/)
- Archivos temporales eliminados (temp_debug_ref.py, temp_repo_structure.xml)

### 4.2 Riesgos de Confusión

**AlTO**:
- Si no se preserva el estado actual, será imposible distinguir qué cambios son legítimos
- Si se mezclan cambios de múltiples orígenes, será imposible rastrear procedencia

**MEDIO**:
- Diferencia entre cambios staged y no staged (algunos archivos como quaternion.py tienen ambos)

**BAJO**:
- Documentos de auditoría R6-R18 (claramente trabajo legítimo de auditorías anteriores)

---

## 5. MATRIZ ARCHIVO/DECISIÓN/EVIDENCIA

### 5.1 Documentos de Auditoría R19

| Archivo | Estado Git | Decisión | Evidencia | Riesgo |
|---------|-----------|----------|----------|-------|
| docs/audit/S2-D1-R19-TRS-CORRECTION.md | ?? | PRESERVAR | Creado durante R19 | BAJO |
| docs/audit/S2-D1-R19-INDEPENDENT-AUDIT.md | ?? | PRESERVAR | Creado durante R19 | BAJO |
| docs/audit/S2-D1-R19-SCOPE-GATE.md | ?? | PRESERVAR | Creado durante R19 | BAJO |

### 5.2 Documentos de Auditoría R6-R18

| Archivo | Estado Git | Decisión | Evidencia | Riesgo |
|---------|-----------|----------|----------|-------|
| docs/audit/S2-D1-R6 a R18 | ?? | PRESERVAR | Trabajo legítimo de auditorías anteriores | BAJO |

### 5.3 Código de Producción Staged

| Archivo | Estado Git | Decisión | Evidencia | Riesgo |
|---------|-----------|----------|----------|-------|
| src/character_engine/math/algebra/quaternion.py | Staged | BLOQUEADO | Origen indeterminado, cambios masivos | ALTO |
| src/character_engine/math/algebra/matrix4.py | Staged | BLOQUEADO | Origen indeterminado | ALTO |
| src/character_engine/math/algebra/vector3.py | Staged | BLOQUEADO | Origen indeterminado | BAJO |
| src/character_engine/domain/anatomy/* | Staged | BLOQUEADO | Origen indeterminado, reestructuración masiva | ALTO |
| tests/* | Staged | BLOQUEADO | Origen indeterminado | MEDIO |
| .cursor/, .github/ | Staged | BLOQUEADO | Origen indeterminado | MEDIO |

### 5.4 Código de Producción No Staged

| Archivo | Estado Git | Decisión | Evidencia | Riesgo |
|---------|-----------|----------|----------|-------|
| transform.py | M | BLOQUEADO | Relación con staged desconocida | ALTO |
| quaternion.py | MM | BLOQUEADO | Relación con staged desconocida | ALTO |
| vector3.py | MM | BLOQUEADO | Relación con staged desconocida | BAJO |
| export/gltf.py | MM | BLOQUEADO | Relación con staged desconocida | MEDIO |
| loader/json_loader.py | MM | BLOQUEADO | Relación con staged desconocida | MEDIO |
| tests/export/test_gltf_export.py | AM | BLOQUEADO | Relación con staged desconocida | MEDIO |

### 5.5 Nuevos Módulos de Dominio

| Directorio | Estado Git | Decisión | Evidencia | Riesgo |
|-----------|-----------|----------|----------|-------|
| src/character_engine/domain/anatomy/osteometry/ | ?? | BLOQUEADO | Origen indeterminado | ALTO |
| src/character_engine/domain/anatomy/pose/ | ?? | BLOQUEADO | Origen indeterminado | ALTO |
| src/character_engine/domain/animation/ | ?? | BLOQUEADO | Origen indeterminado | ALTO |
| src/character_engine/domain/character/ | ?? | BLOQUEADO | Origen indeterminado | ALTO |
| src/character_engine/domain/gameplay/ | ?? | BLOQUEADO | Origen indeterminado | ALTO |
| src/character_engine/domain/rigging/ | ?? | BLOQUEADO | Origen indeterminado | ALTO |
| src/character_engine/domain/tissue/ | ?? | BLOQUEADO | Origen indeterminado | ALTO |
| src/character_engine/domain/trauma/ | ?? | BLOQUEADO | Origen indeterminado | ALTO |

### 5.6 Runtime y Scripts Adicionales

| Directorio/Archivo | Estado Git | Decisión | Evidencia | Riesgo |
|------------------|-----------|----------|----------|-------|
| runtime/blender/ | ?? | BLOQUEADO | Origen indeterminado | MEDIO |
| runtime/godot/ | ?? | BLOQUEADO | Origen indeterminado | MEDIO |
| runtime/upbge/ | ?? | BLOQUEADO | Origen indeterminado | MEDIO |
| scripts/engine_tests.py | ?? | BLOQUEADO | Origen indeterminado | BAJO |
| scripts/export_gameplay_data.py | ?? | BLOQUEADO | Origen indeterminado | BAJO |
| scripts/install_blender_addon.py | ?? | BLOQUEADO | Origen indeterminado | BAJO |

---

## 6. MECANISMO DE PRESERVACIÓN PREVIO

### 6.1 Copia de Seguridad del Estado Actual

**Antes de cualquier recuperación, crear una copia de seguridad completa**:

**Paso 1: Crear directorio de respaldo**
```
mkdir charater_engine_backup_<timestamp>
```

**Paso 2: Copiar working tree completo**
```
xcopy /E /I /H /Y <repositorio> <respaldo>
```

**Paso 3: Exportar staged changes**
```
git diff --cached > <respaldo>/staged_changes.patch
```

**Paso 4: Exportar untracked files**
```
git ls-files --others --exclude-standard > <respaldo>/untracked_files.txt
```

**Paso 5: Guardar estado Git**
```
git status > <respaldo>/git_status.txt
git log --oneline -5 > <respaldo>/git_log.txt
git reflog > <respaldo>/git_reflog.txt
```

**Resultado**: Copia completa del estado actual que puede restaurarse si es necesario

### 6.2 Verificación de Copia de Seguridad

**Paso 6: Verificar integridad**
```
dir <respaldo> /s | find /c "archivos"
```

**Paso 7: Verificar que el respaldo contiene todos los archivos críticos**
- transform.py
- quaternion.py
- vector3.py
- Documentos de auditoría R19

**Resultado**: Confirmación de que la copia de seguridad es completa

---

## 7. SECUENCIA DE RECUPERACIÓN PROPUESTA

### 7.1 Fase 1: Preservación (REQUIERE AUTORIZACIÓN)

**Objetivo**: Preservar todo el trabajo actual antes de cualquier recuperación

**Acciones**:
1. Crear copia de seguridad completa (sección 6)
2. Verificar integridad de copia de seguridad
3. Documentar estado en archivo de log

**Decisión requerida**: Proceder con preservación

**Riesgo**: Ninguno (solo lectura y copia)

### 7.2 Fase 2: Recopilación de Evidencia (REQUIERE AUTORIZACIÓN)

**Objetivo**: Recopilar evidencia de procedencia de cambios staged y no staged

**Acciones**:
1. Preguntar al responsable del proyecto:
   - ¿Cuándo se realizaron los cambios staged?
   - ¿Quién autorizó los cambios staged?
   - ¿Por qué se eliminaron .ai/ y .engine/?
   - ¿Por qué se añadieron .cursor/rules/ y .cursor/skills/?
   - ¿Los cambios staged son trabajo legítimo que debe preservarse?
   - ¿Los cambios no staged en transform.py, quaternion.py, vector3.py son parte del trabajo staged o son posteriores?
   - ¿Existe algún commit o branch en otro repositorio que documente estos cambios?
   - ¿Qué debe hacerse con los nuevos módulos de dominio?

2. Investigar si existe alguna referencia externa (issue tracker, documentation, comunicación) que explique los cambios

**Decisión requerida**: Confirmar si los cambios staged son trabajo legítimo

**Riesgo**: Ninguno (solo recopilación de información)

### 7.3 Fase 3: Separación de Cambios (REQUIERE AUTORIZACIÓN)

**Caso A: Si cambios staged son trabajo legítimo que debe preservarse**

**Acciones**:
1. Commit de cambios staged
2. Deshacer cambios no staged que sean posteriores al trabajo staged
3. Preservar documentos de auditoría R19
4. Preservar documentos de auditoría R6-R18
5. Preservar nuevos módulos de dominio si son legítimos

**Caso B: Si cambios staged NO son trabajo legítimo**

**Acciones**:
1. Deshacer cambios staged: `git reset HEAD`
2. Deshacer cambios no staged: `git restore .`
3. Eliminar archivos sin seguimiento no deseados
4. Preservar documentos de auditoría R19 (son trabajo legítimo)
5. Preservar documentos de auditoría R6-R18 (son trabajo legítimo)

**Caso C: Si hay evidencia mixta**

**Acciones**:
1. Separar cambios staged legítimos de no legítimos
2. Commit de cambios legítimos
3. Deshacer cambios no legítimos
4. Para cambios no seguros, mantener en branch separado para revisión

**Decisión requerida**: Qué cambios preservar y cuáles deshacer

**Riesgo**: ALTO si se deshace trabajo legítimo por error

### 7.4 Fase 4: Recuperación Selectiva (REQUIERE AUTORIZACIÓN)

**Objetivo**: Recuperar solo cambios específicos si se identifican como no autorizados

**Acciones**:
1. Para cambios no staged que se identifican como no autorizados:
   - `git restore <archivo>`
2. Para cambios staged que se identifican como no autorizados:
   - `git reset HEAD <archivo>`
3. Para archivos sin seguimiento que se identifican como no autorizados:
   - Eliminar manualmente

**Decisión requerida**: Qué archivos específicos recuperar

**Riesgo**: MEDIO si se comete error en identificación

---

## 8. CRITERIOS DE ACEPTACIÓN

### 8.1 Criterios para Proceder con Recuperación

**Antes de proceder con cualquier recuperación, se debe**:
1. Tener copia de seguridad completa verificada
2. Tener respuesta del responsable del proyecto sobre procedencia de cambios staged
3. Tener respuesta del responsable del proyecto sobre procedencia de cambios no staged
4. Tener aprobación explícita para el plan de recuperación
5. Tener aprobación explícita para cada fase del plan

### 8.2 Criterios de Éxito de Recuperación

**La recuperación se considera exitosa si**:
1. Todos los cambios no autorizados han sido eliminados
2. Todos los cambios autorizados han sido preservados
3. El repositorio está en un estado coherente
4. Los tests pasan (si aplica)
5. La integridad matemática del repositorio es verificable

---

## 9. RIESGOS RESIDUALES

### 9.1 Riesgos de Decisión

**ALTO**:
- Si se decide deshacer cambios staged sin evidencia suficiente, podría perderse trabajo legítimo masivo
- Si se decide preservar cambios staged sin evidencia suficiente, podrían persistir cambios no autorizados

**MEDIO**:
- Si se decide parcialmente qué preservar, podría crearse un estado híbrido inconsistente

### 9.2 Riesgos de Ejecución

**BAJO** (si se sigue el plan correctamente):
- Si se sigue la secuencia de preservación antes de recuperación
- Si se obtienen respuestas del responsable del proyecto
- Si se realiza copia de seguridad verificada

**ALTO** (si no se sigue el plan):
- Si se ejecutan restauraciones sin copia de seguridad
- Si se ejecutan restauraciones sin autorización
- Si se ejecutan restauraciones sin entender la procedencia de cambios

---

## 10. OPERACIONES QUE REQUIEREN AUTORIZACIÓN EXPLÍCITA

Todas las siguientes operaciones requieren autorización explícita del responsable del proyecto:

1. **Crear copia de seguridad** (Fase 1)
2. **Recopilar evidencia de procedencia** (Fase 2)
3. **Separar cambios legítimos de no legítimos** (Fase 3)
4. **Ejecutar git reset HEAD** (Fase 3, caso B)
5. **Ejecutar git restore** (Fase 3, caso B)
6. **Eliminar archivos sin seguimiento** (Fase 3, caso B)
7. **Commit de cambios legítimos** (Fase 3, caso A)
8. **Crear branch separado para revisión** (Fase 3, caso C)
9. **Recuperación selectiva de archivos específicos** (Fase 4)
10. **Corregir defectos matemáticos en Quaternion.inverse() y Transform.inverse()** (fase posterior, no en este plan)

---

## 11. SEPARACIÓN DE RECUPERACIÓN Y CORRECCIONES MATEMÁTICAS

### 11.1 Recuperación del Repositorio

**Objetivo**: Restaurar integridad del repositorio a un estado conocido y autorizado

**Alcance**: Cambios staged, cambios no staged, archivos sin seguimiento

**Relación con R19**: R19 identificó modificaciones no autorizadas pero no procedió a recuperación

**Estado**: Bloqueado hasta que se resuelva procedencia de cambios

### 11.11 Correcciones Matemáticas Futuras

**Objetivo**: Corregir defectos matemáticos identificados en auditorías R6-R19

**Defectos identificados**:
- Quaternion.inverse(): divide por ||q|| en lugar de ||q||²
- Transform.inverse(): fórmula de posición incorrecta para escala no uniforme
- Frame convention: discrepancia entre implementación (spatial) y comentario (body)

**Estado**: Bloqueado hasta que se resuelva procedencia de cambios en repositorio

**Relación**: La recuperación del repositorio es un prerrequisito para cualquier corrección matemática, pero las correcciones matemáticas son una fase posterior y separada

---

## 12. VEREDICTO

**ESTADO**: `PLAN_READY_FOR_REVIEW`

**Justificación**:
- Se ha diseñado un plan de recuperación reversible y conservador
- Se ha identificado claramente qué cambios deben preservarse (documentos R19, R6-R18)
- Se ha clasificado cada cambio según riesgo y evidencia disponible
- Se ha propuesto un mecanismo de preservación previo (copia de seguridad completa)
- Se ha diseñado una secuencia de recuperación con fases claras
- Se han identificado todas las operaciones que requieren autorización explícita
- Se ha separado claramente la recuperación del repositorio de las correcciones matemáticas futuras
- El plan NO autoriza su ejecución ni desbloquea CE-Q4

**Próximos pasos requeridos**:
1. Autorización para crear copia de seguridad
2. Respuestas del responsable del proyecto sobre procedencia de cambios staged
3. Autorización para proceder con Fase 2 (recopilación de evidencia)
4. Autorización para proceder con Fase 3 (separación de cambios)

---

**END OF S2-D1-R20-B-RECOVERY-PLAN**
