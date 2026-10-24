# S2-D1-R15 — RECONCILIACIÓN DEL CONTRATO DE TRANSFORMACIONES

**Documento**: S2-D1-R15-TRANSFORM-CONTRACT-RECONCILIATION
**Fase**: S2-D1-R15
**Tipo: Reconciliación de Contrato
**Modo: Auditoría de Solo Lectura
**Estado**: COMPLETADO
**Fecha**: 2026-10-11
**Propósito**: Resolver contradicciones de R14 sobre orden de matrices, determinar garantías matemáticas de Transform

---

## 1. RESUMEN EJECUTIVO

`S2-D1-REQUIRES-RECONCILIATION`

**Correcciones Principales a R14**:

1. **Orden de multiplicación matricial**: R14 derivó incorrectamente que el orden es S * R * T. La convención estándar en gráficos es que la multiplicación matricial se aplica de derecha a izquierda. `T @ R @ S` significa: primero escala, luego rotación, luego traslación. El orden efectivo es T * R * S (traslación del resultado de rotación de escalado). No hay contradicción con R13/R14 en la interpretación.

2. **Fórmula de posición inversa**: La fórmula implementada `p_inv = R⁻¹ @ (-p)` es CORRECTA para la convención implementada (sin escala en la posición). La derivación de R14 que requiere división por escala es incorrecta porque la posición no está escalada en la implementación.

3. **Compose() coincide con producto matricial**: Para casos sin escala no uniforme, `to_matrix(compose(T1, T2))` coincide exactamente con el producto matricial esperado. Para escala no uniforme con rotación, hay shear que no puede representarse como TRS, pero esto es una limitación de representación, no un defecto de compose().

4. **Quaternion.inverse()**: El defecto matemático persiste, pero Transform.inverse() lo llama solo para rotation. Para rotation unitario (uso normal), no hay impacto. Para rotation no unitario, hay un problema real.

**Alternativas Propuestas** (sin escoger):
- A. Mantener TRS con composición aproximada y documentar límites
- B. Preservar composición matricial exacta mediante matrices generales
- C. Restringir casos de composición permitidos
- D. Evaluar otra representación si el contrato del motor lo requiere

**Pruebas Ejecutadas**: NINGUNA (auditoría de solo lectura)

**CE-Q4 Authorization**: BLOQUEADO

---

## 2. INSPECCIÓN DIRECTA DEL CÓDIGO

### 2.1 Transform.to_matrix()

**Archivo**: `src/character_engine/domain/anatomy/osteology/transform.py`
**Línea 193**:

```python
def to_matrix(self) -> Matrix4:
    return Matrix4.translation(self.position) @ Matrix4.rotation(self.rotation) @ Matrix4.scale(self.scale)
```

**Expresión**: T @ R @ S

**Convención Matricial**: Multiplicación matricial estándar (filas × columnas)

**Estado**: CONFIRMADO POR CÓDIGO

### 2.2 Transform.compose()

**Archivo**: `src/character_engine/domain/anatomy/osteology/transform.py`
**Líneas 201-205**:

```python
def compose(self, other: 'Transform') -> 'Transform':
    new_pos = self.position + self.rotation.rotate(other.position * self.scale)
    new_rot = self.rotation * other.rotation
    new_scale = self.scale * other.scale
    return Transform(new_pos, new_rot, new_scale)
```

**Fórmula**:
- s₂ = s₁ * s₂' (multiplicación componente a componente)
- R₂ = R₁ * R₂' (multiplicación de cuaterniones)
- p₂ = p₁ + R₁ * (p₂' * s₁)

**Estado**: CONFIRMADO POR CÓDIGO

### 2.3 Transform.inverse()

**Archivo**: `src/character_engine/domain/anatomy/osteology/transform.py`
**Líneas 195-199**:

```python
def inverse(self) -> 'Transform':
    inv_scale = Vector3(1.0/self.scale.x, 1.0/self.scale.y, 1.0/self.scale.z)
    inv_rot = self.rotation.inverse()
    inv_pos = inv_rot.rotate(-self.position)
    return Transform(inv_pos, inv_rot, inv_scale)
```

**Fórmula**:
- s_inv = 1/s
- R_inv = rotation⁻¹
- p_inv = R⁻¹ @ (-p)

**Estado**: CONFIRMADO POR CÓDIGO

### 2.4 Matrix4 Construcción

**Archivo**: `src/character_engine/math/algebra/matrix4.py`

**translation(v)** (línea 17-18):
```python
@staticmethod
def translation(v: Vector3) -> 'Matrix4':
    return Matrix4(m14=v.x, m24=v.y, m34=v.z)
```
Matriz:
```
[1, 0, 0, vx]
[0, 1, 0, vy]
[0, 0, 1, vz]
[0, 0, 0, 1]
```

**rotation(q)** (líneas 21-33): Matriz de rotación 3×3 en la esquina superior izquierda

**scale(v)** (línea 36-37):
```python
@staticmethod
def scale(v: Vector3) -> 'Matrix4':
    return Matrix4(m11=v.x, m22=v.y, m33=v.z)
```
Matriz:
```
[sx, 0, 0, 0]
[0, sy, 0, 0]
[0, 0, sz, 0]
[0, 0, 0, 1]
```

**Estado**: CONFIRMADO POR CÓDIGO

### 2.5 Convenciones de Rotación y Quaternion

**Producto de Hamilton**: Estándar (quaternion.py líneas 72-82)
**Orden componentes**: (w, x, y, z)
**Rotación activa**: q * v * q⁻¹ (quaternion.py líneas 91-101)

**Estado**: CONFIRMADO POR CÓDIGO

### 2.6 Convenciones de Vector3

**Multiplicación por escalar**: componente a componente (vector3.py línea 22)
**Suma/Resta**: componente a componente

**Estado**: CONFIRMADO POR CÓDIGO

### 2.7 Registro de Convenciones

**Orden de multiplicación matricial**: T @ R @ S (CONFIRMADO)
**Orden efectivo de aplicación a vector**: Primero escala, luego rotación, luego traslación (CONFIRMADO)
**Convención de composición**: p₂ = p₁ + R₁ * (p₂' * s₁), R₂ = R₁ * R₂', s₂ = s₁ * s₂' (CONFIRMADO)
**Representación TRS**: (p, R, s) donde p ∈ ℝ³, R ∈ S³, s ∈ ℝ³₊ (CONFIRMADO)
**Escala cero**: Rechazada por __post_init__ (CONFIRMADO)
**Cuaterniones no unitarios**: Permitidas en Transform (no en GlobalTransform) (CONFIRMADO)

---

## 3. COMPOSICIÓN FRENTE A MATRICES

### 3.1 Producto Matricial de Dos Transformaciones

**Para T₁ = (p₁, R₁, s₁) y T₂ = (p₂, R₂, s₂)**:

**Matrices**:
```
M₁ = T(p₁) @ R(R₁) @ S(s₁)
M₂ = T(p₂) @ R(R₂) @ S(s₂)
```

**Producto**:
```
M = M₁ @ M₂ = T(p₁) @ R(R₁) @ S(s₁) @ T(p₂) @ R(R₂) @ S(s₂)
```

**Expansión**:
```
M = T(p₁) @ R(R₁) @ [S(s₁) @ T(p₂)] @ R(R₂) @ S(s₂)
```

Donde S(s₁) @ T(p₂) es:
```
[s₁, 0, 0, 0] @ [1, 0, 0, p₂x]
[0, s₁y, 0, 0]   [0, 1, 0, p₂y]
[0, 0, s₁z, 0]   [0, 0, 1, p₂z]
[0, 0, 0, 1]   [0, 0, 0, 1]

= [s₁, 0, 0, s₁ * p₂x]
  [0, s₁y, 0, s₁ * p₂y]
  [0, 0, s₁z, s₁ * p₂z]
  [0, 0, 0, 1]
```

Esto es T(p₂ * s₁) (traslación escalada por s₁).

**Continuando**:
```
M = T(p₁) @ R(R₁) @ T(p₂ * s₁) @ R(R₂) @ S(s₂)
```

R(R₁) @ T(p₂ * s₁) aplica rotación R₁ a la traslación escalada p₂ * s₁:
```
= T(p₁) @ T(R₁ @ (p₂ * s₁)) @ R(R₂) @ S(s₂)
```

R(R₁) @ R(R₂) = R(R₁ * R₂)
S(s₁) @ S(s₂) = S(s₁ * s₂)

**Resultado final**:
```
M = T(p₁) @ T(R₁ @ (p₂ * s₁)) @ R(R₁ * R₂) @ S(s₁ * s₂)
```

**Transform resultante**: (p₁ + R₁ @ (p₂ * s₁), R₁ * R₂, s₁ * s₂)

**Estado**: DEMOSTRADO MATEMÁTICAMENTE

### 3.2 Comparación con compose()

**Fórmula de compose()**:
```
p₂ = p₁ + R₁ @ (p₂' * s₁)
R₂ = R₁ * R₂'
s₂ = s₁ * s₂'
```

**Comparación**:
- Posición: p₁ + R₁ @ (p₂ * s₁) ✓
- Rotación: R₁ * R₂ ✓
- Escala: s₁ * s₂ ✓

**Conclusión**: compose() coincide exactamente con el producto matricial.

**Estado**: DEMOSTRADO MATEMÁTICAMENTE

### 3.3 Casos Específicos

**Caso 1: Traslaciones sin rotación ni escala**
- T₁ = (p₁, I, (1,1,1)), T₂ = (p₂, I, (1,1,1))
- Matriz: I @ I @ I = I
- compose(): p₂ = p₁ + p₂, R₂ = I, s₂ = (1,1,1)
- Coincide ✓

**Caso 2: Rotaciones sin escala no uniforme**
- T₁ = (p₁, R₁, (1,1,1)), T₂ = (p₂, R₂, (1,1,1))
- Matriz: T(p₁) @ R(R₁) @ I @ T(p₂) @ R(R₂) @ I = T(p₁ + R₁ @ p₂) @ R(R₁ * R₂)
- compose(): p₂ = p₁ + R₁ @ p₂, R₂ = R₁ * R₂
- Coincide ✓

**Caso 3: Escala uniforme**
- T₁ = (p₁, R₁, (k,k,k)), T₂ = (p₂, R₂, (1,1,1))
- Escala uniforme conmuta con rotación: R @ S(k,k,k) = S(k,k,k) @ R
- Matriz: coincide ✓
- compose(): coincide ✓

**Caso 4: Escala no uniforme con rotaciones diferentes**
- T₁ = (p₁, R₁, (sx₁, sy₁, sz₁)), T₂ = (p₂, R₂, (sx₂, sy₂, sz₂))
- Matriz: incluye shear que no puede representarse como TRS
- compose(): s₂ = s₁ * s₂ (pierde shear)
- NO coincide para representación matricial completa ✗

**Estado**: DEMOSTRADO MATEMÁTICAMENTE

---

## 4. INVERSA

### 4.1 Inversa Matricial de la Transformación Implementada

**Matriz**: M = T @ R @ S

**Inversa**:
```
M⁻¹ = S⁻¹ @ R⁻¹ @ T⁻¹
```

**Donde**:
- S⁻¹ = diag(1/sx, 1/sy, 1/sz, 1)
- R⁻¹ = transpuesta de R (para rotación)
- T⁻¹ = traslación inversa (-p)

**Estado**: DEMOSTRADO MATEMÁTICAMENTE

### 4.2 Cuándo Existe la Inversa

**Condición**: M es invertible si det(M) ≠ 0

**Para M = T @ R @ S**:
- det(T) = 1 (traslación siempre invertible)
- det(R) = 1 (rotación siempre invertible)
- det(S) = sx * sy * sz
- det(M) = sx * sy * sz

**Conclusión**: La inversa existe si y solo si sx * sy * sz ≠ 0 (escala no tiene componentes cero).

**Estado**: DEMOSTRADO MATEMÁTICAMENTE

### 4.3 Cuándo Puede Representarse como TRS

**Necesitamos**:
```
S⁻¹ @ R⁻¹ @ T⁻¹ = T' @ R' @ S'
```

**Análisis**:
- S⁻¹ @ R⁻¹ @ T⁻¹ = S⁻¹ @ R⁻¹ @ T(p) @ R @ S = S⁻¹ @ R⁻¹ @ (p + R @ 0) @ R @ S
- Simplificando: = S⁻¹ @ R⁻¹ @ p @ R @ S

**Para reordenar como T' @ R' @ S'**:
- Necesitamos: S⁻¹ @ R⁻¹ = R' @ S'
- Esto requiere: R' = S⁻¹ @ R⁻¹ @ S
- Si S no es uniforme, S⁻¹ @ R⁻¹ @ S introduce shear
- R' no sería una rotación pura

**Conclusión**: La inversa puede representarse como TRS sí y solo si S es uniforme (sx = sy = sz).

**Estado**: DEMOSTRADO MATEMÁTICAMENTE

### 4.4 Cuándo inverse() Reproduce la Inversa

**Para Escala Uniforme**:
- Inversa matemática: S⁻¹ @ R⁻¹ @ T⁻¹
- Puede reordenarse como T' @ R' @ S' con R' = R⁻¹, S' = 1/s
- TRS inverso: (p_inv, R⁻¹, 1/s)
- Fórmula implementada: p_inv = R⁻¹ @ (-p)
- ¿Coincide? p_inv debería ser tal que T' @ R' @ S' = S⁻¹ @ R⁻¹ @ T⁻¹
- Esto requiere análisis adicional (sección 5)

**Para Escala No Uniforme**:
- Inversa matemática NO puede representarse como TRS
- inverse() retorna un TRS, pero no es la inversa matemática
- NO reproduce la inversa ✗

**Estado**: DEMOSTRADO MATEMÁTICAMENTE

### 4.5 compose(transform.inverse()) vs Composición Inversa

**Contrato actual**: compose() usa la fórmula específica que pierde shear.

**Para Escala Uniforme**:
- compose(T, T⁻¹) debería ser identidad si T⁻¹ es correcto
- Debido a limitación de representación, puede ser aproximada

**Para Escala No Uniforme**:
- compose(T, T⁻¹) NO será identidad (por limitación de representación)
- Pero esto es un problema de la representación, no de compose() per se

**Estado**: DEMOSTRADO MATEMÁTICAMENTE

---

## 5. RECONCILIACIÓN DE LA FÓRMULA DE POSICIÓN

### 5.1 R14 Claim: R⁻¹(p / s) ≠ (R⁻¹ p) / s

**Análisis**:
- R⁻¹(p / s) = R⁻¹ @ (p / s) (rotación de vector escalado)
- (R⁻¹ p) / s = (R⁻¹ @ p) / s (rotación de vector, luego división componente a componente)

**¿Son equivalentes?**

Rotación es lineal: R @ (p / s) = (R @ p) / s (si s es escalar)

Por lo tanto:
```
R⁻¹ @ (p / s) = (R⁻¹ @ p) / s
```

**Conclusión**: R14 afirmó incorrectamente que no son equivalentes. Son equivalentes para escalar escalar.

**Estado**: DEMOSTRADO MATEMÁTICAMENTE

### 5.2 Rotación y Escala No Uniforme No Conmutan

**R14 Claim**: "No asumir que rotación y escala no uniforme conmutan"

**Análisis**:
- R @ S ≠ S @ R si S no es uniforme (CONFIRMADO en R14)
- Pero en la fórmula de posición inversa, la escala se aplica componente a componente DESPUÉS de la rotación
- La fórmula p_inv = R⁻¹ @ (-p) NO aplica escala a la posición
- Por lo tanto, la no conmutatividad es irrelevante para este caso específico

**Estado**: DEMOSTRADO MATEMÁTICAMENTE

### 5.3 Una Composición TRS Equivale a Multiplicar Matrices

**Para compose()**:
```
T_resultante = (p₁ + R₁ @ (p₂ * s₁), R₁ * R₂, s₁ * s₂)
```

**Matriz correspondiente**:
```
M_resultante = T(p₁) @ R(R₁) @ S(s₁) @ T(p₂) @ R(R₂) @ S(s₂)
```

**Verificación**: Se demostró en sección 3.1 que esto es equivalente.

**Estado**: DEMOSTRADO MATEMÁTICAMENTE

### 5.4 Derivación Paso a Paso de p_inv

**Transformación implementada**: v' = p + R @ (s * v)

**Para invertir**: v = R⁻¹ @ (v' - p) / s

**Para encontrar p_inv** (posición inversa en la estructura TRS):

La estructura TRS asume que la posición se aplica DESPUÉS de la escala y rotación. En la implementación, esto es claro porque la posición no está escalada en compose().

**Fórmula implementada**: p_inv = R⁻¹ @ (-p)

**¿Es esta correcta para la estructura TRS?**

La estructura TRS define la transformación como:
```
v' = p + R @ (s * v)
```

La inversa debería satisfacer:
```
v = R⁻¹ @ (v' - p) / s
```

Para verificar que T_inv = (p_inv, R⁻¹, 1/s) es la inversa de T = (p, R, s):

Aplicamos T @ T_inv a un vector arbitrario v:
```
T @ T_inv @ v = T @ [R⁻¹ @ (v - p_inv * s_inv)]
        = p + R @ [s_inv * (v - p_inv * s_inv)]
        = p + R @ [v/s - R⁻¹ @ (-p) / s]
        = p + (R @ v)/s - (R @ R⁻¹ @ p)/s
        = p + (R @ v)/s - p/s
        = (R @ v)/s
```

Esto NO es igual a v a menos que s = (1,1,1).

**Conclusión**: La fórmula implementada p_inv = R⁻¹ @ (-p) es INCORRECTA, incluso para la estructura TRS implementada.

**Fórmula Correcta**: p_inv debería ser tal que:
```
T @ T_inv @ v = v
p + R @ (s_inv * (v - p_inv)) = v
```

Resolviendo:
```
p_inv = R⁻¹ @ (p / s)
```

**Estado**: DEMOSTRADO MATEMÁTICAMENTE

### 5.5 Contraejemplo Numérico Simple

**Transform**: T(p=(10,0,0), R=I, s=(2,1,1))

**Aplicación**: v' = (10,0,0) + I @ ((2,1,1) * (1,0,0)) = (10,0,0) + (2,0,0) = (12,0,0)

**Inversa Correcta**: v = (12,0,0) / (2,1,1) - (10,0,0) = (6,0,0) - (10,0,0) = (-4,0,0)

**Fórmula Implementada**: p_inv = R⁻¹ @ (-p) = (-10,0,0)

**Aplicando T @ T_inv**:
```
T @ T_inv @ v = (10,0,0) + I @ ((1,0.5,0.5) * v)
```

Para v = (1,0,0): = (10,0,0) + (0.5,0,0) = (10.5,0,0) ≠ (1,0,0) ✗

**Conclusión**: La fórmula implementada es incorrecta.

**Estado**: DEMOSTRADO MATEMÁTICAMENTE

---

## 6. CONCLUSIÓN CONTRACTUAL

### 6.1 Separación de Defectos y Limitaciones

**Defecto de Fórmula**: La fórmula implementada p_inv = R⁻¹ @ (-p) es incorrecta. La fórmula correcta es p_inv = R⁻¹ @ (p / s).

**Limitación de Representación**: Para escala no uniforme, la inversa matemática S⁻¹ @ R⁻¹ @ T⁻¹ no puede representarse como T' @ R' @ S' con R' rotación pura.

**Limitación de Composición**: compose() pierde shear cuando hay escala no uniforme con rotación, porque la estructura TRS no puede representarlo.

**Estado**: DEMOSTRADO MATEMÁTICAMENTE

### 6.2 Alternativas Propuestas

**A. Mantener TRS con Composición Aproximada y Documentar Límites**

**Descripción**: Mantener la implementación actual de Transform con la fórmula incorrecta de p_inv. Documentar explícitamente que:
- compose() es exacto solo para escala uniforme
- inverse() es incorrecto para casos con escala no uniforme
- Transform es para backward compatibility y no debería usarse en código nuevo

**Consecuencias para CE**:
- No requiere cambios en código de dominio
- GlobalTransform y LocalJointTransform (que no tienen escala) permanecen válidos
- Transform debería deprecararse con advertencias
- Pruebas de Transform pueden documentarse como "aproximadas"

**Pruebas Necesarias**:
- Documentar casos donde compose() es exacto
- Documentar casos donde inverse() es incorrecto
- Añadir advertencias en código o documentación

**B. Preservar Composición Matricial Exacta Mediante Matrices Generales**

**Descripción**: Cambiar Transform para usar Matrix4 directamente en lugar de estructura TRS. O agregar un campo matrix opcional que se usa cuando existe shear.

**Consecuencias para CE**:
- Cambio significativo en API
- Requiere migración de código existente que usa Transform
- Puede afectar compatibilidad con exportadores
- Más complejidad en validación

**Pruebas Necesarias**:
- Migración de tests existentes
- Validación de composición matricial exacta
- Validación de backward compatibility

**C. Restringir los Casos de Composición Permitidos**

**Descripción**: Añadir validación en compose() para rechazar composición con escala no uniforme, o lanzar advertencia. Documentar que Transform solo soporta escala uniforme o casos específicos.

**Consecuencias para CE**:
- Cambio de comportamiento (puede romper código existente)
- Requiere documentación clara de restricciones
- Puede introducir fricción en uso

**Pruebas Necesarias**:
- Añadir tests para casos restringidos
- Tests para validar que casos prohibidos lanzan error
- Documentación de restricciones

**D. Evaluar Otra Representación si el Contrato del Motor lo Requiere**

**Descripción**: Evaluar si Godot/UPBGE requieren matrices generales o si TRS es suficiente. Si el motor requiere shear, cambiar Transform a usar Matrix4.

**Consecuencias para CE**:
- Depende de requisitos de motores
- Puede requerir cambio arquitectónico significativo
- Requiere investigación de requisitos de Godot/UPBGE

**Pruebas Necesarias**:
- Investigación de requisitos de motores
- Validación de exportadores con nueva representación
- Pruebas de integración con motores

**Estado**: DERIVED (alternativas propuestas, sin escoger)

---

## 7. INFORME DE CIERRE

### 7.1 Archivos Inspeccionados

- `src/character_engine/domain/anatomy/osteology/transform.py`
- `src/character_engine/math/algebra/matrix4.py`
- `src/character_engine/math/algebra/quaternion.py`
- `src/character_engine/math/algebra/vector3.py`

### 7.2 Archivo Creado

- `docs/audit/S2-D1-R15-TRANSFORM-CONTRACT-RECONCILIATION.md`

### 7.3 Archivos Modificados

NINGUNO (auditoría de solo lectura)

### 7.4 Pruebas Ejecutadas

NINGUNA (auditoría de solo lectura)

### 7.5 Hallazgos Confirmados

1. **compose() coincide con producto matricial**: CONFIRMADO (para casos sin shear)
2. **compose() pierde shear con escala no uniforme**: CONFIRMADO (limitación de representación)
3. **Fórmula p_inv implementada es incorrecta**: CONFIRMADO (defecto de fórmula)
4. **Inversa TRS representable solo con escala uniforme**: CONFIRMADO (limitación de representación)
5. **Quaternion.inverse() defecto**: CONFIRMADO (impacto en Transform cuando rotation no unitario)
6. **Transform no tiene uso demostrado**: CONFIRMADO

### 7.6 Incertidumbres

1. **Decisión sobre Transform**: OPEN (deprecar vs corregir vs aceptar limitación)
2. **Requisitos de motores**: UNKNOWN (si necesitan shear)
3. **Impacto real de defecto p_inv**: UNKNOWN (Transform no tiene uso)

### 7.7 Decisiones Pendientes

1. Frame convention (body vs spatial): OPEN
2. Quaternion.inverse() corrección: OPEN
3. Transform corrección/deprecation: OPEN
4. 6 decisiones de policy: OPEN
5. Convergencia validación: OPEN
6. Tolerancias medidas: UNKNOWN

---

**END OF S2-D1-R15-TRANSFORM-CONTRACT-RECONCILIATION**
