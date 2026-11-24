# A36 — Judo / jujutsu: agarre, desequilibrio, proyección, caída y ukemi

Estado: modelo ESTIMATE / ASSUMED; poses clave **PLACEHOLDER** (bloqueo). Aditivo y opcional (Decisión 87): no cambia
ningún movimiento, tabla, clip ni hash existente. Código: `domain/physics/judo.py`, `domain/animation/judo_clips.py`;
tests: `tests/unit/test_judo.py`; herramienta: `scripts/judo_contact_sheet.py`. Versión completa en inglés:
`A36_JUDO_THROWS.md` (las tablas son las mismas).

## Resumen

* **Kumikata**: un agarre es una mano de tori sobre un punto de uke (manga, solapa, cuello, cinturón, muñeca, nuca,
  cintura, axila), anclado a un hueso del rig de juego. No se modela fuerza de agarre: no se leyó ninguna.
* **Kuzushi**: centro de masa de uke contra los pies apoyados. Un impulso mueve el centro de masa y, como péndulo
  invertido, recorre una distancia antes de poder frenarse sin dar un paso. El margen es lo que queda hasta el borde del
  apoyo; en cero o menos, el equilibrio está roto. De pie: hacia adelante hacen falta 55,5 N·s, hacia atrás 12,7, de lado
  17,1. Un pie segado o barrido sale del apoyo, y por eso o-soto-gari, o-uchi-gari y de-ashi-barai pasan de 17–21 N·s a 0.
* **Caída**: `FallLanding` (A17) desde la altura de suelta de cada técnica (ASSUMED): seoi-nage 795 J, o-goshi y las
  segadas 640 J, de-ashi-barai 464 J.
* **Ukemi**: calidad = habilidad × (1 − fatiga), correcta desde 0,5 (regla ASSUMED). Con ukemi correcta la cabeza no toca.
  Las cargas de cabeza son las medidas (o-soto-gari 4573 → 679 rad/s²), nunca calculadas; donde no se leyó nada, `null`.
* **Poses clave**: siete por técnica (kumikata, kuzushi, tsukuri, kake, caída, aterrizaje, fin) para tori y uke. Las manos
  que agarran y la pierna que siega se colocan sobre el otro luchador con IK.

## Cuadros intermedios y horneado en Blender

Cada cuadro entre dos poses se resuelve, no solo se interpola: rotaciones y raíz con slerp por el arco corto, suavizado
(tiempo ASSUMED), y cada agarre que sigue en ambas poses se vuelve a resolver con IK en ese cuadro, así las manos no se
sueltan mientras los cuerpos se mueven. `python scripts/bake_judo_clips.py` hornea en Blender 3.6 dos armaduras
(`CE_TORI`, `CE_UKE`) con el cuerpo de bloques, una acción por técnica y luchador en cada cuadro, en
`builds/judo/judo_throws.blend`. Blender coincide con Python a 0,02 mm en todos los cuadros. También renderiza las poses
clave en vista lateral y de tres cuartos (`builds/judo/<técnica>_blender.png`). Límites: los pies apoyados no están
bloqueados (patinan unos centímetros entre poses) y el tiempo es simétrico. Cada técnica dura 1,0–1,3 s (ASSUMED). El
punto más rápido son los pies de uke al girar sobre tori en seoi-nage y o-goshi, 17,5 m/s; la patada más rápida medida
es 14,3 m/s (Vagner 2023).

## Referencias y su límite

Se leyeron las descripciones de las cinco técnicas en Wikipedia, cada una con una sola ilustración. Se encontraron, sin
usarlas como fuente de cuadros: un documento de Nage-no-Kata con secuencias de fotos numeradas, los videos de técnica del
Kodokan y un seoi-nage animado en Wikimedia Commons. No se descargó nada.

**Las poses se escribieron a partir de descripciones y se revisaron en la hoja de secuencia; no se calcaron de una
secuencia de fotos.** No se encontró una secuencia libre y completa de cada una de estas cinco técnicas. Ese es hoy el
principal límite de calidad.

## Límites y próximos pasos

Solo bloqueo: sin poses de manos, sin gi, sin torsión del tronco. La mano de tori queda 15–47 cm corta
en el aterrizaje de algunas técnicas. Todavía no se reproduce en Godot, y la tabla de gameplay no tiene
movimientos de judo. Sigue: revisión del dueño de las hojas, una secuencia de fotos o video por técnica para calcar las
poses, bloqueo de pies y reproducción en Godot.
