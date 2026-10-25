# Phase 6: Slides e informe - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-10-25
**Phase:** 6-Slides e informe
**Areas discussed:** Slides: duración y guion, Figuras en slides/informe

---

## Slides: duración y guion

**Duración y cantidad de slides**

| Option | Description | Selected |
|--------|-------------|----------|
| ~20 min, ~20-25 slides | Ej. 1 ~12-14, Ej. 2 ~7-9; una idea por slide | ✓ |
| ~10-15 min, ~12-15 slides | Solo resultados principales; rigor al informe | |
| ~30 min, 30+ slides | Cada figura y decisión con su slide, estilo TP3 | |
| No sé el tiempo, decidí vos | Base de ~20 min recortable | |

**Rigor metodológico en slides**

| Option | Description | Selected |
|--------|-------------|----------|
| Una slide de método + menciones | Una slide de cómo trabajamos; marcas cortas después | ✓ |
| Integrado en cada ejercicio | Cada sección muestra su regla antes del resultado | |
| Fuera de las slides | Solo resultados; rigor al informe | |

**Orden y títulos**

| Option | Description | Selected |
|--------|-------------|----------|
| Pregunta del enunciado → respuesta | Orden del enunciado, título-conclusión | |
| Por método, título-conclusión | Orden de las fases, título-conclusión, pregunta en chico | ✓ |
| Por método, título descriptivo | Títulos tipo «Matriz U» | |

**Resultados poco favorables**

| Option | Description | Selected |
|--------|-------------|----------|
| Como hallazgos de frente | Slide propia con título-conclusión y el porqué | ✓ |
| Mencionados, sin slide propia | Nota dentro de la slide del método | |
| Solo los centrales | Hebb vs pinv y máximo de Oja de frente; el resto al informe | |

**Campañas en slides**

| Option | Description | Selected |
|--------|-------------|----------|
| Fútbol aparte + 1 tabla resumen | Fútbol, tabla de 3 campañas, followers, mantenimiento (~4) | ✓ |
| Una slide por campaña | ~6 slides | |
| Todo en 2 slides | Tabla de 4 campañas + followers/mantenimiento | |

**Guion**

| Option | Description | Selected |
|--------|-------------|----------|
| Sí, notas del orador por slide | 2-4 frases y números clave | ✓ |
| No, la slide se explica sola | Más texto visible | |
| Guion aparte en el informe | Sección de guion en el informe | |

**Apertura y cierre**

| Option | Description | Selected |
|--------|-------------|----------|
| Portada + método; cierre por ejercicio | Sin agenda ni cierre general | ✓ |
| Portada + agenda; cierre general | Agenda y conclusiones finales | |
| Ambos cierres | Por ejercicio y general | |

**User's choice:** las opciones marcadas.
**Notes:** El usuario pidió más preguntas después de la primera tanda.

---

## Figuras en slides/informe

**Fuente de las figuras de slides**

| Option | Description | Selected |
|--------|-------------|----------|
| Variante «slide» del mismo código | Mismas funciones matplotlib, estilo de slide | ✓ |
| Reusar los SVG tal cual | Texto chico, demasiada anotación | |
| HTML hecho a mano como TP3 | Prolijo pero reescribe cada gráfico | |

**Interactividad del informe**

| Option | Description | Selected |
|--------|-------------|----------|
| Todo estático, SVG inline | Sin JS ni CDN | ✓ |
| Estático + 1-2 interactivas | Biplot/SOM con hover vía plotly | |
| Interactivo donde ayude | Otra ruta de render que mantener | |

**Tema claro/oscuro**

| Option | Description | Selected |
|--------|-------------|----------|
| Figura sobre panel claro siempre | Una versión por figura | ✓ |
| Generar variante oscura | Duplica archivos; invierte QR/matriz U | |
| Forzar todo en claro | Sin modo oscuro | |

**Armado**

| Option | Description | Selected |
|--------|-------------|----------|
| Script + `make` que arma todo | Números leídos de JSON; publicación manual | ✓ |
| Script para figuras, texto a mano | Riesgo de números desactualizados | |
| Armado a mano, una vez | Documentar comando por figura | |

**User's choice:** las opciones marcadas.

---

## Claude's Discretion

- Formato y armado del informe (HTML Artifact por defecto; Docs solo con razón fuerte), forma de la tabla pregunta→respuesta.
- Contenido de `CLAUDE.md`, `DECISIONS.md` y README.
- Uso del tipo Slides y su design system por defecto; nombres de scripts, targets y carpetas; qué figura va en cada slide.

## Deferred Ideas

None.
