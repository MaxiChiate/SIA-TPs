"""Runner paralelo de experimentos sobre el motor de Sokoban.

Corre cada combinación (nivel x algoritmo) N veces y vuelca una fila por
ejecución en un CSV, pensado para que otro sistema haga el análisis después.

Punto de entrada: `python analisis/main.py [config.yaml]`.
"""

from .config import AlgorithmSpec, BenchmarkConfig, BenchmarkConfigError, load_benchmark_config
from .records import CSV_COLUMNS, RunRecord
from .runner import build_tasks, run_benchmark

__all__ = [
    "AlgorithmSpec",
    "BenchmarkConfig",
    "BenchmarkConfigError",
    "load_benchmark_config",
    "CSV_COLUMNS",
    "RunRecord",
    "build_tasks",
    "run_benchmark",
]
