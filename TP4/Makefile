# TP4 SIA: punto de entrada en la raiz. Compatible con GNU Make 3.81.
# Cada plan agrega solo los targets que llaman a cosas que ya existen.

PY ?= .venv/bin/python
UV ?= uv
SERIES ?= analysis/series_smoke_oja.json

.DEFAULT_GOAL := all

.PHONY: all venv prepare eda sweep test clean

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
