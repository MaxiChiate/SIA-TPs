# Roadmap – Motor de Sokoban (TP1, Ejercicio 2)

> Documento pensado para pegarle a Claude Code y que arranque solo con la Fase 0.
> El resto de las fases (búsqueda, heurísticas) las implementa el equipo — no Claude Code.

## Objetivo de esta etapa (Fase 0)

Armar el "tablero de juego" completo, pero **sin ningún algoritmo de búsqueda**:
parser de nivel, motor de reglas, reproducción/animación de una solución ya conocida,
y la interfaz donde después se va a enchufar el agente propio.

En esta fase el "agente" es un cable pelado: para el único nivel que tenemos,
devuelve la solución hardcodeada de abajo. Sirve solo para probar que el motor
y el visualizador andan de punta a punta (parseo → replay → animación).

**Lo que NO entra en esta fase** (eso queda para el equipo, según la consigna):
- BFS, DFS, Greedy, A*, IDDFS
- Heurísticas admisibles / no admisibles
- Conteo real de nodos expandidos / frontera (el motor solo define el molde de esos datos)

## 8. Fases siguientes

- **Fase 1** (equipo): BFS/DFS/Greedy/A*/IDDFS + heurísticas, sobre `legal_moves`/`apply_move`.
- **Fase 2** (equipo): instrumentar `nodes_expanded`/`frontier_nodes` reales en cada
  algoritmo — el motor no puede hacerlo por ustedes, es parte de cada implementación.
- **Fase 3**: sumar más niveles / más cajas (la consigna permite variar la complejidad).
- **Fase 4**: README de cómo correrlo + presentación.

## Cómo arrancar con Claude Code

1. Copiá este archivo como `ROADMAP.md` (o `CLAUDE.md`) en la raíz del repo.
2. Corré `claude` y pedile: *"Leé ROADMAP.md e implementá la Fase 0 completa: parser,
   engine, notation, HardcodedAgent, visualizador HTML, y el test dorado con
   level_01_ufo."*
3. Cuando eso ande y veas la animación de las 86 jugadas, seguís con la Fase 1
   (ahí entran BFS/A*/heurísticas, que es la parte que escriben ustedes).

---

## Correr los tests

No hay `pytest` instalado a nivel de sistema; usar un venv:

```bash
python3 -m venv .venv && .venv/bin/pip install pytest
cd TP1/Ejercicio2_sokoban && ../../<ruta al venv>/bin/python -m pytest sokoban/tests -v
```

Para la Fase 1, el equipo escribe en `sokoban/search/` usando únicamente
`legal_moves`/`apply_move`/`is_goal` de `engine.py` — no hace falta tocar el
parser, el motor ni el visualizador.
