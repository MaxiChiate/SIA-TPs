"""Gene specification: the schema that describes each locus of a genotype.

A ``GeneSchema`` is what a ``Problem`` exposes to the engine: the ordered list of
genes (each with a numeric domain and a continuous/discrete flag) plus a
``block_size`` that lets crossover cut on coherent chunks instead of raw alleles.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from typing import Literal

from .rng import Rng

GeneKind = Literal["continuous", "discrete"]


@dataclass(frozen=True, slots=True)
class Gene:
    """One locus: a name, an inclusive numeric range, and whether it is discrete."""

    name: str
    lower: float
    upper: float
    kind: GeneKind = "continuous"

    def __post_init__(self) -> None:
        if self.upper < self.lower:
            raise ValueError(
                f"gene {self.name!r}: upper {self.upper} < lower {self.lower}"
            )

    def clamp(self, value: float) -> float:
        """Bring ``value`` back into ``[lower, upper]``; round it if discrete."""
        clamped = min(self.upper, max(self.lower, value))
        return float(round(clamped)) if self.kind == "discrete" else clamped

    def random_value(self, rng: Rng) -> float:
        """A fresh value drawn uniformly from this gene's domain."""
        return self.clamp(rng.uniform(self.lower, self.upper))


@dataclass(frozen=True, slots=True)
class GeneSchema:
    """The ordered genes of a genotype, grouped into blocks of ``block_size``.

    ``block_size`` is the natural unit of the problem (e.g. 10 for a triangle:
    6 vertex coordinates + RGBA). Crossover operators use it to keep those units
    intact; a generic problem leaves it at 1.
    """

    genes: tuple[Gene, ...]
    block_size: int = 1

    def __post_init__(self) -> None:
        if not self.genes:
            raise ValueError("GeneSchema needs at least one gene")
        if self.block_size < 1:
            raise ValueError(f"block_size must be >= 1, got {self.block_size}")
        if len(self.genes) % self.block_size != 0:
            raise ValueError(
                f"gene count {len(self.genes)} is not a multiple of "
                f"block_size {self.block_size}"
            )

    def __len__(self) -> int:
        return len(self.genes)

    def __iter__(self) -> Iterator[Gene]:
        return iter(self.genes)

    def __getitem__(self, index: int) -> Gene:
        return self.genes[index]

    @property
    def block_count(self) -> int:
        """How many blocks of ``block_size`` genes the genotype holds."""
        return len(self.genes) // self.block_size

    def clamp_vector(self, alleles: Sequence[float]) -> list[float]:
        """Clamp every allele to its gene's domain, returning a new list."""
        if len(alleles) != len(self.genes):
            raise ValueError(
                f"expected {len(self.genes)} alleles, got {len(alleles)}"
            )
        return [gene.clamp(value) for gene, value in zip(self.genes, alleles)]

    def random_vector(self, rng: Rng) -> list[float]:
        """A full genotype with every allele drawn uniformly from its domain."""
        return [gene.random_value(rng) for gene in self.genes]
