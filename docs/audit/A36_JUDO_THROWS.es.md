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

## Referencias y su límite

Se leyeron las descripciones de las cinco técnicas en Wikipedia, cada una con una sola ilustración. Se encontraron, sin
usarlas como fuente de cuadros: un documento de Nage-no-Kata con secuencias de fotos numeradas, los videos de técnica del
Kodokan y un seoi-nage animado en Wikimedia Commons. No se descargó nada.

**Las poses se escribieron a partir de descripciones y se revisaron en la hoja de secuencia; no se calcaron de una
secuencia de fotos.** No se encontró una secuencia libre y completa de cada una de estas cinco técnicas. Ese es hoy el
principal límite de calidad.

## Límites y próximos pasos

Solo bloqueo: sin intermedios, sin poses de manos, sin gi, sin torsión del tronco. La mano de tori queda 15–47 cm corta
en el aterrizaje de algunas técnicas. Todavía no está horneado para Blender ni Godot, y la tabla de gameplay no tiene
movimientos de judo. Sigue: revisión del dueño de las hojas, una secuencia de fotos o video por técnica para calcar las
poses, horneado en Blender con dos luchadores y reproducción en Godot.
