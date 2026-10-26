#!/usr/bin/env python3
"""Skeleton of the slide deck builder (06-10): the names exist, the behaviour is written in the next commit."""

from __future__ import annotations

SLIDE_FORMAT: dict = {}
OUTLINE: tuple = ()
UNPLACED_SLIDE_FIGURES: dict = {}


class Slide:
    pass


def slide_templates(slide) -> list:
    return []


def build_deck(facts_values, results_dir=None, asset_map=None) -> list:
    return []


def write_deck(deck, out_dir, fmt=None, results_dir=None, asset_map=None) -> None:
    return None


def main(argv=None) -> int:
    return 1
