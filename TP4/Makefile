# TP4 SIA: punto de entrada en la raiz. Compatible con GNU Make 3.81.
# Cada plan agrega solo los targets que llaman a cosas que ya existen.

PY ?= .venv/bin/python
UV ?= uv

.PHONY: venv

# Primer target: un make sin argumentos en TP4/ crea el entorno hasta que
# otro plan defina el objetivo por defecto.
venv: .venv/.installed

.venv/.installed: analysis/requirements.txt
	test -x .venv/bin/python || $(UV) venv --python 3.12 .venv
	$(UV) pip install --python .venv/bin/python -r analysis/requirements.txt
	touch $@
