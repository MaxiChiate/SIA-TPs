# TP4 SIA: punto de entrada en la raiz. Compatible con GNU Make 3.81.
# Cada plan agrega solo los targets que llaman a cosas que ya existen.

PY ?= .venv/bin/python
UV ?= uv
SERIES ?= analysis/series_smoke_oja.json

.DEFAULT_GOAL := all

.PHONY: all venv prepare eda pca som-stage1 som-stage2 som-figures som-profiles sweep test clean

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

venv: .venv/.installed

.venv/.installed: analysis/requirements.txt
	test -x .venv/bin/python || $(UV) venv --python 3.12 .venv
	$(UV) pip install --python .venv/bin/python -r analysis/requirements.txt
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
