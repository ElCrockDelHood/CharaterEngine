# A34 — Corte con sable: masa efectiva, inercia rotacional y punto de impacto

Spec y nota de investigación, 2026-11-05, Decisión 82. Versión en inglés, con las tablas completas: `A34_BLADE_DYNAMICS.md`.
Las tablas se regeneran con `python scripts/blade_dynamics_table.py`.

**Estado.** Especificado, implementado y con tests unitarios, como opción. No adoptado: el `Blade(0.6, 10.0, 0.028)` actual no
cambia, así que no se mueve ninguna tabla de A09 ni A10. Nada de esto está validado contra un corte físico.

## 1. Spec

**Objetivo.** Reemplazar "0,6 kg a 10 m/s" (masa PLACEHOLDER, velocidad ESTIMATE) por un cálculo desde la masa del arma, su
inercia rotacional, el movimiento y el punto de la hoja que golpea.

**Archivos.** Cambia: `domain/physics/cut.py` (solo agregados; `cut_through` y `Blade` quedan igual). Nuevos:
`tests/unit/test_blade_dynamics.py`, `scripts/blade_dynamics_table.py` y esta nota. También una entrada en `INDEX.md`,
`DECISION_LOG.md` y `NOTICE`. No se tocan: `collision.py` (se importa, solo lectura), `strike_model.py`, `head_kinematics.py`,
`body_strike.py`.

**Aceptación.** Reproduce las fórmulas cerradas de una varilla uniforme; recupera los límites libre y con pivote fijo; la
sacudida en la empuñadura es cero en el centro de percusión; una hoja libre nunca le da al contacto más energía de la que tiene
el movimiento; el resultado alimenta el corte existente sin cambios; ni los valores por defecto ni los tests existentes se mueven.

## 2. Física (DERIVED, impulso de cuerpo rígido de libro)

- **Masa efectiva en el punto de impacto:** `1 / m_eff = 1 / M + r² / I_cg`, con `r = x − x_cg`. Vale `M` en el centro de gravedad
  y baja hacia la punta, porque la hoja gira alejándose del blanco en vez de empujarlo.
- **Velocidad:** `v(x) = v_empuñadura + ω x`.
- **Energía que el contacto puede sacarle al movimiento:** `½ m_eff v²`. Después las capas gastan `½ μ v²` contra el blanco (A14).
- **Centro de percusión:** `x_cop = I_empuñadura / (M x_cg)`. Un impacto ahí no da sacudida en la mano.
- **La mano:** una masa `m_c` rígida en la empuñadura cambia `M`, `x_cg` e `I_cg`. Con `m_c = 0` la hoja está libre y con
  `m_c → ∞` la empuñadura es un pivote fijo, `m_eff = I_empuñadura / x²`. No hace falta inventar una mezcla: es un parámetro entre
  dos límites exactos, y en `x_cop` no cambia nada.

## 3. Datos

- **Masa 0,9375 kg, balance 16,75 cm, hoja 0,82 m (ESTIMATE):** medianas de seis sables tipo 1796 medidos por Matt Easton, con
  rangos 830–975 g, 14,5–19 cm y 78–83 cm. El método no está indicado. La fuente dice "desde la empuñadura"; leerlo como desde la
  guarda es ASSUMED. Uno de los seis es una versión de 1850–60 y otro no es reglamentario.
- **Inercia y centro de percusión (ESTIMATE):** **no se encontró ninguna medición de un sable.** Se calculan con un afinamiento de
  la hoja supuesto (ASSUMED, 0,45, probado de 0,25 a 0,7).
- **Mano a guarda 0,07 m y centro de gravedad de la empuñadura 0,03 m:** ASSUMED, sin fuente.
- **Velocidad de la punta (ESTIMATE, probada a 10, 13 y 17,55 m/s):** Greene, Barona y Simon 2023 filmaron un corte vertical a
  240 FPS con 3 + 3 esgrimistas. **Sin verificar:** los rangos 17,55–19,53 m/s (élite) y 12,97–14,93 m/s (novatos) vienen de un
  resumen de búsqueda y no aparecen en el texto extraído del PDF. Es investigación de secundario, n = 6 y arma deportiva, no
  un sable de 0,94 kg.
- **Velocidad de la empuñadura / velocidad de la punta:** 0 y 0,3, ASSUMED, sin fuente.

## 4. Qué muestra (todo ESTIMATE; tablas en la versión en inglés)

1. **Los 30 J del placeholder quedan cerca del tope del rango.** El modelo da entre unos 6 y 33 J. Solo los alcanza la velocidad
   más alta probada, con la empuñadura también en movimiento, y esa velocidad está sin verificar y viene de un arma más liviana.
2. **El movimiento importa más que el punto de impacto.** A 13 m/s la energía en el centro de percusión pasa de 12,4 a 18,2 J con
   la empuñadura en movimiento, y de 10 a 17,55 m/s casi se triplica. Del centro de percusión a la punta cambia un 13 % en rotación
   pura.
3. **En rotación pura, dónde pega casi no cambia la energía; cambia cómo llega.** Con pivote fijo la energía es exactamente
   `½ I ω²` en toda la hoja. Hacia la punta esa energía llega con menos masa y más velocidad (0,43 kg a 8,8 m/s contra 0,13 kg a
   15 m/s). Este modelo de corte solo cuenta energía, así que no puede mostrar esa diferencia, y para un corte puede importar
   tanto como la energía.
4. **El centro de percusión es un punto real de esta arma, pero lo que fija es la sacudida.** Está a unos 0,52 m de la mano y el
   afinamiento lo mueve 4,7 cm en total. Con la empuñadura en movimiento el pico de energía se corre hacia la empuñadura.
5. **El acoplamiento del brazo es una corrección chica pasado el centro de percusión** (de 14,4 a 16,5 J en la punta). Antes de ese
   punto, y con la empuñadura en movimiento, es mayor, porque entra la energía propia del brazo.

## 5. Sin modelar

Cortes deslizantes o de tirón, ángulo y filo, vibración y flexión de la hoja, curvatura, giro de la hoja o cesión de la mano durante
el contacto, largo de la herida a lo largo de la hoja e inercia propia de la empuñadura (cerca del 3 % de `I_cg`, estimado). No hay
validación contra un ensayo de corte ni un sable medido.

## 6. Pendiente

- **Mariano decide** si una tabla adopta esto, cuándo y con qué movimiento. Mueve A09 y A10, y necesita su propia decisión.
- **Lo que más reduciría la incertidumbre:** con un sable o una réplica real, un ensayo de péndulo para `I_empuñadura`, que solo
  pide un cronómetro, y un video del corte para las velocidades de punta y empuñadura. El período medido reemplaza directamente el
  afinamiento supuesto.
- Leer directamente del artículo las velocidades de Greene et al.

Fuentes: lista completa en la versión en inglés.
