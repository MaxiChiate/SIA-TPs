# TP4 SIA: punto de entrada en la raiz. Compatible con GNU Make 3.81.
# Cada plan agrega solo los targets que llaman a cosas que ya existen.

PY ?= .venv/bin/python
UV ?= uv
SERIES ?= analysis/series_smoke_oja.json

.DEFAULT_GOAL := all

.PHONY: all venv prepare eda pca som-stage1 som-stage2 som-figures som-profiles oja campaigns maintenance sweep test clean letters hopfield-letters hopfield-figures qr hopfield-qr hopfield-qr-limits hopfield-qr-figures results

# Un make sin argumentos en TP4/ deja un clone nuevo listo con un solo comando: crea .venv,
# regenera datos/prepared/ (lo leen los ejemplos de kohonen y oja) y compila el binario unico.
all: prepare
	$(MAKE) -C neuron

# Una serie de corridas (cualquier modelo): make sweep SERIES=analysis/series_smoke_kohonen.json
sweep: prepare
	$(PY) analysis/sweep.py $(SERIES)

# Tests de C y de Python. Depende de prepare: un clone nuevo no tiene datos/prepared/ y pytest lo lee.
test: prepare
	$(MAKE) -C neuron test PY=$(abspath $(PY))

# Borra la compilacion; datos/prepared/ y .venv quedan.
clean:
	$(MAKE) -C neuron clean

# Crea .venv e instala analysis/requirements.txt. Con uv usa uv; sin uv cae a python3.12 -m venv mas pip.
venv: .venv/.installed

.venv/.installed: analysis/requirements.txt
	if command -v $(UV) >/dev/null 2>&1; then \
		test -x .venv/bin/python || $(UV) venv --python 3.12 .venv; \
		$(UV) pip install --python .venv/bin/python -r analysis/requirements.txt; \
	else \
		test -x .venv/bin/python || python3.12 -m venv .venv; \
		.venv/bin/python -m pip install -r analysis/requirements.txt; \
	fi
	touch $@

# datos/prepared/ se genera (no se versiona): todo target que lo lea depende de prepare.
prepare: venv
	$(PY) scripts/prepare_creadores.py

# EDA y tabla de auditoria en analysis/results/eda/ (no se versiona).
eda: venv
	$(PY) analysis/eda.py

# PCA por autovalores de la matriz de correlacion: auditado y sensibilidad de 31 columnas,
# en analysis/results/pca/ (no se versiona). Lee datos/prepared/, por eso depende de prepare.
pca: prepare
	$(PY) analysis/pca.py

# Etapa 1 del SOM (140 corridas, leave-one-out y estabilidad) con la regla de eleccion ya commiteada:
# se niega a correr si deliverables/02-kohonen.md, analysis/som_select.py o la serie estan sin commitear.
som-stage1: prepare
	$(PY) analysis/som_stage.py run analysis/series_som_stage1.json --select

# Etapa 2 (robustez del schedule sobre la k elegida): ademas se niega a correr si la regla cambio desde la etapa 1.
som-stage2: prepare
	$(PY) analysis/som_stage.py run analysis/series_som_stage2.json

# Figuras de la grilla elegida (mapa de hits + matriz U, planos de componentes, curvas de la etapa 1, traza): necesita
# selection.json de make som-stage1 y se niega a correr si la regla cambio o no hay grilla elegida.
som-figures: prepare
	$(PY) analysis/som_figures.py

# Regiones, perfiles en unidades originales y contraste con PC1/PC2 de la grilla elegida: necesita selection.json de
# make som-stage1 y se niega a correr si la regla cambio o no hay grilla elegida.
som-profiles: prepare
	$(PY) analysis/som_profiles.py

# Oja en C con 10 seeds (analysis/series_oja.json), comparacion con PC1, dispersion, convergencia y evidencia del
# maximo; escribe analysis/results/oja/ (no se versiona). Lee analysis/results/pca/, por eso depende de pca.
oja: pca
	$(PY) analysis/oja.py

# Listas por campaña con la regla commiteada (sección 4 de deliverables/03-oja-campanas.md), dos líneas base por
# followers y las métricas de D-17; escribe analysis/results/campaigns/ (no se versiona). Se niega a correr si la
# regla o analysis/campaigns_select.py cambiaron desde el commit de la regla. Necesita el índice de Oja (make oja) y
# selection.json del SOM (make som-stage1).
campaigns: oja som-stage1
	$(PY) analysis/campaigns.py

# Demo de mantenimiento con un creador sintético (SYN001, @sintetico_demo): lo mapea con scripts/map_creator.py y el
# scaler guardado, lo ubica en el mapa SOM y en el índice de Oja y corre el chequeo de deriva; escribe
# analysis/results/maintenance/ (no se versiona). Necesita make oja y make som-stage1.
maintenance: oja som-stage1
	$(PY) analysis/maintenance_demo.py

# Las 26 letras 5x5 de datos/letters/alphabet_5x5.txt, dibujadas y aprobadas en el checkpoint de la regla, a una
# matriz ±1 en datos/prepared/ (alphabet_pm1.csv y su meta); no corre la red.
letters: venv
	$(PY) scripts/prepare_letters.py

# Corre los experimentos de Hopfield fijados en la sección 3 de deliverables/04-hopfield-letras.md; se niega a correr
# si la regla, el alfabeto o el código de selección no están commiteados o cambiaron (D-04).
hopfield-letters: letters
	$(PY) analysis/hopfield_letters.py

# Figuras de Hopfield sobre las letras (glifos, solapamientos, término de cruce, recuperación y energía); necesitan los
# resultados de make hopfield-letters y se niegan a dibujar si la regla cambió.
hopfield-figures: venv
	$(PY) analysis/hopfield_figures.py

# Los 5 QR 37x37 de datos/hopfield/*.png a una matriz ±1 en datos/prepared/ (qr_pm1.csv y su meta,
# con sha256 por PNG); no corre la red. Preparación de deliverables/05-hopfield-qr.md (HOP-04).
qr: venv
	$(PY) scripts/prepare_qr.py

# Corre la regla de Hebb sobre los 5 QR fijada en la sección 3 de deliverables/05-hopfield-qr.md; se niega a
# correr si el protocolo, scripts/qr.py o los 5 PNG no están commiteados o cambiaron (D-01).
hopfield-qr: qr
	$(PY) analysis/hopfield_qr.py

# Evidencia de limitaciones (HOP-07, D-11): atractor mayoria de Hebb y sensibilidad a corrimientos de 1-2
# pixeles bajo pinv. Se niega a correr si el protocolo no esta commiteado o cambio (D-01); escribe en su
# propio directorio qr_limits/, que make hopfield-qr nunca borra.
hopfield-qr-limits: qr
	$(PY) analysis/hopfield_qr_limits.py

# Figuras de Hopfield sobre los 5 QR (glifos, solapamientos, curva de recuperación de Hebb y energía por paso);
# necesitan los resultados de make hopfield-qr (y, las de limitaciones, de make hopfield-qr-limits) y se
# niegan a dibujar si el protocolo o el código cambiaron.
hopfield-qr-figures: venv
	$(PY) analysis/hopfield_qr_figures.py

# ---------------------------------------------------------------------------------------------------------------------
# make results: regenera solo los resultados de las fases 1-5 que faltan (D-11). Cada paso tiene un archivo centinela;
# si existe, el paso no se vuelve a correr. Cada regla llama directo al script del paso (el mismo comando que el target
# phony de arriba) y sus prerequisitos son order-only (despues de |): fijan el orden pero no fuerzan una corrida por
# fecha. Asi no se arrastra som-stage1 ni som-stage2 (140 corridas) cuando ya estan hechos.
# ---------------------------------------------------------------------------------------------------------------------
RES := analysis/results
PREP := datos/prepared

RESULTS_SENTINELS := \
	$(PREP)/creadores_zscore.csv \
	$(RES)/eda/audit_table.md \
	$(RES)/pca/audited/decision.json \
	$(RES)/som/series_som_stage1/selection.json \
	$(RES)/som/series_som_stage2/robustness.json \
	$(RES)/som/figures/map.svg \
	$(RES)/som/profiles/pca_contrast.json \
	$(RES)/oja/index.csv \
	$(RES)/campaigns/selection_identity.json \
	$(RES)/maintenance/report_demo.md \
	$(PREP)/alphabet_pm1.csv \
	$(RES)/hopfield/letters/selection.json \
	$(RES)/hopfield/figures/spurious.svg \
	$(PREP)/qr_pm1.csv \
	$(RES)/hopfield/qr/verdict.json \
	$(RES)/hopfield/qr_limits/majority.json \
	$(RES)/hopfield/qr/figures/majority.svg

# Regenera lo que falta de las fases 1-5, en orden de dependencia. Para forzar un paso: rm -rf analysis/results/<paso>
# y volver a correr make results. Un centinela viejo no detecta que el codigo cambio. Las guardas de cada driver
# (regla pre-registrada, identidad del codigo) siguen negandose a correr si la regla cambio: make results no las evita.
results: $(RESULTS_SENTINELS)

# Datos del EDA y la PCA: matriz z-score del conjunto auditado (datos/prepared/ no se versiona).
$(PREP)/creadores_zscore.csv: | .venv/.installed
	$(PY) scripts/prepare_creadores.py

# EDA y tabla de auditoria.
$(RES)/eda/audit_table.md: | .venv/.installed
	$(PY) analysis/eda.py

# PCA auditada y sensibilidad de 31 columnas; lee datos/prepared/.
$(RES)/pca/audited/decision.json: | $(PREP)/creadores_zscore.csv
	$(PY) analysis/pca.py

# Etapa 1 del SOM (140 corridas) con la regla commiteada; si falta el centinela y la regla cambio, el driver se niega.
$(RES)/som/series_som_stage1/selection.json: | $(PREP)/creadores_zscore.csv
	$(PY) analysis/som_stage.py run analysis/series_som_stage1.json --select

# Etapa 2 del SOM (robustez del schedule sobre la k elegida).
$(RES)/som/series_som_stage2/robustness.json: | $(RES)/som/series_som_stage1/selection.json
	$(PY) analysis/som_stage.py run analysis/series_som_stage2.json

# Figuras de la grilla elegida del SOM.
$(RES)/som/figures/map.svg: | $(RES)/som/series_som_stage1/selection.json $(RES)/pca/audited/decision.json
	$(PY) analysis/som_figures.py

# Regiones, perfiles y contraste con PC1/PC2 de la grilla elegida.
$(RES)/som/profiles/pca_contrast.json: | $(RES)/som/series_som_stage1/selection.json $(RES)/pca/audited/decision.json
	$(PY) analysis/som_profiles.py

# Oja en C con 10 seeds, comparacion con PC1 e indice; necesita la PCA.
$(RES)/oja/index.csv: | $(RES)/pca/audited/decision.json
	$(PY) analysis/oja.py

# Listas por campaña con la regla commiteada; necesita el indice de Oja y selection.json del SOM.
$(RES)/campaigns/selection_identity.json: | $(RES)/oja/index.csv $(RES)/som/series_som_stage1/selection.json
	$(PY) analysis/campaigns.py

# Demo de mantenimiento con el creador sintetico; necesita el indice de Oja y selection.json del SOM.
$(RES)/maintenance/report_demo.md: | $(RES)/oja/index.csv $(RES)/som/series_som_stage1/selection.json
	$(PY) analysis/maintenance_demo.py

# Las 26 letras 5x5 a una matriz +-1 en datos/prepared/.
$(PREP)/alphabet_pm1.csv: | .venv/.installed
	$(PY) scripts/prepare_letters.py

# Experimentos de Hopfield sobre las letras (regla de la seccion 3 de deliverables/04-hopfield-letras.md).
$(RES)/hopfield/letters/selection.json: | $(PREP)/alphabet_pm1.csv
	$(PY) analysis/hopfield_letters.py

# Figuras de Hopfield sobre las letras; leen los resultados de hopfield-letters.
$(RES)/hopfield/figures/spurious.svg: | $(RES)/hopfield/letters/selection.json
	$(PY) analysis/hopfield_figures.py

# Los 5 QR 37x37 a una matriz +-1 en datos/prepared/.
$(PREP)/qr_pm1.csv: | .venv/.installed
	$(PY) scripts/prepare_qr.py

# Regla de Hebb sobre los 5 QR (seccion 3 de deliverables/05-hopfield-qr.md).
$(RES)/hopfield/qr/verdict.json: | $(PREP)/qr_pm1.csv
	$(PY) analysis/hopfield_qr.py

# Evidencia de limitaciones de los QR (atractor mayoria y corrimientos de 1-2 pixeles).
$(RES)/hopfield/qr_limits/majority.json: | $(PREP)/qr_pm1.csv
	$(PY) analysis/hopfield_qr_limits.py

# Figuras de Hopfield sobre los 5 QR; leen hopfield-qr y hopfield-qr-limits.
$(RES)/hopfield/qr/figures/majority.svg: | $(RES)/hopfield/qr/verdict.json $(RES)/hopfield/qr_limits/majority.json
	$(PY) analysis/hopfield_qr_figures.py
