"""Parser de niveles en el formato de game-sokoban.com.

| Char | Significado |
|---|---|
| `#` | pared |
| ` ` | piso libre |
| `.` | objetivo (goal) |
| `$` | caja |
| `@` | jugador |
| `*` | caja ya sobre un objetivo |
| `+` | jugador parado sobre un objetivo |
"""

from __future__ import annotations

from .state import Level

_WALL = "#"
_FLOOR = " "
_GOAL = "."
_BOX = "$"
_PLAYER = "@"
_BOX_ON_GOAL = "*"
_PLAYER_ON_GOAL = "+"


class LevelParseError(ValueError):
    """El texto no describe un nivel válido (falta jugador, char desconocido, etc.)."""


def parse_level(text: str, name: str = "") -> Level:
    """Parsea el texto de un nivel al formato de game-sokoban.com.

    Los renglones pueden tener distinto largo (frecuente en archivos de
    Sokoban): se rellenan con espacios a la derecha hasta el ancho máximo
    antes de parsear. Soporta cualquier cantidad de cajas/goals.
    """
    raw_lines = text.rstrip("\n").split("\n")
    # Descarta líneas vacías al principio/final, típicas de triple-quoted strings.
    while raw_lines and raw_lines[0].strip() == "":
        raw_lines.pop(0)
    while raw_lines and raw_lines[-1].strip() == "":
        raw_lines.pop()

    if not raw_lines:
        raise LevelParseError("El nivel está vacío")

    width = max(len(line) for line in raw_lines)
    height = len(raw_lines)
    lines = [line.ljust(width) for line in raw_lines]

    walls: set[tuple[int, int]] = set()
    goals: set[tuple[int, int]] = set()
    boxes: set[tuple[int, int]] = set()
    player: tuple[int, int] | None = None

    for y, line in enumerate(lines):
        for x, char in enumerate(line):
            pos = (x, y)
            if char == _WALL:
                walls.add(pos)
            elif char == _FLOOR:
                pass
            elif char == _GOAL:
                goals.add(pos)
            elif char == _BOX:
                boxes.add(pos)
            elif char == _PLAYER:
                player = pos
            elif char == _BOX_ON_GOAL:
                goals.add(pos)
                boxes.add(pos)
            elif char == _PLAYER_ON_GOAL:
                goals.add(pos)
                player = pos
            else:
                raise LevelParseError(
                    f"Carácter desconocido {char!r} en la posición {pos}"
                )

    if player is None:
        raise LevelParseError("El nivel no tiene jugador (falta '@' o '+')")
    if not boxes:
        raise LevelParseError("El nivel no tiene cajas")
    if len(boxes) != len(goals):
        raise LevelParseError(
            f"Cantidad de cajas ({len(boxes)}) distinta de objetivos ({len(goals)})"
        )

    return Level(
        width=width,
        height=height,
        walls=frozenset(walls),
        goals=frozenset(goals),
        initial_player=player,
        initial_boxes=frozenset(boxes),
        name=name,
    )


def parse_level_file(path: str) -> Level:
    """Lee un nivel desde un archivo y usa el nombre del archivo como `Level.name`."""
    from pathlib import Path

    p = Path(path)
    return parse_level(p.read_text(), name=p.stem)
