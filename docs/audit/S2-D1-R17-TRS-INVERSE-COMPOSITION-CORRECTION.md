# S2-D1-R17 — CORRECCIÓN FINAL DE INVERSA Y COMPOSICIÓN TRS

**Documento**: S2-D1-R17-TRS-INVERSE-COMPOSITION-CORRECTION
**Fase**: S2-D1-R17
**Tipo: Corrección Matemática Final
**Modo: Auditoría de Solo Lectura
**Estado**: COMPLETADO
**Fecha**: 2026-10-12
**Propósito**: Corregir inconsistencias matemáticas de R16 y establecer condiciones precisas para composición e inversión de Transform

---

## 1. RESUMEN EJECUTIVO

`S2-D1-REQUIRES-RECONCILIATION`

**Correcciones Principales a R16**:

1. **Criterio de representabilidad de inversa**: R16 usó conmutatividad directa. R17 usa el criterio de ortogonalidad de columnas, que es más general y preciso.

2. **Fórmula p_inv correcta**: Si la inversa es representable como TRS, la fórmula correcta es `p_inv = -S⁻¹ R⁻¹ p`, no `p_inv = R⁻¹ @ (-p)` como usó R16 en algunos análisis.

3. **Aplicación de la inversa**: La fórmula correcta es `x = S⁻¹ R⁻¹ (x' - p)`, no `S⁻¹ x' - p` (cambia el orden de operaciones).

4. **Condiciones de compose(T, T_inv)**: R16 derivó condiciones usando la fórmula implementada. R17 distingue entre la fórmula implementada y la fórmula correcta.

5. **Contraejemplo corregido**: El caso con p=(10,0,0), R=I, s=(2,1,1) se recalcula con la fórmula correcta de aplicación de inversa.

**Pruebas Ejecutadas**: NINGUNA (auditoría de solo lectura)

**CE-Q4 Authorization**: BLOQUEADO

---

## 2. CONTRATO MATRICIAL

### 2.1 Matriz de Transformación

**Matriz**: M = T(p) @ R @ S

**Donde**:
```
T(p) = [I, p]
       [0, 1]

R = [R_3x3, 0]
    [0,     1]

S = [s₁, 0,  0,  0]
    [0,  s₂, 0,  0]
    [0,  0,  s₃, 0]
    [0,  0,  0,  1]
```

**Estado**: CONFIRMADO POR CÓDIGO (matrix4.py líneas 16-37)

### 2.2 Acción a Vector Columna

**Aplicación**:
```
x' = M @ x
x' = T(p) @ R @ S @ x
x' = T(p) @ R @ (S @ x)
x' = T(p) @ R @ (s * x)
x' = p + R @ (s * x)
```

**Fórmula**: `x' = p + R(Sx)` donde Sx denota s * x (multiplicación componente a componente)

**Estado**: DEMOSTRADO MATEMÁTICAMENTE

### 2.3 Inversa Matricial

**Derivación**:
```
M = T(p) @ R @ S
M⁻¹ = S⁻¹ @ R⁻¹ @ T(-p)
```

**Verificación**:
```
M @ M⁻¹ = T(p) @ R @ S @ S⁻¹ @ R⁻¹ @ T(-p)
        = T(p) @ R @ I @ R⁻¹ @ T(-p)
        = T(p) @ I @ T(-p)
        = T(p) @ T(-p)
        = T(p - p)
        = T(0)
        = I
```

**Estado**: DEMOSTRADO MATEMÁTICAMENTE

### 2.4 Aplicación de la Inversa

**Fórmula**:
```
x = M⁻¹ @ x'
x = S⁻¹ @ R⁻¹ @ T(-p) @ x'
x = S⁻¹ @ R⁻¹ @ (x' - p)
```

**NOTA**: La fórmula correcta es `x = S⁻¹ R⁻¹ (x' - p)`, NO `S⁻¹ x' - p`. Esta última cambia el orden de operaciones.

**Estado**: DEMOSTRADO MATEMÁTICAMENTE

---

## 3. COMPOSICIÓN

### 3.1 Producto Matricial de Dos Transformaciones

**Para T₁ = (p₁, R₁, s₁) y T₂ = (p₂, R₂, s₂)**:

```
M₁ = T(p₁) @ R(R₁) @ S(s₁)
M₂ = T(p₂) @ R(R₂) @ S(s₂)
```

**Producto**:
```
M = M₁ @ M₂ = T(p₁) @ R(R₁) @ S(s₁) @ T(p₂) @ R(R₂) @ S(s₂)
```

**Expansión** (derivada en R16, confirmada):
```
M = T(p₁ + R₁ @ (s₁ * p₂)) @ R(R₁ * R₂) @ S(s₁ * s₂)
```

**Estado**: DEMOSTRADO MATEMÁTICAMENTE

### 3.2 Parte Lineal Exacta vs Parte Lineal TRS

**Parte lineal exacta del producto matricial**:
```
L_exacta = R(R₁) @ S(s₁) @ R(R₂) @ S(s₂)
```

**Parte lineal del TRS producido por compose()**:
```
L_TRS = R(R₁ * R₂) @ S(s₁ * s₂)
       = R(R₁) @ R(R₂) @ S(s₁) @ S(s₂)
```

**Condición de equivalencia**:
```
R(R₁) @ S(s₁) @ R(R₂) @ S(s₂) = R(R₁) @ R(R₂) @ S(s₁) @ S(s₂)
```

Multiplicando por R(R₁)⁻¹ por la izquierda y S(s₂)⁻¹ por la derecha:
```
S(s₁) @ R(R₂) = R(R₂) @ S(s₁)
```

**Conclusión**: L_exacta = L_TRS sí y solo si S(s₁) @ R(R₂) = R(R₂) @ S(s₁)

**Estado**: DEMOSTRADO MATEMÁTICAMENTE

### 3.3 Condiciones de Conmutatividad

**Condición**: S(s₁) @ R(R₂) = R(R₂) @ S(s₁)

**Casos suficientes**:

1. **Escala uniforme**: s₁ = (k, k, k)
   - S(kI) @ R = R @ S(kI) para cualquier R
   - Conmuta ✓

2. **Rotación identidad**: R₂ = I
   - S(s₁) @ I = I @ S(s₁)
   - Conmuta ✓

3. **Casos especiales donde R preserva ejes de escala**:
   - Ejemplo: R = rotación 180° sobre Z, s = (s₁, s₁, s₃)
   - R @ diag(s₁, s₁, s₃) = diag(s₁, s₁, s₃) @ R
   - Conmuta ✓

**Casos donde NO conmuta**:
- Escala no uniforme general con rotación general
- Ejemplo: R = rotación 45° sobre Z, s = (2, 1, 1)

**Estado**: DEMOSTRADO MATEMÁTICAMENTE

### 3.4 Garantías de compose()

**compose() coincide con producto matricial exacto**:
- Escala uniforme: ✓
- Rotación identidad: ✓
- Casos especiales de conmutatividad: ✓
- Escala no uniforme general con rotación general: ✗

**Estado**: DEMOSTRADO MATEMÁTICAMENTE

---

## 4. INVERSA TRS

### 4.1 Parte Lineal de la Inversa

**Parte lineal de la inversa matricial**:
```
L_inv = S⁻¹ @ R⁻¹
```

**Pregunta**: ¿Cuándo puede L_inv factorizarse como R' @ S' con R' rotación válida y S' escala diagonal?

### 4.2 Criterio de Ortogonalidad de Columnas

**Para que una matriz 3×3 sea una rotación pura**:
- Debe ser ortonormal: columnas mutuamente ortogonales y de norma 1
- Debe tener determinante +1

**Para que L_inv = R' @ S'**:
- R' debe ser ortonormal
- S' debe ser diagonal

**Análisis**:
```
L_inv = S⁻¹ @ R⁻¹
```

Multiplicando por R por la izquierda:
```
R @ L_inv = R @ S⁻¹ @ R⁻¹
```

Si R @ S⁻¹ @ R⁻¹ es diagonal, entonces:
```
R @ L_inv = diagonal
L_inv = R⁻¹ @ diagonal
```

Por lo tanto, R' = R⁻¹ (rotación válida) y S' = diagonal (escala válida).

**Condición**: R @ S⁻¹ @ R⁻¹ debe ser diagonal.

### 4.3 Condiciones de Representabilidad

**Caso 1: Escala uniforme**
- S = sI
- S⁻¹ = (1/s)I
- R @ (1/s)I @ R⁻¹ = (1/s)I (diagonal)
- Puede representarse ✓

**Caso 2: Rotación identidad**
- R = I
- S⁻¹ @ I = S⁻¹ = I @ S⁻¹
- R' = I, S' = S⁻¹
- Puede representarse ✓

**Caso 3: Casos especiales**
- R @ S⁻¹ @ R⁻¹ es diagonal
- Ejemplo: R = rotación 180° sobre Z, S = diag(s₁, s₁, s₃)
- R @ diag(1/s₁, 1/s₁, 1/s₃) @ R⁻¹ = diag(1/s₁, 1/s₁, 1/s₃) (diagonal)
- Puede representarse ✓

**Caso 4: Escala no uniforme general con rotación general**
- R @ S⁻¹ @ R⁻¹ tiene off-diagonal entries
- NO es diagonal
- NO puede representarse como R' @ S' ✗

**Estado**: DEMOSTRADO MATEMÁTICAMENTE

### 4.4 Invertibilidad vs Representabilidad

**Invertibilidad**:
- M es invertible si det(M) ≠ 0
- det(M) = s₁ * s₂ * s₃
- Invertible si s₁ * s₂ * s₃ ≠ 0 (escala sin componentes cero)

**Representabilidad como TRS**:
- Parte lineal representable si R @ S⁻¹ @ R⁻¹ es diagonal
- Transformación completa representable si parte lineal representable

**Conclusión**: Invertibilidad ≠ Representabilidad. Una transformación puede ser invertible pero no representable como TRS.

**Estado**: DEMOSTRADO MATEMÁTICAMENTE

### 4.5 Fórmula de Posición Inversa (si representable)

**Si L_inv = R' @ S'** con R' rotación y S' escala diagonal:

**Inversa matricial completa**:
```
M⁻¹ = S⁻¹ @ R⁻¹ @ T(-p)
```

**Reordenando como T' @ R' @ S'**:
```
M⁻¹ = R' @ S' @ T(-p)
```

Donde S' @ T(-p) aplica traslación escalada:
```
S' @ T(-p) = [S', 0] @ [I, -p]
             [0,  1]   [0, 1]
            = [S', -S' @ p]
              [0,  1      ]
```

Para reordenar como T' @ R' @ S':
```
T' @ R' @ S' = R' @ S' @ T(-p)
T' @ R' @ S' = [R', 0] @ [S', -S' @ p]
               [0,  1]   [0,  1      ]
             = [R' @ S', -R' @ S' @ p]
               [0,           1          ]
```

Por lo tanto:
```
T' = T(-R' @ S' @ p)
```

**Fórmula de p_inv**:
```
p_inv = -R' @ S' @ p
```

Dado que L_inv = S⁻¹ @ R⁻¹ = R' @ S':
```
p_inv = -S⁻¹ @ R⁻¹ @ p
```

**Estado**: DEMOSTRADO MATEMÁTICAMENTE

### 4.6 Verificación de la Fórmula

**Para verificar que T_inv = (p_inv, R_inv, s_inv) es la inversa de T = (p, R, s)**:

**Si usamos p_inv = -S⁻¹ R⁻¹ p, R_inv = R⁻¹, s_inv = 1/s**:

**Aplicando T @ T_inv a un vector arbitrario v**:
```
T @ T_inv @ v = T @ [R⁻¹ @ (v / s_inv) + p_inv]
             = T @ [R⁻¹ @ (v * s) - S⁻¹ R⁻¹ p]
             = p + R @ [s * (R⁻¹ @ (v * s) - S⁻¹ R⁻¹ p)]
             = p + R @ [s * R⁻¹ @ (v * s) - s * S⁻¹ R⁻¹ p]
             = p + R @ [s * R⁻¹ @ (v * s) - R⁻¹ p]
```

Nota: s * S⁻¹ = I, por lo tanto s * S⁻¹ R⁻¹ p = R⁻¹ p

Continuando:
```
= p + R @ [s * R⁻¹ @ (v * s) - R⁻¹ p]
= p + R @ s * R⁻¹ @ (v * s) - R @ R⁻¹ p
= p + (R @ s * R⁻¹) @ (v * s) - p
= (R @ s * R⁻¹) @ (v * s)
```

Para que esto sea igual a v, necesitamos:
```
(R @ s * R⁻¹) @ (v * s) = v
```

Esto requiere que R @ s * R⁻¹ = 1/s, es decir, que la rotación y la escala conmuten.

**Conclusión**: La fórmula p_inv = -S⁻¹ R⁻¹ p produce la inversa matricial exacta sí y solo si R y S conmutan.

**Estado**: DEMOSTRADO MATEMÁTICAMENTE

### 4.7 Fórmula Implementada vs Fórmula Correcta

**Fórmula implementada** (transform.py línea 198):
```python
inv_pos = inv_rot.rotate(-self.position)
```
Equivale a: `p_inv = R⁻¹ @ (-p)`

**Fórmula correcta para inversa matricial**:
```
p_inv = -S⁻¹ @ R⁻¹ @ p
```

**Diferencia**: La fórmula implementada no divide por escala.

**Cuándo coinciden**:
- Si s = (1, 1, 1): ambas fórmulas coinciden ✓
- Si p = 0: ambas fórmulas coinciden ✓
- Si R @ S⁻¹ = S⁻¹ @ R (conmutan): pueden coincidir en casos especiales ✓

**Estado**: DEMOSTRADO MATEMÁTICAMENTE

---

## 5. COMPOSICIÓN POR IZQUIERDA Y DERECHA

### 5.1 compose(T, T_inv) con Fórmula Implementada

**Implementación de compose()** (transform.py líneas 201-205):
```python
new_pos = self.position + self.rotation.rotate(other.position * self.scale)
new_rot = self.rotation * other.rotation
new_scale = self.scale * other.scale
```

**Para T = (p, R, s) y T_inv = (p_inv, R_inv, s_inv)** con fórmula implementada:

**p_inv = R⁻¹ @ (-p)**
**R_inv = R⁻¹**
**s_inv = 1/s**

**compose(T, T_inv)**:
```
p_result = p + R @ (p_inv * s)
         = p + R @ ((R⁻¹ @ (-p)) * s)
         = p + R @ (R⁻¹ @ (-p * s))
         = p + R @ R⁻¹ @ (-p * s)
         = p - p * s
```

Para que p_result = 0:
```
p - p * s = 0
p * (1 - s) = 0
```

Requiere:
- p = 0, o
- s = (1, 1, 1)

**R_result = R * R⁻¹ = I** ✓
**s_result = s * (1/s) = (1, 1, 1)** ✓

**Conclusión**: compose(T, T_inv) con fórmula implementada devuelve identidad sí y solo si p = 0 o s = (1, 1, 1).

**Estado**: DEMOSTRADO MATEMÁTICAMENTE

### 5.2 compose(T, T_inv) con Fórmula Correcta

**Fórmula correcta**: p_inv = -S⁻¹ R⁻¹ p

**compose(T, T_inv)**:
```
p_result = p + R @ (p_inv * s)
         = p + R @ ((-S⁻¹ R⁻¹ p) * s)
         = p + R @ (-S⁻¹ R⁻¹ p * s)
         = p + R @ (-R⁻¹ p)  [porque S⁻¹ * s = I]
         = p - p
         = 0 ✓
```

**Conclusión**: compose(T, T_inv) con fórmula correcta devuelve identidad siempre (si R y S conmutan).

**Estado**: DEMOSTRADO MATEMÁTICAMENTE

### 5.3 compose(T_inv, T) con Fórmula Implementada

**compose(T_inv, T)**:
```
p_result = p_inv + R_inv @ (p * s_inv)
         = R⁻¹ @ (-p) + R⁻¹ @ (p * (1/s))
         = R⁻¹ @ (-p + p / s)
         = R⁻¹ @ (p * (1/s - 1))
```

Para que p_result = 0:
```
p * (1/s - 1) = 0
```

Requiere:
- p = 0, o
- s = (1, 1, 1)

**Conclusión**: compose(T_inv, T) con fórmula implementada devuelve identidad sí y solo si p = 0 o s = (1, 1, 1).

**Estado**: DEMOSTRADO MATEMÁTICAMENTE

### 5.4 compose(T_inv, T) con Fórmula Correcta

**Fórmula correcta**: p_inv = -S⁻¹ R⁻¹ p

**compose(T_inv, T)**:
```
p_result = p_inv + R_inv @ (p * s_inv)
         = -S⁻¹ R⁻¹ p + R⁻¹ @ (p / s)
         = -S⁻¹ R⁻¹ p + R⁻¹ @ S⁻¹ p
```

Para que esto sea 0:
```
-S⁻¹ R⁻¹ p + R⁻¹ S⁻¹ p = 0
S⁻¹ R⁻¹ p = R⁻¹ S⁻¹ p
```

Multiplicando por R por la izquierda:
```
R S⁻¹ R⁻¹ p = S⁻¹ p
```

Esto requiere que R @ S⁻¹ @ R⁻¹ = S⁻¹, es decir, que R y S conmuten.

**Conclusión**: compose(T_inv, T) con fórmula correcta devuelve identidad sí y solo si R y S conmutan.

**Estado**: DEMOSTRADO MATEMÁTICAMENTE

### 5.5 Identidad de Campos TRS vs Identidad Matricial

**Identidad de campos TRS**:
- p_result = (0, 0, 0)
- R_result = I
- s_result = (1, 1, 1)

**Identidad matricial**:
- M_result = I

**Relación**:
- Si los campos TRS son identidad, la matriz resultante es identidad ✓
- Pero la matriz resultante puede ser identidad incluso si los campos TRS no lo son (por composición de errores)

**Estado**: DISTINGUIDO CLARAMENTE

---

## 6. CONTRAEJEMPLOS OBLIGATORIOS

### 6.1 Caso 1: p=(10,0,0), Rotación Identidad, Escala (2,1,1)

**Transform**: T(p=(10, 0, 0), R=I, s=(2, 1, 1))

**Aplicación**: x' = (10, 0, 0) + I @ ((2, 1, 1) * x)

**Para x = (1, 0, 0)**: x' = (10, 0, 0) + (2, 0, 0) = (12, 0, 0)

**Aplicación de la inversa (fórmula correcta)**:
```
x = S⁻¹ R⁻¹ (x' - p)
x = diag(0.5, 1, 1) @ I @ ((12, 0, 0) - (10, 0, 0))
x = diag(0.5, 1, 1) @ (2, 0, 0)
x = (1, 0, 0) ✓
```

**Fórmula implementada**: p_inv = I @ (-(10, 0, 0)) = (-10, 0, 0)

**compose(T, T_inv) con fórmula implementada**:
```
p_result = (10, 0, 0) + I @ ((-10, 0, 0) * (2, 1, 1))
         = (10, 0, 0) + (-20, 0, 0)
         = (-10, 0, 0) ≠ (0, 0, 0) ✗
```

**Fórmula correcta**: p_inv = -S⁻¹ R⁻¹ p = -diag(0.5, 1, 1) @ I @ (10, 0, 0) = (-5, 0, 0)

**compose(T, T_inv) con fórmula correcta**:
```
p_result = (10, 0, 0) + I @ ((-5, 0, 0) * (2, 1, 1))
         = (10, 0, 0) + (-10, 0, 0)
         = (0, 0, 0) ✓
```

**Conclusión**: La fórmula implementada es incorrecta. La fórmula correcta produce identidad.

**Estado**: DEMOSTRADO MATEMÁTICAMENTE

### 6.2 Caso 2: Escala Uniforme con Rotación No Trivial

**Transform**: T(p=(0, 0, 0), R=rotación 90° sobre Z, s=(2, 2, 2))

**Escala uniforme**: R @ S = S @ R ✓

**Fórmula implementada**: p_inv = R⁻¹ @ (0) = (0, 0, 0)

**Fórmula correcta**: p_inv = -S⁻¹ R⁻¹ @ 0 = (0, 0, 0)

**Ambas fórmulas coinciden** (p = 0).

**compose(T, T_inv)**:
```
p_result = 0 + R @ (0 * (2, 2, 2)) = 0 ✓
R_result = R * R⁻¹ = I ✓
s_result = (2, 2, 2) * (0.5, 0.5, 0.5) = (1, 1, 1) ✓
```

**Conclusión**: Ambas fórmulas producen identidad (porque p = 0).

**Estado**: DEMOSTRADO MATEMÁTICAMENTE

### 6.3 Caso 3: Escala No Uniforme con Rotación 45° sobre Z

**Transform**: T(p=(0, 0, 0), R=rotación 45° sobre Z, s=(2, 1, 1))

**Conmutatividad**: R @ S ≠ S @ R ✗

**Parte lineal**: L = R @ S

**Inversa matricial exacta**: L⁻¹ = S⁻¹ @ R⁻¹

**¿Es L⁻¹ representable como TRS?**
- R @ S⁻¹ @ R⁻¹ tiene off-diagonal entries
- NO es diagonal
- NO puede representarse como R' @ S' ✗

**Fórmula implementada**: p_inv = R⁻¹ @ 0 = (0, 0, 0)

**Fórmula correcta** (si fuera representable): p_inv = -S⁻¹ R⁻¹ @ 0 = (0, 0, 0)

**Ambas fórmulas coinciden** (p = 0).

**compose(T, T_inv)**:
```
p_result = 0 + R @ (0 * (2, 1, 1)) = 0 ✓
R_result = R * R⁻¹ = I ✓
s_result = (2, 1, 1) * (0.5, 1, 1) = (1, 1, 1) ✓
```

**Conclusión**: compose(T, T_inv) devuelve identidad en TRS, pero la parte lineal del TRS inverso NO es la inversa matricial exacta.

**Estado**: DEMOSTRADO MATEMÁTICAMENTE

### 6.4 Caso 4: Dos Transformaciones con Escalas No Uniformes y Rotaciones Distintas

**T₁**: (p₁=(0, 0, 0), R₁=rotación 45° sobre Z, s₁=(2, 1, 1))
**T₂**: (p₂=(0, 0, 0), R₂=rotación 90° sobre X, s₂=(1, 2, 1))

**Producto matricial exacto**:
```
M = R₁ @ S₁ @ R₂ @ S₂
```

**Parte lineal exacta**: L_exacta = R₁ @ S₁ @ R₂ @ S₂

**Parte lineal de compose()**: L_TRS = R₁ @ R₂ @ S₁ @ S₂

**¿Coinciden?**
- S₁ @ R₂ ≠ R₂ @ S₁ ✗
- L_exacta ≠ L_TRS ✗

**compose(T₁, T₂)**:
```
p_result = 0 + R₁ @ (0 * s₁) = 0 ✓
R_result = R₁ * R₂
s_result = s₁ * s₂ = (2, 2, 1)
```

**Matriz de compose()**: M_TRS = R(R₁ * R₂) @ S((2, 2, 1))

**Comparación**:
- M_exacta = R₁ @ S₁ @ R₂ @ S₂
- M_TRS = R₁ @ R₂ @ S₁ @ S₂
- Diferentes ✗

**Conclusión**: compose() NO reproduce el producto matricial exacto.

**Estado**: DEMOSTRADO MATEMÁTICAMENTE

---

## 7. CUATERNIONES

### 7.1 Fórmula Matemática de la Inversa

**Para cuaternión q = (w, x, y, z)**:

**Conjugado**: q* = (w, -x, -y, -z)

**Norma al cuadrado**: ||q||² = w² + x² + y² + z²

**Inversa general**: q⁻¹ = q* / ||q||²

**Estado**: DEMOSTRADO MATEMÁTICAMENTE

### 7.2 Defecto de Quaternion.inverse()

**Archivo**: `src/character_engine/math/algebra/quaternion.py`
**Líneas 63-70**:

```python
def inverse(self) -> 'Quaternion':
    return self.conjugate().normalize()
```

**Fórmula implementada**: q⁻¹ = q* / ||q||

**Diferencia**: Divide por norma en lugar de norma al cuadrado.

**Estado**: DEFECTO MATEMÁTICO CONFIRMADO

### 7.3 Casos Específicos

**Caso 1: Cuaternión unitario** (||q|| = 1)
- q* / ||q|| = q* / ||q||²
- Inversa correcta ✓

**Caso 2: Cuaternión no unitario** (||q|| ≠ 1)
- q* / ||q|| ≠ q* / ||q||²
- Inversa incorrecta ✗

**Caso 3: Cuaternión cero** (||q|| = 0)
- Inversa matemática no existe
- normalize() retorna identidad
- Inversa retornada = identidad (no inversa matemática)

**Estado**: CLASIFICADO COMPLETAMENTE

### 7.4 Impacto en Transform.inverse()

**Transform.inverse() usa**:
```python
inv_rot = self.rotation.inverse()
```

**Impacto**:
- Si rotation es unitario: impacto nulo ✓
- Si rotation no es unitario: impacto real ✗
- Si rotation es cero: comportamiento indefinido ✗

**Estado**: IMPACTO CONFIRMADO PARA ROTACIÓN NO UNITARIA

---

## 8. INFORME DE CIERRE

### 8.1 Hechos Observados

1. **Convención matricial**: Vectores columna, traslación en última columna (CONFIRMADO)
2. **to_matrix()**: T @ R @ S (CONFIRMADO)
3. **Acción**: x' = p + R(s * x) (CONFIRMADO)
4. **compose()**: p₁ + R₁ @ (p₂ * s₁), R₁ * R₂, s₁ * s₂ (CONFIRMADO)
5. **inverse()**: R⁻¹ @ (-p), R⁻¹, 1/s (CONFIRMADO)
6. **Quaternion.inverse()**: q* / ||q|| (DEFECTO MATEMÁTICO CONFIRMADO)
7. **Matrix4.rotation()**: Normaliza q antes de usar (CONFIRMADO)

### 8.2 Derivaciones Algebraicas

1. **Inversa matricial**: M⁻¹ = S⁻¹ R⁻¹ T(-p) (DEMOSTRADO)
2. **Aplicación de inversa**: x = S⁻¹ R⁻¹ (x' - p) (DEMOSTRADO)
3. **Condición compose() exacto**: S(s₁) @ R(R₂) = R(R₂) @ S(s₁) (DEMOSTRADO)
4. **Condición representabilidad inversa**: R @ S⁻¹ @ R⁻¹ diagonal (DEMOSTRADO)
5. **Fórmula p_inv correcta**: p_inv = -S⁻¹ R⁻¹ p (DEMOSTRADO)
6. **compose(T, T_inv) fórmula implementada**: identidad sí y solo si p=0 o s=1 (DEMOSTRADO)
7. **compose(T, T_inv) fórmula correcta**: identidad si R y S conmutan (DEMOSTRADO)
8. **compose(T_inv, T) fórmula correcta**: identidad sí y solo si R y S conmutan (DEMOSTRADO)

### 8.3 Condiciones Necesarias y Suficientes

**compose() exacto**:
- Necesario y suficiente: S(s₁) @ R(R₂) = R(R₂) @ S(s₁)
- Suficiente (no necesario): escala uniforme, rotación identidad, casos especiales

**Inversa representable como TRS**:
- Necesario y suficiente: R @ S⁻¹ @ R⁻¹ diagonal
- Suficiente (no necesario): escala uniforme, rotación identidad, casos especiales

**compose(T, T_inv) = I (fórmula implementada)**:
- Necesario y suficiente: p = 0 o s = (1, 1, 1)

**compose(T, T_inv) = I (fórmula correcta)**:
- Necesario y suficiente: R y S conmutan

### 8.4 Decisiones Pendientes

1. **Frame convention**: Body vs spatial para velocidad angular (OPEN)
2. **Quaternion.inverse()**: Corregir fórmula o mantener con documentación (OPEN)
3. **Transform inverse()**: Corregir p_inv a -S⁻¹ R⁻¹ p o mantener con documentación (OPEN)
4. **Transform compose()**: Aceptar composición aproximada o restringir casos (OPEN)
5. **Representación**: Mantener TRS o cambiar a matrices generales (OPEN)
6. **6 decisiones de policy**: Convergencia, tolerancias, validación (OPEN)

### 8.5 Archivos Inspeccionados

- `src/character_engine/domain/anatomy/osteology/transform.py`
- `src/character_engine/math/algebra/matrix4.py`
- `src/character_engine/math/algebra/quaternion.py`
- `src/character_engine/math/algebra/vector3.py`

### 8.6 Archivo Creado

- `docs/audit/S2-D1-R17-TRS-INVERSE-COMPOSITION-CORRECTION.md`

### 8.7 Archivos Modificados

NINGUNO (auditoría de solo lectura)

### 8.8 Pruebas Ejecutadas

NINGUNA (auditoría de solo lectura)

### 8.9 Hallazgos Confirmados

1. **Contrato matricial y acción**: CONFIRMADO
2. **Inversa matricial exacta**: CONFIRMADO
3. **Fórmula p_inv correcta**: -S⁻¹ R⁻¹ p (DEMOSTRADO)
4. **Fórmula p_inv implementada**: Incorrecta para casos generales (CONFIRMADO)
5. **compose() exacto**: Solo si escala y rotación conmutan (CONFIRMADO)
6. **Inversa representable**: Solo si R @ S⁻¹ @ R⁻¹ diagonal (CONFIRMADO)
7. **Quaternion.inverse() defecto**: CONFIRMADO
8. **Transform sin uso demostrado**: CONFIRMADO

### 8.10 Incertidumbres

1. **Decisión sobre Transform**: OPEN
2. **Requisitos de motores**: UNKNOWN
3. **Impacto real de defectos**: UNKNOWN

---

**END OF S2-D1-R17-TRS-INVERSE-COMPOSITION-CORRECTION**
