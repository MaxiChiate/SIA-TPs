# TP5 SIA — Deep Learning (autoencoders y VAE)

Materia: Sistemas de Inteligencia Artificial (ITBA), 2° cuatrimestre 2026, Grupo 9.
Enunciado: `docs/SIATP5.pdf`. Cómo correr todo: `README.md`.

## Teoría de la materia (`docs/teoria/`)

Están todas las slides de la cursada en `docs/teoria/*.pdf`, con su texto extraído en `docs/teoria/txt/*.txt` (con
`pdftotext -layout`) para poder buscar con `grep` sin abrir los PDF. Antes de usar un método, una métrica o un término en
la presentación, buscarlo ahí. Los PDF no se versionan (`.gitignore`, pesan 65 MB): en el repo solo está el texto; si
faltan, se copian de la carpeta de slides de la cursada.

## Regla para la presentación (slides y notas)

- **Lo que está en `docs/teoria/` se asume sabido**: no se explica (ni MSE, ni retropropagación, ni Adam, ni el
  autoencoder o el VAE en sí, si están en las slides de la materia). Se puede nombrar y usar directo.
- **Lo que no está en `docs/teoria/` hay que explicarlo** en la slide o en sus notas: qué mide o qué hace y por qué lo
  usamos. Vale sobre todo para métricas o criterios que no vienen de la clase (por ejemplo, un umbral de píxeles
  incorrectos, un criterio de "imagen nueva", una distancia elegida por el equipo): no pueden aparecer sin
  justificación, como sacados de la galera.
- Lo trivial no hace falta explicarlo aunque no esté en las slides (un promedio, un porcentaje, contar píxeles).
- Si algo no está en `docs/teoria/` y no es trivial, avisar al usuario antes de agregarlo a la presentación.
