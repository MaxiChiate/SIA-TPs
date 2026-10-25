# Phase 6: Slides e informe - Context

**Gathered:** 2026-10-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Publicar las **slides** (Artifact, una sección por ejercicio, para presentar) y el **informe** (Artifact, para entender el proyecto, con una tabla que mapea cada pregunta literal del enunciado a la sección donde se responde), y dejar `CLAUDE.md`, `DECISIONS.md` y README con cómo reproducir cada resultado (comando, config y seed). Los pasos de reproducción tienen que regenerar las figuras y tablas que muestran slides e informe (DELIV-01, DELIV-02, DELIV-03).

No se agregan análisis nuevos: todo el contenido sale de lo que ya producen las Fases 1-5 (`deliverables/01..05-*.md` y `analysis/results/`).

</domain>

<decisions>
## Implementation Decisions

### Slides: duración, guion y narrativa
- **D-01:** Presentación de **~20 minutos, ~20-25 slides**. Reparto aproximado: Ej. 1 (EDA/PCA, Kohonen, Oja, campañas) ~12-14 slides; Ej. 2 (letras, QR) ~7-9 slides. Una idea por slide.
- **D-02:** Orden **por método** (PCA → SOM → Oja → campañas → letras → QR), con **título-conclusión** en cada slide (el título dice la conclusión, no el tema: «El mapa sigue a PC1 pero no a PC2», no «Matriz U»). La pregunta del enunciado que responde la slide puede ir en chico, pero no ordena el guion.
- **D-03:** El rigor metodológico entra como **una slide de método** al principio (reglas fijadas y commiteadas antes de ver resultados con guardia sha256, 10 seeds, nulos por permutación) y después **menciones cortas** en cada resultado (p. ej. «regla fijada de antemano»). El detalle de cada regla queda en el informe.
- **D-04:** Los resultados poco favorables van **de frente, con slide propia y título-conclusión**, más una línea del porqué: una sola región en el SOM (R1 = 50) con la regla fijada, etapa 2 «no robusta», Hebb 0 % de recuperación exacta en los QR (solapamiento medio 0,67), y el lookup de Hamming 1-NN que iguala o supera a la pseudo-inversa con ruido alto. Coherente con la Key Decision de PROJECT.md «reportar el resultado de la regla tal cual».
- **D-05:** Campañas en ~4 slides: **fútbol aparte** (alcance masivo / descubrimiento / profundidad educativa y la recomendación), **una tabla resumen** para perros, maquillaje y arte (criterio, top-5, costo por mil argentinos), **una slide de comparación contra solo `followers`** y **una de mantenimiento**.
- **D-06:** Cada slide lleva **notas del orador**: 2-4 frases de qué decir y los números clave para responder preguntas. El cuerpo visible queda limpio. Si el formato Slides no soporta notas, el planner propone el equivalente más cercano y lo informa.
- **D-07:** Apertura con **portada** (TP4 SIA, Grupo 9) y la **slide de método** (D-03). Cada ejercicio **cierra con su propia slide de conclusiones**: Ej. 1 dice qué aporta cada método a la decisión de campaña y Ej. 2 dice qué limitaciones tiene Hopfield para los QR. **No hay agenda ni cierre general.**

### Figuras en slides e informe
- **D-08:** Las figuras de las slides son una **variante «slide» del mismo código matplotlib** que ya dibuja las del informe: la misma función de datos con otro estilo (letra más grande, menos anotaciones, proporción para 16:9). Los datos se calculan una vez y se dibujan dos (patrón de `.planning/research/ARCHITECTURE.md`). No se pintan gráficos a mano en HTML como en TP3. — **Reversibility:** costly — si después se cambia el renderer de las slides, hay que rehacer cada figura de slide.
- **D-09:** El informe es **todo estático**: se usan los SVG de matplotlib existentes, inline. No lleva plotly, JS de gráficos ni CDN para las figuras.
- **D-10:** Tema: cada figura va **siempre sobre un panel claro** (tarjeta con el fondo `SURFACE` de `analysis/plots_style.py` y borde), también en modo oscuro. La página alrededor sí cambia de tema. Hay una sola versión de cada figura y no se generan variantes oscuras: los QR, las letras y la matriz U se leen igual en los dos temas.
- **D-11:** El armado es **por script + `make`**. Un target (p. ej. `make deliverables`, o `make slides` + `make informe`) regenera los resultados que faltan, dibuja las figuras de informe y de slide, y escribe el HTML del informe y los archivos de datos de las slides, listos para publicar. **Los números del texto se leen de los JSON/CSV de `analysis/results/` y no se tipean a mano.** La publicación de los Artifacts es manual (un paso aparte que se documenta). — **Reversibility:** costly — el texto de slides e informe pasa a depender de las claves de los JSON de cada fase; armarlo a mano después pierde la garantía del criterio 3.

### Informe y entrega (decidido en plan-phase, 2026-10-25)
- **D-12:** El informe es **híbrido**: una parte inicial generada (resumen «Qué encontramos», tabla pregunta→sección de DELIV-02, bloque «Cómo trabajamos») con los números leídos de los JSON vía un loader de facts, seguida de los cinco fragmentos `deliverables/0X-*.md` convertidos a HTML como «Detalle técnico (Fase N)». Un test de drift fija ~25 números clave de los fragmentos contra los JSON. Los fragmentos no se editan (están bajo guardia sha256); todo cambio de texto se hace al renderizar. — **Reversibility:** costly — pasar a síntesis pura después obliga a reescribir y revisar a mano todo el texto.
- **D-13:** La jerga interna de los fragmentos (`D-NN`, `Pitfall N`, IDs de requisito como `HOP-04`) se **enlaza al renderizar** a un anexo de glosario generado desde `DECISIONS.md`. Los fragmentos quedan intactos.
- **D-14:** Las slides se entregan **solo como Artifact**. No se exporta ni versiona un PDF de slides en `docs/`.
- **D-15:** El informe llega al docente como **link compartido del Artifact** (HTML). No hace falta exportar PDF/Word del informe; el tipo Docs no se usa. Compartir el link es un paso manual del checkpoint de publicación.

### Claude's Discretion
El usuario eligió no discutir el formato del informe ni los documentos de reproducción. Quedan a criterio del researcher/planner, con estos defaults:
- **Formato del informe:** página HTML autocontenida publicada como Artifact, generada por script desde los resultados (PROJECT.md Key Decision y `.planning/research/STACK.md` §Deliverables). Existe también el tipo de Artifact «Docs» (editable, exporta a PDF/.docx); usarlo solo si el planner encuentra una razón fuerte y la informa. Hay que elegir si el informe reutiliza los fragmentos `deliverables/0X-*.md` (convertidos a HTML) o es una síntesis escrita aparte. Lo que importa es que el texto no diverja de los fragmentos ni de los números.
- **Tabla pregunta→respuesta (DELIV-02):** cada pregunta **literal** del enunciado (`docs/Archivo SIATP 42026.pdf`), con un link a la sección del informe donde se responde y, si conviene, la slide. La forma de la tabla queda libre.
- **Slides:** usar el tipo de Artifact **Slides** (16:9, se exporta a .pptx/PDF), siguiendo las instrucciones que da el tipo al crearlo y su design system por defecto (no se elige paleta a mano). Las figuras de matplotlib se insertan como SVG/imagen dentro de ese formato. Verificar en la investigación cómo el tipo recibe los datos y si soporta notas del orador (blocker abierto en STATE.md).
- **Documentos de reproducción (DELIV-03):** contenido de `CLAUDE.md` (punto de partida para una sesión nueva, como el de TP3 en el commit `7ff59c3`), `DECISIONS.md` (consolida las decisiones D-xx de las 5 fases y las Key Decisions, con link a cada CONTEXT.md/fragmento) y `README.md` (comando, config y seed de cada figura y tabla; cómo armar slides e informe). Nota: en TP3 un compañero borró `CLAUDE.md` y `DECISIONS.md` el día de la entrega (commits `31958a4`, `bcce0da`). En TP4 son requisito (DELIV-03) y se versionan igual.
- Nombres de scripts (p. ej. `analysis/slides.py`, `analysis/informe.py`), de targets del Makefile y de la carpeta de salida (no versionada, como el resto de `analysis/results/`).
- Qué figuras exactas van a cada slide, dentro del presupuesto de D-01 y D-05.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Enunciado y alcance
- `docs/Archivo SIATP 42026.pdf` — enunciado del TP4. Las preguntas literales salen de acá y van a la tabla pregunta→respuesta (DELIV-02).
- `.planning/REQUIREMENTS.md` §Entregables — DELIV-01, DELIV-02, DELIV-03.
- `.planning/ROADMAP.md` §Phase 6 — goal y los 3 criterios de éxito.
- `.planning/PROJECT.md` — Key Decisions (informe en Artifact y slides aparte; reportar resultados tal cual; reglas pre-registradas).

### Contenido fuente (lo que se presenta)
- `deliverables/01-datos-pca.md` — EDA, auditoría de variables, PCA, sensibilidad 31 columnas, cómo reproducir.
- `deliverables/02-kohonen.md` — regla de grilla, etapas 1-2, mapa, regiones, PC1/PC2, matriz U, cómo reproducir.
- `deliverables/03-oja-campanas.md` — Oja vs PC1, «¿elegir el máximo?», regla de campañas, listas, followers, mantenimiento, cómo reproducir.
- `deliverables/04-hopfield-letras.md` — alfabeto, sets, ortogonalidad, ruido, capacidad, espurio, cómo reproducir.
- `deliverables/05-hopfield-qr.md` — QR, protocolo, Hebb, pinv vs Hamming, limitaciones, cómo reproducir.
- `.planning/phases/0{1..5}-*/0X-CONTEXT.md` — decisiones D-xx de cada fase (fuente de `DECISIONS.md`).

### Render y estilo
- `.planning/research/STACK.md` §Deliverables: report and slides — matplotlib SVG para todo lo estático; Slides de Artifact; plotly fuera del informe.
- `.planning/research/ARCHITECTURE.md` — datos de figura separados de los renderers (una función de datos y dos renderers).
- `analysis/plots_style.py` — paleta y estilo compartidos; texto como trazos en SVG; `SURFACE` para el panel claro de D-10.
- `../TP3/analysis/plots_presentation.py` — antecedente de cómo TP3 llenó el formato Slides (solo como referencia, no se copia el pintado a mano: D-08).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `analysis/plots_style.py`: paleta de 8 slots (la misma de TP3), `SURFACE`/`TEXT_*` y el estilo SVG con texto en trazos. La variante «slide» de D-08 se agrega acá (p. ej. un contexto o un parámetro de escala).
- Scripts de figuras por fase: `analysis/eda.py`, `analysis/pca.py`, `analysis/som_figures.py`, `analysis/som_profiles.py`, `analysis/oja.py`, `analysis/campaigns.py`, `analysis/maintenance_demo.py`, `analysis/hopfield_figures.py`, `analysis/hopfield_qr_figures.py`. Todos escriben SVG de matplotlib en `analysis/results/**/figures/`.
- Cada fase deja JSON con los números del texto (p. ej. `verdict.json`, `overlaps.json`, `qr_facts.json`, `selection_identity.json`, `metrics.json`): son la fuente de los números de D-11.
- Cada fragmento `deliverables/0X-*.md` tiene una sección «Cómo reproducir»: es la base del README.

### Established Patterns
- Targets de `make` por paso (`prepare`, `eda`, `pca`, `som-*`, `oja`, `campaigns`, `maintenance`, `letters`, `hopfield-letters`, `hopfield-figures`, `qr`, `hopfield-qr`, `hopfield-qr-limits`, `hopfield-qr-figures`). El target nuevo de D-11 los encadena.
- Resultados generados no versionados (`analysis/results/`), seeds fijas, `PY ?= .venv/bin/python`.
- Texto en español rioplatense con coma decimal y sin «mejor» para el índice de Oja (F3 D-06).

### Integration Points
- Localmente solo están generados los resultados del SOM (`analysis/results/som`, `series_som_stage*`). Antes de armar hay que correr toda la cadena; el target de D-11 tiene que hacerlo o exigirlo.
- La Fase 3 figura «complete, ready to verify» en STATE.md, pero sin verificar. Conviene verificarla antes de congelar los números de campañas en slides e informe.

</code_context>

<specifics>
## Specific Ideas

- Los títulos-conclusión y los hallazgos «de frente» buscan que la presentación cuente lo que realmente salió, incluido lo poco favorable, con la misma honestidad que las reglas pre-registradas de F2-F5.
- La slide de método es donde se cuenta el rigor una sola vez. Las demás slides solo lo señalan.
- Las notas del orador tienen los números clave a mano para responder preguntas del docente sin abrir el informe.

</specifics>

<deferred>
## Deferred Ideas

None. La discusión no salió del alcance de la fase.

</deferred>

---

*Phase: 06-slides-e-informe*
*Context gathered: 2026-10-25*
