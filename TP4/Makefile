# TP4 SIA: punto de entrada en la raiz. Compatible con GNU Make 3.81.
# Cada plan agrega solo los targets que llaman a cosas que ya existen.

PY ?= .venv/bin/python
UV ?= uv

.PHONY: venv prepare eda

# Primer target: un make sin argumentos en TP4/ crea el entorno hasta que
# otro plan defina el objetivo por defecto.
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
